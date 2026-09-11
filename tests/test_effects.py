from dataclasses import replace

import pytest

from dnd_board.character_sheet import (
    AbilityType,
    AttackAction,
    ConditionType,
    DamageType,
    DiceType,
    SkillType,
    SpellComponent,
    SpellId,
    SpellSource,
    SpellStatus,
    TokenKind,
    build_character_sheet,
    build_damage_roll_payload,
    build_spell_damage_roll_payload,
    typed_json_from_value,
    typed_json_to_value,
)
from dnd_board.rules.shared.character_effects import (
    CharacterEffectExecutionContext,
    advance_character_effect_execution,
    execute_pending_character_effect,
    start_character_effect_execution,
)
from dnd_board.rules.shared.effects import (
    ActiveOngoingEffect,
    AbilityCheck,
    AmountCalculation,
    AppliedEffect,
    AppliedEffectResult,
    ApplyEffect,
    ApplyEffectOperation,
    AttackRoll,
    AttackRollEffect,
    AttackRollType,
    AttackerIsVisiblePredicate,
    BoundEffect,
    CalculatedAmount,
    CalculationType,
    CancelPendingAction,
    ChoiceEffect,
    ContestedCheck,
    ContestedCheckEffect,
    ConditionChangeEffect,
    ConditionOperation,
    CollectionOperation,
    DamageEffect,
    DamageDefenseEffect,
    DamageDefenseType,
    DerivedAmount,
    DiceAmount,
    DifficultyClass,
    DifficultyClassType,
    EffectChoice,
    EffectAmountInput,
    EffectDuration,
    EffectDurationType,
    EffectEngine,
    EffectExecutionResult,
    EffectExecutionStatus,
    ResolutionEventResponse,
    EffectInteractionPort,
    EffectNode,
    EffectNodeId,
    EffectParticipantBindings,
    EffectResolutionInputs,
    EffectRollInput,
    EffectResultValue,
    EffectTarget,
    EndingCondition,
    EndingConditionType,
    FeatureMechanics,
    FixedAmount,
    HealingEffect,
    InstallOngoingEffect,
    InstanceScaling,
    Interaction,
    InteractionDecision,
    InteractionDecisionType,
    InteractionTiming,
    Modifier,
    ModifierOperation,
    ModifyPendingDamage,
    OngoingEffect,
    OngoingEffectId,
    PendingDamageModificationType,
    PendingEffectAddsConditionPredicate,
    PendingResolution,
    PendingResolutionStatus,
    PromptResponder,
    PreventCondition,
    RepeatedEffect,
    ReplaceRollOutcome,
    ResolutionEvent,
    ResolutionEventType,
    ResolutionId,
    RollOutcome,
    SavingThrow,
    SavingThrowEffect,
    ScalingBasis,
    ScheduledEffect,
    ActiveScheduledEffect,
    ScheduledEffectId,
    OccurrenceLimit,
    dispatch_scheduled_effects,
    recurring_effects_for_event,
    SequenceEffect,
    SourceHasComponentPredicate,
    TargetHasConditionPredicate,
    TemporaryHitPointsEffect,
    apply_interaction_operations,
    multiplied_damage_effect,
)
from dnd_board.rules.spells import spell_entry


class RecordingExecutionPort:
    def __init__(self) -> None:
        self.saveOutcome = RollOutcome.FAILURE
        self.attackOutcome = RollOutcome.HIT
        self.predicatesMatch = True
        self.applied: list[AppliedEffectResult] = []
        self.scheduled: list[ScheduledEffect] = []
        self.ongoing: list[OngoingEffect] = []
        self.bindings: EffectParticipantBindings | None = None
        self.appliedBindings: list[EffectParticipantBindings | None] = []

    def bind_participants(self, bindings: EffectParticipantBindings | None) -> None:
        self.bindings = bindings

    def prepare_effect(
        self,
        node_id: EffectNodeId,
        effect: EffectNode,
        owning_attack_node_id: EffectNodeId | None,
    ) -> EffectNode:
        return effect

    def apply_effect(self, node_id: EffectNodeId, effect: AppliedEffect, previous_results: list[AppliedEffectResult]) -> AppliedEffectResult:
        self.appliedBindings.append(self.bindings)
        amount = None
        if isinstance(effect, DamageEffect) and isinstance(effect.amount, FixedAmount):
            amount = effect.amount.value * effect.multiplierNumerator // effect.multiplierDenominator
        elif isinstance(effect, HealingEffect) and isinstance(effect.amount, DerivedAmount):
            source_amount = next(result.amount for result in reversed(previous_results) if result.amount is not None)
            amount = source_amount * effect.amount.numerator // effect.amount.denominator
        result = AppliedEffectResult(effect=effect, amount=amount, effectNodeId=node_id)
        self.applied.append(result)
        return result

    def resolve_saving_throw(self, node_id: EffectNodeId, saving_throw: SavingThrow) -> RollOutcome:
        return self.saveOutcome

    def resolve_attack_roll(self, node_id: EffectNodeId, attack: AttackRoll) -> RollOutcome:
        return self.attackOutcome

    def resolve_contested_check(self, node_id: EffectNodeId, contest: ContestedCheck) -> RollOutcome:
        return self.saveOutcome

    def record_roll_outcome(self, node_id: EffectNodeId, effect: EffectNode, outcome: RollOutcome) -> None:
        return None

    def evaluate_predicates(self, node_id: EffectNodeId, predicates) -> bool:
        return self.predicatesMatch

    def resolve_instance_count(self, instances: InstanceScaling) -> int:
        return instances.baseInstances + instances.additionalInstances

    def choose_effects(self, choice: ChoiceEffect) -> list[EffectNode]:
        return [entry.effect for entry in choice.choices[: choice.maximum]]

    def schedule_effect(self, node_id: EffectNodeId, effect: ScheduledEffect) -> None:
        self.scheduled.append(effect)

    def install_ongoing_effect(self, node_id: EffectNodeId, effect: OngoingEffect) -> None:
        self.ongoing.append(effect)


