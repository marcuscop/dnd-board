from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace

from dnd_board.application.action_service import (
    resolve_damage_save_for_roll,
    resolve_damage_save_prompt_against_target,
    response_ability_roll,
    roll_advantage_log_label,
    save_modifier,
)
from dnd_board.application.resource_service import reset_sheet_resources
from dnd_board.application.room_state import (
    ActiveConcentration,
    ActiveConditionSource,
    ActiveMaxHitPointIncrease,
    ActiveMaxHitPointReduction,
    ConditionRemovalSave,
    Room,
)
from dnd_board.character_sheet import (
    ActiveConcentrationStatus,
    ActiveConcentrationUpdate,
    AbilityType,
    CharacterSheet,
    ConditionDuration,
    ConditionType,
    EquipmentItem,
    EquipmentSlot,
    EquipmentType,
    HitPoints,
    RollModifierEffectTarget,
    RollModifierBreakdown,
    RollPayload,
    RollResolution,
    RollResolutionMode,
    RestType,
    SheetSectionType,
    SpellEntry,
    SpellId,
    condition_saving_throw_forced_failure_conditions,
    enum_key,
    enum_label,
    enum_value,
    resolve_roll_against_target as resolve_dnd_roll_against_target,
)
from dnd_board.rules.shared.character_effects import (
    ResolvedCharacterEffect,
    applicable_character_modifiers,
    added_condition_types,
    condition_change_effects,
    first_damage_effect,
    ongoing_effects_after_ending,
)
from dnd_board.rules.shared.effects import (
    ActionAllowanceEffect,
    ConditionOperation,
    EffectDurationType,
    EndingConditionType,
    MaximumHitPointsEffect,
    MaximumHitPointsOperation,
    OngoingEffectId,
    RestEffect,
    CalculationType,
    ModifierOperation,
    ModifierScope,
)
from dnd_board.rules.encounter import ActionAllowance, AllowanceSource, grant_action_allowance
from dnd_board.rules.shared.resources import ResourceUpdate
from dnd_board.rules.shared.condition_effects import normalize_conditions
from dnd_board.rules.equipment import valid_equipment_slots


@dataclass(frozen=True)
class CharacterStatePersistence:
    save_room: Callable[[Room], None]
    load_conditions: Callable[[str, str], list[ConditionType]]
    persist_conditions: Callable[[str, str, list[ConditionType]], None]
    rebuild_sheet: Callable[[Room, str], CharacterSheet | None]


