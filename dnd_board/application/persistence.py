from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from dnd_board.application.room_state import (
    ActiveConcentration,
    ActiveConditionSource,
    ActiveMaxHitPointIncrease,
    ActiveMaxHitPointReduction,
    FogState,
    Room,
    Token,
)
from dnd_board.character_sheet import (
    ConditionType,
    RestType,
    RollSource,
    SpellId,
    enum_key,
    enum_label,
    enum_value,
    sanitize_identifier,
    typed_json_from_value,
    typed_json_to_value,
)
from dnd_board.rules.shared.effects import ActiveOngoingEffect, ActiveScheduledEffect


@dataclass(frozen=True)
class LoadedRoomSave:
    board_id: str
    tokens: tuple[dict[str, Any], ...]
    fog: dict[str, Any]
    resource_uses: dict[str, dict[str, int]]
    max_hit_point_increases: dict[str, list[ActiveMaxHitPointIncrease]]
    max_hit_point_reductions: dict[str, list[ActiveMaxHitPointReduction]]
    exhaustion_levels: dict[str, int]
    suppressed_conditions: dict[str, list[ConditionType]]
    active_concentrations: dict[str, ActiveConcentration]
    ongoing_effects: dict[str, list[ActiveOngoingEffect]]
    scheduled_effects: dict[str, list[ActiveScheduledEffect]]


def load_room(path: Path) -> LoadedRoomSave | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict) or not isinstance(data.get("tokens"), list):
        return None

    tokens = tuple(token for token in data["tokens"] if isinstance(token, dict))
    fog = data.get("fog") if isinstance(data.get("fog"), dict) else {}
    return LoadedRoomSave(
        board_id=str(data.get("boardId", "")),
        tokens=tokens,
        fog=fog,
        resource_uses=_resource_uses(data.get("resources")),
        max_hit_point_increases=_max_hit_point_increases(data.get("maxHitPointIncreases")),
        max_hit_point_reductions=_max_hit_point_reductions(data.get("maxHitPointReductions")),
        exhaustion_levels=_exhaustion_levels(data.get("exhaustionLevels")),
        suppressed_conditions=_suppressed_conditions(data.get("suppressedConditions")),
        active_concentrations=_active_concentrations(data.get("activeConcentrations")),
        ongoing_effects=_active_effects(data.get("ongoingEffects"), ActiveOngoingEffect),
        scheduled_effects=_active_effects(data.get("scheduledEffects"), ActiveScheduledEffect),
    )


def _resource_uses(raw: Any) -> dict[str, dict[str, int]]:
    if not isinstance(raw, dict):
        return {}
    resources: dict[str, dict[str, int]] = {}
    for raw_sheet_id, raw_resources in raw.items():
        if not isinstance(raw_resources, dict):
            continue
        sheet_id = sanitize_identifier(str(raw_sheet_id))
        entries: dict[str, int] = {}
        for raw_resource_id, raw_current in raw_resources.items():
            try:
                entries[sanitize_identifier(str(raw_resource_id))] = max(0, int(raw_current))
            except (TypeError, ValueError):
                continue
        if sheet_id and entries:
            resources[sheet_id] = entries
    return resources


def _exhaustion_levels(raw: Any) -> dict[str, int]:
    if not isinstance(raw, dict):
        return {}
    levels: dict[str, int] = {}
    for raw_sheet_id, raw_level in raw.items():
        try:
            level = max(0, min(6, int(raw_level)))
        except (TypeError, ValueError):
            continue
        sheet_id = sanitize_identifier(str(raw_sheet_id))
        if sheet_id and level:
            levels[sheet_id] = level
    return levels


def _suppressed_conditions(raw: Any) -> dict[str, list[ConditionType]]:
    if not isinstance(raw, dict):
        return {}
    loaded: dict[str, list[ConditionType]] = {}
    for raw_sheet_id, raw_conditions in raw.items():
        if not isinstance(raw_conditions, list):
            continue
        sheet_id = sanitize_identifier(str(raw_sheet_id))
        conditions = [
            condition
            for value in raw_conditions
            if (condition := enum_value(ConditionType, value)) is not None
        ]
        if sheet_id and conditions:
            loaded[sheet_id] = list(dict.fromkeys(conditions))
    return loaded


def _max_hit_point_increases(raw: Any) -> dict[str, list[ActiveMaxHitPointIncrease]]:
    if not isinstance(raw, dict):
        return {}
    loaded: dict[str, list[ActiveMaxHitPointIncrease]] = {}
    for raw_sheet_id, raw_increases in raw.items():
        sheet_id = sanitize_identifier(str(raw_sheet_id))
        increases: list[ActiveMaxHitPointIncrease] = []
        for value in raw_increases if isinstance(raw_increases, list) else []:
            if not isinstance(value, dict):
                continue
            source = typed_json_to_value(value.get("source"), RollSource)
            try:
                amount = max(0, int(value.get("amount")))
            except (TypeError, ValueError):
                continue
            if source is not None and amount:
                increases.append(ActiveMaxHitPointIncrease(amount, source, str(value.get("sourceName") or source.sourceId)))
        if sheet_id and increases:
            loaded[sheet_id] = increases
    return loaded


