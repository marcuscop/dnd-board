from __future__ import annotations

import json
from io import BytesIO
from dataclasses import asdict
from pathlib import Path
from time import time_ns
from typing import Any

from fastapi import Body, FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, UnidentifiedImageError
from pillow_heif import register_heif_opener

from dnd_board.application.room_state import (
    ActiveMaxHitPointIncrease,
    ActiveMaxHitPointReduction,
    Asset,
    Board,
    Campaign,
    DamageDefenseType,
    FogState,
    Player,
    RevealedArea,
    Room,
    Token,
)
from dnd_board.application.character_state_service import (
    CharacterStatePersistence,
    active_concentration_status,
    conditions_for_exhaustion_level,
    reset_character_for_rest,
    remove_active_ongoing_effect,
    set_equipment_slot,
    update_condition_state,
    update_exhaustion_state,
    valid_equipment_slots,
)
from dnd_board.application.action_service import (
    ActionOperations,
    ActionServiceError,
    SpellRollType,
    create_ability_score_action,
    create_ad_hoc_dice_action,
    create_attack_action,
    create_sheet_entry_action,
    create_spell_attack_action,
    create_spell_damage_action,
    create_spell_simple_action,
    create_bound_weapon_spell_action,
    log_roll_note as log_action_note,
)
from dnd_board.application.sheet_projection import project_sheet
from dnd_board.application.persistence import (
    LoadedRoomSave,
    fog_to_dict,
    load_room as read_room_save,
    save_room as write_room_save,
    token_to_dict,
)
from dnd_board.application.resolution_service import (
    ResolutionOperations,
    ResolutionServiceError,
    resolve_pending_roll,
    respond_to_prompt,
)
from dnd_board.application.progression_service import (
    ProgressionOperations,
    ProgressionServiceError,
    apply_progression_selection,
    level_character,
)
from dnd_board.application.campaign_repository import (
    CampaignPaths,
    active_campaign as find_active_campaign,
    campaign_asset_dir as find_campaign_asset_dir,
    campaign_save_dir as find_campaign_save_dir,
    existing_save_path as find_existing_save_path,
    get_campaign as find_campaign,
    humanize_name,
    load_party_manifest,
    normalize_party_member_id as normalize_repository_member_id,
    save_party_member as write_party_member,
    save_path as find_save_path,
    update_party_member as write_updated_party_member,
    writable_party_manifest_path as find_writable_party_manifest_path,
)
from dnd_board.application.board_service import (
    BoardOperations,
    apply_token_radius_from_message as apply_radius_from_message,
    can_control_token as player_can_control_token,
    clear_scene as apply_scene_clear,
    default_token_radius as board_default_token_radius,
    delete_token as apply_token_deletion,
    is_dm as player_is_dm,
    is_redundant_reveal_area as reveal_is_redundant,
    load_asset_token as apply_asset_load,
    lock_token as apply_token_lock,
    max_token_radius as board_max_token_radius,
    move_token as apply_token_move,
    release_token as apply_token_release,
    reveal_fog as apply_fog_reveal,
    set_board as apply_board_selection,
    set_fog_mode as apply_fog_mode,
    set_token_radius as apply_token_radius,
    set_token_scene as apply_token_scene,
)

from dnd_board.character_sheet import (
    AbilityType,
    CharacterSheet,
    ClassType,
    ConditionType,
    DamageType,
    DiceType,
    EquipmentSlot,
    HitPoints,
    PartyMemberConfig,
    PartyMemberSheet,
    PartyMember,
    PartyManifest,
    RollPayload,
    RollLogEntry,
    RollResolutionMode,
    RollResolution,
    ResolutionInterceptorPrompt,
    RestType,
    TokenKind,
    build_character_sheet,
    condition_adjusted_armor_class,
    condition_adjusted_speed_for_exhaustion,
    enum_value,
    enum_key,
    enum_label,
    effective_damage_resistance_list,
    party_manifest_from_dict,
    roll_payload_to_dict,
    roll_log_entry_to_dict,
    resolution_interceptor_prompt_to_dict,
    sanitize_identifier,
)
from dnd_board.character_builder import (
    CharacterBuilderPayloadField,
    SUPPORTED_CLASS_TYPES,
    build_party_member_config,
    character_builder_options,
    character_builder_request_from_payload,
    payload_key,
)
from dnd_board.rules.progression import (
    parse_progression_choice_id,
)
from dnd_board.rules.shared.effects import (
    CollectionOperation,
    DamageDefenseType as RulesDamageDefenseType,
    EffectNodeId,
    OngoingEffectId,
)
from dnd_board.rules.shared.resources import (
    ResourceState,
    adjust_resource,
)

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


app = FastAPI()
rooms: dict[str, Room] = {}
next_connection_id = 1


def resolution_operations() -> ResolutionOperations:
    return ResolutionOperations(
        source_sheet=source_sheet_for_roll,
        all_sheets=all_room_sheets,
        state_persistence=character_state_persistence(),
        action_operations=action_operations(),
        save=save_room_to_disk,
        broadcast=broadcast,
        broadcast_room=broadcast_room_state,
        history_limit=ROLL_HISTORY_LIMIT,
    )


def character_state_persistence() -> CharacterStatePersistence:
    return CharacterStatePersistence(
        save_room=save_room_to_disk,
        load_conditions=sheet_conditions,
        persist_conditions=persist_sheet_conditions,
    )


def action_operations() -> ActionOperations:
    return ActionOperations(
        all_sheets=all_room_sheets,
        state_persistence=character_state_persistence(),
        save=save_room_to_disk,
        broadcast=broadcast,
        broadcast_room=broadcast_room_state,
        history_limit=ROLL_HISTORY_LIMIT,
    )


def progression_operations() -> ProgressionOperations:
    return ProgressionOperations(
        update_member=update_party_member_config,
        state_persistence=character_state_persistence(),
    )


def campaign_paths() -> CampaignPaths:
    return CampaignPaths(
        campaign_dir=CAMPAIGN_DIR,
        legacy_save_dir=LEGACY_SAVE_DIR,
        save_dir=SAVE_DIR,
        default_campaign_id=DEFAULT_CAMPAIGN_ID,
        max_players=MAX_PLAYERS,
    )


def board_operations() -> BoardOperations:
    return BoardOperations(
        broadcast=broadcast,
        broadcast_room=broadcast_room_state,
        send=send,
        get_board=get_board,
        get_asset=get_asset,
        get_room_board=get_room_board,
        board_to_dict=board_to_dict,
        remove_pending_rolls=remove_pending_rolls_for_token,
        state_persistence=character_state_persistence(),
        default_token_color=DEFAULT_TOKEN_COLOR,
        minimum_token_radius=MIN_TOKEN_RADIUS,
        maximum_token_radius=MAX_TOKEN_RADIUS,
        default_token_radius=DEFAULT_TOKEN_RADIUS,
        minimum_reveal_distance=MIN_REVEAL_POINT_DISTANCE,
        reveal_distance_ratio=REVEAL_POINT_DISTANCE_RATIO,
    )


