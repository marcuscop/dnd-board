from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, replace
from enum import Enum
from typing import Mapping, Sequence


class ResourceKind(Enum):
    SPELL_SLOT = "Spell Slot"
    FEATURE_USE = "Feature Use"
    ITEM_CHARGE = "Item Charge"
    AMMUNITION = "Ammunition"
    ACTION = "Action"
    BONUS_ACTION = "Bonus Action"
    REACTION = "Reaction"


class ResourceId(Enum):
    SPELL_SLOT = "Selected Spell Slot"
    FIRST_LEVEL_SPELL_SLOTS = "First Level Spell Slots"
    SECOND_LEVEL_SPELL_SLOTS = "Second Level Spell Slots"
    THIRD_LEVEL_SPELL_SLOTS = "Third Level Spell Slots"
    FOURTH_LEVEL_SPELL_SLOTS = "Fourth Level Spell Slots"
    FIFTH_LEVEL_SPELL_SLOTS = "Fifth Level Spell Slots"
    SIXTH_LEVEL_SPELL_SLOTS = "Sixth Level Spell Slots"
    SEVENTH_LEVEL_SPELL_SLOTS = "Seventh Level Spell Slots"
    EIGHTH_LEVEL_SPELL_SLOTS = "Eighth Level Spell Slots"
    NINTH_LEVEL_SPELL_SLOTS = "Ninth Level Spell Slots"
    SECOND_WIND = "Second Wind"
    ACTION_SURGE = "Action Surge"
    INDOMITABLE = "Indomitable"
    ARCANE_RECOVERY = "Arcane Recovery"
    SUPERIORITY_DICE = "Superiority Dice"
    PSI_WARRIOR_PSIONIC_ENERGY_DICE = "Psi Warrior Psionic Energy Dice"
    SOULKNIFE_PSIONIC_ENERGY_DICE = "Soulknife Psionic Energy Dice"
    STROKE_OF_LUCK = "Stroke of Luck"
    LUCK_POINTS = "Luck Points"
    MAGE_SLAYER = "Mage Slayer"
    BOON_OF_COMBAT_PROWESS = "Boon of Combat Prowess"
    BOON_OF_DIMENSIONAL_TRAVEL = "Boon of Dimensional Travel"
    BOON_OF_FATE = "Boon of Fate"
    BOON_OF_RECOVERY = "Boon of Recovery"
    MAGIC_INITIATE_FREE_CAST = "Magic Initiate Free Cast"
    GROUP_RECOVERY = "Group Recovery"
    KNOW_YOUR_ENEMY = "Know Your Enemy"
    ARCANE_SHOT = "Arcane Shot"
    UNWAVERING_MARK = "Unwavering Mark"
    WARDING_MANEUVER = "Warding Maneuver"
    FIGHTING_SPIRIT = "Fighting Spirit"
    STRENGTH_BEFORE_DEATH = "Strength Before Death"
    STEADY_AIM = "Steady Aim"
    PROTECTION_FROM_EVIL_AND_GOOD = "Protection from Evil and Good"
    GIANTS_MIGHT = "Giant's Might"
    RUNIC_SHIELD = "Runic Shield"
    CLOUD_RUNE = "Cloud Rune"
    FIRE_RUNE = "Fire Rune"
    FROST_RUNE = "Frost Rune"
    STONE_RUNE = "Stone Rune"
    HILL_RUNE = "Hill Rune"
    STORM_RUNE = "Storm Rune"
    UNLEASH_INCARNATION = "Unleash Incarnation"
    SHADOW_MARTYR = "Shadow Martyr"
    RECLAIM_POTENTIAL = "Reclaim Potential"
    PSIONIC_ENERGY_RECOVERY = "Psionic Energy Recovery"
    TELEKINETIC_MOVEMENT = "Telekinetic Movement"
    PSI_POWERED_LEAP = "Psi-Powered Leap"
    BULWARK_OF_FORCE = "Bulwark of Force"
    TELEKINETIC_MASTER = "Telekinetic Master"
    SPELL_THIEF = "Spell Thief"
    WAILS_FROM_THE_GRAVE = "Wails from the Grave"
    SOUL_TRINKETS = "Soul Trinkets"
    VOICE_OF_DEATH = "Voice of Death"
    GHOST_WALK = "Ghost Walk"
    BLOODTHIRST = "Bloodthirst"
    PSYCHIC_VEIL = "Psychic Veil"
    REND_MIND = "Rend Mind"
    ARCANE_WARD = "Arcane Ward"
    PORTENT = "Portent"
    GREATER_PORTENT = "Greater Portent"
    BLADESONG = "Bladesong"
    ILLUSORY_SELF = "Illusory Self"
    ARROWS = "Arrows"
    BOLTS = "Bolts"
    ACTION = "Action"
    BONUS_ACTION = "Bonus Action"
    REACTION = "Reaction"


