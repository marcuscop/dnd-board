from __future__ import annotations

import json
import random
from io import BytesIO
from dataclasses import asdict, dataclass
from pathlib import Path
from time import time_ns
from typing import Any

from fastapi import Body, FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, UnidentifiedImageError
from pillow_heif import register_heif_opener

from dnd_board.character_sheet import (
    AbilityScores,
    AbilityType,
    CharacterSheet,
    CharacterClassLevel,
    ClassType,
    ConditionApplicationMode,
    ConditionDuration,
    ConditionType,
    DiceType,
    EquipmentSlot,
    PartyMemberConfig,
    PartyMemberSheet,
    PartyMember,
    PartyManifest,
    RollPayload,
    RollLogEntry,
    RollLogEntryType,
    RollModifierBreakdown,
    RollResolutionMode,
    RollResourceSpend,
    RollResolution,
    RollSource,
    RestType,
    SheetSectionType,
    SkillType,
    SpellSource,
    TokenKind,
    build_attack_roll_payload,
    build_ability_check_roll_payload,
    build_character_sheet,
    build_damage_roll_payload,
    build_saving_throw_roll_payload,
    build_roll_action_payload,
    ability_modifier,
    enum_value,
    enum_key,
    enum_label,
    party_manifest_from_dict,
    positive_int,
    resolve_roll_against_target as resolve_dnd_roll_against_target,
    roll_payload_to_dict,
    roll_log_entry_to_dict,
    roll_resolution_to_dict,
    sheet_to_dict,
    typed_json_from_value,
)
from dnd_board.character_builder import (
    CharacterBuilderPayloadField,
    build_party_member_config,
    character_builder_options,
    character_builder_request_from_payload,
    payload_key,
)
from dnd_board.rules.progression import ProgressionChoiceId, apply_progression_choice, class_hit_die, fighter_asi_levels_up_to, parse_progression_choice_id, prune_progression_choices, rogue_asi_levels_up_to, update_class_level

BOARD_WIDTH = 1200
BOARD_HEIGHT = 720
MAX_PLAYERS = 8
ROLL_HISTORY_LIMIT = 10
DEFAULT_CAMPAIGN_ID = "test-campaign"
CAMPAIGN_DIR = Path("campaigns")
SHARED_DIR = Path("shared")
BOARD_DIR = Path("boards")
PARTY_DIR = Path("party")
SHARED_ASSET_DIR = SHARED_DIR / "assets"
UPLOAD_DIR = Path("data/uploads")
LEGACY_SAVE_DIR = Path("data/saves")
SAVE_DIR = LEGACY_SAVE_DIR
MAX_AVATAR_BYTES = 10 * 1024 * 1024
MAX_AVATAR_PIXELS = 16_000_000
MIN_TOKEN_RADIUS = 8
MAX_TOKEN_RADIUS = 480
DEFAULT_TOKEN_RADIUS = 70
DEFAULT_TOKEN_COLOR = "#111827"
MIN_REVEAL_POINT_DISTANCE = 8
REVEAL_POINT_DISTANCE_RATIO = 0.22

register_heif_opener()
Image.MAX_IMAGE_PIXELS = MAX_AVATAR_PIXELS


@dataclass
class Token:
    id: str
    kind: TokenKind
    name: str
    owner: str
    color: str
    x: float
    y: float
    radius: float
    inScene: bool
    avatarUrl: str | None = None
    lockedBy: str | None = None


@dataclass
class Player:
    id: str
    name: str
    player_key: str
    websocket: WebSocket | None
    room_id: str | None = None


@dataclass
class RevealedArea:
    x: float
    y: float
    radius: float


@dataclass
class FogState:
    hideMode: bool
    brushSize: float
    revealedAreas: list[RevealedArea]


@dataclass
class Board:
    id: str
    name: str
    url: str | None
    width: int
    height: int


@dataclass
class Asset:
    id: str
    kind: TokenKind
    name: str
    avatarUrl: str


@dataclass
class Campaign:
    id: str
    name: str
    path: Path


@dataclass
class Room:
    id: str
    tokens: dict[str, Token]
    players: dict[str, Player]
    fog: FogState
    board_id: str
    next_token_number: int
    pending_rolls: dict[tuple[str, str, str, str], RollPayload]
    roll_history: list[RollLogEntry]
    hit_points: dict[str, int]
    temporary_hit_points: dict[str, int]
    condition_overrides: dict[str, list[ConditionType]]
    condition_durations: dict[str, dict[ConditionType, ConditionDuration]]
    resource_uses: dict[str, dict[str, int]]
    equipment_slots: dict[str, dict[str, EquipmentSlot]]


app = FastAPI()
rooms: dict[str, Room] = {}
next_connection_id = 1


@app.get("/health")
async def health() -> PlainTextResponse:
    return PlainTextResponse("ok")


@app.post("/api/rooms/{room_id}/tokens/{token_id}/avatar")
async def upload_avatar(room_id: str, token_id: str, playerKey: str, file: UploadFile = File(...)) -> dict[str, Any]:
    room = get_or_create_room(sanitize_room_id(room_id))
    token = room.tokens.get(token_id)
    if token is None:
        raise HTTPException(status_code=404, detail="Token not found")

    player = Player(id="http-upload", name="Uploader", player_key=normalize_player_key(playerKey, room.id), websocket=None)
    if not can_control_token(player, token):
        raise HTTPException(status_code=403, detail="Cannot update another player's avatar")

    content = await file.read()
    if len(content) > MAX_AVATAR_BYTES:
        raise HTTPException(status_code=400, detail="Avatar image is too large")

    avatar_png = convert_avatar_to_png(content)

    target_dir = UPLOAD_DIR / room.id / token.id
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / "avatar.png"
    target.write_bytes(avatar_png)

    token.avatarUrl = f"/uploads/{room.id}/{token.id}/avatar.png?v={time_ns()}"
    await broadcast(room, {"type": "token_updated", "token": token_to_dict(token)})
    return {"token": token_to_dict(token)}


@app.post("/api/rooms/{room_id}/tokens/{token_id}/radius")
async def resize_token(room_id: str, token_id: str, playerKey: str, radius: float) -> dict[str, Any]:
    room = get_or_create_room(sanitize_room_id(room_id))
    player = Player(id="http-resize", name="DM", player_key=normalize_player_key(playerKey, room.id), websocket=None, room_id=room.id)
    token = await set_token_radius(room, player, token_id, radius)
    if token is None:
        raise HTTPException(status_code=404 if is_dm(player) else 403, detail="Token resize failed")
    return {"token": token_to_dict(token)}


@app.post("/api/rooms/{room_id}/save")
async def save_room(room_id: str, playerKey: str) -> dict[str, Any]:
    sanitized_room_id = sanitize_room_id(room_id)
    if normalize_player_key(playerKey, sanitized_room_id) != "dm":
        raise HTTPException(status_code=403, detail="Only the DM can save room state")

    room = get_or_create_room(sanitized_room_id)
    save_room_to_disk(room)
    return {
        "roomId": room.id,
        "saved": True,
        "tokens": [token_to_dict(token) for token in room.tokens.values()],
        "fog": fog_to_dict(room.fog),
        "board": board_to_dict(get_room_board(room)),
    }


@app.get("/api/rooms/{room_id}/state")
async def get_room_state(room_id: str) -> dict[str, Any]:
    room = get_or_create_room(sanitize_room_id(room_id))
    return room_state_message(room)


@app.get("/api/rooms/{room_id}/sheet")
async def get_room_sheets(room_id: str, playerKey: str) -> dict[str, Any]:
    sanitized_room_id = sanitize_room_id(room_id)
    room = get_or_create_room(sanitized_room_id)
    player = Player(id="http-sheet", name="Sheet Viewer", player_key=normalize_player_key(playerKey, room.id), websocket=None, room_id=room.id)
    return sheet_state_message(room, player)


@app.get("/api/rooms/{room_id}/sheet/{sheet_id}")
async def get_room_sheet(room_id: str, sheet_id: str, playerKey: str) -> dict[str, Any]:
    sanitized_room_id = sanitize_room_id(room_id)
    room = get_or_create_room(sanitized_room_id)
    player = Player(id="http-sheet", name="Sheet Viewer", player_key=normalize_player_key(playerKey, room.id), websocket=None, room_id=room.id)
    sheet = get_visible_sheet(room, player, sanitize_asset_id(sheet_id))
    if sheet is None:
        raise HTTPException(status_code=404, detail="Sheet not found")
    return {"roomId": room.id, "playerKey": player.player_key, "sheet": sheet_to_dict(sheet)}


@app.get("/api/rooms/{room_id}/character-builder/options")
async def get_character_builder_options(room_id: str) -> dict[str, Any]:
    return {"roomId": sanitize_room_id(room_id), **character_builder_options()}