async def action_service_response(operation: Any) -> dict[str, Any]:
    try:
        return await operation
    except ActionServiceError as error:
        raise HTTPException(status_code=error.status_code, detail=error.detail) from error


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
    sheet = get_visible_sheet(room, player, sanitize_identifier(sheet_id))
    if sheet is None:
        raise HTTPException(status_code=404, detail="Sheet not found")
    return {"roomId": room.id, "playerKey": player.player_key, "sheet": project_sheet(sheet)}


@app.get("/api/rooms/{room_id}/character-builder/options")
async def get_character_builder_options(room_id: str) -> dict[str, Any]:
    return {"roomId": sanitize_room_id(room_id), **character_builder_options()}


@app.post("/api/rooms/{room_id}/characters")
async def create_room_character(room_id: str, playerKey: str, payload: dict[str, Any] | None = Body(default=None)) -> dict[str, Any]:
    sanitized_room_id = sanitize_room_id(room_id)
    room = get_or_create_room(sanitized_room_id)
    player = Player(id="http-character-builder", name="Character Builder", player_key=normalize_player_key(playerKey, room.id), websocket=None, room_id=room.id)
    body = payload if isinstance(payload, dict) else {}
    requested_member_id = sanitize_identifier(str(body.get(payload_key(CharacterBuilderPayloadField.MEMBER_ID), "")))
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
    room.max_hit_point_increases.pop(member.id, None)
    room.max_hit_point_reductions.pop(member.id, None)
    room.exhaustion_levels.pop(member.id, None)
    room.condition_overrides.pop(member.id, None)
    room.condition_removals.pop(member.id, None)
    room.condition_durations.pop(member.id, None)
    room.damage_resistances.pop(member.id, None)
    room.damage_vulnerabilities.pop(member.id, None)
    room.damage_immunities.pop(member.id, None)
    await broadcast_room_state(room)
    return sheet_state_message(room, player)


@app.post("/api/rooms/{room_id}/sheet/{sheet_id}/rolls/attack")
async def roll_sheet_attack(room_id: str, sheet_id: str, playerKey: str, attackId: str = "main-hand", weaponOption: str | None = None) -> dict[str, Any]:
    return await create_attack_roll(room_id, sheet_id, playerKey, attackId, weaponOption)


@app.post("/api/rooms/{room_id}/sheet/{sheet_id}/rolls/damage")
async def roll_sheet_damage(room_id: str, sheet_id: str, playerKey: str, attackId: str = "main-hand", weaponOption: str | None = None) -> dict[str, Any]:
    return await create_damage_roll(room_id, sheet_id, playerKey, attackId, weaponOption)


@app.post("/api/rooms/{room_id}/sheet/{sheet_id}/spells/{spell_id}/rolls/attack")
async def roll_sheet_spell_attack(room_id: str, sheet_id: str, spell_id: str, playerKey: str, spellSlotLevel: int | None = None) -> dict[str, Any]:
    return await create_spell_attack_roll(room_id, sheet_id, playerKey, spell_id, spellSlotLevel)


@app.post("/api/rooms/{room_id}/sheet/{sheet_id}/spells/{spell_id}/rolls/weapon-attack")
async def roll_sheet_bound_weapon_attack(room_id: str, sheet_id: str, spell_id: str, playerKey: str, equipmentInstanceId: str, effectIndex: int = 0, choiceIndex: int | None = None) -> dict[str, Any]:
    return await create_bound_weapon_spell_roll(room_id, sheet_id, playerKey, spell_id, effectIndex, equipmentInstanceId, choiceIndex)


@app.post("/api/rooms/{room_id}/sheet/{sheet_id}/spells/{spell_id}/rolls/damage")
async def roll_sheet_spell_damage(room_id: str, sheet_id: str, spell_id: str, playerKey: str, effectIndex: int = 0, spellSlotLevel: int | None = None, instanceIndex: int | None = None, damageSaveSucceeded: bool | None = None, choiceIndex: int | None = None) -> dict[str, Any]:
    return await create_spell_damage_roll(room_id, sheet_id, playerKey, spell_id, effectIndex, spellSlotLevel, instanceIndex, damageSaveSucceeded, choiceIndex)


@app.post("/api/rooms/{room_id}/sheet/{sheet_id}/spells/{spell_id}/rolls/healing")
async def roll_sheet_spell_healing(room_id: str, sheet_id: str, spell_id: str, playerKey: str, effectIndex: int = 0, spellSlotLevel: int | None = None) -> dict[str, Any]:
    return await create_spell_healing_roll(room_id, sheet_id, playerKey, spell_id, effectIndex, spellSlotLevel)


@app.post("/api/rooms/{room_id}/sheet/{sheet_id}/spells/{spell_id}/rolls/temporary-hit-points")
async def roll_sheet_spell_temporary_hit_points(room_id: str, sheet_id: str, spell_id: str, playerKey: str, effectIndex: int = 0, spellSlotLevel: int | None = None) -> dict[str, Any]:
    return await create_spell_temporary_hit_points_roll(room_id, sheet_id, playerKey, spell_id, effectIndex, spellSlotLevel)


@app.post("/api/rooms/{room_id}/sheet/{sheet_id}/spells/{spell_id}/rolls/effect")
async def roll_sheet_spell_effect(room_id: str, sheet_id: str, spell_id: str, playerKey: str, effectIndex: int = 0, spellSlotLevel: int | None = None, choiceIndex: int | None = None, equipmentInstanceId: str | None = None) -> dict[str, Any]:
    return await create_spell_condition_roll(room_id, sheet_id, playerKey, spell_id, effectIndex, spellSlotLevel, choiceIndex, equipmentInstanceId)


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


@app.post("/api/rooms/{room_id}/dice")
async def roll_ad_hoc_dice(room_id: str, playerKey: str, dice: str = "d20", count: int = 1) -> dict[str, Any]:
    return await create_ad_hoc_dice_roll(room_id, playerKey, dice, count)


@app.post("/api/rooms/{room_id}/sheet/{sheet_id}/rolls/clear")
async def clear_sheet_rolls(room_id: str, sheet_id: str, playerKey: str) -> dict[str, Any]:
    sanitized_room_id = sanitize_room_id(room_id)
    room = get_or_create_room(sanitized_room_id)
    player = Player(id="http-sheet-clear-rolls", name="Sheet Rolls", player_key=normalize_player_key(playerKey, room.id), websocket=None, room_id=room.id)
    sheet = get_visible_sheet(room, player, sanitize_identifier(sheet_id))
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
    sheet = get_visible_sheet(room, player, sanitize_identifier(sheet_id))
    if sheet is None:
        raise HTTPException(status_code=404, detail="Sheet not found")
    if not can_control_sheet_roll(player, sheet):
        raise HTTPException(status_code=403, detail="Cannot update this sheet")

    resource = next((candidate for candidate in sheet.resources if sanitize_identifier(candidate.id) == sanitize_identifier(resource_id)), None)
    if resource is None:
        raise HTTPException(status_code=404, detail="Resource not found")

    adjusted = adjust_resource(
        ResourceState(resource.resource, resource.currentUses, resource.maxUses),
        currentUses,
    ).current
    room.resource_uses.setdefault(sheet.tokenId, {})[resource.id] = adjusted
    save_room_to_disk(room)
    await log_action_note(
        room,
        sheet,
        player,
        resource.name,
        f"Resource adjusted to {adjusted}/{resource.maxUses}",
        DiceType.D20,
        [],
        action_operations(),
    )
    await broadcast_room_state(room)
    updated = get_visible_sheet(room, player, sheet.id)
    return {"roomId": room.id, "sheet": project_sheet(updated) if updated else project_sheet(sheet)}


