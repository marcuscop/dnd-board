from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from typing import Iterable

from dnd_board.character_sheet import ActivationTiming, TimeEconomy
from dnd_board.rules.shared.resources import (
    RESOURCE_DEFINITIONS,
    ResourceId,
    ResourceRecoveryTrigger,
    ResourceState,
    recover_resources,
)


class EncounterStatus(Enum):
    ACTIVE = "active"
    TRANSITIONING = "transitioning"


class TurnBoundary(Enum):
    START = "start"
    END = "end"


class EncounterTransitionPhase(Enum):
    END_EFFECTS = "endEffects"
    ADVANCE = "advance"
    START_EFFECTS = "startEffects"
    COMPLETE = "complete"


class TurnParticipantReference(Enum):
    SOURCE = "source"
    OWNER = "owner"
    TARGET = "target"


class TurnOccurrence(Enum):
    THIS = "this"
    NEXT = "next"
    AFTER_COUNT = "afterCount"


class UsageScope(Enum):
    ONCE_ON_OWN_TURN = "onceOnOwnTurn"
    ONCE_ON_ANY_TURN = "onceOnAnyTurn"
    ONCE_PER_ROUND = "oncePerRound"
    UNTIL_NEXT_TURN = "untilNextTurn"


class ActionCategory(Enum):
    ATTACK = "attack"
    MAGIC = "magic"
    FEATURE = "feature"
    ITEM = "item"
    OTHER = "other"


class ActivationKind(Enum):
    ATTACK_ACTION = "attackAction"
    SPELL = "spell"
    FEATURE = "feature"
    ITEM = "item"


@dataclass(frozen=True)
class ActivationKey:
    kind: ActivationKind
    sourceId: str
    optionId: str = ""


class AllowanceExpiration(Enum):
    TURN_START = "turnStart"
    TURN_END = "turnEnd"
    ROUND_END = "roundEnd"
    ENCOUNTER_END = "encounterEnd"


@dataclass(frozen=True)
class TurnTiming:
    participant: TurnParticipantReference
    boundary: TurnBoundary
    occurrence: TurnOccurrence = TurnOccurrence.NEXT
    count: int = 1

    def __post_init__(self) -> None:
        if self.count < 1:
            raise ValueError("Turn timing count must be positive")


@dataclass(frozen=True)
class AllowanceSource:
    resource: ResourceId
    grantIndex: int = 0


@dataclass(frozen=True)
class ActionAllowance:
    resource: ResourceId
    amount: int
    source: AllowanceSource
    allowedCategories: tuple[ActionCategory, ...] = ()
    expires: AllowanceExpiration = AllowanceExpiration.TURN_END

    def __post_init__(self) -> None:
        if self.amount < 1:
            raise ValueError("An action allowance must grant at least one use")


@dataclass(frozen=True)
class ActiveActionActivation:
    key: ActivationKey
    category: ActionCategory
    remainingPartIds: tuple[int, ...]

    def __post_init__(self) -> None:
        if not self.remainingPartIds:
            raise ValueError("An active action must have a remaining part")

    @property
    def remainingParts(self) -> int:
        return len(self.remainingPartIds)


@dataclass(frozen=True)
class InteractionUsage:
    resource: ResourceId
    scope: UsageScope
    turnId: str
    round: int


@dataclass(frozen=True)
class EncounterParticipant:
    participantId: str
    initiative: int


@dataclass(frozen=True)
class EncounterParticipantState:
    participantId: str
    resources: tuple[ResourceState, ...]
    allowances: tuple[ActionAllowance, ...] = ()
    activeActions: tuple[ActiveActionActivation, ...] = ()
    interactionUsages: tuple[InteractionUsage, ...] = ()


@dataclass(frozen=True)
class EncounterState:
    encounterId: str
    participants: tuple[EncounterParticipant, ...]
    currentIndex: int
    round: int
    turnId: str
    status: EncounterStatus = EncounterStatus.ACTIVE
    participantStates: tuple[EncounterParticipantState, ...] = ()
    transitionBoundary: TurnBoundary | None = None
    transitionPhase: EncounterTransitionPhase | None = None

    def __post_init__(self) -> None:
        if not self.participants:
            raise ValueError("An encounter requires at least one participant")
        ids = [participant.participantId for participant in self.participants]
        if len(ids) != len(set(ids)):
            raise ValueError("Encounter participants must be unique")
        if self.currentIndex < 0 or self.currentIndex >= len(self.participants):
            raise ValueError("Encounter current participant is out of range")
        if self.round < 1:
            raise ValueError("Encounter round must be positive")

    @property
    def currentParticipantId(self) -> str:
        return self.participants[self.currentIndex].participantId


