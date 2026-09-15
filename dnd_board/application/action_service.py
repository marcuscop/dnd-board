from __future__ import annotations

import random
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, replace
from enum import StrEnum
from time import time_ns
from typing import Any, TYPE_CHECKING

from dnd_board.application.resource_service import payable_resource_costs, spend_sheet_resources
from dnd_board.application.resolution_interactions import resolution_prompt_for_d20_test
from dnd_board.application.encounter_service import authorize_action, commit_action_authorization
from dnd_board.application.room_state import Player, Room
from dnd_board.character_sheet import (
    ActivationTiming,
    AbilityType,
    CharacterSheet,
    ConditionType,
    DiceType,
    DamageType,
    RollModifierBreakdown,
    RollModifierEffectTarget,
    RollPayload,
    RollLogEntry,
    RollLogEntryType,
    RollResolution,
    RollResolutionMode,
    RollSource,
    SheetSectionType,
    SpellSaveOutcome,
    SpellEntry,
    TimeEconomy,
    active_roll_modifier_breakdown,
    ability_modifier,
    condition_saving_throw_advantage_conditions,
    condition_saving_throw_disadvantage_conditions,
    condition_saving_throw_forced_failure_conditions,
    creature_type_list_label,
    enum_key,
    enum_label,
    enum_value,
    build_ability_check_roll_payload,
    build_combined_attack_roll_payload,
    build_damage_roll_payload,
    build_roll_action_payload,
    build_saving_throw_roll_payload,
    build_spell_attack_roll_payload,
    build_spell_condition_roll_payload,
    build_spell_damage_roll_payload,
    build_spell_healing_roll_payload,
    build_spell_temporary_hit_points_roll_payload,
    roll_log_entry_to_dict,
    roll_payload_to_dict,
    roll_resolution_to_dict,
    resolution_interceptor_prompt_to_dict,
    sanitize_identifier,
)
from dnd_board.rules.shared.weapon_effects import (
    build_bound_weapon_spell_attack_payload,
    build_bound_weapon_spell_effect_payload,
)
from dnd_board.rules.shared.character_effects import (
    activated_effect_node,
    added_condition_types,
    character_allocation_value,
    direct_damage_action_at,
    first_attack_roll_effect,
    ongoing_effects_after_ending,
    scaled_instance_count,
)
from dnd_board.rules.shared.condition_effects import (
    action_failure_chance,
    activation_blocking_condition,
    conditions_ending_on_event,
)
from dnd_board.rules.shared.effects import CalculationType, ChoiceEffect, EndingConditionType, RepeatedEffect, ResolutionEventType
from dnd_board.rules.shared.resources import (
    InsufficientResourceError,
    ResourceCost,
    ResourceId,
    ResourceUpdate,
)
from dnd_board.rules.encounter import ActionCategory, ActivationKey, ActivationKind

if TYPE_CHECKING:
    from dnd_board.application.character_state_service import CharacterStatePersistence


@dataclass(frozen=True)
class ActionOperations:
    all_sheets: Callable[[Room], list[CharacterSheet]]
    state_persistence: CharacterStatePersistence
    save: Callable[[Room], None]
    broadcast: Callable[[Room, dict[str, Any]], Awaitable[None]]
    broadcast_room: Callable[[Room], Awaitable[None]]
    history_limit: int


class ActionServiceError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class SpellRollType(StrEnum):
    HEALING = "healing"
    TEMPORARY_HIT_POINTS = "temporaryHitPoints"
    EFFECT = "effect"


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
        advantage_conditions = (advantage_conditions or []) + condition_saving_throw_advantage_conditions(
            sheet,
            ability,
            pending_conditions,
        )
        disadvantage_conditions = (disadvantage_conditions or []) + condition_saving_throw_disadvantage_conditions(
            sheet,
            ability,
        )
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
        source=RollSource(
            section=SheetSectionType.ABILITY_SCORES,
            sourceId=enum_key(ability),
            actionId=action_id,
        ),
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


def ability_check_modifier(sheet: CharacterSheet, ability: AbilityType) -> int:
    return ability_modifier(getattr(sheet.abilityScores, enum_key(ability)))


def skill_modifier(sheet: CharacterSheet, skill_name: str, fallback_ability: AbilityType) -> int:
    skill = next((candidate for candidate in sheet.skills if candidate.name == skill_name), None)
    return skill.modifier if skill is not None else ability_check_modifier(sheet, fallback_ability)


def save_modifier(sheet: CharacterSheet, ability: AbilityType) -> int:
    saving_throw = next((save for save in sheet.savingThrows if save.ability == ability), None)
    modifier = ability_check_modifier(sheet, ability)
    if saving_throw is not None and saving_throw.proficient:
        modifier += sheet.proficiencyBonus
    return modifier


