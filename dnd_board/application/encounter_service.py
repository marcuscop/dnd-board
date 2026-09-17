from __future__ import annotations

import random
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass, replace
from time import time_ns
from typing import Any

from dnd_board.application.room_state import Player, Room
from dnd_board.character_sheet import ActivationTiming, CharacterSheet, RollResolutionMode, TimeEconomy, enum_key
from dnd_board.rules.encounter import (
    ActionCategory,
    ActivationKey,
    ActivationAuthorization,
    EncounterParticipant,
    EncounterState,
    EncounterStatus,
    EncounterTransitionPhase,
    TurnBoundary,
    authorize_activation,
    adjust_participant_resource,
    complete_encounter_transition,
    participant_state_after_turn_start,
    participant_state_at_encounter_start,
    participant_state_with_capacities,
    spend_activation,
    start_encounter_state,
    synchronize_participant_capacities,
    transition_encounter,
)
from dnd_board.rules.shared.character_effects import character_allocation_value
from dnd_board.rules.shared.effects import CalculationType, ResolutionEventType, ongoing_effects_after_turn_boundary
from dnd_board.rules.shared.resources import ResourceId, ResourceRecoveryTrigger, ResourceUpdate


@dataclass(frozen=True)
class EncounterOperations:
    save: Callable[[Room], None]
    broadcast_room: Callable[[Room], Awaitable[None]]
    resolve_turn_boundary: Callable[[Room, CharacterSheet, ResolutionEventType], Awaitable[dict[str, Any]]]
    recover_resources: Callable[[Room, CharacterSheet, ResourceRecoveryTrigger], list[ResourceUpdate]]


class EncounterServiceError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def encounter_to_dict(encounter: EncounterState | None) -> dict[str, Any] | None:
    if encounter is None:
        return None
    return {
        "encounterId": encounter.encounterId,
        "participants": [
            {"participantId": participant.participantId, "initiative": participant.initiative}
            for participant in encounter.participants
        ],
        "currentParticipantId": encounter.currentParticipantId,
        "currentIndex": encounter.currentIndex,
        "round": encounter.round,
        "turnId": encounter.turnId,
        "status": encounter.status.value,
        "transitionBoundary": encounter.transitionBoundary.value if encounter.transitionBoundary is not None else None,
        "transitionPhase": encounter.transitionPhase.value if encounter.transitionPhase is not None else None,
        "participantStates": [
            {
                "participantId": participant.participantId,
                "resources": [
                    {
                        "resource": enum_key(resource.resource),
                        "current": resource.current,
                        "maximum": resource.maximum,
                    }
                    for resource in participant.resources
                ],
                "allowances": [
                    {
                        "resource": enum_key(allowance.resource),
                        "amount": allowance.amount,
                        "sourceResource": enum_key(allowance.source.resource),
                        "sourceGrantIndex": allowance.source.grantIndex,
                        "allowedCategories": [category.value for category in allowance.allowedCategories],
                        "expires": allowance.expires.value,
                    }
                    for allowance in participant.allowances
                ],
                "activeActions": [
                    {
                        "key": {
                            "kind": action.key.kind.value,
                            "sourceId": action.key.sourceId,
                            "optionId": action.key.optionId,
                        },
                        "category": action.category.value,
                        "remainingParts": action.remainingParts,
                    }
                    for action in participant.activeActions
                ],
                "interactionUsages": [
                    {
                        "resource": enum_key(usage.resource),
                        "scope": usage.scope.value,
                        "turnId": usage.turnId,
                        "round": usage.round,
                    }
                    for usage in participant.interactionUsages
                ],
            }
            for participant in encounter.participantStates
        ],
    }


def roll_initiatives(
    participant_ids: Iterable[str],
    sheets: Iterable[CharacterSheet],
) -> list[dict[str, int | str]]:
    sheets_by_id = {sheet.id: sheet for sheet in sheets}
    results: list[dict[str, int | str]] = []
    for participant_id in participant_ids:
        sheet = sheets_by_id.get(participant_id)
        if sheet is None:
            raise EncounterServiceError(404, f"Participant not found: {participant_id}")
        die = random.randint(1, 20)
        results.append(
            {
                "participantId": participant_id,
                "die": die,
                "modifier": sheet.initiativeBonus,
                "total": die + sheet.initiativeBonus,
            }
        )
    return results


