from __future__ import annotations

import random
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, replace
from time import time_ns
from typing import Any

from dnd_board.application.action_service import (
    ActionOperations,
    ability_check_modifier,
    log_blocked_roll,
    log_roll_note,
    resolve_damage_save_for_roll,
    response_ability_roll,
    save_modifier,
    skill_modifier,
    store_roll,
)
from dnd_board.application.character_state_service import (
    CharacterStatePersistence,
    apply_roll_result,
)
from dnd_board.application.resolution_interactions import (
    resolution_prompt_for_d20_test,
    resolution_prompt_for_effect_event,
)
from dnd_board.application.resource_service import spend_sheet_resources
from dnd_board.application.encounter_service import authorize_action, commit_action_authorization
from dnd_board.application.room_state import CharacterRuntimeSnapshot, InteractionEventKey, PendingCharacterResolution, Player, Room
from dnd_board.character_sheet import (
    AbilityType,
    AttackAction,
    CharacterSheet,
    ClassType,
    DamageType,
    DamageComponentKind,
    DiceType,
    RollLogEntry,
    RollLogEntryType,
    RollPayload,
    RollSource,
    RollModifierBreakdown,
    RollResolution,
    RollResolutionMode,
    SheetSectionType,
    ResolutionInterceptorPrompt,
    ResolutionInterceptorType,
    ResolutionPromptContinuation,
    RollModifierEffectTarget,
    SpellSaveOutcome,
    attack_roll_with_critical_damage,
    attack_roll_with_target_condition_modifiers,
    ability_modifier,
    build_attack_roll_payload,
    effect_saving_throw_dc,
    enum_key,
    enum_label,
    resolution_interceptor_prompt_to_dict,
    roll_log_entry_to_dict,
    roll_resolution_to_dict,
    sanitize_identifier,
    spell_casting_ability,
)
from dnd_board.rules.shared.character_effects import (
    CharacterEffectExecutionContext,
    ResolvedCharacterEffect,
    advance_character_effect_execution,
    first_contested_check_effect,
    reduced_damage_effect_node,
    resolved_d20,
    start_character_effect_execution,
)
from dnd_board.rules.shared.effects import (
    AbilityCheck,
    AmountCalculation,
    ApplyEffect,
    ApplyEffectOperation,
    AttackRoll,
    AttackRollEffect,
    AttackRollType,
    BoundEffect,
    CalculatedAmount,
    CombinedAmount,
    DiceAmount,
    DifficultyClassType,
    EffectAmountInput,
    EffectNodeId,
    EffectResolutionInputs,
    EffectParticipantBindings,
    EffectRollInput,
    FixedAmount,
    InteractionEffectRecipient,
    ModifyRoll,
    ModifyPendingDamage,
    PendingDamageModificationType,
    PendingDamageRerollSelection,
    ResolutionEventType,
    ResolutionEvent,
    ResolutionEventResponse,
    RollOutcome,
    RollModificationType,
    RerollSavingThrow,
    RerollPendingDamage,
    SavingThrowEffect,
    SequenceEffect,
    ResolutionId,
    apply_interaction_operations,
    dispatch_scheduled_effects,
    recurring_effects_for_event,
)
from dnd_board.rules.shared.resources import InsufficientResourceError, ResourceUpdate
from dnd_board.rules.encounter import (
    ActionCategory,
    interaction_usage_allowed,
    record_interaction_usage,
)


ResolutionResult = RollResolution | ResolutionInterceptorPrompt
AppliedInterceptorResult = tuple[RollPayload, list[str], list[RollPayload], RollResolution | None]


@dataclass(frozen=True)
class ResolutionOperations:
    source_sheet: Callable[[Room, RollPayload], CharacterSheet | None]
    all_sheets: Callable[[Room], list[CharacterSheet]]
    state_persistence: CharacterStatePersistence
    action_operations: ActionOperations
    save: Callable[[Room], None]
    broadcast: Callable[[Room, dict[str, Any]], Awaitable[None]]
    broadcast_room: Callable[[Room], Awaitable[None]]
    history_limit: int


class ResolutionServiceError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


async def resolve_turn_boundary_event(
    room: Room,
    participant: CharacterSheet,
    event_type: ResolutionEventType,
    operations: ResolutionOperations,
) -> dict[str, Any]:
    if event_type not in {ResolutionEventType.TURN_STARTED, ResolutionEventType.TURN_ENDED}:
        raise ValueError("Turn boundary resolution requires a turn event")
    created_at = time_ns()
    roll = RollPayload(
        id=f"turn-event-{created_at}",
        sheetId=participant.id,
        tokenId=participant.tokenId,
        roller="dm",
        source=RollSource(
            section=SheetSectionType.FEATURES,
            sourceId=enum_key(event_type),
            actionId=enum_key(event_type),
        ),
        sourceLabel=enum_label(event_type),
        resolution=RollResolutionMode.NONE,
        label=enum_label(event_type),
        iconUrl=None,
        dice=[],
        diceType=DiceType.D20,
        die="",
        modifier=0,
        modifierBreakdown=[],
        total=0,
        createdAt=created_at,
        pendingEffect=SequenceEffect([]),
    )
    return await resolve_pending_roll(
        room,
        roll,
        participant,
        False,
        operations,
        declaration_event_type=event_type,
    )


async def resolve_pending_roll(
    room: Room,
    roll: RollPayload,
    target: CharacterSheet,
    preserve_roll: bool,
    operations: ResolutionOperations,
    declaration_event_type: ResolutionEventType | None = None,
) -> dict[str, Any]:
    resolution_or_prompt = resolve_roll_or_prompt(
        room,
        roll,
        target,
        operations,
        declaration_event_type=declaration_event_type,
    )
    if isinstance(resolution_or_prompt, ResolutionInterceptorPrompt):
        if not preserve_roll:
            room.pending_rolls.pop(roll_queue_key(roll), None)
        room.pending_resolution_prompts[resolution_or_prompt.id] = resolution_or_prompt
        prompt_data = resolution_interceptor_prompt_to_dict(resolution_or_prompt)
        await operations.broadcast(room, {"type": "resolution_prompt_created", "prompt": prompt_data})
        return {"roomId": room.id, "prompt": prompt_data}

    if resolution_or_prompt.concentrationUpdates:
        operations.save(room)
    if not preserve_roll:
        room.pending_rolls.pop(roll_queue_key(roll), None)
    response, message = _record_resolution(
        room,
        roll,
        resolution_or_prompt,
        operations,
        preserve_roll=preserve_roll,
    )
    await operations.broadcast(room, message)
    return response