@app.post("/api/rooms/{room_id}/sheet/{sheet_id}/level")
async def update_sheet_level(room_id: str, sheet_id: str, playerKey: str, delta: int, className: str = "fighter") -> dict[str, Any]:
    sanitized_room_id = sanitize_room_id(room_id)
    room = get_or_create_room(sanitized_room_id)
    player = Player(id="http-sheet-level", name="DM", player_key=normalize_player_key(playerKey, room.id), websocket=None, room_id=room.id)
    if not is_dm(player):
        raise HTTPException(status_code=403, detail="Only the DM can level sheets")

    class_type = enum_value(ClassType, className)
    if class_type not in SUPPORTED_CLASS_TYPES:
        raise HTTPException(status_code=400, detail="Invalid class")

    sheet = get_visible_sheet(room, player, sanitize_identifier(sheet_id))
    if sheet is None:
        raise HTTPException(status_code=404, detail="Sheet not found")
    try:
        updated_member = level_character(
            room,
            sheet,
            class_type,
            delta,
            progression_operations(),
        )
    except ProgressionServiceError as error:
        raise HTTPException(status_code=error.status_code, detail=error.detail) from error

    updated_sheet = get_visible_sheet(room, player, updated_member.id)
    return {"roomId": room.id, "sheet": project_sheet(updated_sheet) if updated_sheet else None}


@app.post("/api/rooms/{room_id}/sheet/{sheet_id}/choices/{choice_id}")
async def update_sheet_progression_choice(room_id: str, sheet_id: str, choice_id: str, playerKey: str, payload: dict[str, Any] | None = Body(default=None)) -> dict[str, Any]:
    sanitized_room_id = sanitize_room_id(room_id)
    room = get_or_create_room(sanitized_room_id)
    player = Player(id="http-sheet-choice", name="Sheet Choice", player_key=normalize_player_key(playerKey, room.id), websocket=None, room_id=room.id)
    sheet = get_visible_sheet(room, player, sanitize_identifier(sheet_id))
    if sheet is None:
        raise HTTPException(status_code=404, detail="Sheet not found")
    if not can_control_sheet_roll(player, sheet):
        raise HTTPException(status_code=403, detail="Cannot update this sheet")

    values = payload.get("values", []) if isinstance(payload, dict) else []
    if not isinstance(values, list):
        raise HTTPException(status_code=400, detail="Choice values must be a list")

    choice = parse_progression_choice_id(choice_id)
    if choice is None:
        raise HTTPException(status_code=400, detail="Invalid progression choice")
    try:
        updated_member = apply_progression_selection(
            room,
            sanitize_identifier(sheet_id),
            choice,
            [str(value) for value in values],
            progression_operations(),
        )
    except ProgressionServiceError as error:
        raise HTTPException(status_code=error.status_code, detail=error.detail) from error

    updated_sheet = get_visible_sheet(room, player, updated_member.id)
    return {"roomId": room.id, "sheet": project_sheet(updated_sheet) if updated_sheet else None}


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
            recovered_resources = reset_character_for_rest(
                room,
                sheet,
                rest_type,
                character_state_persistence(),
            )
            if recovered_resources:
                recovery_summary = ", ".join(
                    f"{resource.label} {resource.current}/{resource.maximum}"
                    for resource in recovered_resources
                )
                await log_action_note(
                    room,
                    sheet,
                    player,
                    enum_label(rest_type),
                    f"Resources recovered: {recovery_summary}",
                    DiceType.D20,
                    [],
                    action_operations(),
                )
    save_room_to_disk(room)
    await broadcast_room_state(room)
    return sheet_state_message(room, player)


@app.post("/api/rooms/{room_id}/sheet/{sheet_id}/equipment/{item_id}/slot")
async def update_sheet_equipment_slot(room_id: str, sheet_id: str, item_id: str, playerKey: str, slot: str) -> dict[str, Any]:
    sanitized_room_id = sanitize_room_id(room_id)
    room = get_or_create_room(sanitized_room_id)
    player = Player(id="http-sheet-equipment", name="Sheet Equipment", player_key=normalize_player_key(playerKey, room.id), websocket=None, room_id=room.id)
    sheet = get_visible_sheet(room, player, sanitize_identifier(sheet_id))
    if sheet is None:
        raise HTTPException(status_code=404, detail="Sheet not found")
    if not can_control_sheet_roll(player, sheet):
        raise HTTPException(status_code=403, detail="Cannot update this sheet")

    item = next((candidate for candidate in sheet.equipment if sanitize_identifier(candidate.id) == sanitize_identifier(item_id)), None)
    if item is None:
        raise HTTPException(status_code=404, detail="Equipment item not found")

    equipment_slot = enum_value(EquipmentSlot, slot)
    if equipment_slot is None:
        raise HTTPException(status_code=400, detail="Invalid equipment slot")
    if equipment_slot not in valid_equipment_slots(item):
        raise HTTPException(status_code=400, detail="Invalid slot for equipment item")

    set_equipment_slot(room, sheet, item.id, equipment_slot)
    save_room_to_disk(room)
    await broadcast_room_state(room)
    updated = get_visible_sheet(room, player, sheet.id)
    return {"roomId": room.id, "sheet": project_sheet(updated) if updated else project_sheet(sheet)}


@app.post("/api/rooms/{room_id}/sheet/{sheet_id}/ongoing-effects/remove")
async def remove_sheet_ongoing_effect(
    room_id: str,
    sheet_id: str,
    playerKey: str,
    resolutionSeed: int = Body(),
    effectNodePath: list[int] = Body(),
) -> dict[str, Any]:
    sanitized_room_id = sanitize_room_id(room_id)
    room = get_or_create_room(sanitized_room_id)
    player = Player(id="http-sheet-ongoing-effect", name="Sheet Effect", player_key=normalize_player_key(playerKey, room.id), websocket=None, room_id=room.id)
    sheet = get_visible_sheet(room, player, sanitize_identifier(sheet_id))
    if sheet is None:
        raise HTTPException(status_code=404, detail="Sheet not found")
    if not can_control_sheet_roll(player, sheet):
        raise HTTPException(status_code=403, detail="Cannot update this sheet")
    if any(index < 0 for index in effectNodePath):
        raise HTTPException(status_code=400, detail="Invalid ongoing effect ID")

    effect_id = OngoingEffectId(resolutionSeed, EffectNodeId(tuple(effectNodePath)))
    active = next((effect for effect in sheet.ongoingEffects if effect.id == effect_id), None)
    if active is None:
        raise HTTPException(status_code=404, detail="Ongoing effect not found")
    if not remove_active_ongoing_effect(room, sheet, effect_id):
        raise HTTPException(status_code=400, detail="Ongoing effect cannot be removed manually")
    save_room_to_disk(room)
    await log_action_note(
        room,
        sheet,
        player,
        active.sourceLabel,
        "Ongoing effect removed",
        DiceType.D20,
        [],
        action_operations(),
    )
    await broadcast_room_state(room)
    updated = get_visible_sheet(room, player, sheet.id)
    return {"roomId": room.id, "sheet": project_sheet(updated) if updated else None}