async def start_encounter(
    room: Room,
    player: Player,
    participants: Iterable[EncounterParticipant],
    sheets: Iterable[CharacterSheet],
    operations: EncounterOperations,
) -> EncounterState:
    _require_dm(player)
    ordered = tuple(participants)
    sheets_by_id = {sheet.id: sheet for sheet in sheets}
    valid_participant_ids = set(sheets_by_id)
    if any(participant.participantId not in valid_participant_ids for participant in ordered):
        raise EncounterServiceError(400, "Encounter contains an unknown participant")
    try:
        encounter = start_encounter_state(_new_id("encounter"), _new_id("turn"), ordered)
    except ValueError as error:
        raise EncounterServiceError(400, str(error)) from error
    room.encounter = replace(
        encounter,
        status=EncounterStatus.TRANSITIONING,
        transitionBoundary=TurnBoundary.START,
        transitionPhase=EncounterTransitionPhase.START_EFFECTS,
    )
    room.encounter = _synchronize_sheet_capacities(room.encounter, sheets_by_id.values())
    room.encounter = replace(
        room.encounter,
        participantStates=tuple(
            participant_state_at_encounter_start(
                participant,
                current=participant.participantId == room.encounter.currentParticipantId,
            )
            for participant in room.encounter.participantStates
        ),
    )
    operations.save(room)
    await operations.broadcast_room(room)
    return await resume_turn_transition(room, sheets_by_id.values(), operations)


async def update_encounter_order(
    room: Room,
    player: Player,
    participants: Iterable[EncounterParticipant],
    sheets: Iterable[CharacterSheet],
    operations: EncounterOperations,
) -> EncounterState:
    _require_dm(player)
    if room.encounter is None:
        raise EncounterServiceError(409, "No encounter is active")
    if room.encounter.status != EncounterStatus.ACTIVE:
        raise EncounterServiceError(409, "Finish changing turns before editing the encounter")
    ordered = tuple(participants)
    sheets_by_id = {sheet.id: sheet for sheet in sheets}
    valid_participant_ids = set(sheets_by_id)
    ids = [participant.participantId for participant in ordered]
    if not ids or len(ids) != len(set(ids)) or any(value not in valid_participant_ids for value in ids):
        raise EncounterServiceError(400, "Encounter participants are invalid")
    current_id = room.encounter.currentParticipantId
    current_index = (
        ids.index(current_id)
        if current_id in ids
        else room.encounter.currentIndex % len(ids)
    )
    previous_states = {entry.participantId: entry for entry in room.encounter.participantStates}
    rebuilt = start_encounter_state(room.encounter.encounterId, room.encounter.turnId, ordered)
    rebuilt = _synchronize_sheet_capacities(rebuilt, sheets_by_id.values())
    current_was_removed = current_id not in ids
    states = []
    for entry in rebuilt.participantStates:
        previous = previous_states.get(entry.participantId)
        if previous is not None:
            previous = participant_state_with_capacities(
                previous,
                _sheet_capacities(
                    sheets_by_id[entry.participantId], sheets_by_id.values()
                ),
            )
            states.append(
                participant_state_after_turn_start(
                    previous,
                    round_number=room.encounter.round,
                )
                if current_was_removed and entry.participantId == ids[current_index]
                else previous
            )
        elif entry.participantId == ids[current_index]:
            states.append(participant_state_at_encounter_start(entry, current=True))
        else:
            states.append(participant_state_at_encounter_start(entry, current=False))
    room.encounter = replace(
        rebuilt,
        currentIndex=current_index,
        round=room.encounter.round,
        participantStates=tuple(states),
        status=(
            EncounterStatus.TRANSITIONING
            if current_was_removed
            else room.encounter.status
        ),
        transitionBoundary=TurnBoundary.START if current_was_removed else None,
        transitionPhase=(
            EncounterTransitionPhase.START_EFFECTS
            if current_was_removed
            else None
        ),
        turnId=_new_id("turn") if current_was_removed else room.encounter.turnId,
    )
    operations.save(room)
    await operations.broadcast_room(room)
    if current_was_removed:
        return await resume_turn_transition(room, sheets_by_id.values(), operations)
    return room.encounter