@app.post("/api/rooms/{room_id}/characters")
async def create_room_character(room_id: str, playerKey: str, payload: dict[str, Any] | None = Body(default=None)) -> dict[str, Any]:
    sanitized_room_id = sanitize_room_id(room_id)
    room = get_or_create_room(sanitized_room_id)
    player = Player(id="http-character-builder", name="Character Builder", player_key=normalize_player_key(playerKey, room.id), websocket=None, room_id=room.id)
    body = payload if isinstance(payload, dict) else {}
    requested_member_id = sanitize_asset_id(str(body.get(payload_key(CharacterBuilderPayloadField.MEMBER_ID), "")))
    member_id = requested_member_id or ("player-1" if is_dm(player) else player.player_key)
    if normalize_party_member_id(member_id, "") != member_id:
        raise HTTPException(status_code=400, detail="Choose a player slot")
    if not is_dm(player) and member_id != player.player_key:
        raise HTTPException(status_code=403, detail="Cannot create a character for another player")
    existing_member = party_member_by_id(member_id, room.id)
    if existing_member is not None:
        raise HTTPException(status_code=400, detail="That player slot is already in the game")
    if len(load_party_members(room.id)) >= MAX_PLAYERS:
        raise HTTPException(status_code=400, detail="The party already has 8 characters")

    try:
        builder_request = character_builder_request_from_payload(body, default_member_id=member_id, default_owner=member_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    member = build_party_member_config(builder_request)
    save_party_member_config(room.id, member)
    refresh_party_token(room, member)
    room.resource_uses.pop(member.id, None)
    room.hit_points.pop(member.id, None)
    room.temporary_hit_points.pop(member.id, None)
    room.condition_overrides.pop(member.id, None)
    room.condition_durations.pop(member.id, None)
    await broadcast_room_state(room)
    return sheet_state_message(room, player)


@app.post("/api/rooms/{room_id}/sheet/{sheet_id}/rolls/attack")
async def roll_sheet_attack(room_id: str, sheet_id: str, playerKey: str, attackId: str = "main-hand") -> dict[str, Any]:
    return await create_attack_roll(room_id, sheet_id, playerKey, attackId)


@app.post("/api/rooms/{room_id}/sheet/{sheet_id}/rolls/damage")
async def roll_sheet_damage(room_id: str, sheet_id: str, playerKey: str, attackId: str = "main-hand") -> dict[str, Any]:
    return await create_damage_roll(room_id, sheet_id, playerKey, attackId)


@app.post("/api/rooms/{room_id}/sheet/{sheet_id}/rolls/ability-check")
async def roll_sheet_ability_check(room_id: str, sheet_id: str, playerKey: str, ability: str) -> dict[str, Any]:
    return await create_ability_check_roll(room_id, sheet_id, playerKey, ability)


@app.post("/api/rooms/{room_id}/sheet/{sheet_id}/rolls/saving-throw")
async def roll_sheet_saving_throw(room_id: str, sheet_id: str, playerKey: str, ability: str) -> dict[str, Any]:
    return await create_saving_throw_roll(room_id, sheet_id, playerKey, ability)


@app.post("/api/rooms/{room_id}/sheet/{sheet_id}/resources/{resource_id}/rolls/{action_id}")
async def roll_sheet_resource_action(room_id: str, sheet_id: str, resource_id: str, action_id: str, playerKey: str) -> dict[str, Any]:
    return await create_resource_roll(room_id, sheet_id, playerKey, resource_id, action_id)


@app.post("/api/rooms/{room_id}/sheet/{sheet_id}/abilities/{ability_id}/rolls/{action_id}")
async def roll_sheet_ability_action(room_id: str, sheet_id: str, ability_id: str, action_id: str, playerKey: str) -> dict[str, Any]:
    return await create_ability_roll(room_id, sheet_id, playerKey, ability_id, action_id)


@app.post("/api/rooms/{room_id}/sheet/{sheet_id}/rolls/clear")
async def clear_sheet_rolls(room_id: str, sheet_id: str, playerKey: str) -> dict[str, Any]:
    sanitized_room_id = sanitize_room_id(room_id)
    room = get_or_create_room(sanitized_room_id)
    player = Player(id="http-sheet-clear-rolls", name="Sheet Rolls", player_key=normalize_player_key(playerKey, room.id), websocket=None, room_id=room.id)
    sheet = get_visible_sheet(room, player, sanitize_asset_id(sheet_id))
    if sheet is None:
        raise HTTPException(status_code=404, detail="Sheet not found")
    if not can_control_sheet_roll(player, sheet):
        raise HTTPException(status_code=403, detail="Cannot clear this sheet's rolls")

    remove_pending_rolls_for_token(room, sheet.tokenId)
    return sheet_state_message(room, player)


@app.post("/api/rooms/{room_id}/sheet/{sheet_id}/resources/{resource_id}")
async def update_sheet_resource(room_id: str, sheet_id: str, resource_id: str, playerKey: str, currentUses: int) -> dict[str, Any]:
    sanitized_room_id = sanitize_room_id(room_id)
    room = get_or_create_room(sanitized_room_id)
    player = Player(id="http-sheet-resource", name="Sheet Tracker", player_key=normalize_player_key(playerKey, room.id), websocket=None, room_id=room.id)
    sheet = get_visible_sheet(room, player, sanitize_asset_id(sheet_id))
    if sheet is None:
        raise HTTPException(status_code=404, detail="Sheet not found")
    if not can_control_sheet_roll(player, sheet):
        raise HTTPException(status_code=403, detail="Cannot update this sheet")

    resource = next((candidate for candidate in sheet.resources if sanitize_asset_id(candidate.id) == sanitize_asset_id(resource_id)), None)
    if resource is None:
        raise HTTPException(status_code=404, detail="Resource not found")

    room.resource_uses.setdefault(sheet.tokenId, {})[resource.id] = clamp_int(int(currentUses), 0, resource.maxUses)
    updated = get_visible_sheet(room, player, sheet.id)
    return {"roomId": room.id, "sheet": sheet_to_dict(updated) if updated else sheet_to_dict(sheet)}


@app.post("/api/rooms/{room_id}/sheet/{sheet_id}/level")
async def update_sheet_level(room_id: str, sheet_id: str, playerKey: str, delta: int, className: str = "fighter") -> dict[str, Any]:
    sanitized_room_id = sanitize_room_id(room_id)
    room = get_or_create_room(sanitized_room_id)
    player = Player(id="http-sheet-level", name="DM", player_key=normalize_player_key(playerKey, room.id), websocket=None, room_id=room.id)
    if not is_dm(player):
        raise HTTPException(status_code=403, detail="Only the DM can level sheets")

    class_type = enum_value(ClassType, className)
    if class_type is None:
        raise HTTPException(status_code=400, detail="Invalid class")

    sanitized_sheet_id = sanitize_asset_id(sheet_id)
    current_sheet = get_visible_sheet(room, player, sanitized_sheet_id)
    if current_sheet is None:
        raise HTTPException(status_code=404, detail="Sheet not found")
    level_delta = clamp_int(delta, -1, 1)
    if level_delta > 0 and current_sheet.pendingChoices:
        raise HTTPException(status_code=400, detail=f"Resolve pending level choices before leveling up: {pending_choice_summary(current_sheet)}")

    updated_member = update_party_member_config(
        room.id,
        sanitized_sheet_id,
        lambda member: set_member_class_levels(member, update_class_level(member_sheet_classes(member), class_type, level_delta)),
    )
    if updated_member is None:
        raise HTTPException(status_code=404, detail="Sheet not found")

    room.resource_uses.pop(updated_member.id, None)
    room.hit_points.pop(updated_member.id, None)
    room.temporary_hit_points.pop(updated_member.id, None)
    room.condition_overrides.pop(updated_member.id, None)
    room.condition_durations.pop(updated_member.id, None)
    sheet = get_visible_sheet(room, player, updated_member.id)
    return {"roomId": room.id, "sheet": sheet_to_dict(sheet) if sheet else None}


@app.post("/api/rooms/{room_id}/sheet/{sheet_id}/choices/{choice_id}")
async def update_sheet_progression_choice(room_id: str, sheet_id: str, choice_id: str, playerKey: str, payload: dict[str, Any] | None = Body(default=None)) -> dict[str, Any]:
    sanitized_room_id = sanitize_room_id(room_id)
    room = get_or_create_room(sanitized_room_id)
    player = Player(id="http-sheet-choice", name="Sheet Choice", player_key=normalize_player_key(playerKey, room.id), websocket=None, room_id=room.id)
    sheet = get_visible_sheet(room, player, sanitize_asset_id(sheet_id))
    if sheet is None:
        raise HTTPException(status_code=404, detail="Sheet not found")
    if not can_control_sheet_roll(player, sheet):
        raise HTTPException(status_code=403, detail="Cannot update this sheet")

    values = payload.get("values", []) if isinstance(payload, dict) else []
    if not isinstance(values, list):
        raise HTTPException(status_code=400, detail="Choice values must be a list")

    parsed_choice_id = parse_progression_choice_id(choice_id)
    if parsed_choice_id == ProgressionChoiceId.HIT_POINT_INCREASE:
        updated_member = update_party_member_config(
            room.id,
            sanitize_asset_id(sheet_id),
            lambda member: apply_member_hit_point_choice(member, str(values[0]) if values else "fixed"),
        )
    elif parsed_choice_id == ProgressionChoiceId.FIGHTER_ABILITY_SCORE_IMPROVEMENT:
        updated_member = update_party_member_config(
            room.id,
            sanitize_asset_id(sheet_id),
            lambda member: apply_member_ability_score_improvement(member, [str(value) for value in values]),
        )
    elif parsed_choice_id == ProgressionChoiceId.ROGUE_ABILITY_SCORE_IMPROVEMENT:
        updated_member = update_party_member_config(
            room.id,
            sanitize_asset_id(sheet_id),
            lambda member: apply_member_ability_score_improvement(member, [str(value) for value in values]),
        )
    elif parsed_choice_id == ProgressionChoiceId.ELDRITCH_KNIGHT_SPELLS:
        updated_member = update_party_member_config(
            room.id,
            sanitize_asset_id(sheet_id),
            lambda member: apply_member_eldritch_knight_spells(member, [str(value) for value in values]),
        )
    elif parsed_choice_id == ProgressionChoiceId.ARCANE_TRICKSTER_SPELLS:
        updated_member = update_party_member_config(
            room.id,
            sanitize_asset_id(sheet_id),
            lambda member: apply_member_arcane_trickster_spells(member, [str(value) for value in values]),
        )
    elif parsed_choice_id is None:
        raise HTTPException(status_code=400, detail="Invalid progression choice")
    else:
        updated_member = update_party_member_config(
            room.id,
            sanitize_asset_id(sheet_id),
            lambda member: set_member_class_levels(member, apply_progression_choice(member_sheet_classes(member), parsed_choice_id, [str(value) for value in values])),
        )
    if updated_member is None:
        raise HTTPException(status_code=404, detail="Sheet not found")

    room.resource_uses.pop(updated_member.id, None)
    updated_sheet = get_visible_sheet(room, player, updated_member.id)
    return {"roomId": room.id, "sheet": sheet_to_dict(updated_sheet) if updated_sheet else None}


@app.post("/api/rooms/{room_id}/sheet/rest")
async def rest_room_sheets(room_id: str, playerKey: str, rest: str) -> dict[str, Any]:
    sanitized_room_id = sanitize_room_id(room_id)
    room = get_or_create_room(sanitized_room_id)
    player = Player(id="http-sheet-rest", name="DM", player_key=normalize_player_key(playerKey, room.id), websocket=None, room_id=room.id)
    if not is_dm(player):
        raise HTTPException(status_code=403, detail="Only the DM can rest sheets")

    rest_type = parse_rest_type(rest)
    if rest_type is None:
        raise HTTPException(status_code=400, detail="Invalid rest type")

    for sheet in visible_sheets(room, player):
        if sheet.kind == TokenKind.CHARACTER:
            reset_sheet_resources(room, sheet, rest_type)
            reset_sheet_conditions(room, sheet, rest_type)
            reset_sheet_temporary_hit_points(room, sheet, rest_type)
    return sheet_state_message(room, player)


@app.post("/api/rooms/{room_id}/sheet/{sheet_id}/equipment/{item_id}/slot")
async def update_sheet_equipment_slot(room_id: str, sheet_id: str, item_id: str, playerKey: str, slot: str) -> dict[str, Any]:
    sanitized_room_id = sanitize_room_id(room_id)
    room = get_or_create_room(sanitized_room_id)
    player = Player(id="http-sheet-equipment", name="Sheet Equipment", player_key=normalize_player_key(playerKey, room.id), websocket=None, room_id=room.id)
    sheet = get_visible_sheet(room, player, sanitize_asset_id(sheet_id))
    if sheet is None:
        raise HTTPException(status_code=404, detail="Sheet not found")
    if not can_control_sheet_roll(player, sheet):
        raise HTTPException(status_code=403, detail="Cannot update this sheet")

    item = next((candidate for candidate in sheet.equipment if sanitize_asset_id(candidate.id) == sanitize_asset_id(item_id)), None)
    if item is None:
        raise HTTPException(status_code=404, detail="Equipment item not found")

    equipment_slot = enum_value(EquipmentSlot, slot)
    if equipment_slot is None:
        raise HTTPException(status_code=400, detail="Invalid equipment slot")
    if equipment_slot not in valid_equipment_slots(item):
        raise HTTPException(status_code=400, detail="Invalid slot for equipment item")

    set_equipment_slot(room, sheet, item.id, equipment_slot)
    updated = get_visible_sheet(room, player, sheet.id)
    return {"roomId": room.id, "sheet": sheet_to_dict(updated) if updated else sheet_to_dict(sheet)}


@app.post("/api/rooms/{room_id}/sheet/{sheet_id}/conditions/{condition}")
async def update_sheet_condition(room_id: str, sheet_id: str, condition: str, playerKey: str, active: bool) -> dict[str, Any]:
    sanitized_room_id = sanitize_room_id(room_id)
    room = get_or_create_room(sanitized_room_id)
    player = Player(id="http-sheet-condition", name="Sheet Condition", player_key=normalize_player_key(playerKey, room.id), websocket=None, room_id=room.id)
    sheet = get_visible_sheet(room, player, sanitize_asset_id(sheet_id))
    if sheet is None:
        raise HTTPException(status_code=404, detail="Sheet not found")
    if not can_control_sheet_roll(player, sheet):
        raise HTTPException(status_code=403, detail="Cannot update this sheet")

    condition_type = enum_value(ConditionType, condition)
    if condition_type is None:
        raise HTTPException(status_code=400, detail="Invalid condition")

    next_conditions = updated_conditions(sheet.conditions, condition_type, active)
    updated_member = update_party_member_config(
        room.id,
        sanitize_asset_id(sheet_id),
        lambda member: set_member_conditions(member, next_conditions),
    )

    updated_sheet_id = updated_member.id if updated_member is not None else sheet.tokenId
    room.condition_overrides[updated_sheet_id] = next_conditions
    if active:
        room.condition_durations.setdefault(updated_sheet_id, {})[condition_type] = ConditionDuration.MANUAL
    else:
        room.condition_durations.setdefault(updated_sheet_id, {}).pop(condition_type, None)
    updated = get_visible_sheet(room, player, updated_sheet_id)
    return {"roomId": room.id, "sheet": sheet_to_dict(updated) if updated else None}


@app.post("/api/rooms/{room_id}/rolls/{roll_id}/resolve")
async def resolve_roll(room_id: str, roll_id: str, playerKey: str, targetSheetId: str) -> dict[str, Any]:
    sanitized_room_id = sanitize_room_id(room_id)
    room = get_or_create_room(sanitized_room_id)
    player = Player(id="http-roll-resolve", name="DM", player_key=normalize_player_key(playerKey, room.id), websocket=None, room_id=room.id)
    if not is_dm(player):
        raise HTTPException(status_code=403, detail="Only the DM can resolve rolls")

    roll = next((candidate for candidate in room.pending_rolls.values() if candidate.id == sanitize_asset_id(roll_id)), None)
    if roll is None:
        raise HTTPException(status_code=404, detail="Roll not found")

    target = get_visible_sheet(room, player, sanitize_asset_id(targetSheetId))
    if target is None:
        raise HTTPException(status_code=404, detail="Target sheet not found")

    resolution = resolve_roll_against_target(room, roll, target)
    room.pending_rolls.pop(roll_queue_key(roll), None)
    resolution_data = roll_resolution_to_dict(resolution)
    log_entry = append_roll_log_entry(
        room,
        RollLogEntry(
            id=f"log-{resolution.id}",
            entryType=RollLogEntryType.ROLL_RESOLVED,
            createdAt=resolution.createdAt,
            roll=roll,
            resolution=resolution,
        ),
    )
    await broadcast(
        room,
        {
            "type": "roll_resolved",
            "rollId": roll.id,
            "tokenId": roll.tokenId,
            "resolution": resolution_data,
            "logEntry": roll_log_entry_to_dict(log_entry),
        },
    )
    return {"roomId": room.id, "resolution": resolution_data, "logEntry": roll_log_entry_to_dict(log_entry)}


@app.get("/campaigns/{campaign_id}/{asset_kind}/{filename}")
async def serve_campaign_asset(campaign_id: str, asset_kind: str, filename: str) -> FileResponse:
    campaign = get_campaign(sanitize_asset_id(campaign_id))
    if campaign is None or asset_kind not in {"boards", "party"}:
        raise HTTPException(status_code=404, detail="Asset not found")

    target = campaign.path / asset_kind / Path(filename).name
    if not target.is_file():
        raise HTTPException(status_code=404, detail="Asset not found")
    return FileResponse(target)


@app.post("/api/rooms/{room_id}/load")
async def load_room(room_id: str, playerKey: str) -> dict[str, Any]:
    sanitized_room_id = sanitize_room_id(room_id)
    if normalize_player_key(playerKey, sanitized_room_id) != "dm":
        raise HTTPException(status_code=403, detail="Only the DM can load room state")

    room = get_or_create_room(sanitized_room_id)
    loaded = await load_room_from_disk(room, Player(id="http-load", name="DM", player_key="dm", websocket=None))
    if not loaded:
        raise HTTPException(status_code=404, detail="No saved room state found")

    return {
        "roomId": room.id,
        "loaded": True,
        "tokens": [token_to_dict(token) for token in room.tokens.values()],
        "fog": fog_to_dict(room.fog),
        "board": board_to_dict(get_room_board(room)),
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    global next_connection_id
    await websocket.accept()
    player = Player(id=f"connection-{next_connection_id}", name="Player", player_key="", websocket=websocket)
    next_connection_id += 1
    await send(player, {"type": "hello", "playerId": player.id})

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                continue

            await handle_message(player, message)
    except WebSocketDisconnect:
        await leave_room(player)


async def handle_message(player: Player, message: dict[str, Any]) -> None:
    message_type = message.get("type")

    if message_type == "join_room":
        await join_room(
            player,
            str(message.get("roomId", "table")),
            str(message.get("playerName", "Player")),
            str(message.get("playerKey", "")),
        )
        return

    room = get_player_room(player)
    if room is None:
        return

    if message_type == "request_token_lock":
        await lock_token(room, player, str(message.get("tokenId", "")), message)
        return

    if message_type == "move_token":
        await move_token(room, player, str(message.get("tokenId", "")), message)
        return

    if message_type == "release_token":
        await release_token(room, player, str(message.get("tokenId", "")))
        return

    if message_type == "set_token_scene":
        await set_token_scene(room, player, str(message.get("tokenId", "")), message)
        return

    if message_type == "set_token_radius":
        await set_token_radius(room, player, str(message.get("tokenId", "")), message.get("radius"))
        return

    if message_type == "set_fog_mode":
        await set_fog_mode(room, player, message)
        return

    if message_type == "reveal_fog":
        await reveal_fog(room, player, message)
        return

    if message_type == "set_board":
        await set_board(room, player, str(message.get("boardId", "")))
        return

    if message_type == "load_asset":
        await load_asset_token(room, player, str(message.get("assetKind", "")), str(message.get("assetId", "")))
        return

    if message_type == "delete_token":
        await delete_token(room, player, str(message.get("tokenId", "")))
        return

    if message_type == "clear_scene":
        await clear_scene(room, player)


async def join_room(player: Player, requested_room_id: str, player_name: str, player_key: str) -> None:
    await leave_room(player)

    room_id = sanitize_room_id(requested_room_id)
    room = get_or_create_room(room_id)

    if len(room.players) >= MAX_PLAYERS:
        if player.websocket is not None:
            await player.websocket.close(code=1008, reason="Room is full")
        return

    player.room_id = room_id
    player.player_key = normalize_player_key(player_key, room_id)
    player.name = player_name.strip()[:24] or "Player"
    room.players[player.id] = player

    await broadcast_room_state(room)


async def leave_room(player: Player) -> None:
    if player.room_id is None:
        return

    room = rooms.get(player.room_id)
    player.room_id = None
    if room is None:
        return

    room.players.pop(player.id, None)
    for token in room.tokens.values():
        if token.lockedBy == player.player_key:
            token.lockedBy = None
            await broadcast(room, {"type": "token_updated", "token": token_to_dict(token)})

    await broadcast(room, {"type": "player_count", "count": len(room.players)})

    if not room.players:
        rooms.pop(room.id, None)


async def lock_token(room: Room, player: Player, token_id: str, message: dict[str, Any] | None = None) -> None:
    token = room.tokens.get(token_id)
    if token is None:
        return

    if not can_control_token(player, token):
        await send(player, {"type": "token_lock_denied", "tokenId": token_id, "reason": "not_owner"})
        return

    if token.lockedBy and token.lockedBy != player.player_key:
        await send(player, {"type": "token_lock_denied", "tokenId": token_id, "lockedBy": token.lockedBy})
        return

    if message is not None:
        apply_token_radius_from_message(room, player, token, message)
    token.lockedBy = player.player_key
    await broadcast(room, {"type": "token_updated", "token": token_to_dict(token)})


async def move_token(room: Room, player: Player, token_id: str, message: dict[str, Any]) -> None:
    token = room.tokens.get(token_id)
    if token is None or token.lockedBy != player.player_key or not can_control_token(player, token):
        return

    board = get_room_board(room)
    apply_token_radius_from_message(room, player, token, message)
    token.x = clamp(to_float(message.get("x")), token.radius, board.width - token.radius)
    token.y = clamp(to_float(message.get("y")), token.radius, board.height - token.radius)
    await broadcast(room, {"type": "token_updated", "token": token_to_dict(token)})


async def release_token(room: Room, player: Player, token_id: str) -> None:
    token = room.tokens.get(token_id)
    if token is None or token.lockedBy != player.player_key or not can_control_token(player, token):
        return

    token.lockedBy = None
    await broadcast(room, {"type": "token_updated", "token": token_to_dict(token)})


async def set_token_scene(room: Room, player: Player, token_id: str, message: dict[str, Any]) -> None:
    token = room.tokens.get(token_id)
    if token is None or token.lockedBy != player.player_key or not can_control_token(player, token):
        return

    token.inScene = bool(message.get("inScene"))
    if token.inScene:
        board = get_room_board(room)
        apply_token_radius_from_message(room, player, token, message)
        token.x = clamp(to_float(message.get("x", token.x)), token.radius, board.width - token.radius)
        token.y = clamp(to_float(message.get("y", token.y)), token.radius, board.height - token.radius)

    await broadcast(room, {"type": "token_updated", "token": token_to_dict(token)})


async def set_token_radius(room: Room, player: Player, token_id: str, radius: Any) -> Token | None:
    if not is_dm(player):
        return None

    token = room.tokens.get(token_id)
    if token is None:
        return None

    board = get_room_board(room)
    token.radius = clamp(to_float(radius), MIN_TOKEN_RADIUS, max_token_radius(board))
    token.x = clamp(token.x, token.radius, board.width - token.radius)
    token.y = clamp(token.y, token.radius, board.height - token.radius)
    await broadcast(room, {"type": "token_updated", "token": token_to_dict(token)})
    await broadcast_room_state(room)
    return token


def apply_token_radius_from_message(room: Room, player: Player, token: Token, message: dict[str, Any]) -> None:
    if not is_dm(player) or "radius" not in message:
        return

    board = get_room_board(room)
    token.radius = clamp(to_float(message.get("radius")), MIN_TOKEN_RADIUS, max_token_radius(board))


async def set_fog_mode(room: Room, player: Player, message: dict[str, Any]) -> None:
    if not is_dm(player):
        return

    hide_mode = bool(message.get("hideMode"))
    room.fog.hideMode = hide_mode
    room.fog.brushSize = clamp(to_float(message.get("brushSize", room.fog.brushSize)), 20, 360)
    if not hide_mode:
        room.fog.revealedAreas = []

    await broadcast(room, {"type": "fog_updated", "fog": fog_to_dict(room.fog)})


async def reveal_fog(room: Room, player: Player, message: dict[str, Any]) -> None:
    if not is_dm(player) or not room.fog.hideMode:
        return

    board = get_room_board(room)
    area = RevealedArea(
        x=clamp(to_float(message.get("x")), 0, board.width),
        y=clamp(to_float(message.get("y")), 0, board.height),
        radius=clamp(to_float(message.get("radius", room.fog.brushSize)), 20, 360),
    )
    if is_redundant_reveal_area(room.fog.revealedAreas, area):
        return

    room.fog.revealedAreas.append(area)
    await broadcast(room, {"type": "fog_updated", "fog": fog_to_dict(room.fog)})


def is_redundant_reveal_area(revealed_areas: list[RevealedArea], area: RevealedArea) -> bool:
    if not revealed_areas:
        return False

    previous = revealed_areas[-1]
    if abs(previous.radius - area.radius) > 0.001:
        return False

    min_distance = max(MIN_REVEAL_POINT_DISTANCE, area.radius * REVEAL_POINT_DISTANCE_RATIO)
    return ((previous.x - area.x) ** 2 + (previous.y - area.y) ** 2) ** 0.5 < min_distance


async def set_board(room: Room, player: Player, board_id: str) -> None:
    if not is_dm(player):
        return

    board = get_board(board_id, room.id)
    if board is None:
        return

    board_changed = room.board_id != board.id
    room.board_id = board.id
    await broadcast(room, {"type": "board_updated", "board": board_to_dict(board)})
    if board_changed and room.fog.hideMode:
        room.fog.revealedAreas = []
        await broadcast(room, {"type": "fog_updated", "fog": fog_to_dict(room.fog)})


async def load_asset_token(room: Room, player: Player, asset_kind: str, asset_id: str) -> None:
    if not is_dm(player):
        return

    asset = get_asset(asset_kind, asset_id)
    if asset is None:
        return

    board = get_room_board(room)
    token = Token(
        id=f"{enum_key(asset.kind)}-{room.next_token_number}",
        kind=TokenKind.ASSET,
        name=asset.name,
        owner="dm",
        color=DEFAULT_TOKEN_COLOR,
        x=board.width / 2,
        y=board.height / 2,
        radius=default_token_radius(board),
        inScene=True,
        avatarUrl=asset.avatarUrl,
    )
    room.next_token_number += 1
    room.tokens[token.id] = token
    await broadcast(room, {"type": "token_updated", "token": token_to_dict(token)})


async def delete_token(room: Room, player: Player, token_id: str) -> None:
    if not is_dm(player):
        return

    token = room.tokens.get(token_id)
    if token is None or token.kind == TokenKind.CHARACTER:
        return

    room.tokens.pop(token_id)
    remove_pending_rolls_for_token(room, token_id)
    room.hit_points.pop(token_id, None)
    room.temporary_hit_points.pop(token_id, None)
    room.condition_overrides.pop(token_id, None)
    room.condition_durations.pop(token_id, None)
    await broadcast(room, {"type": "token_deleted", "tokenId": token_id})


async def clear_scene(room: Room, player: Player) -> None:
    if not is_dm(player):
        return

    for token in room.tokens.values():
        token.inScene = False
        token.lockedBy = None
    await broadcast_room_state(room)


def get_or_create_room(room_id: str) -> Room:
    room = rooms.get(room_id)
    if room is not None:
        return room

    saved_board_id = load_saved_board_id(room_id)
    saved_board = get_board(saved_board_id, room_id) or fallback_board()
    saved_tokens = load_saved_tokens(room_id, saved_board)
    tokens = merge_saved_tokens_with_party(saved_tokens, room_id) if saved_tokens is not None else seed_tokens(room_id)
    room = Room(
        id=room_id,
        tokens={token.id: token for token in tokens},
        players={},
        fog=load_saved_fog(room_id, saved_board),
        board_id=saved_board_id,
        next_token_number=next_dynamic_token_number(tokens),
        pending_rolls={},
        roll_history=[],
        hit_points={},
        temporary_hit_points={},
        condition_overrides={},
        condition_durations={},
        resource_uses=load_saved_resource_uses(room_id),
        equipment_slots={},
    )
    rooms[room_id] = room
    return room


def seed_tokens(campaign_id: str | None = None) -> list[Token]:
    return [party_member_to_token(member, index) for index, member in enumerate(load_party_members(campaign_id))]


def party_member_to_token(member: PartyMember, index: int) -> Token:
    return Token(
        id=member.id,
        kind=TokenKind.CHARACTER,
        name=member.name,
        owner=member.owner,
        color=DEFAULT_TOKEN_COLOR,
        x=240 + index * 80,
        y=260 + (index % 2) * 80,
        radius=DEFAULT_TOKEN_RADIUS,
        inScene=False,
        avatarUrl=member.avatarUrl,
    )


def merge_saved_tokens_with_party(saved_tokens: list[Token], campaign_id: str | None = None) -> list[Token]:
    saved_by_id = {token.id: token for token in saved_tokens}
    tokens: list[Token] = []
    for index, member in enumerate(load_party_members(campaign_id)):
        token = party_member_to_token(member, index)
        saved = saved_by_id.get(token.id)
        if saved is not None and saved.kind == TokenKind.CHARACTER:
            token.x = saved.x
            token.y = saved.y
            token.radius = saved.radius
            token.inScene = saved.inScene
        tokens.append(token)

    tokens.extend(token for token in saved_tokens if token.kind != TokenKind.CHARACTER)
    return tokens


def get_player_room(player: Player) -> Room | None:
    if player.room_id is None:
        return None
    return rooms.get(player.room_id)


def get_room_board(room: Room) -> Board:
    return get_board(room.board_id, room.id) or fallback_board()


def max_token_radius(board: Board) -> float:
    return min(MAX_TOKEN_RADIUS, max(MIN_TOKEN_RADIUS, min(board.width, board.height) / 3))


def default_token_radius(board: Board) -> float:
    return clamp(DEFAULT_TOKEN_RADIUS, MIN_TOKEN_RADIUS, max_token_radius(board))


async def broadcast_room_state(room: Room) -> None:
    await broadcast(room, room_state_message(room))


def room_state_message(room: Room) -> dict[str, Any]:
    return {
        "type": "room_state",
        "roomId": room.id,
        "players": [{"id": player.id, "name": player.name} for player in room.players.values()],
        "tokens": [token_to_dict(token) for token in room.tokens.values()],
        "fog": fog_to_dict(room.fog),
        "board": board_to_dict(get_room_board(room)),
        "boards": [board_to_dict(board) for board in list_boards(room.id)],
        "assets": [asset_to_dict(asset) for asset in list_assets()],
    }


def sheet_state_message(room: Room, player: Player) -> dict[str, Any]:
    return {
        "type": "sheet_state",
        "roomId": room.id,
        "playerKey": player.player_key,
        "sheets": [sheet_to_dict(sheet) for sheet in visible_sheets(room, player)],
        "pendingRolls": [roll_payload_to_dict(roll) for roll in visible_pending_rolls(room, player)],
        "rollHistory": [roll_log_entry_to_dict(entry) for entry in visible_roll_history(room, player)],
    }


def visible_sheets(room: Room, player: Player) -> list[CharacterSheet]:
    return [token_to_sheet(token, room.id, room.hit_points.get(token.id)) for token in room.tokens.values() if can_view_sheet(player, token)]


def visible_pending_rolls(room: Room, player: Player) -> list[RollPayload]:
    visible_token_ids = {sheet.tokenId for sheet in visible_sheets(room, player)}
    return [roll for roll in room.pending_rolls.values() if roll.tokenId in visible_token_ids]


def visible_roll_history(room: Room, player: Player) -> list[RollLogEntry]:
    visible_token_ids = {sheet.tokenId for sheet in visible_sheets(room, player)}
    return [entry for entry in room.roll_history if entry.roll.tokenId in visible_token_ids]


def get_visible_sheet(room: Room, player: Player, sheet_id: str) -> CharacterSheet | None:
    for sheet in visible_sheets(room, player):
        if sheet.id == sheet_id:
            return sheet
    return None


def can_view_sheet(player: Player, token: Token) -> bool:
    return is_dm(player) or token.kind == TokenKind.CHARACTER


def can_control_sheet_roll(player: Player, sheet: CharacterSheet) -> bool:
    return is_dm(player) or player.player_key == sheet.owner


def token_to_sheet(token: Token, campaign_id: str | None = None, current_hp: int | None = None) -> CharacterSheet:
    party_member = party_member_by_id(token.id, campaign_id) if token.kind == TokenKind.CHARACTER else None
    room = rooms.get(campaign_id or "")
    resource_overrides = room.resource_uses.get(token.id, {}) if room is not None else {}
    equipment_slot_overrides = room.equipment_slots.get(token.id, {}) if room is not None else {}
    sheet = build_character_sheet(
        token_id=token.id,
        kind=token.kind,
        name=token.name,
        owner=token.owner,
        avatar_url=token.avatarUrl,
        party_member=party_member,
        current_hp=current_hp,
        resource_overrides=resource_overrides,
        equipment_slot_overrides=equipment_slot_overrides,
    )
    if room is not None:
        sheet.hp.temporary = room.temporary_hit_points.get(token.id, sheet.hp.temporary)
        sheet.conditions = room.condition_overrides.get(token.id, sheet.conditions)
    return sheet


async def create_attack_roll(room_id: str, sheet_id: str, player_key: str, attack_id: str) -> dict[str, Any]:
    room, player, sheet = roll_context(room_id, sheet_id, player_key)
    action = find_attack(sheet, attack_id)
    payload = build_attack_roll_payload(sheet, player.player_key, action)
    return await store_roll(room, payload)


async def create_damage_roll(room_id: str, sheet_id: str, player_key: str, attack_id: str) -> dict[str, Any]:
    room, player, sheet = roll_context(room_id, sheet_id, player_key)
    action = find_attack(sheet, attack_id)
    payload = build_damage_roll_payload(sheet, player.player_key, action)
    return await store_roll(room, payload)


async def create_ability_check_roll(room_id: str, sheet_id: str, player_key: str, ability_key: str) -> dict[str, Any]:
    room, player, sheet = roll_context(room_id, sheet_id, player_key)
    ability = parse_ability(ability_key)
    payload = build_ability_check_roll_payload(sheet, player.player_key, ability)
    return await store_roll(room, payload)


async def create_saving_throw_roll(room_id: str, sheet_id: str, player_key: str, ability_key: str) -> dict[str, Any]:
    room, player, sheet = roll_context(room_id, sheet_id, player_key)
    ability = parse_ability(ability_key)
    payload = build_saving_throw_roll_payload(sheet, player.player_key, ability)
    return await store_roll(room, payload)


def parse_ability(ability_key: str) -> AbilityType:
    ability = enum_value(AbilityType, ability_key)
    if ability is None:
        raise HTTPException(status_code=404, detail="Ability not found")
    return ability


async def create_resource_roll(room_id: str, sheet_id: str, player_key: str, resource_id: str, action_id: str) -> dict[str, Any]:
    room, player, sheet = roll_context(room_id, sheet_id, player_key)
    sanitized_resource_id = sanitize_asset_id(resource_id)
    resource = next((candidate for candidate in sheet.resources if sanitize_asset_id(candidate.id) == sanitized_resource_id), None)
    if resource is None:
        raise HTTPException(status_code=404, detail="Resource not found")

    actions = resource.rollActions or []
    sanitized_action_id = sanitize_asset_id(action_id)
    action = next((candidate for candidate in actions if sanitize_asset_id(enum_key(candidate.id)) == sanitized_action_id), None)
    if action is None:
        raise HTTPException(status_code=404, detail="Roll action not found")

    source = RollSource(section=SheetSectionType.RESOURCES, sourceId=resource.id, actionId=enum_key(action.id))
    payload = build_roll_action_payload(sheet, player.player_key, source, action, source_label=resource.name)
    if action.consumesResource is not None:
        spend_resource_use(room, sheet, enum_key(action.consumesResource), payload)
    return await store_roll(room, payload)


async def create_ability_roll(room_id: str, sheet_id: str, player_key: str, ability_id: str, action_id: str) -> dict[str, Any]:
    room, player, sheet = roll_context(room_id, sheet_id, player_key)
    sanitized_ability_id = sanitize_asset_id(ability_id)
    ability = next((candidate for candidate in sheet.abilities if sanitize_asset_id(candidate.id) == sanitized_ability_id), None)
    if ability is None:
        raise HTTPException(status_code=404, detail="Ability not found")

    actions = ability.rollActions or []
    sanitized_action_id = sanitize_asset_id(action_id)
    action = next((candidate for candidate in actions if sanitize_asset_id(enum_key(candidate.id)) == sanitized_action_id), None)
    if action is None:
        raise HTTPException(status_code=404, detail="Roll action not found")

    source = RollSource(section=SheetSectionType.ABILITIES, sourceId=ability.id, actionId=enum_key(action.id))
    payload = build_roll_action_payload(sheet, player.player_key, source, action, source_label=ability.source)
    if action.consumesResource is not None:
        spend_resource_use(room, sheet, enum_key(action.consumesResource), payload)
    return await store_roll(room, payload)


def roll_context(room_id: str, sheet_id: str, player_key: str) -> tuple[Room, Player, CharacterSheet]:
    sanitized_room_id = sanitize_room_id(room_id)
    room = get_or_create_room(sanitized_room_id)
    player = Player(id="http-sheet-roll", name="Sheet Roller", player_key=normalize_player_key(player_key, room.id), websocket=None, room_id=room.id)
    sheet = get_visible_sheet(room, player, sanitize_asset_id(sheet_id))
    if sheet is None:
        raise HTTPException(status_code=404, detail="Sheet not found")
    if not can_control_sheet_roll(player, sheet):
        raise HTTPException(status_code=403, detail="Cannot roll for this sheet")
    return room, player, sheet


def find_attack(sheet: CharacterSheet, attack_id: str):
    sanitized_attack_id = sanitize_asset_id(attack_id)
    action = next((attack for attack in sheet.attacks if sanitize_asset_id(attack.id) == sanitized_attack_id), None)
    if action is None and sanitized_attack_id == "main-hand" and sheet.attacks:
        action = sheet.attacks[0]
    if action is None:
        raise HTTPException(status_code=404, detail="Attack not found")
    return action


async def store_roll(room: Room, payload: RollPayload) -> dict[str, Any]:
    if roll_resolves_immediately(payload):
        target = source_sheet_for_roll(room, payload)
        if target is None:
            raise HTTPException(status_code=404, detail="Sheet not found")
        resolution = resolve_roll_against_target(room, payload, target)
        resolution_data = roll_resolution_to_dict(resolution)
        log_entry = append_roll_log_entry(
            room,
            RollLogEntry(
                id=f"log-{resolution.id}",
                entryType=RollLogEntryType.ROLL_RESOLVED,
                createdAt=resolution.createdAt,
                roll=payload,
                resolution=resolution,
            ),
        )
        await broadcast(
            room,
            {
                "type": "roll_resolved",
                "rollId": payload.id,
                "tokenId": payload.tokenId,
                "resolution": resolution_data,
                "logEntry": roll_log_entry_to_dict(log_entry),
            },
        )
        return {"roomId": room.id, "roll": roll_payload_to_dict(payload), "resolution": resolution_data, "logEntry": roll_log_entry_to_dict(log_entry)}

    room.pending_rolls[roll_queue_key(payload)] = payload
    roll = roll_payload_to_dict(payload)
    log_entry = append_roll_log_entry(
        room,
        RollLogEntry(
            id=f"log-{payload.id}",
            entryType=RollLogEntryType.ROLL_CREATED,
            createdAt=payload.createdAt,
            roll=payload,
        ),
    )
    await broadcast(room, {"type": "roll_created", "roll": roll, "logEntry": roll_log_entry_to_dict(log_entry)})
    return {"roomId": room.id, "roll": roll, "logEntry": roll_log_entry_to_dict(log_entry)}


def roll_resolves_immediately(roll: RollPayload) -> bool:
    return roll.resolution == RollResolutionMode.HEAL_SELF


def append_roll_log_entry(room: Room, entry: RollLogEntry) -> RollLogEntry:
    room.roll_history.append(entry)
    room.roll_history = room.roll_history[-ROLL_HISTORY_LIMIT:]
    return entry


def set_equipment_slot(room: Room, sheet: CharacterSheet, item_id: str, slot: EquipmentSlot) -> None:
    token_slots = room.equipment_slots.setdefault(sheet.tokenId, {})
    if slot == EquipmentSlot.ARMOR:
        for item in sheet.equipment:
            if item.slot == EquipmentSlot.ARMOR:
                token_slots[item.id] = EquipmentSlot.CARRIED
    elif slot == EquipmentSlot.TWO_HANDS:
        for item in sheet.equipment:
            if item.slot in {EquipmentSlot.MAIN_HAND, EquipmentSlot.OFF_HAND, EquipmentSlot.TWO_HANDS}:
                token_slots[item.id] = EquipmentSlot.CARRIED
    elif slot in {EquipmentSlot.MAIN_HAND, EquipmentSlot.OFF_HAND}:
        for item in sheet.equipment:
            if item.slot in {slot, EquipmentSlot.TWO_HANDS}:
                token_slots[item.id] = EquipmentSlot.CARRIED
    token_slots[item_id] = slot


def valid_equipment_slots(item) -> set[EquipmentSlot]:
    from dnd_board.character_sheet import EquipmentType

    if item.itemType == EquipmentType.ARMOR:
        return {EquipmentSlot.CARRIED, EquipmentSlot.ARMOR}
    if item.itemType == EquipmentType.SHIELD:
        return {EquipmentSlot.CARRIED, EquipmentSlot.MAIN_HAND, EquipmentSlot.OFF_HAND}
    if item.itemType == EquipmentType.WEAPON:
        return {EquipmentSlot.CARRIED, EquipmentSlot.MAIN_HAND, EquipmentSlot.OFF_HAND, EquipmentSlot.TWO_HANDS}
    return {EquipmentSlot.CARRIED}


def parse_rest_type(rest: str) -> RestType | None:
    normalized = sanitize_asset_id(rest)
    if normalized in {"short", "short-rest", "shortrest"}:
        return RestType.SHORT_REST
    if normalized in {"long", "long-rest", "longrest"}:
        return RestType.LONG_REST
    return None


def reset_sheet_resources(room: Room, sheet: CharacterSheet, rest_type: RestType) -> None:
    refreshed_resources = {
        resource.id: resource.maxUses
        for resource in sheet.resources
        if resource_resets_on_rest(resource.reset, rest_type)
    }
    if not refreshed_resources:
        return
    room.resource_uses.setdefault(sheet.tokenId, {}).update(refreshed_resources)


def resource_resets_on_rest(resource_reset: RestType, rest_type: RestType) -> bool:
    if resource_reset == RestType.NONE:
        return False
    if rest_type == RestType.LONG_REST:
        return resource_reset in {RestType.SHORT_REST, RestType.LONG_REST}
    return resource_reset == RestType.SHORT_REST


def reset_sheet_conditions(room: Room, sheet: CharacterSheet, rest_type: RestType) -> None:
    durations = room.condition_durations.get(sheet.tokenId, {})
    expired = {condition for condition, duration in durations.items() if condition_clears_on_rest(duration, rest_type)}
    if not expired:
        return

    next_conditions = [condition for condition in sheet.conditions if condition not in expired]
    room.condition_overrides[sheet.tokenId] = next_conditions
    for condition in expired:
        durations.pop(condition, None)
    update_party_member_config(room.id, sheet.id, lambda member: set_member_conditions(member, next_conditions))


def condition_clears_on_rest(condition_duration: ConditionDuration, rest_type: RestType) -> bool:
    if condition_duration == ConditionDuration.UNTIL_SHORT_REST:
        return rest_type in {RestType.SHORT_REST, RestType.LONG_REST}
    if condition_duration == ConditionDuration.UNTIL_LONG_REST:
        return rest_type == RestType.LONG_REST
    return False


def reset_sheet_temporary_hit_points(room: Room, sheet: CharacterSheet, rest_type: RestType) -> None:
    if rest_type == RestType.LONG_REST:
        room.temporary_hit_points.pop(sheet.tokenId, None)


def spend_resource_use(room: Room, sheet: CharacterSheet, resource_id: str, payload: RollPayload) -> None:
    resource = next((candidate for candidate in sheet.resources if candidate.id == resource_id), None)
    if resource is None:
        return

    remaining_uses = clamp_int(resource.currentUses - 1, 0, resource.maxUses)
    room.resource_uses.setdefault(sheet.tokenId, {})[resource.id] = remaining_uses
    payload.resourceSpent = RollResourceSpend(
        resourceId=resource.id,
        resourceName=resource.name,
        remainingUses=remaining_uses,
        maxUses=resource.maxUses,
    )


def roll_queue_key(roll: RollPayload) -> tuple[str, str, str, str]:
    return (roll.tokenId, enum_key(roll.source.section), roll.source.sourceId, roll.source.actionId)


def remove_pending_rolls_for_token(room: Room, token_id: str) -> None:
    for key in [key for key, roll in room.pending_rolls.items() if roll.tokenId == token_id]:
        room.pending_rolls.pop(key, None)


def resolve_roll_against_target(room: Room, roll: RollPayload, target: CharacterSheet) -> RollResolution:
    resolution = resolve_dnd_roll_against_target(roll, target)
    source = source_sheet_for_roll(room, roll)
    target_save_outcomes = resolve_target_save_effects(roll, target)
    source_check_outcomes = resolve_source_check_condition_effects(roll, source, target)
    response_rolls = [response_roll for _outcome, _condition, response_roll in target_save_outcomes]
    response_rolls.extend(response_roll for _outcome, _condition, response_rolls_for_effect in source_check_outcomes for response_roll in response_rolls_for_effect)
    if target_save_outcomes:
        resolution.targetConditions = apply_response_roll_conditions(
            resolution.targetConditions,
            [(outcome, condition) for outcome, condition, _response_roll in target_save_outcomes],
        )
        resolution.outcome = f"{resolution.outcome}; {'; '.join(outcome for outcome, _condition, _response_roll in target_save_outcomes)}"
    if source_check_outcomes:
        resolution.targetConditions = apply_response_roll_conditions(
            resolution.targetConditions,
            [(outcome, condition) for outcome, condition, _response_rolls in source_check_outcomes],
        )
        resolution.outcome = f"{resolution.outcome}; {'; '.join(outcome for outcome, _condition, _response_rolls in source_check_outcomes)}"
    if response_rolls:
        for response_roll in response_rolls:
            room.pending_rolls[roll_queue_key(response_roll)] = response_roll
        resolution.responseRolls = response_rolls
    if roll.resolution in {RollResolutionMode.APPLY_DAMAGE, RollResolutionMode.HEAL_SELF, RollResolutionMode.APPLY_TEMPORARY_HIT_POINTS}:
        room.hit_points[target.tokenId] = resolution.targetHp.current
        room.temporary_hit_points[target.tokenId] = resolution.targetHp.temporary
    apply_resolved_conditions(room, target.id, resolution.targetConditions, roll)
    return resolution


def resolve_target_save_effects(roll: RollPayload, target: CharacterSheet) -> list[tuple[str, ConditionType | None, RollPayload]]:
    outcomes: list[tuple[str, ConditionType | None, RollPayload]] = []
    for effect in roll.conditionEffects or []:
        if effect.mode != ConditionApplicationMode.TARGET_SAVE or effect.savingThrow is None or effect.saveDc is None:
            continue
        response_roll = response_ability_roll(
            sheet=target,
            ability=effect.savingThrow,
            action_id="save",
            label=f"{enum_label(effect.savingThrow)} Save",
            source_label=roll.label,
            modifier=save_modifier(target, effect.savingThrow),
        )
        if response_roll.total < effect.saveDc:
            if effect.condition is None:
                outcomes.append((f"{target.name} fails DC {effect.saveDc} {enum_label(effect.savingThrow)} save", None, response_roll))
            else:
                outcomes.append(
                    (
                        f"{target.name} fails DC {effect.saveDc} {enum_label(effect.savingThrow)} save and gains {enum_label(effect.condition)}",
                        effect.condition,
                        response_roll,
                    )
                )
        else:
            effect_label = enum_label(effect.condition) if effect.condition is not None else "effect"
            outcomes.append((f"{target.name} passes DC {effect.saveDc} {enum_label(effect.savingThrow)} save against {effect_label}", None, response_roll))
    return outcomes


def source_sheet_for_roll(room: Room, roll: RollPayload) -> CharacterSheet | None:
    token = room.tokens.get(roll.tokenId)
    if token is None:
        return None
    return token_to_sheet(token, room.id, room.hit_points.get(token.id))


def resolve_source_check_condition_effects(
    roll: RollPayload,
    source: CharacterSheet | None,
    target: CharacterSheet,
) -> list[tuple[str, ConditionType | None, list[RollPayload]]]:
    if source is None:
        return []
    outcomes: list[tuple[str, ConditionType | None, list[RollPayload]]] = []
    for effect in roll.conditionEffects or []:
        if effect.mode != ConditionApplicationMode.SOURCE_CHECK or effect.sourceCheck is None or not effect.contestChecks:
            continue
        source_check = condition_source_check(source, effect)
        target_check = condition_target_contest_check(target, effect)
        source_response_roll = response_ability_roll(
            sheet=source,
            ability=effect.sourceCheck,
            action_id="check",
            label=source_check[0],
            source_label=roll.label,
            modifier=source_check[1] + max(0, roll.total),
        )
        target_response_roll = response_ability_roll(
            sheet=target,
            ability=target_check[2],
            action_id="check",
            label=target_check[0],
            source_label=roll.label,
            modifier=target_check[1],
        )
        response_rolls = [source_response_roll, target_response_roll]
        if source_response_roll.total > target_response_roll.total:
            outcomes.append(
                (
                    f"{source.name} wins {source_check[0]} {source_response_roll.total} vs {target.name} {target_check[0]} {target_response_roll.total}; {target.name} gains {enum_label(effect.condition)}",
                    effect.condition,
                    response_rolls,
                )
            )
        else:
            outcomes.append(
                (
                    f"{source.name} fails {source_check[0]} {source_response_roll.total} vs {target.name} {target_check[0]} {target_response_roll.total}; no {enum_label(effect.condition)}",
                    None,
                    response_rolls,
                )
            )
    return outcomes


def condition_source_check(source: CharacterSheet, effect) -> tuple[str, int]:
    if effect.condition == ConditionType.GRAPPLED and effect.sourceCheck == AbilityType.STRENGTH:
        return (f"{enum_label(AbilityType.STRENGTH)} ({enum_label(SkillType.ATHLETICS)})", skill_modifier(source, enum_key(SkillType.ATHLETICS), AbilityType.STRENGTH))
    return (f"{enum_label(effect.sourceCheck)} check", ability_check_modifier(source, effect.sourceCheck))


def condition_target_contest_check(target: CharacterSheet, effect) -> tuple[str, int, AbilityType]:
    options = [condition_target_check(target, effect.condition, ability) for ability in effect.contestChecks or []]
    return max(options, key=lambda option: option[1])


def condition_target_check(target: CharacterSheet, condition: ConditionType | None, ability: AbilityType) -> tuple[str, int, AbilityType]:
    if condition == ConditionType.GRAPPLED and ability == AbilityType.STRENGTH:
        return (f"{enum_label(AbilityType.STRENGTH)} ({enum_label(SkillType.ATHLETICS)})", skill_modifier(target, enum_key(SkillType.ATHLETICS), AbilityType.STRENGTH), ability)
    if condition == ConditionType.GRAPPLED and ability == AbilityType.DEXTERITY:
        return (f"{enum_label(AbilityType.DEXTERITY)} ({enum_label(SkillType.ACROBATICS)})", skill_modifier(target, enum_key(SkillType.ACROBATICS), AbilityType.DEXTERITY), ability)
    return (f"{enum_label(ability)} check", ability_check_modifier(target, ability), ability)


def response_ability_roll(
    *,
    sheet: CharacterSheet,
    ability: AbilityType,
    action_id: str,
    label: str,
    source_label: str,
    modifier: int,
) -> RollPayload:
    die_roll = random.randint(1, 20)
    created_at = time_ns()
    return RollPayload(
        id=f"roll-{created_at}",
        sheetId=sheet.id,
        tokenId=sheet.tokenId,
        roller=sheet.owner,
        source=RollSource(section=SheetSectionType.ABILITY_SCORES, sourceId=enum_key(ability), actionId=action_id),
        sourceLabel=source_label,
        resolution=RollResolutionMode.NONE,
        label=label,
        iconUrl=None,
        dice=[die_roll],
        diceType=DiceType.D20,
        die=enum_key(DiceType.D20),
        modifier=modifier,
        modifierBreakdown=[RollModifierBreakdown(source=label, value=modifier)] if modifier else [],
        total=die_roll + modifier,
        createdAt=created_at,
    )


def skill_modifier(sheet: CharacterSheet, skill_name: str, fallback_ability: AbilityType) -> int:
    skill = next((candidate for candidate in sheet.skills if candidate.name == skill_name), None)
    return skill.modifier if skill is not None else ability_check_modifier(sheet, fallback_ability)


def ability_check_modifier(sheet: CharacterSheet, ability: AbilityType) -> int:
    return ability_modifier(getattr(sheet.abilityScores, enum_key(ability)))


def save_modifier(sheet: CharacterSheet, ability: AbilityType) -> int:
    saving_throw = next((save for save in sheet.savingThrows if save.ability == ability), None)
    modifier = ability_check_modifier(sheet, ability)
    if saving_throw is not None and saving_throw.proficient:
        modifier += sheet.proficiencyBonus
    return modifier


def apply_response_roll_conditions(
    current_conditions: list[ConditionType],
    outcomes: list[tuple[str, ConditionType | None]],
) -> list[ConditionType]:
    next_conditions = list(current_conditions)
    for _outcome, condition in outcomes:
        if condition is not None and condition not in next_conditions:
            next_conditions.append(condition)
    return next_conditions


def apply_resolved_conditions(room: Room, sheet_id: str, conditions: list[ConditionType], roll: RollPayload) -> None:
    room.condition_overrides[sheet_id] = list(conditions)
    active_conditions = set(conditions)
    durations = room.condition_durations.setdefault(sheet_id, {})
    for condition in list(durations):
        if condition not in active_conditions:
            durations.pop(condition, None)
    for effect in roll.conditionEffects or []:
        if effect.condition in active_conditions:
            durations[effect.condition] = effect.duration
    update_party_member_config(room.id, sheet_id, lambda updated: set_member_conditions(updated, conditions))


def party_member_by_id(member_id: str, campaign_id: str | None = None) -> PartyMember | None:
    for member in load_party_members(campaign_id):
        if member.id == member_id:
            return member
    return None


async def broadcast(room: Room, message: dict[str, Any]) -> None:
    disconnected: list[Player] = []
    for player in room.players.values():
        try:
            await send(player, message)
        except (RuntimeError, WebSocketDisconnect):
            disconnected.append(player)

    for player in disconnected:
        await leave_room(player)


async def send(player: Player, message: dict[str, Any]) -> None:
    if player.websocket is None:
        return
    await player.websocket.send_text(json.dumps(message))


def token_to_dict(token: Token) -> dict[str, Any]:
    data = asdict(token)
    data["kind"] = enum_key(token.kind)
    if data["lockedBy"] is None:
        data.pop("lockedBy")
    if data["avatarUrl"] is None:
        data.pop("avatarUrl")
    return data


def can_control_token(player: Player, token: Token) -> bool:
    return is_dm(player) or player.player_key == token.owner


def is_dm(player: Player) -> bool:
    return player.player_key == "dm"


def sanitize_room_id(room_id: str) -> str:
    sanitized = "".join(character for character in room_id.strip().lower() if character.isalnum() or character == "-")
    return sanitized[:40] or "table"


def normalize_player_key(player_key: str, campaign_id: str | None = None) -> str:
    normalized = player_key.strip().lower()
    if normalize_party_member_id(normalized, "") == normalized:
        return normalized
    party_members = load_party_members(campaign_id)
    valid_player_keys = {member.owner for member in party_members}
    if normalized in valid_player_keys or normalized == "dm":
        return normalized
    for member in party_members:
        if sanitize_asset_id(member.name) == sanitize_asset_id(normalized):
            return member.owner
    return "player-1"


def save_room_to_disk(room: Room) -> None:
    path = save_path(room.id)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "roomId": room.id,
        "tokens": [token_to_dict(token) for token in room.tokens.values()],
        "fog": fog_to_dict(room.fog),
        "boardId": room.board_id,
        "resources": room.resource_uses,
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


async def load_room_from_disk(room: Room, player: Player) -> bool:
    if not is_dm(player):
        return False

    saved_board_id = load_saved_board_id(room.id)
    saved_board = get_board(saved_board_id, room.id) or fallback_board()
    saved_tokens = load_saved_tokens(room.id, saved_board)
    if saved_tokens is None:
        return False

    tokens = merge_saved_tokens_with_party(saved_tokens, room.id)
    room.tokens = {token.id: token for token in tokens}
    room.fog = load_saved_fog(room.id, saved_board)
    room.board_id = saved_board_id
    room.next_token_number = next_dynamic_token_number(tokens)
    room.pending_rolls = {}
    room.roll_history = []
    room.hit_points = {}
    room.temporary_hit_points = {}
    room.condition_overrides = {}
    room.condition_durations = {}
    room.resource_uses = load_saved_resource_uses(room.id)
    room.equipment_slots = {}
    await broadcast_room_state(room)
    return True


def load_saved_tokens(room_id: str, board: Board | None = None) -> list[Token] | None:
    path = existing_save_path(room_id)
    if not path.exists():
        return None

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        active_board = board or fallback_board()
        return [token_from_dict(token_data, active_board, room_id) for token_data in data.get("tokens", [])]
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return None


def load_saved_fog(room_id: str, board: Board | None = None) -> FogState:
    path = existing_save_path(room_id)
    if not path.exists():
        return default_fog()

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return fog_from_dict(data.get("fog", {}), board or fallback_board())
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return default_fog()


def load_saved_board_id(room_id: str) -> str:
    path = existing_save_path(room_id)
    if not path.exists():
        return default_board_id(room_id)

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        board_id = str(data.get("boardId", default_board_id(room_id)))
        return board_id if get_board(board_id, room_id) is not None else default_board_id(room_id)
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return default_board_id(room_id)


def load_saved_resource_uses(room_id: str) -> dict[str, dict[str, int]]:
    path = existing_save_path(room_id)
    if not path.exists():
        return {}

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    raw_resources = data.get("resources")
    if not isinstance(raw_resources, dict):
        return {}

    resources: dict[str, dict[str, int]] = {}
    for raw_token_id, raw_token_resources in raw_resources.items():
        if not isinstance(raw_token_resources, dict):
            continue
        token_id = sanitize_asset_id(str(raw_token_id))
        token_resources: dict[str, int] = {}
        for raw_resource_id, raw_current_uses in raw_token_resources.items():
            try:
                token_resources[sanitize_asset_id(str(raw_resource_id))] = max(0, int(raw_current_uses))
            except (TypeError, ValueError):
                continue
        if token_id and token_resources:
            resources[token_id] = token_resources
    return resources


def token_from_dict(data: dict[str, Any], board: Board | None = None, campaign_id: str | None = None) -> Token:
    active_board = board or fallback_board()

    return Token(
        id=str(data["id"]),
        kind=token_kind_from_value(data.get("kind")),
        name=str(data["name"]),
        owner=normalize_owner(str(data["owner"]), campaign_id),
        color=DEFAULT_TOKEN_COLOR,
        x=clamp(to_float(data["x"]), 0, active_board.width),
        y=clamp(to_float(data["y"]), 0, active_board.height),
        radius=clamp(to_float(data["radius"]), MIN_TOKEN_RADIUS, MAX_TOKEN_RADIUS),
        inScene=bool(data["inScene"]),
        avatarUrl=str(data["avatarUrl"]) if data.get("avatarUrl") else None,
        lockedBy=None,
    )


def token_kind_from_value(value: Any) -> TokenKind:
    normalized = str(value or "").strip().replace("-", "_").replace(" ", "_").upper()
    if normalized in {TokenKind.ASSET.name, enum_key(TokenKind.ASSET).upper()}:
        return TokenKind.ASSET
    return TokenKind.CHARACTER


def default_fog() -> FogState:
    return FogState(hideMode=False, brushSize=120, revealedAreas=[])


def fallback_board() -> Board:
    return blank_board()


def blank_board() -> Board:
    return Board(id="-", name="-", url=None, width=BOARD_WIDTH, height=BOARD_HEIGHT)


def default_board_id(campaign_id: str | None = None) -> str:
    boards = list_boards(campaign_id)
    return boards[0].id if boards else blank_board().id


def list_boards(campaign_id: str | None = None) -> list[Board]:
    boards: list[Board] = [blank_board()]
    for path in list_image_files(campaign_asset_dir("boards", campaign_id), BOARD_DIR):
        board_id = sanitize_asset_id(path.stem)
        if not board_id:
            continue
        dimensions = image_dimensions(path)
        if dimensions is None:
            continue
        width, height = dimensions
        boards.append(Board(id=board_id, name=humanize_asset_name(path.stem), url=campaign_file_url("boards", path, campaign_id), width=width, height=height))
    return boards


def load_party_members(campaign_id: str | None = None) -> list[PartyMember]:
    configured = load_party_members_from_manifest(campaign_asset_dir("party", campaign_id) / "party.json", campaign_id)
    if configured:
        return configured[:MAX_PLAYERS]

    members: list[PartyMember] = []
    for index, path in enumerate(list_image_files(campaign_asset_dir("party", campaign_id))[:MAX_PLAYERS], start=1):
        player_id = f"player-{index}"
        members.append(
            PartyMember(
                id=player_id,
                name=humanize_asset_name(path.stem),
                owner=player_id,
                avatarUrl=campaign_file_url("party", path, campaign_id),
                abilityScores=None,
                maxHp=None,
            )
        )
    return members or default_party_members()


def update_party_member_config(campaign_id: str, member_id: str, update: Any) -> PartyMemberConfig | None:
    path = campaign_asset_dir("party", campaign_id) / "party.json"
    manifest = load_party_manifest_config(path)
    if manifest is None:
        return None

    target = next((member for member in manifest.members if normalize_party_member_id(member.id, "") == member_id), None)
    if target is None:
        return None

    update(target)
    path.write_text(json.dumps(typed_json_from_value(manifest), indent=2, sort_keys=False), encoding="utf-8")
    return target


def save_party_member_config(campaign_id: str, member: PartyMemberConfig) -> PartyMemberConfig:
    path = writable_party_manifest_path(campaign_id)
    manifest = load_party_manifest_config(path) or PartyManifest(members=[])
    target = next((candidate for candidate in manifest.members if normalize_party_member_id(candidate.id, "") == member.id), None)
    if target is None:
        manifest.members.append(member)
    else:
        index = manifest.members.index(target)
        manifest.members[index] = member
    path.write_text(json.dumps(typed_json_from_value(manifest), indent=2, sort_keys=False), encoding="utf-8")
    return member


def writable_party_manifest_path(campaign_id: str) -> Path:
    campaign_path = CAMPAIGN_DIR / sanitize_asset_id(campaign_id)
    party_path = campaign_path / "party"
    party_path.mkdir(parents=True, exist_ok=True)
    campaign_config = campaign_path / "campaign.json"
    if not campaign_config.exists():
        campaign_config.write_text(json.dumps({"id": campaign_path.name, "name": humanize_asset_name(campaign_path.name)}, indent=2), encoding="utf-8")
    return party_path / "party.json"


def refresh_party_token(room: Room, member: PartyMemberConfig) -> None:
    token = room.tokens.get(member.id)
    if token is None:
        token = party_member_to_token(
            PartyMember(
                id=member.id,
                name=member.name,
                owner=member.id,
                avatarUrl=None,
                abilityScores=member.abilityScores,
                maxHp=member.maxHp,
                sheet=member.sheet,
            ),
            len([candidate for candidate in room.tokens.values() if candidate.kind == TokenKind.CHARACTER]),
        )
        room.tokens[member.id] = token
    token.name = member.name
    token.owner = member.id


def load_party_manifest_config(path: Path) -> PartyManifest | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return party_manifest_from_dict(data)


def member_sheet_classes(member: PartyMemberConfig) -> list[CharacterClassLevel]:
    if member.sheet is None:
        member.sheet = PartyMemberSheet(classes=[CharacterClassLevel(name=ClassType.FIGHTER, level=1)])
    if not member.sheet.classes:
        member.sheet.classes = [CharacterClassLevel(name=ClassType.FIGHTER, level=1)]
    return prune_progression_choices(member.sheet.classes)


def set_member_class_levels(member: PartyMemberConfig, classes: list[CharacterClassLevel]) -> None:
    if member.sheet is None:
        member.sheet = PartyMemberSheet()
    member.sheet.classes = prune_progression_choices(classes)
    prune_member_hit_point_increases(member)
    prune_member_ability_score_improvements(member)
    prune_member_eldritch_knight_spells(member)
    prune_member_arcane_trickster_spells(member)


def set_member_condition(member: PartyMemberConfig, condition: ConditionType, active: bool) -> None:
    if member.sheet is None:
        member.sheet = PartyMemberSheet()
    member.sheet.conditions = updated_conditions(member.sheet.conditions or [], condition, active) or None


def updated_conditions(conditions: list[ConditionType], condition: ConditionType, active: bool) -> list[ConditionType]:
    if active and condition not in conditions:
        return [*conditions, condition]
    if not active:
        return [candidate for candidate in conditions if candidate != condition]
    return list(conditions)


def set_member_conditions(member: PartyMemberConfig, conditions: list[ConditionType]) -> None:
    if member.sheet is None:
        member.sheet = PartyMemberSheet()
    member.sheet.conditions = conditions or None


def pending_choice_summary(sheet: CharacterSheet) -> str:
    return ", ".join(choice.label for choice in sheet.pendingChoices)


def apply_member_hit_point_choice(member: PartyMemberConfig, choice: str) -> None:
    classes = member_sheet_classes(member)
    expected_increases = max(0, total_member_level(member) - 1)
    if expected_increases <= 0:
        return
    if member.sheet is None:
        member.sheet = PartyMemberSheet(classes=classes)
    increases = member.sheet.hitPointIncreases or []
    if len(increases) >= expected_increases:
        return
    bump = class_hit_point_bump(member, classes[0].name if classes else ClassType.FIGHTER, choice)
    if member.maxHp is None:
        member.maxHp = max(1, class_level_one_hit_points(classes[0].name if classes else ClassType.FIGHTER) + member_constitution_modifier(member))
    member.maxHp += bump
    member.sheet.hitPointIncreases = [*increases, bump]
    prune_member_hit_point_increases(member)


def apply_member_eldritch_knight_spells(member: PartyMemberConfig, values: list[str]) -> None:
    from dnd_board.rules.classes.fighter.archetypes import eldritch_knight_catalog_spell, is_eldritch_knight_spell_selection_valid
    from dnd_board.rules.classes.fighter.base import FighterSubclassType

    fighter = next((character_class for character_class in member_sheet_classes(member) if character_class.name == ClassType.FIGHTER), None)
    if fighter is None or fighter.subclass != FighterSubclassType.ELDRITCH_KNIGHT or fighter.level < 3:
        raise HTTPException(status_code=400, detail="Eldritch Knight spellcasting is not available")

    selected_ids = unique_clean_values(values)
    spells = []
    for spell_id in selected_ids:
        spell = eldritch_knight_catalog_spell(spell_id)
        if spell is None:
            raise HTTPException(status_code=400, detail="Invalid Eldritch Knight spell")
        spells.append(spell)

    if not is_eldritch_knight_spell_selection_valid(fighter.level, spells):
        raise HTTPException(status_code=400, detail="Choose legal Eldritch Knight cantrips and wizard spells")

    if member.sheet is None:
        member.sheet = PartyMemberSheet(classes=[fighter])
    member.sheet.spells = spells


def apply_member_arcane_trickster_spells(member: PartyMemberConfig, values: list[str]) -> None:
    from dnd_board.rules.classes.rogue.archetypes import arcane_trickster_catalog_spell, is_arcane_trickster_spell_selection_valid, normalized_arcane_trickster_spell
    from dnd_board.rules.classes.rogue.base import RogueSubclassType

    rogue = next((character_class for character_class in member_sheet_classes(member) if character_class.name == ClassType.ROGUE), None)
    if rogue is None or rogue.subclass != RogueSubclassType.ARCANE_TRICKSTER or rogue.level < 3:
        raise HTTPException(status_code=400, detail="Arcane Trickster spellcasting is not available")

    selected_ids = unique_clean_values(values)
    spells = []
    for spell_id in selected_ids:
        spell = arcane_trickster_catalog_spell(spell_id)
        if spell is None:
            raise HTTPException(status_code=400, detail="Invalid Arcane Trickster spell")
        spells.append(normalized_arcane_trickster_spell(spell))

    if not is_arcane_trickster_spell_selection_valid(rogue.level, spells):
        raise HTTPException(status_code=400, detail="Choose legal Arcane Trickster cantrips and wizard spells")

    if member.sheet is None:
        member.sheet = PartyMemberSheet(classes=[rogue])
    other_spells = [
        spell
        for spell in member.sheet.spells or []
        if spell.source != SpellSource.ARCANE_TRICKSTER
    ]
    member.sheet.spells = [*other_spells, *spells]


def class_hit_point_bump(member: PartyMemberConfig, class_name: ClassType, choice: str) -> int:
    constitution_modifier = member_constitution_modifier(member)
    hit_die = class_hit_die(class_name)
    if normalize_choice_id(choice) == "roll":
        return max(1, random.randint(1, hit_die) + constitution_modifier)
    return max(1, (hit_die // 2 + 1) + constitution_modifier)


def class_level_one_hit_points(class_name: ClassType) -> int:
    return class_hit_die(class_name)


def member_constitution_modifier(member: PartyMemberConfig) -> int:
    constitution = member.abilityScores.constitution if member.abilityScores else 10
    return ability_modifier(constitution)


def prune_member_hit_point_increases(member: PartyMemberConfig) -> None:
    if member.sheet is None or not member.sheet.hitPointIncreases:
        return
    expected_increases = max(0, total_member_level(member) - 1)
    increases = member.sheet.hitPointIncreases
    if len(increases) <= expected_increases:
        return
    removed = increases[expected_increases:]
    member.sheet.hitPointIncreases = increases[:expected_increases] or None
    if member.maxHp is not None:
        member.maxHp = max(1, member.maxHp - sum(removed))


def apply_member_ability_score_improvement(member: PartyMemberConfig, values: list[str]) -> None:
    classes = member_sheet_classes(member)
    expected_improvements = expected_member_ability_score_improvements(classes)
    if expected_improvements <= 0:
        return
    if member.sheet is None:
        member.sheet = PartyMemberSheet(classes=classes)
    improvements = member.sheet.abilityScoreImprovements or []
    if len(improvements) >= expected_improvements:
        return

    if is_feat_choice(values):
        apply_member_feat_improvement(member, improvements, values[0])
        return

    requested_changes = ability_score_improvement_changes(values)
    ensure_member_ability_scores(member)
    applied_changes: dict[AbilityType, int] = {}
    for ability, delta in requested_changes.items():
        ability_key = enum_key(ability)
        current_score = getattr(member.abilityScores, ability_key)
        next_score = min(20, current_score + delta)
        applied_delta = next_score - current_score
        if applied_delta > 0:
            setattr(member.abilityScores, ability_key, next_score)
            if ability == AbilityType.CONSTITUTION:
                apply_constitution_hp_delta(member, current_score, next_score)
            applied_changes[ability] = applied_delta

    if not applied_changes:
        raise HTTPException(status_code=400, detail="Ability scores cannot be increased above 20")
    member.sheet.abilityScoreImprovements = [*improvements, serialize_ability_score_improvement(applied_changes)]


def is_feat_choice(values: list[str]) -> bool:
    clean_values = [value for value in values if value.strip()]
    return len(clean_values) == 1 and normalize_choice_id(clean_values[0]).startswith("feat")


def apply_member_feat_improvement(member: PartyMemberConfig, improvements: list[str], value: str) -> None:
    from dnd_board.rules.feats import general_feat_feature, parse_general_feat, selected_general_feat_keys

    feat_key = value.split(":", 1)[1] if ":" in value else value
    feat_type = parse_general_feat(feat_key)
    if feat_type is None:
        raise HTTPException(status_code=400, detail="Invalid feat")
    feature = general_feat_feature(feat_key)
    if feature is None:
        raise HTTPException(status_code=400, detail="Invalid feat")
    existing_feats = member.sheet.feats or []
    if feature.id in selected_general_feat_keys(existing_feats):
        raise HTTPException(status_code=400, detail="Feat is already selected")
    member.sheet.feats = [*existing_feats, feature]
    member.sheet.abilityScoreImprovements = [*improvements, serialize_feat_improvement(feature.id)]


def ability_score_improvement_changes(values: list[str]) -> dict[AbilityType, int]:
    clean_values = [value for value in values if value.strip()]
    if len(clean_values) > 2:
        raise HTTPException(status_code=400, detail="Choose one ability twice or two abilities once")

    parsed: list[AbilityType] = []
    for value in clean_values:
        ability = enum_value(AbilityType, value)
        if ability is None:
            raise HTTPException(status_code=400, detail="Invalid ability score")
        parsed.append(ability)

    if len(parsed) == 1:
        parsed.append(parsed[0])
    if len(parsed) != 2:
        raise HTTPException(status_code=400, detail="Choose one ability twice or two abilities once")

    changes: dict[AbilityType, int] = {}
    for ability in parsed:
        changes[ability] = changes.get(ability, 0) + 1
    return changes


def ensure_member_ability_scores(member: PartyMemberConfig) -> None:
    if member.abilityScores is None:
        member.abilityScores = AbilityScores(strength=10, dexterity=10, constitution=10, intelligence=10, wisdom=10, charisma=10)


def serialize_ability_score_improvement(changes: dict[AbilityType, int]) -> str:
    return ",".join(f"{enum_key(ability)}:{delta}" for ability, delta in changes.items())


def serialize_feat_improvement(feat_key: str) -> str:
    return f"feat:{feat_key}"


def parse_feat_improvement(value: str) -> str | None:
    if not value.startswith("feat:"):
        return None
    return value.split(":", 1)[1]


def parse_ability_score_improvement(value: str) -> dict[AbilityType, int]:
    changes: dict[AbilityType, int] = {}
    for part in value.split(","):
        ability_key, separator, delta_text = part.partition(":")
        if not separator:
            continue
        ability = enum_value(AbilityType, ability_key)
        if ability is None:
            continue
        try:
            delta = int(delta_text)
        except ValueError:
            continue
        if delta > 0:
            changes[ability] = changes.get(ability, 0) + delta
    return changes


def prune_member_ability_score_improvements(member: PartyMemberConfig) -> None:
    if member.sheet is None or not member.sheet.abilityScoreImprovements:
        return
    expected_improvements = expected_member_ability_score_improvements(member_sheet_classes(member))
    improvements = member.sheet.abilityScoreImprovements
    if len(improvements) <= expected_improvements:
        return

    removed = improvements[expected_improvements:]
    member.sheet.abilityScoreImprovements = improvements[:expected_improvements] or None
    ensure_member_ability_scores(member)
    for improvement in reversed(removed):
        feat_key = parse_feat_improvement(improvement)
        if feat_key is not None:
            member.sheet.feats = [feat for feat in member.sheet.feats or [] if feat.id != feat_key] or None
            continue
        for ability, delta in parse_ability_score_improvement(improvement).items():
            ability_key = enum_key(ability)
            current_score = getattr(member.abilityScores, ability_key)
            next_score = max(1, current_score - delta)
            setattr(member.abilityScores, ability_key, next_score)
            if ability == AbilityType.CONSTITUTION:
                apply_constitution_hp_delta(member, current_score, next_score)


def expected_member_ability_score_improvements(classes: list[CharacterClassLevel]) -> int:
    fighter = next((character_class for character_class in classes if character_class.name == ClassType.FIGHTER), None)
    rogue = next((character_class for character_class in classes if character_class.name == ClassType.ROGUE), None)
    return (fighter_asi_levels_up_to(fighter.level) if fighter is not None else 0) + (rogue_asi_levels_up_to(rogue.level) if rogue is not None else 0)


def apply_constitution_hp_delta(member: PartyMemberConfig, previous_score: int, next_score: int) -> None:
    if member.maxHp is None:
        return
    modifier_delta = ability_modifier(next_score) - ability_modifier(previous_score)
    if modifier_delta != 0:
        member.maxHp = max(1, member.maxHp + total_member_level(member) * modifier_delta)


def prune_member_eldritch_knight_spells(member: PartyMemberConfig) -> None:
    from dnd_board.rules.classes.fighter.archetypes import eldritch_knight_catalog_spell, pruned_eldritch_knight_spells
    from dnd_board.rules.classes.fighter.base import FighterSubclassType

    if member.sheet is None or not member.sheet.spells:
        return

    fighter = next((character_class for character_class in member_sheet_classes(member) if character_class.name == ClassType.FIGHTER), None)
    if fighter is None or fighter.subclass != FighterSubclassType.ELDRITCH_KNIGHT or fighter.level < 3:
        member.sheet.spells = [spell for spell in member.sheet.spells if eldritch_knight_catalog_spell(spell.id) is None] or None
        return

    eldritch_knight_spells = [spell for spell in member.sheet.spells if eldritch_knight_catalog_spell(spell.id) is not None]
    other_spells = [spell for spell in member.sheet.spells if eldritch_knight_catalog_spell(spell.id) is None]
    member.sheet.spells = [
        *other_spells,
        *pruned_eldritch_knight_spells(fighter.level, eldritch_knight_spells),
    ] or None


def prune_member_arcane_trickster_spells(member: PartyMemberConfig) -> None:
    from dnd_board.rules.classes.rogue.archetypes import arcane_trickster_catalog_spell, pruned_arcane_trickster_spells
    from dnd_board.rules.classes.rogue.base import RogueSubclassType

    if member.sheet is None or not member.sheet.spells:
        return

    rogue = next((character_class for character_class in member_sheet_classes(member) if character_class.name == ClassType.ROGUE), None)
    if rogue is None or rogue.subclass != RogueSubclassType.ARCANE_TRICKSTER or rogue.level < 3:
        member.sheet.spells = [spell for spell in member.sheet.spells if arcane_trickster_catalog_spell(spell.id) is None or spell.source != SpellSource.ARCANE_TRICKSTER] or None
        return

    arcane_trickster_spells = [spell for spell in member.sheet.spells if spell.source == SpellSource.ARCANE_TRICKSTER]
    other_spells = [spell for spell in member.sheet.spells if spell.source != SpellSource.ARCANE_TRICKSTER]
    member.sheet.spells = [
        *other_spells,
        *pruned_arcane_trickster_spells(rogue.level, arcane_trickster_spells),
    ] or None


def unique_clean_values(values: list[str]) -> list[str]:
    cleaned: list[str] = []
    for value in values:
        clean_value = value.strip()
        if clean_value and clean_value not in cleaned:
            cleaned.append(clean_value)
    return cleaned


def total_member_level(member: PartyMemberConfig) -> int:
    return sum(character_class.level for character_class in member_sheet_classes(member))


def normalize_choice_id(value: str) -> str:
    return value.strip().replace("-", "").replace("_", "").lower()


def load_party_members_from_manifest(path: Path, campaign_id: str | None = None) -> list[PartyMember]:
    if not path.is_file():
        return []

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    manifest = party_manifest_from_dict(data)
    if manifest is None:
        return []

    members: list[PartyMember] = []
    seen: set[str] = set()
    for index, raw_member in enumerate(manifest.members, start=1):
        fallback_id = f"player-{index}"
        player_id = normalize_party_member_id(raw_member.id or fallback_id, fallback_id)
        if player_id in seen:
            continue
        seen.add(player_id)

        image_path = party_image_path(raw_member.image or "", campaign_id)
        members.append(
            PartyMember(
                id=player_id,
                name=raw_member.name.strip()[:40] or humanize_asset_name(player_id),
                owner=player_id,
                avatarUrl=campaign_file_url("party", image_path, campaign_id) if image_path is not None else None,
                abilityScores=raw_member.abilityScores,
                maxHp=raw_member.maxHp,
                sheet=raw_member.sheet,
            )
        )
    return members


def normalize_party_member_id(value: str, fallback: str) -> str:
    normalized = sanitize_asset_id(value)
    if normalized.startswith("player-"):
        try:
            number = int(normalized.rsplit("-", 1)[1])
        except (IndexError, ValueError):
            return fallback
        if 1 <= number <= MAX_PLAYERS:
            return f"player-{number}"
    return fallback


def party_image_path(filename: str, campaign_id: str | None = None) -> Path | None:
    if not filename:
        return None
    path = campaign_asset_dir("party", campaign_id) / Path(filename).name
    return path if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".gif"} else None


def default_party_members() -> list[PartyMember]:
    return [
        PartyMember(id=f"player-{index + 1}", name=f"Player {index + 1}", owner=f"player-{index + 1}", avatarUrl=None, abilityScores=None, maxHp=None)
        for index in range(4)
    ]


def get_board(board_id: str, campaign_id: str | None = None) -> Board | None:
    normalized = sanitize_asset_id(board_id)
    for board in list_boards(campaign_id):
        if board.id == normalized:
            return board
    return None


def board_to_dict(board: Board) -> dict[str, Any]:
    data = asdict(board)
    if data["url"] is None:
        data.pop("url")
    return data


def image_dimensions(path: Path) -> tuple[int, int] | None:
    try:
        with Image.open(path) as image:
            return image.size
    except (OSError, UnidentifiedImageError, Image.DecompressionBombError):
        return None


def sanitize_asset_id(asset_id: str) -> str:
    return "".join(character for character in asset_id.strip().lower() if character.isalnum() or character == "-")[:60]


def humanize_asset_name(asset_name: str) -> str:
    return asset_name.replace("-", " ").replace("_", " ").title()


def list_assets() -> list[Asset]:
    return list_assets_from_dir(TokenKind.ASSET, SHARED_ASSET_DIR)


def list_assets_from_dir(kind: TokenKind, directory: Path) -> list[Asset]:
    assets: list[Asset] = []
    for path in list_image_files(directory):
        asset_id = sanitize_asset_id(path.stem)
        if not asset_id:
            continue
        assets.append(Asset(id=asset_id, kind=kind, name=humanize_asset_name(path.stem), avatarUrl=asset_file_url(path)))
    return assets


def get_asset(asset_kind: str, asset_id: str) -> Asset | None:
    normalized_kind = asset_kind.strip().lower()
    normalized_id = sanitize_asset_id(asset_id)
    for asset in list_assets():
        if enum_key(asset.kind) == normalized_kind and asset.id == normalized_id:
            return asset
    return None


def asset_to_dict(asset: Asset) -> dict[str, Any]:
    data = asdict(asset)
    data["kind"] = enum_key(asset.kind)
    return data


def normalize_owner(owner: str, campaign_id: str | None = None) -> str:
    normalized = owner.strip().lower()
    if normalized == "dm":
        return normalized
    return normalize_player_key(normalized, campaign_id)


def next_dynamic_token_number(tokens: list[Token]) -> int:
    highest = 0
    for token in tokens:
        if token.kind == TokenKind.CHARACTER:
            continue
        try:
            highest = max(highest, int(token.id.rsplit("-", 1)[1]))
        except (IndexError, ValueError):
            continue
    return highest + 1


def active_campaign(campaign_id: str | None = None) -> Campaign:
    requested_id = sanitize_asset_id(campaign_id or DEFAULT_CAMPAIGN_ID)
    campaign = get_campaign(requested_id)
    if campaign is not None:
        return campaign
    default_campaign = get_campaign(DEFAULT_CAMPAIGN_ID)
    return default_campaign or Campaign(id=DEFAULT_CAMPAIGN_ID, name=humanize_asset_name(DEFAULT_CAMPAIGN_ID), path=CAMPAIGN_DIR / DEFAULT_CAMPAIGN_ID)


def get_campaign(campaign_id: str) -> Campaign | None:
    campaign_path = CAMPAIGN_DIR / sanitize_asset_id(campaign_id)
    if not campaign_path.exists() or not campaign_path.is_dir():
        return None
    return Campaign(id=campaign_path.name, name=humanize_asset_name(campaign_path.name), path=campaign_path)


def campaign_asset_dir(directory_name: str, campaign_id: str | None = None) -> Path:
    return active_campaign(campaign_id).path / directory_name


def campaign_save_dir(campaign_id: str | None = None) -> Path:
    return active_campaign(campaign_id).path / "saves"


def save_path(room_id: str) -> Path:
    if SAVE_DIR != LEGACY_SAVE_DIR:
        return SAVE_DIR / f"{room_id}.json"
    return campaign_save_dir(room_id) / f"{room_id}.json"


def existing_save_path(room_id: str) -> Path:
    campaign_path = save_path(room_id)
    if campaign_path.exists():
        return campaign_path
    return LEGACY_SAVE_DIR / f"{room_id}.json"


def list_image_files(*directories: Path) -> list[Path]:
    seen: set[str] = set()
    paths: list[Path] = []
    for directory in directories:
        if not directory.exists():
            continue
        for path in sorted(directory.iterdir()):
            if path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp", ".gif"}:
                continue
            asset_id = sanitize_asset_id(path.stem)
            if not asset_id or asset_id in seen:
                continue
            seen.add(asset_id)
            paths.append(path)
    return paths


def asset_file_url(path: Path) -> str:
    if path.parent == SHARED_ASSET_DIR:
        return f"/shared/assets/{path.name}"
    return f"/shared/assets/{path.name}"


def campaign_file_url(directory_name: str, path: Path, campaign_id: str | None = None) -> str:
    campaign = active_campaign(campaign_id)
    campaign_directory = campaign_asset_dir(directory_name, campaign.id)
    if path.parent == campaign_directory:
        return f"/campaigns/{campaign.id}/{directory_name}/{path.name}"
    if path.parent == BOARD_DIR:
        return f"/boards/{path.name}"
    return f"/campaigns/{campaign.id}/{directory_name}/{path.name}"


def fog_to_dict(fog: FogState) -> dict[str, Any]:
    return {
        "hideMode": fog.hideMode,
        "brushSize": fog.brushSize,
        "revealedAreas": [asdict(area) for area in fog.revealedAreas],
    }


def fog_from_dict(data: dict[str, Any], board: Board | None = None) -> FogState:
    active_board = board or fallback_board()
    return FogState(
        hideMode=bool(data.get("hideMode", False)),
        brushSize=clamp(to_float(data.get("brushSize", 120)), 20, 360),
        revealedAreas=[
            RevealedArea(
                x=clamp(to_float(area.get("x")), 0, active_board.width),
                y=clamp(to_float(area.get("y")), 0, active_board.height),
                radius=clamp(to_float(area.get("radius", 120)), 20, 360),
            )
            for area in data.get("revealedAreas", [])
            if isinstance(area, dict)
        ],
    )


def convert_avatar_to_png(content: bytes) -> bytes:
    try:
        with Image.open(BytesIO(content)) as image:
            image.load()
            image.thumbnail((512, 512))
            converted = image.convert("RGBA")
    except (OSError, UnidentifiedImageError, Image.DecompressionBombError) as error:
        raise HTTPException(status_code=400, detail="Avatar must be a valid image file") from error

    output = BytesIO()
    converted.save(output, format="PNG", optimize=True)
    return output.getvalue()


def to_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0


def clamp(value: float, minimum: float, maximum: float) -> float:
    return min(maximum, max(minimum, value))


def clamp_int(value: int, minimum: int, maximum: int) -> int:
    return min(maximum, max(minimum, value))


dist_dir = Path(__file__).resolve().parent.parent / "dist"
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR, check_dir=False), name="uploads")
app.mount("/shared", StaticFiles(directory=SHARED_DIR, check_dir=False), name="shared")
app.mount("/boards", StaticFiles(directory=BOARD_DIR, check_dir=False), name="boards")
if dist_dir.exists():
    app.mount("/assets", StaticFiles(directory=dist_dir / "assets", check_dir=False), name="assets")

    @app.get("/{path:path}")
    async def serve_client(path: str) -> FileResponse:
        target = dist_dir / path
        if path and target.is_file():
            return FileResponse(target)
        return FileResponse(dist_dir / "index.html")