@app.post("/api/rooms/{room_id}/sheet/{sheet_id}/conditions/{condition}")
async def update_sheet_condition(room_id: str, sheet_id: str, condition: str, playerKey: str, active: bool) -> dict[str, Any]:
    sanitized_room_id = sanitize_room_id(room_id)
    room = get_or_create_room(sanitized_room_id)
    player = Player(id="http-sheet-condition", name="Sheet Condition", player_key=normalize_player_key(playerKey, room.id), websocket=None, room_id=room.id)
    sheet = get_visible_sheet(room, player, sanitize_identifier(sheet_id))
    if sheet is None:
        raise HTTPException(status_code=404, detail="Sheet not found")
    if not can_control_sheet_roll(player, sheet):
        raise HTTPException(status_code=403, detail="Cannot update this sheet")

    condition_type = enum_value(ConditionType, condition)
    if condition_type is None:
        raise HTTPException(status_code=400, detail="Invalid condition")
    if condition_type == ConditionType.EXHAUSTION:
        return await update_sheet_exhaustion(room_id, sheet_id, playerKey, 1 if active else 0)

    updated_sheet_id = update_condition_state(
        room,
        sheet,
        condition_type,
        active,
        character_state_persistence(),
    )
    updated = get_visible_sheet(room, player, updated_sheet_id)
    return {"roomId": room.id, "sheet": project_sheet(updated) if updated else None}


@app.post("/api/rooms/{room_id}/sheet/{sheet_id}/exhaustion")
async def update_sheet_exhaustion(room_id: str, sheet_id: str, playerKey: str, level: int) -> dict[str, Any]:
    sanitized_room_id = sanitize_room_id(room_id)
    room = get_or_create_room(sanitized_room_id)
    player = Player(id="http-sheet-exhaustion", name="Sheet Exhaustion", player_key=normalize_player_key(playerKey, room.id), websocket=None, room_id=room.id)
    sheet = get_visible_sheet(room, player, sanitize_identifier(sheet_id))
    if sheet is None:
        raise HTTPException(status_code=404, detail="Sheet not found")
    if not can_control_sheet_roll(player, sheet):
        raise HTTPException(status_code=403, detail="Cannot update this sheet")

    updated_sheet_id = update_exhaustion_state(
        room,
        sheet,
        level,
        character_state_persistence(),
    )
    updated = get_visible_sheet(room, player, updated_sheet_id)
    if updated is not None:
        room.hit_points[updated_sheet_id] = updated.hp.current
    return {"roomId": room.id, "sheet": project_sheet(updated) if updated else None}


@app.post("/api/rooms/{room_id}/sheet/{sheet_id}/defenses/{defense}/{damage_type}")
async def update_sheet_damage_defense(room_id: str, sheet_id: str, defense: str, damage_type: str, playerKey: str, active: bool) -> dict[str, Any]:
    sanitized_room_id = sanitize_room_id(room_id)
    sanitized_sheet_id = sanitize_identifier(sheet_id)
    room = get_or_create_room(sanitized_room_id)
    player = Player(id="http-sheet-defense", name="Sheet Defense", player_key=normalize_player_key(playerKey, room.id), websocket=None, room_id=room.id)
    if not is_dm(player):
        raise HTTPException(status_code=403, detail="Only the DM can update damage defenses")

    sheet = get_visible_sheet(room, player, sanitized_sheet_id)
    if sheet is None:
        raise HTTPException(status_code=404, detail="Sheet not found")

    defense_type = enum_value(DamageDefenseType, defense)
    if defense_type is None:
        raise HTTPException(status_code=400, detail="Invalid damage defense")
    parsed_damage_type = enum_value(DamageType, damage_type)
    if parsed_damage_type is None:
        raise HTTPException(status_code=400, detail="Invalid damage type")

    updated_member = update_party_member_config(
        room.id,
        sanitized_sheet_id,
        lambda member: set_member_damage_defense(member, defense_type, parsed_damage_type, active),
    )

    updated_sheet_id = updated_member.id if updated_member is not None else sheet.tokenId
    if updated_member is None:
        set_room_damage_defense(room, updated_sheet_id, defense_type, parsed_damage_type, active)

    updated = get_visible_sheet(room, player, updated_sheet_id)
    return {"roomId": room.id, "sheet": project_sheet(updated) if updated else None}


@app.post("/api/rooms/{room_id}/rolls/{roll_id}/resolve")
async def resolve_roll(room_id: str, roll_id: str, playerKey: str, targetSheetId: str, preserveRoll: bool = False) -> dict[str, Any]:
    sanitized_room_id = sanitize_room_id(room_id)
    room = get_or_create_room(sanitized_room_id)
    player = Player(id="http-roll-resolve", name="DM", player_key=normalize_player_key(playerKey, room.id), websocket=None, room_id=room.id)
    if not is_dm(player):
        raise HTTPException(status_code=403, detail="Only the DM can resolve rolls")

    roll = next((candidate for candidate in room.pending_rolls.values() if candidate.id == sanitize_identifier(roll_id)), None)
    if roll is None:
        raise HTTPException(status_code=404, detail="Roll not found")

    target = get_visible_sheet(room, player, sanitize_identifier(targetSheetId))
    if target is None:
        raise HTTPException(status_code=404, detail="Target sheet not found")

    try:
        return await resolve_pending_roll(room, roll, target, preserveRoll, resolution_operations())
    except ResolutionServiceError as error:
        raise HTTPException(status_code=error.status_code, detail=error.detail) from error