def _max_hit_point_reductions(raw: Any) -> dict[str, list[ActiveMaxHitPointReduction]]:
    if not isinstance(raw, dict):
        return {}
    loaded: dict[str, list[ActiveMaxHitPointReduction]] = {}
    for raw_sheet_id, raw_reductions in raw.items():
        sheet_id = sanitize_identifier(str(raw_sheet_id))
        reductions: list[ActiveMaxHitPointReduction] = []
        for value in raw_reductions if isinstance(raw_reductions, list) else []:
            if not isinstance(value, dict):
                continue
            source = typed_json_to_value(value.get("source"), RollSource)
            reset = enum_value(RestType, value.get("reset"))
            try:
                amount = max(0, int(value.get("amount")))
            except (TypeError, ValueError):
                continue
            if source is not None and reset is not None and amount:
                reductions.append(ActiveMaxHitPointReduction(amount, source, str(value.get("sourceName") or source.sourceId), reset))
        if sheet_id and reductions:
            loaded[sheet_id] = reductions
    return loaded


def _active_concentrations(raw: Any) -> dict[str, ActiveConcentration]:
    if not isinstance(raw, dict):
        return {}
    loaded: dict[str, ActiveConcentration] = {}
    for raw_sheet_id, value in raw.items():
        if not isinstance(value, dict):
            continue
        sheet_id = sanitize_identifier(str(raw_sheet_id))
        spell_id = enum_value(SpellId, value.get("spellId"))
        if not sheet_id or spell_id is None:
            continue
        caster_id = sanitize_identifier(str(value.get("casterSheetId", sheet_id)))
        sources: list[ActiveConditionSource] = []
        for raw_source in value.get("conditionSources", []):
            if not isinstance(raw_source, dict):
                continue
            condition = enum_value(ConditionType, raw_source.get("condition"))
            source_spell = enum_value(SpellId, raw_source.get("spellId"))
            target_id = sanitize_identifier(str(raw_source.get("targetSheetId", "")))
            source_caster = sanitize_identifier(str(raw_source.get("casterSheetId", caster_id)))
            if condition is not None and source_spell is not None and target_id and source_caster:
                sources.append(ActiveConditionSource(target_id, condition, source_spell, source_caster, bool(raw_source.get("wasAlreadyActive", False))))
        loaded[sheet_id] = ActiveConcentration(caster_id, spell_id, str(value.get("spellName") or enum_label(spell_id)), sources)
    return loaded


def _active_effects(raw: Any, effect_type: type[Any]) -> dict[str, list[Any]]:
    if not isinstance(raw, dict):
        return {}
    loaded: dict[str, list[Any]] = {}
    for raw_sheet_id, raw_effects in raw.items():
        if not isinstance(raw_effects, list):
            continue
        sheet_id = sanitize_identifier(str(raw_sheet_id))
        effects = [
            effect
            for value in raw_effects
            if isinstance((effect := typed_json_to_value(value, effect_type)), effect_type)
            and effect.targetSheetId == sheet_id
        ]
        if sheet_id and effects:
            loaded[sheet_id] = effects
    return loaded


def save_room(room: Room, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(room_save_data(room), indent=2, sort_keys=True), encoding="utf-8")


def room_save_data(room: Room) -> dict[str, Any]:
    return {
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


def token_to_dict(token: Token) -> dict[str, Any]:
    data = asdict(token)
    data["kind"] = enum_key(token.kind)
    if data["lockedBy"] is None:
        data.pop("lockedBy")
    if data["avatarUrl"] is None:
        data.pop("avatarUrl")
    return data


def fog_to_dict(fog: FogState) -> dict[str, Any]:
    return {
        "hideMode": fog.hideMode,
        "brushSize": fog.brushSize,
        "revealedAreas": [asdict(area) for area in fog.revealedAreas],
    }


def max_hit_point_reductions_to_dict(
    reductions: dict[str, list[ActiveMaxHitPointReduction]],
) -> dict[str, Any]:
    return {
        sheet_id: [
            {
                "amount": reduction.amount,
                "source": typed_json_from_value(reduction.source),
                "sourceName": reduction.sourceName,
                "reset": enum_key(reduction.reset),
            }
            for reduction in sheet_reductions
        ]
        for sheet_id, sheet_reductions in reductions.items()
        if sheet_reductions
    }


def max_hit_point_increases_to_dict(
    increases: dict[str, list[ActiveMaxHitPointIncrease]],
) -> dict[str, Any]:
    return {
        sheet_id: [
            {
                "amount": increase.amount,
                "source": typed_json_from_value(increase.source),
                "sourceName": increase.sourceName,
            }
            for increase in sheet_increases
        ]
        for sheet_id, sheet_increases in increases.items()
        if sheet_increases
    }


def active_concentrations_to_dict(
    active_concentrations: dict[str, ActiveConcentration],
) -> dict[str, Any]:
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