def apply_roll_result(
    room: Room,
    roll: RollPayload,
    target: CharacterSheet,
    source: CharacterSheet | None,
    effect_resolution: ResolvedCharacterEffect | None,
    sheets: list[CharacterSheet],
    persistence: CharacterStatePersistence,
) -> RollResolution:
    if (
        roll.resolution == RollResolutionMode.NONE
        and roll.pendingEffect is None
        and roll.damageSavingThrow is not None
        and roll.damageSaveDc is not None
    ):
        return resolve_damage_save_prompt_against_target(roll, target)

    damage_save_outcome, damage_save_roll, resolved_roll = resolve_damage_save_for_roll(roll, target)
    resolution = resolve_dnd_roll_against_target(resolved_roll, target, source, effect_resolution)
    _apply_effect_sheet_updates(room, resolution, sheets, persistence)
    concentration_update_sheet_ids: set[str] = set()
    damage_triggered_condition_outcomes = _resolve_damage_triggered_condition_saves(
        room,
        roll,
        target,
        resolution,
    )
    response_rolls = _dedupe_response_rolls(
        [
            *([damage_save_roll] if damage_save_roll is not None else []),
            *(
                response_roll
                for _outcome, _conditions, response_roll in damage_triggered_condition_outcomes
            ),
        ]
    )
    if damage_save_outcome:
        resolution.outcome = f"{resolution.outcome}; {damage_save_outcome}"
    if damage_triggered_condition_outcomes:
        for _outcome, cleared_conditions, _response_roll in damage_triggered_condition_outcomes:
            resolution.targetConditions = [
                condition
                for condition in resolution.targetConditions
                if condition not in cleared_conditions
            ]
        outcomes = "; ".join(
            outcome for outcome, _conditions, _response_roll in damage_triggered_condition_outcomes
        )
        resolution.outcome = f"{resolution.outcome}; {outcomes}"
    if response_rolls:
        for response_roll in response_rolls:
            room.pending_rolls[_roll_queue_key(response_roll)] = response_roll
        resolution.responseRolls = response_rolls
    if roll.resolution in {
        RollResolutionMode.APPLY_DAMAGE,
        RollResolutionMode.HEAL_SELF,
        RollResolutionMode.APPLY_TEMPORARY_HIT_POINTS,
    }:
        room.hit_points[target.tokenId] = resolution.targetHp.current
        room.temporary_hit_points[target.tokenId] = resolution.targetHp.temporary
    death_outcome = _apply_dead_condition_after_damage(resolution)
    if death_outcome:
        resolution.outcome = f"{resolution.outcome}; {death_outcome}"
    concentration_outcome, concentration_roll = _resolve_concentration_save_after_damage(
        room,
        target,
        source,
        roll,
        resolution,
        persistence,
    )
    if concentration_outcome:
        resolution.outcome = f"{resolution.outcome}; {concentration_outcome}"
        concentration_update_sheet_ids.add(target.id)
    if concentration_roll is not None:
        response_rolls = _dedupe_response_rolls([*response_rolls, concentration_roll])
        room.pending_rolls[_roll_queue_key(concentration_roll)] = concentration_roll
        resolution.responseRolls = response_rolls
    _apply_resolved_conditions(
        room,
        target.id,
        target.conditions,
        resolution.targetConditions,
        roll,
        source,
        persistence,
    )
    if concentration_spell_for_roll(source, roll) is not None and source is not None:
        concentration_update_sheet_ids.add(source.id)
    if concentration_update_sheet_ids:
        resolution.concentrationUpdates = [
            ActiveConcentrationUpdate(
                sheetId=sheet_id,
                activeConcentration=active_concentration_status(
                    room.active_concentrations.get(sheet_id)
                ),
            )
            for sheet_id in sorted(concentration_update_sheet_ids)
        ]
    return resolution


def active_concentration_status(
    active: ActiveConcentration | None,
) -> ActiveConcentrationStatus | None:
    if active is None:
        return None
    return ActiveConcentrationStatus(spellId=active.spellId, spellName=active.spellName)


def clear_active_concentration(
    room: Room,
    caster_sheet_id: str,
    persistence: CharacterStatePersistence,
) -> list[str]:
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
            persistence.save_room(room)
        return []

    removed: list[str] = []
    for condition_source in active.conditionSources:
        remaining_sources = [
            other_source
            for concentration in room.active_concentrations.values()
            for other_source in concentration.conditionSources
            if other_source.targetSheetId == condition_source.targetSheetId
            and other_source.condition == condition_source.condition
        ]
        if condition_source.wasAlreadyActive or remaining_sources:
            continue
        current_conditions = room.condition_overrides.get(
            condition_source.targetSheetId
        ) or persistence.load_conditions(condition_source.targetSheetId, room.id)
        next_conditions = [
            condition
            for condition in current_conditions
            if condition != condition_source.condition
        ]
        if next_conditions != current_conditions:
            room.condition_overrides[condition_source.targetSheetId] = next_conditions
            room.condition_durations.setdefault(condition_source.targetSheetId, {}).pop(
                condition_source.condition,
                None,
            )
            room.condition_removals.setdefault(condition_source.targetSheetId, {}).pop(
                condition_source.condition,
                None,
            )
            persistence.persist_conditions(room.id, condition_source.targetSheetId, next_conditions)
            removed.append(enum_label(condition_source.condition))
    if ongoing_changed:
        persistence.save_room(room)
    return removed