def resolve_damage_save_for_roll(
    roll: RollPayload,
    target: CharacterSheet,
) -> tuple[str | None, RollPayload | None, RollPayload]:
    if (
        (roll.resolution != RollResolutionMode.APPLY_DAMAGE and roll.pendingEffect is None)
        or roll.damageSavingThrow is None
        or roll.damageSaveDc is None
        or roll.damageSaveOutcome is None
        or roll.damageSaveOutcome == SpellSaveOutcome.NONE
    ):
        return None, None, roll
    if roll.damageSaveSucceeded is not None:
        return _previous_save_outcome(roll, target)

    disadvantage = _damage_save_disadvantage_applies(roll, target)
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
    forced_failure = _damage_save_forced_failure_applies(roll, target)
    forced_failure_conditions = condition_saving_throw_forced_failure_conditions(
        target,
        roll.damageSavingThrow,
    )
    forced_failure_label = _damage_save_forced_failure_label(
        target,
        forced_failure,
        forced_failure_conditions,
    )
    if forced_failure or forced_failure_conditions or response_roll.total < roll.damageSaveDc:
        return (
            f"{target.name} fails DC {roll.damageSaveDc} {enum_label(roll.damageSavingThrow)} "
            f"save{save_label}{forced_failure_label}",
            response_roll,
            replace(roll, damageSaveSucceeded=False),
        )
    if roll.damageSaveOutcome == SpellSaveOutcome.HALF_DAMAGE:
        return (
            f"{target.name} passes DC {roll.damageSaveDc} {enum_label(roll.damageSavingThrow)} "
            f"save{save_label} for half damage",
            response_roll,
            replace(roll, damageSaveSucceeded=True),
        )
    if roll.damageSaveOutcome == SpellSaveOutcome.NEGATES:
        return (
            f"{target.name} passes DC {roll.damageSaveDc} {enum_label(roll.damageSavingThrow)} "
            f"save{save_label} and takes no damage",
            response_roll,
            replace(roll, total=0, damageComponents=None, damageSaveSucceeded=True),
        )
    return (
        f"{target.name} passes DC {roll.damageSaveDc} {enum_label(roll.damageSavingThrow)} "
        f"save{save_label}",
        response_roll,
        replace(roll, damageSaveSucceeded=True),
    )


def resolve_damage_save_prompt_against_target(
    roll: RollPayload,
    target: CharacterSheet,
) -> RollResolution:
    assert roll.damageSavingThrow is not None
    assert roll.damageSaveDc is not None
    disadvantage = _damage_save_disadvantage_applies(roll, target)
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
    forced_failure = _damage_save_forced_failure_applies(roll, target)
    forced_failure_conditions = condition_saving_throw_forced_failure_conditions(
        target,
        roll.damageSavingThrow,
    )
    forced_failure_label = _damage_save_forced_failure_label(
        target,
        forced_failure,
        forced_failure_conditions,
    )
    if forced_failure or forced_failure_conditions or response_roll.total < roll.damageSaveDc:
        outcome = (
            f"{target.name} fails DC {roll.damageSaveDc} {enum_label(roll.damageSavingThrow)} "
            f"save{save_label}{forced_failure_label}; resolve failed-save damage/effects next"
        )
    else:
        outcome = (
            f"{target.name} passes DC {roll.damageSaveDc} {enum_label(roll.damageSavingThrow)} "
            f"save{save_label}; resolve passed-save damage/effects next"
        )
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


def _previous_save_outcome(
    roll: RollPayload,
    target: CharacterSheet,
) -> tuple[str, None, RollPayload]:
    assert roll.damageSavingThrow is not None
    assert roll.damageSaveDc is not None
    if not roll.damageSaveSucceeded:
        return (
            f"{target.name} previously failed the DC {roll.damageSaveDc} "
            f"{enum_label(roll.damageSavingThrow)} save",
            None,
            roll,
        )
    if roll.damageSaveOutcome == SpellSaveOutcome.HALF_DAMAGE:
        return (
            f"{target.name} previously passed the DC {roll.damageSaveDc} "
            f"{enum_label(roll.damageSavingThrow)} save for half damage",
            None,
            replace(roll, damageSaveSucceeded=True),
        )
    if roll.damageSaveOutcome == SpellSaveOutcome.NEGATES:
        return (
            f"{target.name} previously passed the DC {roll.damageSaveDc} "
            f"{enum_label(roll.damageSavingThrow)} save and takes no damage",
            None,
            replace(roll, total=0, damageComponents=None, damageSaveSucceeded=True),
        )
    return (
        f"{target.name} previously passed the DC {roll.damageSaveDc} "
        f"{enum_label(roll.damageSavingThrow)} save",
        None,
        replace(roll, damageSaveSucceeded=True),
    )