def default_test_event_response(event: ResolutionEvent) -> ResolutionEventResponse:
    if event.eventType in {
        ResolutionEventType.ATTACK_ROLLED,
        ResolutionEventType.SAVE_ROLLED,
        ResolutionEventType.CHECK_ROLLED,
    }:
        assert event.rollOutcome is not None
        return ResolutionEventResponse(rollOutcome=event.rollOutcome)
    if event.eventType in {
        ResolutionEventType.DAMAGE_APPLIED,
        ResolutionEventType.CONDITION_APPLIED,
        ResolutionEventType.EFFECT_COMMITTED,
        ResolutionEventType.REST_COMPLETED,
    }:
        return ResolutionEventResponse()
    return ResolutionEventResponse(pendingEffect=event.pendingEffect)


def test_resumable_engine_executes_bound_child_with_its_own_participants() -> None:
    root_bindings = EffectParticipantBindings("source-a", "target-a", "source-a")
    child_bindings = EffectParticipantBindings("source-b", "target-b", "source-b")
    root = ApplyEffect(DamageEffect(FixedAmount(3), DamageType.FIRE))
    child = ApplyEffect(DamageEffect(FixedAmount(2), DamageType.COLD))
    engine = EffectEngine()
    execution = engine.start(root, bindings=root_bindings)
    context = RecordingExecutionPort()
    response = None
    child_injected = False

    while True:
        advanced = engine.advance(execution, context, response)
        response = None
        if isinstance(advanced, EffectExecutionResult):
            break
        response = default_test_event_response(advanced)
        if not child_injected:
            response = replace(response, boundEffects=[BoundEffect(child, child_bindings)])
            child_injected = True

    assert context.appliedBindings == [child_bindings, root_bindings]


class UncannyDodgeInteractions(EffectInteractionPort):
    def __init__(self, cancel: bool = False) -> None:
        self.cancel = cancel
        self.beforeEvents: list[ResolutionEvent] = []
        self.rollEvents: list[ResolutionEvent] = []
        self.afterEvents: list[ResolutionEvent] = []

    def before_effect(self, event: ResolutionEvent) -> EffectNode | None:
        self.beforeEvents.append(event)
        if self.cancel:
            return None
        if event.eventType == ResolutionEventType.DAMAGE_PENDING:
            return multiplied_damage_effect(event.pendingEffect, 1, 2)
        return event.pendingEffect

    def after_roll(self, event: ResolutionEvent) -> RollOutcome:
        self.rollEvents.append(event)
        assert event.rollOutcome is not None
        return event.rollOutcome

    def after_effect(self, event: ResolutionEvent, result: EffectExecutionResult) -> None:
        self.afterEvents.append(event)


def test_recursive_effect_engine_resolves_save_sequence_and_derived_healing() -> None:
    damage = ApplyEffect(DamageEffect(FixedAmount(13), DamageType.NECROTIC))
    effect = SavingThrowEffect(
        savingThrow=SavingThrow(
            ability=AbilityType.CONSTITUTION,
            difficultyClass=DifficultyClass(DifficultyClassType.SOURCE_SPELL_SAVE_DC),
        ),
        onFailure=SequenceEffect(
            [
                damage,
                ApplyEffect(
                    HealingEffect(
                        DerivedAmount(EffectResultValue.DAMAGE_APPLIED, numerator=1, denominator=2),
                        target=EffectTarget.SOURCE,
                    )
                ),
            ]
        ),
        onSuccess=ApplyEffect(replace(damage.effect, multiplierNumerator=1, multiplierDenominator=2)),
    )
    port = RecordingExecutionPort()

    result = EffectEngine().resolve(effect, port)

    assert result.status == EffectExecutionStatus.COMPLETED
    assert [applied.amount for applied in result.appliedEffects] == [13, 6]

    port.saveOutcome = RollOutcome.SUCCESS
    assert [applied.amount for applied in EffectEngine().resolve(effect, port).appliedEffects] == [6]


def test_effect_engine_resolves_contested_check_branch() -> None:
    effect = ContestedCheckEffect(
        contest=ContestedCheck(
            sourceCheck=AbilityCheck(AbilityType.STRENGTH, SkillType.ATHLETICS),
            targetChecks=[
                AbilityCheck(AbilityType.STRENGTH, SkillType.ATHLETICS),
                AbilityCheck(AbilityType.DEXTERITY, SkillType.ACROBATICS),
            ],
        ),
        onSourceWin=ApplyEffect(ConditionChangeEffect(ConditionType.GRAPPLED, ConditionOperation.ADD)),
    )
    port = RecordingExecutionPort()
    port.saveOutcome = RollOutcome.SUCCESS

    result = EffectEngine().resolve(effect, port)

    assert [applied.effect.condition for applied in result.appliedEffects] == [ConditionType.GRAPPLED]
    port.saveOutcome = RollOutcome.FAILURE
    assert EffectEngine().resolve(effect, port).appliedEffects == []


