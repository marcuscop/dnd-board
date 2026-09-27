from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

from dnd_board.application.resource_service import spend_sheet_resources
from dnd_board.application.room_state import Room
from dnd_board.character_sheet import CharacterSheet, RollPayload
from dnd_board.rules.shared.effects import EffectNodeId
from dnd_board.rules.shared.proactive_rerolls import DieReroll, reroll_failed_d20, reroll_minimum_damage_die, reroll_runtime_damage_die
from dnd_board.rules.shared.resources import (
    RESOURCE_DEFINITIONS,
    InsufficientResourceError,
    ProactiveRerollTrigger,
    ResourceCost,
)


def reroll_failed_test(
    room: Room,
    roll: RollPayload,
    owner: CharacterSheet,
    all_sheets: Callable[[Room], list[CharacterSheet]],
    save: Callable[[Room], None],
) -> DieReroll | None:
    if not policy_allows(roll, ProactiveRerollTrigger.FAILED_D20_TEST):
        return None
    result = reroll_failed_d20(roll, RESOURCE_DEFINITIONS[roll.proactiveResource].label)
    return _spend_reroll(room, roll, result, owner, all_sheets, save)


def reroll_minimum_damage(
    room: Room,
    roll: RollPayload,
    owner: CharacterSheet,
    node_id: EffectNodeId,
    all_sheets: Callable[[Room], list[CharacterSheet]],
    save: Callable[[Room], None],
) -> DieReroll | None:
    if not policy_allows(roll, ProactiveRerollTrigger.MINIMUM_DAMAGE_DIE):
        return None
    result = reroll_minimum_damage_die(roll, RESOURCE_DEFINITIONS[roll.proactiveResource].label, node_id)
    return _spend_reroll(room, roll, result, owner, all_sheets, save)


def reroll_runtime_damage(
    room: Room,
    roll: RollPayload,
    owner: CharacterSheet,
    dice: list[tuple[int, int]],
    all_sheets: Callable[[Room], list[CharacterSheet]],
    save: Callable[[Room], None],
) -> DieReroll | None:
    if not policy_allows(roll, ProactiveRerollTrigger.MINIMUM_DAMAGE_DIE):
        return None
    result = reroll_runtime_damage_die(roll, dice)
    spent = _spend_reroll(room, roll, result, owner, all_sheets, save)
    if spent is not None:
        for index, (sides, value) in enumerate(dice):
            if value == 1:
                dice[index] = (sides, spent.replacement)
                break
    return spent


def policy_allows(roll: RollPayload, trigger: ProactiveRerollTrigger) -> bool:
    if roll.proactiveResource is None:
        return False
    definition = RESOURCE_DEFINITIONS.get(roll.proactiveResource)
    return definition is not None and definition.proactiveReroll is not None and trigger in definition.proactiveReroll.triggers


def _spend_reroll(
    room: Room,
    original: RollPayload,
    result: DieReroll | None,
    owner: CharacterSheet,
    all_sheets: Callable[[Room], list[CharacterSheet]],
    save: Callable[[Room], None],
) -> DieReroll | None:
    if result is None or original.proactiveResource is None:
        return None
    current_owner = next((sheet for sheet in all_sheets(room) if sheet.id == owner.id), None)
    if current_owner is None:
        return None
    try:
        updates = spend_sheet_resources(room, current_owner, (ResourceCost(original.proactiveResource),))
    except InsufficientResourceError:
        return None
    save(room)
    return replace(result, roll=replace(
        result.roll,
        proactiveResource=None,
        resourcesSpent=[*(original.resourcesSpent or []), *(replace(update, ownerSheetId=owner.id) for update in updates)],
    ))