class ResourceRecoveryTrigger(Enum):
    SHORT_REST = "Short Rest"
    LONG_REST = "Long Rest"


@dataclass(frozen=True)
class ResourceKey:
    id: ResourceId
    kind: ResourceKind


@dataclass(frozen=True)
class ResourceRecovery:
    trigger: ResourceRecoveryTrigger
    amount: int | None = None


@dataclass(frozen=True)
class ResourceDefinition:
    key: ResourceKey
    label: str
    recoveries: tuple[ResourceRecovery, ...] = ()


@dataclass(frozen=True)
class ResourceState:
    resource: ResourceId
    current: int
    maximum: int


@dataclass(frozen=True)
class ResourceCost:
    resource: ResourceId
    amount: int = 1


@dataclass(frozen=True)
class ResourceUpdate:
    resource: ResourceId
    label: str
    current: int
    maximum: int


class InsufficientResourceError(ValueError):
    def __init__(self, resource: ResourceId, required: int, available: int) -> None:
        super().__init__(f"{resource.value} requires {required}, but only {available} remain")
        self.resource = resource
        self.required = required
        self.available = available


SPELL_SLOT_RESOURCE_IDS: tuple[ResourceId, ...] = (
    ResourceId.FIRST_LEVEL_SPELL_SLOTS,
    ResourceId.SECOND_LEVEL_SPELL_SLOTS,
    ResourceId.THIRD_LEVEL_SPELL_SLOTS,
    ResourceId.FOURTH_LEVEL_SPELL_SLOTS,
    ResourceId.FIFTH_LEVEL_SPELL_SLOTS,
    ResourceId.SIXTH_LEVEL_SPELL_SLOTS,
    ResourceId.SEVENTH_LEVEL_SPELL_SLOTS,
    ResourceId.EIGHTH_LEVEL_SPELL_SLOTS,
    ResourceId.NINTH_LEVEL_SPELL_SLOTS,
)


def spell_slot_resource_id(level: int) -> ResourceId:
    if level < 1 or level > len(SPELL_SLOT_RESOURCE_IDS):
        raise ValueError(f"Invalid spell slot level: {level}")
    return SPELL_SLOT_RESOURCE_IDS[level - 1]


def spell_slot_level(resource: ResourceId) -> int | None:
    try:
        return SPELL_SLOT_RESOURCE_IDS.index(resource) + 1
    except ValueError:
        return None


def full_recovery(trigger: ResourceRecoveryTrigger) -> ResourceRecovery:
    return ResourceRecovery(trigger)


RESOURCE_DEFINITIONS: Mapping[ResourceId, ResourceDefinition] = {
    **{
        resource: ResourceDefinition(
            ResourceKey(resource, ResourceKind.SPELL_SLOT),
            resource.value,
            (full_recovery(ResourceRecoveryTrigger.LONG_REST),),
        )
        for resource in SPELL_SLOT_RESOURCE_IDS
    },
    ResourceId.SECOND_WIND: ResourceDefinition(
        ResourceKey(ResourceId.SECOND_WIND, ResourceKind.FEATURE_USE),
        ResourceId.SECOND_WIND.value,
        (
            ResourceRecovery(ResourceRecoveryTrigger.SHORT_REST, amount=1),
            full_recovery(ResourceRecoveryTrigger.LONG_REST),
        ),
    ),
    ResourceId.INDOMITABLE: ResourceDefinition(
        ResourceKey(ResourceId.INDOMITABLE, ResourceKind.FEATURE_USE),
        ResourceId.INDOMITABLE.value,
        (full_recovery(ResourceRecoveryTrigger.LONG_REST),),
    ),
    ResourceId.ARROWS: ResourceDefinition(ResourceKey(ResourceId.ARROWS, ResourceKind.AMMUNITION), ResourceId.ARROWS.value),
    ResourceId.BOLTS: ResourceDefinition(ResourceKey(ResourceId.BOLTS, ResourceKind.AMMUNITION), ResourceId.BOLTS.value),
    ResourceId.ACTION: ResourceDefinition(ResourceKey(ResourceId.ACTION, ResourceKind.ACTION), ResourceId.ACTION.value),
    ResourceId.BONUS_ACTION: ResourceDefinition(ResourceKey(ResourceId.BONUS_ACTION, ResourceKind.BONUS_ACTION), ResourceId.BONUS_ACTION.value),
    ResourceId.REACTION: ResourceDefinition(ResourceKey(ResourceId.REACTION, ResourceKind.REACTION), ResourceId.REACTION.value),
}