def test_effect_engine_resolves_attack_repeat_choice_schedule_and_ongoing_nodes() -> None:
    damage = ApplyEffect(DamageEffect(FixedAmount(4), DamageType.FORCE))
    scheduled = ScheduledEffect(ResolutionEventType.TURN_ENDED, damage)
    ongoing = OngoingEffect(
        duration=EffectDuration(EffectDurationType.CONCENTRATION),
        recurringEffects=[scheduled],
        endingConditions=[EndingCondition(EndingConditionType.SOURCE_CONCENTRATION_ENDS)],
    )
    effect = AttackRollEffect(
        attack=AttackRoll(AttackRollType.SPELL, AbilityType.INTELLIGENCE),
        onHit=SequenceEffect(
            [
                RepeatedEffect(InstanceScaling(2, additionalInstances=1), damage),
                ChoiceEffect(
                    choices=[
                        EffectChoice(ConditionType.PRONE, ApplyEffect(ConditionChangeEffect(ConditionType.PRONE, ConditionOperation.ADD))),
                        EffectChoice(ConditionType.BLINDED, ApplyEffect(ConditionChangeEffect(ConditionType.BLINDED, ConditionOperation.ADD))),
                    ]
                ),
                scheduled,
                InstallOngoingEffect(ongoing),
            ]
        ),
    )
    port = RecordingExecutionPort()

    result = EffectEngine().resolve(effect, port)

    assert result.status == EffectExecutionStatus.COMPLETED
    assert len(result.appliedEffects) == 4
    assert len(port.scheduled) == 1
    assert port.ongoing == [ongoing]

    port.attackOutcome = RollOutcome.MISS
    assert EffectEngine().resolve(effect, port).appliedEffects == []


def test_interaction_hook_can_transform_or_cancel_pending_damage() -> None:
    effect = ApplyEffect(DamageEffect(FixedAmount(13), DamageType.SLASHING))
    port = RecordingExecutionPort()
    interactions = UncannyDodgeInteractions()

    result = EffectEngine(interactions).resolve(effect, port)

    assert [applied.amount for applied in result.appliedEffects] == [6]
    assert interactions.beforeEvents[0].eventType == ResolutionEventType.DAMAGE_PENDING
    assert interactions.afterEvents[0].eventType == ResolutionEventType.DAMAGE_APPLIED
    assert interactions.afterEvents[0].resolutionId == interactions.beforeEvents[0].resolutionId

    cancelled = EffectEngine(UncannyDodgeInteractions(cancel=True)).resolve(effect, RecordingExecutionPort())
    assert cancelled.status == EffectExecutionStatus.CANCELLED
    assert cancelled.appliedEffects == []


def test_interaction_hook_can_replace_a_failed_save_before_branching() -> None:
    class MageSlayerInteractions(UncannyDodgeInteractions):
        def before_effect(self, event: ResolutionEvent) -> EffectNode | None:
            self.beforeEvents.append(event)
            return event.pendingEffect

        def after_roll(self, event: ResolutionEvent) -> RollOutcome:
            self.rollEvents.append(event)
            if event.eventType == ResolutionEventType.SAVE_ROLLED and event.rollOutcome == RollOutcome.FAILURE:
                return RollOutcome.SUCCESS
            assert event.rollOutcome is not None
            return event.rollOutcome

    effect = SavingThrowEffect(
        SavingThrow(
            AbilityType.INTELLIGENCE,
            DifficultyClass(DifficultyClassType.SOURCE_SPELL_SAVE_DC),
        ),
        onFailure=ApplyEffect(DamageEffect(FixedAmount(10), DamageType.PSYCHIC)),
        onSuccess=ApplyEffect(DamageEffect(FixedAmount(5), DamageType.PSYCHIC)),
    )
    interactions = MageSlayerInteractions()

    result = EffectEngine(interactions).resolve(effect, RecordingExecutionPort())

    assert [applied.amount for applied in result.appliedEffects] == [5]
    assert interactions.rollEvents[0].eventType == ResolutionEventType.SAVE_ROLLED