@dataclass(frozen=True)
class ActivationAuthorization:
    allowed: bool
    reason: str | None = None
    resource: ResourceId | None = None
    allowance: ActionAllowance | None = None
    activeAction: ActiveActionActivation | None = None
    category: ActionCategory | None = None
    partId: int | None = None


def action_resource(activation: TimeEconomy | None) -> ResourceId | None:
    return {
        TimeEconomy.ACTION: ResourceId.ACTION,
        TimeEconomy.BONUS_ACTION: ResourceId.BONUS_ACTION,
        TimeEconomy.REACTION: ResourceId.REACTION,
    }.get(activation)


def initial_participant_state(participant_id: str, *, current: bool) -> EncounterParticipantState:
    return EncounterParticipantState(
        participantId=participant_id,
        resources=(
            ResourceState(ResourceId.ACTION, 1 if current else 0, 1),
            ResourceState(ResourceId.BONUS_ACTION, 1 if current else 0, 1),
            ResourceState(ResourceId.REACTION, 1, 1),
        ),
    )


def start_encounter_state(
    encounter_id: str,
    turn_id: str,
    participants: Iterable[EncounterParticipant],
) -> EncounterState:
    ordered = tuple(participants)
    return EncounterState(
        encounterId=encounter_id,
        participants=ordered,
        currentIndex=0,
        round=1,
        turnId=turn_id,
        participantStates=tuple(
            initial_participant_state(participant.participantId, current=index == 0)
            for index, participant in enumerate(ordered)
        ),
    )


def authorize_activation(
    encounter: EncounterState | None,
    participant_id: str,
    activation: TimeEconomy | None,
    category: ActionCategory,
    *,
    timing: ActivationTiming = ActivationTiming.UNRESTRICTED,
    activation_key: ActivationKey | None = None,
    part_id: int | None = None,
    resolution_response: bool = False,
) -> ActivationAuthorization:
    resource_id = action_resource(activation)
    if encounter is None:
        return ActivationAuthorization(True, category=category)
    if encounter.status != EncounterStatus.ACTIVE and not resolution_response:
        return ActivationAuthorization(False, "The encounter is changing turns")
    if participant_id not in {entry.participantId for entry in encounter.participants}:
        return ActivationAuthorization(False, "This character is not participating in the encounter")
    own_turn_required = timing == ActivationTiming.OWN_TURN or resource_id in {
        ResourceId.ACTION,
        ResourceId.BONUS_ACTION,
    }
    if own_turn_required and encounter.currentParticipantId != participant_id:
        return ActivationAuthorization(False, "It is not this character's turn")

    if resource_id is None:
        return ActivationAuthorization(True, category=category)

    participant = participant_state(encounter, participant_id)
    active_action = next(
        (
            entry for entry in participant.activeActions
            if (
                activation_key is not None
                and entry.key == activation_key
                and (part_id is None or part_id in entry.remainingPartIds)
            )
        ),
        None,
    )
    if resource_id == ResourceId.ACTION and active_action is not None:
        return ActivationAuthorization(
            True,
            activeAction=active_action,
            category=category,
            partId=part_id,
        )
    state = next((entry for entry in participant.resources if entry.resource == resource_id), None)
    if state is not None and state.current > 0:
        return ActivationAuthorization(True, resource=resource_id, category=category)
    allowance = next(
        (
            entry
            for entry in participant.allowances
            if entry.resource == resource_id
            and entry.amount > 0
            and (not entry.allowedCategories or category in entry.allowedCategories)
        ),
        None,
    )
    if allowance is not None:
        return ActivationAuthorization(True, resource=resource_id, allowance=allowance, category=category)
    return ActivationAuthorization(False, f"No {resource_id.value} remains")