async def respond_to_prompt(
    room: Room,
    prompt: ResolutionInterceptorPrompt,
    player: Player,
    target: CharacterSheet,
    use: bool,
    operations: ResolutionOperations,
) -> dict[str, Any]:
    if prompt.effectExecutionId is not None:
        resolution_or_prompt = await _respond_to_effect_prompt(
            room,
            prompt,
            player,
            target,
            use,
            operations,
        )
        return await _publish_prompt_result(room, prompt, resolution_or_prompt, operations)

    if prompt.continuation == ResolutionPromptContinuation.STORE_ROLL:
        return await _respond_to_d20_test_prompt(room, prompt, player, target, use, operations)

    response_rolls = list(prompt.responseRolls or [])
    outcome_prefixes = [_decision_summary(prompt, use)]
    next_roll = prompt.pendingRoll
    ignored = [*prompt.ignoredInterceptors, resolution_interceptor_key(prompt)]
    await _claim_prompt(room, prompt, player, target, use, operations)
    if use:
        owner = _sheet_by_id(operations.all_sheets(room), prompt.ownerSheetId) or target
        used_roll, used_outcomes, used_response_rolls, canceled_resolution = apply_resolution_interceptor(
            prompt,
            target,
            owner,
        )
        outcome_prefixes.extend(used_outcomes)
        response_rolls.extend(used_response_rolls)
        if canceled_resolution is not None:
            resolution = attach_resolution_context(canceled_resolution, outcome_prefixes, response_rolls)
            return await _publish_prompt_result(room, prompt, resolution, operations)
        next_roll = used_roll

    resolution_or_prompt = resolve_roll_or_prompt(
        room,
        next_roll,
        target,
        operations,
        ignored,
        response_rolls,
        outcome_prefixes,
    )
    return await _publish_prompt_result(room, prompt, resolution_or_prompt, operations)


async def _respond_to_d20_test_prompt(
    room: Room,
    prompt: ResolutionInterceptorPrompt,
    player: Player,
    owner: CharacterSheet,
    use: bool,
    operations: ResolutionOperations,
) -> dict[str, Any]:
    await _claim_prompt(room, prompt, player, owner, use, operations)
    roll = prompt.pendingRoll
    if use:
        roll, _outcomes, _response_rolls, canceled = apply_resolution_interceptor(
            prompt,
            owner,
            owner,
        )
        if canceled is not None:
            raise ResolutionServiceError(409, "A D20 Test interaction cannot cancel the roll")

    ignored = {*prompt.ignoredInterceptors, resolution_interceptor_key(prompt)}
    next_prompt = resolution_prompt_for_d20_test(roll, owner, ignored)
    await operations.broadcast(
        room,
        {"type": "resolution_prompt_resolved", "promptId": prompt.id},
    )
    if next_prompt is not None:
        room.pending_resolution_prompts[next_prompt.id] = next_prompt
        prompt_data = resolution_interceptor_prompt_to_dict(next_prompt)
        await operations.broadcast(room, {"type": "resolution_prompt_created", "prompt": prompt_data})
        return {"roomId": room.id, "prompt": prompt_data}
    return await store_roll(room, roll, operations.action_operations)


def continue_effect_resolution(
    room: Room,
    pending: PendingCharacterResolution,
    target: CharacterSheet,
    operations: ResolutionOperations,
    response: ResolutionEventResponse | None = None,
) -> ResolutionResult:
    while True:
        advanced = advance_character_effect_execution(pending.active, response)
        response = None
        if isinstance(advanced, ResolvedCharacterEffect):
            room.pending_effect_executions.pop(pending.active.execution.resolutionId.value, None)
            scheduled_state_changed = bool(pending.touchedScheduledTargets)
            for sheet_id in pending.touchedScheduledTargets:
                remaining = pending.scheduledEffectStates.get(sheet_id, [])
                if remaining:
                    room.scheduled_effects[sheet_id] = remaining
                else:
                    room.scheduled_effects.pop(sheet_id, None)
            for response_roll in pending.responseRolls:
                room.pending_rolls[roll_queue_key(response_roll)] = response_roll
            primary_target = pending.active.context.sheets[pending.targetSheetId]
            resolution = apply_roll_result(
                room,
                pending.roll,
                primary_target,
                operations.source_sheet(room, pending.roll),
                advanced,
                operations.all_sheets(room),
                operations.state_persistence,
            )
            if scheduled_state_changed:
                operations.save(room)
            return attach_resolution_context(resolution, pending.outcomePrefixes, pending.responseRolls)

        current_target = pending.active.context.current_target()
        current_source = pending.active.context.source or current_target
        pending_damage = (
            pending.active.context.pendingDamages.get(advanced.effectNodeId)
            if advanced.effectNodeId is not None
            else None
        )
        event_amount = (
            pending_damage.currentAmount
            if pending_damage is not None
            else pending.active.context.amountInputs.get(advanced.effectNodeId)
            if advanced.effectNodeId is not None
            else None
        )
        event_effect = (
            ApplyEffect(replace(pending_damage.effect, amount=FixedAmount(pending_damage.currentAmount), scaling=[]))
            if advanced.eventType == ResolutionEventType.DAMAGE_PENDING and pending_damage is not None
            else advanced.pendingEffect
        )
        if event_effect is not advanced.pendingEffect:
            advanced = replace(advanced, pendingEffect=event_effect)
            pending.active.execution.waitingFor = advanced
        if (
            advanced.eventType == ResolutionEventType.ATTACK_ROLLED
            and advanced.rollOutcome is None
            and advanced.effectNodeId is not None
            and isinstance(advanced.pendingEffect, AttackRollEffect)
        ):
            attack_roll = runtime_attack_roll_for_effect(
                pending.roll,
                current_source,
                current_target,
                advanced.effectNodeId,
                advanced.pendingEffect.attack,
            )
            natural = resolved_d20(attack_roll)
            roll_outcome = RollOutcome.HIT if natural == 20 or (natural != 1 and attack_roll.total >= current_target.armorClass) else RollOutcome.MISS
            pending.active.context.attackRollPayloads[advanced.effectNodeId] = attack_roll
            pending.active.context.attackRollOutcomes[advanced.effectNodeId] = roll_outcome
            pending.responseRolls.append(attack_roll)
            advanced = replace(advanced, rollOutcome=roll_outcome)
            pending.active.execution.waitingFor = advanced
        if (
            advanced.eventType == ResolutionEventType.SAVE_ROLLED
            and advanced.rollOutcome is None
            and advanced.effectNodeId is not None
            and isinstance(advanced.pendingEffect, SavingThrowEffect)
        ):
            saving_throw = advanced.pendingEffect.savingThrow
            save_dc = (
                pending.roll.damageSaveDc
                if saving_throw.difficultyClass.calculation == DifficultyClassType.SOURCE_SPELL_SAVE_DC
                and pending.roll.damageSaveDc is not None
                else effect_saving_throw_dc(current_source, saving_throw)
            )
            configured = replace(
                pending.roll,
                damageSavingThrow=saving_throw.ability,
                damageSaveDc=save_dc,
                damageSaveOutcome=pending.roll.damageSaveOutcome or SpellSaveOutcome.PARTIAL,
                damageSaveSucceeded=None,
            )
            save_outcome, save_roll, resolved_roll = resolve_damage_save_for_roll(configured, current_target)
            roll_outcome = RollOutcome.SUCCESS if resolved_roll.damageSaveSucceeded else RollOutcome.FAILURE
            inputs = resolved_roll.effectInputs or EffectResolutionInputs()
            pending.roll = replace(
                resolved_roll,
                effectInputs=replace(
                    inputs,
                    rolls=[*inputs.rolls, EffectRollInput(advanced.effectNodeId, roll_outcome)],
                ),
            )
            pending.active.context.roll = pending.roll
            pending.active.context.savingThrowOutcomes[advanced.effectNodeId] = roll_outcome
            if save_outcome:
                pending.outcomePrefixes.append(save_outcome)
            if save_roll is not None:
                pending.active.context.savingThrowRollPayloads[advanced.effectNodeId] = save_roll
                pending.responseRolls.append(save_roll)
            advanced = replace(advanced, rollOutcome=roll_outcome)
            pending.active.execution.waitingFor = advanced
        event_key = InteractionEventKey(advanced.eventType, advanced.effectNodeId)
        if pending.interactionEvent != event_key:
            pending.interactionEvent = event_key
            pending.ignoredInterceptors.clear()
        node_roll = pending.roll
        if advanced.effectNodeId is not None:
            if advanced.eventType == ResolutionEventType.ATTACK_ROLLED:
                node_roll = pending.active.context.attackRollPayloads.get(advanced.effectNodeId, pending.roll)
            elif advanced.eventType == ResolutionEventType.SAVE_ROLLED:
                node_roll = pending.active.context.savingThrowRollPayloads.get(advanced.effectNodeId, pending.roll)
                node_roll = replace(
                    node_roll,
                    source=pending.roll.source,
                    sourceLabel=pending.roll.sourceLabel,
                )
        event_damage_components = node_roll.damageComponents
        if advanced.eventType == ResolutionEventType.DAMAGE_PENDING and advanced.effectNodeId is not None:
            matching_components = [
                replace(component, effectNodeIds=[EffectNodeId(())])
                for component in (node_roll.damageComponents or [])
                if advanced.effectNodeId in component.effectNodeIds
            ]
            event_damage_components = matching_components or None
        event_roll = replace(
            node_roll,
            sheetId=current_source.id,
            tokenId=current_source.tokenId,
            pendingEffect=event_effect,
            damageComponents=event_damage_components,
            effectInputs=(
                EffectResolutionInputs(amounts=[EffectAmountInput(EffectNodeId(()), event_amount)])
                if event_amount is not None
                else pending.roll.effectInputs
            ),
        )
        if advanced.eventType == ResolutionEventType.SAVE_ROLLED and isinstance(advanced.pendingEffect, SavingThrowEffect):
            event_roll = replace(
                event_roll,
                damageSavingThrow=advanced.pendingEffect.savingThrow.ability,
                damageSaveDc=(
                    pending.roll.damageSaveDc
                    if pending.roll.damageSaveDc is not None
                    else effect_saving_throw_dc(current_source, advanced.pendingEffect.savingThrow)
                ),
                damageSaveSucceeded=advanced.rollOutcome == RollOutcome.SUCCESS,
            )
        prompt = resolution_prompt_for_effect_event(
            pending.roll,
            event_roll,
            current_target,
            advanced,
            set(pending.ignoredInterceptors),
            pending.responseRolls,
            operations.all_sheets(room),
            operations.source_sheet(room, pending.roll),
            current_source,
            room.encounter,
        )
        if prompt is not None:
            execution_id = pending.active.execution.resolutionId.value
            room.pending_effect_executions[execution_id] = pending
            return replace(prompt, effectExecutionId=execution_id)

        if advanced.eventType == ResolutionEventType.ATTACK_ROLLED and advanced.effectNodeId is not None:
            finalize_attack_roll_event(pending, advanced.effectNodeId)
        response = default_effect_event_response(advanced)
        if pending.pendingBoundEffects:
            response = replace(response, boundEffects=list(pending.pendingBoundEffects))
            pending.pendingBoundEffects.clear()
        if event_key not in pending.dispatchedEvents:
            pending.dispatchedEvents.add(event_key)
            response = replace(
                response,
                boundEffects=[
                    *response.boundEffects,
                    *bound_effect_dispatches_for_event(room, pending, advanced, operations),
                ],
            )