def test_effect_execution_resumes_nested_roll_without_replaying_committed_siblings() -> None:
    effect = SequenceEffect([
        ApplyEffect(DamageEffect(FixedAmount(3), DamageType.FIRE)),
        SavingThrowEffect(
            SavingThrow(AbilityType.DEXTERITY, DifficultyClass(DifficultyClassType.FIXED, fixedValue=12)),
            onFailure=ApplyEffect(DamageEffect(FixedAmount(7), DamageType.COLD)),
        ),
    ])
    context = RecordingExecutionPort()
    engine = EffectEngine()
    execution = engine.start(effect)
    response = None
    save_event = None

    while save_event is None:
        advanced = engine.advance(execution, context, response)
        response = None
        assert not isinstance(advanced, EffectExecutionResult)
        if advanced.eventType == ResolutionEventType.SAVE_ROLLED:
            save_event = advanced
        elif advanced.eventType in {
            ResolutionEventType.DAMAGE_APPLIED,
            ResolutionEventType.CONDITION_APPLIED,
            ResolutionEventType.EFFECT_COMMITTED,
            ResolutionEventType.REST_COMPLETED,
        }:
            response = ResolutionEventResponse()
        else:
            response = ResolutionEventResponse(pendingEffect=advanced.pendingEffect)

    assert [result.amount for result in execution.appliedEffects] == [3]
    assert engine.advance(execution, context) == save_event
    response = ResolutionEventResponse(rollOutcome=RollOutcome.FAILURE)
    while True:
        advanced = engine.advance(execution, context, response)
        response = None
        if isinstance(advanced, EffectExecutionResult):
            result = advanced
            break
        response = (
            ResolutionEventResponse()
            if advanced.eventType in {
                ResolutionEventType.DAMAGE_APPLIED,
                ResolutionEventType.CONDITION_APPLIED,
                ResolutionEventType.EFFECT_COMMITTED,
                ResolutionEventType.REST_COMPLETED,
            }
            else ResolutionEventResponse(pendingEffect=advanced.pendingEffect)
        )

    assert result.status == EffectExecutionStatus.COMPLETED
    assert [applied.amount for applied in result.appliedEffects] == [3, 7]


def test_effect_execution_runs_interaction_effect_as_nested_execution_before_resuming_event() -> None:
    root = ApplyEffect(DamageEffect(FixedAmount(10), DamageType.SLASHING))
    reaction = ApplyEffect(HealingEffect(FixedAmount(4)))
    context = RecordingExecutionPort()
    engine = EffectEngine()
    execution = engine.start(root)

    pending_damage = engine.advance(execution, context)
    assert isinstance(pending_damage, ResolutionEvent)
    assert pending_damage.eventType == ResolutionEventType.DAMAGE_PENDING

    pending_reaction = engine.advance(
        execution,
        context,
        ResolutionEventResponse(pendingEffect=root, additionalEffects=[reaction]),
    )
    assert isinstance(pending_reaction, ResolutionEvent)
    assert pending_reaction.eventType == ResolutionEventType.EFFECT_PENDING
    assert pending_reaction.effectNodeId == EffectNodeId((-1, 0))

    response = ResolutionEventResponse(pendingEffect=reaction)
    while True:
        advanced = engine.advance(execution, context, response)
        response = None
        if isinstance(advanced, EffectExecutionResult):
            result = advanced
            break
        response = (
            ResolutionEventResponse()
            if advanced.eventType in {
                ResolutionEventType.DAMAGE_APPLIED,
                ResolutionEventType.CONDITION_APPLIED,
                ResolutionEventType.EFFECT_COMMITTED,
                ResolutionEventType.REST_COMPLETED,
            }
            else ResolutionEventResponse(pendingEffect=advanced.pendingEffect)
        )

    assert [type(applied.effect) for applied in result.appliedEffects] == [HealingEffect, DamageEffect]
    assert result.appliedEffects[-1].amount == 10


def test_cancelling_nested_effect_skips_only_that_node() -> None:
    effect = SequenceEffect([
        ApplyEffect(ConditionChangeEffect(ConditionType.PRONE, ConditionOperation.ADD)),
        ApplyEffect(DamageEffect(FixedAmount(5), DamageType.FORCE)),
    ])
    context = RecordingExecutionPort()
    engine = EffectEngine()
    execution = engine.start(effect)
    response = None

    while True:
        advanced = engine.advance(execution, context, response)
        response = None
        if isinstance(advanced, EffectExecutionResult):
            result = advanced
            break
        if advanced.eventType == ResolutionEventType.CONDITION_PENDING:
            response = ResolutionEventResponse(pendingEffect=None)
        elif advanced.eventType in {
            ResolutionEventType.DAMAGE_APPLIED,
            ResolutionEventType.CONDITION_APPLIED,
            ResolutionEventType.EFFECT_COMMITTED,
            ResolutionEventType.REST_COMPLETED,
        }:
            response = ResolutionEventResponse()
        else:
            response = ResolutionEventResponse(pendingEffect=advanced.pendingEffect)

    assert result.status == EffectExecutionStatus.COMPLETED
    assert [type(applied.effect) for applied in result.appliedEffects] == [DamageEffect]