async def advance_turn(
    room: Room,
    player: Player,
    turn_id: str,
    sheets: Iterable[CharacterSheet],
    operations: EncounterOperations,
) -> EncounterState:
    encounter = room.encounter
    if encounter is None:
        raise EncounterServiceError(409, "No encounter is active")
    if encounter.turnId != turn_id:
        raise EncounterServiceError(409, "That turn has already ended")
    sheets_by_id = {sheet.id: sheet for sheet in sheets}
    current = sheets_by_id.get(encounter.currentParticipantId)
    if player.player_key != "dm" and (current is None or current.owner != player.player_key):
        raise EncounterServiceError(403, "Only the current character's owner or the DM can end this turn")
    unresolved_rolls = any(
        roll.resolution != RollResolutionMode.NONE or roll.pendingEffect is not None
        for roll in room.pending_rolls.values()
    )
    if room.pending_resolution_prompts or room.pending_effect_executions or unresolved_rolls:
        raise EncounterServiceError(409, "Finish the pending resolution before ending the turn")

    room.encounter = replace(
        encounter,
        status=EncounterStatus.TRANSITIONING,
        transitionBoundary=TurnBoundary.END,
        transitionPhase=EncounterTransitionPhase.END_EFFECTS,
    )
    operations.save(room)
    await operations.broadcast_room(room)
    return await resume_turn_transition(room, sheets_by_id.values(), operations)


async def resume_turn_transition(
    room: Room,
    sheets: Iterable[CharacterSheet],
    operations: EncounterOperations,
) -> EncounterState:
    encounter = room.encounter
    if encounter is None or encounter.status != EncounterStatus.TRANSITIONING:
        if encounter is None:
            raise EncounterServiceError(409, "No encounter is active")
        return encounter
    if room.pending_resolution_prompts or room.pending_effect_executions:
        return encounter
    sheets_by_id = {sheet.id: sheet for sheet in sheets}

    if encounter.transitionPhase == EncounterTransitionPhase.END_EFFECTS:
        room.encounter = replace(encounter, transitionPhase=EncounterTransitionPhase.ADVANCE)
        operations.save(room)
        participant = sheets_by_id.get(encounter.currentParticipantId)
        if participant is not None:
            operations.recover_resources(room, participant, ResourceRecoveryTrigger.TURN_ENDED)
            result = await operations.resolve_turn_boundary(room, participant, ResolutionEventType.TURN_ENDED)
            if "prompt" in result:
                return room.encounter
        encounter = room.encounter

    if encounter is not None and encounter.transitionPhase == EncounterTransitionPhase.ADVANCE:
        _reconcile_turn_durations(room, encounter.currentParticipantId, TurnBoundary.END)
        encounter = _synchronize_sheet_capacities(encounter, sheets_by_id.values())
        room.encounter = transition_encounter(encounter, _new_id("turn"))
        operations.save(room)
        await operations.broadcast_room(room)
        encounter = room.encounter

    if encounter is not None and encounter.transitionPhase == EncounterTransitionPhase.START_EFFECTS:
        room.encounter = replace(encounter, transitionPhase=EncounterTransitionPhase.COMPLETE)
        operations.save(room)
        participant = sheets_by_id.get(encounter.currentParticipantId)
        if participant is not None:
            operations.recover_resources(room, participant, ResourceRecoveryTrigger.TURN_STARTED)
            result = await operations.resolve_turn_boundary(room, participant, ResolutionEventType.TURN_STARTED)
            if "prompt" in result:
                return room.encounter
        encounter = room.encounter

    if encounter is not None and encounter.transitionPhase == EncounterTransitionPhase.COMPLETE:
        _reconcile_turn_durations(room, encounter.currentParticipantId, TurnBoundary.START)
        room.encounter = complete_encounter_transition(encounter)
        operations.save(room)
        await operations.broadcast_room(room)
    return room.encounter


async def end_encounter(
    room: Room,
    player: Player,
    operations: EncounterOperations,
) -> None:
    _require_dm(player)
    if room.encounter is None:
        raise EncounterServiceError(409, "No encounter is active")
    if room.pending_resolution_prompts or room.pending_effect_executions:
        raise EncounterServiceError(409, "Finish the pending resolution before ending the encounter")
    room.encounter = None
    operations.save(room)
    await operations.broadcast_room(room)


