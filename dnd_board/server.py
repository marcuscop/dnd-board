from __future__ import annotations

import json
import random
from io import BytesIO
from dataclasses import asdict, dataclass, field, replace
from enum import Enum
from pathlib import Path
from time import time_ns
from typing import Any

from fastapi import Body, FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, UnidentifiedImageError
from pillow_heif import register_heif_opener

from dnd_board.character_sheet import (
    ActiveConcentrationStatus,
    ActiveConcentrationUpdate,
    AbilityScores,
    AbilityType,
    AttackAction,
    CharacterSheet,
    CharacterClassLevel,
    ClassType,
    ConditionDuration,
    ConditionType,
    DamageType,
    DiceType,
    EquipmentSlot,
    HitPoints,
    PartyMemberConfig,
    PartyMemberSheet,
    PartyMember,
    PartyManifest,
    ProficiencyLevel,
    RollPayload,
    RollLogEntry,
    RollLogEntryType,
    RollModifierBreakdown,
    RollModifierEffectTarget,
    RollResolutionMode,
    RollResolution,
    RollSource,
    ResolutionInterceptorPrompt,
    ResolutionInterceptorTrigger,
    ResolutionInterceptorType,
    RestType,
    SheetSectionType,
    SkillType,
    SpellComponent,
    SpellEntry,
    SpellId,
    SpellSaveOutcome,
    SpellSource,
    TimeEconomy,
    TokenKind,
    build_attack_roll_payload,
    build_combined_attack_roll_payload,
    build_ability_check_roll_payload,
    build_character_sheet,
    build_damage_roll_payload,
    build_spell_attack_roll_payload,
    build_spell_condition_roll_payload,
    build_spell_damage_roll_payload,
    build_spell_healing_roll_payload,
    build_spell_temporary_hit_points_roll_payload,
    build_saving_throw_roll_payload,
    build_roll_action_payload,
    build_true_strike_attack_roll_payload,
    build_true_strike_damage_roll_payload,
    ability_modifier,
    active_roll_modifier_breakdown,
    attack_roll_with_critical_damage,
    attack_roll_with_target_condition_modifiers,
    condition_adjusted_armor_class,
    condition_adjusted_speed,
    condition_adjusted_speed_for_exhaustion,
    condition_immunity_blocks,
    condition_saving_throw_advantage_conditions,
    condition_saving_throw_disadvantage_conditions,
    condition_saving_throw_forced_failure_conditions,
    creature_type_list_label,
    target_creature_type_matches,
    shillelagh_weapon_attacks,
    true_strike_weapon_attack,
    true_strike_weapon_attacks,
    enum_value,
    enum_key,
    enum_label,
    effective_damage_resistance_list,
    effect_saving_throw_dc,
    party_manifest_from_dict,
    positive_int,
    resolve_roll_against_target as resolve_dnd_roll_against_target,
    roll_payload_to_dict,
    roll_log_entry_to_dict,
    resolution_interceptor_prompt_to_dict,
    roll_resolution_to_dict,
    sanitize_identifier,
    sheet_to_dict,
    spell_casting_ability,
    typed_json_from_value,
    typed_json_to_value,
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
    ProgressionChoiceId,
    apply_progression_choice,
    class_hit_die,
    fighter_asi_levels_up_to,
    fighter_skill_option_types,
    fighter_skill_proficiency_count,
    parse_progression_choice_id,
    prune_progression_choices,
    rogue_asi_levels_up_to,
    rogue_expertise_count,
    rogue_skill_option_types,
    rogue_skill_proficiency_count,
    update_class_level,
    wizard_asi_levels_up_to,
    wizard_skill_option_types,
    wizard_skill_proficiency_count,
)
from dnd_board.rules.shared.effects import (
    ActiveOngoingEffect,
    ActiveScheduledEffect,
    AbilityCheck,
    AmountCalculation,
    ApplyEffect,
    AttackerIsVisiblePredicate,
    AttackRoll,
    AttackRollEffect,
    AttackRollType,
    BoundEffect,
    CalculatedAmount,
    CombinedAmount,
    CancelPendingAction,
    ContestedCheck,
    ContestedCheckEffect,
    ConditionOperation,
    CollectionOperation,
    DamageDefenseType as RulesDamageDefenseType,
    Interaction,
    InteractionDecisionType,
    EffectDurationType,
    DifficultyClassType,
    EffectAmountInput,
    EffectNodeId,
    EffectParticipantBindings,
    EffectResolutionInputs,
    EffectRollInput,
    EndingConditionType,
    FixedAmount,
    DiceAmount,
    ModifyRoll,
    RollModificationType,
    PendingDamageModificationType,
    SequenceEffect,
    ModifyPendingDamage,
    PreventCondition,
    ModifyAction,
    ApplyEffectOperation,
    ScheduleEffectOperation,
    ReplaceRollOutcome,
    ResolutionEvent,
    ResolutionEventResponse,
    ResolutionEventType,
    ResolutionId,
    RerollSavingThrow,
    RollOutcome,
    RollOutcomePredicate,
    SavingThrowEffect,
    SavingThrowAbilityPredicate,
    SourceIsAttackPredicate,
    SourceIsSpellPredicate,
    TargetIsOwnerPredicate,
    apply_interaction_operations,
    dispatch_scheduled_effects,
    recurring_effects_for_event,
)
from dnd_board.rules.shared.effects import MaximumHitPointsEffect, MaximumHitPointsOperation, RestEffect
from dnd_board.rules.shared.resources import (
    RESOURCE_DEFINITIONS,
    InsufficientResourceError,
    ResourceCost,
    ResourceDefinition,
    ResourceId,
    ResourceKey,
    ResourceRecoveryTrigger,
    ResourceState,
    ResourceUpdate,
    adjust_resource,
    recover_resources,
    spell_slot_resource_id,
    spend_resources,
)
from dnd_board.rules.shared.character_effects import (
    CharacterEffectExecution,
    CharacterEffectExecutionContext,
    ResolvedCharacterEffect,
    added_condition_types,
    advance_character_effect_execution,
    first_contested_check_effect,
    resolved_d20,
    start_character_effect_execution,
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
class ConditionRemovalSave:
    savingThrow: AbilityType
    saveDc: int
    advantage: bool = False


@dataclass
class ActiveConditionSource:
    targetSheetId: str
    condition: ConditionType
    spellId: SpellId
    casterSheetId: str
    wasAlreadyActive: bool = False


@dataclass
class ActiveConcentration:
    casterSheetId: str
    spellId: SpellId
    spellName: str
    conditionSources: list[ActiveConditionSource]


@dataclass
class ActiveMaxHitPointReduction:
    amount: int
    sourceSpellId: SpellId
    sourceName: str
    reset: RestType


@dataclass
class ActiveMaxHitPointIncrease:
    amount: int
    sourceSpellId: SpellId
    sourceName: str


class DamageDefenseType(Enum):
    RESISTANCE = "resistance"
    VULNERABILITY = "vulnerability"
    IMMUNITY = "immunity"


@dataclass
class Room:
    id: str
    tokens: dict[str, Token]
    players: dict[str, Player]
    fog: FogState
    board_id: str
    next_token_number: int
    pending_rolls: dict[tuple[str, str, str, str], RollPayload]
    pending_resolution_prompts: dict[str, ResolutionInterceptorPrompt]
    roll_history: list[RollLogEntry]
    hit_points: dict[str, int]
    temporary_hit_points: dict[str, int]
    max_hit_point_increases: dict[str, list[ActiveMaxHitPointIncrease]]
    max_hit_point_reductions: dict[str, list[ActiveMaxHitPointReduction]]
    exhaustion_levels: dict[str, int]
    condition_overrides: dict[str, list[ConditionType]]
    suppressed_conditions: dict[str, list[ConditionType]]
    condition_durations: dict[str, dict[ConditionType, ConditionDuration]]
    condition_removals: dict[str, dict[ConditionType, ConditionRemovalSave]]
    active_concentrations: dict[str, ActiveConcentration]
    damage_resistances: dict[str, list[DamageType]]
    damage_vulnerabilities: dict[str, list[DamageType]]
    damage_immunities: dict[str, list[DamageType]]
    resource_uses: dict[str, dict[str, int]]
    equipment_slots: dict[str, dict[str, EquipmentSlot]]
    ongoing_effects: dict[str, list[ActiveOngoingEffect]]
    scheduled_effects: dict[str, list[ActiveScheduledEffect]]
    pending_effect_executions: dict[int, PendingCharacterResolution]


@dataclass(frozen=True)
class CharacterRuntimeSnapshot:
    hitPoints: HitPoints
    conditions: tuple[ConditionType, ...]
    suppressedConditions: tuple[ConditionType, ...]
    damageResistances: tuple[DamageType, ...]
    damageVulnerabilities: tuple[DamageType, ...]
    damageImmunities: tuple[DamageType, ...]
    ongoingEffects: tuple[ActiveOngoingEffect, ...]


@dataclass
class PendingCharacterResolution:
    active: CharacterEffectExecution
    roll: RollPayload
    targetSheetId: str
    responseRolls: list[RollPayload]
    outcomePrefixes: list[str]
    ignoredInterceptors: list[str]
    participantSnapshots: dict[str, CharacterRuntimeSnapshot]
    interactionEvent: InteractionEventKey | None = None
    dispatchedEvents: set[InteractionEventKey] = field(default_factory=set)
    scheduledEffectStates: dict[str, list[ActiveScheduledEffect]] = field(default_factory=dict)
    touchedScheduledTargets: set[str] = field(default_factory=set)


@dataclass(frozen=True)
class InteractionEventKey:
    eventType: ResolutionEventType
    effectNodeId: EffectNodeId | None


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
async def roll_sheet_attack(room_id: str, sheet_id: str, playerKey: str, attackId: str = "main-hand") -> dict[str, Any]:
    return await create_attack_roll(room_id, sheet_id, playerKey, attackId)


@app.post("/api/rooms/{room_id}/sheet/{sheet_id}/rolls/damage")
async def roll_sheet_damage(room_id: str, sheet_id: str, playerKey: str, attackId: str = "main-hand") -> dict[str, Any]:
    return await create_damage_roll(room_id, sheet_id, playerKey, attackId)


@app.post("/api/rooms/{room_id}/sheet/{sheet_id}/spells/{spell_id}/rolls/attack")
async def roll_sheet_spell_attack(room_id: str, sheet_id: str, spell_id: str, playerKey: str, spellSlotLevel: int | None = None) -> dict[str, Any]:
    return await create_spell_attack_roll(room_id, sheet_id, playerKey, spell_id, spellSlotLevel)


@app.post("/api/rooms/{room_id}/sheet/{sheet_id}/spells/{spell_id}/rolls/true-strike-attack")
async def roll_sheet_true_strike_attack(room_id: str, sheet_id: str, spell_id: str, playerKey: str, attackId: str, damageType: str) -> dict[str, Any]:
    return await create_true_strike_attack_roll(room_id, sheet_id, playerKey, spell_id, attackId, damageType)


@app.post("/api/rooms/{room_id}/sheet/{sheet_id}/spells/{spell_id}/rolls/damage")
async def roll_sheet_spell_damage(room_id: str, sheet_id: str, spell_id: str, playerKey: str, effectIndex: int = 0, spellSlotLevel: int | None = None, instanceIndex: int | None = None, damageSaveSucceeded: bool | None = None, choiceIndex: int | None = None) -> dict[str, Any]:
    return await create_spell_damage_roll(room_id, sheet_id, playerKey, spell_id, effectIndex, spellSlotLevel, instanceIndex, damageSaveSucceeded, choiceIndex)


@app.post("/api/rooms/{room_id}/sheet/{sheet_id}/spells/{spell_id}/rolls/true-strike-damage")
async def roll_sheet_true_strike_damage(room_id: str, sheet_id: str, spell_id: str, playerKey: str, attackId: str, damageType: str) -> dict[str, Any]:
    return await create_true_strike_damage_roll(room_id, sheet_id, playerKey, spell_id, attackId, damageType)


@app.post("/api/rooms/{room_id}/sheet/{sheet_id}/spells/{spell_id}/rolls/healing")
async def roll_sheet_spell_healing(room_id: str, sheet_id: str, spell_id: str, playerKey: str, effectIndex: int = 0, spellSlotLevel: int | None = None) -> dict[str, Any]:
    return await create_spell_healing_roll(room_id, sheet_id, playerKey, spell_id, effectIndex, spellSlotLevel)


@app.post("/api/rooms/{room_id}/sheet/{sheet_id}/spells/{spell_id}/rolls/temporary-hit-points")
async def roll_sheet_spell_temporary_hit_points(room_id: str, sheet_id: str, spell_id: str, playerKey: str, effectIndex: int = 0, spellSlotLevel: int | None = None) -> dict[str, Any]:
    return await create_spell_temporary_hit_points_roll(room_id, sheet_id, playerKey, spell_id, effectIndex, spellSlotLevel)


@app.post("/api/rooms/{room_id}/sheet/{sheet_id}/spells/{spell_id}/rolls/effect")
async def roll_sheet_spell_effect(room_id: str, sheet_id: str, spell_id: str, playerKey: str, effectIndex: int = 0, spellSlotLevel: int | None = None, choiceIndex: int | None = None) -> dict[str, Any]:
    return await create_spell_condition_roll(room_id, sheet_id, playerKey, spell_id, effectIndex, spellSlotLevel, choiceIndex)


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

    adjusted = adjust_resource(
        ResourceState(resource.resource, resource.currentUses, resource.maxUses),
        currentUses,
    ).current
    room.resource_uses.setdefault(sheet.tokenId, {})[resource.id] = adjusted
    save_room_to_disk(room)
    await log_roll_note(
        room,
        sheet,
        player,
        resource.name,
        f"Resource adjusted to {adjusted}/{resource.maxUses}",
        DiceType.D20,
        [],
    )
    await broadcast_room_state(room)
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
    if class_type not in SUPPORTED_CLASS_TYPES:
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
    room.max_hit_point_increases.pop(updated_member.id, None)
    room.max_hit_point_reductions.pop(updated_member.id, None)
    room.exhaustion_levels.pop(updated_member.id, None)
    room.condition_overrides.pop(updated_member.id, None)
    room.condition_durations.pop(updated_member.id, None)
    room.condition_removals.pop(updated_member.id, None)
    clear_active_concentration(room, updated_member.id)
    room.damage_resistances.pop(updated_member.id, None)
    room.damage_vulnerabilities.pop(updated_member.id, None)
    room.damage_immunities.pop(updated_member.id, None)
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
    elif parsed_choice_id == ProgressionChoiceId.WIZARD_ABILITY_SCORE_IMPROVEMENT:
        updated_member = update_party_member_config(
            room.id,
            sanitize_asset_id(sheet_id),
            lambda member: apply_member_ability_score_improvement(member, [str(value) for value in values]),
        )
    elif parsed_choice_id == ProgressionChoiceId.FIGHTER_SKILL_PROFICIENCIES:
        updated_member = update_party_member_config(
            room.id,
            sanitize_asset_id(sheet_id),
            lambda member: apply_member_fighter_skill_proficiencies(member, [str(value) for value in values]),
        )
    elif parsed_choice_id == ProgressionChoiceId.ROGUE_SKILL_PROFICIENCIES:
        updated_member = update_party_member_config(
            room.id,
            sanitize_asset_id(sheet_id),
            lambda member: apply_member_rogue_skill_proficiencies(member, [str(value) for value in values]),
        )
    elif parsed_choice_id == ProgressionChoiceId.WIZARD_SKILL_PROFICIENCIES:
        updated_member = update_party_member_config(
            room.id,
            sanitize_asset_id(sheet_id),
            lambda member: apply_member_wizard_skill_proficiencies(member, [str(value) for value in values]),
        )
    elif parsed_choice_id == ProgressionChoiceId.ROGUE_EXPERTISE:
        updated_member = update_party_member_config(
            room.id,
            sanitize_asset_id(sheet_id),
            lambda member: apply_member_rogue_expertise(member, [str(value) for value in values]),
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
    elif parsed_choice_id == ProgressionChoiceId.WIZARD_CANTRIPS:
        updated_member = update_party_member_config(
            room.id,
            sanitize_asset_id(sheet_id),
            lambda member: apply_member_wizard_cantrips(member, [str(value) for value in values]),
        )
    elif parsed_choice_id == ProgressionChoiceId.WIZARD_SPELLBOOK_SPELLS:
        updated_member = update_party_member_config(
            room.id,
            sanitize_asset_id(sheet_id),
            lambda member: apply_member_wizard_spellbook_spells(member, [str(value) for value in values]),
        )
    elif parsed_choice_id == ProgressionChoiceId.WIZARD_PREPARED_SPELLS:
        updated_member = update_party_member_config(
            room.id,
            sanitize_asset_id(sheet_id),
            lambda member: apply_member_wizard_prepared_spells(member, [str(value) for value in values]),
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
            recovered_resources = reset_sheet_resources(room, sheet, rest_type)
            reset_sheet_conditions(room, sheet, rest_type)
            reset_sheet_temporary_hit_points(room, sheet, rest_type)
            reset_sheet_max_hit_point_increases(room, sheet, rest_type)
            reset_sheet_max_hit_point_reductions(room, sheet, rest_type)
            reset_sheet_exhaustion(room, sheet, rest_type)
            if recovered_resources:
                recovery_summary = ", ".join(
                    f"{resource.label} {resource.current}/{resource.maximum}"
                    for resource in recovered_resources
                )
                await log_roll_note(
                    room,
                    sheet,
                    player,
                    enum_label(rest_type),
                    f"Resources recovered: {recovery_summary}",
                    DiceType.D20,
                    [],
                )
    save_room_to_disk(room)
    await broadcast_room_state(room)
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
    if condition_type == ConditionType.EXHAUSTION:
        return await update_sheet_exhaustion(room_id, sheet_id, playerKey, 1 if active else 0)

    previous_active_concentrations = active_concentrations_to_dict(room.active_concentrations)
    next_conditions = updated_conditions(sheet.conditions, condition_type, active)
    updated_member = update_party_member_config(
        room.id,
        sanitize_asset_id(sheet_id),
        lambda member: set_member_conditions(member, next_conditions),
    )

    updated_sheet_id = updated_member.id if updated_member is not None else sheet.tokenId
    room.condition_overrides[updated_sheet_id] = next_conditions
    if active:
        from dnd_board.rules.shared.condition_effects import condition_blocks_all_actions

        room.condition_durations.setdefault(updated_sheet_id, {})[condition_type] = ConditionDuration.MANUAL
        if condition_blocks_all_actions(condition_type):
            clear_active_concentration(room, updated_sheet_id)
    else:
        room.condition_durations.setdefault(updated_sheet_id, {}).pop(condition_type, None)
        room.condition_removals.setdefault(updated_sheet_id, {}).pop(condition_type, None)
        room.suppressed_conditions[updated_sheet_id] = [
            condition for condition in room.suppressed_conditions.get(updated_sheet_id, [])
            if condition != condition_type
        ]
        remove_active_condition_sources(room, updated_sheet_id, condition_type)
    if previous_active_concentrations != active_concentrations_to_dict(room.active_concentrations):
        save_room_to_disk(room)
    updated = get_visible_sheet(room, player, updated_sheet_id)
    return {"roomId": room.id, "sheet": sheet_to_dict(updated) if updated else None}


@app.post("/api/rooms/{room_id}/sheet/{sheet_id}/exhaustion")
async def update_sheet_exhaustion(room_id: str, sheet_id: str, playerKey: str, level: int) -> dict[str, Any]:
    sanitized_room_id = sanitize_room_id(room_id)
    room = get_or_create_room(sanitized_room_id)
    player = Player(id="http-sheet-exhaustion", name="Sheet Exhaustion", player_key=normalize_player_key(playerKey, room.id), websocket=None, room_id=room.id)
    sheet = get_visible_sheet(room, player, sanitize_asset_id(sheet_id))
    if sheet is None:
        raise HTTPException(status_code=404, detail="Sheet not found")
    if not can_control_sheet_roll(player, sheet):
        raise HTTPException(status_code=403, detail="Cannot update this sheet")

    next_level = clamp_int(level, 0, 6)
    updated_sheet_id = sheet.tokenId
    room.exhaustion_levels[updated_sheet_id] = next_level
    if next_level == 0:
        room.exhaustion_levels.pop(updated_sheet_id, None)
    next_conditions = conditions_for_exhaustion_level(room.condition_overrides.get(updated_sheet_id, sheet.conditions), next_level)
    if next_level >= 6 and ConditionType.DEAD not in next_conditions:
        next_conditions = normalized_conditions([*next_conditions, ConditionType.DEAD])
    room.condition_overrides[updated_sheet_id] = next_conditions
    if next_level > 0:
        room.condition_durations.setdefault(updated_sheet_id, {})[ConditionType.EXHAUSTION] = ConditionDuration.MANUAL
    else:
        room.condition_durations.setdefault(updated_sheet_id, {}).pop(ConditionType.EXHAUSTION, None)
    update_party_member_config(room.id, sheet.id, lambda member: set_member_conditions(member, next_conditions))
    save_room_to_disk(room)
    updated = get_visible_sheet(room, player, updated_sheet_id)
    if updated is not None:
        room.hit_points[updated_sheet_id] = updated.hp.current
    return {"roomId": room.id, "sheet": sheet_to_dict(updated) if updated else None}


@app.post("/api/rooms/{room_id}/sheet/{sheet_id}/defenses/{defense}/{damage_type}")
async def update_sheet_damage_defense(room_id: str, sheet_id: str, defense: str, damage_type: str, playerKey: str, active: bool) -> dict[str, Any]:
    sanitized_room_id = sanitize_room_id(room_id)
    sanitized_sheet_id = sanitize_asset_id(sheet_id)
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
    return {"roomId": room.id, "sheet": sheet_to_dict(updated) if updated else None}


@app.post("/api/rooms/{room_id}/rolls/{roll_id}/resolve")
async def resolve_roll(room_id: str, roll_id: str, playerKey: str, targetSheetId: str, preserveRoll: bool = False) -> dict[str, Any]:
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

    resolution_or_prompt = resolve_roll_or_prompt(room, roll, target)
    if isinstance(resolution_or_prompt, ResolutionInterceptorPrompt):
        if not preserveRoll:
            room.pending_rolls.pop(roll_queue_key(roll), None)
        room.pending_resolution_prompts[resolution_or_prompt.id] = resolution_or_prompt
        prompt_data = resolution_interceptor_prompt_to_dict(resolution_or_prompt)
        await broadcast(room, {"type": "resolution_prompt_created", "prompt": prompt_data})
        return {"roomId": room.id, "prompt": prompt_data}

    resolution = resolution_or_prompt
    save_room_if_concentration_changed(room, resolution)
    if not preserveRoll:
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
            "preserveRoll": preserveRoll,
            "resolution": resolution_data,
            "logEntry": roll_log_entry_to_dict(log_entry),
        },
    )
    return {"roomId": room.id, "preserveRoll": preserveRoll, "resolution": resolution_data, "logEntry": roll_log_entry_to_dict(log_entry)}


@app.post("/api/rooms/{room_id}/resolution-prompts/{prompt_id}/respond")
async def respond_to_resolution_prompt(room_id: str, prompt_id: str, playerKey: str, use: bool) -> dict[str, Any]:
    sanitized_room_id = sanitize_room_id(room_id)
    room = get_or_create_room(sanitized_room_id)
    player = Player(id="http-resolution-prompt", name="Prompt", player_key=normalize_player_key(playerKey, room.id), websocket=None, room_id=room.id)
    prompt = room.pending_resolution_prompts.get(sanitize_asset_id(prompt_id))
    if prompt is None:
        raise HTTPException(status_code=404, detail="Resolution prompt not found")
    if not is_dm(player) and prompt.ownerPlayerKey != player.player_key:
        raise HTTPException(status_code=403, detail="Cannot answer another player's prompt")

    target = get_visible_sheet(room, Player(id="prompt-dm", name="DM", player_key="dm", websocket=None, room_id=room.id), prompt.targetSheetId)
    if target is None:
        raise HTTPException(status_code=404, detail="Target sheet not found")

    if prompt.effectExecutionId is not None:
        pending = room.pending_effect_executions.get(prompt.effectExecutionId)
        if pending is None:
            raise HTTPException(status_code=409, detail="Effect execution is no longer active")
        conflicting_participants = pending_execution_conflicts(room, pending)
        if conflicting_participants:
            room.pending_effect_executions.pop(prompt.effectExecutionId, None)
            names = ", ".join(conflicting_participants)
            raise HTTPException(
                status_code=409,
                detail=f"Effect execution canceled because participant state changed: {names}. Roll again.",
            )
        effect_event = pending.active.execution.waitingFor
        if effect_event is None:
            raise HTTPException(status_code=409, detail="Effect execution is not waiting for a response")
        await claim_resolution_prompt(room, prompt, player, target, use)
        pending.ignoredInterceptors.append(resolution_interceptor_key(prompt))
        pending.outcomePrefixes.append(f"{prompt.ownerName} {'uses' if use else 'declines'} {prompt.label}")
        if use:
            live_pending_damage = (
                pending.active.context.pendingDamages.get(effect_event.effectNodeId)
                if effect_event.eventType == ResolutionEventType.DAMAGE_PENDING
                and effect_event.effectNodeId is not None
                else None
            )
            used_roll, used_outcomes, used_response_rolls, canceled_resolution = apply_resolution_interceptor(
                room,
                prompt,
                target,
                modify_damage_roll=live_pending_damage is None,
            )
            pending.outcomePrefixes.extend(used_outcomes)
            pending.responseRolls.extend(used_response_rolls)
            if canceled_resolution is not None:
                room.pending_effect_executions.pop(prompt.effectExecutionId, None)
                resolution_or_prompt: ResolutionResult = attach_resolution_context(
                    canceled_resolution,
                    pending.outcomePrefixes,
                    pending.responseRolls,
                )
            else:
                pending_damage_modifications = [
                    operation
                    for operation in prompt.interaction.operations
                    if isinstance(operation, ModifyPendingDamage)
                ]
                if (
                    effect_event.eventType == ResolutionEventType.DAMAGE_PENDING
                    and effect_event.effectNodeId is not None
                    and pending_damage_modifications
                ):
                    apply_pending_damage_modifications(
                        pending.active.context,
                        effect_event.effectNodeId,
                        pending_damage_modifications,
                        next(
                            (
                                sheet
                                for sheet in all_room_sheets(room)
                                if sheet.id == prompt.ownerSheetId
                            ),
                            target,
                        ),
                    )
                    current_damage = pending.active.context.pendingDamages.get(effect_event.effectNodeId)
                    if current_damage is not None:
                        used_roll = replace(
                            used_roll,
                            pendingEffect=ApplyEffect(current_damage.effect),
                            effectInputs=EffectResolutionInputs(
                                amounts=[EffectAmountInput(EffectNodeId(()), current_damage.currentAmount)]
                            ),
                        )
                updated_amounts = {
                    entry.effectNodeId: entry.amount
                    for entry in (used_roll.effectInputs.amounts if used_roll.effectInputs is not None else [])
                }
                if effect_event.effectNodeId is not None and EffectNodeId(()) in updated_amounts:
                    root_amount = updated_amounts.pop(EffectNodeId(()))
                    updated_amounts.setdefault(effect_event.effectNodeId, root_amount)
                if effect_event.effectNodeId is not None:
                    pending.active.context.update_pending_damage(
                        effect_event.effectNodeId,
                        used_roll.pendingEffect,
                        updated_amounts.get(effect_event.effectNodeId),
                    )
                pending.active.context.amountInputs.update(updated_amounts)
                if effect_event.effectNodeId is not None:
                    pending_damage = pending.active.context.pendingDamages.get(effect_event.effectNodeId)
                    if pending_damage is not None:
                        pending.active.context.amountInputs[effect_event.effectNodeId] = pending_damage.currentAmount
                if effect_event.eventType == ResolutionEventType.SAVE_ROLLED:
                    succeeded = used_roll.damageSaveSucceeded is True
                    roll_outcome = RollOutcome.SUCCESS if succeeded else RollOutcome.FAILURE
                    pending.roll = replace(pending.roll, damageSaveSucceeded=succeeded)
                    pending.active.context.roll = pending.roll
                    if effect_event.effectNodeId is not None:
                        pending.active.context.savingThrowOutcomes[effect_event.effectNodeId] = roll_outcome
                    pending.active.execution.waitingFor = replace(effect_event, rollOutcome=roll_outcome)
                elif effect_event.eventType == ResolutionEventType.ATTACK_ROLLED:
                    natural = resolved_d20(used_roll)
                    hit = natural == 20 or (natural != 1 and used_roll.total >= target.armorClass)
                    roll_outcome = RollOutcome.HIT if hit else RollOutcome.MISS
                    if effect_event.effectNodeId is not None:
                        pending.active.context.attackRollOutcomes[effect_event.effectNodeId] = roll_outcome
                        pending.active.context.attackRollPayloads[effect_event.effectNodeId] = used_roll
                    if used_roll.id == pending.roll.id:
                        pending.roll = replace(
                            pending.roll,
                            dice=used_roll.dice,
                            die=used_roll.die,
                            modifier=used_roll.modifier,
                            modifierBreakdown=used_roll.modifierBreakdown,
                            total=used_roll.total,
                            advantageConditions=used_roll.advantageConditions,
                            disadvantageConditions=used_roll.disadvantageConditions,
                            criticalHit=False,
                        )
                        pending.active.context.roll = pending.roll
                    pending.active.execution.waitingFor = replace(effect_event, rollOutcome=roll_outcome)
                else:
                    pending.active.execution.waitingFor = replace(effect_event, pendingEffect=used_roll.pendingEffect)
                resolution_or_prompt = continue_character_effect_resolution(room, pending, target)
        else:
            resolution_or_prompt = continue_character_effect_resolution(room, pending, target)

        if isinstance(resolution_or_prompt, ResolutionInterceptorPrompt):
            room.pending_resolution_prompts[resolution_or_prompt.id] = resolution_or_prompt
            prompt_data = resolution_interceptor_prompt_to_dict(resolution_or_prompt)
            await broadcast(room, {"type": "resolution_prompt_resolved", "promptId": prompt.id})
            await broadcast(room, {"type": "resolution_prompt_created", "prompt": prompt_data})
            return {"roomId": room.id, "prompt": prompt_data}

        resolution = resolution_or_prompt
        save_room_if_concentration_changed(room, resolution)
        resolution_data = roll_resolution_to_dict(resolution)
        log_entry = append_roll_log_entry(
            room,
            RollLogEntry(
                id=f"log-{resolution.id}",
                entryType=RollLogEntryType.ROLL_RESOLVED,
                createdAt=resolution.createdAt,
                roll=prompt.sourceRoll,
                resolution=resolution,
            ),
        )
        await broadcast(room, {"type": "resolution_prompt_resolved", "promptId": prompt.id})
        await broadcast(room, {"type": "roll_resolved", "rollId": prompt.sourceRoll.id, "tokenId": prompt.sourceRoll.tokenId, "resolution": resolution_data, "logEntry": roll_log_entry_to_dict(log_entry)})
        return {"roomId": room.id, "resolution": resolution_data, "logEntry": roll_log_entry_to_dict(log_entry)}

    response_rolls = list(prompt.responseRolls or [])
    outcome_prefixes = [f"{prompt.ownerName} {'uses' if use else 'declines'} {prompt.label}"]
    next_roll = prompt.pendingRoll
    ignored = [*prompt.ignoredInterceptors, resolution_interceptor_key(prompt)]
    await claim_resolution_prompt(room, prompt, player, target, use)
    if use:
        used_roll, used_outcomes, used_response_rolls, canceled_resolution = apply_resolution_interceptor(room, prompt, target)
        outcome_prefixes.extend(used_outcomes)
        response_rolls.extend(used_response_rolls)
        if canceled_resolution is not None:
            resolution = attach_resolution_context(canceled_resolution, outcome_prefixes, response_rolls)
            resolution_data = roll_resolution_to_dict(resolution)
            log_entry = append_roll_log_entry(
                room,
                RollLogEntry(
                    id=f"log-{resolution.id}",
                    entryType=RollLogEntryType.ROLL_RESOLVED,
                    createdAt=resolution.createdAt,
                    roll=prompt.sourceRoll,
                    resolution=resolution,
                ),
            )
            await broadcast(room, {"type": "resolution_prompt_resolved", "promptId": prompt.id})
            await broadcast(room, {"type": "roll_resolved", "rollId": prompt.sourceRoll.id, "tokenId": prompt.sourceRoll.tokenId, "resolution": resolution_data, "logEntry": roll_log_entry_to_dict(log_entry)})
            return {"roomId": room.id, "resolution": resolution_data, "logEntry": roll_log_entry_to_dict(log_entry)}
        next_roll = used_roll

    resolution_or_prompt = resolve_roll_or_prompt(room, next_roll, target, ignored, response_rolls, outcome_prefixes)
    if isinstance(resolution_or_prompt, ResolutionInterceptorPrompt):
        room.pending_resolution_prompts[resolution_or_prompt.id] = resolution_or_prompt
        prompt_data = resolution_interceptor_prompt_to_dict(resolution_or_prompt)
        await broadcast(room, {"type": "resolution_prompt_resolved", "promptId": prompt.id})
        await broadcast(room, {"type": "resolution_prompt_created", "prompt": prompt_data})
        return {"roomId": room.id, "prompt": prompt_data}

    resolution = resolution_or_prompt
    save_room_if_concentration_changed(room, resolution)
    resolution_data = roll_resolution_to_dict(resolution)
    log_entry = append_roll_log_entry(
        room,
        RollLogEntry(
            id=f"log-{resolution.id}",
            entryType=RollLogEntryType.ROLL_RESOLVED,
            createdAt=resolution.createdAt,
            roll=prompt.sourceRoll,
            resolution=resolution,
        ),
    )
    await broadcast(room, {"type": "resolution_prompt_resolved", "promptId": prompt.id})
    await broadcast(room, {"type": "roll_resolved", "rollId": prompt.sourceRoll.id, "tokenId": prompt.sourceRoll.tokenId, "resolution": resolution_data, "logEntry": roll_log_entry_to_dict(log_entry)})
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
    room.max_hit_point_increases.pop(token_id, None)
    room.max_hit_point_reductions.pop(token_id, None)
    room.exhaustion_levels.pop(token_id, None)
    room.condition_overrides.pop(token_id, None)
    room.suppressed_conditions.pop(token_id, None)
    room.condition_durations.pop(token_id, None)
    room.condition_removals.pop(token_id, None)
    clear_active_concentration(room, token_id)
    room.damage_resistances.pop(token_id, None)
    room.damage_vulnerabilities.pop(token_id, None)
    room.damage_immunities.pop(token_id, None)
    room.ongoing_effects.pop(token_id, None)
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
        pending_resolution_prompts={},
        roll_history=[],
        hit_points={},
        temporary_hit_points={},
        max_hit_point_increases=load_saved_max_hit_point_increases(room_id),
        max_hit_point_reductions=load_saved_max_hit_point_reductions(room_id),
        exhaustion_levels=load_saved_exhaustion_levels(room_id),
        condition_overrides={},
        suppressed_conditions=load_saved_suppressed_conditions(room_id),
        condition_durations={},
        condition_removals={},
        active_concentrations=load_saved_active_concentrations(room_id),
        damage_resistances={},
        damage_vulnerabilities={},
        damage_immunities={},
        resource_uses=load_saved_resource_uses(room_id),
        equipment_slots={},
        ongoing_effects=load_saved_ongoing_effects(room_id),
        scheduled_effects=load_saved_scheduled_effects(room_id),
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
    sheets = visible_sheets(room, player)
    return {
        "type": "sheet_state",
        "roomId": room.id,
        "playerKey": player.player_key,
        "sheets": [sheet_to_dict(sheet) for sheet in sheets],
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
    return sheet


async def create_attack_roll(room_id: str, sheet_id: str, player_key: str, attack_id: str) -> dict[str, Any]:
    room, player, sheet = roll_context(room_id, sheet_id, player_key)
    action = find_attack(sheet, attack_id)
    await assert_roll_activation_allowed(room, sheet, player, action.activation, action.name, "Attack Roll")
    payload = build_combined_attack_roll_payload(sheet, player.player_key, action)
    await consume_action_resources(room, sheet, player, action.resourceCosts, payload)
    return await store_outgoing_roll(room, sheet, payload)


async def create_damage_roll(room_id: str, sheet_id: str, player_key: str, attack_id: str) -> dict[str, Any]:
    room, player, sheet = roll_context(room_id, sheet_id, player_key)
    action = find_attack(sheet, attack_id)
    await assert_roll_activation_allowed(room, sheet, player, action.activation, action.name, "Damage Roll")
    payload = build_damage_roll_payload(sheet, player.player_key, action)
    await consume_action_resources(room, sheet, player, action.resourceCosts, payload)
    return await store_outgoing_roll(room, sheet, payload)


async def create_spell_attack_roll(room_id: str, sheet_id: str, player_key: str, spell_id: str, spell_slot_level: int | None = None) -> dict[str, Any]:
    room, player, sheet = roll_context(room_id, sheet_id, player_key)
    spell = find_spell(sheet, spell_id)
    validate_spell_slot_level(sheet, spell, spell_slot_level)
    from dnd_board.rules.shared.character_effects import first_attack_roll_effect

    if spell.mechanics is None or not any(first_attack_roll_effect(effect) is not None for effect in spell.mechanics.activatedEffects):
        raise HTTPException(status_code=404, detail="Spell attack not found")
    await assert_roll_activation_allowed(room, sheet, player, spell.castingTime, enum_label(spell.name), "Spell Attack")
    await assert_slowed_somatic_spell_cast_allowed(room, sheet, player, spell)
    payload = build_spell_attack_roll_payload(sheet, player.player_key, spell)
    await consume_action_resources(room, sheet, player, spell.resourceCosts or (), payload, spell_slot_level or spell.level)
    return await store_outgoing_roll(room, sheet, payload)


async def create_true_strike_attack_roll(room_id: str, sheet_id: str, player_key: str, spell_id: str, attack_id: str, damage_type_key: str) -> dict[str, Any]:
    room, player, sheet = roll_context(room_id, sheet_id, player_key)
    spell, attack, damage_type = await true_strike_context(room, player, sheet, spell_id, attack_id, damage_type_key)
    await assert_roll_activation_allowed(room, sheet, player, spell.castingTime, enum_label(spell.name), "True Strike Attack")
    await assert_slowed_somatic_spell_cast_allowed(room, sheet, player, spell)
    payload = build_true_strike_attack_roll_payload(sheet, player.player_key, spell, attack, damage_type)
    return await store_outgoing_roll(room, sheet, payload)


async def create_true_strike_damage_roll(room_id: str, sheet_id: str, player_key: str, spell_id: str, attack_id: str, damage_type_key: str) -> dict[str, Any]:
    room, player, sheet = roll_context(room_id, sheet_id, player_key)
    spell, attack, damage_type = await true_strike_context(room, player, sheet, spell_id, attack_id, damage_type_key)
    await assert_roll_activation_allowed(room, sheet, player, spell.castingTime, enum_label(spell.name), "True Strike Damage")
    payload = build_true_strike_damage_roll_payload(sheet, player.player_key, spell, attack, damage_type)
    return await store_outgoing_roll(room, sheet, payload)


async def true_strike_context(room: Room, player: Player, sheet: CharacterSheet, spell_id: str, attack_id: str, damage_type_key: str) -> tuple[SpellEntry, AttackAction, DamageType]:
    spell = find_spell(sheet, spell_id)
    if spell.id != SpellId.TRUE_STRIKE:
        raise HTTPException(status_code=404, detail="True Strike spell not found")
    if not true_strike_weapon_attacks(sheet):
        await log_blocked_roll(room, sheet, player, enum_label(spell.name), "True Strike", "requires a wielded proficient weapon")
        raise HTTPException(status_code=400, detail="True Strike requires a wielded proficient weapon")
    attack = true_strike_weapon_attack(sheet, attack_id)
    if attack is None:
        await log_blocked_roll(room, sheet, player, enum_label(spell.name), "True Strike", "selected weapon is not wielded and proficient")
        raise HTTPException(status_code=404, detail="True Strike weapon attack not found")
    damage_type = enum_value(DamageType, damage_type_key)
    if damage_type is None or damage_type not in {attack.damageType, DamageType.RADIANT}:
        raise HTTPException(status_code=400, detail="Invalid True Strike damage type")
    return spell, attack, damage_type


async def create_spell_damage_roll(room_id: str, sheet_id: str, player_key: str, spell_id: str, effect_index: int = 0, spell_slot_level: int | None = None, instance_index: int | None = None, damage_save_succeeded: bool | None = None, choice_index: int | None = None) -> dict[str, Any]:
    room, player, sheet = roll_context(room_id, sheet_id, player_key)
    spell = find_spell(sheet, spell_id)
    validate_spell_slot_level(sheet, spell, spell_slot_level)
    await assert_roll_activation_allowed(room, sheet, player, spell.castingTime, enum_label(spell.name), "Spell Damage")
    if spell_damage_roll_requires_cast_check(spell, effect_index):
        await assert_slowed_somatic_spell_cast_allowed(room, sheet, player, spell)
    try:
        payload = build_spell_damage_roll_payload(sheet, player.player_key, spell, effect_index, spell_slot_level, instance_index, damage_save_succeeded, choice_index)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    await consume_action_resources(room, sheet, player, spell.resourceCosts or (), payload, spell_slot_level or spell.level)
    return await store_outgoing_roll(room, sheet, payload)


async def create_spell_healing_roll(room_id: str, sheet_id: str, player_key: str, spell_id: str, effect_index: int = 0, spell_slot_level: int | None = None) -> dict[str, Any]:
    room, player, sheet = roll_context(room_id, sheet_id, player_key)
    spell = find_spell(sheet, spell_id)
    validate_spell_slot_level(sheet, spell, spell_slot_level)
    await assert_roll_activation_allowed(room, sheet, player, spell.castingTime, enum_label(spell.name), "Spell Healing")
    await assert_slowed_somatic_spell_cast_allowed(room, sheet, player, spell)
    try:
        payload = build_spell_healing_roll_payload(sheet, player.player_key, spell, effect_index, spell_slot_level)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    await consume_action_resources(room, sheet, player, spell.resourceCosts or (), payload, spell_slot_level or spell.level)
    return await store_outgoing_roll(room, sheet, payload)


async def create_spell_temporary_hit_points_roll(room_id: str, sheet_id: str, player_key: str, spell_id: str, effect_index: int = 0, spell_slot_level: int | None = None) -> dict[str, Any]:
    room, player, sheet = roll_context(room_id, sheet_id, player_key)
    spell = find_spell(sheet, spell_id)
    validate_spell_slot_level(sheet, spell, spell_slot_level)
    await assert_roll_activation_allowed(room, sheet, player, spell.castingTime, enum_label(spell.name), "Temporary Hit Points")
    await assert_slowed_somatic_spell_cast_allowed(room, sheet, player, spell)
    try:
        payload = build_spell_temporary_hit_points_roll_payload(sheet, player.player_key, spell, effect_index, spell_slot_level)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    await consume_action_resources(room, sheet, player, spell.resourceCosts or (), payload, spell_slot_level or spell.level)
    return await store_outgoing_roll(room, sheet, payload)


async def create_spell_condition_roll(room_id: str, sheet_id: str, player_key: str, spell_id: str, effect_index: int = 0, spell_slot_level: int | None = None, choice_index: int | None = None) -> dict[str, Any]:
    room, player, sheet = roll_context(room_id, sheet_id, player_key)
    spell = find_spell(sheet, spell_id)
    validate_spell_slot_level(sheet, spell, spell_slot_level)
    if spell.id == SpellId.SHILLELAGH and not shillelagh_weapon_attacks(sheet):
        await log_blocked_roll(room, sheet, player, enum_label(spell.name), "Shillelagh", "requires a wielded proficient Club or Quarterstaff")
        raise HTTPException(status_code=400, detail="Shillelagh requires a wielded proficient Club or Quarterstaff")
    await assert_roll_activation_allowed(room, sheet, player, spell.castingTime, enum_label(spell.name), "Spell Effect")
    await assert_slowed_somatic_spell_cast_allowed(room, sheet, player, spell)
    try:
        payload = build_spell_condition_roll_payload(
            sheet,
            player.player_key,
            spell,
            effect_index,
            choice_index,
        )
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    await consume_action_resources(room, sheet, player, spell.resourceCosts or (), payload, spell_slot_level or spell.level)
    return await store_outgoing_roll(room, sheet, payload)


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

    await assert_roll_activation_allowed(room, sheet, player, action.activation or resource.activation, resource.name, enum_label(action.name))
    source = RollSource(section=SheetSectionType.RESOURCES, sourceId=resource.id, actionId=enum_key(action.id))
    payload = build_roll_action_payload(sheet, player.player_key, source, action, source_label=resource.name)
    await consume_action_resources(room, sheet, player, action.resourceCosts, payload)
    return await store_outgoing_roll(room, sheet, payload)


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

    await assert_roll_activation_allowed(room, sheet, player, action.activation or ability.activation, ability.source, enum_label(action.name))
    source = RollSource(section=SheetSectionType.ABILITIES, sourceId=ability.id, actionId=enum_key(action.id))
    payload = build_roll_action_payload(sheet, player.player_key, source, action, source_label=ability.source)
    await consume_action_resources(room, sheet, player, action.resourceCosts, payload)
    return await store_outgoing_roll(room, sheet, payload)


async def create_ad_hoc_dice_roll(room_id: str, player_key: str, dice: str, count: int) -> dict[str, Any]:
    sanitized_room_id = sanitize_room_id(room_id)
    room = get_or_create_room(sanitized_room_id)
    player = Player(id="http-dice-roller", name="Dice Roller", player_key=normalize_player_key(player_key, room.id), websocket=None, room_id=room.id)
    dice_type = enum_value(DiceType, dice)
    if dice_type is None:
        raise HTTPException(status_code=400, detail="Invalid dice type")
    dice_count = clamp_int(count, 1, 20)
    rolls = [random.randint(1, dice_type.value) for _ in range(dice_count)]
    created_at = time_ns()
    payload = RollPayload(
        id=f"roll-{created_at}",
        sheetId=player.player_key,
        tokenId=player.player_key,
        roller=player.player_key,
        source=RollSource(section=SheetSectionType.DICE_ROLLER, sourceId=enum_key(dice_type), actionId="roll"),
        sourceLabel="Dice Roller",
        resolution=RollResolutionMode.NONE,
        label=f"{dice_count}{enum_key(dice_type)}",
        iconUrl=None,
        dice=rolls,
        diceType=dice_type,
        die=f"{dice_count}{enum_key(dice_type)}",
        modifier=0,
        modifierBreakdown=[],
        total=sum(rolls),
        createdAt=created_at,
    )
    log_entry = append_roll_log_entry(
        room,
        RollLogEntry(
            id=f"log-{payload.id}",
            entryType=RollLogEntryType.ROLL_CREATED,
            createdAt=payload.createdAt,
            roll=payload,
        ),
    )
    await broadcast(room, {"type": "roll_logged", "roll": roll_payload_to_dict(payload), "logEntry": roll_log_entry_to_dict(log_entry)})
    return {"roomId": room.id, "roll": roll_payload_to_dict(payload), "logEntry": roll_log_entry_to_dict(log_entry)}


async def store_outgoing_roll(room: Room, sheet: CharacterSheet, payload: RollPayload) -> dict[str, Any]:
    response = await store_roll(room, payload)
    clear_conditions_after_outgoing_roll(room, sheet, payload)
    if payload.resourcesSpent:
        save_room_to_disk(room)
        await broadcast_room_state(room)
    return response


def clear_conditions_after_outgoing_roll(room: Room, sheet: CharacterSheet, roll: RollPayload) -> bool:
    from dnd_board.rules.shared.condition_effects import conditions_ending_on_event
    from dnd_board.rules.shared.character_effects import ongoing_effects_after_ending

    is_spell = roll.source.section == SheetSectionType.SPELLS
    is_attack = roll.source.actionId == "attackVsArmorClass" or roll.resolution == RollResolutionMode.ATTACK_VS_ARMOR_CLASS
    deals_damage = roll.resolution == RollResolutionMode.APPLY_DAMAGE
    ended = set(
        conditions_ending_on_event(sheet.conditions, ResolutionEventType.SPELL_DECLARED, is_spell=is_spell)
        + conditions_ending_on_event(sheet.conditions, ResolutionEventType.ACTION_DECLARED, is_attack=is_attack)
        + conditions_ending_on_event(sheet.conditions, ResolutionEventType.DAMAGE_APPLIED, deals_damage=deals_damage)
    )
    active_effects = list(room.ongoing_effects.get(sheet.id, []))
    remaining_effects = active_effects
    if is_spell:
        remaining_effects = ongoing_effects_after_ending(remaining_effects, EndingConditionType.OWNER_CASTS_SPELL, target_sheet_id=sheet.id)
    if is_attack:
        remaining_effects = ongoing_effects_after_ending(remaining_effects, EndingConditionType.OWNER_ATTACKS, target_sheet_id=sheet.id)
    if deals_damage:
        remaining_effects = ongoing_effects_after_ending(remaining_effects, EndingConditionType.OWNER_DEALS_DAMAGE, target_sheet_id=sheet.id)
    if not ended and remaining_effects == active_effects:
        return False

    next_conditions = [condition for condition in sheet.conditions if condition not in ended]
    room.condition_overrides[sheet.tokenId] = next_conditions
    for condition in ended:
        room.condition_durations.setdefault(sheet.tokenId, {}).pop(condition, None)
        room.condition_removals.setdefault(sheet.tokenId, {}).pop(condition, None)
    room.suppressed_conditions[sheet.tokenId] = [
        condition for condition in room.suppressed_conditions.get(sheet.tokenId, [])
        if condition not in ended
    ]
    update_party_member_config(room.id, sheet.id, lambda member: set_member_conditions(member, next_conditions))
    if remaining_effects != active_effects:
        room.ongoing_effects[sheet.id] = remaining_effects
        save_room_to_disk(room)
    return True


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


def find_spell(sheet: CharacterSheet, spell_id: str) -> SpellEntry:
    sanitized_spell_id = sanitize_asset_id(spell_id)
    spell = next((candidate for candidate in sheet.spells if sanitize_asset_id(enum_key(candidate.id)) == sanitized_spell_id), None)
    if spell is None:
        raise HTTPException(status_code=404, detail="Spell not found")
    return spell


async def assert_roll_activation_allowed(
    room: Room,
    sheet: CharacterSheet,
    player: Player,
    activation: TimeEconomy | None,
    source_label: str,
    roll_label: str,
) -> None:
    from dnd_board.rules.shared.condition_effects import activation_blocking_condition

    blocking_condition = activation_blocking_condition(sheet.conditions, activation)
    if blocking_condition is not None:
        scope = "Reactions" if activation == TimeEconomy.REACTION and blocking_condition == ConditionType.SLOWED else "Actions, Bonus Actions, and Reactions"
        await log_blocked_roll(room, sheet, player, source_label, roll_label, f"{enum_label(blocking_condition)} prevents {scope}")
        if scope == "Reactions":
            raise HTTPException(status_code=400, detail=f"{enum_label(blocking_condition)} creatures cannot take Reactions")
        raise HTTPException(status_code=400, detail=f"{enum_label(blocking_condition)} creatures cannot take Actions, Bonus Actions, or Reactions")


async def assert_slowed_somatic_spell_cast_allowed(room: Room, sheet: CharacterSheet, player: Player, spell: SpellEntry) -> None:
    from dnd_board.rules.shared.condition_effects import action_failure_chance

    failure = action_failure_chance(sheet.conditions, spell.castingTime, spell.components)
    if failure is None:
        return
    condition, chance = failure
    check = random.randint(1, chance.denominator)
    spell_label = enum_label(spell.name)
    if check <= chance.numerator:
        await log_blocked_roll(room, sheet, player, spell_label, "Spell Cast", f"{enum_label(condition)} somatic delay fails on 1d{chance.denominator} ({check})")
        raise HTTPException(status_code=400, detail=f"{enum_label(condition)} somatic spell failed")
    await log_roll_note(room, sheet, player, spell_label, f"{enum_label(condition)} somatic check succeeds on 1d{chance.denominator} ({check}); spell continues", DiceType.D4, [check])


def spell_damage_roll_requires_cast_check(spell: SpellEntry, effect_index: int) -> bool:
    return spell.mechanics is not None


def validate_spell_slot_level(sheet: CharacterSheet, spell: SpellEntry, spell_slot_level: int | None) -> None:
    if spell_slot_level is None or spell.level == 0:
        return
    if spell_slot_level < spell.level:
        raise HTTPException(status_code=400, detail="Spell slot level is too low")
    if spell_slot_level not in {resource.spellSlotLevel for resource in sheet.resources if resource.spellSlotLevel is not None}:
        raise HTTPException(status_code=400, detail="Spell slot level is not available")


async def store_roll(room: Room, payload: RollPayload) -> dict[str, Any]:
    if roll_resolves_immediately(payload):
        target = source_sheet_for_roll(room, payload)
        if target is None:
            raise HTTPException(status_code=404, detail="Sheet not found")
        resolution = resolve_roll_against_target(room, payload, target)
        save_room_if_concentration_changed(room, resolution)
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
    return roll.resolution == RollResolutionMode.HEAL_SELF and roll.source.section != SheetSectionType.SPELLS


async def log_blocked_roll(room: Room, sheet: CharacterSheet, player: Player, source_label: str, roll_label: str, reason: str) -> RollLogEntry:
    return await log_roll_note(
        room,
        sheet,
        player,
        source_label,
        f"{roll_label} blocked: {reason}",
        DiceType.D20,
        [],
        entry_type=RollLogEntryType.ROLL_BLOCKED,
        message_type="roll_blocked",
    )


async def log_roll_note(
    room: Room,
    sheet: CharacterSheet,
    player: Player,
    source_label: str,
    label: str,
    dice_type: DiceType,
    dice: list[int],
    entry_type: RollLogEntryType = RollLogEntryType.ROLL_CREATED,
    message_type: str = "roll_logged",
) -> RollLogEntry:
    created_at = time_ns()
    payload = RollPayload(
        id=f"roll-{created_at}",
        sheetId=sheet.id,
        tokenId=sheet.tokenId,
        roller=player.player_key,
        source=RollSource(section=SheetSectionType.ABILITIES, sourceId=sanitize_identifier(source_label), actionId="log"),
        sourceLabel=source_label,
        resolution=RollResolutionMode.NONE,
        label=label,
        iconUrl=None,
        dice=dice,
        diceType=dice_type,
        die=enum_key(dice_type),
        modifier=0,
        modifierBreakdown=[],
        total=sum(dice),
        createdAt=created_at,
    )
    log_entry = append_roll_log_entry(
        room,
        RollLogEntry(
            id=f"log-{payload.id}",
            entryType=entry_type,
            createdAt=payload.createdAt,
            roll=payload,
        ),
    )
    await broadcast(room, {"type": message_type, "logEntry": roll_log_entry_to_dict(log_entry)})
    return log_entry


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


def reset_sheet_resources(room: Room, sheet: CharacterSheet, rest_type: RestType) -> list[ResourceUpdate]:
    recovery_trigger = (
        ResourceRecoveryTrigger.SHORT_REST
        if rest_type == RestType.SHORT_REST
        else ResourceRecoveryTrigger.LONG_REST
    )
    recovery_definitions = dict(RESOURCE_DEFINITIONS)
    for resource in sheet.resources:
        recovery_definitions[resource.resource] = ResourceDefinition(
            ResourceKey(resource.resource, resource.kind),
            resource.name,
            resource.recoveries,
        )
    recovered_states = recover_resources(
        [ResourceState(resource.resource, resource.currentUses, resource.maxUses) for resource in sheet.resources],
        recovery_definitions,
        recovery_trigger,
    )
    refreshed_resources = {
        resource.id: recovered.current
        for resource, recovered in zip(sheet.resources, recovered_states)
        if recovered.current != resource.currentUses
    }
    if not refreshed_resources:
        return []
    room.resource_uses.setdefault(sheet.tokenId, {}).update(refreshed_resources)
    return [
        ResourceUpdate(resource.resource, resource.name, refreshed_resources[resource.id], resource.maxUses)
        for resource in sheet.resources
        if resource.id in refreshed_resources
    ]


def reset_sheet_conditions(room: Room, sheet: CharacterSheet, rest_type: RestType) -> None:
    durations = room.condition_durations.get(sheet.tokenId, {})
    expired = {condition for condition, duration in durations.items() if condition_clears_on_rest(duration, rest_type)}
    if expired:
        next_conditions = [condition for condition in sheet.conditions if condition not in expired]
        room.condition_overrides[sheet.tokenId] = next_conditions
        for condition in expired:
            durations.pop(condition, None)
            room.condition_removals.setdefault(sheet.tokenId, {}).pop(condition, None)
        room.suppressed_conditions[sheet.tokenId] = [
            condition for condition in room.suppressed_conditions.get(sheet.tokenId, [])
            if condition not in expired
        ]
        update_party_member_config(room.id, sheet.id, lambda member: set_member_conditions(member, next_conditions))

    active_effects = room.ongoing_effects.get(sheet.tokenId, [])
    expiring_duration_types = {EffectDurationType.UNTIL_SHORT_REST, EffectDurationType.UNTIL_LONG_REST}
    if rest_type == RestType.SHORT_REST:
        expiring_duration_types.remove(EffectDurationType.UNTIL_LONG_REST)
    remaining_effects = [
        active
        for active in active_effects
        if active.effect.duration.durationType not in expiring_duration_types
    ]
    if remaining_effects != active_effects:
        room.ongoing_effects[sheet.tokenId] = remaining_effects


def condition_clears_on_rest(condition_duration: ConditionDuration, rest_type: RestType) -> bool:
    if condition_duration == ConditionDuration.UNTIL_SHORT_REST:
        return rest_type in {RestType.SHORT_REST, RestType.LONG_REST}
    if condition_duration == ConditionDuration.UNTIL_LONG_REST:
        return rest_type == RestType.LONG_REST
    return False


def reset_sheet_temporary_hit_points(room: Room, sheet: CharacterSheet, rest_type: RestType) -> None:
    if rest_type == RestType.LONG_REST:
        room.temporary_hit_points.pop(sheet.tokenId, None)


def reset_sheet_max_hit_point_reductions(room: Room, sheet: CharacterSheet, rest_type: RestType) -> None:
    reductions = room.max_hit_point_reductions.get(sheet.tokenId, [])
    remaining = [reduction for reduction in reductions if not reset_applies_to_rest(reduction.reset, rest_type)]
    if remaining:
        room.max_hit_point_reductions[sheet.tokenId] = remaining
        return
    room.max_hit_point_reductions.pop(sheet.tokenId, None)


def reset_applies_to_rest(reset: RestType, rest_type: RestType) -> bool:
    if reset == RestType.NONE:
        return False
    if rest_type == RestType.LONG_REST:
        return reset in {RestType.SHORT_REST, RestType.LONG_REST}
    return reset == RestType.SHORT_REST


def reset_sheet_max_hit_point_increases(room: Room, sheet: CharacterSheet, rest_type: RestType) -> None:
    if rest_type != RestType.LONG_REST:
        return
    room.max_hit_point_increases.pop(sheet.tokenId, None)


def reset_sheet_exhaustion(room: Room, sheet: CharacterSheet, rest_type: RestType) -> None:
    if rest_type != RestType.LONG_REST:
        return
    current_level = room.exhaustion_levels.get(sheet.tokenId, sheet.exhaustionLevel)
    current_hp = sheet.hp.current
    next_level = max(0, current_level - 1)
    if next_level > 0:
        room.exhaustion_levels[sheet.tokenId] = next_level
    else:
        room.exhaustion_levels.pop(sheet.tokenId, None)
    next_conditions = conditions_for_exhaustion_level(room.condition_overrides.get(sheet.tokenId, sheet.conditions), next_level)
    room.condition_overrides[sheet.tokenId] = next_conditions
    room.hit_points[sheet.tokenId] = current_hp
    update_party_member_config(room.id, sheet.id, lambda member: set_member_conditions(member, next_conditions))


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


def conditions_for_exhaustion_level(conditions: list[ConditionType], exhaustion_level: int) -> list[ConditionType]:
    next_conditions = [condition for condition in conditions if condition != ConditionType.EXHAUSTION]
    if exhaustion_level > 0:
        next_conditions.append(ConditionType.EXHAUSTION)
    return normalized_conditions(next_conditions)


def resolved_resource_costs(costs: tuple[ResourceCost, ...], spell_slot_level: int | None = None) -> tuple[ResourceCost, ...]:
    return tuple(
        ResourceCost(spell_slot_resource_id(spell_slot_level), cost.amount)
        if cost.resource == ResourceId.SPELL_SLOT and spell_slot_level is not None
        else cost
        for cost in costs
    )


async def consume_action_resources(
    room: Room,
    sheet: CharacterSheet,
    player: Player,
    costs: tuple[ResourceCost, ...],
    payload: RollPayload,
    spell_slot_level: int | None = None,
) -> list[ResourceUpdate]:
    resolved_costs = resolved_resource_costs(costs, spell_slot_level)
    if not resolved_costs:
        return []
    if any(cost.resource == ResourceId.SPELL_SLOT for cost in resolved_costs):
        raise HTTPException(status_code=400, detail="A spell-slot cost requires a selected slot level")

    resources_by_id = {
        resource.resource: resource
        for resource in sheet.resources
    }
    states = [
        ResourceState(resource_id, resource.currentUses, resource.maxUses)
        for resource_id, resource in resources_by_id.items()
    ]
    try:
        updated_states = spend_resources(states, resolved_costs)
    except InsufficientResourceError as error:
        await log_blocked_roll(room, sheet, player, payload.sourceLabel, payload.label, str(error))
        raise HTTPException(status_code=409, detail=str(error)) from error

    previous_by_id = {state.resource: state for state in states}
    spent: list[ResourceUpdate] = []
    for state in updated_states:
        previous = previous_by_id[state.resource]
        if state.current == previous.current:
            continue
        tracker = resources_by_id[state.resource]
        room.resource_uses.setdefault(sheet.tokenId, {})[tracker.id] = state.current
        spent.append(ResourceUpdate(state.resource, tracker.name, state.current, state.maximum))
    payload.resourcesSpent = spent or None
    return spent


async def claim_resolution_prompt(
    room: Room,
    prompt: ResolutionInterceptorPrompt,
    player: Player,
    target: CharacterSheet,
    use: bool,
) -> None:
    if room.pending_resolution_prompts.get(prompt.id) is not prompt:
        raise HTTPException(status_code=409, detail="Resolution prompt has already been answered")

    costs = prompt.interaction.resourceCosts
    owner = next((sheet for sheet in all_room_sheets(room) if sheet.id == prompt.ownerSheetId), target)
    updates: list[ResourceUpdate] = []
    if use and costs:
        resource_payload = replace(
            prompt.pendingRoll,
            sourceLabel=prompt.label,
            label=prompt.useLabel,
            resourcesSpent=None,
        )
        updates = await consume_action_resources(room, owner, player, costs, resource_payload)

    # Claim the prompt before broadcasting resource changes. Failed payment raises
    # above and deliberately leaves the prompt available for another response.
    if room.pending_resolution_prompts.get(prompt.id) is not prompt:
        raise HTTPException(status_code=409, detail="Resolution prompt has already been answered")
    room.pending_resolution_prompts.pop(prompt.id)
    if not updates:
        return
    save_room_to_disk(room)
    await broadcast_room_state(room)
    summary = ", ".join(f"{update.label} {update.current}/{update.maximum}" for update in updates)
    await log_roll_note(room, owner, player, prompt.label, f"Resources spent: {summary}", DiceType.D20, [])


def roll_queue_key(roll: RollPayload) -> tuple[str, str, str, str]:
    return (roll.tokenId, enum_key(roll.source.section), roll.source.sourceId, roll.source.actionId)


def remove_pending_rolls_for_token(room: Room, token_id: str) -> None:
    for key in [key for key, roll in room.pending_rolls.items() if roll.tokenId == token_id]:
        room.pending_rolls.pop(key, None)


ResolutionResult = RollResolution | ResolutionInterceptorPrompt


def resolve_roll_or_prompt(
    room: Room,
    roll: RollPayload,
    target: CharacterSheet,
    ignored_interceptors: list[str] | None = None,
    response_rolls: list[RollPayload] | None = None,
    outcome_prefixes: list[str] | None = None,
) -> ResolutionResult:
    ignored = set(ignored_interceptors or [])
    prefixes = list(outcome_prefixes or [])
    pre_response_rolls = list(response_rolls or [])

    working_roll = attack_roll_with_target_condition_modifiers(roll, target)
    working_roll, contest_outcome, contest_rolls = resolve_contested_check_for_roll(room, working_roll, target)
    if contest_outcome is not None:
        prefixes.append(contest_outcome)
        pre_response_rolls.extend(contest_rolls)

    if working_roll.pendingEffect is not None:
        source = source_sheet_for_roll(room, working_roll)
        active = PendingCharacterResolution(
            active=start_character_effect_execution(
                working_roll,
                target,
                source,
            ),
            roll=working_roll,
            targetSheetId=target.id,
            responseRolls=pre_response_rolls,
            outcomePrefixes=prefixes,
            ignoredInterceptors=list(ignored),
            participantSnapshots={
                sheet.id: character_runtime_snapshot(sheet)
                for sheet in (target, source)
                if sheet is not None
            },
        )
        return continue_character_effect_resolution(room, active, target)

    for response_roll in pre_response_rolls:
        room.pending_rolls[roll_queue_key(response_roll)] = response_roll
    resolution = resolve_roll_against_target(room, working_roll, target)
    return attach_resolution_context(resolution, prefixes, pre_response_rolls)


def continue_character_effect_resolution(
    room: Room,
    pending: PendingCharacterResolution,
    target: CharacterSheet,
    response: ResolutionEventResponse | None = None,
) -> ResolutionResult:
    while True:
        advanced = advance_character_effect_execution(pending.active, response)
        response = None
        if isinstance(advanced, ResolvedCharacterEffect):
            room.pending_effect_executions.pop(pending.active.execution.resolutionId.value, None)
            scheduled_state_changed = bool(pending.touchedScheduledTargets)
            for sheet_id in pending.touchedScheduledTargets:
                remaining = pending.scheduledEffectStates.get(sheet_id, [])
                if remaining:
                    room.scheduled_effects[sheet_id] = remaining
                else:
                    room.scheduled_effects.pop(sheet_id, None)
            for response_roll in pending.responseRolls:
                room.pending_rolls[roll_queue_key(response_roll)] = response_roll
            primary_target = pending.active.context.sheets[pending.targetSheetId]
            resolution = resolve_roll_against_target(room, pending.roll, primary_target, advanced)
            if scheduled_state_changed:
                save_room_to_disk(room)
            return attach_resolution_context(resolution, pending.outcomePrefixes, pending.responseRolls)

        current_target = pending.active.context.current_target()
        current_source = pending.active.context.source or current_target
        pending_damage = (
            pending.active.context.pendingDamages.get(advanced.effectNodeId)
            if advanced.effectNodeId is not None
            else None
        )
        event_amount = (
            pending_damage.currentAmount
            if pending_damage is not None
            else pending.active.context.amountInputs.get(advanced.effectNodeId)
            if advanced.effectNodeId is not None
            else None
        )
        event_effect = (
            ApplyEffect(replace(pending_damage.effect, amount=FixedAmount(pending_damage.currentAmount), scaling=[]))
            if advanced.eventType == ResolutionEventType.DAMAGE_PENDING and pending_damage is not None
            else advanced.pendingEffect
        )
        if event_effect is not advanced.pendingEffect:
            advanced = replace(advanced, pendingEffect=event_effect)
            pending.active.execution.waitingFor = advanced
        if (
            advanced.eventType == ResolutionEventType.ATTACK_ROLLED
            and advanced.rollOutcome is None
            and advanced.effectNodeId is not None
            and isinstance(advanced.pendingEffect, AttackRollEffect)
        ):
            attack_roll = runtime_attack_roll_for_effect(
                pending.roll,
                current_source,
                current_target,
                advanced.effectNodeId,
                advanced.pendingEffect.attack,
            )
            natural = resolved_d20(attack_roll)
            roll_outcome = RollOutcome.HIT if natural == 20 or (natural != 1 and attack_roll.total >= current_target.armorClass) else RollOutcome.MISS
            pending.active.context.attackRollPayloads[advanced.effectNodeId] = attack_roll
            pending.active.context.attackRollOutcomes[advanced.effectNodeId] = roll_outcome
            pending.responseRolls.append(attack_roll)
            advanced = replace(advanced, rollOutcome=roll_outcome)
            pending.active.execution.waitingFor = advanced
        if (
            advanced.eventType == ResolutionEventType.SAVE_ROLLED
            and advanced.rollOutcome is None
            and advanced.effectNodeId is not None
            and isinstance(advanced.pendingEffect, SavingThrowEffect)
        ):
            saving_throw = advanced.pendingEffect.savingThrow
            save_dc = (
                pending.roll.damageSaveDc
                if saving_throw.difficultyClass.calculation == DifficultyClassType.SOURCE_SPELL_SAVE_DC
                and pending.roll.damageSaveDc is not None
                else effect_saving_throw_dc(current_source, saving_throw)
            )
            configured = replace(
                pending.roll,
                damageSavingThrow=saving_throw.ability,
                damageSaveDc=save_dc,
                damageSaveOutcome=pending.roll.damageSaveOutcome or SpellSaveOutcome.PARTIAL,
                damageSaveSucceeded=None,
            )
            save_outcome, save_roll, resolved_roll = resolve_damage_save_for_roll(configured, current_target)
            roll_outcome = RollOutcome.SUCCESS if resolved_roll.damageSaveSucceeded else RollOutcome.FAILURE
            inputs = resolved_roll.effectInputs or EffectResolutionInputs()
            pending.roll = replace(
                resolved_roll,
                effectInputs=replace(
                    inputs,
                    rolls=[*inputs.rolls, EffectRollInput(advanced.effectNodeId, roll_outcome)],
                ),
            )
            pending.active.context.roll = pending.roll
            pending.active.context.savingThrowOutcomes[advanced.effectNodeId] = roll_outcome
            if save_outcome:
                pending.outcomePrefixes.append(save_outcome)
            if save_roll is not None:
                pending.responseRolls.append(save_roll)
            advanced = replace(advanced, rollOutcome=roll_outcome)
            pending.active.execution.waitingFor = advanced
        event_key = InteractionEventKey(advanced.eventType, advanced.effectNodeId)
        if pending.interactionEvent != event_key:
            pending.interactionEvent = event_key
            pending.ignoredInterceptors.clear()
        node_roll = (
            pending.active.context.attackRollPayloads.get(advanced.effectNodeId, pending.roll)
            if advanced.effectNodeId is not None
            else pending.roll
        )
        event_roll = replace(
            node_roll,
            sheetId=current_source.id,
            tokenId=current_source.tokenId,
            pendingEffect=event_effect,
            effectInputs=(
                EffectResolutionInputs(amounts=[EffectAmountInput(EffectNodeId(()), event_amount)])
                if event_amount is not None
                else pending.roll.effectInputs
            ),
        )
        if advanced.eventType == ResolutionEventType.SAVE_ROLLED and isinstance(advanced.pendingEffect, SavingThrowEffect):
            event_roll = replace(
                event_roll,
                damageSavingThrow=advanced.pendingEffect.savingThrow.ability,
                damageSaveDc=(
                    pending.roll.damageSaveDc
                    if pending.roll.damageSaveDc is not None
                    else effect_saving_throw_dc(current_source, advanced.pendingEffect.savingThrow)
                ),
                damageSaveSucceeded=advanced.rollOutcome == RollOutcome.SUCCESS,
            )
        prompt = resolution_prompt_for_effect_event(
            room,
            pending.roll,
            event_roll,
            current_target,
            advanced,
            set(pending.ignoredInterceptors),
            pending.responseRolls,
        )
        if prompt is not None:
            execution_id = pending.active.execution.resolutionId.value
            room.pending_effect_executions[execution_id] = pending
            return replace(prompt, effectExecutionId=execution_id)

        if advanced.eventType == ResolutionEventType.ATTACK_ROLLED and advanced.effectNodeId is not None:
            finalize_attack_roll_event(pending, advanced.effectNodeId)
        response = default_effect_event_response(advanced)
        if event_key not in pending.dispatchedEvents:
            pending.dispatchedEvents.add(event_key)
            response = replace(
                response,
                boundEffects=bound_effect_dispatches_for_event(room, pending, advanced),
            )


def character_runtime_snapshot(sheet: CharacterSheet) -> CharacterRuntimeSnapshot:
    return CharacterRuntimeSnapshot(
        hitPoints=sheet.hp,
        conditions=tuple(sheet.conditions),
        suppressedConditions=tuple(sheet.suppressedConditions),
        damageResistances=tuple(sheet.damageResistances),
        damageVulnerabilities=tuple(sheet.damageVulnerabilities),
        damageImmunities=tuple(sheet.damageImmunities),
        ongoingEffects=tuple(sheet.ongoingEffects),
    )


def pending_execution_conflicts(room: Room, pending: PendingCharacterResolution) -> list[str]:
    dm = Player(id="execution-conflict", name="DM", player_key="dm", websocket=None, room_id=room.id)
    conflicts: list[str] = []
    for sheet_id, snapshot in pending.participantSnapshots.items():
        sheet = get_visible_sheet(room, dm, sheet_id)
        if sheet is None or character_runtime_snapshot(sheet) != snapshot:
            conflicts.append(sheet.name if sheet is not None else sheet_id)
    return conflicts


def runtime_attack_roll_for_effect(
    parent_roll: RollPayload,
    source: CharacterSheet,
    target: CharacterSheet,
    node_id: EffectNodeId,
    attack: AttackRoll,
) -> RollPayload:
    ability = attack.ability
    if ability is None and attack.attackType == AttackRollType.SPELL:
        source_spell = next(
            (
                spell for spell in [*source.spells, *source.spellbook]
                if enum_key(spell.id) == parent_roll.source.sourceId
            ),
            None,
        )
        if source_spell is not None:
            ability = spell_casting_ability(source, source_spell)
    ability = ability or AbilityType.STRENGTH
    action = AttackAction(
        id=f"effect-attack-{'-'.join(str(part) for part in node_id.path)}",
        name="Triggered Attack",
        ability=ability,
        damageDiceCount=0,
        damageDiceType=DiceType.D4,
        damageType=parent_roll.damageType or DamageType.FORCE,
    )
    attack_roll = build_attack_roll_payload(source, parent_roll.roller, action)
    attack_roll = replace(
        attack_roll,
        source=parent_roll.source,
        sourceLabel=parent_roll.sourceLabel,
        label="Spell Attack" if attack.attackType == AttackRollType.SPELL else "Attack Roll",
    )
    return attack_roll_with_target_condition_modifiers(attack_roll, target)


def finalize_attack_roll_event(pending: PendingCharacterResolution, node_id: EffectNodeId) -> None:
    attack_roll = pending.active.context.attackRollPayloads.get(node_id)
    if attack_roll is None:
        return
    finalized = attack_roll_with_critical_damage(attack_roll)
    if resolved_d20(finalized) == 20:
        finalized = replace(finalized, criticalHit=True)
        pending.active.context.criticalAttackNodes.add(node_id)
        pending.active.context.criticalDamagePreparedNodes.update(
            effect_node_id
            for component in finalized.damageComponents or []
            for effect_node_id in component.effectNodeIds or []
        )
    else:
        finalized = replace(finalized, criticalHit=False)
        pending.active.context.criticalAttackNodes.discard(node_id)
    pending.active.context.attackRollPayloads[node_id] = finalized
    if finalized.id == pending.roll.id:
        pending.roll = finalized
        pending.active.context.roll = finalized
        if finalized.effectInputs is not None:
            pending.active.context.amountInputs.update(
                {entry.effectNodeId: entry.amount for entry in finalized.effectInputs.amounts}
            )


def bound_effect_dispatches_for_event(
    room: Room,
    pending: PendingCharacterResolution,
    event: ResolutionEvent,
) -> list[BoundEffect]:
    if event.eventType not in {
        ResolutionEventType.DAMAGE_APPLIED,
        ResolutionEventType.CONDITION_APPLIED,
        ResolutionEventType.EFFECT_COMMITTED,
        ResolutionEventType.REST_COMPLETED,
    } or event.bindings is None:
        return []

    target_id = event.bindings.targetSheetId
    persisted_state = pending.scheduledEffectStates.setdefault(
        target_id,
        list(room.scheduled_effects.get(target_id, [])),
    )
    excluded_sources = {event.dispatchSource} if event.dispatchSource is not None else set()
    persisted = dispatch_scheduled_effects(persisted_state, event.eventType, excluded_sources)
    pending.scheduledEffectStates[target_id] = persisted.remaining
    pending.touchedScheduledTargets.add(target_id)

    local_scheduled = [
        active for active in pending.active.context.scheduledEffects
        if active.targetSheetId == target_id
    ]
    local = dispatch_scheduled_effects(local_scheduled, event.eventType, excluded_sources)
    local_ids = {active.id for active in local_scheduled}
    pending.active.context.scheduledEffects = [
        active for active in pending.active.context.scheduledEffects
        if active.id not in local_ids
    ] + local.remaining

    target_state = pending.active.context.participants.get(target_id)
    recurring = recurring_effects_for_event(
        target_state.ongoingEffects if target_state is not None else [],
        event.eventType,
    )
    dispatches = [*persisted.dispatched, *local.dispatched, *recurring]
    sheets = {sheet.id: sheet for sheet in all_room_sheets(room)}
    bound: list[BoundEffect] = []
    for dispatch in dispatches:
        if dispatch.source == event.dispatchSource:
            continue
        source = sheets.get(dispatch.sourceSheetId)
        target = sheets.get(dispatch.targetSheetId)
        if source is None or target is None:
            continue
        pending.active.context.register_participant(source)
        pending.active.context.register_participant(target)
        pending.participantSnapshots.setdefault(source.id, character_runtime_snapshot(source))
        pending.participantSnapshots.setdefault(target.id, character_runtime_snapshot(target))
        bound.append(BoundEffect(
            effect=dispatch.effect,
            bindings=EffectParticipantBindings(
                sourceSheetId=source.id,
                targetSheetId=target.id,
                ownerSheetId=source.id,
            ),
            dispatchSource=dispatch.source,
        ))
    return bound


def resolution_prompt_for_effect_event(
    room: Room,
    source_roll: RollPayload,
    event_roll: RollPayload,
    target: CharacterSheet,
    event: ResolutionEvent,
    ignored: set[str],
    response_rolls: list[RollPayload],
) -> ResolutionInterceptorPrompt | None:
    if event.eventType == ResolutionEventType.CONDITION_PENDING:
        return condition_interaction_prompt_for_roll(room, source_roll, event_roll, target, ignored, response_rolls)
    if event.eventType == ResolutionEventType.DAMAGE_PENDING:
        return damage_interaction_prompt_for_roll(room, source_roll, event_roll, target, ignored, response_rolls)
    if event.eventType == ResolutionEventType.SAVE_ROLLED and event.rollOutcome == RollOutcome.FAILURE:
        return failed_save_prompt_for_roll(room, source_roll, event_roll, target, ignored, response_rolls, [])
    if event.eventType == ResolutionEventType.ATTACK_ROLLED:
        return attack_interaction_prompt_for_roll(room, source_roll, event_roll, target, ignored, response_rolls)
    if event.eventType == ResolutionEventType.SPELL_DECLARED:
        return counterspell_prompt_for_roll(room, source_roll, target, ignored, response_rolls, [])
    return None


def default_effect_event_response(event: ResolutionEvent) -> ResolutionEventResponse:
    if event.eventType in {
        ResolutionEventType.ATTACK_ROLLED,
        ResolutionEventType.SAVE_ROLLED,
        ResolutionEventType.CHECK_ROLLED,
    }:
        return ResolutionEventResponse(rollOutcome=event.rollOutcome)
    if event.eventType in {
        ResolutionEventType.DAMAGE_APPLIED,
        ResolutionEventType.CONDITION_APPLIED,
        ResolutionEventType.EFFECT_COMMITTED,
        ResolutionEventType.REST_COMPLETED,
    }:
        return ResolutionEventResponse()
    return ResolutionEventResponse(pendingEffect=event.pendingEffect)


def resolve_contested_check_for_roll(
    room: Room,
    roll: RollPayload,
    target: CharacterSheet,
) -> tuple[RollPayload, str | None, list[RollPayload]]:
    found = first_contested_check_effect(roll.pendingEffect)
    if found is None:
        return roll, None, []
    node_id, effect = found
    existing_inputs = roll.effectInputs or EffectResolutionInputs()
    if any(entry.effectNodeId == node_id for entry in existing_inputs.rolls):
        return roll, None, []
    source = source_sheet_for_roll(room, roll)
    if source is None:
        return roll, None, []

    source_label, source_modifier = ability_check_spec(source, effect.contest.sourceCheck)
    target_options = [
        (*ability_check_spec(target, check), check)
        for check in effect.contest.targetChecks
    ]
    target_label, target_modifier, target_check = max(target_options, key=lambda option: option[1])
    source_response = response_ability_roll(
        sheet=source,
        ability=effect.contest.sourceCheck.ability,
        action_id="contest",
        label=source_label,
        source_label=roll.label,
        modifier=source_modifier + max(0, roll.total),
        saving_throw_conditions=False,
        modifier_target=RollModifierEffectTarget.ABILITY_CHECK,
    )
    target_response = response_ability_roll(
        sheet=target,
        ability=target_check.ability,
        action_id="contest",
        label=target_label,
        source_label=roll.label,
        modifier=target_modifier,
        saving_throw_conditions=False,
        modifier_target=RollModifierEffectTarget.ABILITY_CHECK,
    )
    source_won = source_response.total > target_response.total
    outcome = RollOutcome.SUCCESS if source_won else RollOutcome.FAILURE
    verb = "wins" if source_won else "fails"
    description = (
        f"{source.name} {verb} {source_label} {source_response.total} vs "
        f"{target.name} {target_label} {target_response.total}"
    )
    return replace(
        roll,
        effectInputs=replace(
            existing_inputs,
            rolls=[*existing_inputs.rolls, EffectRollInput(node_id, outcome)],
        ),
    ), description, [source_response, target_response]


def ability_check_spec(sheet: CharacterSheet, check: AbilityCheck) -> tuple[str, int]:
    if check.skill is not None:
        return (
            f"{enum_label(check.ability)} ({enum_label(check.skill)})",
            skill_modifier(sheet, enum_key(check.skill), check.ability),
        )
    return f"{enum_label(check.ability)} Check", ability_check_modifier(sheet, check.ability)


def attach_resolution_context(resolution: RollResolution, outcome_prefixes: list[str], response_rolls: list[RollPayload]) -> RollResolution:
    if outcome_prefixes:
        resolution.outcome = f"{'; '.join(outcome_prefixes)}; {resolution.outcome}"
    if response_rolls:
        merged = dedupe_response_rolls([*response_rolls, *(resolution.responseRolls or [])])
        resolution.responseRolls = merged
    return resolution


def counterspell_prompt_for_roll(
    room: Room,
    source_roll: RollPayload,
    target: CharacterSheet,
    ignored: set[str],
    response_rolls: list[RollPayload],
    outcome_prefixes: list[str],
) -> ResolutionInterceptorPrompt | None:
    if source_roll.source.section != SheetSectionType.SPELLS or source_roll.source.sourceId == enum_key(SpellId.COUNTERSPELL):
        return None
    source = source_sheet_for_roll(room, source_roll)
    for sheet in all_room_sheets(room):
        if source is not None and sheet.id == source.id:
            continue
        for interaction_source in matching_sheet_interactions(sheet, ResolutionEventType.SPELL_DECLARED, source_roll, source_sheet=source, target=target):
            interceptor_type = interceptor_type_for_interaction(interaction_source.interaction)
            if interceptor_type != ResolutionInterceptorType.CANCEL_ACTION:
                continue
            key = resolution_interceptor_key_for(interceptor_type, sheet.id, interaction_source.label)
            if key in ignored:
                continue
            return ResolutionInterceptorPrompt(
                id=f"prompt-{time_ns()}",
                interceptorType=interceptor_type,
                trigger=ResolutionInterceptorTrigger.BEFORE_SPELL_RESOLVES,
                sourceRoll=source_roll,
                pendingRoll=source_roll,
                targetSheetId=target.id,
                targetTokenId=target.tokenId,
                targetName=target.name,
                ownerSheetId=sheet.id,
                ownerTokenId=sheet.tokenId,
                ownerName=sheet.name,
                ownerPlayerKey=sheet.owner,
                label=interaction_source.label,
                description=f"{source_roll.sourceLabel} is about to resolve against {target.name}.",
                useLabel=f"Use {interaction_source.label}",
                declineLabel="Decline",
                createdAt=time_ns(),
                interaction=interaction_source.interaction,
                ignoredInterceptors=list(ignored),
                responseRolls=response_rolls or None,
            )
    return None


def condition_interaction_prompt_for_roll(
    room: Room,
    source_roll: RollPayload,
    pending_roll: RollPayload,
    target: CharacterSheet,
    ignored: set[str],
    response_rolls: list[RollPayload],
) -> ResolutionInterceptorPrompt | None:
    if not added_condition_types(pending_roll.pendingEffect):
        return None
    interaction_source = next(
        (
            candidate
            for candidate in matching_sheet_interactions(
                target,
                ResolutionEventType.CONDITION_PENDING,
                pending_roll,
                source_sheet=source_sheet_for_roll(room, pending_roll),
                target=target,
            )
            if candidate.interaction.decision.decisionType == InteractionDecisionType.PROMPT
            and interceptor_type_for_interaction(candidate.interaction) is not None
            and resolution_interceptor_key_for(
                interceptor_type_for_interaction(candidate.interaction),
                target.id,
                candidate.label,
            ) not in ignored
        ),
        None,
    )
    if interaction_source is None:
        return None
    interceptor_type = interceptor_type_for_interaction(interaction_source.interaction)
    assert interceptor_type is not None
    return ResolutionInterceptorPrompt(
        id=f"prompt-{time_ns()}",
        interceptorType=interceptor_type,
        trigger=ResolutionInterceptorTrigger.BEFORE_CONDITION_APPLIED,
        sourceRoll=source_roll,
        pendingRoll=pending_roll,
        targetSheetId=target.id,
        targetTokenId=target.tokenId,
        targetName=target.name,
        ownerSheetId=target.id,
        ownerTokenId=target.tokenId,
        ownerName=target.name,
        ownerPlayerKey=target.owner,
        label=interaction_source.label,
        description=f"{source_roll.sourceLabel} is about to apply a condition to {target.name}.",
        useLabel=f"Use {interaction_source.label}",
        declineLabel="Decline",
        createdAt=time_ns(),
        interaction=interaction_source.interaction,
        ignoredInterceptors=list(ignored),
        responseRolls=response_rolls or None,
    )


def failed_save_prompt_for_roll(
    room: Room,
    source_roll: RollPayload,
    pending_roll: RollPayload,
    target: CharacterSheet,
    ignored: set[str],
    response_rolls: list[RollPayload],
    outcome_prefixes: list[str],
) -> ResolutionInterceptorPrompt | None:
    saving_throw = failed_save_ability(pending_roll)
    save_dc = failed_save_dc(pending_roll)
    if saving_throw is None or save_dc is None:
        return None
    for interaction_source in failed_save_interactions(room, target, pending_roll):
        interceptor_type = interceptor_type_for_interaction(interaction_source.interaction)
        if interceptor_type is None:
            continue
        key = resolution_interceptor_key_for(interceptor_type, target.id, interaction_source.label)
        if key in ignored:
            continue
        return ResolutionInterceptorPrompt(
            id=f"prompt-{time_ns()}",
            interceptorType=interceptor_type,
            trigger=ResolutionInterceptorTrigger.BEFORE_FAILED_SAVE_FINALIZES,
            sourceRoll=source_roll,
            pendingRoll=pending_roll,
            targetSheetId=target.id,
            targetTokenId=target.tokenId,
            targetName=target.name,
            ownerSheetId=target.id,
            ownerTokenId=target.tokenId,
            ownerName=target.name,
            ownerPlayerKey=target.owner,
            label=interaction_source.label,
            description=f"{target.name} failed a DC {save_dc} {enum_label(saving_throw)} save.",
            useLabel=failed_save_use_label(interceptor_type),
            declineLabel="Decline",
            createdAt=time_ns(),
            interaction=interaction_source.interaction,
            ignoredInterceptors=list(ignored),
            responseRolls=response_rolls or None,
        )
    return None


def attack_interaction_prompt_for_roll(
    room: Room,
    source_roll: RollPayload,
    pending_roll: RollPayload,
    target: CharacterSheet,
    ignored: set[str],
    response_rolls: list[RollPayload],
) -> ResolutionInterceptorPrompt | None:
    if pending_roll.resolution != RollResolutionMode.ATTACK_VS_ARMOR_CLASS:
        return None
    source_sheet = source_sheet_for_roll(room, pending_roll)
    for owner in all_room_sheets(room):
        if source_sheet is not None and owner.id == source_sheet.id:
            continue
        for interaction_source in matching_sheet_interactions(
            owner,
            ResolutionEventType.ATTACK_ROLLED,
            pending_roll,
            source_sheet=source_sheet,
            target=target,
        ):
            interceptor_type = interceptor_type_for_interaction(interaction_source.interaction)
            if interceptor_type != ResolutionInterceptorType.MODIFY_ROLL:
                continue
            key = resolution_interceptor_key_for(interceptor_type, owner.id, interaction_source.label)
            if key in ignored:
                continue
            return ResolutionInterceptorPrompt(
                id=f"prompt-{time_ns()}",
                interceptorType=interceptor_type,
                trigger=ResolutionInterceptorTrigger.BEFORE_ATTACK_RESOLVES,
                sourceRoll=source_roll,
                pendingRoll=pending_roll,
                targetSheetId=target.id,
                targetTokenId=target.tokenId,
                targetName=target.name,
                ownerSheetId=owner.id,
                ownerTokenId=owner.tokenId,
                ownerName=owner.name,
                ownerPlayerKey=owner.owner,
                label=interaction_source.label,
                description=f"{source_roll.sourceLabel} is about to resolve against {target.name}.",
                useLabel=f"Use {interaction_source.label}",
                declineLabel="Decline",
                createdAt=time_ns(),
                interaction=interaction_source.interaction,
                ignoredInterceptors=list(ignored),
                responseRolls=response_rolls or None,
            )
    return None


def damage_interaction_prompt_for_roll(
    room: Room,
    source_roll: RollPayload,
    pending_roll: RollPayload,
    target: CharacterSheet,
    ignored: set[str],
    response_rolls: list[RollPayload],
) -> ResolutionInterceptorPrompt | None:
    if not roll_can_apply_damage(pending_roll):
        return None
    source_sheet = source_sheet_for_roll(room, pending_roll)
    match = next(
        (
            (owner, interaction_source)
            for owner in all_room_sheets(room)
            if source_sheet is None or owner.id != source_sheet.id
            for interaction_source in matching_sheet_interactions(
                owner,
                ResolutionEventType.DAMAGE_PENDING,
                pending_roll,
                source_sheet=source_sheet,
                target=target,
            )
            if interceptor_type_for_interaction(interaction_source.interaction) == ResolutionInterceptorType.MODIFY_PENDING_DAMAGE
            and resolution_interceptor_key_for(
                ResolutionInterceptorType.MODIFY_PENDING_DAMAGE,
                owner.id,
                interaction_source.label,
            ) not in ignored
        ),
        None,
    )
    if match is None:
        return None
    owner, interaction_source = match
    interceptor_type = ResolutionInterceptorType.MODIFY_PENDING_DAMAGE
    stable_amount = next(
        (
            entry.amount for entry in (pending_roll.effectInputs.amounts if pending_roll.effectInputs is not None else [])
            if entry.effectNodeId == EffectNodeId(())
        ),
        None,
    )
    if stable_amount is not None and stable_amount <= 0:
        return None
    return ResolutionInterceptorPrompt(
        id=f"prompt-{time_ns()}",
        interceptorType=interceptor_type,
        trigger=ResolutionInterceptorTrigger.BEFORE_DAMAGE_APPLIED,
        sourceRoll=source_roll,
        pendingRoll=pending_roll,
        targetSheetId=target.id,
        targetTokenId=target.tokenId,
        targetName=target.name,
        ownerSheetId=owner.id,
        ownerTokenId=owner.tokenId,
        ownerName=owner.name,
        ownerPlayerKey=owner.owner,
        label=interaction_source.label,
        description=f"{target.name} is about to take damage.",
        useLabel=f"Use {interaction_source.label}",
        declineLabel="Decline",
        createdAt=time_ns(),
        interaction=interaction_source.interaction,
        ignoredInterceptors=list(ignored),
        responseRolls=response_rolls or None,
    )


@dataclass(frozen=True)
class SheetInteractionSource:
    label: str
    interaction: Interaction


def sheet_interaction_sources(sheet: CharacterSheet) -> list[SheetInteractionSource]:
    from dnd_board.rules.shared.condition_effects import condition_ongoing_effects

    sources: list[SheetInteractionSource] = []

    def add_mechanics(label: str, mechanics) -> None:
        if mechanics is not None:
            sources.extend(SheetInteractionSource(label, interaction) for interaction in mechanics.interactions)

    seen_spells: set[SpellId] = set()
    for spell in [*sheet.spells, *sheet.spellbook]:
        if spell.id in seen_spells:
            continue
        seen_spells.add(spell.id)
        add_mechanics(enum_label(spell.name), spell.mechanics)
    for feature in sheet.features:
        add_mechanics(feature.name, feature.mechanics)
        for action in feature.rollActions or []:
            add_mechanics(enum_label(action.name), action.mechanics)
    for ability in sheet.abilities:
        add_mechanics(ability.name, ability.mechanics)
        for action in ability.rollActions or []:
            add_mechanics(enum_label(action.name), action.mechanics)
    for resource in sheet.resources:
        if resource.currentUses <= 0:
            continue
        add_mechanics(resource.name, resource.mechanics)
        for action in resource.rollActions or []:
            add_mechanics(enum_label(action.name), action.mechanics)
    for attack in sheet.attacks:
        add_mechanics(attack.name, attack.mechanics)
    for condition, ongoing_effect in condition_ongoing_effects(sheet.conditions, sheet.suppressedConditions):
        sources.extend(
            SheetInteractionSource(enum_label(condition), interaction)
            for interaction in ongoing_effect.interactions
        )
    for active in sheet.ongoingEffects:
        sources.extend(
            SheetInteractionSource(active.sourceLabel, interaction)
            for interaction in active.effect.interactions
        )
    return sources


def matching_sheet_interactions(
    sheet: CharacterSheet,
    event_type: ResolutionEventType,
    roll: RollPayload,
    *,
    source_sheet: CharacterSheet | None = None,
    target: CharacterSheet | None = None,
) -> list[SheetInteractionSource]:
    return [
        interaction_source
        for interaction_source in sheet_interaction_sources(sheet)
        if interaction_source.interaction.trigger == event_type
        and interaction_predicates_match(interaction_source.interaction, sheet, roll, source=source_sheet, target=target)
    ]


def interaction_predicates_match(
    interaction: Interaction,
    owner: CharacterSheet,
    roll: RollPayload,
    *,
    source: CharacterSheet | None,
    target: CharacterSheet | None,
) -> bool:
    from dnd_board.rules.shared.character_effects import CharacterEffectExecutionContext
    from dnd_board.rules.shared.effects import EffectNodeId

    context = CharacterEffectExecutionContext(roll, target or owner, source, owner=owner)
    return context.evaluate_predicates(EffectNodeId(()), interaction.predicates)


def interceptor_type_for_interaction(interaction: Interaction) -> ResolutionInterceptorType | None:
    if any(isinstance(operation, CancelPendingAction) for operation in interaction.operations):
        return ResolutionInterceptorType.CANCEL_ACTION
    if any(isinstance(operation, RerollSavingThrow) for operation in interaction.operations):
        return ResolutionInterceptorType.REROLL_SAVING_THROW
    if any(isinstance(operation, ReplaceRollOutcome) for operation in interaction.operations):
        return ResolutionInterceptorType.REPLACE_ROLL_OUTCOME
    if any(isinstance(operation, ModifyPendingDamage) for operation in interaction.operations):
        return ResolutionInterceptorType.MODIFY_PENDING_DAMAGE
    if any(isinstance(operation, ModifyRoll) for operation in interaction.operations):
        return ResolutionInterceptorType.MODIFY_ROLL
    if any(isinstance(operation, PreventCondition) for operation in interaction.operations):
        return ResolutionInterceptorType.PREVENT_CONDITION
    if any(isinstance(operation, ModifyAction) for operation in interaction.operations):
        return ResolutionInterceptorType.MODIFY_ACTION
    if any(isinstance(operation, ApplyEffectOperation) for operation in interaction.operations):
        return ResolutionInterceptorType.APPLY_EFFECT
    if any(isinstance(operation, ScheduleEffectOperation) for operation in interaction.operations):
        return ResolutionInterceptorType.SCHEDULE_EFFECT
    return None


def failed_save_interactions(room: Room, target: CharacterSheet, roll: RollPayload) -> list[SheetInteractionSource]:
    return matching_sheet_interactions(
        target,
        ResolutionEventType.SAVE_ROLLED,
        roll,
        source_sheet=source_sheet_for_roll(room, roll),
        target=target,
    )


def failed_save_use_label(interceptor_type: ResolutionInterceptorType) -> str:
    if interceptor_type == ResolutionInterceptorType.REROLL_SAVING_THROW:
        return "Reroll"
    if interceptor_type == ResolutionInterceptorType.REPLACE_ROLL_OUTCOME:
        return "Succeed Instead"
    return "Use"


def apply_resolution_interceptor(
    room: Room,
    prompt: ResolutionInterceptorPrompt,
    target: CharacterSheet,
    modify_damage_roll: bool = True,
) -> tuple[RollPayload, list[str], list[RollPayload], RollResolution | None]:
    owner = next((sheet for sheet in all_room_sheets(room) if sheet.id == prompt.ownerSheetId), target)
    roll_outcome = RollOutcome.FAILURE if failed_save_ability(prompt.pendingRoll) is not None else None
    operation_result = apply_interaction_operations(
        ResolutionEvent(
            resolutionId=ResolutionId(time_ns()),
            eventType=prompt.interaction.trigger,
            pendingEffect=prompt.pendingRoll.pendingEffect,
            rollOutcome=roll_outcome,
        ),
        prompt.interaction.operations,
    )
    modified_roll = roll_after_interaction_operations(
        prompt.pendingRoll,
        operation_result,
        owner,
        prompt.label,
        modify_damage=modify_damage_roll,
    )
    if operation_result.cancelled:
        resolution = RollResolution(
            id=f"resolution-{time_ns()}",
            roll=prompt.sourceRoll,
            targetSheetId=target.id,
            targetTokenId=target.tokenId,
            targetName=target.name,
            targetArmorClass=target.armorClass,
            targetHp=target.hp,
            targetConditions=target.conditions,
            outcome=f"{prompt.ownerName} counters {prompt.sourceRoll.sourceLabel}; it has no effect on {target.name}",
            createdAt=time_ns(),
        )
        return modified_roll, [], [], resolution
    if operation_result.rollOutcome == RollOutcome.SUCCESS and roll_outcome == RollOutcome.FAILURE:
        return successful_save_roll(modified_roll), [f"{prompt.ownerName} turns the failed save into a success"], [], None
    if operation_result.savingThrowRerolls:
        saving_throw = failed_save_ability(prompt.pendingRoll) or AbilityType.STRENGTH
        save_dc = failed_save_dc(prompt.pendingRoll)
        reroll_bonus = interaction_reroll_bonus(target, operation_result.savingThrowRerolls[0])
        reroll = response_ability_roll(
            sheet=target,
            ability=saving_throw,
            action_id=enum_key(prompt.interceptorType),
            label=prompt.label,
            source_label=modified_roll.sourceLabel,
            modifier=save_modifier(target, saving_throw) + reroll_bonus,
        )
        succeeded = save_dc is not None and reroll.total >= save_dc
        outcome = f"{target.name} rerolls with {prompt.label} and {'passes' if succeeded else 'fails'} with {reroll.total}"
        return save_outcome_roll(modified_roll, succeeded), [outcome], [reroll], None
    if operation_result.pendingDamageModifications:
        modification = operation_result.pendingDamageModifications[0]
        action = "halves" if modification.modification == PendingDamageModificationType.MULTIPLY and modification.numerator == 1 and modification.denominator == 2 else "modifies"
        return modified_roll, [f"{prompt.ownerName} {action} the incoming damage"], [], None
    return modified_roll, [], [], None


def roll_after_interaction_operations(
    roll: RollPayload,
    operation_result,
    owner: CharacterSheet,
    source_label: str,
    modify_damage: bool = True,
) -> RollPayload:
    pending_effect = operation_result.pendingEffect
    appended_effects = [*operation_result.additionalEffects, *operation_result.scheduledEffects]
    if appended_effects:
        pending_effect = SequenceEffect([*([pending_effect] if pending_effect is not None else []), *appended_effects])
    updated = replace(roll, pendingEffect=pending_effect)

    if modify_damage:
        for modification in operation_result.pendingDamageModifications:
            if modification.modification == PendingDamageModificationType.PREVENT:
                updated = scaled_damage_roll(updated, 0, 1)
            elif modification.modification == PendingDamageModificationType.MULTIPLY:
                updated = scaled_damage_roll(updated, modification.numerator, modification.denominator)
            elif modification.modification == PendingDamageModificationType.REDUCE:
                updated = reduced_damage_roll(updated, interaction_amount(owner, modification.amount))

    for modification in operation_result.rollModifications:
        updated = modified_d20_roll(updated, modification, owner, source_label)
    return updated


def apply_pending_damage_modifications(
    context: CharacterEffectExecutionContext,
    node_id: EffectNodeId,
    modifications: list[ModifyPendingDamage],
    owner: CharacterSheet,
) -> None:
    pending = context.pendingDamages.get(node_id)
    if pending is None:
        return
    amount = pending.currentAmount
    for modification in modifications:
        if modification.modification == PendingDamageModificationType.PREVENT:
            amount = 0
        elif modification.modification == PendingDamageModificationType.MULTIPLY:
            if modification.denominator == 0:
                raise ValueError("Damage multiplier denominator cannot be zero")
            amount = max(0, amount * modification.numerator // modification.denominator)
        elif modification.modification == PendingDamageModificationType.REDUCE:
            amount = max(0, amount - interaction_amount(owner, modification.amount))
    pending.currentAmount = amount
    pending.effect = replace(pending.effect, amount=FixedAmount(amount), scaling=[])
    context.amountInputs[node_id] = amount


def scaled_damage_roll(roll: RollPayload, numerator: int, denominator: int) -> RollPayload:
    if denominator == 0:
        raise ValueError("Damage multiplier denominator cannot be zero")
    if roll.resolution == RollResolutionMode.ATTACK_VS_ARMOR_CLASS:
        return roll
    if roll.damageComponents:
        components = [replace(component, total=max(0, component.total * numerator // denominator)) for component in roll.damageComponents]
        return replace(roll, total=sum(component.total for component in components), damageComponents=components)
    return replace(roll, total=max(0, roll.total * numerator // denominator))


def reduced_damage_roll(roll: RollPayload, amount: int) -> RollPayload:
    remaining = max(0, amount)
    pending_effect = roll.pendingEffect
    if roll.damageComponents:
        components = []
        amount_inputs = list(roll.effectInputs.amounts) if roll.effectInputs is not None else []
        addressed_damage = False
        for component in roll.damageComponents:
            reduction = min(component.total, remaining)
            reduced_total = component.total - reduction
            components.append(replace(component, total=reduced_total))
            if component.effectNodeIds:
                addressed_damage = True
                amount_inputs = [entry for entry in amount_inputs if entry.effectNodeId not in component.effectNodeIds]
                amount_inputs.extend(EffectAmountInput(node_id, reduced_total) for node_id in component.effectNodeIds)
            remaining -= reduction
        if pending_effect is not None and not addressed_damage:
            from dnd_board.rules.shared.character_effects import reduced_damage_effect_node

            pending_effect = reduced_damage_effect_node(pending_effect, max(0, amount))
        return replace(
            roll,
            total=roll.total if roll.resolution == RollResolutionMode.ATTACK_VS_ARMOR_CLASS else sum(component.total for component in components),
            damageComponents=components,
            pendingEffect=pending_effect,
            effectInputs=replace(roll.effectInputs, amounts=amount_inputs) if roll.effectInputs is not None else None,
        )
    total = max(0, roll.total - remaining)
    if pending_effect is not None:
        from dnd_board.rules.shared.character_effects import reduced_damage_effect_node

        pending_effect = reduced_damage_effect_node(pending_effect, max(0, amount))
    return replace(
        roll,
        total=roll.total if roll.resolution == RollResolutionMode.ATTACK_VS_ARMOR_CLASS else total,
        pendingEffect=pending_effect,
    )


def interaction_amount(owner: CharacterSheet, amount) -> int:
    if isinstance(amount, CombinedAmount):
        return sum(interaction_amount(owner, part) for part in amount.amounts)
    if isinstance(amount, FixedAmount):
        return amount.value
    if isinstance(amount, DiceAmount):
        return amount.staticBonus + sum(random.randint(1, amount.diceType.value) for _ in range(amount.diceCount))
    if isinstance(amount, CalculatedAmount):
        if amount.calculation == AmountCalculation.SOURCE_CLASS_LEVEL and amount.characterClass is not None:
            value = class_level(owner, amount.characterClass)
        elif amount.calculation == AmountCalculation.SOURCE_CHARACTER_LEVEL:
            value = sum(character_class.level for character_class in owner.classes)
        elif amount.calculation == AmountCalculation.SOURCE_PROFICIENCY_BONUS:
            value = owner.proficiencyBonus
        elif amount.calculation == AmountCalculation.SOURCE_ABILITY_MODIFIER and amount.ability is not None:
            value = ability_modifier(getattr(owner.abilityScores, enum_key(amount.ability)))
        else:
            value = 0
        value *= amount.multiplier
        return max(amount.minimum, value) if amount.minimum is not None else value
    return 0


def modified_d20_roll(roll: RollPayload, modification: ModifyRoll, owner: CharacterSheet, source_label: str) -> RollPayload:
    if modification.modification in {RollModificationType.ADD, RollModificationType.SUBTRACT}:
        amount = interaction_amount(owner, modification.amount)
        value = amount if modification.modification == RollModificationType.ADD else -amount
        return replace(
            roll,
            modifier=roll.modifier + value,
            modifierBreakdown=[*roll.modifierBreakdown, RollModifierBreakdown(source_label, value)],
            total=roll.total + value,
        )
    if not roll.dice or roll.diceType != DiceType.D20:
        return roll
    extra = random.randint(1, 20)
    dice = [roll.dice[0], extra]
    selected = max(dice) if modification.modification == RollModificationType.ADVANTAGE else min(dice)
    die = "2d20kh1" if modification.modification == RollModificationType.ADVANTAGE else "2d20kl1"
    return replace(roll, dice=dice, die=die, total=selected + roll.modifier)


def interaction_reroll_bonus(sheet: CharacterSheet, reroll: RerollSavingThrow) -> int:
    if not isinstance(reroll.bonus, CalculatedAmount):
        return 0
    if reroll.bonus.calculation == AmountCalculation.SOURCE_CLASS_LEVEL and reroll.bonus.characterClass is not None:
        return class_level(sheet, reroll.bonus.characterClass) * reroll.bonus.multiplier
    return 0


def halved_damage_roll(roll: RollPayload) -> RollPayload:
    pending_effect = roll.pendingEffect
    if pending_effect is not None:
        from dnd_board.rules.shared.effects import multiplied_damage_effect

        pending_effect = multiplied_damage_effect(pending_effect, 1, 2)
        if roll.resolution == RollResolutionMode.ATTACK_VS_ARMOR_CLASS:
            return replace(roll, pendingEffect=pending_effect)
    if roll.damageComponents:
        components = [replace(component, total=max(0, component.total // 2)) for component in roll.damageComponents]
        return replace(
            roll,
            total=sum(component.total for component in components),
            damageComponents=components,
            pendingEffect=pending_effect,
        )
    return replace(roll, total=max(0, roll.total // 2), pendingEffect=pending_effect)


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


def successful_save_roll(roll: RollPayload) -> RollPayload:
    return save_outcome_roll(roll, True)


def save_outcome_roll(roll: RollPayload, succeeded: bool) -> RollPayload:
    if roll.damageSavingThrow is not None:
        effect_inputs = roll.effectInputs
        if effect_inputs is not None and effect_inputs.rolls:
            latest = effect_inputs.rolls[-1]
            rolls = [
                *effect_inputs.rolls[:-1],
                replace(latest, outcome=RollOutcome.SUCCESS if succeeded else RollOutcome.FAILURE),
            ]
            return replace(roll, damageSaveSucceeded=succeeded, effectInputs=replace(effect_inputs, rolls=rolls))
        return replace(roll, damageSaveSucceeded=succeeded)
    return roll


def all_room_sheets(room: Room) -> list[CharacterSheet]:
    player = Player(id="interceptor-dm", name="DM", player_key="dm", websocket=None, room_id=room.id)
    return visible_sheets(room, player)


def class_level(sheet: CharacterSheet, class_type: ClassType) -> int:
    return sum(character_class.level for character_class in sheet.classes if character_class.name == class_type)


def resolution_interceptor_key(prompt: ResolutionInterceptorPrompt) -> str:
    return resolution_interceptor_key_for(prompt.interceptorType, prompt.ownerSheetId, prompt.label)


def resolution_interceptor_key_for(interceptor_type: ResolutionInterceptorType, owner_sheet_id: str, label: str) -> str:
    return f"{enum_key(interceptor_type)}:{owner_sheet_id}:{sanitize_asset_id(label)}"


def resolve_roll_against_target(
    room: Room,
    roll: RollPayload,
    target: CharacterSheet,
    effect_resolution: ResolvedCharacterEffect | None = None,
) -> RollResolution:
    if roll.resolution == RollResolutionMode.NONE and roll.pendingEffect is None and roll.damageSavingThrow is not None and roll.damageSaveDc is not None:
        return resolve_damage_save_prompt_against_target(roll, target)
    damage_save_outcome, damage_save_roll, resolved_roll = resolve_damage_save_for_roll(roll, target)
    source = source_sheet_for_roll(room, roll)
    resolution = resolve_dnd_roll_against_target(resolved_roll, target, source, effect_resolution)
    apply_effect_sheet_updates(room, resolution)
    concentration_update_sheet_ids: set[str] = set()
    damage_triggered_condition_outcomes = resolve_damage_triggered_condition_saves(room, roll, target, resolution)
    response_rolls = dedupe_response_rolls(
        [
            *([damage_save_roll] if damage_save_roll is not None else []),
            *(response_roll for _outcome, _conditions, response_roll in damage_triggered_condition_outcomes),
        ]
    )
    if damage_save_outcome:
        resolution.outcome = f"{resolution.outcome}; {damage_save_outcome}"
    if damage_triggered_condition_outcomes:
        for _outcome, cleared_conditions, _response_roll in damage_triggered_condition_outcomes:
            resolution.targetConditions = [condition for condition in resolution.targetConditions if condition not in cleared_conditions]
        resolution.outcome = f"{resolution.outcome}; {'; '.join(outcome for outcome, _conditions, _response_roll in damage_triggered_condition_outcomes)}"
    if response_rolls:
        for response_roll in response_rolls:
            room.pending_rolls[roll_queue_key(response_roll)] = response_roll
        resolution.responseRolls = response_rolls
    if roll.resolution in {RollResolutionMode.APPLY_DAMAGE, RollResolutionMode.HEAL_SELF, RollResolutionMode.APPLY_TEMPORARY_HIT_POINTS}:
        room.hit_points[target.tokenId] = resolution.targetHp.current
        room.temporary_hit_points[target.tokenId] = resolution.targetHp.temporary
    death_outcome = apply_dead_condition_after_damage(resolution)
    if death_outcome:
        resolution.outcome = f"{resolution.outcome}; {death_outcome}"
    concentration_outcome, concentration_roll = resolve_concentration_save_after_damage(room, target, resolution)
    if concentration_outcome:
        resolution.outcome = f"{resolution.outcome}; {concentration_outcome}"
        concentration_update_sheet_ids.add(target.id)
    if concentration_roll is not None:
        response_rolls = dedupe_response_rolls([*response_rolls, concentration_roll])
        room.pending_rolls[roll_queue_key(concentration_roll)] = concentration_roll
        resolution.responseRolls = response_rolls
    apply_resolved_conditions(room, target.id, target.conditions, resolution.targetConditions, roll, source)
    if concentration_spell_for_roll(source, roll) is not None and source is not None:
        concentration_update_sheet_ids.add(source.id)
    if concentration_update_sheet_ids:
        resolution.concentrationUpdates = [
            ActiveConcentrationUpdate(
                sheetId=sheet_id,
                activeConcentration=active_concentration_status(room.active_concentrations.get(sheet_id)),
            )
            for sheet_id in sorted(concentration_update_sheet_ids)
        ]
    return resolution


def apply_effect_sheet_updates(room: Room, resolution: RollResolution) -> None:
    persistent_effect_changed = False
    for update in resolution.sheetUpdates or []:
        if update.hp is not None:
            room.hit_points[update.tokenId] = update.hp.current
            room.temporary_hit_points[update.tokenId] = update.hp.temporary
        if update.conditions is not None:
            room.condition_overrides[update.tokenId] = update.conditions
        if update.suppressedConditions is not None:
            room.suppressed_conditions[update.tokenId] = update.suppressedConditions
            persistent_effect_changed = True
        if update.damageResistances is not None:
            room.damage_resistances[update.tokenId] = update.damageResistances
        if update.damageVulnerabilities is not None:
            room.damage_vulnerabilities[update.tokenId] = update.damageVulnerabilities
        if update.damageImmunities is not None:
            room.damage_immunities[update.tokenId] = update.damageImmunities
        if update.ongoingEffects is not None:
            room.ongoing_effects[update.tokenId] = update.ongoingEffects
            persistent_effect_changed = True
        if update.scheduledEffects:
            scheduled = room.scheduled_effects.setdefault(update.tokenId, [])
            existing_ids = {active.id for active in scheduled}
            scheduled.extend(active for active in update.scheduledEffects if active.id not in existing_ids)
            persistent_effect_changed = True
        for applied in update.appliedEffects or []:
            effect = applied.effect
            if isinstance(effect, RestEffect):
                effect_sheet = next((sheet for sheet in all_room_sheets(room) if sheet.id == update.sheetId), None)
                if effect_sheet is None:
                    continue
                reset_sheet_resources(room, effect_sheet, effect.rest)
                reset_sheet_conditions(room, effect_sheet, effect.rest)
                reset_sheet_temporary_hit_points(room, effect_sheet, effect.rest)
                rested_conditions = list(room.condition_overrides.get(update.tokenId, effect_sheet.conditions))
                update.conditions = rested_conditions
                if resolution.targetSheetId == update.sheetId:
                    resolution.targetConditions = rested_conditions
                persistent_effect_changed = True
                continue
            if not isinstance(effect, MaximumHitPointsEffect):
                continue
            amount = max(0, applied.amount or 0)
            if amount <= 0:
                continue
            source_spell_id = enum_value(SpellId, resolution.roll.source.sourceId) or SpellId.AID
            if effect.operation == MaximumHitPointsOperation.REDUCE:
                existing_reductions = room.max_hit_point_reductions.setdefault(update.tokenId, [])
                existing_reductions.append(
                    ActiveMaxHitPointReduction(
                        amount=amount,
                        reset=effect.reset,
                        sourceSpellId=source_spell_id,
                        sourceName=resolution.roll.sourceLabel,
                    )
                )
                persistent_effect_changed = True
                continue
            existing = room.max_hit_point_increases.setdefault(update.tokenId, [])
            existing[:] = [active for active in existing if active.sourceSpellId != source_spell_id]
            existing.append(
                ActiveMaxHitPointIncrease(
                    amount=amount,
                    sourceSpellId=source_spell_id,
                    sourceName=resolution.roll.sourceLabel,
                )
            )
            persistent_effect_changed = True
    if persistent_effect_changed:
        save_room_to_disk(room)


def apply_dead_condition_after_damage(resolution: RollResolution) -> str | None:
    if not roll_can_apply_damage(resolution.roll):
        return None
    if resolution.targetHp.current > 0 or ConditionType.DEAD in resolution.targetConditions:
        return None
    resolution.targetConditions = normalized_conditions([*resolution.targetConditions, ConditionType.DEAD])
    return f"{resolution.targetName} gains {enum_label(ConditionType.DEAD)}"








def hit_point_damage_taken(before: HitPoints, after: HitPoints) -> int:
    return max(0, before.current - after.current) + max(0, before.temporary - after.temporary)


def dedupe_response_rolls(response_rolls: list[RollPayload]) -> list[RollPayload]:
    deduped: list[RollPayload] = []
    seen: set[str] = set()
    for response_roll in response_rolls:
        if response_roll.id in seen:
            continue
        seen.add(response_roll.id)
        deduped.append(response_roll)
    return deduped


def unique_text(values) -> list[str]:
    unique: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        unique.append(value)
    return unique


def resolve_damage_save_for_roll(roll: RollPayload, target: CharacterSheet) -> tuple[str | None, RollPayload | None, RollPayload]:
    if (
        (roll.resolution != RollResolutionMode.APPLY_DAMAGE and roll.pendingEffect is None)
        or roll.damageSavingThrow is None
        or roll.damageSaveDc is None
        or roll.damageSaveOutcome is None
        or roll.damageSaveOutcome == SpellSaveOutcome.NONE
    ):
        return None, None, roll
    if roll.damageSaveSucceeded is not None:
        if not roll.damageSaveSucceeded:
            return f"{target.name} previously failed the DC {roll.damageSaveDc} {enum_label(roll.damageSavingThrow)} save", None, roll
        if roll.damageSaveOutcome == SpellSaveOutcome.HALF_DAMAGE:
            return (
                f"{target.name} previously passed the DC {roll.damageSaveDc} {enum_label(roll.damageSavingThrow)} save for half damage",
                None,
                replace(roll, damageSaveSucceeded=True),
            )
        if roll.damageSaveOutcome == SpellSaveOutcome.NEGATES:
            return (
                f"{target.name} previously passed the DC {roll.damageSaveDc} {enum_label(roll.damageSavingThrow)} save and takes no damage",
                None,
                replace(roll, total=0, damageComponents=None, damageSaveSucceeded=True),
            )
        return f"{target.name} previously passed the DC {roll.damageSaveDc} {enum_label(roll.damageSavingThrow)} save", None, replace(roll, damageSaveSucceeded=True)
    disadvantage = damage_save_disadvantage_applies(roll, target)
    response_roll = response_ability_roll(
        sheet=target,
        ability=roll.damageSavingThrow,
        action_id="save",
        label=f"{enum_label(roll.damageSavingThrow)} Save",
        source_label=roll.label,
        modifier=save_modifier(target, roll.damageSavingThrow),
        disadvantage=disadvantage,
        pending_conditions=added_condition_types(roll.pendingEffect),
    )
    save_label = roll_advantage_log_label(response_roll)
    forced_failure = damage_save_forced_failure_applies(roll, target)
    forced_failure_conditions = condition_saving_throw_forced_failure_conditions(target, roll.damageSavingThrow)
    forced_failure_label = damage_save_forced_failure_label(target, forced_failure, forced_failure_conditions)
    if forced_failure or forced_failure_conditions or response_roll.total < roll.damageSaveDc:
        return f"{target.name} fails DC {roll.damageSaveDc} {enum_label(roll.damageSavingThrow)} save{save_label}{forced_failure_label}", response_roll, replace(roll, damageSaveSucceeded=False)
    if roll.damageSaveOutcome == SpellSaveOutcome.HALF_DAMAGE:
        return (
            f"{target.name} passes DC {roll.damageSaveDc} {enum_label(roll.damageSavingThrow)} save{save_label} for half damage",
            response_roll,
            replace(roll, damageSaveSucceeded=True),
        )
    if roll.damageSaveOutcome == SpellSaveOutcome.NEGATES:
        return (
            f"{target.name} passes DC {roll.damageSaveDc} {enum_label(roll.damageSavingThrow)} save{save_label} and takes no damage",
            response_roll,
            replace(roll, total=0, damageComponents=None, damageSaveSucceeded=True),
        )
    return f"{target.name} passes DC {roll.damageSaveDc} {enum_label(roll.damageSavingThrow)} save{save_label}", response_roll, replace(roll, damageSaveSucceeded=True)


def resolve_damage_save_prompt_against_target(roll: RollPayload, target: CharacterSheet) -> RollResolution:
    assert roll.damageSavingThrow is not None
    assert roll.damageSaveDc is not None
    disadvantage = damage_save_disadvantage_applies(roll, target)
    response_roll = response_ability_roll(
        sheet=target,
        ability=roll.damageSavingThrow,
        action_id="save",
        label=f"{enum_label(roll.damageSavingThrow)} Save",
        source_label=roll.sourceLabel,
        modifier=save_modifier(target, roll.damageSavingThrow),
        disadvantage=disadvantage,
        pending_conditions=added_condition_types(roll.pendingEffect),
    )
    save_label = roll_advantage_log_label(response_roll)
    forced_failure = damage_save_forced_failure_applies(roll, target)
    forced_failure_conditions = condition_saving_throw_forced_failure_conditions(target, roll.damageSavingThrow)
    forced_failure_label = damage_save_forced_failure_label(target, forced_failure, forced_failure_conditions)
    if forced_failure or forced_failure_conditions or response_roll.total < roll.damageSaveDc:
        outcome = f"{target.name} fails DC {roll.damageSaveDc} {enum_label(roll.damageSavingThrow)} save{save_label}{forced_failure_label}; resolve failed-save damage/effects next"
    else:
        outcome = f"{target.name} passes DC {roll.damageSaveDc} {enum_label(roll.damageSavingThrow)} save{save_label}; resolve passed-save damage/effects next"
    return RollResolution(
        id=f"resolution-{time_ns()}",
        roll=response_roll,
        targetSheetId=target.id,
        targetTokenId=target.tokenId,
        targetName=target.name,
        targetArmorClass=target.armorClass,
        targetHp=target.hp,
        targetConditions=target.conditions,
        outcome=outcome,
        createdAt=time_ns(),
    )


def damage_save_disadvantage_applies(roll: RollPayload, target: CharacterSheet) -> bool:
    return bool(roll.damageSaveDisadvantageCreatureTypes and set(roll.damageSaveDisadvantageCreatureTypes).intersection(target.creatureTypes))


def damage_save_forced_failure_applies(roll: RollPayload, target: CharacterSheet) -> bool:
    return bool(roll.damageSaveForcedFailureCreatureTypes and set(roll.damageSaveForcedFailureCreatureTypes).intersection(target.creatureTypes))


def damage_save_forced_failure_label(target: CharacterSheet, creature_type_forced_failure: bool, condition_forced_failures: list[ConditionType]) -> str:
    labels = []
    if creature_type_forced_failure:
        labels.append(creature_type_list_label(target.creatureTypes))
    labels.extend(enum_label(condition) for condition in condition_forced_failures)
    return f" due to {text_list_label(labels)}" if labels else ""


def resolve_damage_triggered_condition_saves(
    room: Room,
    roll: RollPayload,
    target: CharacterSheet,
    resolution: RollResolution,
) -> list[tuple[str, list[ConditionType], RollPayload]]:
    if not roll_can_apply_damage(roll) or not damage_was_taken(target.hp, resolution.targetHp):
        return []
    removals = room.condition_removals.get(target.id, {})
    active_conditions = set(target.conditions)
    grouped_removals: dict[tuple[AbilityType, int, bool], list[ConditionType]] = {}
    for condition, removal in removals.items():
        if condition in active_conditions:
            grouped_removals.setdefault((removal.savingThrow, removal.saveDc, removal.advantage), []).append(condition)

    outcomes: list[tuple[str, list[ConditionType], RollPayload]] = []
    for (saving_throw, save_dc, advantage), conditions in grouped_removals.items():
        response_roll = response_ability_roll(
            sheet=target,
            ability=saving_throw,
            action_id="damage-save",
            label=f"{enum_label(saving_throw)} Save",
            source_label="Damage",
            modifier=save_modifier(target, saving_throw),
            advantage=advantage,
            advantage_conditions=[ConditionType.PROTECTION_FROM_POISON] if advantage else None,
        )
        condition_label = text_list_label([enum_label(condition) for condition in conditions])
        advantage_label = roll_advantage_log_label(response_roll)
        forced_failure_conditions = condition_saving_throw_forced_failure_conditions(target, saving_throw)
        forced_failure_label = f" due to {text_list_label([enum_label(condition) for condition in forced_failure_conditions])}" if forced_failure_conditions else ""
        if not forced_failure_conditions and response_roll.total >= save_dc:
            outcomes.append(
                (
                    f"{target.name} passes DC {save_dc} {enum_label(saving_throw)} save{advantage_label} after taking damage and ends {condition_label}",
                    conditions,
                    response_roll,
                )
            )
        else:
            outcomes.append(
                (
                    f"{target.name} fails DC {save_dc} {enum_label(saving_throw)} save{advantage_label}{forced_failure_label} after taking damage; {condition_label} remains",
                    [],
                    response_roll,
                )
            )
    return outcomes


def damage_was_taken(before: HitPoints, after: HitPoints) -> bool:
    return after.current < before.current or after.temporary < before.temporary


def text_list_label(values: list[str]) -> str:
    if len(values) <= 1:
        return values[0] if values else ""
    return f"{', '.join(values[:-1])}, and {values[-1]}"


def source_sheet_for_roll(room: Room, roll: RollPayload) -> CharacterSheet | None:
    token = room.tokens.get(roll.tokenId)
    if token is None:
        return None
    return token_to_sheet(token, room.id, room.hit_points.get(token.id))


def response_ability_roll(
    *,
    sheet: CharacterSheet,
    ability: AbilityType,
    action_id: str,
    label: str,
    source_label: str,
    modifier: int,
    advantage: bool = False,
    disadvantage: bool = False,
    advantage_conditions: list[ConditionType] | None = None,
    disadvantage_conditions: list[ConditionType] | None = None,
    saving_throw_conditions: bool = True,
    modifier_target: RollModifierEffectTarget = RollModifierEffectTarget.SAVING_THROW,
    pending_conditions: list[ConditionType] | None = None,
) -> RollPayload:
    if saving_throw_conditions:
        advantage_conditions = (advantage_conditions or []) + condition_saving_throw_advantage_conditions(sheet, ability, pending_conditions)
        disadvantage_conditions = (disadvantage_conditions or []) + condition_saving_throw_disadvantage_conditions(sheet, ability)
    has_advantage = (advantage or bool(advantage_conditions)) and not (disadvantage or disadvantage_conditions)
    has_disadvantage = (disadvantage or bool(disadvantage_conditions)) and not (advantage or advantage_conditions)
    dice = [random.randint(1, 20)]
    if has_advantage or has_disadvantage:
        dice.append(random.randint(1, 20))
    die_roll = min(dice) if has_disadvantage else max(dice)
    created_at = time_ns()
    modifier_breakdown = [RollModifierBreakdown(source=label, value=modifier)] if modifier else []
    modifier_breakdown.extend(active_roll_modifier_breakdown(sheet, modifier_target, ability))
    total_modifier = sum(part.value for part in modifier_breakdown)
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
        dice=dice,
        diceType=DiceType.D20,
        die="2d20kl1" if has_disadvantage else "2d20kh1" if has_advantage else enum_key(DiceType.D20),
        modifier=total_modifier,
        modifierBreakdown=modifier_breakdown,
        total=die_roll + total_modifier,
        createdAt=created_at,
        advantageConditions=advantage_conditions or None,
        disadvantageConditions=disadvantage_conditions or None,
    )


def roll_advantage_log_label(roll: RollPayload) -> str:
    if roll.die == "2d20kh1":
        return " with Advantage"
    if roll.die == "2d20kl1":
        return " with Disadvantage"
    return ""


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
    return normalized_conditions(next_conditions)


def active_concentration_status(active: ActiveConcentration | None) -> ActiveConcentrationStatus | None:
    if active is None:
        return None
    return ActiveConcentrationStatus(spellId=active.spellId, spellName=active.spellName)


def resolve_concentration_save_after_damage(room: Room, target: CharacterSheet, resolution: RollResolution) -> tuple[str | None, RollPayload | None]:
    active = room.active_concentrations.get(target.id)
    damage_taken = hit_point_damage_taken(target.hp, resolution.targetHp)
    if active is None or damage_taken <= 0:
        return None, None
    if ConditionType.DEAD in resolution.targetConditions:
        removed_conditions = clear_active_concentration(room, target.id)
        removed_label = f" and removes {text_list_label(removed_conditions)}" if removed_conditions else ""
        return f"{target.name} is {enum_label(ConditionType.DEAD)}; {active.spellName} ends{removed_label}", None
    save_dc = max(10, damage_taken // 2)
    response_roll = response_ability_roll(
        sheet=target,
        ability=AbilityType.CONSTITUTION,
        action_id="concentration-save",
        label="Concentration Save",
        source_label=active.spellName,
        modifier=save_modifier(target, AbilityType.CONSTITUTION),
        modifier_target=RollModifierEffectTarget.CONCENTRATION_SAVE,
    )
    advantage_label = roll_advantage_log_label(response_roll)
    if response_roll.total >= save_dc:
        return f"{target.name} passes DC {save_dc} Concentration save{advantage_label} for {active.spellName}", response_roll
    removed_conditions = clear_active_concentration(room, target.id)
    removed_label = f" and removes {text_list_label(removed_conditions)}" if removed_conditions else ""
    return f"{target.name} fails DC {save_dc} Concentration save{advantage_label}; {active.spellName} ends{removed_label}", response_roll


def concentration_spell_for_roll(source: CharacterSheet | None, roll: RollPayload) -> SpellEntry | None:
    if source is None or roll.source.section != SheetSectionType.SPELLS:
        return None
    spell_id = enum_value(SpellId, roll.source.sourceId)
    if spell_id is None:
        return None
    spell = next((candidate for candidate in source.spells if candidate.id == spell_id), None)
    return spell if spell is not None and spell.concentration else None


def clear_active_concentration(room: Room, caster_sheet_id: str) -> list[str]:
    from dnd_board.rules.shared.character_effects import ongoing_effects_after_ending

    active = room.active_concentrations.pop(caster_sheet_id, None)
    ongoing_changed = False
    for target_sheet_id, effects in list(room.ongoing_effects.items()):
        remaining = ongoing_effects_after_ending(
            effects,
            EndingConditionType.SOURCE_CONCENTRATION_ENDS,
            source_sheet_id=caster_sheet_id,
        )
        if remaining != effects:
            room.ongoing_effects[target_sheet_id] = remaining
            ongoing_changed = True
    if active is None:
        if ongoing_changed:
            save_room_to_disk(room)
        return []
    removed: list[str] = []
    for source in active.conditionSources:
        remaining_sources = [
            other_source
            for concentration in room.active_concentrations.values()
            for other_source in concentration.conditionSources
            if other_source.targetSheetId == source.targetSheetId and other_source.condition == source.condition
        ]
        if source.wasAlreadyActive or remaining_sources:
            continue
        current_conditions = room.condition_overrides.get(source.targetSheetId) or sheet_conditions(source.targetSheetId, room.id)
        next_conditions = [condition for condition in current_conditions if condition != source.condition]
        if next_conditions != current_conditions:
            room.condition_overrides[source.targetSheetId] = next_conditions
            room.condition_durations.setdefault(source.targetSheetId, {}).pop(source.condition, None)
            room.condition_removals.setdefault(source.targetSheetId, {}).pop(source.condition, None)
            update_party_member_config(room.id, source.targetSheetId, lambda updated, conditions=next_conditions: set_member_conditions(updated, conditions))
            removed.append(enum_label(source.condition))
    if ongoing_changed:
        save_room_to_disk(room)
    return removed


def sheet_conditions(sheet_id: str, campaign_id: str) -> list[ConditionType]:
    manifest = load_party_manifest_config(campaign_asset_dir("party", campaign_id) / "party.json")
    if manifest is None:
        return []
    member = next((candidate for candidate in manifest.members if candidate.id == sheet_id), None)
    if member is None or member.sheet is None or member.sheet.conditions is None:
        return []
    return list(member.sheet.conditions)


def remove_active_condition_sources(room: Room, target_sheet_id: str, condition: ConditionType) -> None:
    for caster_sheet_id, concentration in list(room.active_concentrations.items()):
        concentration.conditionSources = [
            source
            for source in concentration.conditionSources
            if source.targetSheetId != target_sheet_id or source.condition != condition
        ]
        if not concentration.conditionSources:
            room.active_concentrations.pop(caster_sheet_id, None)


def record_active_concentration_conditions(
    room: Room,
    source: CharacterSheet | None,
    target_sheet_id: str,
    previous_conditions: list[ConditionType],
    conditions: list[ConditionType],
    roll: RollPayload,
) -> None:
    spell = concentration_spell_for_roll(source, roll)
    if spell is None:
        return
    caster_sheet_id = source.id
    active = room.active_concentrations.get(caster_sheet_id)
    if active is not None and active.spellId != spell.id:
        clear_active_concentration(room, caster_sheet_id)
        active = None
    if active is None:
        active = ActiveConcentration(casterSheetId=caster_sheet_id, spellId=spell.id, spellName=enum_label(spell.name), conditionSources=[])
        room.active_concentrations[caster_sheet_id] = active
    active_conditions = set(conditions)
    previous_condition_set = set(previous_conditions)
    existing_source_keys = {(source_record.targetSheetId, source_record.condition) for source_record in active.conditionSources}
    applied_conditions = added_condition_types(roll.pendingEffect)
    for condition in dict.fromkeys(applied_conditions):
        if condition not in active_conditions:
            continue
        source_key = (target_sheet_id, condition)
        if source_key in existing_source_keys:
            continue
        active.conditionSources.append(
            ActiveConditionSource(
                targetSheetId=target_sheet_id,
                condition=condition,
                spellId=spell.id,
                casterSheetId=caster_sheet_id,
                wasAlreadyActive=condition in previous_condition_set,
            )
        )


def apply_resolved_conditions(room: Room, sheet_id: str, previous_conditions: list[ConditionType], conditions: list[ConditionType], roll: RollPayload, source: CharacterSheet | None) -> None:
    room.condition_overrides[sheet_id] = list(conditions)
    active_conditions = set(conditions)
    durations = room.condition_durations.setdefault(sheet_id, {})
    removals = room.condition_removals.setdefault(sheet_id, {})
    for condition in list(durations):
        if condition not in active_conditions:
            durations.pop(condition, None)
    for condition in list(removals):
        if condition not in active_conditions:
            removals.pop(condition, None)
    from dnd_board.rules.shared.character_effects import condition_change_effects

    for effect in condition_change_effects(roll.pendingEffect):
        if effect.operation != ConditionOperation.ADD or effect.condition not in active_conditions:
            continue
        if effect.duration is not None:
            duration = {
                EffectDurationType.UNTIL_SHORT_REST: ConditionDuration.UNTIL_SHORT_REST,
                EffectDurationType.UNTIL_LONG_REST: ConditionDuration.UNTIL_LONG_REST,
            }.get(effect.duration.durationType, ConditionDuration.MANUAL)
            durations[effect.condition] = duration
        ending = next(
            (
                ending
                for ending in effect.endingConditions
                if ending.endingCondition == EndingConditionType.TARGET_TAKES_DAMAGE and ending.savingThrow is not None
            ),
            None,
        )
        if ending is not None and roll.damageSaveDc is not None:
            removals[effect.condition] = ConditionRemovalSave(
                savingThrow=ending.savingThrow.ability,
                saveDc=roll.damageSaveDc,
                advantage=ending.advantage,
            )
    record_active_concentration_conditions(room, source, sheet_id, previous_conditions, conditions, roll)
    update_party_member_config(room.id, sheet_id, lambda updated: set_member_conditions(updated, conditions))


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
        "activeConcentrations": active_concentrations_to_dict(room.active_concentrations),
        "suppressedConditions": {
            sheet_id: [enum_key(condition) for condition in conditions]
            for sheet_id, conditions in room.suppressed_conditions.items()
            if conditions
        },
        "ongoingEffects": {
            sheet_id: [typed_json_from_value(effect) for effect in effects]
            for sheet_id, effects in room.ongoing_effects.items()
            if effects
        },
        "scheduledEffects": {
            sheet_id: [typed_json_from_value(effect) for effect in effects]
            for sheet_id, effects in room.scheduled_effects.items()
            if effects
        },
        "maxHitPointIncreases": max_hit_point_increases_to_dict(room.max_hit_point_increases),
        "maxHitPointReductions": max_hit_point_reductions_to_dict(room.max_hit_point_reductions),
        "exhaustionLevels": room.exhaustion_levels,
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def save_room_if_concentration_changed(room: Room, resolution: RollResolution) -> None:
    if resolution.concentrationUpdates:
        save_room_to_disk(room)


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
    room.pending_resolution_prompts = {}
    room.pending_effect_executions = {}
    room.roll_history = []
    room.hit_points = {}
    room.temporary_hit_points = {}
    room.max_hit_point_increases = load_saved_max_hit_point_increases(room.id)
    room.max_hit_point_reductions = load_saved_max_hit_point_reductions(room.id)
    room.exhaustion_levels = load_saved_exhaustion_levels(room.id)
    room.condition_overrides = {}
    room.suppressed_conditions = load_saved_suppressed_conditions(room.id)
    room.condition_durations = {}
    room.condition_removals = {}
    room.active_concentrations = load_saved_active_concentrations(room.id)
    room.damage_resistances = {}
    room.damage_vulnerabilities = {}
    room.damage_immunities = {}
    room.resource_uses = load_saved_resource_uses(room.id)
    room.equipment_slots = {}
    room.ongoing_effects = load_saved_ongoing_effects(room.id)
    room.scheduled_effects = load_saved_scheduled_effects(room.id)
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


def load_saved_exhaustion_levels(room_id: str) -> dict[str, int]:
    path = existing_save_path(room_id)
    if not path.exists():
        return {}

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    raw_levels = data.get("exhaustionLevels")
    if not isinstance(raw_levels, dict):
        return {}

    levels: dict[str, int] = {}
    for raw_sheet_id, raw_level in raw_levels.items():
        sheet_id = sanitize_asset_id(str(raw_sheet_id))
        try:
            level = clamp_int(int(raw_level), 0, 6)
        except (TypeError, ValueError):
            continue
        if sheet_id and level > 0:
            levels[sheet_id] = level
    return levels


def load_saved_suppressed_conditions(room_id: str) -> dict[str, list[ConditionType]]:
    path = existing_save_path(room_id)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    raw_by_sheet = data.get("suppressedConditions")
    if not isinstance(raw_by_sheet, dict):
        return {}
    loaded: dict[str, list[ConditionType]] = {}
    for raw_sheet_id, raw_conditions in raw_by_sheet.items():
        if not isinstance(raw_conditions, list):
            continue
        sheet_id = sanitize_asset_id(str(raw_sheet_id))
        conditions = [
            condition
            for raw_condition in raw_conditions
            if (condition := enum_value(ConditionType, raw_condition)) is not None
        ]
        if sheet_id and conditions:
            loaded[sheet_id] = list(dict.fromkeys(conditions))
    return loaded


def max_hit_point_reductions_to_dict(reductions: dict[str, list[ActiveMaxHitPointReduction]]) -> dict[str, Any]:
    return {
        sheet_id: [
            {
                "amount": reduction.amount,
                "sourceSpellId": enum_key(reduction.sourceSpellId),
                "sourceName": reduction.sourceName,
                "reset": enum_key(reduction.reset),
            }
            for reduction in sheet_reductions
        ]
        for sheet_id, sheet_reductions in reductions.items()
        if sheet_reductions
    }


def max_hit_point_increases_to_dict(increases: dict[str, list[ActiveMaxHitPointIncrease]]) -> dict[str, Any]:
    return {
        sheet_id: [
            {
                "amount": increase.amount,
                "sourceSpellId": enum_key(increase.sourceSpellId),
                "sourceName": increase.sourceName,
            }
            for increase in sheet_increases
        ]
        for sheet_id, sheet_increases in increases.items()
        if sheet_increases
    }


def load_saved_max_hit_point_increases(room_id: str) -> dict[str, list[ActiveMaxHitPointIncrease]]:
    path = existing_save_path(room_id)
    if not path.exists():
        return {}

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    raw_increases = data.get("maxHitPointIncreases")
    if not isinstance(raw_increases, dict):
        return {}

    increases: dict[str, list[ActiveMaxHitPointIncrease]] = {}
    for raw_sheet_id, raw_sheet_increases in raw_increases.items():
        if not isinstance(raw_sheet_increases, list):
            continue
        sheet_id = sanitize_asset_id(str(raw_sheet_id))
        sheet_increases: list[ActiveMaxHitPointIncrease] = []
        for raw_increase in raw_sheet_increases:
            if not isinstance(raw_increase, dict):
                continue
            source_spell_id = enum_value(SpellId, raw_increase.get("sourceSpellId"))
            try:
                amount = max(0, int(raw_increase.get("amount")))
            except (TypeError, ValueError):
                continue
            if not sheet_id or source_spell_id is None or amount <= 0:
                continue
            sheet_increases.append(
                ActiveMaxHitPointIncrease(
                    amount=amount,
                    sourceSpellId=source_spell_id,
                    sourceName=str(raw_increase.get("sourceName") or enum_label(source_spell_id)),
                )
            )
        if sheet_increases:
            increases[sheet_id] = sheet_increases
    return increases


def load_saved_max_hit_point_reductions(room_id: str) -> dict[str, list[ActiveMaxHitPointReduction]]:
    path = existing_save_path(room_id)
    if not path.exists():
        return {}

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    raw_reductions = data.get("maxHitPointReductions")
    if not isinstance(raw_reductions, dict):
        return {}

    reductions: dict[str, list[ActiveMaxHitPointReduction]] = {}
    for raw_sheet_id, raw_sheet_reductions in raw_reductions.items():
        if not isinstance(raw_sheet_reductions, list):
            continue
        sheet_id = sanitize_asset_id(str(raw_sheet_id))
        sheet_reductions: list[ActiveMaxHitPointReduction] = []
        for raw_reduction in raw_sheet_reductions:
            if not isinstance(raw_reduction, dict):
                continue
            source_spell_id = enum_value(SpellId, raw_reduction.get("sourceSpellId"))
            reset = enum_value(RestType, raw_reduction.get("reset"))
            try:
                amount = max(0, int(raw_reduction.get("amount")))
            except (TypeError, ValueError):
                continue
            if not sheet_id or source_spell_id is None or reset is None or amount <= 0:
                continue
            sheet_reductions.append(
                ActiveMaxHitPointReduction(
                    amount=amount,
                    sourceSpellId=source_spell_id,
                    sourceName=str(raw_reduction.get("sourceName") or enum_label(source_spell_id)),
                    reset=reset,
                )
            )
        if sheet_reductions:
            reductions[sheet_id] = sheet_reductions
    return reductions


def active_concentrations_to_dict(active_concentrations: dict[str, ActiveConcentration]) -> dict[str, Any]:
    return {
        sheet_id: {
            "casterSheetId": concentration.casterSheetId,
            "spellId": enum_key(concentration.spellId),
            "spellName": concentration.spellName,
            "conditionSources": [
                {
                    "targetSheetId": source.targetSheetId,
                    "condition": enum_key(source.condition),
                    "spellId": enum_key(source.spellId),
                    "casterSheetId": source.casterSheetId,
                    "wasAlreadyActive": source.wasAlreadyActive,
                }
                for source in concentration.conditionSources
            ],
        }
        for sheet_id, concentration in active_concentrations.items()
    }


def load_saved_active_concentrations(room_id: str) -> dict[str, ActiveConcentration]:
    path = existing_save_path(room_id)
    if not path.exists():
        return {}

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    raw_active_concentrations = data.get("activeConcentrations")
    if not isinstance(raw_active_concentrations, dict):
        return {}

    active_concentrations: dict[str, ActiveConcentration] = {}
    for raw_sheet_id, raw_concentration in raw_active_concentrations.items():
        if not isinstance(raw_concentration, dict):
            continue
        sheet_id = sanitize_asset_id(str(raw_sheet_id))
        spell_id = enum_value(SpellId, raw_concentration.get("spellId"))
        if not sheet_id or spell_id is None:
            continue
        caster_sheet_id = sanitize_asset_id(str(raw_concentration.get("casterSheetId", sheet_id)))
        condition_sources: list[ActiveConditionSource] = []
        for raw_source in raw_concentration.get("conditionSources", []):
            if not isinstance(raw_source, dict):
                continue
            condition = enum_value(ConditionType, raw_source.get("condition"))
            source_spell_id = enum_value(SpellId, raw_source.get("spellId"))
            target_sheet_id = sanitize_asset_id(str(raw_source.get("targetSheetId", "")))
            source_caster_sheet_id = sanitize_asset_id(str(raw_source.get("casterSheetId", caster_sheet_id)))
            if condition is None or source_spell_id is None or not target_sheet_id or not source_caster_sheet_id:
                continue
            condition_sources.append(
                ActiveConditionSource(
                    targetSheetId=target_sheet_id,
                    condition=condition,
                    spellId=source_spell_id,
                    casterSheetId=source_caster_sheet_id,
                    wasAlreadyActive=bool(raw_source.get("wasAlreadyActive", False)),
                )
            )
        active_concentrations[sheet_id] = ActiveConcentration(
            casterSheetId=caster_sheet_id,
            spellId=spell_id,
            spellName=str(raw_concentration.get("spellName") or enum_label(spell_id)),
            conditionSources=condition_sources,
        )
    return active_concentrations


def load_saved_ongoing_effects(room_id: str) -> dict[str, list[ActiveOngoingEffect]]:
    path = existing_save_path(room_id)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    raw_by_sheet = data.get("ongoingEffects")
    if not isinstance(raw_by_sheet, dict):
        return {}
    loaded: dict[str, list[ActiveOngoingEffect]] = {}
    for raw_sheet_id, raw_effects in raw_by_sheet.items():
        if not isinstance(raw_effects, list):
            continue
        sheet_id = sanitize_asset_id(str(raw_sheet_id))
        effects = [
            effect
            for raw_effect in raw_effects
            if isinstance((effect := typed_json_to_value(raw_effect, ActiveOngoingEffect)), ActiveOngoingEffect)
            and effect.targetSheetId == sheet_id
        ]
        if sheet_id and effects:
            loaded[sheet_id] = effects
    return loaded


def load_saved_scheduled_effects(room_id: str) -> dict[str, list[ActiveScheduledEffect]]:
    path = existing_save_path(room_id)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    raw_by_sheet = data.get("scheduledEffects")
    if not isinstance(raw_by_sheet, dict):
        return {}
    loaded: dict[str, list[ActiveScheduledEffect]] = {}
    for raw_sheet_id, raw_effects in raw_by_sheet.items():
        if not isinstance(raw_effects, list):
            continue
        sheet_id = sanitize_asset_id(str(raw_sheet_id))
        effects = [
            effect
            for raw_effect in raw_effects
            if isinstance((effect := typed_json_to_value(raw_effect, ActiveScheduledEffect)), ActiveScheduledEffect)
            and effect.targetSheetId == sheet_id
        ]
        if sheet_id and effects:
            loaded[sheet_id] = effects
    return loaded


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
    prune_member_wizard_spells(member)


def set_member_condition(member: PartyMemberConfig, condition: ConditionType, active: bool) -> None:
    if member.sheet is None:
        member.sheet = PartyMemberSheet()
    member.sheet.conditions = updated_conditions(member.sheet.conditions or [], condition, active) or None


def updated_conditions(conditions: list[ConditionType], condition: ConditionType, active: bool) -> list[ConditionType]:
    if active and condition not in conditions:
        return normalized_conditions([*conditions, condition])
    if not active:
        return [candidate for candidate in conditions if candidate != condition]
    return normalized_conditions(list(conditions))


def normalized_conditions(conditions: list[ConditionType]) -> list[ConditionType]:
    next_conditions = list(conditions)
    if ConditionType.PROTECTION_FROM_POISON in next_conditions and ConditionType.POISONED in next_conditions:
        next_conditions = [condition for condition in next_conditions if condition != ConditionType.POISONED]
    return next_conditions


def set_member_conditions(member: PartyMemberConfig, conditions: list[ConditionType]) -> None:
    if member.sheet is None:
        member.sheet = PartyMemberSheet()
    member.sheet.conditions = conditions or None


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


def apply_member_wizard_cantrips(member: PartyMemberConfig, values: list[str]) -> None:
    from dnd_board.rules.classes.wizard.base import is_wizard_cantrip_selection_valid

    wizard = next((character_class for character_class in member_sheet_classes(member) if character_class.name == ClassType.WIZARD), None)
    if wizard is None or wizard.level < 1:
        raise HTTPException(status_code=400, detail="Wizard spellcasting is not available")

    spells = wizard_spells_from_values(values)
    if not is_wizard_cantrip_selection_valid(wizard.level, spells):
        raise HTTPException(status_code=400, detail="Choose legal Wizard cantrips")

    if member.sheet is None:
        member.sheet = PartyMemberSheet(classes=[wizard])
    other_spells = [spell for spell in member.sheet.spells or [] if spell.source != SpellSource.WIZARD or spell.level > 0]
    member.sheet.spells = [*other_spells, *spells]


def apply_member_wizard_spellbook_spells(member: PartyMemberConfig, values: list[str]) -> None:
    from dnd_board.rules.classes.wizard.base import is_wizard_spellbook_selection_valid

    wizard = next((character_class for character_class in member_sheet_classes(member) if character_class.name == ClassType.WIZARD), None)
    if wizard is None or wizard.level < 1:
        raise HTTPException(status_code=400, detail="Wizard spellbook is not available")

    spells = wizard_spells_from_values(values)
    if not is_wizard_spellbook_selection_valid(wizard.level, spells):
        raise HTTPException(status_code=400, detail="Choose legal Wizard spellbook spells")

    if member.sheet is None:
        member.sheet = PartyMemberSheet(classes=[wizard])
    member.sheet.spellbook = spells
    member.sheet.spells = [
        spell
        for spell in member.sheet.spells or []
        if spell.source != SpellSource.WIZARD or spell.level == 0 or any(spell.id == spellbook_spell.id for spellbook_spell in spells)
    ]


def apply_member_wizard_prepared_spells(member: PartyMemberConfig, values: list[str]) -> None:
    from dnd_board.rules.classes.wizard.base import is_wizard_prepared_spell_selection_valid

    wizard = next((character_class for character_class in member_sheet_classes(member) if character_class.name == ClassType.WIZARD), None)
    if wizard is None or wizard.level < 1:
        raise HTTPException(status_code=400, detail="Wizard spellcasting is not available")

    spells = wizard_spells_from_values(values)
    if not is_wizard_prepared_spell_selection_valid(wizard.level, spells):
        raise HTTPException(status_code=400, detail="Choose legal prepared Wizard spells")
    spellbook_ids = {spell.id for spell in member.sheet.spellbook or []} if member.sheet else set()
    if spellbook_ids and any(spell.id not in spellbook_ids for spell in spells):
        raise HTTPException(status_code=400, detail="Prepared Wizard spells must be in your spellbook")

    if member.sheet is None:
        member.sheet = PartyMemberSheet(classes=[wizard])
    other_spells = [spell for spell in member.sheet.spells or [] if spell.source != SpellSource.WIZARD or spell.level == 0]
    member.sheet.spells = [*other_spells, *spells]


def wizard_spells_from_values(values: list[str]) -> list[SpellEntry]:
    from dnd_board.rules.classes.wizard.base import wizard_catalog_spell

    spells = []
    for spell_id in unique_clean_values(values):
        spell = wizard_catalog_spell(spell_id)
        if spell is None:
            raise HTTPException(status_code=400, detail="Invalid Wizard spell")
        spells.append(spell)
    return spells


def apply_member_fighter_skill_proficiencies(member: PartyMemberConfig, values: list[str]) -> None:
    fighter = next((character_class for character_class in member_sheet_classes(member) if character_class.name == ClassType.FIGHTER), None)
    if fighter is None or fighter.level < 1:
        raise HTTPException(status_code=400, detail="Fighter skill proficiencies are not available")

    selected_skills = parse_skill_choices(values)
    expected_count = fighter_skill_proficiency_count(fighter)
    if len(selected_skills) != expected_count:
        raise HTTPException(status_code=400, detail=f"Choose {expected_count} Fighter skill proficiencies")

    fighter_options = set(fighter_skill_option_types())
    if any(skill not in fighter_options for skill in selected_skills):
        raise HTTPException(status_code=400, detail="Invalid Fighter skill proficiency")

    if member.sheet is None:
        member.sheet = PartyMemberSheet(classes=[fighter])
    skills = dict(member.sheet.skills or {})
    for skill in selected_skills:
        skill_key = enum_key(skill)
        if skills.get(skill_key) != ProficiencyLevel.EXPERTISE:
            skills[skill_key] = ProficiencyLevel.PROFICIENT
    member.sheet.skills = skills or None


def apply_member_rogue_skill_proficiencies(member: PartyMemberConfig, values: list[str]) -> None:
    rogue = next((character_class for character_class in member_sheet_classes(member) if character_class.name == ClassType.ROGUE), None)
    if rogue is None or rogue.level < 1:
        raise HTTPException(status_code=400, detail="Rogue skill proficiencies are not available")

    selected_skills = parse_skill_choices(values)
    expected_count = rogue_skill_proficiency_count(rogue)
    if len(selected_skills) != expected_count:
        raise HTTPException(status_code=400, detail=f"Choose {expected_count} Rogue skill proficiencies")

    rogue_options = set(rogue_skill_option_types())
    if any(skill not in rogue_options for skill in selected_skills):
        raise HTTPException(status_code=400, detail="Invalid Rogue skill proficiency")

    if member.sheet is None:
        member.sheet = PartyMemberSheet(classes=[rogue])
    skills = dict(member.sheet.skills or {})
    for skill in selected_skills:
        skill_key = enum_key(skill)
        if skills.get(skill_key) != ProficiencyLevel.EXPERTISE:
            skills[skill_key] = ProficiencyLevel.PROFICIENT
    member.sheet.skills = skills or None


def apply_member_rogue_expertise(member: PartyMemberConfig, values: list[str]) -> None:
    rogue = next((character_class for character_class in member_sheet_classes(member) if character_class.name == ClassType.ROGUE), None)
    if rogue is None or rogue.level < 1:
        raise HTTPException(status_code=400, detail="Rogue Expertise is not available")

    selected_skills = parse_skill_choices(values)
    skills = dict(member.sheet.skills if member.sheet and member.sheet.skills else {})
    eligible_skill_keys = {
        skill_key
        for skill_key, proficiency in skills.items()
        if proficiency in {ProficiencyLevel.PROFICIENT, ProficiencyLevel.EXPERTISE}
    }
    expected_count = min(rogue_expertise_count(rogue), len(eligible_skill_keys))
    if len(selected_skills) != expected_count:
        raise HTTPException(status_code=400, detail=f"Choose {expected_count} Rogue Expertise skills")
    if any(enum_key(skill) not in eligible_skill_keys for skill in selected_skills):
        raise HTTPException(status_code=400, detail="Expertise requires an existing skill proficiency")

    if member.sheet is None:
        member.sheet = PartyMemberSheet(classes=[rogue])
    for skill in selected_skills:
        skills[enum_key(skill)] = ProficiencyLevel.EXPERTISE
    member.sheet.skills = skills or None


def apply_member_wizard_skill_proficiencies(member: PartyMemberConfig, values: list[str]) -> None:
    wizard = next((character_class for character_class in member_sheet_classes(member) if character_class.name == ClassType.WIZARD), None)
    if wizard is None or wizard.level < 1:
        raise HTTPException(status_code=400, detail="Wizard skill proficiencies are not available")

    selected_skills = parse_skill_choices(values)
    expected_count = wizard_skill_proficiency_count(wizard)
    if len(selected_skills) != expected_count:
        raise HTTPException(status_code=400, detail=f"Choose {expected_count} Wizard skill proficiencies")

    wizard_options = set(wizard_skill_option_types())
    if any(skill not in wizard_options for skill in selected_skills):
        raise HTTPException(status_code=400, detail="Invalid Wizard skill proficiency")

    if member.sheet is None:
        member.sheet = PartyMemberSheet(classes=[wizard])
    skills = dict(member.sheet.skills or {})
    for skill in selected_skills:
        skill_key = enum_key(skill)
        if skills.get(skill_key) != ProficiencyLevel.EXPERTISE:
            skills[skill_key] = ProficiencyLevel.PROFICIENT
    member.sheet.skills = skills or None


def parse_skill_choices(values: list[str]) -> list[SkillType]:
    selected: list[SkillType] = []
    for value in unique_clean_values(values):
        skill = enum_value(SkillType, value)
        if skill is None:
            raise HTTPException(status_code=400, detail="Invalid skill")
        selected.append(skill)
    return selected


def class_hit_point_bump(member: PartyMemberConfig, class_name: ClassType, choice: str) -> int:
    from dnd_board.rules.feats import GeneralFeatType

    constitution_modifier = member_constitution_modifier(member)
    hit_die = class_hit_die(class_name)
    feat_bonus = 2 if member_has_general_feat(member, GeneralFeatType.TOUGH) else 0
    if normalize_choice_id(choice) == "roll":
        return max(1, random.randint(1, hit_die) + constitution_modifier + feat_bonus)
    return max(1, (hit_die // 2 + 1) + constitution_modifier + feat_bonus)


def class_level_one_hit_points(class_name: ClassType) -> int:
    return class_hit_die(class_name)


def member_constitution_modifier(member: PartyMemberConfig) -> int:
    constitution = member.abilityScores.constitution if member.abilityScores else 10
    return ability_modifier(constitution)


def member_has_general_feat(member: PartyMemberConfig, feat_type) -> bool:
    from dnd_board.rules.feats import parse_general_feat

    if member.sheet is None:
        return False
    return any(parse_general_feat(feature.id) == feat_type for feature in member.sheet.feats or [])


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
    from dnd_board.rules.feats import FeatCategory, general_feat_category, general_feat_feature, parse_general_feat, selected_general_feat_keys

    feat_key = value.split(":", 1)[1] if ":" in value else value
    feat_type = parse_general_feat(feat_key)
    if feat_type is None:
        raise HTTPException(status_code=400, detail="Invalid feat")
    if general_feat_category(feat_type) != FeatCategory.GENERAL:
        raise HTTPException(status_code=400, detail="That feat is not available from this progression choice")
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
    from dnd_board.rules.feats import GeneralFeatType

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
            feat_type = GeneralFeatType.TOUGH if parse_feat_improvement(improvement) == enum_key(GeneralFeatType.TOUGH) else None
            if feat_type == GeneralFeatType.TOUGH and member.maxHp is not None:
                member.maxHp = max(1, member.maxHp - 2 * total_member_level(member))
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
    wizard = next((character_class for character_class in classes if character_class.name == ClassType.WIZARD), None)
    return (
        (fighter_asi_levels_up_to(fighter.level) if fighter is not None else 0)
        + (rogue_asi_levels_up_to(rogue.level) if rogue is not None else 0)
        + (wizard_asi_levels_up_to(wizard.level) if wizard is not None else 0)
    )


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
        member.sheet.spells = [
            spell
            for spell in member.sheet.spells
            if spell.source != SpellSource.ELDRITCH_KNIGHT or eldritch_knight_catalog_spell(spell.id) is None
        ] or None
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


def prune_member_wizard_spells(member: PartyMemberConfig) -> None:
    from dnd_board.rules.classes.wizard.base import pruned_wizard_spellbook, pruned_wizard_spells

    if member.sheet is None:
        return

    wizard = next((character_class for character_class in member_sheet_classes(member) if character_class.name == ClassType.WIZARD), None)
    if wizard is None or wizard.level < 1:
        return

    pruned_spellbook = pruned_wizard_spellbook(wizard.level, member.sheet.spellbook or [])
    member.sheet.spellbook = pruned_spellbook or None
    spellbook_ids = {spell.id for spell in pruned_spellbook}
    if member.sheet.spells:
        wizard_spells = [
            spell
            for spell in member.sheet.spells
            if spell.source == SpellSource.WIZARD and (spell.level == 0 or not spellbook_ids or spell.id in spellbook_ids)
        ]
        other_spells = [spell for spell in member.sheet.spells if spell.source != SpellSource.WIZARD]
        member.sheet.spells = [*other_spells, *pruned_wizard_spells(wizard.level, wizard_spells)] or None


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