def _damage_save_disadvantage_applies(roll: RollPayload, target: CharacterSheet) -> bool:
    return bool(
        roll.damageSaveDisadvantageCreatureTypes
        and set(roll.damageSaveDisadvantageCreatureTypes).intersection(target.creatureTypes)
    )


def _damage_save_forced_failure_applies(roll: RollPayload, target: CharacterSheet) -> bool:
    return bool(
        roll.damageSaveForcedFailureCreatureTypes
        and set(roll.damageSaveForcedFailureCreatureTypes).intersection(target.creatureTypes)
    )


def _damage_save_forced_failure_label(
    target: CharacterSheet,
    creature_type_forced_failure: bool,
    condition_forced_failures: list[ConditionType],
) -> str:
    labels = []
    if creature_type_forced_failure:
        labels.append(creature_type_list_label(target.creatureTypes))
    labels.extend(enum_label(condition) for condition in condition_forced_failures)
    return f" due to {_text_list_label(labels)}" if labels else ""


def _text_list_label(values: list[str]) -> str:
    if len(values) <= 1:
        return values[0] if values else ""
    return f"{', '.join(values[:-1])}, and {values[-1]}"


async def create_attack_action(
    room: Room,
    player: Player,
    sheet: CharacterSheet,
    attack_id: str,
    operations: ActionOperations,
    *,
    damage_only: bool = False,
    weapon_option: str | None = None,
    turn_id: str | None = None,
) -> dict[str, Any]:
    attack = find_attack(sheet, attack_id)
    if weapon_option is not None and not any(
        enum_key(option.id) == weapon_option
        for option in attack.weaponAttackOptions or []
    ):
        raise ActionServiceError(400, "Invalid weapon attack option")
    label = "Damage Roll" if damage_only else "Attack Roll"
    activation = None if damage_only else attack.activation
    attack_activation_key = ActivationKey(ActivationKind.ATTACK_ACTION, "attack")
    await assert_activation_allowed(
        room,
        sheet,
        player,
        activation,
        attack.name,
        label,
        operations,
        ActionCategory.ATTACK,
        turn_id,
        activation_key=attack_activation_key,
    )
    payload = (
        build_damage_roll_payload(sheet, player.player_key, attack, weapon_option)
        if damage_only
        else build_combined_attack_roll_payload(sheet, player.player_key, attack, weapon_option)
    )
    await consume_action_resources(
        room,
        sheet,
        player,
        attack.resourceCosts,
        payload,
        operations,
        activation=activation,
        category=ActionCategory.ATTACK,
        turn_id=turn_id,
        activation_instances=character_allocation_value(
            sheet,
            CalculationType.ATTACKS_PER_ACTION,
            participant_sheets=operations.all_sheets(room),
        ),
        activation_key=attack_activation_key,
    )
    return await store_outgoing_roll(room, sheet, payload, operations)


async def create_spell_attack_action(
    room: Room,
    player: Player,
    sheet: CharacterSheet,
    spell_id: str,
    spell_slot_level: int | None,
    operations: ActionOperations,
    turn_id: str | None = None,
) -> dict[str, Any]:
    spell = find_spell(sheet, spell_id)
    validate_spell_slot_level(sheet, spell, spell_slot_level)
    if spell.mechanics is None or not any(
        first_attack_roll_effect(effect) is not None
        for effect in spell.mechanics.activatedEffects
    ):
        raise ActionServiceError(404, "Spell attack not found")
    await assert_activation_allowed(
        room,
        sheet,
        player,
        spell.castingTime,
        enum_label(spell.name),
        "Spell Attack",
        operations,
        ActionCategory.MAGIC,
        turn_id,
    )
    await assert_somatic_spell_cast_allowed(room, sheet, player, spell, operations)
    payload = build_spell_attack_roll_payload(sheet, player.player_key, spell)
    await consume_action_resources(
        room,
        sheet,
        player,
        spell.resourceCosts or (),
        payload,
        operations,
        spell_slot_level or spell.level,
        activation=spell.castingTime,
        category=ActionCategory.MAGIC,
        turn_id=turn_id,
    )
    return await store_outgoing_roll(room, sheet, payload, operations)


async def create_bound_weapon_spell_action(
    room: Room,
    player: Player,
    sheet: CharacterSheet,
    spell_id: str,
    effect_index: int,
    equipment_instance_id: str,
    choice_index: int | None,
    operations: ActionOperations,
    turn_id: str | None = None,
) -> dict[str, Any]:
    spell = find_spell(sheet, spell_id)
    await assert_activation_allowed(
        room,
        sheet,
        player,
        spell.castingTime,
        enum_label(spell.name),
        "Bound Weapon Attack",
        operations,
        ActionCategory.MAGIC,
        turn_id,
    )
    await assert_somatic_spell_cast_allowed(room, sheet, player, spell, operations)
    try:
        payload = build_bound_weapon_spell_attack_payload(
            sheet,
            player.player_key,
            spell,
            effect_index,
            equipment_instance_id,
            choice_index,
        )
    except ValueError as error:
        await log_blocked_roll(
            room,
            sheet,
            player,
            enum_label(spell.name),
            "Bound Weapon Attack",
            str(error),
            operations,
        )
        raise ActionServiceError(400, str(error)) from error
    await _spend_spell_resources(room, sheet, player, spell, payload, None, operations, turn_id)
    return await store_outgoing_roll(room, sheet, payload, operations)