def test_feature_mechanics_with_passive_and_prompted_interaction_round_trips() -> None:
    mechanics = FeatureMechanics(
        activatedEffects=[
            ApplyEffect(
                TemporaryHitPointsEffect(
                    CalculatedAmount(AmountCalculation.SOURCE_CLASS_LEVEL, minimum=1)
                )
            ),
            ContestedCheckEffect(
                ContestedCheck(
                    AbilityCheck(AbilityType.STRENGTH, SkillType.ATHLETICS),
                    [AbilityCheck(AbilityType.DEXTERITY, SkillType.ACROBATICS)],
                ),
                onSourceWin=ApplyEffect(ConditionChangeEffect(ConditionType.GRAPPLED, ConditionOperation.ADD)),
            ),
        ],
        passiveModifiers=[
            Modifier(
                calculation=CalculationType.DAMAGE_ROLL,
                operation=ModifierOperation.ADD,
                amount=FixedAmount(2),
            )
        ],
        interactions=[
            Interaction(
                trigger=ResolutionEventType.DAMAGE_PENDING,
                timing=InteractionTiming.BEFORE_EVENT,
                decision=InteractionDecision(
                    InteractionDecisionType.PROMPT,
                    PromptResponder.OWNER_OR_DM,
                ),
                predicates=[
                    AttackerIsVisiblePredicate(),
                    SourceHasComponentPredicate(SpellComponent.SOMATIC),
                    PendingEffectAddsConditionPredicate(ConditionType.POISONED),
                ],
                operations=[
                    ModifyPendingDamage(PendingDamageModificationType.MULTIPLY, 1, 2),
                    ApplyEffectOperation(
                        ApplyEffect(ConditionChangeEffect(ConditionType.PRONE, ConditionOperation.ADD))
                    ),
                ],
            )
        ],
    )

    assert typed_json_to_value(typed_json_from_value(mechanics), FeatureMechanics) == mechanics


def test_pending_resolution_round_trips_for_future_prompt_persistence() -> None:
    effect = ApplyEffect(DamageEffect(FixedAmount(9), DamageType.THUNDER))
    event = ResolutionEvent(ResolutionId(42), ResolutionEventType.DAMAGE_PENDING, effect)
    pending = PendingResolution(
        resolutionId=event.resolutionId,
        rootEffect=effect,
        status=PendingResolutionStatus.PAUSED,
        currentEvent=event,
        handledInteractionIndexes=[0, 2],
    )

    assert typed_json_to_value(typed_json_from_value(pending), PendingResolution) == pending


def test_effect_model_rejects_invalid_bounds_and_limits_resolution_depth() -> None:
    with pytest.raises(ValueError, match="fixedValue"):
        DifficultyClass(DifficultyClassType.FIXED)
    with pytest.raises(ValueError, match="ability"):
        DifficultyClass(DifficultyClassType.SOURCE_ABILITY)
    with pytest.raises(ValueError, match="denominator"):
        DerivedAmount(EffectResultValue.DAMAGE_APPLIED, denominator=0)
    with pytest.raises(ValueError, match="Choice bounds"):
        ChoiceEffect([], minimum=1, maximum=1)
    with pytest.raises(ValueError, match="positive"):
        EffectEngine(maximumDepth=0)

    nested: EffectNode = ApplyEffect(DamageEffect(FixedAmount(1), DamageType.FIRE))
    for _ in range(4):
        nested = SequenceEffect([nested])

    with pytest.raises(RecursionError, match="maximum resolution depth"):
        EffectEngine(maximumDepth=3).resolve(nested, RecordingExecutionPort())


def test_damage_multiplier_recurses_through_sequences_without_changing_other_effects() -> None:
    damage = ApplyEffect(DamageEffect(FixedAmount(8), DamageType.COLD))
    condition = ApplyEffect(ConditionChangeEffect(ConditionType.PRONE, ConditionOperation.ADD))
    transformed = multiplied_damage_effect(SequenceEffect([damage, condition]), 1, 2)

    assert isinstance(transformed, SequenceEffect)
    transformed_damage = transformed.effects[0]
    assert isinstance(transformed_damage, ApplyEffect)
    assert isinstance(transformed_damage.effect, DamageEffect)
    assert transformed_damage.effect.multiplierNumerator == 1
    assert transformed_damage.effect.multiplierDenominator == 2
    assert transformed.effects[1] == condition

    with pytest.raises(ValueError, match="denominator"):
        multiplied_damage_effect(damage, 1, 0)


def test_declarative_interaction_operations_transform_pending_resolution() -> None:
    damage = ApplyEffect(DamageEffect(FixedAmount(12), DamageType.FORCE))
    prone = ApplyEffect(ConditionChangeEffect(ConditionType.PRONE, ConditionOperation.ADD))
    event = ResolutionEvent(
        resolutionId=ResolutionId(7),
        eventType=ResolutionEventType.DAMAGE_PENDING,
        pendingEffect=SequenceEffect([damage, prone]),
        rollOutcome=RollOutcome.FAILURE,
    )

    result = apply_interaction_operations(
        event,
        [
            ReplaceRollOutcome(RollOutcome.SUCCESS),
            ModifyPendingDamage(PendingDamageModificationType.MULTIPLY, 1, 2),
            PreventCondition([ConditionType.PRONE]),
            ApplyEffectOperation(ApplyEffect(HealingEffect(FixedAmount(2), EffectTarget.SOURCE))),
        ],
    )

    assert result.cancelled is False
    assert result.rollOutcome == RollOutcome.SUCCESS
    assert isinstance(result.pendingEffect, SequenceEffect)
    assert len(result.pendingEffect.effects) == 1
    transformed = result.pendingEffect.effects[0]
    assert isinstance(transformed, ApplyEffect)
    assert isinstance(transformed.effect, DamageEffect)
    assert transformed.effect.multiplierDenominator == 2
    assert len(result.additionalEffects) == 1
    assert event.resolutionId == ResolutionId(7)

    cancelled = apply_interaction_operations(event, [CancelPendingAction()])
    assert cancelled.cancelled is True