def resolve_roll_or_prompt(
    room: Room,
    roll: RollPayload,
    target: CharacterSheet,
    operations: ResolutionOperations,
    ignored_interceptors: list[str] | None = None,
    response_rolls: list[RollPayload] | None = None,
    outcome_prefixes: list[str] | None = None,
    declaration_event_type: ResolutionEventType | None = None,
) -> ResolutionResult:
    ignored = set(ignored_interceptors or [])
    prefixes = list(outcome_prefixes or [])
    pre_response_rolls = list(response_rolls or [])

    source = operations.source_sheet(room, roll)
    working_roll = attack_roll_with_target_condition_modifiers(roll, target, source)
    working_roll, contest_outcome, contest_rolls = resolve_contested_check_for_roll(
        working_roll,
        target,
        source,
    )
    if contest_outcome is not None:
        prefixes.append(contest_outcome)
        pre_response_rolls.extend(contest_rolls)

    if working_roll.pendingEffect is not None:
        active = PendingCharacterResolution(
            active=start_character_effect_execution(
                working_roll,
                target,
                source,
                declaration_event_type,
            ),
            roll=working_roll,
            targetSheetId=target.id,
            responseRolls=pre_response_rolls,
            outcomePrefixes=prefixes,
            ignoredInterceptors=list(ignored),
            participantSnapshots={
                sheet.id: character_runtime_snapshot(sheet)
                for sheet in (target, source)
                if sheet is not None
            },
        )
        return continue_effect_resolution(room, active, target, operations)

    for response_roll in pre_response_rolls:
        room.pending_rolls[roll_queue_key(response_roll)] = response_roll
    resolution = apply_roll_result(
        room,
        working_roll,
        target,
        source,
        None,
        operations.all_sheets(room),
        operations.state_persistence,
    )
    return attach_resolution_context(resolution, prefixes, pre_response_rolls)


def resolve_contested_check_for_roll(
    roll: RollPayload,
    target: CharacterSheet,
    source: CharacterSheet | None,
) -> tuple[RollPayload, str | None, list[RollPayload]]:
    found = first_contested_check_effect(roll.pendingEffect)
    if found is None:
        return roll, None, []
    node_id, effect = found
    existing_inputs = roll.effectInputs or EffectResolutionInputs()
    if any(entry.effectNodeId == node_id for entry in existing_inputs.rolls) or source is None:
        return roll, None, []

    source_label, source_modifier = _ability_check_spec(source, effect.contest.sourceCheck)
    target_options = [
        (*_ability_check_spec(target, check), check)
        for check in effect.contest.targetChecks
    ]
    target_label, target_modifier, target_check = max(target_options, key=lambda option: option[1])
    source_response = response_ability_roll(
        sheet=source,
        ability=effect.contest.sourceCheck.ability,
        action_id="contest",
        label=source_label,
        source_label=roll.label,
        modifier=source_modifier + max(0, roll.total),
        saving_throw_conditions=False,
        modifier_target=RollModifierEffectTarget.ABILITY_CHECK,
    )
    target_response = response_ability_roll(
        sheet=target,
        ability=target_check.ability,
        action_id="contest",
        label=target_label,
        source_label=roll.label,
        modifier=target_modifier,
        saving_throw_conditions=False,
        modifier_target=RollModifierEffectTarget.ABILITY_CHECK,
    )
    source_won = source_response.total > target_response.total
    outcome = RollOutcome.SUCCESS if source_won else RollOutcome.FAILURE
    verb = "wins" if source_won else "fails"
    description = (
        f"{source.name} {verb} {source_label} {source_response.total} vs "
        f"{target.name} {target_label} {target_response.total}"
    )
    return (
        replace(
            roll,
            effectInputs=replace(
                existing_inputs,
                rolls=[*existing_inputs.rolls, EffectRollInput(node_id, outcome)],
            ),
        ),
        description,
        [source_response, target_response],
    )