def remove_active_condition_sources(
    room: Room,
    target_sheet_id: str,
    condition: ConditionType,
) -> None:
    for caster_sheet_id, concentration in list(room.active_concentrations.items()):
        concentration.conditionSources = [
            source
            for source in concentration.conditionSources
            if source.targetSheetId != target_sheet_id or source.condition != condition
        ]
        if not concentration.conditionSources:
            room.active_concentrations.pop(caster_sheet_id, None)


def _apply_effect_sheet_updates(
    room: Room,
    resolution: RollResolution,
    sheets: list[CharacterSheet],
    persistence: CharacterStatePersistence,
) -> None:
    persistent_effect_changed = False
    sheets_by_id = {sheet.id: sheet for sheet in sheets}
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
            existing_ids = {
                active.id for active in room.ongoing_effects.get(update.tokenId, [])
            }
            room.ongoing_effects[update.tokenId] = [
                replace(
                    active,
                    installedTurnId=room.encounter.turnId,
                )
                if (
                    active.id not in existing_ids
                    and active.installedTurnId is None
                    and room.encounter is not None
                )
                else active
                for active in update.ongoingEffects
            ]
            persistent_effect_changed = True
        if update.scheduledEffects:
            scheduled = room.scheduled_effects.setdefault(update.tokenId, [])
            existing_ids = {active.id for active in scheduled}
            scheduled.extend(
                active for active in update.scheduledEffects if active.id not in existing_ids
            )
            persistent_effect_changed = True
        for applied in update.appliedEffects or []:
            effect = applied.effect
            if isinstance(effect, ActionAllowanceEffect):
                if room.encounter is not None:
                    room.encounter = grant_action_allowance(
                        room.encounter,
                        update.sheetId,
                        ActionAllowance(
                            resource=effect.resource,
                            amount=effect.amount,
                            source=AllowanceSource(effect.sourceResource),
                            allowedCategories=effect.allowedCategories,
                            expires=effect.expires,
                        ),
                    )
                    persistent_effect_changed = True
                continue
            if isinstance(effect, RestEffect):
                effect_sheet = sheets_by_id.get(update.sheetId)
                if effect_sheet is None:
                    continue
                reset_character_for_rest(room, effect_sheet, effect.rest, persistence)
                rested_conditions = list(
                    room.condition_overrides.get(update.tokenId, effect_sheet.conditions)
                )
                update.conditions = rested_conditions
                if resolution.targetSheetId == update.sheetId:
                    resolution.targetConditions = rested_conditions
                if effect.rest == RestType.LONG_REST:
                    rested_sheet = persistence.rebuild_sheet(room, effect_sheet.tokenId)
                    if rested_sheet is not None:
                        update.hp = rested_sheet.hp
                        if resolution.targetSheetId == update.sheetId:
                            resolution.targetHp = rested_sheet.hp
                persistent_effect_changed = True
                continue
            if not isinstance(effect, MaximumHitPointsEffect):
                continue
            amount = max(0, applied.amount or 0)
            if amount <= 0:
                continue
            if effect.operation == MaximumHitPointsOperation.REDUCE:
                room.max_hit_point_reductions.setdefault(update.tokenId, []).append(
                    ActiveMaxHitPointReduction(
                        amount=amount,
                        reset=effect.reset,
                        source=resolution.roll.source,
                        sourceName=resolution.roll.sourceLabel,
                    )
                )
                persistent_effect_changed = True
                continue
            existing = room.max_hit_point_increases.setdefault(update.tokenId, [])
            existing[:] = [
                active for active in existing if active.source != resolution.roll.source
            ]
            existing.append(
                ActiveMaxHitPointIncrease(
                    amount=amount,
                    source=resolution.roll.source,
                    sourceName=resolution.roll.sourceLabel,
                )
            )
            persistent_effect_changed = True
    if persistent_effect_changed:
        persistence.save_room(room)