async def adjust_encounter_resource(
    room: Room,
    player: Player,
    participant_id: str,
    resource_id: ResourceId,
    current: int,
    operations: EncounterOperations,
) -> EncounterState:
    _require_dm(player)
    if room.encounter is None:
        raise EncounterServiceError(409, "No encounter is active")
    try:
        room.encounter = adjust_participant_resource(
            room.encounter, participant_id, resource_id, current
        )
    except ValueError as error:
        raise EncounterServiceError(400, str(error)) from error
    operations.save(room)
    await operations.broadcast_room(room)
    return room.encounter


def authorize_action(
    room: Room,
    participant_id: str,
    activation: TimeEconomy | None,
    category: ActionCategory,
    turn_id: str | None = None,
    *,
    timing: ActivationTiming = ActivationTiming.UNRESTRICTED,
    activation_key: ActivationKey | None = None,
    part_id: int | None = None,
    resolution_response: bool = False,
    sheet: CharacterSheet | None = None,
    participant_sheets: Iterable[CharacterSheet] = (),
) -> ActivationAuthorization:
    if room.encounter is not None and not any(
        participant.participantId == participant_id
        for participant in room.encounter.participants
    ):
        return ActivationAuthorization(False, "This character is not participating in the encounter")
    if room.encounter is not None and sheet is not None:
        room.encounter = synchronize_participant_capacities(
            room.encounter,
            participant_id,
            _sheet_capacities(sheet, participant_sheets),
        )
    if room.encounter is not None:
        if turn_id is None:
            return ActivationAuthorization(False, "Refresh the sheet before acting in this encounter")
        if room.encounter.turnId != turn_id:
            return ActivationAuthorization(False, "That turn has already ended")
    return authorize_activation(
        room.encounter,
        participant_id,
        activation,
        category,
        timing=timing,
        activation_key=activation_key,
        part_id=part_id,
        resolution_response=resolution_response,
    )


def commit_action_authorization(
    room: Room,
    participant_id: str,
    authorization: ActivationAuthorization,
    activation_instances: int = 1,
    activation_key: ActivationKey | None = None,
    part_id: int | None = None,
) -> None:
    if room.encounter is None or (
        authorization.resource is None and authorization.activeAction is None
    ):
        return
    room.encounter = spend_activation(
        room.encounter,
        participant_id,
        authorization,
        activation_instances,
        activation_key,
        part_id,
    )


def _require_dm(player: Player) -> None:
    if player.player_key != "dm":
        raise EncounterServiceError(403, "Only the DM can manage encounters")


def _new_id(prefix: str) -> str:
    return f"{prefix}-{time_ns()}"


def _reconcile_turn_durations(
    room: Room,
    participant_id: str,
    boundary: TurnBoundary,
) -> None:
    for target_id, effects in list(room.ongoing_effects.items()):
        remaining = ongoing_effects_after_turn_boundary(
            effects,
            participant_id,
            boundary,
            room.encounter.turnId if room.encounter is not None else None,
        )
        if remaining:
            room.ongoing_effects[target_id] = remaining
        else:
            room.ongoing_effects.pop(target_id, None)


def _sheet_capacities(
    sheet: CharacterSheet,
    participant_sheets: Iterable[CharacterSheet] = (),
) -> dict[ResourceId, int]:
    return {
        ResourceId.ACTION: character_allocation_value(
            sheet,
            CalculationType.ACTION_CAPACITY,
            participant_sheets=participant_sheets,
        ),
        ResourceId.BONUS_ACTION: character_allocation_value(
            sheet,
            CalculationType.BONUS_ACTION_CAPACITY,
            participant_sheets=participant_sheets,
        ),
        ResourceId.REACTION: character_allocation_value(
            sheet,
            CalculationType.REACTION_CAPACITY,
            participant_sheets=participant_sheets,
        ),
    }


def _synchronize_sheet_capacities(
    encounter: EncounterState,
    sheets: Iterable[CharacterSheet],
) -> EncounterState:
    all_sheets = tuple(sheets)
    for sheet in all_sheets:
        if sheet.id in {participant.participantId for participant in encounter.participants}:
            encounter = synchronize_participant_capacities(
                encounter,
                sheet.id,
                _sheet_capacities(sheet, all_sheets),
            )
    return encounter
