from __future__ import annotations

from dnd_board.application.room_state import Room
from dnd_board.character_sheet import CharacterSheet, RestType
from dnd_board.rules.shared.resources import (
    RESOURCE_DEFINITIONS,
    ResourceCost,
    ResourceDefinition,
    ResourceId,
    ResourceKey,
    ResourceRecoveryTrigger,
    ResourceState,
    ResourceUpdate,
    recover_resources,
    spell_slot_resource_id,
    spend_resources,
)


def resolved_resource_costs(
    costs: tuple[ResourceCost, ...],
    spell_slot_level: int | None = None,
) -> tuple[ResourceCost, ...]:
    return tuple(
        ResourceCost(spell_slot_resource_id(spell_slot_level), cost.amount)
        if cost.resource == ResourceId.SPELL_SLOT and spell_slot_level is not None
        else cost
        for cost in costs
    )


def spend_sheet_resources(
    room: Room,
    sheet: CharacterSheet,
    costs: tuple[ResourceCost, ...],
    spell_slot_level: int | None = None,
) -> list[ResourceUpdate]:
    resolved_costs = resolved_resource_costs(costs, spell_slot_level)
    if not resolved_costs:
        return []
    if any(cost.resource == ResourceId.SPELL_SLOT for cost in resolved_costs):
        raise ValueError("A spell-slot cost requires a selected slot level")

    resources_by_id = {resource.resource: resource for resource in sheet.resources}
    states = [
        ResourceState(resource_id, resource.currentUses, resource.maxUses)
        for resource_id, resource in resources_by_id.items()
    ]
    updated_states = spend_resources(states, resolved_costs)
    previous_by_id = {state.resource: state for state in states}
    updates: list[ResourceUpdate] = []
    for state in updated_states:
        previous = previous_by_id[state.resource]
        if state.current == previous.current:
            continue
        tracker = resources_by_id[state.resource]
        room.resource_uses.setdefault(sheet.tokenId, {})[tracker.id] = state.current
        updates.append(ResourceUpdate(state.resource, tracker.name, state.current, state.maximum))
    return updates


def reset_sheet_resources(
    room: Room,
    sheet: CharacterSheet,
    rest_type: RestType,
) -> list[ResourceUpdate]:
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
