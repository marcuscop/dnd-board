from __future__ import annotations

import random
from dataclasses import dataclass

from dnd_board.character_sheet import CharacterSheet, DiceType, HIT_DIE_RESOURCES, ability_modifier
from dnd_board.rules.shared.resources import ResourceId, ResourceKind


@dataclass(frozen=True)
class HitDieSpend:
    resource: ResourceId
    count: int


@dataclass(frozen=True)
class HitDieRestResult:
    resource: ResourceId
    die: DiceType
    rolls: tuple[int, ...]
    healing: int
    hitPointsRestored: int
    remaining: int


def validate_hit_die_spends(sheet: CharacterSheet, spends: list[HitDieSpend]) -> None:
    if spends and sheet.hp.current < 1:
        raise ValueError(f"{sheet.name} must have at least 1 Hit Point to benefit from a Short Rest")
    resources = {resource.resource: resource for resource in sheet.resources}
    seen: set[ResourceId] = set()
    for spend in spends:
        resource = resources.get(spend.resource)
        if resource is None or resource.kind != ResourceKind.HIT_DIE or spend.resource not in HIT_DIE_RESOURCES.values():
            raise ValueError(f"{sheet.name} does not have that Hit Die")
        if spend.resource in seen:
            raise ValueError(f"Duplicate Hit Die selection for {sheet.name}")
        seen.add(spend.resource)
        if isinstance(spend.count, bool) or not isinstance(spend.count, int) or spend.count < 1:
            raise ValueError("Hit Dice spent must be a positive whole number")
        if spend.count > resource.currentUses:
            raise ValueError(f"{sheet.name} has only {resource.currentUses} {resource.name} remaining")


def roll_hit_dice_for_rest(sheet: CharacterSheet, spends: list[HitDieSpend]) -> tuple[int, list[HitDieRestResult]]:
    validate_hit_die_spends(sheet, spends)
    resources = {resource.resource: resource for resource in sheet.resources}
    die_sizes = {resource: size for size, resource in HIT_DIE_RESOURCES.items()}
    constitution_modifier = ability_modifier(sheet.abilityScores.constitution)
    current_hp = sheet.hp.current
    results: list[HitDieRestResult] = []
    for spend in spends:
        die = DiceType(die_sizes[spend.resource])
        rolls = tuple(random.randint(1, die.value) for _ in range(spend.count))
        healing = sum(max(1, roll + constitution_modifier) for roll in rolls)
        next_hp = min(sheet.hp.max, current_hp + healing)
        results.append(HitDieRestResult(
            resource=spend.resource,
            die=die,
            rolls=rolls,
            healing=healing,
            hitPointsRestored=next_hp - current_hp,
            remaining=resources[spend.resource].currentUses - spend.count,
        ))
        current_hp = next_hp
    return current_hp, results