def _ability_check_spec(sheet: CharacterSheet, check: AbilityCheck) -> tuple[str, int]:
    if check.skill is not None:
        return (
            f"{enum_label(check.ability)} ({enum_label(check.skill)})",
            skill_modifier(sheet, enum_key(check.skill), check.ability),
        )
    return f"{enum_label(check.ability)} Check", ability_check_modifier(sheet, check.ability)


def character_runtime_snapshot(sheet: CharacterSheet) -> CharacterRuntimeSnapshot:
    return CharacterRuntimeSnapshot(
        hitPoints=sheet.hp,
        conditions=tuple(sheet.conditions),
        suppressedConditions=tuple(sheet.suppressedConditions),
        damageResistances=tuple(sheet.damageResistances),
        damageVulnerabilities=tuple(sheet.damageVulnerabilities),
        damageImmunities=tuple(sheet.damageImmunities),
        ongoingEffects=tuple(sheet.ongoingEffects),
    )


def runtime_attack_roll_for_effect(
    parent_roll: RollPayload,
    source: CharacterSheet,
    target: CharacterSheet,
    node_id: EffectNodeId,
    attack: AttackRoll,
) -> RollPayload:
    ability = attack.ability
    if ability is None and attack.attackType == AttackRollType.SPELL:
        source_spell = next(
            (
                spell for spell in [*source.spells, *source.spellbook]
                if enum_key(spell.id) == parent_roll.source.sourceId
            ),
            None,
        )
        if source_spell is not None:
            ability = spell_casting_ability(source, source_spell)
    ability = ability or AbilityType.STRENGTH
    action = AttackAction(
        id=f"effect-attack-{'-'.join(str(part) for part in node_id.path)}",
        name="Triggered Attack",
        ability=ability,
        damageDiceCount=0,
        damageDiceType=DiceType.D4,
        damageType=parent_roll.damageType or DamageType.FORCE,
    )
    attack_roll = build_attack_roll_payload(source, parent_roll.roller, action)
    attack_roll = replace(
        attack_roll,
        source=parent_roll.source,
        sourceLabel=parent_roll.sourceLabel,
        label="Spell Attack" if attack.attackType == AttackRollType.SPELL else "Attack Roll",
    )
    return attack_roll_with_target_condition_modifiers(attack_roll, target, source)


def finalize_attack_roll_event(pending: PendingCharacterResolution, node_id: EffectNodeId) -> None:
    attack_roll = pending.active.context.attackRollPayloads.get(node_id)
    if attack_roll is None:
        return
    finalized = attack_roll_with_critical_damage(attack_roll)
    if resolved_d20(finalized) == 20:
        finalized = replace(finalized, criticalHit=True)
        pending.active.context.criticalAttackNodes.add(node_id)
        pending.active.context.criticalDamagePreparedNodes.update(
            effect_node_id
            for component in finalized.damageComponents or []
            for effect_node_id in component.effectNodeIds or []
        )
    else:
        finalized = replace(finalized, criticalHit=False)
        pending.active.context.criticalAttackNodes.discard(node_id)
    pending.active.context.attackRollPayloads[node_id] = finalized
    if finalized.id == pending.roll.id:
        pending.roll = finalized
        pending.active.context.roll = finalized
        if finalized.effectInputs is not None:
            pending.active.context.amountInputs.update(
                {entry.effectNodeId: entry.amount for entry in finalized.effectInputs.amounts}
            )


def bound_effect_dispatches_for_event(
    room: Room,
    pending: PendingCharacterResolution,
    event: ResolutionEvent,
    operations: ResolutionOperations,
) -> list[BoundEffect]:
    if event.eventType not in {
        ResolutionEventType.DAMAGE_APPLIED,
        ResolutionEventType.CONDITION_APPLIED,
        ResolutionEventType.EFFECT_COMMITTED,
        ResolutionEventType.TURN_STARTED,
        ResolutionEventType.TURN_ENDED,
        ResolutionEventType.REST_COMPLETED,
    } or event.bindings is None:
        return []

    target_id = event.bindings.targetSheetId
    persisted_state = pending.scheduledEffectStates.setdefault(
        target_id,
        list(room.scheduled_effects.get(target_id, [])),
    )
    excluded_sources = {event.dispatchSource} if event.dispatchSource is not None else set()
    persisted = dispatch_scheduled_effects(persisted_state, event.eventType, excluded_sources)
    pending.scheduledEffectStates[target_id] = persisted.remaining
    pending.touchedScheduledTargets.add(target_id)

    local_scheduled = [
        active for active in pending.active.context.scheduledEffects
        if active.targetSheetId == target_id
    ]
    local = dispatch_scheduled_effects(local_scheduled, event.eventType, excluded_sources)
    local_ids = {active.id for active in local_scheduled}
    pending.active.context.scheduledEffects = [
        active for active in pending.active.context.scheduledEffects
        if active.id not in local_ids
    ] + local.remaining

    target_state = pending.active.context.participants.get(target_id)
    recurring = recurring_effects_for_event(
        target_state.ongoingEffects if target_state is not None else [],
        event.eventType,
    )
    dispatches = [*persisted.dispatched, *local.dispatched, *recurring]
    sheets = {sheet.id: sheet for sheet in operations.all_sheets(room)}
    bound: list[BoundEffect] = []
    for dispatch in dispatches:
        if dispatch.source == event.dispatchSource:
            continue
        source = sheets.get(dispatch.sourceSheetId)
        target = sheets.get(dispatch.targetSheetId)
        if source is None or target is None:
            continue
        pending.active.context.register_participant(source)
        pending.active.context.register_participant(target)
        pending.participantSnapshots.setdefault(source.id, character_runtime_snapshot(source))
        pending.participantSnapshots.setdefault(target.id, character_runtime_snapshot(target))
        bound.append(BoundEffect(
            effect=dispatch.effect,
            bindings=EffectParticipantBindings(
                sourceSheetId=source.id,
                targetSheetId=target.id,
                ownerSheetId=source.id,
            ),
            dispatchSource=dispatch.source,
        ))
    return bound


def default_effect_event_response(event: ResolutionEvent) -> ResolutionEventResponse:
    if event.eventType in {
        ResolutionEventType.ATTACK_ROLLED,
        ResolutionEventType.SAVE_ROLLED,
        ResolutionEventType.CHECK_ROLLED,
    }:
        return ResolutionEventResponse(rollOutcome=event.rollOutcome)
    if event.eventType in {
        ResolutionEventType.DAMAGE_APPLIED,
        ResolutionEventType.CONDITION_APPLIED,
        ResolutionEventType.EFFECT_COMMITTED,
        ResolutionEventType.REST_COMPLETED,
    }:
        return ResolutionEventResponse()
    return ResolutionEventResponse(pendingEffect=event.pendingEffect)