def reset_sheet_conditions(
    room: Room,
    sheet: CharacterSheet,
    rest_type: RestType,
    persistence: CharacterStatePersistence,
) -> None:
    durations = room.condition_durations.get(sheet.tokenId, {})
    expired = {
        condition
        for condition, duration in durations.items()
        if condition_clears_on_rest(duration, rest_type)
    }
    if expired:
        current_conditions = room.condition_overrides.get(sheet.tokenId, sheet.conditions)
        next_conditions = [condition for condition in current_conditions if condition not in expired]
        room.condition_overrides[sheet.tokenId] = next_conditions
        for condition in expired:
            durations.pop(condition, None)
            room.condition_removals.setdefault(sheet.tokenId, {}).pop(condition, None)
        room.suppressed_conditions[sheet.tokenId] = [
            condition
            for condition in room.suppressed_conditions.get(sheet.tokenId, [])
            if condition not in expired
        ]
        persistence.persist_conditions(room.id, sheet.id, next_conditions)

    active_effects = room.ongoing_effects.get(sheet.tokenId, [])
    expiring_duration_types = {
        EffectDurationType.UNTIL_SHORT_REST,
        EffectDurationType.UNTIL_LONG_REST,
    }
    if rest_type == RestType.SHORT_REST:
        expiring_duration_types.remove(EffectDurationType.UNTIL_LONG_REST)
    remaining_effects = [
        active
        for active in active_effects
        if active.effect.duration.durationType not in expiring_duration_types
    ]
    if remaining_effects != active_effects:
        room.ongoing_effects[sheet.tokenId] = remaining_effects


def condition_clears_on_rest(
    condition_duration: ConditionDuration,
    rest_type: RestType,
) -> bool:
    if condition_duration == ConditionDuration.UNTIL_SHORT_REST:
        return rest_type in {RestType.SHORT_REST, RestType.LONG_REST}
    if condition_duration == ConditionDuration.UNTIL_LONG_REST:
        return rest_type == RestType.LONG_REST
    return False


def reset_character_for_rest(
    room: Room,
    sheet: CharacterSheet,
    rest_type: RestType,
    persistence: CharacterStatePersistence,
) -> list[ResourceUpdate]:
    recovered = reset_sheet_resources(room, sheet, rest_type)
    if rest_type == RestType.LONG_REST:
        clear_active_concentration(room, sheet.id, persistence)
    remaining_ongoing = ongoing_effects_after_ending(
        room.ongoing_effects.get(sheet.tokenId, []),
        EndingConditionType.REST_COMPLETED,
    )
    if remaining_ongoing:
        room.ongoing_effects[sheet.tokenId] = remaining_ongoing
    else:
        room.ongoing_effects.pop(sheet.tokenId, None)
    reset_sheet_conditions(room, sheet, rest_type, persistence)
    if rest_type == RestType.LONG_REST:
        room.temporary_hit_points.pop(sheet.tokenId, None)
        room.max_hit_point_increases.pop(sheet.tokenId, None)
        _reset_exhaustion(room, sheet, persistence)
    reductions = room.max_hit_point_reductions.get(sheet.tokenId, [])
    remaining = [entry for entry in reductions if not reset_applies_to_rest(entry.reset, rest_type)]
    if remaining:
        room.max_hit_point_reductions[sheet.tokenId] = remaining
    else:
        room.max_hit_point_reductions.pop(sheet.tokenId, None)
    if rest_type == RestType.LONG_REST:
        refreshed = persistence.rebuild_sheet(room, sheet.tokenId)
        if refreshed is not None:
            room.hit_points[sheet.tokenId] = refreshed.hp.max
    return recovered


def reset_applies_to_rest(reset: RestType, rest_type: RestType) -> bool:
    if reset == RestType.NONE:
        return False
    if rest_type == RestType.LONG_REST:
        return reset in {RestType.SHORT_REST, RestType.LONG_REST}
    return reset == RestType.SHORT_REST


