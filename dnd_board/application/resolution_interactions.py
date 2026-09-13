from __future__ import annotations

from dataclasses import dataclass
from time import time_ns

from dnd_board.character_sheet import (
    AbilityType,
    CharacterSheet,
    ResolutionInterceptorPrompt,
    ResolutionInterceptorTrigger,
    ResolutionInterceptorType,
    RollPayload,
    RollResolutionMode,
    SheetSectionType,
    enum_key,
    enum_label,
    sanitize_identifier,
)
from dnd_board.rules.shared.character_effects import (
    CharacterEffectExecutionContext,
    added_condition_types,
    first_damage_effect,
)
from dnd_board.rules.shared.condition_effects import condition_ongoing_effects
from dnd_board.rules.shared.effects import (
    ApplyEffectOperation,
    CancelPendingAction,
    EffectNodeId,
    Interaction,
    InteractionDecisionType,
    ModifyAction,
    ModifyPendingDamage,
    ModifyRoll,
    PreventCondition,
    ReplaceRollOutcome,
    ResolutionEvent,
    ResolutionEventType,
    RerollSavingThrow,
    RollOutcome,
    ScheduleEffectOperation,
    SourceIsOwnerPredicate,
)


@dataclass(frozen=True)
class SheetInteractionSource:
    label: str
    interaction: Interaction


def resolution_prompt_for_effect_event(
    source_roll: RollPayload,
    event_roll: RollPayload,
    target: CharacterSheet,
    event: ResolutionEvent,
    ignored: set[str],
    response_rolls: list[RollPayload],
    sheets: list[CharacterSheet],
    action_source: CharacterSheet | None,
    event_source: CharacterSheet | None,
) -> ResolutionInterceptorPrompt | None:
    if event.eventType == ResolutionEventType.CONDITION_PENDING:
        return _condition_prompt(
            source_roll,
            event_roll,
            target,
            ignored,
            response_rolls,
            event_source,
        )
    if event.eventType == ResolutionEventType.DAMAGE_PENDING:
        return _damage_prompt(
            source_roll,
            event_roll,
            target,
            ignored,
            response_rolls,
            sheets,
            event_source,
        )
    if event.eventType == ResolutionEventType.SAVE_ROLLED and event.rollOutcome == RollOutcome.FAILURE:
        return _failed_save_prompt(
            source_roll,
            event_roll,
            target,
            ignored,
            response_rolls,
            event_source,
        )
    if event.eventType == ResolutionEventType.ATTACK_ROLLED:
        return _attack_prompt(
            source_roll,
            event_roll,
            target,
            ignored,
            response_rolls,
            sheets,
            event_source,
        )
    if event.eventType == ResolutionEventType.SPELL_DECLARED:
        return _spell_cancellation_prompt(
            source_roll,
            target,
            ignored,
            response_rolls,
            sheets,
            action_source,
        )
    if event.eventType in {ResolutionEventType.TURN_STARTED, ResolutionEventType.TURN_ENDED}:
        return _turn_boundary_prompt(
            source_roll,
            event_roll,
            target,
            event.eventType,
            ignored,
            response_rolls,
            sheets,
            event_source,
        )
    return None


def _turn_boundary_prompt(
    source_roll: RollPayload,
    pending_roll: RollPayload,
    target: CharacterSheet,
    event_type: ResolutionEventType,
    ignored: set[str],
    response_rolls: list[RollPayload],
    sheets: list[CharacterSheet],
    source: CharacterSheet | None,
) -> ResolutionInterceptorPrompt | None:
    for owner in sheets:
        for interaction_source in matching_sheet_interactions(
            owner,
            event_type,
            pending_roll,
            source_sheet=source,
            target=target,
        ):
            interceptor_type = interceptor_type_for_interaction(interaction_source.interaction)
            if interceptor_type is None:
                continue
            key = resolution_interceptor_key_for(interceptor_type, owner.id, interaction_source.label)
            if key in ignored:
                continue
            return _prompt(
                interceptor_type=interceptor_type,
                trigger=ResolutionInterceptorTrigger.BEFORE_TURN_BOUNDARY,
                source_roll=source_roll,
                pending_roll=pending_roll,
                target=target,
                owner=owner,
                interaction_source=interaction_source,
                description=f"{enum_label(event_type)} is resolving for {target.name}.",
                ignored=ignored,
                response_rolls=response_rolls,
            )
    return None