def test_weapon_and_burning_hands_define_and_roll_direct_effect_trees() -> None:
    sheet = build_character_sheet(
        token_id="effect-source",
        kind=TokenKind.CHARACTER,
        name="Effect Source",
        owner="player-1",
        avatar_url=None,
        party_member=None,
        current_hp=None,
        resource_overrides={},
    )
    creature_sheet = build_character_sheet(
        token_id="effect-target",
        kind=TokenKind.ASSET,
        name="Effect Target",
        owner="dm",
        avatar_url=None,
        party_member=None,
        current_hp=None,
        resource_overrides={},
    )
    weapon = creature_sheet.attacks[0]
    assert weapon.mechanics is not None
    weapon_effect = weapon.mechanics.activatedEffects[0]

    assert isinstance(weapon_effect, AttackRollEffect)
    assert isinstance(weapon_effect.onHit, ApplyEffect)
    assert isinstance(weapon_effect.onHit.effect, DamageEffect)
    assert weapon_effect.onHit.effect.damageType == DamageType.SLASHING
    weapon_roll = build_damage_roll_payload(creature_sheet, "dm", weapon)
    assert isinstance(weapon_roll.pendingEffect, ApplyEffect)
    assert isinstance(weapon_roll.pendingEffect.effect, DamageEffect)
    assert isinstance(weapon_roll.pendingEffect.effect.amount, FixedAmount)

    burning_hands = spell_entry(SpellId.BURNING_HANDS)
    assert burning_hands is not None
    assert burning_hands.mechanics is not None
    burning_effect = burning_hands.mechanics.activatedEffects[0]
    assert isinstance(burning_effect, SavingThrowEffect)
    assert burning_effect.savingThrow.ability == AbilityType.DEXTERITY
    burning_hands = replace(
        burning_hands,
        status=SpellStatus(SpellSource.WIZARD, AbilityType.INTELLIGENCE),
    )
    burning_roll = replace(
        build_spell_damage_roll_payload(sheet, "player-1", burning_hands, spell_slot_level=2),
        damageSaveSucceeded=True,
    )
    assert isinstance(burning_roll.pendingEffect, SavingThrowEffect)
    assert isinstance(burning_roll.pendingEffect.onSuccess, ApplyEffect)
    assert isinstance(burning_roll.pendingEffect.onSuccess.effect, DamageEffect)
    assert burning_roll.pendingEffect.onSuccess.effect.damageType == DamageType.FIRE
    assert burning_roll.pendingEffect.onSuccess.effect.multiplierDenominator == 2


def test_effect_nodes_receive_independent_typed_paths_and_roll_outcomes() -> None:
    class PerNodeExecutionPort(RecordingExecutionPort):
        def resolve_saving_throw(self, node_id: EffectNodeId, saving_throw: SavingThrow) -> RollOutcome:
            return {
                EffectNodeId((0,)): RollOutcome.SUCCESS,
                EffectNodeId((1,)): RollOutcome.FAILURE,
            }[node_id]

    effect = SequenceEffect([
        SavingThrowEffect(
            SavingThrow(AbilityType.DEXTERITY, DifficultyClass(DifficultyClassType.FIXED, fixedValue=12)),
            onFailure=ApplyEffect(DamageEffect(FixedAmount(9), DamageType.FIRE)),
            onSuccess=ApplyEffect(DamageEffect(FixedAmount(4), DamageType.FIRE)),
        ),
        SavingThrowEffect(
            SavingThrow(AbilityType.WISDOM, DifficultyClass(DifficultyClassType.FIXED, fixedValue=14)),
            onFailure=ApplyEffect(DamageEffect(FixedAmount(7), DamageType.PSYCHIC)),
        ),
    ])

    result = EffectEngine().resolve(effect, PerNodeExecutionPort())

    assert [entry.amount for entry in result.appliedEffects] == [4, 7]
    assert [entry.effectNodeId for entry in result.appliedEffects] == [
        EffectNodeId((0, 1)),
        EffectNodeId((1, 0)),
    ]


def test_effect_resolution_inputs_round_trip_with_typed_node_ids() -> None:
    inputs = EffectResolutionInputs(
        rolls=[EffectRollInput(EffectNodeId((2, 0)), RollOutcome.FAILURE)],
        amounts=[EffectAmountInput(EffectNodeId((2, 0, 0)), 11)],
    )

    assert typed_json_to_value(typed_json_from_value(inputs), EffectResolutionInputs) == inputs