async def create_spell_damage_action(
    room: Room,
    player: Player,
    sheet: CharacterSheet,
    spell_id: str,
    effect_index: int,
    spell_slot_level: int | None,
    instance_index: int | None,
    damage_save_succeeded: bool | None,
    choice_index: int | None,
    operations: ActionOperations,
    turn_id: str | None = None,
) -> dict[str, Any]:
    spell = find_spell(sheet, spell_id)
    validate_spell_slot_level(sheet, spell, spell_slot_level)
    activation_key = _spell_activation_key(spell_id, effect_index, spell_slot_level, choice_index)
    activation_instances = _spell_effect_instance_count(
        sheet, spell, effect_index, spell_slot_level, choice_index
    )
    activation_authorization = await assert_activation_allowed(
        room,
        sheet,
        player,
        spell.castingTime,
        enum_label(spell.name),
        "Spell Damage",
        operations,
        ActionCategory.MAGIC,
        turn_id,
        activation_key=activation_key,
        part_id=instance_index,
    )
    if spell.mechanics is not None and activation_authorization.activeAction is None:
        await assert_somatic_spell_cast_allowed(room, sheet, player, spell, operations)
    try:
        payload = build_spell_damage_roll_payload(
            sheet,
            player.player_key,
            spell,
            effect_index,
            spell_slot_level,
            instance_index,
            damage_save_succeeded,
            choice_index,
        )
    except ValueError as error:
        raise ActionServiceError(404, str(error)) from error
    await _spend_spell_resources(
        room,
        sheet,
        player,
        spell,
        payload,
        spell_slot_level,
        operations,
        turn_id,
        activation_instances=activation_instances,
        activation_key=activation_key,
        part_id=instance_index,
    )
    return await store_outgoing_roll(room, sheet, payload, operations)


async def create_spell_simple_action(
    room: Room,
    player: Player,
    sheet: CharacterSheet,
    spell_id: str,
    effect_index: int,
    spell_slot_level: int | None,
    operations: ActionOperations,
    *,
    action_type: SpellRollType,
    choice_index: int | None = None,
    equipment_instance_id: str | None = None,
    turn_id: str | None = None,
) -> dict[str, Any]:
    spell = find_spell(sheet, spell_id)
    validate_spell_slot_level(sheet, spell, spell_slot_level)
    labels = {
        SpellRollType.HEALING: "Spell Healing",
        SpellRollType.TEMPORARY_HIT_POINTS: "Temporary Hit Points",
        SpellRollType.EFFECT: "Spell Effect",
    }
    await assert_activation_allowed(
        room,
        sheet,
        player,
        spell.castingTime,
        enum_label(spell.name),
        labels[action_type],
        operations,
        ActionCategory.MAGIC,
        turn_id,
    )
    await assert_somatic_spell_cast_allowed(room, sheet, player, spell, operations)
    try:
        if action_type == SpellRollType.HEALING:
            payload = build_spell_healing_roll_payload(
                sheet,
                player.player_key,
                spell,
                effect_index,
                spell_slot_level,
            )
        elif action_type == SpellRollType.TEMPORARY_HIT_POINTS:
            payload = build_spell_temporary_hit_points_roll_payload(
                sheet,
                player.player_key,
                spell,
                effect_index,
                spell_slot_level,
            )
        else:
            payload = (
                build_bound_weapon_spell_effect_payload(
                    sheet,
                    player.player_key,
                    spell,
                    effect_index,
                    equipment_instance_id,
                )
                if equipment_instance_id is not None
                else build_spell_condition_roll_payload(
                    sheet,
                    player.player_key,
                    spell,
                    effect_index,
                    choice_index,
                )
            )
    except ValueError as error:
        if equipment_instance_id is not None:
            await log_blocked_roll(
                room,
                sheet,
                player,
                enum_label(spell.name),
                labels[action_type],
                str(error),
                operations,
            )
        raise ActionServiceError(400 if equipment_instance_id is not None else 404, str(error)) from error
    await _spend_spell_resources(
        room,
        sheet,
        player,
        spell,
        payload,
        spell_slot_level,
        operations,
        turn_id,
    )
    return await store_outgoing_roll(room, sheet, payload, operations)