@app.post("/api/rooms/{room_id}/resolution-prompts/{prompt_id}/respond")
async def respond_to_resolution_prompt(room_id: str, prompt_id: str, playerKey: str, use: bool) -> dict[str, Any]:
    sanitized_room_id = sanitize_room_id(room_id)
    room = get_or_create_room(sanitized_room_id)
    player = Player(id="http-resolution-prompt", name="Prompt", player_key=normalize_player_key(playerKey, room.id), websocket=None, room_id=room.id)
    prompt = room.pending_resolution_prompts.get(sanitize_identifier(prompt_id))
    if prompt is None:
        raise HTTPException(status_code=404, detail="Resolution prompt not found")
    if not is_dm(player) and prompt.ownerPlayerKey != player.player_key:
        raise HTTPException(status_code=403, detail="Cannot answer another player's prompt")

    target = get_visible_sheet(room, Player(id="prompt-dm", name="DM", player_key="dm", websocket=None, room_id=room.id), prompt.targetSheetId)
    if target is None:
        raise HTTPException(status_code=404, detail="Target sheet not found")

    try:
        return await respond_to_prompt(room, prompt, player, target, use, resolution_operations())
    except ResolutionServiceError as error:
        raise HTTPException(status_code=error.status_code, detail=error.detail) from error


@app.get("/campaigns/{campaign_id}/{asset_kind}/{filename}")
async def serve_campaign_asset(campaign_id: str, asset_kind: str, filename: str) -> FileResponse:
    campaign = get_campaign(sanitize_identifier(campaign_id))
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
    await apply_token_lock(room, player, token_id, message, board_operations())


async def move_token(room: Room, player: Player, token_id: str, message: dict[str, Any]) -> None:
    await apply_token_move(room, player, token_id, message, board_operations())


async def release_token(room: Room, player: Player, token_id: str) -> None:
    await apply_token_release(room, player, token_id, board_operations())


async def set_token_scene(room: Room, player: Player, token_id: str, message: dict[str, Any]) -> None:
    await apply_token_scene(room, player, token_id, message, board_operations())


async def set_token_radius(room: Room, player: Player, token_id: str, radius: Any) -> Token | None:
    return await apply_token_radius(room, player, token_id, radius, board_operations())


def apply_token_radius_from_message(room: Room, player: Player, token: Token, message: dict[str, Any]) -> None:
    apply_radius_from_message(room, player, token, message, board_operations())


async def set_fog_mode(room: Room, player: Player, message: dict[str, Any]) -> None:
    await apply_fog_mode(room, player, message, board_operations())


async def reveal_fog(room: Room, player: Player, message: dict[str, Any]) -> None:
    await apply_fog_reveal(room, player, message, board_operations())


def is_redundant_reveal_area(revealed_areas: list[RevealedArea], area: RevealedArea) -> bool:
    return reveal_is_redundant(revealed_areas, area, board_operations())


async def set_board(room: Room, player: Player, board_id: str) -> None:
    await apply_board_selection(room, player, board_id, board_operations())


async def load_asset_token(room: Room, player: Player, asset_kind: str, asset_id: str) -> None:
    await apply_asset_load(room, player, asset_kind, asset_id, board_operations())


async def delete_token(room: Room, player: Player, token_id: str) -> None:
    await apply_token_deletion(room, player, token_id, board_operations())


async def clear_scene(room: Room, player: Player) -> None:
    await apply_scene_clear(room, player, board_operations())