def set_equipment_slot(
    room: Room,
    sheet: CharacterSheet,
    item_id: str,
    slot: EquipmentSlot,
) -> None:
    token_slots = room.equipment_slots.setdefault(sheet.tokenId, {})
    if slot == EquipmentSlot.ARMOR:
        conflicting = {EquipmentSlot.ARMOR}
    elif slot == EquipmentSlot.TWO_HANDS:
        conflicting = {EquipmentSlot.MAIN_HAND, EquipmentSlot.OFF_HAND, EquipmentSlot.TWO_HANDS}
    elif slot in {EquipmentSlot.MAIN_HAND, EquipmentSlot.OFF_HAND}:
        conflicting = {slot, EquipmentSlot.TWO_HANDS}
    else:
        conflicting = set()
    for item in sheet.equipment:
        if item.slot in conflicting:
            token_slots[item.id] = EquipmentSlot.CARRIED
    token_slots[item_id] = slot
    wielded_slots = {
        EquipmentSlot.MAIN_HAND,
        EquipmentSlot.OFF_HAND,
        EquipmentSlot.TWO_HANDS,
    }
    for item in sheet.equipment:
        effective_slot = token_slots.get(item.id, item.slot)
        if effective_slot in wielded_slots:
            continue
        for target_sheet_id, active in list(room.ongoing_effects.items()):
            remaining = ongoing_effects_after_ending(
                active,
                EndingConditionType.SOURCE_UNEQUIPPED,
                source_sheet_id=sheet.tokenId,
                equipment_instance_id=item.id,
            )
            if remaining:
                room.ongoing_effects[target_sheet_id] = remaining
            else:
                room.ongoing_effects.pop(target_sheet_id, None)


def remove_active_ongoing_effect(
    room: Room,
    sheet: CharacterSheet,
    effect_id: OngoingEffectId,
) -> bool:
    active = room.ongoing_effects.get(sheet.tokenId, [])
    removable = next(
        (
            effect
            for effect in active
            if effect.id == effect_id
            and any(
                ending.endingCondition == EndingConditionType.MANUAL
                for ending in effect.effect.endingConditions
            )
        ),
        None,
    )
    if removable is None:
        return False
    remaining = [effect for effect in active if effect.id != effect_id]
    if remaining:
        room.ongoing_effects[sheet.tokenId] = remaining
    else:
        room.ongoing_effects.pop(sheet.tokenId, None)
    return True


def updated_conditions(
    conditions: list[ConditionType],
    condition: ConditionType,
    active: bool,
) -> list[ConditionType]:
    if active and condition not in conditions:
        return normalize_conditions([*conditions, condition])
    if not active:
        return [candidate for candidate in conditions if candidate != condition]
    return normalize_conditions(list(conditions))


def update_condition_state(
    room: Room,
    sheet: CharacterSheet,
    condition: ConditionType,
    active: bool,
    persistence: CharacterStatePersistence,
) -> str:
    next_conditions = updated_conditions(sheet.conditions, condition, active)
    sheet_id = sheet.tokenId
    room.condition_overrides[sheet_id] = next_conditions
    if active:
        from dnd_board.rules.shared.condition_effects import condition_blocks_all_actions

        room.condition_durations.setdefault(sheet_id, {})[condition] = ConditionDuration.MANUAL
        if condition_blocks_all_actions(condition):
            clear_active_concentration(room, sheet_id, persistence)
    else:
        room.condition_durations.setdefault(sheet_id, {}).pop(condition, None)
        room.condition_removals.setdefault(sheet_id, {}).pop(condition, None)
        room.suppressed_conditions[sheet_id] = [
            current for current in room.suppressed_conditions.get(sheet_id, [])
            if current != condition
        ]
        remove_active_condition_sources(room, sheet_id, condition)
    persistence.persist_conditions(room.id, sheet.id, next_conditions)
    persistence.save_room(room)
    return sheet_id