async def create_ability_score_action(
    room: Room,
    player: Player,
    sheet: CharacterSheet,
    ability_key: str,
    operations: ActionOperations,
    *,
    saving_throw: bool = False,
) -> dict[str, Any]:
    ability = enum_value(AbilityType, ability_key)
    if ability is None:
        raise ActionServiceError(404, "Ability not found")
    payload = (
        build_saving_throw_roll_payload(sheet, player.player_key, ability)
        if saving_throw
        else build_ability_check_roll_payload(sheet, player.player_key, ability)
    )
    prompt = resolution_prompt_for_d20_test(payload, sheet)
    if prompt is not None:
        room.pending_resolution_prompts[prompt.id] = prompt
        prompt_data = resolution_interceptor_prompt_to_dict(prompt)
        await operations.broadcast(room, {"type": "resolution_prompt_created", "prompt": prompt_data})
        return {"roomId": room.id, "prompt": prompt_data}
    return await store_roll(room, payload, operations)


async def create_sheet_entry_action(
    room: Room,
    player: Player,
    sheet: CharacterSheet,
    entry_id: str,
    action_id: str,
    operations: ActionOperations,
    *,
    resource_entry: bool,
    turn_id: str | None = None,
) -> dict[str, Any]:
    entries = sheet.resources if resource_entry else sheet.abilities
    entry = next(
        (candidate for candidate in entries if sanitize_identifier(candidate.id) == sanitize_identifier(entry_id)),
        None,
    )
    if entry is None:
        raise ActionServiceError(404, "Resource not found" if resource_entry else "Ability not found")
    action = next(
        (
            candidate
            for candidate in entry.rollActions or []
            if sanitize_identifier(enum_key(candidate.id)) == sanitize_identifier(action_id)
        ),
        None,
    )
    if action is None:
        raise ActionServiceError(404, "Roll action not found")
    source_label = entry.name if resource_entry else entry.source
    await assert_activation_allowed(
        room,
        sheet,
        player,
        action.activation or entry.activation,
        source_label,
        enum_label(action.name),
        operations,
        ActionCategory.FEATURE,
        turn_id,
        timing=action.activationTiming,
    )
    source = RollSource(
        section=SheetSectionType.RESOURCES if resource_entry else SheetSectionType.ABILITIES,
        sourceId=entry.id,
        actionId=enum_key(action.id),
    )
    payload = build_roll_action_payload(
        sheet,
        player.player_key,
        source,
        action,
        source_label=source_label,
    )
    await consume_action_resources(
        room,
        sheet,
        player,
        action.resourceCosts,
        payload,
        operations,
        activation=action.activation or entry.activation,
        category=ActionCategory.FEATURE,
        turn_id=turn_id,
        timing=action.activationTiming,
        activation_key=ActivationKey(ActivationKind.FEATURE, entry.id, enum_key(action.id)),
    )
    return await store_outgoing_roll(room, sheet, payload, operations)


async def create_ad_hoc_dice_action(
    room: Room,
    player: Player,
    dice: str,
    count: int,
    operations: ActionOperations,
) -> dict[str, Any]:
    dice_type = enum_value(DiceType, dice)
    if dice_type is None:
        raise ActionServiceError(400, "Invalid dice type")
    dice_count = min(20, max(1, count))
    rolls = [random.randint(1, dice_type.value) for _ in range(dice_count)]
    created_at = time_ns()
    payload = RollPayload(
        id=f"roll-{created_at}",
        sheetId=player.player_key,
        tokenId=player.player_key,
        roller=player.player_key,
        source=RollSource(
            section=SheetSectionType.DICE_ROLLER,
            sourceId=enum_key(dice_type),
            actionId="roll",
        ),
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
    log_entry = append_roll_log_entry(room, _created_log_entry(payload), operations.history_limit)
    await operations.broadcast(
        room,
        {
            "type": "roll_logged",
            "roll": roll_payload_to_dict(payload),
            "logEntry": roll_log_entry_to_dict(log_entry),
        },
    )
    return {
        "roomId": room.id,
        "roll": roll_payload_to_dict(payload),
        "logEntry": roll_log_entry_to_dict(log_entry),
    }


async def store_outgoing_roll(
    room: Room,
    sheet: CharacterSheet,
    payload: RollPayload,
    operations: ActionOperations,
) -> dict[str, Any]:
    response = await store_roll(room, payload, operations)
    clear_conditions_after_outgoing_roll(room, sheet, payload, operations)
    if payload.resourcesSpent:
        operations.save(room)
        await operations.broadcast_room(room)
    return response


async def store_roll(
    room: Room,
    payload: RollPayload,
    operations: ActionOperations,
) -> dict[str, Any]:
    if _roll_resolves_immediately(payload):
        from dnd_board.application.character_state_service import apply_roll_result

        target = next(
            (sheet for sheet in operations.all_sheets(room) if sheet.id == payload.sheetId),
            None,
        )
        if target is None:
            raise ActionServiceError(404, "Sheet not found")
        resolution = apply_roll_result(
            room,
            payload,
            target,
            target,
            None,
            operations.all_sheets(room),
            operations.state_persistence,
        )
        if resolution.concentrationUpdates:
            operations.save(room)
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
            operations.history_limit,
        )
        await operations.broadcast(
            room,
            {
                "type": "roll_resolved",
                "rollId": payload.id,
                "tokenId": payload.tokenId,
                "resolution": resolution_data,
                "logEntry": roll_log_entry_to_dict(log_entry),
            },
        )
        return {
            "roomId": room.id,
            "roll": roll_payload_to_dict(payload),
            "resolution": resolution_data,
            "logEntry": roll_log_entry_to_dict(log_entry),
        }

    room.pending_rolls[_roll_queue_key(payload)] = payload
    roll = roll_payload_to_dict(payload)
    log_entry = append_roll_log_entry(room, _created_log_entry(payload), operations.history_limit)
    await operations.broadcast(
        room,
        {"type": "roll_created", "roll": roll, "logEntry": roll_log_entry_to_dict(log_entry)},
    )
    return {"roomId": room.id, "roll": roll, "logEntry": roll_log_entry_to_dict(log_entry)}