def get_or_create_room(room_id: str) -> Room:
    room = rooms.get(room_id)
    if room is not None:
        return room

    saved = read_room_save(existing_save_path(room_id))
    saved_board_id = valid_saved_board_id(saved, room_id)
    saved_board = get_board(saved_board_id, room_id) or fallback_board()
    saved_tokens = saved_tokens_from_data(saved, saved_board, room_id)
    tokens = merge_saved_tokens_with_party(saved_tokens, room_id) if saved_tokens is not None else seed_tokens(room_id)
    room = Room(
        id=room_id,
        tokens={token.id: token for token in tokens},
        players={},
        fog=saved_fog_from_data(saved, saved_board),
        board_id=saved_board_id,
        next_token_number=next_dynamic_token_number(tokens),
        pending_rolls={},
        pending_resolution_prompts={},
        roll_history=[],
        hit_points={},
        temporary_hit_points={},
        max_hit_point_increases=saved.max_hit_point_increases if saved else {},
        max_hit_point_reductions=saved.max_hit_point_reductions if saved else {},
        exhaustion_levels=saved.exhaustion_levels if saved else {},
        condition_overrides={},
        suppressed_conditions=saved.suppressed_conditions if saved else {},
        condition_durations={},
        condition_removals={},
        active_concentrations=saved.active_concentrations if saved else {},
        damage_resistances={},
        damage_vulnerabilities={},
        damage_immunities={},
        resource_uses=saved.resource_uses if saved else {},
        equipment_slots={},
        ongoing_effects=saved.ongoing_effects if saved else {},
        scheduled_effects=saved.scheduled_effects if saved else {},
        pending_effect_executions={},
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
    return board_max_token_radius(board, board_operations())


def default_token_radius(board: Board) -> float:
    return board_default_token_radius(board, board_operations())


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
    sheets = visible_sheets(room, player)
    return {
        "type": "sheet_state",
        "roomId": room.id,
        "playerKey": player.player_key,
        "sheets": [project_sheet(sheet) for sheet in sheets],
        "pendingRolls": [roll_payload_to_dict(roll) for roll in visible_pending_rolls(room, player)],
        "pendingResolutionPrompts": [resolution_interceptor_prompt_to_dict(prompt) for prompt in visible_resolution_prompts(room, player)],
        "rollHistory": [roll_log_entry_to_dict(entry) for entry in visible_roll_history(room, player)],
    }


def visible_sheets(room: Room, player: Player) -> list[CharacterSheet]:
    party_members = party_member_map(room.id)
    return [
        token_to_sheet(token, room.id, room.hit_points.get(token.id), party_members=party_members)
        for token in room.tokens.values()
        if can_view_sheet(player, token)
    ]


def visible_pending_rolls(room: Room, player: Player, visible_token_ids: set[str] | None = None) -> list[RollPayload]:
    return list(room.pending_rolls.values())


def visible_resolution_prompts(room: Room, player: Player) -> list[ResolutionInterceptorPrompt]:
    if is_dm(player):
        return list(room.pending_resolution_prompts.values())
    return [prompt for prompt in room.pending_resolution_prompts.values() if prompt.ownerPlayerKey == player.player_key]


def visible_roll_history(room: Room, player: Player, visible_token_ids: set[str] | None = None) -> list[RollLogEntry]:
    return list(room.roll_history)


def get_visible_sheet(room: Room, player: Player, sheet_id: str) -> CharacterSheet | None:
    for sheet in visible_sheets(room, player):
        if sheet.id == sheet_id:
            return sheet
    return None


def can_view_sheet(player: Player, token: Token) -> bool:
    return is_dm(player) or token.kind == TokenKind.CHARACTER


def can_control_sheet_roll(player: Player, sheet: CharacterSheet) -> bool:
    return is_dm(player) or player.player_key == sheet.owner


def token_to_sheet(
    token: Token,
    campaign_id: str | None = None,
    current_hp: int | None = None,
    party_members: dict[str, PartyMember] | None = None,
) -> CharacterSheet:
    party_member = None
    if token.kind == TokenKind.CHARACTER:
        party_member = party_members.get(token.id) if party_members is not None else party_member_by_id(token.id, campaign_id)
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
        base_speed = sheet.speed
        sheet.hp = hit_points_after_max_increases(sheet.hp, room.max_hit_point_increases.get(token.id, []), increase_current=token.id not in room.hit_points)
        sheet.hp.temporary = room.temporary_hit_points.get(token.id, sheet.hp.temporary)
        sheet.hp = hit_points_after_max_reductions(sheet.hp, room.max_hit_point_reductions.get(token.id, []))
        sheet.conditions = room.condition_overrides.get(token.id, sheet.conditions)
        from dnd_board.rules.shared.condition_effects import suppressed_conditions

        derived_suppressions = suppressed_conditions(sheet.conditions)
        sheet.suppressedConditions = list(dict.fromkeys([
            *room.suppressed_conditions.get(token.id, []),
            *(condition for condition in sheet.conditions if condition in derived_suppressions),
        ]))
        sheet.ongoingEffects = list(room.ongoing_effects.get(token.id, []))
        sheet.exhaustionLevel = room.exhaustion_levels.get(token.id, sheet.exhaustionLevel)
        sheet.conditions = conditions_for_exhaustion_level(sheet.conditions, sheet.exhaustionLevel)
        sheet.damageResistances = merged_damage_defenses(sheet.damageResistances, room.damage_resistances.get(token.id, []))
        sheet.damageVulnerabilities = merged_damage_defenses(sheet.damageVulnerabilities, room.damage_vulnerabilities.get(token.id, []))
        sheet.damageImmunities = merged_damage_defenses(sheet.damageImmunities, room.damage_immunities.get(token.id, []))
        for active in sheet.ongoingEffects:
            for defense in active.effect.damageDefenses:
                defenses = {
                    RulesDamageDefenseType.RESISTANCE: sheet.damageResistances,
                    RulesDamageDefenseType.VULNERABILITY: sheet.damageVulnerabilities,
                    RulesDamageDefenseType.IMMUNITY: sheet.damageImmunities,
                }[defense.defense]
                if defense.operation == CollectionOperation.ADD and defense.damageType not in defenses:
                    defenses.append(defense.damageType)
                elif defense.operation == CollectionOperation.REMOVE:
                    defenses[:] = [damage_type for damage_type in defenses if damage_type != defense.damageType]
        sheet.damageResistances = effective_damage_resistance_list(sheet)
        active_concentration = room.active_concentrations.get(token.id)
        if active_concentration is not None:
            sheet.activeConcentration = active_concentration_status(active_concentration)
        sheet.speed = base_speed
    sheet.armorClass = condition_adjusted_armor_class(sheet)
    sheet.speed = condition_adjusted_speed_for_exhaustion(
        sheet.speed,
        sheet.conditions,
        sheet.exhaustionLevel,
        sheet.ongoingEffects,
        sheet.suppressedConditions,
    )
    from dnd_board.rules.shared.weapon_effects import projected_weapon_attack

    sheet.attacks = [projected_weapon_attack(sheet, attack) for attack in sheet.attacks]
    return sheet


async def create_attack_roll(room_id: str, sheet_id: str, player_key: str, attack_id: str, weapon_option: str | None = None) -> dict[str, Any]:
    room, player, sheet = roll_context(room_id, sheet_id, player_key)
    return await action_service_response(
        create_attack_action(room, player, sheet, attack_id, action_operations(), weapon_option=weapon_option)
    )


async def create_damage_roll(room_id: str, sheet_id: str, player_key: str, attack_id: str, weapon_option: str | None = None) -> dict[str, Any]:
    room, player, sheet = roll_context(room_id, sheet_id, player_key)
    return await action_service_response(
        create_attack_action(
            room,
            player,
            sheet,
            attack_id,
            action_operations(),
            damage_only=True,
            weapon_option=weapon_option,
        )
    )


async def create_spell_attack_roll(room_id: str, sheet_id: str, player_key: str, spell_id: str, spell_slot_level: int | None = None) -> dict[str, Any]:
    room, player, sheet = roll_context(room_id, sheet_id, player_key)
    return await action_service_response(
        create_spell_attack_action(
            room,
            player,
            sheet,
            spell_id,
            spell_slot_level,
            action_operations(),
        )
    )


async def create_bound_weapon_spell_roll(room_id: str, sheet_id: str, player_key: str, spell_id: str, effect_index: int, equipment_instance_id: str, choice_index: int | None) -> dict[str, Any]:
    room, player, sheet = roll_context(room_id, sheet_id, player_key)
    return await action_service_response(
        create_bound_weapon_spell_action(
            room,
            player,
            sheet,
            spell_id,
            effect_index,
            equipment_instance_id,
            choice_index,
            action_operations(),
        )
    )


async def create_spell_damage_roll(room_id: str, sheet_id: str, player_key: str, spell_id: str, effect_index: int = 0, spell_slot_level: int | None = None, instance_index: int | None = None, damage_save_succeeded: bool | None = None, choice_index: int | None = None) -> dict[str, Any]:
    room, player, sheet = roll_context(room_id, sheet_id, player_key)
    return await action_service_response(
        create_spell_damage_action(
            room,
            player,
            sheet,
            spell_id,
            effect_index,
            spell_slot_level,
            instance_index,
            damage_save_succeeded,
            choice_index,
            action_operations(),
        )
    )


async def create_spell_healing_roll(room_id: str, sheet_id: str, player_key: str, spell_id: str, effect_index: int = 0, spell_slot_level: int | None = None) -> dict[str, Any]:
    room, player, sheet = roll_context(room_id, sheet_id, player_key)
    return await action_service_response(
        create_spell_simple_action(
            room,
            player,
            sheet,
            spell_id,
            effect_index,
            spell_slot_level,
            action_operations(),
            action_type=SpellRollType.HEALING,
        )
    )


async def create_spell_temporary_hit_points_roll(room_id: str, sheet_id: str, player_key: str, spell_id: str, effect_index: int = 0, spell_slot_level: int | None = None) -> dict[str, Any]:
    room, player, sheet = roll_context(room_id, sheet_id, player_key)
    return await action_service_response(
        create_spell_simple_action(
            room,
            player,
            sheet,
            spell_id,
            effect_index,
            spell_slot_level,
            action_operations(),
            action_type=SpellRollType.TEMPORARY_HIT_POINTS,
        )
    )


async def create_spell_condition_roll(room_id: str, sheet_id: str, player_key: str, spell_id: str, effect_index: int = 0, spell_slot_level: int | None = None, choice_index: int | None = None, equipment_instance_id: str | None = None) -> dict[str, Any]:
    room, player, sheet = roll_context(room_id, sheet_id, player_key)
    return await action_service_response(
        create_spell_simple_action(
            room,
            player,
            sheet,
            spell_id,
            effect_index,
            spell_slot_level,
            action_operations(),
            action_type=SpellRollType.EFFECT,
            choice_index=choice_index,
            equipment_instance_id=equipment_instance_id,
        )
    )


async def create_ability_check_roll(room_id: str, sheet_id: str, player_key: str, ability_key: str) -> dict[str, Any]:
    room, player, sheet = roll_context(room_id, sheet_id, player_key)
    return await action_service_response(
        create_ability_score_action(
            room,
            player,
            sheet,
            ability_key,
            action_operations(),
        )
    )


async def create_saving_throw_roll(room_id: str, sheet_id: str, player_key: str, ability_key: str) -> dict[str, Any]:
    room, player, sheet = roll_context(room_id, sheet_id, player_key)
    return await action_service_response(
        create_ability_score_action(
            room,
            player,
            sheet,
            ability_key,
            action_operations(),
            saving_throw=True,
        )
    )


async def create_resource_roll(room_id: str, sheet_id: str, player_key: str, resource_id: str, action_id: str) -> dict[str, Any]:
    room, player, sheet = roll_context(room_id, sheet_id, player_key)
    return await action_service_response(
        create_sheet_entry_action(
            room,
            player,
            sheet,
            resource_id,
            action_id,
            action_operations(),
            resource_entry=True,
        )
    )


async def create_ability_roll(room_id: str, sheet_id: str, player_key: str, ability_id: str, action_id: str) -> dict[str, Any]:
    room, player, sheet = roll_context(room_id, sheet_id, player_key)
    return await action_service_response(
        create_sheet_entry_action(
            room,
            player,
            sheet,
            ability_id,
            action_id,
            action_operations(),
            resource_entry=False,
        )
    )


async def create_ad_hoc_dice_roll(room_id: str, player_key: str, dice: str, count: int) -> dict[str, Any]:
    sanitized_room_id = sanitize_room_id(room_id)
    room = get_or_create_room(sanitized_room_id)
    player = Player(id="http-dice-roller", name="Dice Roller", player_key=normalize_player_key(player_key, room.id), websocket=None, room_id=room.id)
    return await action_service_response(
        create_ad_hoc_dice_action(room, player, dice, count, action_operations())
    )


def roll_context(room_id: str, sheet_id: str, player_key: str) -> tuple[Room, Player, CharacterSheet]:
    sanitized_room_id = sanitize_room_id(room_id)
    room = get_or_create_room(sanitized_room_id)
    player = Player(id="http-sheet-roll", name="Sheet Roller", player_key=normalize_player_key(player_key, room.id), websocket=None, room_id=room.id)
    sheet = get_visible_sheet(room, player, sanitize_identifier(sheet_id))
    if sheet is None:
        raise HTTPException(status_code=404, detail="Sheet not found")
    if not can_control_sheet_roll(player, sheet):
        raise HTTPException(status_code=403, detail="Cannot roll for this sheet")
    return room, player, sheet


def parse_rest_type(rest: str) -> RestType | None:
    normalized = sanitize_identifier(rest)
    if normalized in {"short", "short-rest", "shortrest"}:
        return RestType.SHORT_REST
    if normalized in {"long", "long-rest", "longrest"}:
        return RestType.LONG_REST
    return None


def hit_points_after_max_reductions(hp: HitPoints, reductions: list[ActiveMaxHitPointReduction]) -> HitPoints:
    reduction_total = sum(max(0, reduction.amount) for reduction in reductions)
    if reduction_total <= 0:
        return hp
    effective_max = max(1, hp.max - reduction_total)
    return HitPoints(current=min(hp.current, effective_max), max=effective_max, temporary=hp.temporary)


def hit_points_after_max_increases(hp: HitPoints, increases: list[ActiveMaxHitPointIncrease], *, increase_current: bool) -> HitPoints:
    increase_total = sum(max(0, increase.amount) for increase in increases)
    if increase_total <= 0:
        return hp
    effective_max = hp.max + increase_total
    effective_current = hp.current + increase_total if increase_current else min(hp.current, effective_max)
    return HitPoints(current=effective_current, max=effective_max, temporary=hp.temporary)



def roll_queue_key(roll: RollPayload) -> tuple[str, str, str, str]:
    return (roll.tokenId, enum_key(roll.source.section), roll.source.sourceId, roll.source.actionId)


def remove_pending_rolls_for_token(room: Room, token_id: str) -> None:
    for key in [key for key, roll in room.pending_rolls.items() if roll.tokenId == token_id]:
        room.pending_rolls.pop(key, None)


def roll_can_apply_damage(roll: RollPayload) -> bool:
    if roll.resolution == RollResolutionMode.APPLY_DAMAGE:
        return True
    if roll.pendingEffect is None:
        return False
    from dnd_board.rules.shared.character_effects import first_damage_effect

    return first_damage_effect(roll.pendingEffect) is not None


def failed_save_ability(roll: RollPayload) -> AbilityType | None:
    return roll.damageSavingThrow if roll.damageSaveSucceeded is False else None


def failed_save_dc(roll: RollPayload) -> int | None:
    return roll.damageSaveDc if roll.damageSaveSucceeded is False else None


def all_room_sheets(room: Room) -> list[CharacterSheet]:
    player = Player(id="interceptor-dm", name="DM", player_key="dm", websocket=None, room_id=room.id)
    return visible_sheets(room, player)


def source_sheet_for_roll(room: Room, roll: RollPayload) -> CharacterSheet | None:
    token = room.tokens.get(roll.tokenId)
    if token is None:
        return None
    return token_to_sheet(token, room.id, room.hit_points.get(token.id))


def sheet_conditions(sheet_id: str, campaign_id: str) -> list[ConditionType]:
    manifest = load_party_manifest_config(campaign_asset_dir("party", campaign_id) / "party.json")
    if manifest is None:
        return []
    member = next((candidate for candidate in manifest.members if candidate.id == sheet_id), None)
    if member is None or member.sheet is None or member.sheet.conditions is None:
        return []
    return list(member.sheet.conditions)


def party_member_by_id(member_id: str, campaign_id: str | None = None) -> PartyMember | None:
    return party_member_map(campaign_id).get(member_id)


def party_member_map(campaign_id: str | None = None) -> dict[str, PartyMember]:
    return {member.id: member for member in load_party_members(campaign_id)}


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


def can_control_token(player: Player, token: Token) -> bool:
    return player_can_control_token(player, token)


def is_dm(player: Player) -> bool:
    return player_is_dm(player)


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
        if sanitize_identifier(member.name) == sanitize_identifier(normalized):
            return member.owner
    return "player-1"


def save_room_to_disk(room: Room) -> None:
    write_room_save(room, save_path(room.id))


def save_room_if_concentration_changed(room: Room, resolution: RollResolution) -> None:
    if resolution.concentrationUpdates:
        save_room_to_disk(room)


async def load_room_from_disk(room: Room, player: Player) -> bool:
    if not is_dm(player):
        return False

    saved = read_room_save(existing_save_path(room.id))
    if saved is None:
        return False
    saved_board_id = valid_saved_board_id(saved, room.id)
    saved_board = get_board(saved_board_id, room.id) or fallback_board()
    saved_tokens = saved_tokens_from_data(saved, saved_board, room.id)
    if saved_tokens is None:
        return False

    tokens = merge_saved_tokens_with_party(saved_tokens, room.id)
    room.tokens = {token.id: token for token in tokens}
    room.fog = saved_fog_from_data(saved, saved_board)
    room.board_id = saved_board_id
    room.next_token_number = next_dynamic_token_number(tokens)
    room.pending_rolls = {}
    room.pending_resolution_prompts = {}
    room.pending_effect_executions = {}
    room.roll_history = []
    room.hit_points = {}
    room.temporary_hit_points = {}
    room.max_hit_point_increases = saved.max_hit_point_increases
    room.max_hit_point_reductions = saved.max_hit_point_reductions
    room.exhaustion_levels = saved.exhaustion_levels
    room.condition_overrides = {}
    room.suppressed_conditions = saved.suppressed_conditions
    room.condition_durations = {}
    room.condition_removals = {}
    room.active_concentrations = saved.active_concentrations
    room.damage_resistances = {}
    room.damage_vulnerabilities = {}
    room.damage_immunities = {}
    room.resource_uses = saved.resource_uses
    room.equipment_slots = {}
    room.ongoing_effects = saved.ongoing_effects
    room.scheduled_effects = saved.scheduled_effects
    await broadcast_room_state(room)
    return True


def valid_saved_board_id(saved: LoadedRoomSave | None, campaign_id: str) -> str:
    default_id = default_board_id(campaign_id)
    if saved is None or get_board(saved.board_id, campaign_id) is None:
        return default_id
    return saved.board_id


def saved_tokens_from_data(
    saved: LoadedRoomSave | None,
    board: Board,
    campaign_id: str,
) -> list[Token] | None:
    if saved is None:
        return None
    try:
        return [token_from_dict(token, board, campaign_id) for token in saved.tokens]
    except (KeyError, TypeError, ValueError):
        return None


def saved_fog_from_data(saved: LoadedRoomSave | None, board: Board) -> FogState:
    if saved is None:
        return default_fog()
    try:
        return fog_from_dict(saved.fog, board)
    except (TypeError, ValueError):
        return default_fog()


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
        board_id = sanitize_identifier(path.stem)
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
    return write_updated_party_member(
        campaign_paths(),
        campaign_id,
        member_id,
        update,
    )


def save_party_member_config(campaign_id: str, member: PartyMemberConfig) -> PartyMemberConfig:
    return write_party_member(campaign_paths(), campaign_id, member)


def writable_party_manifest_path(campaign_id: str) -> Path:
    return find_writable_party_manifest_path(campaign_paths(), campaign_id)


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
    return load_party_manifest(path)


def set_member_conditions(member: PartyMemberConfig, conditions: list[ConditionType]) -> None:
    if member.sheet is None:
        member.sheet = PartyMemberSheet()
    member.sheet.conditions = conditions or None


def persist_sheet_conditions(
    campaign_id: str,
    sheet_id: str,
    conditions: list[ConditionType],
) -> None:
    update_party_member_config(
        campaign_id,
        sheet_id,
        lambda member: set_member_conditions(member, conditions),
    )


def set_member_damage_defense(member: PartyMemberConfig, defense: DamageDefenseType, damage_type: DamageType, active: bool) -> None:
    if member.sheet is None:
        member.sheet = PartyMemberSheet()
    if defense == DamageDefenseType.RESISTANCE:
        member.sheet.damageResistances = updated_damage_defense_list(member.sheet.damageResistances or [], damage_type, active)
        return
    if defense == DamageDefenseType.VULNERABILITY:
        member.sheet.damageVulnerabilities = updated_damage_defense_list(member.sheet.damageVulnerabilities or [], damage_type, active)
        return
    member.sheet.damageImmunities = updated_damage_defense_list(member.sheet.damageImmunities or [], damage_type, active)


def set_room_damage_defense(room: Room, sheet_id: str, defense: DamageDefenseType, damage_type: DamageType, active: bool) -> None:
    damage_defenses = room_damage_defenses(room, defense)
    updated = updated_damage_defense_list(damage_defenses.get(sheet_id, []), damage_type, active)
    if updated is None:
        damage_defenses.pop(sheet_id, None)
    else:
        damage_defenses[sheet_id] = updated


def room_damage_defenses(room: Room, defense: DamageDefenseType) -> dict[str, list[DamageType]]:
    if defense == DamageDefenseType.RESISTANCE:
        return room.damage_resistances
    if defense == DamageDefenseType.VULNERABILITY:
        return room.damage_vulnerabilities
    return room.damage_immunities


def updated_damage_defense_list(defenses: list[DamageType], damage_type: DamageType, active: bool) -> list[DamageType] | None:
    if active and damage_type not in defenses:
        return [*defenses, damage_type]
    if not active:
        return [defense for defense in defenses if defense != damage_type] or None
    return list(defenses) or None


def merged_damage_defenses(sheet_defenses: list[DamageType], room_defenses: list[DamageType]) -> list[DamageType]:
    merged = list(sheet_defenses)
    for defense in room_defenses:
        if defense not in merged:
            merged.append(defense)
    return merged


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
    return normalize_repository_member_id(campaign_paths(), value, fallback)


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
    normalized = sanitize_identifier(board_id)
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



def humanize_asset_name(asset_name: str) -> str:
    return humanize_name(asset_name)


def list_assets() -> list[Asset]:
    return list_assets_from_dir(TokenKind.ASSET, SHARED_ASSET_DIR)


def list_assets_from_dir(kind: TokenKind, directory: Path) -> list[Asset]:
    assets: list[Asset] = []
    for path in list_image_files(directory):
        asset_id = sanitize_identifier(path.stem)
        if not asset_id:
            continue
        assets.append(Asset(id=asset_id, kind=kind, name=humanize_asset_name(path.stem), avatarUrl=asset_file_url(path)))
    return assets


def get_asset(asset_kind: str, asset_id: str) -> Asset | None:
    normalized_kind = asset_kind.strip().lower()
    normalized_id = sanitize_identifier(asset_id)
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
    return find_active_campaign(campaign_paths(), campaign_id)


def get_campaign(campaign_id: str) -> Campaign | None:
    return find_campaign(campaign_paths(), campaign_id)


def campaign_asset_dir(directory_name: str, campaign_id: str | None = None) -> Path:
    return find_campaign_asset_dir(campaign_paths(), directory_name, campaign_id)


def campaign_save_dir(campaign_id: str | None = None) -> Path:
    return find_campaign_save_dir(campaign_paths(), campaign_id)


def save_path(room_id: str) -> Path:
    return find_save_path(campaign_paths(), room_id)


def existing_save_path(room_id: str) -> Path:
    return find_existing_save_path(campaign_paths(), room_id)


def list_image_files(*directories: Path) -> list[Path]:
    seen: set[str] = set()
    paths: list[Path] = []
    for directory in directories:
        if not directory.exists():
            continue
        for path in sorted(directory.iterdir()):
            if path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp", ".gif"}:
                continue
            asset_id = sanitize_identifier(path.stem)
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