def _spell_cancellation_prompt(
    source_roll: RollPayload,
    target: CharacterSheet,
    ignored: set[str],
    response_rolls: list[RollPayload],
    sheets: list[CharacterSheet],
    source: CharacterSheet | None,
) -> ResolutionInterceptorPrompt | None:
    if source_roll.source.section != SheetSectionType.SPELLS:
        return None
    for sheet in sheets:
        if source is not None and sheet.id == source.id:
            continue
        for interaction_source in matching_sheet_interactions(
            sheet,
            ResolutionEventType.SPELL_DECLARED,
            source_roll,
            source_sheet=source,
            target=target,
        ):
            interceptor_type = interceptor_type_for_interaction(interaction_source.interaction)
            if interceptor_type != ResolutionInterceptorType.CANCEL_ACTION:
                continue
            key = resolution_interceptor_key_for(interceptor_type, sheet.id, interaction_source.label)
            if key in ignored:
                continue
            return _prompt(
                interceptor_type=interceptor_type,
                trigger=ResolutionInterceptorTrigger.BEFORE_SPELL_RESOLVES,
                source_roll=source_roll,
                pending_roll=source_roll,
                target=target,
                owner=sheet,
                interaction_source=interaction_source,
                description=f"{source_roll.sourceLabel} is about to resolve against {target.name}.",
                ignored=ignored,
                response_rolls=response_rolls,
            )
    return None


def _condition_prompt(
    source_roll: RollPayload,
    pending_roll: RollPayload,
    target: CharacterSheet,
    ignored: set[str],
    response_rolls: list[RollPayload],
    source: CharacterSheet | None,
) -> ResolutionInterceptorPrompt | None:
    if not added_condition_types(pending_roll.pendingEffect):
        return None
    interaction_source = next(
        (
            candidate
            for candidate in matching_sheet_interactions(
                target,
                ResolutionEventType.CONDITION_PENDING,
                pending_roll,
                source_sheet=source,
                target=target,
            )
            if candidate.interaction.decision.decisionType == InteractionDecisionType.PROMPT
            and interceptor_type_for_interaction(candidate.interaction) is not None
            and resolution_interceptor_key_for(
                interceptor_type_for_interaction(candidate.interaction),
                target.id,
                candidate.label,
            )
            not in ignored
        ),
        None,
    )
    if interaction_source is None:
        return None
    interceptor_type = interceptor_type_for_interaction(interaction_source.interaction)
    assert interceptor_type is not None
    return _prompt(
        interceptor_type=interceptor_type,
        trigger=ResolutionInterceptorTrigger.BEFORE_CONDITION_APPLIED,
        source_roll=source_roll,
        pending_roll=pending_roll,
        target=target,
        owner=target,
        interaction_source=interaction_source,
        description=f"{source_roll.sourceLabel} is about to apply a condition to {target.name}.",
        ignored=ignored,
        response_rolls=response_rolls,
    )


def _failed_save_prompt(
    source_roll: RollPayload,
    pending_roll: RollPayload,
    target: CharacterSheet,
    ignored: set[str],
    response_rolls: list[RollPayload],
    source: CharacterSheet | None,
) -> ResolutionInterceptorPrompt | None:
    saving_throw = _failed_save_ability(pending_roll)
    save_dc = _failed_save_dc(pending_roll)
    if saving_throw is None or save_dc is None:
        return None
    for interaction_source in matching_sheet_interactions(
        target,
        ResolutionEventType.SAVE_ROLLED,
        pending_roll,
        source_sheet=source,
        target=target,
    ):
        interceptor_type = interceptor_type_for_interaction(interaction_source.interaction)
        if interceptor_type is None:
            continue
        key = resolution_interceptor_key_for(interceptor_type, target.id, interaction_source.label)
        if key in ignored:
            continue
        return _prompt(
            interceptor_type=interceptor_type,
            trigger=ResolutionInterceptorTrigger.BEFORE_FAILED_SAVE_FINALIZES,
            source_roll=source_roll,
            pending_roll=pending_roll,
            target=target,
            owner=target,
            interaction_source=interaction_source,
            description=f"{target.name} failed a DC {save_dc} {enum_label(saving_throw)} save.",
            ignored=ignored,
            response_rolls=response_rolls,
            use_label=_failed_save_use_label(interceptor_type),
        )
    return None