def update_exhaustion_state(
    room: Room,
    sheet: CharacterSheet,
    level: int,
    persistence: CharacterStatePersistence,
) -> str:
    next_level = min(6, max(0, level))
    sheet_id = sheet.tokenId
    if next_level:
        room.exhaustion_levels[sheet_id] = next_level
    else:
        room.exhaustion_levels.pop(sheet_id, None)
    next_conditions = conditions_for_exhaustion_level(
        room.condition_overrides.get(sheet_id, sheet.conditions),
        next_level,
    )
    if next_level >= 6 and ConditionType.DEAD not in next_conditions:
        next_conditions = normalize_conditions([*next_conditions, ConditionType.DEAD])
    room.condition_overrides[sheet_id] = next_conditions
    if next_level:
        room.condition_durations.setdefault(sheet_id, {})[ConditionType.EXHAUSTION] = ConditionDuration.MANUAL
    else:
        room.condition_durations.setdefault(sheet_id, {}).pop(ConditionType.EXHAUSTION, None)
    persistence.persist_conditions(room.id, sheet.id, next_conditions)
    persistence.save_room(room)
    return sheet_id


def conditions_for_exhaustion_level(
    conditions: list[ConditionType],
    exhaustion_level: int,
) -> list[ConditionType]:
    next_conditions = [condition for condition in conditions if condition != ConditionType.EXHAUSTION]
    if exhaustion_level > 0:
        next_conditions.append(ConditionType.EXHAUSTION)
    return normalize_conditions(next_conditions)


def _reset_exhaustion(
    room: Room,
    sheet: CharacterSheet,
    persistence: CharacterStatePersistence,
) -> None:
    current_level = room.exhaustion_levels.get(sheet.tokenId, sheet.exhaustionLevel)
    next_level = max(0, current_level - 1)
    if next_level > 0:
        room.exhaustion_levels[sheet.tokenId] = next_level
    else:
        room.exhaustion_levels.pop(sheet.tokenId, None)
    next_conditions = conditions_for_exhaustion_level(
        room.condition_overrides.get(sheet.tokenId, sheet.conditions),
        next_level,
    )
    room.condition_overrides[sheet.tokenId] = next_conditions
    room.hit_points[sheet.tokenId] = sheet.hp.current
    persistence.persist_conditions(room.id, sheet.id, next_conditions)


def _apply_dead_condition_after_damage(resolution: RollResolution) -> str | None:
    if not _roll_can_apply_damage(resolution.roll):
        return None
    if resolution.targetHp.current > 0 or ConditionType.DEAD in resolution.targetConditions:
        return None
    resolution.targetConditions = normalize_conditions(
        [*resolution.targetConditions, ConditionType.DEAD]
    )
    return f"{resolution.targetName} gains {enum_label(ConditionType.DEAD)}"


def _resolve_damage_triggered_condition_saves(
    room: Room,
    roll: RollPayload,
    target: CharacterSheet,
    resolution: RollResolution,
) -> list[tuple[str, list[ConditionType], RollPayload]]:
    if not _roll_can_apply_damage(roll) or not _damage_was_taken(target.hp, resolution.targetHp):
        return []
    removals = room.condition_removals.get(target.id, {})
    active_conditions = set(target.conditions)
    grouped_removals: dict[tuple[AbilityType, int, bool], list[ConditionType]] = {}
    for condition, removal in removals.items():
        if condition in active_conditions:
            grouped_removals.setdefault(
                (removal.savingThrow, removal.saveDc, removal.advantage),
                [],
            ).append(condition)

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
        )
        condition_label = _text_list_label([enum_label(condition) for condition in conditions])
        advantage_label = roll_advantage_log_label(response_roll)
        forced_failure_conditions = condition_saving_throw_forced_failure_conditions(
            target,
            saving_throw,
        )
        forced_failure_label = (
            f" due to {_text_list_label([enum_label(condition) for condition in forced_failure_conditions])}"
            if forced_failure_conditions
            else ""
        )
        if not forced_failure_conditions and response_roll.total >= save_dc:
            outcomes.append(
                (
                    f"{target.name} passes DC {save_dc} {enum_label(saving_throw)} "
                    f"save{advantage_label} after taking damage and ends {condition_label}",
                    conditions,
                    response_roll,
                )
            )
        else:
            outcomes.append(
                (
                    f"{target.name} fails DC {save_dc} {enum_label(saving_throw)} "
                    f"save{advantage_label}{forced_failure_label} after taking damage; "
                    f"{condition_label} remains",
                    [],
                    response_roll,
                )
            )
    return outcomes