async def _respond_to_effect_prompt(
    room: Room,
    prompt: ResolutionInterceptorPrompt,
    player: Player,
    target: CharacterSheet,
    use: bool,
    operations: ResolutionOperations,
) -> ResolutionResult:
    execution_id = prompt.effectExecutionId
    assert execution_id is not None
    pending = room.pending_effect_executions.get(execution_id)
    if pending is None:
        raise ResolutionServiceError(409, "Effect execution is no longer active")
    conflicting_participants = pending_execution_conflicts(pending, operations.all_sheets(room))
    if conflicting_participants:
        room.pending_effect_executions.pop(execution_id, None)
        names = ", ".join(conflicting_participants)
        raise ResolutionServiceError(
            409,
            f"Effect execution canceled because participant state changed: {names}. Roll again.",
        )
    effect_event = pending.active.execution.waitingFor
    if effect_event is None:
        raise ResolutionServiceError(409, "Effect execution is not waiting for a response")

    await _claim_prompt(room, prompt, player, target, use, operations)
    pending.ignoredInterceptors.append(resolution_interceptor_key(prompt))
    pending.outcomePrefixes.append(_decision_summary(prompt, use))
    if not use:
        return continue_effect_resolution(room, pending, target, operations)

    live_pending_damage = (
        pending.active.context.pendingDamages.get(effect_event.effectNodeId)
        if effect_event.eventType == ResolutionEventType.DAMAGE_PENDING
        and effect_event.effectNodeId is not None
        else None
    )
    owner = _sheet_by_id(operations.all_sheets(room), prompt.ownerSheetId) or target
    rerolls_pending_damage = any(
        isinstance(operation, RerollPendingDamage)
        for operation in prompt.interaction.operations
    )
    used_roll, used_outcomes, used_response_rolls, canceled_resolution = apply_resolution_interceptor(
        prompt,
        target,
        owner,
        modify_damage_roll=live_pending_damage is None or rerolls_pending_damage,
    )
    pending.outcomePrefixes.extend(used_outcomes)
    replaced_response_roll_ids = {roll.id for roll in used_response_rolls}
    if replaced_response_roll_ids:
        pending.responseRolls = [
            roll for roll in pending.responseRolls
            if roll.id not in replaced_response_roll_ids
        ]
    pending.responseRolls.extend(used_response_rolls)
    if canceled_resolution is not None:
        room.pending_effect_executions.pop(execution_id, None)
        return attach_resolution_context(canceled_resolution, pending.outcomePrefixes, pending.responseRolls)

    owner_effects = [
        operation.effect
        for operation in prompt.interaction.operations
        if isinstance(operation, ApplyEffectOperation)
        and operation.recipient == InteractionEffectRecipient.OWNER
    ]
    if owner_effects:
        pending.active.context.register_participant(owner)
        pending.participantSnapshots.setdefault(owner.id, character_runtime_snapshot(owner))
        pending.pendingBoundEffects.extend(
            BoundEffect(
                effect=effect,
                bindings=EffectParticipantBindings(
                    sourceSheetId=owner.id,
                    targetSheetId=owner.id,
                    ownerSheetId=owner.id,
                ),
            )
            for effect in owner_effects
        )

    pending_damage_modifications = [
        operation
        for operation in prompt.interaction.operations
        if isinstance(operation, ModifyPendingDamage)
    ]
    if (
        effect_event.eventType == ResolutionEventType.DAMAGE_PENDING
        and effect_event.effectNodeId is not None
        and pending_damage_modifications
    ):
        apply_pending_damage_modifications(
            pending.active.context,
            effect_event.effectNodeId,
            pending_damage_modifications,
            owner,
        )
        current_damage = pending.active.context.pendingDamages.get(effect_event.effectNodeId)
        if current_damage is not None:
            used_roll = replace(
                used_roll,
                pendingEffect=ApplyEffect(current_damage.effect),
                effectInputs=EffectResolutionInputs(
                    amounts=[EffectAmountInput(EffectNodeId(()), current_damage.currentAmount)]
                ),
            )

    updated_amounts = {
        entry.effectNodeId: entry.amount
        for entry in (used_roll.effectInputs.amounts if used_roll.effectInputs is not None else [])
    }
    if effect_event.effectNodeId is not None and EffectNodeId(()) in updated_amounts:
        root_amount = updated_amounts.pop(EffectNodeId(()))
        updated_amounts.setdefault(effect_event.effectNodeId, root_amount)
    if effect_event.effectNodeId is not None:
        pending.active.context.update_pending_damage(
            effect_event.effectNodeId,
            used_roll.pendingEffect,
            updated_amounts.get(effect_event.effectNodeId),
        )
        if rerolls_pending_damage and used_roll.damageComponents:
            rerolled_component = used_roll.damageComponents[0]
            pending.roll = replace(
                pending.roll,
                damageComponents=[
                    replace(
                        component,
                        dice=rerolled_component.dice,
                        total=rerolled_component.total,
                        modifierBreakdown=rerolled_component.modifierBreakdown,
                    )
                    if effect_event.effectNodeId in component.effectNodeIds
                    else component
                    for component in (pending.roll.damageComponents or [])
                ],
            )
            pending.active.context.roll = pending.roll
    pending.active.context.amountInputs.update(updated_amounts)
    if effect_event.effectNodeId is not None:
        pending_damage = pending.active.context.pendingDamages.get(effect_event.effectNodeId)
        if pending_damage is not None:
            pending.active.context.amountInputs[effect_event.effectNodeId] = pending_damage.currentAmount

    if effect_event.eventType == ResolutionEventType.SAVE_ROLLED:
        succeeded = used_roll.damageSaveSucceeded is True
        roll_outcome = RollOutcome.SUCCESS if succeeded else RollOutcome.FAILURE
        pending.roll = replace(pending.roll, damageSaveSucceeded=succeeded)
        pending.active.context.roll = pending.roll
        if effect_event.effectNodeId is not None:
            pending.active.context.savingThrowOutcomes[effect_event.effectNodeId] = roll_outcome
            pending.active.context.savingThrowRollPayloads[effect_event.effectNodeId] = used_roll
        pending.active.execution.waitingFor = replace(effect_event, rollOutcome=roll_outcome)
    elif effect_event.eventType == ResolutionEventType.ATTACK_ROLLED:
        natural = resolved_d20(used_roll)
        hit = natural == 20 or (natural != 1 and used_roll.total >= target.armorClass)
        roll_outcome = RollOutcome.HIT if hit else RollOutcome.MISS
        if effect_event.effectNodeId is not None:
            pending.active.context.attackRollOutcomes[effect_event.effectNodeId] = roll_outcome
            pending.active.context.attackRollPayloads[effect_event.effectNodeId] = used_roll
        if used_roll.id == pending.roll.id:
            pending.roll = replace(
                pending.roll,
                dice=used_roll.dice,
                die=used_roll.die,
                modifier=used_roll.modifier,
                modifierBreakdown=used_roll.modifierBreakdown,
                total=used_roll.total,
                advantageConditions=used_roll.advantageConditions,
                disadvantageConditions=used_roll.disadvantageConditions,
                criticalHit=False,
            )
            pending.active.context.roll = pending.roll
        pending.active.execution.waitingFor = replace(effect_event, rollOutcome=roll_outcome)
    else:
        pending.active.execution.waitingFor = replace(effect_event, pendingEffect=used_roll.pendingEffect)
    return continue_effect_resolution(room, pending, target, operations)