def test_character_execution_uses_per_node_amounts_and_installs_ongoing_effects() -> None:
    target = build_character_sheet(
        token_id="effect-target",
        kind=TokenKind.ASSET,
        name="Target",
        owner="dm",
        avatar_url=None,
        party_member=None,
        current_hp=30,
        resource_overrides={},
    )
    roll = build_damage_roll_payload(target, "dm", target.attacks[0])
    ongoing = OngoingEffect(
        duration=EffectDuration(EffectDurationType.UNTIL_LONG_REST),
        modifiers=[Modifier(CalculationType.ARMOR_CLASS, ModifierOperation.ADD, amount=FixedAmount(2))],
    )
    roll = replace(
        roll,
        pendingEffect=SequenceEffect([
            ApplyEffect(DamageEffect(FixedAmount(1), DamageType.FIRE)),
            ApplyEffect(DamageEffect(FixedAmount(1), DamageType.FIRE)),
            InstallOngoingEffect(ongoing),
            ScheduledEffect(
                ResolutionEventType.TURN_ENDED,
                ApplyEffect(DamageEffect(FixedAmount(2), DamageType.FIRE)),
            ),
        ]),
        effectInputs=EffectResolutionInputs(amounts=[
            EffectAmountInput(EffectNodeId((0,)), 3),
            EffectAmountInput(EffectNodeId((1,)), 7),
        ]),
    )

    resolved = execute_pending_character_effect(roll, target, target)

    assert resolved.hitPoints.current == target.hp.current - 10
    assert len(resolved.ongoingEffects) == 1
    assert resolved.ongoingEffects[0].effect == ongoing
    assert resolved.ongoingEffects[0].id.effectNodeId == EffectNodeId((2,))
    assert len(resolved.scheduledEffects) == 1
    assert resolved.scheduledEffects[0].effect.trigger == ResolutionEventType.TURN_ENDED
    assert resolved.scheduledEffects[0].targetSheetId == target.id


def test_scheduled_and_ongoing_effects_dispatch_for_matching_runtime_event() -> None:
    child = ApplyEffect(DamageEffect(FixedAmount(2), DamageType.FIRE))
    active = ActiveScheduledEffect(
        id=ScheduledEffectId(22, EffectNodeId((1,))),
        sourceSheetId="source",
        targetSheetId="target",
        sourceLabel="Delayed Fire",
        effect=ScheduledEffect(ResolutionEventType.DAMAGE_APPLIED, child, OccurrenceLimit(2)),
        remainingOccurrences=2,
    )

    first = dispatch_scheduled_effects([active], ResolutionEventType.DAMAGE_APPLIED)
    assert [dispatch.effect for dispatch in first.dispatched] == [child]
    assert first.remaining == [replace(active, remainingOccurrences=1)]
    assert dispatch_scheduled_effects(first.remaining, ResolutionEventType.DAMAGE_APPLIED).remaining == []
    assert dispatch_scheduled_effects([active], ResolutionEventType.REST_COMPLETED).dispatched == []
    suppressed = dispatch_scheduled_effects(
        first.remaining,
        ResolutionEventType.DAMAGE_APPLIED,
        {active.id},
    )
    assert suppressed.dispatched == []
    assert suppressed.remaining == first.remaining

    ongoing = ActiveOngoingEffect(
        id=OngoingEffectId(23, EffectNodeId((2,))),
        sourceSheetId="source",
        targetSheetId="target",
        sourceLabel="Recurring Fire",
        effect=OngoingEffect(
            EffectDuration(EffectDurationType.UNTIL_LONG_REST),
            recurringEffects=[ScheduledEffect(ResolutionEventType.DAMAGE_APPLIED, child)],
        ),
    )
    assert [dispatch.effect for dispatch in recurring_effects_for_event([ongoing], ResolutionEventType.DAMAGE_APPLIED)] == [child]


def test_source_healing_updates_shared_state_when_source_is_target() -> None:
    target = build_character_sheet(
        token_id="self-healing-target",
        kind=TokenKind.ASSET,
        name="Target",
        owner="dm",
        avatar_url=None,
        party_member=None,
        current_hp=40,
        resource_overrides={},
    )
    target.hp = replace(target.hp, current=30, max=40)
    roll = replace(
        build_damage_roll_payload(target, "dm", target.attacks[0]),
        pendingEffect=SequenceEffect([
            ApplyEffect(DamageEffect(FixedAmount(10), DamageType.NECROTIC)),
            ApplyEffect(HealingEffect(FixedAmount(10), EffectTarget.SOURCE)),
        ]),
    )

    resolved = execute_pending_character_effect(roll, target, target)

    assert resolved.hitPoints.current == 30
    assert resolved.sourceHitPoints == resolved.hitPoints


def test_character_effect_execution_preserves_working_hit_points_while_paused() -> None:
    target = build_character_sheet(
        token_id="paused-character-effect",
        kind=TokenKind.ASSET,
        name="Target",
        owner="dm",
        avatar_url=None,
        party_member=None,
        current_hp=30,
        resource_overrides={},
    )
    roll = replace(
        build_damage_roll_payload(target, "dm", target.attacks[0]),
        pendingEffect=SequenceEffect([
            ApplyEffect(DamageEffect(FixedAmount(3), DamageType.FIRE)),
            ApplyEffect(DamageEffect(FixedAmount(7), DamageType.COLD)),
        ]),
    )
    active = start_character_effect_execution(roll, target, target)
    response = None

    while active.context.hitPoints.current == target.hp.current:
        event = advance_character_effect_execution(active, response)
        assert isinstance(event, ResolutionEvent)
        response = (
            ResolutionEventResponse()
            if event.eventType in {
                ResolutionEventType.DAMAGE_APPLIED,
                ResolutionEventType.EFFECT_COMMITTED,
            }
            else ResolutionEventResponse(pendingEffect=event.pendingEffect)
        )

    assert active.context.hitPoints.current == target.hp.current - 3
    paused_event = advance_character_effect_execution(active, response)
    assert isinstance(paused_event, ResolutionEvent)
    assert active.context.hitPoints.current == target.hp.current - 3


