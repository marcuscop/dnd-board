import pytest

from dnd_board.character_sheet import ResourceTracker, TimeEconomy
from dnd_board.rules.shared.resources import (
    RESOURCE_DEFINITIONS,
    InsufficientResourceError,
    ResourceCost,
    ResourceDefinition,
    ResourceId,
    ResourceKey,
    ResourceRecoveryTrigger,
    ResourceState,
    adjust_resource,
    recover_resources,
    spell_slot_resource_id,
    spend_resources,
)


def test_resource_costs_are_validated_and_spent_atomically() -> None:
    states = [
        ResourceState(ResourceId.SECOND_WIND, 2, 2),
        ResourceState(ResourceId.REACTION, 1, 1),
    ]

    spent = spend_resources(
        states,
        (ResourceCost(ResourceId.SECOND_WIND), ResourceCost(ResourceId.REACTION)),
    )

    assert spent == [
        ResourceState(ResourceId.SECOND_WIND, 1, 2),
        ResourceState(ResourceId.REACTION, 0, 1),
    ]
    with pytest.raises(InsufficientResourceError):
        spend_resources(states, (ResourceCost(ResourceId.SECOND_WIND), ResourceCost(ResourceId.REACTION, 2)))
    assert states == [
        ResourceState(ResourceId.SECOND_WIND, 2, 2),
        ResourceState(ResourceId.REACTION, 1, 1),
    ]


def test_resource_adjustment_and_recovery_stay_within_capacity() -> None:
    second_wind = ResourceState(ResourceId.SECOND_WIND, 0, 3)
    spell_slot = ResourceState(ResourceId.FIRST_LEVEL_SPELL_SLOTS, 0, 4)

    assert adjust_resource(second_wind, -2).current == 0
    assert adjust_resource(second_wind, 8).current == 3
    assert recover_resources(
        [second_wind, spell_slot],
        RESOURCE_DEFINITIONS,
        ResourceRecoveryTrigger.SHORT_REST,
    ) == [ResourceState(ResourceId.SECOND_WIND, 1, 3), spell_slot]
    assert recover_resources(
        [second_wind, spell_slot],
        RESOURCE_DEFINITIONS,
        ResourceRecoveryTrigger.LONG_REST,
    ) == [
        ResourceState(ResourceId.SECOND_WIND, 3, 3),
        ResourceState(ResourceId.FIRST_LEVEL_SPELL_SLOTS, 4, 4),
    ]


def test_spell_slot_resource_ids_are_typed_by_level() -> None:
    assert spell_slot_resource_id(1) == ResourceId.FIRST_LEVEL_SPELL_SLOTS
    assert spell_slot_resource_id(9) == ResourceId.NINTH_LEVEL_SPELL_SLOTS
    with pytest.raises(ValueError):
        spell_slot_resource_id(0)


def test_every_stateful_resource_has_a_definition() -> None:
    assert set(RESOURCE_DEFINITIONS) == set(ResourceId) - {ResourceId.SPELL_SLOT}


def test_short_rest_resources_also_recover_on_a_long_rest() -> None:
    action_surge = ResourceState(ResourceId.ACTION_SURGE, 0, 2)

    assert recover_resources(
        [action_surge],
        RESOURCE_DEFINITIONS,
        ResourceRecoveryTrigger.SHORT_REST,
    ) == [ResourceState(ResourceId.ACTION_SURGE, 2, 2)]
    assert recover_resources(
        [action_surge],
        RESOURCE_DEFINITIONS,
        ResourceRecoveryTrigger.LONG_REST,
    ) == [ResourceState(ResourceId.ACTION_SURGE, 2, 2)]


def test_tracker_distinguishes_default_from_explicitly_empty_recovery() -> None:
    inherited = ResourceTracker(
        "inherited",
        "Inherited",
        0,
        1,
        TimeEconomy.SPECIAL,
        "Uses the shared definition.",
        ResourceId.ACTION_SURGE,
    )
    never_recovers = ResourceTracker(
        "manual",
        "Manual",
        0,
        1,
        TimeEconomy.SPECIAL,
        "Manual recovery only.",
        ResourceId.ACTION_SURGE,
        recoveries=(),
    )

    assert inherited.recoveries == RESOURCE_DEFINITIONS[ResourceId.ACTION_SURGE].recoveries
    assert never_recovers.recoveries == ()
    manual_definition = ResourceDefinition(
        ResourceKey(never_recovers.resource, never_recovers.kind),
        never_recovers.name,
        never_recovers.recoveries,
    )
    empty_state = ResourceState(ResourceId.ACTION_SURGE, 0, 1)
    assert recover_resources(
        [empty_state],
        {ResourceId.ACTION_SURGE: manual_definition},
        ResourceRecoveryTrigger.SHORT_REST,
    ) == [empty_state]
    assert recover_resources(
        [empty_state],
        {ResourceId.ACTION_SURGE: manual_definition},
        ResourceRecoveryTrigger.LONG_REST,
    ) == [empty_state]