async def _claim_prompt(
    room: Room,
    prompt: ResolutionInterceptorPrompt,
    player: Player,
    target: CharacterSheet,
    use: bool,
    operations: ResolutionOperations,
) -> None:
    if room.pending_resolution_prompts.get(prompt.id) is not prompt:
        raise ResolutionServiceError(409, "Resolution prompt has already been answered")

    owner = next((sheet for sheet in operations.all_sheets(room) if sheet.id == prompt.ownerSheetId), target)
    if use and not interaction_usage_allowed(
        room.encounter,
        owner.id,
        prompt.interaction.usageResource,
        prompt.interaction.usageScope,
    ):
        raise ResolutionServiceError(409, "This interaction has already been used for its current timing scope")
    updates: list[ResourceUpdate] = []
    authorization = authorize_action(
        room,
        owner.id,
        prompt.interaction.activation if use else None,
        ActionCategory.MAGIC if prompt.pendingRoll.source.section == SheetSectionType.SPELLS else ActionCategory.FEATURE,
        room.encounter.turnId if room.encounter is not None else None,
        resolution_response=True,
        sheet=owner,
        participant_sheets=operations.all_sheets(room),
    )
    if use and not authorization.allowed:
        reason = authorization.reason or "Reaction is unavailable"
        await log_blocked_roll(
            room,
            owner,
            player,
            prompt.label,
            prompt.useLabel,
            reason,
            operations.action_operations,
        )
        raise ResolutionServiceError(409, reason)
    if use and prompt.interaction.resourceCosts:
        resource_payload = replace(
            prompt.pendingRoll,
            sourceLabel=prompt.label,
            label=prompt.useLabel,
            resourcesSpent=None,
        )
        try:
            updates = spend_sheet_resources(room, owner, prompt.interaction.resourceCosts)
        except InsufficientResourceError as error:
            await log_blocked_roll(
                room,
                owner,
                player,
                resource_payload.sourceLabel,
                resource_payload.label,
                str(error),
                operations.action_operations,
            )
            raise ResolutionServiceError(409, str(error)) from error
        except ValueError as error:
            raise ResolutionServiceError(400, str(error)) from error

    if use:
        commit_action_authorization(room, owner.id, authorization)
        if (
            room.encounter is not None
            and prompt.interaction.usageResource is not None
            and prompt.interaction.usageScope is not None
        ):
            room.encounter = record_interaction_usage(
                room.encounter,
                owner.id,
                prompt.interaction.usageResource,
                prompt.interaction.usageScope,
            )
        if authorization.resource is not None and room.encounter is not None:
            participant = next(
                entry for entry in room.encounter.participantStates
                if entry.participantId == owner.id
            )
            state = next(entry for entry in participant.resources if entry.resource == authorization.resource)
            updates.append(ResourceUpdate(state.resource, state.resource.value, state.current, state.maximum))

    # Claim and commit payment before yielding to broadcasts. Failed payment leaves
    # the prompt available for another valid response.
    if room.pending_resolution_prompts.get(prompt.id) is not prompt:
        raise ResolutionServiceError(409, "Resolution prompt has already been answered")
    room.pending_resolution_prompts.pop(prompt.id)
    if not updates:
        return
    operations.save(room)
    await operations.broadcast_room(room)
    summary = ", ".join(f"{update.label} {update.current}/{update.maximum}" for update in updates)
    await log_roll_note(
        room,
        owner,
        player,
        prompt.label,
        f"Resources spent: {summary}",
        DiceType.D20,
        [],
        operations.action_operations,
    )


async def _publish_prompt_result(
    room: Room,
    answered_prompt: ResolutionInterceptorPrompt,
    resolution_or_prompt: ResolutionResult,
    operations: ResolutionOperations,
) -> dict[str, Any]:
    if isinstance(resolution_or_prompt, ResolutionInterceptorPrompt):
        room.pending_resolution_prompts[resolution_or_prompt.id] = resolution_or_prompt
        prompt_data = resolution_interceptor_prompt_to_dict(resolution_or_prompt)
        await operations.broadcast(
            room,
            {"type": "resolution_prompt_resolved", "promptId": answered_prompt.id},
        )
        await operations.broadcast(room, {"type": "resolution_prompt_created", "prompt": prompt_data})
        return {"roomId": room.id, "prompt": prompt_data}

    if resolution_or_prompt.concentrationUpdates:
        operations.save(room)
    response, message = _record_resolution(
        room,
        answered_prompt.sourceRoll,
        resolution_or_prompt,
        operations,
    )
    await operations.broadcast(
        room,
        {"type": "resolution_prompt_resolved", "promptId": answered_prompt.id},
    )
    await operations.broadcast(room, message)
    return response