def test_reaction_changed_branch_requests_unresolved_nested_save() -> None:
    target = build_character_sheet(
        token_id="reaction-save-branch",
        kind=TokenKind.ASSET,
        name="Target",
        owner="dm",
        avatar_url=None,
        party_member=None,
        current_hp=30,
        resource_overrides={},
    )
    second_save = SavingThrowEffect(
        SavingThrow(AbilityType.DEXTERITY, DifficultyClass(DifficultyClassType.FIXED, fixedValue=13)),
        onFailure=ApplyEffect(ConditionChangeEffect(ConditionType.PRONE, ConditionOperation.ADD)),
    )
    root = SavingThrowEffect(
        SavingThrow(AbilityType.WISDOM, DifficultyClass(DifficultyClassType.FIXED, fixedValue=12)),
        onSuccess=second_save,
    )
    roll = replace(
        build_damage_roll_payload(target, "dm", target.attacks[0]),
        pendingEffect=root,
        damageSaveSucceeded=False,
        effectInputs=EffectResolutionInputs(
            rolls=[EffectRollInput(EffectNodeId(()), RollOutcome.FAILURE)],
        ),
    )
    active = start_character_effect_execution(roll, target, target)
    response = None

    while True:
        event = advance_character_effect_execution(active, response)
        assert isinstance(event, ResolutionEvent)
        if event.eventType == ResolutionEventType.SAVE_ROLLED:
            break
        response = default_test_event_response(event)

    assert event.effectNodeId == EffectNodeId(())
    response = ResolutionEventResponse(rollOutcome=RollOutcome.SUCCESS)
    while True:
        event = advance_character_effect_execution(active, response)
        assert isinstance(event, ResolutionEvent)
        if event.eventType == ResolutionEventType.SAVE_ROLLED:
            break
        response = default_test_event_response(event)

    assert event.effectNodeId == EffectNodeId((1,))
    assert event.rollOutcome is None


def test_later_damage_node_uses_defense_granted_by_earlier_node() -> None:
    target = build_character_sheet(
        token_id="defense-sequence-target",
        kind=TokenKind.ASSET,
        name="Target",
        owner="dm",
        avatar_url=None,
        party_member=None,
        current_hp=40,
        resource_overrides={},
    )
    roll = replace(
        build_damage_roll_payload(target, "dm", target.attacks[0]),
        pendingEffect=SequenceEffect([
            ApplyEffect(DamageDefenseEffect(DamageDefenseType.IMMUNITY, DamageType.FIRE, CollectionOperation.ADD)),
            ApplyEffect(DamageEffect(FixedAmount(10), DamageType.FIRE)),
        ]),
    )

    resolved = execute_pending_character_effect(roll, target, target)

    assert resolved.hitPoints == target.hp
    assert DamageType.FIRE in resolved.damageImmunities


def test_spell_builder_addresses_same_type_damage_by_effect_node(monkeypatch) -> None:
    monkeypatch.setattr("dnd_board.character_sheet.random.randint", lambda minimum, maximum: minimum)
    caster = build_character_sheet(
        token_id="node-damage-caster",
        kind=TokenKind.ASSET,
        name="Caster",
        owner="dm",
        avatar_url=None,
        party_member=None,
        current_hp=30,
        resource_overrides={},
    )
    target = replace(caster, id="node-damage-target", tokenId="node-damage-target")
    target.hp = replace(target.hp, current=30, max=30)
    spell = spell_entry(SpellId.FIRE_BOLT)
    assert spell is not None
    spell = replace(
        spell,
        mechanics=FeatureMechanics(activatedEffects=[SequenceEffect([
            ApplyEffect(DamageEffect(FixedAmount(3), DamageType.FIRE)),
            ApplyEffect(DamageEffect(FixedAmount(7), DamageType.FIRE)),
        ])]),
    )

    roll = build_spell_damage_roll_payload(caster, "dm", spell)
    resolved = execute_pending_character_effect(roll, target, caster)

    assert [component.total for component in roll.damageComponents or []] == [3, 7]
    assert [entry.effectNodeId for entry in roll.effectInputs.amounts] == [EffectNodeId((0,)), EffectNodeId((1,))]
    assert resolved.hitPoints.current == 20


def test_suppress_condition_keeps_marker_but_disables_its_mechanics() -> None:
    target = build_character_sheet(
        token_id="suppressed-target",
        kind=TokenKind.ASSET,
        name="Target",
        owner="dm",
        avatar_url=None,
        party_member=None,
        current_hp=None,
        resource_overrides={},
    )
    target.conditions = [ConditionType.FRIGHTENED]
    roll = replace(
        build_damage_roll_payload(target, "dm", target.attacks[0]),
        pendingEffect=ApplyEffect(ConditionChangeEffect(ConditionType.FRIGHTENED, ConditionOperation.SUPPRESS)),
    )

    resolved = execute_pending_character_effect(roll, target, target)

    assert resolved.conditions == [ConditionType.FRIGHTENED]
    assert resolved.suppressedConditions == [ConditionType.FRIGHTENED]

    suppressed_target = replace(
        target,
        suppressedConditions=[ConditionType.FRIGHTENED],
    )
    context = CharacterEffectExecutionContext(roll, suppressed_target, suppressed_target)
    assert not context.evaluate_predicates(
        EffectNodeId(()),
        [TargetHasConditionPredicate(ConditionType.FRIGHTENED)],
    )