def spend_activation(
    encounter: EncounterState,
    participant_id: str,
    authorization: ActivationAuthorization,
    activation_instances: int = 1,
    activation_key: ActivationKey | None = None,
    part_id: int | None = None,
) -> EncounterState:
    if not authorization.allowed:
        return encounter
    participant = participant_state(encounter, participant_id)
    active_actions = participant.activeActions
    if authorization.activeAction is not None:
        consumed_part = (
            authorization.partId
            if authorization.partId is not None
            else authorization.activeAction.remainingPartIds[0]
        )
        active_actions = tuple(
            replace(
                entry,
                remainingPartIds=tuple(
                    value for value in entry.remainingPartIds if value != consumed_part
                ),
            )
            for entry in active_actions
            if entry == authorization.activeAction and entry.remainingParts > 1
        ) + tuple(entry for entry in active_actions if entry != authorization.activeAction)
        return replace_participant_state(encounter, replace(participant, activeActions=active_actions))
    if authorization.resource is None:
        return encounter
    if authorization.allowance is not None:
        allowances = tuple(
            replace(entry, amount=entry.amount - 1)
            for entry in participant.allowances
            if entry == authorization.allowance and entry.amount > 1
        ) + tuple(
            entry
            for entry in participant.allowances
            if entry != authorization.allowance
        )
        updated = replace(participant, allowances=allowances)
    else:
        updated = replace(
            participant,
            resources=tuple(
                replace(entry, current=entry.current - 1)
                if entry.resource == authorization.resource
                else entry
                for entry in participant.resources
            ),
        )
    if authorization.resource == ResourceId.ACTION and activation_instances > 1:
        if activation_key is None:
            raise ValueError("Multipart actions require an activation key")
        updated = replace(
            updated,
            activeActions=(*updated.activeActions, ActiveActionActivation(
                key=activation_key,
                category=authorization.category or ActionCategory.OTHER,
                remainingPartIds=tuple(
                    index
                    for index in range(activation_instances)
                    if index != (part_id if part_id is not None else 0)
                ),
            )),
        )
    return replace_participant_state(encounter, updated)


def transition_encounter(encounter: EncounterState, turn_id: str) -> EncounterState:
    outgoing_id = encounter.currentParticipantId
    next_index = (encounter.currentIndex + 1) % len(encounter.participants)
    next_round = encounter.round + 1 if next_index == 0 else encounter.round
    incoming_id = encounter.participants[next_index].participantId
    states: list[EncounterParticipantState] = []
    for participant in encounter.participantStates:
        if participant.participantId == outgoing_id:
            participant = participant_state_after_turn_end(
                participant,
                round_ended=next_round != encounter.round,
            )
        elif next_round != encounter.round:
            participant = replace(
                participant,
                allowances=tuple(
                    allowance
                    for allowance in participant.allowances
                    if allowance.expires != AllowanceExpiration.ROUND_END
                ),
            )
        if participant.participantId == incoming_id:
            participant = participant_state_after_turn_start(
                participant,
                round_number=next_round,
            )
        states.append(participant)
    return replace(
        encounter,
        currentIndex=next_index,
        round=next_round,
        turnId=turn_id,
        status=EncounterStatus.TRANSITIONING,
        participantStates=tuple(states),
        transitionBoundary=TurnBoundary.START,
        transitionPhase=EncounterTransitionPhase.START_EFFECTS,
    )


def participant_state_after_turn_end(
    participant: EncounterParticipantState,
    *,
    round_ended: bool,
) -> EncounterParticipantState:
    return replace(
        participant,
        resources=tuple(
            replace(entry, current=0)
            if entry.resource in {ResourceId.ACTION, ResourceId.BONUS_ACTION}
            else entry
            for entry in participant.resources
        ),
        allowances=tuple(
            entry
            for entry in participant.allowances
            if entry.expires != AllowanceExpiration.TURN_END
            and not (round_ended and entry.expires == AllowanceExpiration.ROUND_END)
        ),
        activeActions=(),
    )


def participant_state_after_turn_start(
    participant: EncounterParticipantState,
    *,
    round_number: int,
) -> EncounterParticipantState:
    return replace(
        participant,
        resources=tuple(recover_resources(
            participant.resources,
            RESOURCE_DEFINITIONS,
            ResourceRecoveryTrigger.TURN_STARTED,
        )),
        allowances=tuple(
            entry
            for entry in participant.allowances
            if entry.expires != AllowanceExpiration.TURN_START
        ),
        activeActions=(),
        interactionUsages=tuple(
            usage
            for usage in participant.interactionUsages
            if usage.scope == UsageScope.ONCE_PER_ROUND and usage.round == round_number
        ),
    )


def participant_state_at_encounter_start(
    participant: EncounterParticipantState,
    *,
    current: bool,
) -> EncounterParticipantState:
    return replace(
        participant,
        resources=tuple(
            replace(
                resource,
                current=(
                    resource.maximum
                    if resource.resource == ResourceId.REACTION
                    or (
                        current
                        and resource.resource in {
                            ResourceId.ACTION,
                            ResourceId.BONUS_ACTION,
                        }
                    )
                    else 0
                ),
            )
            for resource in participant.resources
        ),
    )