def _record_resolution(
    room: Room,
    source_roll: RollPayload,
    resolution: RollResolution,
    operations: ResolutionOperations,
    *,
    preserve_roll: bool | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    resolution_data = roll_resolution_to_dict(resolution)
    log_entry = RollLogEntry(
        id=f"log-{resolution.id}",
        entryType=RollLogEntryType.ROLL_RESOLVED,
        createdAt=resolution.createdAt,
        roll=source_roll,
        resolution=resolution,
    )
    room.roll_history.append(log_entry)
    room.roll_history = room.roll_history[-operations.history_limit:]
    message: dict[str, Any] = {
        "type": "roll_resolved",
        "rollId": source_roll.id,
        "tokenId": source_roll.tokenId,
        "resolution": resolution_data,
        "logEntry": roll_log_entry_to_dict(log_entry),
    }
    response: dict[str, Any] = {
        "roomId": room.id,
        "resolution": resolution_data,
        "logEntry": roll_log_entry_to_dict(log_entry),
    }
    if preserve_roll is not None:
        message["preserveRoll"] = preserve_roll
        response["preserveRoll"] = preserve_roll
    return response, message


def roll_queue_key(roll: RollPayload) -> tuple[str, str, str, str]:
    return (roll.tokenId, enum_key(roll.source.section), roll.source.sourceId, roll.source.actionId)


def _decision_summary(prompt: ResolutionInterceptorPrompt, use: bool) -> str:
    return f"{prompt.ownerName} {'uses' if use else 'declines'} {prompt.label}"


def pending_execution_conflicts(
    pending: PendingCharacterResolution,
    sheets: list[CharacterSheet],
) -> list[str]:
    sheets_by_id = {sheet.id: sheet for sheet in sheets}
    conflicts: list[str] = []
    for sheet_id, snapshot in pending.participantSnapshots.items():
        sheet = sheets_by_id.get(sheet_id)
        if sheet is None or character_runtime_snapshot(sheet) != snapshot:
            conflicts.append(sheet.name if sheet is not None else sheet_id)
    return conflicts


def resolution_interceptor_key(prompt: ResolutionInterceptorPrompt) -> str:
    return (
        f"{enum_key(prompt.interceptorType)}:{prompt.ownerSheetId}:"
        f"{sanitize_identifier(prompt.label)}"
    )


def attach_resolution_context(
    resolution: RollResolution,
    outcome_prefixes: list[str],
    response_rolls: list[RollPayload],
) -> RollResolution:
    if outcome_prefixes:
        resolution.outcome = f"{'; '.join(outcome_prefixes)}; {resolution.outcome}"
    if response_rolls:
        resolution.responseRolls = _dedupe_response_rolls(
            [*response_rolls, *(resolution.responseRolls or [])]
        )
    return resolution


def apply_resolution_interceptor(
    prompt: ResolutionInterceptorPrompt,
    target: CharacterSheet,
    owner: CharacterSheet,
    modify_damage_roll: bool = True,
) -> AppliedInterceptorResult:
    roll_outcome = RollOutcome.FAILURE if _failed_save_ability(prompt.pendingRoll) is not None else None
    operation_result = apply_interaction_operations(
        ResolutionEvent(
            resolutionId=ResolutionId(time_ns()),
            eventType=prompt.interaction.trigger,
            pendingEffect=prompt.pendingRoll.pendingEffect,
            rollOutcome=roll_outcome,
        ),
        prompt.interaction.operations,
    )
    modified_roll = _roll_after_interaction_operations(
        prompt.pendingRoll,
        operation_result,
        owner,
        prompt.label,
        modify_damage=modify_damage_roll,
    )
    if operation_result.rollModifications and _failed_save_ability(prompt.pendingRoll) is not None:
        save_dc = _failed_save_dc(prompt.pendingRoll)
        if save_dc is not None:
            modified_roll = _save_outcome_roll(modified_roll, modified_roll.total >= save_dc)
    if operation_result.cancelled:
        resolution = RollResolution(
            id=f"resolution-{time_ns()}",
            roll=prompt.sourceRoll,
            targetSheetId=target.id,
            targetTokenId=target.tokenId,
            targetName=target.name,
            targetArmorClass=target.armorClass,
            targetHp=target.hp,
            targetConditions=target.conditions,
            outcome=(
                f"{prompt.ownerName} counters {prompt.sourceRoll.sourceLabel}; "
                f"it has no effect on {target.name}"
            ),
            createdAt=time_ns(),
        )
        return modified_roll, [], [], resolution
    if operation_result.rollOutcome == RollOutcome.SUCCESS and roll_outcome == RollOutcome.FAILURE:
        return _save_outcome_roll(modified_roll, True), [f"{prompt.ownerName} turns the failed save into a success"], [], None
    if operation_result.rollModifications and _failed_save_ability(prompt.pendingRoll) is not None:
        succeeded = modified_roll.damageSaveSucceeded is True
        return (
            modified_roll,
            [f"{prompt.ownerName} uses {prompt.label} and {'passes' if succeeded else 'fails'} with {modified_roll.total}"],
            [modified_roll],
            None,
        )
    if operation_result.savingThrowRerolls:
        saving_throw = _failed_save_ability(prompt.pendingRoll) or AbilityType.STRENGTH
        save_dc = _failed_save_dc(prompt.pendingRoll)
        reroll_bonus = _interaction_reroll_bonus(target, operation_result.savingThrowRerolls[0])
        reroll = response_ability_roll(
            sheet=target,
            ability=saving_throw,
            action_id=enum_key(prompt.interceptorType),
            label=prompt.label,
            source_label=modified_roll.sourceLabel,
            modifier=save_modifier(target, saving_throw) + reroll_bonus,
        )
        succeeded = save_dc is not None and reroll.total >= save_dc
        outcome = (
            f"{target.name} rerolls with {prompt.label} and "
            f"{'passes' if succeeded else 'fails'} with {reroll.total}"
        )
        return _save_outcome_roll(modified_roll, succeeded), [outcome], [reroll], None
    if operation_result.pendingDamageModifications:
        modification = operation_result.pendingDamageModifications[0]
        action = (
            "halves"
            if modification.modification == PendingDamageModificationType.MULTIPLY
            and modification.numerator == 1
            and modification.denominator == 2
            else "modifies"
        )
        return modified_roll, [f"{prompt.ownerName} {action} the incoming damage"], [], None
    if operation_result.pendingDamageRerolls:
        return modified_roll, [f"{prompt.ownerName} rerolls the weapon damage"], [], None
    return modified_roll, [], [], None


def apply_pending_damage_modifications(
    context: CharacterEffectExecutionContext,
    node_id: EffectNodeId,
    modifications: list[ModifyPendingDamage],
    owner: CharacterSheet,
) -> None:
    pending = context.pendingDamages.get(node_id)
    if pending is None:
        return
    amount = pending.currentAmount
    for modification in modifications:
        if modification.modification == PendingDamageModificationType.PREVENT:
            amount = 0
        elif modification.modification == PendingDamageModificationType.MULTIPLY:
            if modification.denominator == 0:
                raise ValueError("Damage multiplier denominator cannot be zero")
            amount = max(0, amount * modification.numerator // modification.denominator)
        elif modification.modification == PendingDamageModificationType.REDUCE:
            amount = max(0, amount - _interaction_amount(owner, modification.amount))
    pending.currentAmount = amount
    pending.effect = replace(pending.effect, amount=FixedAmount(amount), scaling=[])
    context.amountInputs[node_id] = amount


def _roll_after_interaction_operations(
    roll: RollPayload,
    operation_result: Any,
    owner: CharacterSheet,
    source_label: str,
    modify_damage: bool = True,
) -> RollPayload:
    pending_effect = operation_result.pendingEffect
    appended_effects = [*operation_result.additionalEffects, *operation_result.scheduledEffects]
    if appended_effects:
        pending_effect = SequenceEffect(
            [*([pending_effect] if pending_effect is not None else []), *appended_effects]
        )
    updated = replace(roll, pendingEffect=pending_effect)
    if modify_damage:
        for modification in operation_result.pendingDamageModifications:
            if modification.modification == PendingDamageModificationType.PREVENT:
                updated = _scaled_damage_roll(updated, 0, 1)
            elif modification.modification == PendingDamageModificationType.MULTIPLY:
                updated = _scaled_damage_roll(updated, modification.numerator, modification.denominator)
            elif modification.modification == PendingDamageModificationType.REDUCE:
                updated = _reduced_damage_roll(updated, _interaction_amount(owner, modification.amount))
        for reroll in operation_result.pendingDamageRerolls:
            updated = _rerolled_pending_damage_roll(updated, reroll, source_label)
    for modification in operation_result.rollModifications:
        updated = _modified_d20_roll(updated, modification, owner, source_label)
    return updated


def _rerolled_pending_damage_roll(
    roll: RollPayload,
    reroll: RerollPendingDamage,
    source_label: str,
) -> RollPayload:
    components = list(roll.damageComponents or [])
    if not components:
        return roll
    amount_inputs = list(roll.effectInputs.amounts) if roll.effectInputs is not None else []
    updated_components = []
    for component in components:
        if component.kind != DamageComponentKind.WEAPON_DICE or not component.dice:
            updated_components.append(component)
            continue
        rerolled_dice = [random.randint(1, component.diceType.value) for _ in component.dice]
        rerolled_total = sum(rerolled_dice) + component.modifier
        if reroll.selection == PendingDamageRerollSelection.HIGHER:
            keep_reroll = rerolled_total > component.total
        elif reroll.selection == PendingDamageRerollSelection.LOWER:
            keep_reroll = rerolled_total < component.total
        else:
            keep_reroll = True
        kept_dice = rerolled_dice if keep_reroll else component.dice
        kept_total = rerolled_total if keep_reroll else component.total
        description = (
            f"Original {component.dice}; rerolled {rerolled_dice}; "
            f"kept {'reroll' if keep_reroll else 'original'}"
        )
        updated = replace(
            component,
            dice=kept_dice,
            total=kept_total,
            modifierBreakdown=[
                *component.modifierBreakdown,
                RollModifierBreakdown(source_label, 0, description),
            ],
        )
        updated_components.append(updated)
        if component.effectNodeIds:
            amount_inputs = [
                entry for entry in amount_inputs
                if entry.effectNodeId not in component.effectNodeIds
            ]
            amount_inputs.extend(
                EffectAmountInput(node_id, kept_total)
                for node_id in component.effectNodeIds
            )
    return replace(
        roll,
        total=(
            roll.total
            if roll.resolution == RollResolutionMode.ATTACK_VS_ARMOR_CLASS
            else sum(component.total for component in updated_components)
        ),
        damageComponents=updated_components,
        effectInputs=(
            replace(roll.effectInputs, amounts=amount_inputs)
            if roll.effectInputs is not None
            else None
        ),
    )


def _scaled_damage_roll(roll: RollPayload, numerator: int, denominator: int) -> RollPayload:
    if denominator == 0:
        raise ValueError("Damage multiplier denominator cannot be zero")
    if roll.resolution == RollResolutionMode.ATTACK_VS_ARMOR_CLASS:
        return roll
    if roll.damageComponents:
        components = [
            replace(component, total=max(0, component.total * numerator // denominator))
            for component in roll.damageComponents
        ]
        return replace(roll, total=sum(component.total for component in components), damageComponents=components)
    return replace(roll, total=max(0, roll.total * numerator // denominator))


def _reduced_damage_roll(roll: RollPayload, amount: int) -> RollPayload:
    remaining = max(0, amount)
    pending_effect = roll.pendingEffect
    if roll.damageComponents:
        components = []
        amount_inputs = list(roll.effectInputs.amounts) if roll.effectInputs is not None else []
        addressed_damage = False
        for component in roll.damageComponents:
            reduction = min(component.total, remaining)
            reduced_total = component.total - reduction
            components.append(replace(component, total=reduced_total))
            if component.effectNodeIds:
                addressed_damage = True
                amount_inputs = [
                    entry for entry in amount_inputs
                    if entry.effectNodeId not in component.effectNodeIds
                ]
                amount_inputs.extend(
                    EffectAmountInput(node_id, reduced_total)
                    for node_id in component.effectNodeIds
                )
            remaining -= reduction
        if pending_effect is not None and not addressed_damage:
            pending_effect = reduced_damage_effect_node(pending_effect, max(0, amount))
        return replace(
            roll,
            total=(
                roll.total
                if roll.resolution == RollResolutionMode.ATTACK_VS_ARMOR_CLASS
                else sum(component.total for component in components)
            ),
            damageComponents=components,
            pendingEffect=pending_effect,
            effectInputs=(
                replace(roll.effectInputs, amounts=amount_inputs)
                if roll.effectInputs is not None
                else None
            ),
        )
    total = max(0, roll.total - remaining)
    if pending_effect is not None:
        pending_effect = reduced_damage_effect_node(pending_effect, max(0, amount))
    return replace(
        roll,
        total=roll.total if roll.resolution == RollResolutionMode.ATTACK_VS_ARMOR_CLASS else total,
        pendingEffect=pending_effect,
    )


def _interaction_amount(owner: CharacterSheet, amount: Any) -> int:
    if isinstance(amount, CombinedAmount):
        return sum(_interaction_amount(owner, part) for part in amount.amounts)
    if isinstance(amount, FixedAmount):
        return amount.value
    if isinstance(amount, DiceAmount):
        return amount.staticBonus + sum(
            random.randint(1, amount.diceType.value) for _ in range(amount.diceCount)
        )
    if isinstance(amount, CalculatedAmount):
        if amount.calculation == AmountCalculation.SOURCE_CLASS_LEVEL and amount.characterClass is not None:
            value = _class_level(owner, amount.characterClass)
        elif amount.calculation == AmountCalculation.SOURCE_CHARACTER_LEVEL:
            value = sum(character_class.level for character_class in owner.classes)
        elif amount.calculation == AmountCalculation.SOURCE_PROFICIENCY_BONUS:
            value = owner.proficiencyBonus
        elif amount.calculation == AmountCalculation.SOURCE_ABILITY_MODIFIER and amount.ability is not None:
            value = ability_modifier(getattr(owner.abilityScores, enum_key(amount.ability)))
        else:
            value = 0
        value *= amount.multiplier
        return max(amount.minimum, value) if amount.minimum is not None else value
    return 0


def _modified_d20_roll(
    roll: RollPayload,
    modification: ModifyRoll,
    owner: CharacterSheet,
    source_label: str,
) -> RollPayload:
    if modification.modification in {RollModificationType.ADD, RollModificationType.SUBTRACT}:
        amount = _interaction_amount(owner, modification.amount)
        value = amount if modification.modification == RollModificationType.ADD else -amount
        return replace(
            roll,
            modifier=roll.modifier + value,
            modifierBreakdown=[*roll.modifierBreakdown, RollModifierBreakdown(source_label, value)],
            total=roll.total + value,
        )
    if not roll.dice or roll.diceType != DiceType.D20:
        return roll
    extra = random.randint(1, 20)
    dice = [roll.dice[0], extra]
    selected = max(dice) if modification.modification == RollModificationType.ADVANTAGE else min(dice)
    die = "2d20kh1" if modification.modification == RollModificationType.ADVANTAGE else "2d20kl1"
    return replace(roll, dice=dice, die=die, total=selected + roll.modifier)


def _interaction_reroll_bonus(sheet: CharacterSheet, reroll: RerollSavingThrow) -> int:
    if not isinstance(reroll.bonus, CalculatedAmount):
        return 0
    if reroll.bonus.calculation == AmountCalculation.SOURCE_CLASS_LEVEL and reroll.bonus.characterClass is not None:
        return _class_level(sheet, reroll.bonus.characterClass) * reroll.bonus.multiplier
    return 0


def _save_outcome_roll(roll: RollPayload, succeeded: bool) -> RollPayload:
    if roll.damageSavingThrow is not None:
        effect_inputs = roll.effectInputs
        if effect_inputs is not None and effect_inputs.rolls:
            latest = effect_inputs.rolls[-1]
            rolls = [
                *effect_inputs.rolls[:-1],
                replace(latest, outcome=RollOutcome.SUCCESS if succeeded else RollOutcome.FAILURE),
            ]
            return replace(
                roll,
                damageSaveSucceeded=succeeded,
                effectInputs=replace(effect_inputs, rolls=rolls),
            )
        return replace(roll, damageSaveSucceeded=succeeded)
    return roll


def _failed_save_ability(roll: RollPayload) -> AbilityType | None:
    return roll.damageSavingThrow if roll.damageSaveSucceeded is False else None


def _failed_save_dc(roll: RollPayload) -> int | None:
    return roll.damageSaveDc if roll.damageSaveSucceeded is False else None


def _class_level(sheet: CharacterSheet, class_type: ClassType) -> int:
    return sum(character_class.level for character_class in sheet.classes if character_class.name == class_type)


def _dedupe_response_rolls(response_rolls: list[RollPayload]) -> list[RollPayload]:
    deduped: list[RollPayload] = []
    seen: set[str] = set()
    for response_roll in response_rolls:
        if response_roll.id in seen:
            continue
        seen.add(response_roll.id)
        deduped.append(response_roll)
    return deduped


def _sheet_by_id(sheets: list[CharacterSheet], sheet_id: str) -> CharacterSheet | None:
    return next((sheet for sheet in sheets if sheet.id == sheet_id), None)