def _attack_prompt(
    source_roll: RollPayload,
    pending_roll: RollPayload,
    target: CharacterSheet,
    ignored: set[str],
    response_rolls: list[RollPayload],
    sheets: list[CharacterSheet],
    source: CharacterSheet | None,
) -> ResolutionInterceptorPrompt | None:
    if pending_roll.resolution != RollResolutionMode.ATTACK_VS_ARMOR_CLASS:
        return None
    for owner in sheets:
        for interaction_source in matching_sheet_interactions(
            owner,
            ResolutionEventType.ATTACK_ROLLED,
            pending_roll,
            source_sheet=source,
            target=target,
        ):
            if (
                source is not None
                and owner.id == source.id
                and not any(
                    isinstance(predicate, SourceIsOwnerPredicate) and predicate.expected
                    for predicate in interaction_source.interaction.predicates
                )
            ):
                continue
            interceptor_type = interceptor_type_for_interaction(interaction_source.interaction)
            if interceptor_type != ResolutionInterceptorType.MODIFY_ROLL:
                continue
            key = resolution_interceptor_key_for(interceptor_type, owner.id, interaction_source.label)
            if key in ignored:
                continue
            return _prompt(
                interceptor_type=interceptor_type,
                trigger=ResolutionInterceptorTrigger.BEFORE_ATTACK_RESOLVES,
                source_roll=source_roll,
                pending_roll=pending_roll,
                target=target,
                owner=owner,
                interaction_source=interaction_source,
                description=f"{source_roll.sourceLabel} is about to resolve against {target.name}.",
                ignored=ignored,
                response_rolls=response_rolls,
            )
    return None


def _damage_prompt(
    source_roll: RollPayload,
    pending_roll: RollPayload,
    target: CharacterSheet,
    ignored: set[str],
    response_rolls: list[RollPayload],
    sheets: list[CharacterSheet],
    source: CharacterSheet | None,
) -> ResolutionInterceptorPrompt | None:
    if not roll_can_apply_damage(pending_roll):
        return None
    match = next(
        (
            (owner, interaction_source)
            for owner in sheets
            if source is None or owner.id != source.id
            for interaction_source in matching_sheet_interactions(
                owner,
                ResolutionEventType.DAMAGE_PENDING,
                pending_roll,
                source_sheet=source,
                target=target,
            )
            if interceptor_type_for_interaction(interaction_source.interaction)
            == ResolutionInterceptorType.MODIFY_PENDING_DAMAGE
            and resolution_interceptor_key_for(
                ResolutionInterceptorType.MODIFY_PENDING_DAMAGE,
                owner.id,
                interaction_source.label,
            )
            not in ignored
        ),
        None,
    )
    if match is None:
        return None
    owner, interaction_source = match
    stable_amount = next(
        (
            entry.amount
            for entry in (
                pending_roll.effectInputs.amounts
                if pending_roll.effectInputs is not None
                else []
            )
            if entry.effectNodeId == EffectNodeId(())
        ),
        None,
    )
    if stable_amount is not None and stable_amount <= 0:
        return None
    return _prompt(
        interceptor_type=ResolutionInterceptorType.MODIFY_PENDING_DAMAGE,
        trigger=ResolutionInterceptorTrigger.BEFORE_DAMAGE_APPLIED,
        source_roll=source_roll,
        pending_roll=pending_roll,
        target=target,
        owner=owner,
        interaction_source=interaction_source,
        description=f"{target.name} is about to take damage.",
        ignored=ignored,
        response_rolls=response_rolls,
    )


def _prompt(
    *,
    interceptor_type: ResolutionInterceptorType,
    trigger: ResolutionInterceptorTrigger,
    source_roll: RollPayload,
    pending_roll: RollPayload,
    target: CharacterSheet,
    owner: CharacterSheet,
    interaction_source: SheetInteractionSource,
    description: str,
    ignored: set[str],
    response_rolls: list[RollPayload],
    use_label: str | None = None,
) -> ResolutionInterceptorPrompt:
    return ResolutionInterceptorPrompt(
        id=f"prompt-{time_ns()}",
        interceptorType=interceptor_type,
        trigger=trigger,
        sourceRoll=source_roll,
        pendingRoll=pending_roll,
        targetSheetId=target.id,
        targetTokenId=target.tokenId,
        targetName=target.name,
        ownerSheetId=owner.id,
        ownerTokenId=owner.tokenId,
        ownerName=owner.name,
        ownerPlayerKey=owner.owner,
        label=interaction_source.label,
        description=description,
        useLabel=use_label or f"Use {interaction_source.label}",
        declineLabel="Decline",
        createdAt=time_ns(),
        interaction=interaction_source.interaction,
        ignoredInterceptors=list(ignored),
        responseRolls=response_rolls or None,
    )


