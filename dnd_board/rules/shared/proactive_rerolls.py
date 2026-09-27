from __future__ import annotations

from dataclasses import dataclass, replace
import random
from typing import Callable

from dnd_board.character_sheet import DieReplacement, RollModifierBreakdown, RollPayload, RollResolutionMode
from dnd_board.rules.shared.character_effects import resolved_d20
from dnd_board.rules.shared.effects import EffectNodeId


@dataclass(frozen=True)
class DieReroll:
    roll: RollPayload
    original: int
    replacement: int


def reroll_failed_d20(
    roll: RollPayload,
    source_label: str,
    roll_die: Callable[[int, int], int] | None = None,
) -> DieReroll | None:
    if not roll.dice or roll.diceType.value != 20:
        return None
    original = resolved_d20(roll)
    index = roll.dice.index(original)
    replacement = (roll_die or random.randint)(1, 20)
    dice = list(roll.dice)
    dice[index] = replacement
    updated = replace(roll, dice=dice)
    updated = replace(
        updated,
        total=resolved_d20(updated) + updated.modifier,
        modifierBreakdown=[
            *roll.modifierBreakdown,
            RollModifierBreakdown(source_label, 0, f"Rerolled {original} to {replacement}; new roll required"),
        ],
        dieReplacements=[*(roll.dieReplacements or []), DieReplacement(original, replacement, roll.proactiveResource)],
    )
    return DieReroll(updated, original, replacement)


def reroll_minimum_damage_die(
    roll: RollPayload,
    source_label: str,
    node_id: EffectNodeId | None = None,
    roll_die: Callable[[int, int], int] | None = None,
) -> DieReroll | None:
    components = list(roll.damageComponents or [])
    for component_index, component in enumerate(components):
        if node_id is not None and node_id not in (component.effectNodeIds or []):
            continue
        if 1 not in component.dice:
            continue
        die_index = component.dice.index(1)
        replacement = (roll_die or random.randint)(1, component.diceType.value)
        dice = list(component.dice)
        dice[die_index] = replacement
        updated_component = replace(
            component,
            dice=dice,
            total=component.total + replacement - 1,
            modifierBreakdown=[
                *component.modifierBreakdown,
                RollModifierBreakdown(source_label, 0, f"Rerolled damage die 1 to {replacement}; new roll required"),
            ],
        )
        components[component_index] = updated_component
        affected_nodes = set(component.effectNodeIds or [])
        inputs = roll.effectInputs
        if inputs is not None:
            inputs = replace(inputs, amounts=[
                replace(entry, amount=entry.amount + replacement - 1)
                if entry.effectNodeId in affected_nodes else entry
                for entry in inputs.amounts
            ])
        updated = replace(
            roll,
            damageComponents=components,
            effectInputs=inputs,
            total=(roll.total if roll.resolution == RollResolutionMode.ATTACK_VS_ARMOR_CLASS else roll.total + replacement - 1),
            dieReplacements=[*(roll.dieReplacements or []), DieReplacement(1, replacement, roll.proactiveResource)],
        )
        if roll.resolution != RollResolutionMode.ATTACK_VS_ARMOR_CLASS and component_index == 0:
            updated = replace(updated, dice=dice)
        return DieReroll(updated, 1, replacement)
    if components or roll.resolution == RollResolutionMode.ATTACK_VS_ARMOR_CLASS or 1 not in roll.dice:
        return None
    die_index = roll.dice.index(1)
    replacement = (roll_die or random.randint)(1, roll.diceType.value)
    dice = list(roll.dice)
    dice[die_index] = replacement
    inputs = roll.effectInputs
    if inputs is not None:
        inputs = replace(inputs, amounts=[
            replace(entry, amount=entry.amount + replacement - 1)
            if node_id is None or entry.effectNodeId == node_id else entry
            for entry in inputs.amounts
        ])
    return DieReroll(
        replace(
            roll,
            dice=dice,
            total=roll.total + replacement - 1,
            effectInputs=inputs,
            modifierBreakdown=[
                *roll.modifierBreakdown,
                RollModifierBreakdown(source_label, 0, f"Rerolled damage die 1 to {replacement}; new roll required"),
            ],
            dieReplacements=[*(roll.dieReplacements or []), DieReplacement(1, replacement, roll.proactiveResource)],
        ),
        1,
        replacement,
    )


def reroll_runtime_damage_die(
    roll: RollPayload,
    dice: list[tuple[int, int]],
    roll_die: Callable[[int, int], int] | None = None,
) -> DieReroll | None:
    for sides, value in dice:
        if value != 1:
            continue
        replacement = (roll_die or random.randint)(1, sides)
        updated = replace(
            roll,
            dieReplacements=[*(roll.dieReplacements or []), DieReplacement(1, replacement, roll.proactiveResource)],
        )
        return DieReroll(updated, 1, replacement)
    return None