async def consume_action_resources(
    room: Room,
    sheet: CharacterSheet,
    player: Player,
    costs: tuple[ResourceCost, ...],
    payload: RollPayload,
    operations: ActionOperations,
    spell_slot_level: int | None = None,
    *,
    activation: TimeEconomy | None = None,
    category: ActionCategory = ActionCategory.OTHER,
    turn_id: str | None = None,
    activation_instances: int = 1,
    timing: ActivationTiming = ActivationTiming.UNRESTRICTED,
    activation_key: ActivationKey | None = None,
    part_id: int | None = None,
) -> list[ResourceUpdate]:
    authorization = authorize_action(
        room,
        sheet.id,
        activation,
        category,
        turn_id,
        timing=timing,
        activation_key=activation_key,
        part_id=part_id,
        sheet=sheet,
        participant_sheets=operations.all_sheets(room),
    )
    if not authorization.allowed:
        reason = authorization.reason or "Action is unavailable"
        await log_blocked_roll(
            room,
            sheet,
            player,
            payload.sourceLabel,
            payload.label,
            reason,
            operations,
        )
        raise ActionServiceError(409, reason)
    try:
        payable_costs = payable_resource_costs(
            costs,
            continuation=authorization.activeAction is not None,
        )
        spent = spend_sheet_resources(room, sheet, payable_costs, spell_slot_level)
    except InsufficientResourceError as error:
        await log_blocked_roll(
            room,
            sheet,
            player,
            payload.sourceLabel,
            payload.label,
            str(error),
            operations,
        )
        raise ActionServiceError(409, str(error)) from error
    except ValueError as error:
        raise ActionServiceError(400, str(error)) from error
    encounter_before = room.encounter
    commit_action_authorization(
        room,
        sheet.id,
        authorization,
        activation_instances,
        activation_key,
        part_id,
    )
    activation_resource = authorization.resource
    if encounter_before != room.encounter and activation_resource is not None and room.encounter is not None:
        participant = next(
            entry for entry in room.encounter.participantStates
            if entry.participantId == sheet.id
        )
        state = next(entry for entry in participant.resources if entry.resource == activation_resource)
        spent.append(ResourceUpdate(state.resource, state.resource.value, state.current, state.maximum))
    payload.resourcesSpent = spent or None
    return spent


async def assert_activation_allowed(
    room: Room,
    sheet: CharacterSheet,
    player: Player,
    activation: TimeEconomy | None,
    source_label: str,
    roll_label: str,
    operations: ActionOperations,
    category: ActionCategory = ActionCategory.OTHER,
    turn_id: str | None = None,
    *,
    timing: ActivationTiming = ActivationTiming.UNRESTRICTED,
    activation_key: ActivationKey | None = None,
    part_id: int | None = None,
) -> ActivationAuthorization:
    authorization = authorize_action(
        room,
        sheet.id,
        activation,
        category,
        turn_id,
        timing=timing,
        activation_key=activation_key,
        part_id=part_id,
        sheet=sheet,
        participant_sheets=operations.all_sheets(room),
    )
    if not authorization.allowed:
        reason = authorization.reason or "Action is unavailable"
        await log_blocked_roll(room, sheet, player, source_label, roll_label, reason, operations)
        raise ActionServiceError(409, reason)
    blocking_condition = activation_blocking_condition(sheet.conditions, activation)
    if blocking_condition is None:
        return authorization
    reaction_only = activation == TimeEconomy.REACTION and blocking_condition == ConditionType.SLOWED
    scope = "Reactions" if reaction_only else "Actions, Bonus Actions, and Reactions"
    await log_blocked_roll(
        room,
        sheet,
        player,
        source_label,
        roll_label,
        f"{enum_label(blocking_condition)} prevents {scope}",
        operations,
    )
    detail = (
        f"{enum_label(blocking_condition)} creatures cannot take Reactions"
        if reaction_only
        else f"{enum_label(blocking_condition)} creatures cannot take Actions, Bonus Actions, or Reactions"
    )
    raise ActionServiceError(400, detail)