_SHORT_REST_RESOURCE_IDS = {
    ResourceId.ACTION_SURGE,
    ResourceId.SUPERIORITY_DICE,
    ResourceId.STROKE_OF_LUCK,
    ResourceId.MAGE_SLAYER,
    ResourceId.BOON_OF_COMBAT_PROWESS,
    ResourceId.BOON_OF_DIMENSIONAL_TRAVEL,
    ResourceId.BOON_OF_FATE,
    ResourceId.GROUP_RECOVERY,
    ResourceId.ARCANE_SHOT,
    ResourceId.STEADY_AIM,
    ResourceId.CLOUD_RUNE,
    ResourceId.FIRE_RUNE,
    ResourceId.FROST_RUNE,
    ResourceId.STONE_RUNE,
    ResourceId.HILL_RUNE,
    ResourceId.STORM_RUNE,
    ResourceId.SHADOW_MARTYR,
    ResourceId.PSIONIC_ENERGY_RECOVERY,
    ResourceId.TELEKINETIC_MOVEMENT,
    ResourceId.PSI_POWERED_LEAP,
    ResourceId.VOICE_OF_DEATH,
    ResourceId.ILLUSORY_SELF,
}

_LONG_REST_RESOURCE_IDS = {
    ResourceId.ARCANE_RECOVERY,
    ResourceId.PSI_WARRIOR_PSIONIC_ENERGY_DICE,
    ResourceId.SOULKNIFE_PSIONIC_ENERGY_DICE,
    ResourceId.LUCK_POINTS,
    ResourceId.BOON_OF_RECOVERY,
    ResourceId.MAGIC_INITIATE_FREE_CAST,
    ResourceId.KNOW_YOUR_ENEMY,
    ResourceId.UNWAVERING_MARK,
    ResourceId.WARDING_MANEUVER,
    ResourceId.FIGHTING_SPIRIT,
    ResourceId.STRENGTH_BEFORE_DEATH,
    ResourceId.PROTECTION_FROM_EVIL_AND_GOOD,
    ResourceId.GIANTS_MIGHT,
    ResourceId.RUNIC_SHIELD,
    ResourceId.UNLEASH_INCARNATION,
    ResourceId.RECLAIM_POTENTIAL,
    ResourceId.BULWARK_OF_FORCE,
    ResourceId.TELEKINETIC_MASTER,
    ResourceId.SPELL_THIEF,
    ResourceId.WAILS_FROM_THE_GRAVE,
    ResourceId.SOUL_TRINKETS,
    ResourceId.GHOST_WALK,
    ResourceId.BLOODTHIRST,
    ResourceId.PSYCHIC_VEIL,
    ResourceId.REND_MIND,
    ResourceId.ARCANE_WARD,
    ResourceId.PORTENT,
    ResourceId.GREATER_PORTENT,
    ResourceId.BLADESONG,
}

RESOURCE_DEFINITIONS = {
    **RESOURCE_DEFINITIONS,
    **{
        resource: ResourceDefinition(
            ResourceKey(resource, ResourceKind.FEATURE_USE),
            resource.value,
            (
                full_recovery(ResourceRecoveryTrigger.SHORT_REST),
                full_recovery(ResourceRecoveryTrigger.LONG_REST),
            ),
        )
        for resource in _SHORT_REST_RESOURCE_IDS
    },
    **{
        resource: ResourceDefinition(
            ResourceKey(resource, ResourceKind.FEATURE_USE),
            resource.value,
            (full_recovery(ResourceRecoveryTrigger.LONG_REST),),
        )
        for resource in _LONG_REST_RESOURCE_IDS
    },
}


def spend_resources(states: Sequence[ResourceState], costs: Sequence[ResourceCost]) -> list[ResourceState]:
    required = Counter[ResourceId]()
    for cost in costs:
        if cost.amount < 0:
            raise ValueError("Resource costs cannot be negative")
        required[cost.resource] += cost.amount

    by_id = {state.resource: state for state in states}
    for resource, amount in required.items():
        state = by_id.get(resource)
        available = state.current if state is not None else 0
        if available < amount:
            raise InsufficientResourceError(resource, amount, available)

    return [
        replace(state, current=state.current - required[state.resource])
        for state in states
    ]


def adjust_resource(state: ResourceState, current: int) -> ResourceState:
    return replace(state, current=max(0, min(int(current), state.maximum)))


def recover_resources(
    states: Sequence[ResourceState],
    definitions: Mapping[ResourceId, ResourceDefinition],
    trigger: ResourceRecoveryTrigger,
) -> list[ResourceState]:
    recovered: list[ResourceState] = []
    for state in states:
        definition = definitions.get(state.resource)
        recovery = next((entry for entry in definition.recoveries if entry.trigger == trigger), None) if definition else None
        if recovery is None:
            recovered.append(state)
            continue
        current = state.maximum if recovery.amount is None else min(state.maximum, state.current + recovery.amount)
        recovered.append(replace(state, current=current))
    return recovered


def resource_model_types() -> tuple[type, ...]:
    return (
        ResourceKind,
        ResourceId,
        ResourceRecoveryTrigger,
        ResourceKey,
        ResourceRecovery,
        ResourceDefinition,
        ResourceState,
        ResourceCost,
        ResourceUpdate,
    )