def _resolve_concentration_save_after_damage(
    room: Room,
    target: CharacterSheet,
    source: CharacterSheet | None,
    triggering_roll: RollPayload,
    resolution: RollResolution,
    persistence: CharacterStatePersistence,
) -> tuple[str | None, RollPayload | None]:
    active = room.active_concentrations.get(target.id)
    damage_taken = _hit_point_damage_taken(target.hp, resolution.targetHp)
    if active is None or damage_taken <= 0:
        return None, None
    if ConditionType.DEAD in resolution.targetConditions:
        removed_conditions = clear_active_concentration(room, target.id, persistence)
        removed_label = (
            f" and removes {_text_list_label(removed_conditions)}" if removed_conditions else ""
        )
        return (
            f"{target.name} is {enum_label(ConditionType.DEAD)}; "
            f"{active.spellName} ends{removed_label}",
            None,
        )
    save_dc = max(10, damage_taken // 2)
    source_modifiers = (
        applicable_character_modifiers(
            source,
            CalculationType.CONCENTRATION_SAVE,
            ModifierScope.CAUSED_BY_OWNER,
            triggering_roll,
            target,
            source,
        )
        if source is not None
        else []
    )
    source_disadvantage = any(
        modifier.operation == ModifierOperation.DISADVANTAGE
        for _label, modifier in source_modifiers
    )
    owner_modifiers = applicable_character_modifiers(
        target,
        CalculationType.CONCENTRATION_SAVE,
        ModifierScope.OWNER,
        triggering_roll,
        target,
        source,
    )
    owner_advantage = any(
        modifier.operation == ModifierOperation.ADVANTAGE
        for _label, modifier in owner_modifiers
    )
    response_roll = response_ability_roll(
        sheet=target,
        ability=AbilityType.CONSTITUTION,
        action_id="concentration-save",
        label="Concentration Save",
        source_label=active.spellName,
        modifier=save_modifier(target, AbilityType.CONSTITUTION),
        modifier_target=RollModifierEffectTarget.CONCENTRATION_SAVE,
        advantage=owner_advantage,
        disadvantage=source_disadvantage,
    )
    if source_disadvantage or owner_advantage:
        response_roll = replace(
            response_roll,
            modifierBreakdown=[
                *response_roll.modifierBreakdown,
                *(
                    RollModifierBreakdown(label, 0, modifier.description)
                    for label, modifier in source_modifiers
                    if modifier.operation == ModifierOperation.DISADVANTAGE
                ),
                *(
                    RollModifierBreakdown(label, 0, modifier.description)
                    for label, modifier in owner_modifiers
                    if modifier.operation == ModifierOperation.ADVANTAGE
                ),
            ],
        )
    advantage_label = roll_advantage_log_label(response_roll)
    if response_roll.total >= save_dc:
        return (
            f"{target.name} passes DC {save_dc} Concentration save{advantage_label} "
            f"for {active.spellName}",
            response_roll,
        )
    removed_conditions = clear_active_concentration(room, target.id, persistence)
    removed_label = (
        f" and removes {_text_list_label(removed_conditions)}" if removed_conditions else ""
    )
    return (
        f"{target.name} fails DC {save_dc} Concentration save{advantage_label}; "
        f"{active.spellName} ends{removed_label}",
        response_roll,
    )


def concentration_spell_for_roll(
    source: CharacterSheet | None,
    roll: RollPayload,
) -> SpellEntry | None:
    if source is None or roll.source.section != SheetSectionType.SPELLS:
        return None
    spell_id = enum_value(SpellId, roll.source.sourceId)
    if spell_id is None:
        return None
    spell = next((candidate for candidate in source.spells if candidate.id == spell_id), None)
    return spell if spell is not None and spell.concentration else None


def _apply_resolved_conditions(
    room: Room,
    sheet_id: str,
    previous_conditions: list[ConditionType],
    conditions: list[ConditionType],
    roll: RollPayload,
    source: CharacterSheet | None,
    persistence: CharacterStatePersistence,
) -> None:
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
    for effect in condition_change_effects(roll.pendingEffect):
        if effect.operation != ConditionOperation.ADD or effect.condition not in active_conditions:
            continue
        if effect.duration is not None:
            durations[effect.condition] = {
                EffectDurationType.UNTIL_SHORT_REST: ConditionDuration.UNTIL_SHORT_REST,
                EffectDurationType.UNTIL_LONG_REST: ConditionDuration.UNTIL_LONG_REST,
            }.get(effect.duration.durationType, ConditionDuration.MANUAL)
        ending = next(
            (
                ending
                for ending in effect.endingConditions
                if ending.endingCondition == EndingConditionType.TARGET_TAKES_DAMAGE
                and ending.savingThrow is not None
            ),
            None,
        )
        if ending is not None and roll.damageSaveDc is not None:
            removals[effect.condition] = ConditionRemovalSave(
                savingThrow=ending.savingThrow.ability,
                saveDc=roll.damageSaveDc,
                advantage=ending.advantage,
            )
    _record_active_concentration_conditions(
        room,
        source,
        sheet_id,
        previous_conditions,
        conditions,
        roll,
        persistence,
    )
    persistence.persist_conditions(room.id, sheet_id, conditions)


def _record_active_concentration_conditions(
    room: Room,
    source: CharacterSheet | None,
    target_sheet_id: str,
    previous_conditions: list[ConditionType],
    conditions: list[ConditionType],
    roll: RollPayload,
    persistence: CharacterStatePersistence,
) -> None:
    spell = concentration_spell_for_roll(source, roll)
    if spell is None or source is None:
        return
    caster_sheet_id = source.id
    active = room.active_concentrations.get(caster_sheet_id)
    if active is not None and active.spellId != spell.id:
        clear_active_concentration(room, caster_sheet_id, persistence)
        active = None
    if active is None:
        active = ActiveConcentration(
            casterSheetId=caster_sheet_id,
            spellId=spell.id,
            spellName=enum_label(spell.name),
            conditionSources=[],
        )
        room.active_concentrations[caster_sheet_id] = active
    active_conditions = set(conditions)
    previous_condition_set = set(previous_conditions)
    existing_source_keys = {
        (source_record.targetSheetId, source_record.condition)
        for source_record in active.conditionSources
    }
    for condition in dict.fromkeys(added_condition_types(roll.pendingEffect)):
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


def _roll_can_apply_damage(roll: RollPayload) -> bool:
    if roll.resolution == RollResolutionMode.APPLY_DAMAGE:
        return True
    return roll.pendingEffect is not None and first_damage_effect(roll.pendingEffect) is not None


def _hit_point_damage_taken(before: HitPoints, after: HitPoints) -> int:
    return max(0, before.current - after.current) + max(0, before.temporary - after.temporary)


def _damage_was_taken(before: HitPoints, after: HitPoints) -> bool:
    return after.current < before.current or after.temporary < before.temporary


def _dedupe_response_rolls(response_rolls: list[RollPayload]) -> list[RollPayload]:
    deduped: list[RollPayload] = []
    seen: set[str] = set()
    for response_roll in response_rolls:
        if response_roll.id in seen:
            continue
        seen.add(response_roll.id)
        deduped.append(response_roll)
    return deduped


def _text_list_label(values: list[str]) -> str:
    if len(values) <= 1:
        return values[0] if values else ""
    return f"{', '.join(values[:-1])}, and {values[-1]}"


def _roll_queue_key(roll: RollPayload) -> tuple[str, str, str, str]:
    return (
        roll.tokenId,
        enum_key(roll.source.section),
        roll.source.sourceId,
        roll.source.actionId,
    )