async def assert_somatic_spell_cast_allowed(
    room: Room,
    sheet: CharacterSheet,
    player: Player,
    spell: SpellEntry,
    operations: ActionOperations,
) -> None:
    failure = action_failure_chance(sheet.conditions, spell.castingTime, spell.components)
    if failure is None:
        return
    condition, chance = failure
    check = random.randint(1, chance.denominator)
    spell_label = enum_label(spell.name)
    if check <= chance.numerator:
        reason = (
            f"{enum_label(condition)} somatic delay fails on "
            f"1d{chance.denominator} ({check})"
        )
        await log_blocked_roll(
            room,
            sheet,
            player,
            spell_label,
            "Spell Cast",
            reason,
            operations,
        )
        raise ActionServiceError(400, f"{enum_label(condition)} somatic spell failed")
    await log_roll_note(
        room,
        sheet,
        player,
        spell_label,
        (
            f"{enum_label(condition)} somatic check succeeds on "
            f"1d{chance.denominator} ({check}); spell continues"
        ),
        DiceType.D4,
        [check],
        operations,
    )


async def log_blocked_roll(
    room: Room,
    sheet: CharacterSheet,
    player: Player,
    source_label: str,
    roll_label: str,
    reason: str,
    operations: ActionOperations,
) -> RollLogEntry:
    return await log_roll_note(
        room,
        sheet,
        player,
        source_label,
        f"{roll_label} blocked: {reason}",
        DiceType.D20,
        [],
        operations,
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
    operations: ActionOperations,
    *,
    entry_type: RollLogEntryType = RollLogEntryType.ROLL_CREATED,
    message_type: str = "roll_logged",
) -> RollLogEntry:
    created_at = time_ns()
    payload = RollPayload(
        id=f"roll-{created_at}",
        sheetId=sheet.id,
        tokenId=sheet.tokenId,
        roller=player.player_key,
        source=RollSource(
            section=SheetSectionType.ABILITIES,
            sourceId=sanitize_identifier(source_label),
            actionId="log",
        ),
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
        operations.history_limit,
    )
    await operations.broadcast(
        room,
        {"type": message_type, "logEntry": roll_log_entry_to_dict(log_entry)},
    )
    return log_entry


def append_roll_log_entry(
    room: Room,
    entry: RollLogEntry,
    history_limit: int,
) -> RollLogEntry:
    room.roll_history.append(entry)
    room.roll_history = room.roll_history[-history_limit:]
    return entry


def clear_conditions_after_outgoing_roll(
    room: Room,
    sheet: CharacterSheet,
    roll: RollPayload,
    operations: ActionOperations,
) -> bool:
    is_spell = roll.source.section == SheetSectionType.SPELLS
    is_attack = (
        roll.source.actionId == enum_key(RollResolutionMode.ATTACK_VS_ARMOR_CLASS)
        or roll.resolution == RollResolutionMode.ATTACK_VS_ARMOR_CLASS
    )
    deals_damage = roll.resolution == RollResolutionMode.APPLY_DAMAGE
    ended = set(
        conditions_ending_on_event(
            sheet.conditions,
            ResolutionEventType.SPELL_DECLARED,
            is_spell=is_spell,
        )
        + conditions_ending_on_event(
            sheet.conditions,
            ResolutionEventType.ACTION_DECLARED,
            is_attack=is_attack,
        )
        + conditions_ending_on_event(
            sheet.conditions,
            ResolutionEventType.DAMAGE_APPLIED,
            deals_damage=deals_damage,
        )
    )
    active_effects = list(room.ongoing_effects.get(sheet.id, []))
    remaining_effects = active_effects
    if is_spell:
        remaining_effects = ongoing_effects_after_ending(
            remaining_effects,
            EndingConditionType.OWNER_CASTS_SPELL,
            target_sheet_id=sheet.id,
        )
    if is_attack:
        remaining_effects = ongoing_effects_after_ending(
            remaining_effects,
            EndingConditionType.OWNER_ATTACKS,
            target_sheet_id=sheet.id,
        )
    if deals_damage:
        remaining_effects = ongoing_effects_after_ending(
            remaining_effects,
            EndingConditionType.OWNER_DEALS_DAMAGE,
            target_sheet_id=sheet.id,
        )
    if not ended and remaining_effects == active_effects:
        return False
    next_conditions = [condition for condition in sheet.conditions if condition not in ended]
    room.condition_overrides[sheet.tokenId] = next_conditions
    for condition in ended:
        room.condition_durations.setdefault(sheet.tokenId, {}).pop(condition, None)
        room.condition_removals.setdefault(sheet.tokenId, {}).pop(condition, None)
    room.suppressed_conditions[sheet.tokenId] = [
        condition
        for condition in room.suppressed_conditions.get(sheet.tokenId, [])
        if condition not in ended
    ]
    operations.state_persistence.persist_conditions(room.id, sheet.id, next_conditions)
    if remaining_effects != active_effects:
        room.ongoing_effects[sheet.id] = remaining_effects
        operations.save(room)
    return True