def sheet_interaction_sources(sheet: CharacterSheet) -> list[SheetInteractionSource]:
    sources: list[SheetInteractionSource] = []

    def add_mechanics(label: str, mechanics) -> None:
        if mechanics is not None:
            sources.extend(
                SheetInteractionSource(label, interaction)
                for interaction in mechanics.interactions
            )

    seen_spells: set[SpellId] = set()
    for spell in [*sheet.spells, *sheet.spellbook]:
        if spell.id in seen_spells:
            continue
        seen_spells.add(spell.id)
        add_mechanics(enum_label(spell.name), spell.mechanics)
    for feature in sheet.features:
        add_mechanics(feature.name, feature.mechanics)
        for action in feature.rollActions or []:
            add_mechanics(enum_label(action.name), action.mechanics)
    for ability in sheet.abilities:
        add_mechanics(ability.name, ability.mechanics)
        for action in ability.rollActions or []:
            add_mechanics(enum_label(action.name), action.mechanics)
    for resource in sheet.resources:
        if resource.currentUses <= 0:
            continue
        add_mechanics(resource.name, resource.mechanics)
        for action in resource.rollActions or []:
            add_mechanics(enum_label(action.name), action.mechanics)
    for attack in sheet.attacks:
        add_mechanics(attack.name, attack.mechanics)
    for condition, ongoing_effect in condition_ongoing_effects(
        sheet.conditions,
        sheet.suppressedConditions,
    ):
        sources.extend(
            SheetInteractionSource(enum_label(condition), interaction)
            for interaction in ongoing_effect.interactions
        )
    for active in sheet.ongoingEffects:
        sources.extend(
            SheetInteractionSource(active.sourceLabel, interaction)
            for interaction in active.effect.interactions
        )
    return sources


def matching_sheet_interactions(
    sheet: CharacterSheet,
    event_type: ResolutionEventType,
    roll: RollPayload,
    *,
    source_sheet: CharacterSheet | None = None,
    target: CharacterSheet | None = None,
) -> list[SheetInteractionSource]:
    return [
        interaction_source
        for interaction_source in sheet_interaction_sources(sheet)
        if interaction_source.interaction.trigger == event_type
        and _interaction_predicates_match(
            interaction_source.interaction,
            sheet,
            roll,
            source=source_sheet,
            target=target,
        )
    ]


def interceptor_type_for_interaction(
    interaction: Interaction,
) -> ResolutionInterceptorType | None:
    operation_types = (
        (CancelPendingAction, ResolutionInterceptorType.CANCEL_ACTION),
        (RerollSavingThrow, ResolutionInterceptorType.REROLL_SAVING_THROW),
        (ReplaceRollOutcome, ResolutionInterceptorType.REPLACE_ROLL_OUTCOME),
        (ModifyPendingDamage, ResolutionInterceptorType.MODIFY_PENDING_DAMAGE),
        (ModifyRoll, ResolutionInterceptorType.MODIFY_ROLL),
        (PreventCondition, ResolutionInterceptorType.PREVENT_CONDITION),
        (ModifyAction, ResolutionInterceptorType.MODIFY_ACTION),
        (ApplyEffectOperation, ResolutionInterceptorType.APPLY_EFFECT),
        (ScheduleEffectOperation, ResolutionInterceptorType.SCHEDULE_EFFECT),
    )
    return next(
        (
            interceptor_type
            for operation_type, interceptor_type in operation_types
            if any(isinstance(operation, operation_type) for operation in interaction.operations)
        ),
        None,
    )


def resolution_interceptor_key_for(
    interceptor_type: ResolutionInterceptorType,
    owner_sheet_id: str,
    label: str,
) -> str:
    return f"{enum_key(interceptor_type)}:{owner_sheet_id}:{sanitize_identifier(label)}"


def roll_can_apply_damage(roll: RollPayload) -> bool:
    if roll.resolution == RollResolutionMode.APPLY_DAMAGE:
        return True
    return roll.pendingEffect is not None and first_damage_effect(roll.pendingEffect) is not None


def _interaction_predicates_match(
    interaction: Interaction,
    owner: CharacterSheet,
    roll: RollPayload,
    *,
    source: CharacterSheet | None,
    target: CharacterSheet | None,
) -> bool:
    context = CharacterEffectExecutionContext(roll, target or owner, source, owner=owner)
    return context.evaluate_predicates(EffectNodeId(()), interaction.predicates)


def _failed_save_use_label(interceptor_type: ResolutionInterceptorType) -> str:
    if interceptor_type == ResolutionInterceptorType.REROLL_SAVING_THROW:
        return "Reroll"
    if interceptor_type == ResolutionInterceptorType.REPLACE_ROLL_OUTCOME:
        return "Succeed Instead"
    return "Use"


def _failed_save_ability(roll: RollPayload) -> AbilityType | None:
    return roll.damageSavingThrow if roll.damageSaveSucceeded is False else None


def _failed_save_dc(roll: RollPayload) -> int | None:
    return roll.damageSaveDc if roll.damageSaveSucceeded is False else None