def complete_encounter_transition(encounter: EncounterState) -> EncounterState:
    return replace(
        encounter,
        status=EncounterStatus.ACTIVE,
        transitionBoundary=None,
        transitionPhase=None,
    )


def grant_action_allowance(
    encounter: EncounterState,
    participant_id: str,
    allowance: ActionAllowance,
) -> EncounterState:
    participant = participant_state(encounter, participant_id)
    matching = next(
        (entry for entry in participant.allowances if entry.source == allowance.source),
        None,
    )
    allowances = tuple(entry for entry in participant.allowances if entry.source != allowance.source)
    granted = replace(
        allowance,
        amount=allowance.amount + (matching.amount if matching is not None else 0),
    )
    return replace_participant_state(encounter, replace(participant, allowances=(*allowances, granted)))


def participant_state(encounter: EncounterState, participant_id: str) -> EncounterParticipantState:
    participant = next(
        (entry for entry in encounter.participantStates if entry.participantId == participant_id),
        None,
    )
    if participant is None:
        raise ValueError("Encounter participant state is missing")
    return participant


def replace_participant_state(
    encounter: EncounterState,
    participant: EncounterParticipantState,
) -> EncounterState:
    return replace(
        encounter,
        participantStates=tuple(
            participant if entry.participantId == participant.participantId else entry
            for entry in encounter.participantStates
        ),
    )


def adjust_participant_resource(
    encounter: EncounterState,
    participant_id: str,
    resource_id: ResourceId,
    current: int,
) -> EncounterState:
    if resource_id not in {
        ResourceId.ACTION,
        ResourceId.BONUS_ACTION,
        ResourceId.REACTION,
    }:
        raise ValueError("Only encounter action resources can be adjusted")
    participant = participant_state(encounter, participant_id)
    resource = next(
        (entry for entry in participant.resources if entry.resource == resource_id),
        None,
    )
    if resource is None:
        raise ValueError("Encounter resource is missing")
    adjusted = replace(resource, current=max(0, min(current, resource.maximum)))
    return replace_participant_state(
        encounter,
        replace(
            participant,
            resources=tuple(
                adjusted if entry.resource == resource_id else entry
                for entry in participant.resources
            ),
        ),
    )


def synchronize_participant_capacities(
    encounter: EncounterState,
    participant_id: str,
    capacities: dict[ResourceId, int],
) -> EncounterState:
    participant = participant_state(encounter, participant_id)
    updated = participant_state_with_capacities(participant, capacities)
    return replace_participant_state(encounter, updated)


def participant_state_with_capacities(
    participant: EncounterParticipantState,
    capacities: dict[ResourceId, int],
) -> EncounterParticipantState:
    resources = tuple(
        replace(
            resource,
            current=min(resource.current, capacities.get(resource.resource, resource.maximum)),
            maximum=capacities.get(resource.resource, resource.maximum),
        )
        for resource in participant.resources
    )
    return replace(participant, resources=resources)


def interaction_usage_allowed(
    encounter: EncounterState | None,
    participant_id: str,
    resource_id: ResourceId | None,
    scope: UsageScope | None,
) -> bool:
    if encounter is None or scope is None or resource_id is None:
        return True
    participant = participant_state(encounter, participant_id)
    matching = [entry for entry in participant.interactionUsages if entry.resource == resource_id]
    if scope == UsageScope.ONCE_ON_OWN_TURN and encounter.currentParticipantId != participant_id:
        return False
    if scope in {UsageScope.ONCE_ON_OWN_TURN, UsageScope.ONCE_ON_ANY_TURN}:
        return not any(entry.turnId == encounter.turnId for entry in matching)
    if scope == UsageScope.ONCE_PER_ROUND:
        return not any(entry.round == encounter.round for entry in matching)
    return not matching


def record_interaction_usage(
    encounter: EncounterState,
    participant_id: str,
    resource_id: ResourceId,
    scope: UsageScope,
) -> EncounterState:
    participant = participant_state(encounter, participant_id)
    usage = InteractionUsage(resource_id, scope, encounter.turnId, encounter.round)
    return replace_participant_state(
        encounter,
        replace(participant, interactionUsages=(*participant.interactionUsages, usage)),
    )