def find_attack(sheet: CharacterSheet, attack_id: str):
    sanitized = sanitize_identifier(attack_id)
    attack = next(
        (candidate for candidate in sheet.attacks if sanitize_identifier(candidate.id) == sanitized),
        None,
    )
    if attack is None and sanitized == "main-hand" and sheet.attacks:
        attack = sheet.attacks[0]
    if attack is None:
        raise ActionServiceError(404, "Attack not found")
    return attack


def find_spell(sheet: CharacterSheet, spell_id: str) -> SpellEntry:
    sanitized = sanitize_identifier(spell_id)
    spell = next(
        (
            candidate
            for candidate in sheet.spells
            if sanitize_identifier(enum_key(candidate.id)) == sanitized
        ),
        None,
    )
    if spell is None:
        raise ActionServiceError(404, "Spell not found")
    return spell


def validate_spell_slot_level(
    sheet: CharacterSheet,
    spell: SpellEntry,
    spell_slot_level: int | None,
) -> None:
    if spell_slot_level is None or spell.level == 0:
        return
    if spell_slot_level < spell.level:
        raise ActionServiceError(400, "Spell slot level is too low")
    available_levels = {
        resource.spellSlotLevel
        for resource in sheet.resources
        if resource.spellSlotLevel is not None
    }
    if spell_slot_level not in available_levels:
        raise ActionServiceError(400, "Spell slot level is not available")


def _spell_activation_key(
    spell_id: str,
    effect_index: int,
    spell_slot_level: int | None,
    choice_index: int | None,
) -> ActivationKey:
    option_id = ":".join(
        str(value) for value in (
            effect_index,
            spell_slot_level if spell_slot_level is not None else 0,
            choice_index if choice_index is not None else 0,
        )
    )
    return ActivationKey(ActivationKind.SPELL, spell_id, option_id)


def _spell_effect_instance_count(
    sheet: CharacterSheet,
    spell: SpellEntry,
    effect_index: int,
    spell_slot_level: int | None,
    choice_index: int | None,
) -> int:
    if spell.mechanics is None:
        return 1
    node = activated_effect_node(direct_damage_action_at(spell.mechanics, effect_index))
    if isinstance(node, ChoiceEffect):
        selected = choice_index if choice_index is not None else 0
        if selected < 0 or selected >= len(node.choices):
            return 1
        node = activated_effect_node(node.choices[selected].effect)
    if not isinstance(node, RepeatedEffect):
        return 1
    return scaled_instance_count(node.instances, sheet, spell.level, spell_slot_level)


async def _spend_spell_resources(
    room: Room,
    sheet: CharacterSheet,
    player: Player,
    spell: SpellEntry,
    payload: RollPayload,
    spell_slot_level: int | None,
    operations: ActionOperations,
    turn_id: str | None = None,
    *,
    activation_instances: int = 1,
    activation_key: ActivationKey | None = None,
    part_id: int | None = None,
) -> None:
    await consume_action_resources(
        room,
        sheet,
        player,
        spell.resourceCosts or (),
        payload,
        operations,
        spell_slot_level or spell.level,
        activation=spell.castingTime,
        category=ActionCategory.MAGIC,
        turn_id=turn_id,
        activation_instances=activation_instances,
        activation_key=activation_key,
        part_id=part_id,
    )


def _roll_resolves_immediately(roll: RollPayload) -> bool:
    return (
        (
            roll.resolution == RollResolutionMode.HEAL_SELF
            and roll.source.section != SheetSectionType.SPELLS
        )
        or roll.resolution == RollResolutionMode.APPLY_TO_SELF
    )


def _created_log_entry(payload: RollPayload) -> RollLogEntry:
    return RollLogEntry(
        id=f"log-{payload.id}",
        entryType=RollLogEntryType.ROLL_CREATED,
        createdAt=payload.createdAt,
        roll=payload,
    )


def _roll_queue_key(roll: RollPayload) -> tuple[str, str, str, str]:
    return (
        roll.tokenId,
        enum_key(roll.source.section),
        roll.source.sourceId,
        roll.source.actionId,
    )
