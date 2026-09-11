from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum, auto
from time import time_ns
from typing import Protocol, TypeAlias

from dnd_board.character_sheet import (
    AbilityType,
    AttackDamageAbilityModifierMode,
    AttackKind,
    AttackRangeType,
    ClassType,
    ConditionType,
    CreatureType,
    DamageType,
    DiceType,
    RestType,
    SkillType,
    SpellComponent,
    TimeEconomy,
    WeaponProperty,
    WeaponCategory,
)
from dnd_board.rules.shared.resources import ResourceCost


class EffectTarget(Enum):
    SOURCE = auto()
    TARGET = auto()
    EACH_TARGET = auto()


class EffectResultValue(Enum):
    DAMAGE_ROLLED = auto()
    DAMAGE_APPLIED = auto()
    HEALING_ROLLED = auto()
    HEALING_APPLIED = auto()


class AmountCalculation(Enum):
    SOURCE_ABILITY_MODIFIER = auto()
    SOURCE_SPELLCASTING_MODIFIER = auto()
    SOURCE_CLASS_LEVEL = auto()
    SOURCE_CHARACTER_LEVEL = auto()
    SOURCE_PROFICIENCY_BONUS = auto()
    SOURCE_EQUIPPED_SHIELD_ARMOR_CLASS = auto()


@dataclass(frozen=True)
class FixedAmount:
    value: int


@dataclass(frozen=True)
class DiceAmount:
    diceCount: int
    diceType: DiceType
    staticBonus: int = 0

    def __post_init__(self) -> None:
        if self.diceCount < 0:
            raise ValueError("diceCount cannot be negative")


@dataclass(frozen=True)
class CalculatedAmount:
    calculation: AmountCalculation
    ability: AbilityType | None = None
    characterClass: ClassType | None = None
    multiplier: int = 1
    minimum: int | None = None


@dataclass(frozen=True)
class DerivedAmount:
    result: EffectResultValue
    numerator: int = 1
    denominator: int = 1

    def __post_init__(self) -> None:
        if self.denominator == 0:
            raise ValueError("Derived amount denominator cannot be zero")


BasicEffectAmount: TypeAlias = FixedAmount | DiceAmount | CalculatedAmount | DerivedAmount


@dataclass(frozen=True)
class CombinedAmount:
    amounts: list[BasicEffectAmount]

    def __post_init__(self) -> None:
        if not self.amounts:
            raise ValueError("Combined amount requires at least one amount")


EffectAmount: TypeAlias = BasicEffectAmount | CombinedAmount


class ScalingBasis(Enum):
    CHARACTER_LEVEL = auto()
    CASTER_LEVEL = auto()
    SPELL_SLOT_LEVEL = auto()


@dataclass(frozen=True)
class AmountScaling:
    basis: ScalingBasis
    interval: int
    additionalDice: DiceAmount | None = None
    additionalFixedAmount: int = 0
    thresholds: list[int] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.interval < 1:
            raise ValueError("Scaling interval must be positive")
        if any(level < 1 for level in self.thresholds):
            raise ValueError("Scaling thresholds must be positive")
        if self.thresholds != sorted(set(self.thresholds)):
            raise ValueError("Scaling thresholds must be unique and sorted")


class ConditionOperation(Enum):
    ADD = auto()
    REMOVE = auto()
    SUPPRESS = auto()


class MaximumHitPointsOperation(Enum):
    INCREASE = auto()
    REDUCE = auto()


class DamageDefenseType(Enum):
    RESISTANCE = auto()
    VULNERABILITY = auto()
    IMMUNITY = auto()


class CollectionOperation(Enum):
    ADD = auto()
    REMOVE = auto()


class MovementType(Enum):
    FORCED = auto()
    TELEPORT = auto()


class AppliedEffectKind(Enum):
    DAMAGE = auto()
    HEALING = auto()
    TEMPORARY_HIT_POINTS = auto()
    CONDITION_CHANGE = auto()
    MAXIMUM_HIT_POINTS = auto()
    DAMAGE_DEFENSE = auto()
    REST = auto()
    MOVEMENT = auto()


@dataclass(frozen=True)
class DamageEffect:
    amount: EffectAmount
    damageType: DamageType | None
    target: EffectTarget = EffectTarget.TARGET
    scaling: list[AmountScaling] = field(default_factory=list)
    multiplierNumerator: int = 1
    multiplierDenominator: int = 1
    kind: AppliedEffectKind = field(init=False, default=AppliedEffectKind.DAMAGE)

    def __post_init__(self) -> None:
        if self.multiplierDenominator == 0:
            raise ValueError("Damage multiplier denominator cannot be zero")


@dataclass(frozen=True)
class HealingEffect:
    amount: EffectAmount
    target: EffectTarget = EffectTarget.TARGET
    scaling: list[AmountScaling] = field(default_factory=list)
    kind: AppliedEffectKind = field(init=False, default=AppliedEffectKind.HEALING)


@dataclass(frozen=True)
class TemporaryHitPointsEffect:
    amount: EffectAmount
    target: EffectTarget = EffectTarget.TARGET
    scaling: list[AmountScaling] = field(default_factory=list)
    kind: AppliedEffectKind = field(init=False, default=AppliedEffectKind.TEMPORARY_HIT_POINTS)


@dataclass(frozen=True)
class ConditionChangeEffect:
    condition: ConditionType
    operation: ConditionOperation
    target: EffectTarget = EffectTarget.TARGET
    duration: EffectDuration | None = None
    endingConditions: list[EndingCondition] = field(default_factory=list)
    kind: AppliedEffectKind = field(init=False, default=AppliedEffectKind.CONDITION_CHANGE)


@dataclass(frozen=True)
class MaximumHitPointsEffect:
    amount: EffectAmount
    operation: MaximumHitPointsOperation
    target: EffectTarget = EffectTarget.TARGET
    reset: RestType = RestType.NONE
    scaling: list[AmountScaling] = field(default_factory=list)
    kind: AppliedEffectKind = field(init=False, default=AppliedEffectKind.MAXIMUM_HIT_POINTS)


@dataclass(frozen=True)
class DamageDefenseEffect:
    defense: DamageDefenseType
    damageType: DamageType
    operation: CollectionOperation
    target: EffectTarget = EffectTarget.TARGET
    kind: AppliedEffectKind = field(init=False, default=AppliedEffectKind.DAMAGE_DEFENSE)


@dataclass(frozen=True)
class RestEffect:
    rest: RestType
    target: EffectTarget = EffectTarget.TARGET
    kind: AppliedEffectKind = field(init=False, default=AppliedEffectKind.REST)


@dataclass(frozen=True)
class MovementEffect:
    movementType: MovementType
    distanceFeet: int
    target: EffectTarget = EffectTarget.TARGET
    kind: AppliedEffectKind = field(init=False, default=AppliedEffectKind.MOVEMENT)


AppliedEffect: TypeAlias = (
    DamageEffect
    | HealingEffect
    | TemporaryHitPointsEffect
    | ConditionChangeEffect
    | MaximumHitPointsEffect
    | DamageDefenseEffect
    | RestEffect
    | MovementEffect
)


class DifficultyClassType(Enum):
    FIXED = auto()
    SOURCE_SPELL_SAVE_DC = auto()
    SOURCE_ABILITY = auto()
    SOURCE_BEST_ABILITY = auto()


@dataclass(frozen=True)
class DifficultyClass:
    calculation: DifficultyClassType
    fixedValue: int | None = None
    ability: AbilityType | None = None
    abilities: list[AbilityType] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.calculation == DifficultyClassType.FIXED and self.fixedValue is None:
            raise ValueError("A fixed difficulty class requires fixedValue")
        if self.calculation == DifficultyClassType.SOURCE_ABILITY and self.ability is None:
            raise ValueError("A source-ability difficulty class requires ability")
        if self.calculation == DifficultyClassType.SOURCE_BEST_ABILITY and not self.abilities:
            raise ValueError("A best-ability difficulty class requires abilities")


@dataclass(frozen=True)
class SavingThrow:
    ability: AbilityType
    difficultyClass: DifficultyClass
    disadvantageCreatureTypes: list[CreatureType] = field(default_factory=list)
    forcedFailureCreatureTypes: list[CreatureType] = field(default_factory=list)


class AttackRollType(Enum):
    WEAPON = auto()
    SPELL = auto()


@dataclass(frozen=True)
class AttackRoll:
    attackType: AttackRollType
    ability: AbilityType | None = None


@dataclass(frozen=True)
class AbilityCheck:
    ability: AbilityType
    skill: SkillType | None = None


@dataclass(frozen=True)
class ContestedCheck:
    sourceCheck: AbilityCheck
    targetChecks: list[AbilityCheck]

    def __post_init__(self) -> None:
        if not self.targetChecks:
            raise ValueError("A contested check requires at least one target check")


class RollOutcome(Enum):
    SUCCESS = auto()
    FAILURE = auto()
    HIT = auto()
    MISS = auto()


@dataclass(frozen=True)
class TargetIsOwnerPredicate:
    expected: bool = True


@dataclass(frozen=True)
class SourceIsAttackPredicate:
    pass


@dataclass(frozen=True)
class SourceIsSpellPredicate:
    pass


@dataclass(frozen=True)
class SourceHasComponentPredicate:
    component: SpellComponent


@dataclass(frozen=True)
class TargetHasConditionPredicate:
    condition: ConditionType


@dataclass(frozen=True)
class PendingEffectAddsConditionPredicate:
    condition: ConditionType


@dataclass(frozen=True)
class SourceHasConditionPredicate:
    condition: ConditionType


@dataclass(frozen=True)
class TargetHasCreatureTypePredicate:
    creatureType: CreatureType


@dataclass(frozen=True)
class TargetHasAnyCreatureTypePredicate:
    creatureTypes: list[CreatureType]


@dataclass(frozen=True)
class SavingThrowAbilityPredicate:
    abilities: list[AbilityType]


@dataclass(frozen=True)
class CalculationAbilityPredicate:
    abilities: list[AbilityType]


@dataclass(frozen=True)
class RollOutcomePredicate:
    outcome: RollOutcome


@dataclass(frozen=True)
class WeaponHasPropertyPredicate:
    property: WeaponProperty


@dataclass(frozen=True)
class WeaponHasAnyPropertyPredicate:
    properties: list[WeaponProperty]


@dataclass(frozen=True)
class SourceAttackRangePredicate:
    attackRange: AttackRangeType


@dataclass(frozen=True)
class SourceWeaponCategoryPredicate:
    weaponCategory: WeaponCategory


@dataclass(frozen=True)
class SourceAttackKindPredicate:
    attackKind: AttackKind


@dataclass(frozen=True)
class SourceDamageAbilityModifierPredicate:
    mode: AttackDamageAbilityModifierMode


@dataclass(frozen=True)
class OwnerWieldsExactlyOneOneHandedWeaponPredicate:
    pass


@dataclass(frozen=True)
class OwnerWearsHeavyArmorPredicate:
    expected: bool = True


@dataclass(frozen=True)
class OwnerWieldsShieldPredicate:
    expected: bool = True


@dataclass(frozen=True)
class OwnerWieldsWeaponOrShieldPredicate:
    pass


@dataclass(frozen=True)
class WithinDistancePredicate:
    distanceFeet: int


@dataclass(frozen=True)
class AttackerIsVisiblePredicate:
    pass


@dataclass(frozen=True)
class OwnerWearsArmorPredicate:
    expected: bool = True


@dataclass(frozen=True)
class SourceUsesTimeEconomyPredicate:
    timeEconomy: TimeEconomy


@dataclass(frozen=True)
class RandomChancePredicate:
    numerator: int
    denominator: int

    def __post_init__(self) -> None:
        if self.denominator < 1 or self.numerator < 0 or self.numerator > self.denominator:
            raise ValueError("Random chance must be between zero and one")


Predicate: TypeAlias = (
    TargetIsOwnerPredicate
    | SourceIsAttackPredicate
    | SourceIsSpellPredicate
    | SourceHasComponentPredicate
    | TargetHasConditionPredicate
    | PendingEffectAddsConditionPredicate
    | SourceHasConditionPredicate
    | TargetHasCreatureTypePredicate
    | TargetHasAnyCreatureTypePredicate
    | SavingThrowAbilityPredicate
    | CalculationAbilityPredicate
    | RollOutcomePredicate
    | WeaponHasPropertyPredicate
    | WeaponHasAnyPropertyPredicate
    | SourceAttackRangePredicate
    | SourceWeaponCategoryPredicate
    | SourceAttackKindPredicate
    | SourceDamageAbilityModifierPredicate
    | OwnerWieldsExactlyOneOneHandedWeaponPredicate
    | OwnerWearsHeavyArmorPredicate
    | OwnerWieldsShieldPredicate
    | OwnerWieldsWeaponOrShieldPredicate
    | WithinDistancePredicate
    | AttackerIsVisiblePredicate
    | OwnerWearsArmorPredicate
    | SourceUsesTimeEconomyPredicate
    | RandomChancePredicate
)


class CalculationType(Enum):
    ATTACK_ROLL = auto()
    DAMAGE_ROLL = auto()
    SAVING_THROW = auto()
    ABILITY_CHECK = auto()
    ARMOR_CLASS = auto()
    SPEED = auto()
    SPELL_SAVE_DC = auto()
    CONCENTRATION_SAVE = auto()


class ModifierOperation(Enum):
    ADD = auto()
    SUBTRACT = auto()
    ADVANTAGE = auto()
    DISADVANTAGE = auto()
    FORCE_SUCCESS = auto()
    FORCE_FAILURE = auto()
    MULTIPLY = auto()
    SET = auto()
    MINIMUM = auto()


class ModifierScope(Enum):
    OWNER = auto()
    AGAINST_OWNER = auto()


@dataclass(frozen=True)
class Modifier:
    calculation: CalculationType
    operation: ModifierOperation
    predicates: list[Predicate] = field(default_factory=list)
    amount: EffectAmount | None = None
    scope: ModifierScope = ModifierScope.OWNER
    numerator: int = 1
    denominator: int = 1
    description: str = ""

    def __post_init__(self) -> None:
        if self.denominator == 0:
            raise ValueError("Modifier denominator cannot be zero")


class EffectDurationType(Enum):
    INSTANTANEOUS = auto()
    UNTIL_START_OF_TURN = auto()
    UNTIL_END_OF_TURN = auto()
    ROUNDS = auto()
    MINUTES = auto()
    HOURS = auto()
    UNTIL_SHORT_REST = auto()
    UNTIL_LONG_REST = auto()
    CONCENTRATION = auto()
    WHILE_EQUIPPED = auto()
    PERMANENT = auto()
    MANUAL = auto()


@dataclass(frozen=True)
class EffectDuration:
    durationType: EffectDurationType
    amount: int = 0


class EndingConditionType(Enum):
    SOURCE_CONCENTRATION_ENDS = auto()
    SOURCE_UNEQUIPPED = auto()
    OWNER_ATTACKS = auto()
    OWNER_CASTS_SPELL = auto()
    OWNER_DEALS_DAMAGE = auto()
    TARGET_SUCCEEDS_SAVE = auto()
    TARGET_TAKES_DAMAGE = auto()
    MANUAL = auto()


@dataclass(frozen=True)
class EndingCondition:
    endingCondition: EndingConditionType
    savingThrow: SavingThrow | None = None
    advantage: bool = False


class ResolutionEventType(Enum):
    ACTION_DECLARED = auto()
    SPELL_DECLARED = auto()
    ATTACK_ROLLED = auto()
    SAVE_ROLLED = auto()
    CHECK_ROLLED = auto()
    DAMAGE_PENDING = auto()
    DAMAGE_APPLIED = auto()
    CONDITION_PENDING = auto()
    CONDITION_APPLIED = auto()
    EFFECT_PENDING = auto()
    EFFECT_COMMITTED = auto()
    TURN_STARTED = auto()
    TURN_ENDED = auto()
    REST_COMPLETED = auto()


class InteractionTiming(Enum):
    BEFORE_EVENT = auto()
    AFTER_EVENT = auto()


class InteractionDecisionType(Enum):
    AUTOMATIC = auto()
    PROMPT = auto()


class PromptResponder(Enum):
    OWNER = auto()
    DM = auto()
    OWNER_OR_DM = auto()


class InteractionChoice(Enum):
    ACCEPT = auto()
    DECLINE = auto()


@dataclass(frozen=True)
class InteractionDecision:
    decisionType: InteractionDecisionType
    responder: PromptResponder = PromptResponder.OWNER_OR_DM


class RollModificationType(Enum):
    ADD = auto()
    SUBTRACT = auto()
    ADVANTAGE = auto()
    DISADVANTAGE = auto()


class PendingDamageModificationType(Enum):
    MULTIPLY = auto()
    REDUCE = auto()
    PREVENT = auto()


class ActionModificationType(Enum):
    RANGE = auto()
    TARGET_COUNT = auto()
    COMPONENTS = auto()
    DAMAGE_TYPE = auto()
    TIME_ECONOMY = auto()


@dataclass(frozen=True)
class CancelPendingAction:
    pass


@dataclass(frozen=True)
class ReplaceRollOutcome:
    outcome: RollOutcome


@dataclass(frozen=True)
class ModifyRoll:
    modification: RollModificationType
    amount: EffectAmount | None = None


@dataclass(frozen=True)
class RerollSavingThrow:
    bonus: EffectAmount | None = None


@dataclass(frozen=True)
class ModifyPendingDamage:
    modification: PendingDamageModificationType
    numerator: int = 1
    denominator: int = 1
    amount: EffectAmount | None = None


@dataclass(frozen=True)
class PreventCondition:
    conditions: list[ConditionType]


@dataclass(frozen=True)
class ModifyAction:
    modification: ActionModificationType
    amount: int | None = None
    damageType: DamageType | None = None
    timeEconomy: TimeEconomy | None = None
    removedComponents: list[SpellComponent] = field(default_factory=list)


@dataclass(frozen=True)
class ApplyEffectOperation:
    effect: EffectNode


@dataclass(frozen=True)
class ScheduleEffectOperation:
    effect: EffectNode
    trigger: ResolutionEventType


ResolutionOperation: TypeAlias = (
    CancelPendingAction
    | ReplaceRollOutcome
    | ModifyRoll
    | RerollSavingThrow
    | ModifyPendingDamage
    | PreventCondition
    | ModifyAction
    | ApplyEffectOperation
    | ScheduleEffectOperation
)


@dataclass(frozen=True)
class Interaction:
    trigger: ResolutionEventType
    timing: InteractionTiming
    decision: InteractionDecision
    predicates: list[Predicate] = field(default_factory=list)
    operations: list[ResolutionOperation] = field(default_factory=list)
    resourceCosts: tuple[ResourceCost, ...] = ()


class PendingResolutionStatus(Enum):
    READY = auto()
    PAUSED = auto()
    COMPLETED = auto()
    CANCELLED = auto()


@dataclass(frozen=True)
class ResolutionId:
    value: int


@dataclass(frozen=True)
class EffectNodeId:
    path: tuple[int, ...]

    def child(self, index: int) -> EffectNodeId:
        if index < 0:
            raise ValueError("Effect node child index cannot be negative")
        return EffectNodeId((*self.path, index))


@dataclass(frozen=True)
class EffectRollInput:
    effectNodeId: EffectNodeId
    outcome: RollOutcome


@dataclass(frozen=True)
class EffectAmountInput:
    effectNodeId: EffectNodeId
    amount: int


@dataclass(frozen=True)
class EffectResolutionInputs:
    rolls: list[EffectRollInput] = field(default_factory=list)
    amounts: list[EffectAmountInput] = field(default_factory=list)


@dataclass(frozen=True)
class ResolutionEvent:
    resolutionId: ResolutionId
    eventType: ResolutionEventType
    pendingEffect: EffectNode | None
    rollOutcome: RollOutcome | None = None
    effectNodeId: EffectNodeId | None = None
    bindings: EffectParticipantBindings | None = None
    dispatchSource: EffectDispatchSource | None = None


@dataclass(frozen=True)
class InteractionPrompt:
    resolutionId: ResolutionId
    interactionIndex: int
    responder: PromptResponder


@dataclass(frozen=True)
class InteractionResponse:
    resolutionId: ResolutionId
    interactionIndex: int
    choice: InteractionChoice


@dataclass(frozen=True)
class PendingResolution:
    resolutionId: ResolutionId
    rootEffect: EffectNode
    status: PendingResolutionStatus = PendingResolutionStatus.READY
    currentEvent: ResolutionEvent | None = None
    pendingPrompts: list[InteractionPrompt] = field(default_factory=list)
    handledInteractionIndexes: list[int] = field(default_factory=list)


@dataclass(frozen=True)
class OccurrenceLimit:
    count: int

    def __post_init__(self) -> None:
        if self.count < 1:
            raise ValueError("Occurrence limit must be positive")


@dataclass(frozen=True)
class OngoingEffect:
    duration: EffectDuration
    modifiers: list[Modifier] = field(default_factory=list)
    interactions: list[Interaction] = field(default_factory=list)
    damageDefenses: list[DamageDefenseEffect] = field(default_factory=list)
    suppressedConditions: list[ConditionType] = field(default_factory=list)
    recurringEffects: list[ScheduledEffect] = field(default_factory=list)
    endingConditions: list[EndingCondition] = field(default_factory=list)


@dataclass(frozen=True)
class OngoingEffectId:
    resolutionSeed: int
    effectNodeId: EffectNodeId


@dataclass(frozen=True)
class ActiveOngoingEffect:
    id: OngoingEffectId
    sourceSheetId: str
    targetSheetId: str
    sourceLabel: str
    effect: OngoingEffect


@dataclass(frozen=True)
class ApplyEffect:
    effect: AppliedEffect


@dataclass(frozen=True)
class ActivatedEffect:
    effect: EffectNode
    label: str = ""
    description: str = ""


@dataclass(frozen=True)
class SequenceEffect:
    effects: list[EffectNode]


@dataclass(frozen=True)
class SavingThrowEffect:
    savingThrow: SavingThrow
    onFailure: EffectNode | None = None
    onSuccess: EffectNode | None = None


@dataclass(frozen=True)
class AttackRollEffect:
    attack: AttackRoll
    onHit: EffectNode | None = None
    onMiss: EffectNode | None = None


@dataclass(frozen=True)
class ContestedCheckEffect:
    contest: ContestedCheck
    onSourceWin: EffectNode | None = None
    onTargetWin: EffectNode | None = None


@dataclass(frozen=True)
class ConditionalEffect:
    predicates: list[Predicate]
    whenTrue: EffectNode
    whenFalse: EffectNode | None = None


@dataclass(frozen=True)
class InstanceScaling:
    baseInstances: int
    basis: ScalingBasis | None = None
    interval: int = 1
    additionalInstances: int = 0
    thresholds: list[int] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.baseInstances < 0:
            raise ValueError("baseInstances cannot be negative")
        if self.interval < 1:
            raise ValueError("Instance scaling interval must be positive")
        if self.thresholds != sorted(set(self.thresholds)):
            raise ValueError("Instance scaling thresholds must be unique and sorted")


@dataclass(frozen=True)
class RepeatedEffect:
    instances: InstanceScaling
    effect: EffectNode


@dataclass(frozen=True)
class ScheduledEffect:
    trigger: ResolutionEventType
    effect: EffectNode
    occurrences: OccurrenceLimit | None = None


@dataclass(frozen=True)
class ScheduledEffectId:
    resolutionSeed: int
    effectNodeId: EffectNodeId


@dataclass(frozen=True)
class ActiveScheduledEffect:
    id: ScheduledEffectId
    sourceSheetId: str
    targetSheetId: str
    sourceLabel: str
    effect: ScheduledEffect
    remainingOccurrences: int | None = None


EffectDispatchSource: TypeAlias = ScheduledEffectId | OngoingEffectId


@dataclass(frozen=True)
class EffectParticipantBindings:
    sourceSheetId: str
    targetSheetId: str
    ownerSheetId: str


@dataclass(frozen=True)
class BoundEffect:
    effect: EffectNode
    bindings: EffectParticipantBindings | None
    dispatchSource: EffectDispatchSource | None = None


@dataclass(frozen=True)
class ScheduledEffectDispatch:
    source: EffectDispatchSource
    sourceSheetId: str
    targetSheetId: str
    sourceLabel: str
    effect: EffectNode


@dataclass(frozen=True)
class ScheduledEffectDispatchResult:
    dispatched: list[ScheduledEffectDispatch]
    remaining: list[ActiveScheduledEffect]


def dispatch_scheduled_effects(
    active_effects: list[ActiveScheduledEffect],
    event_type: ResolutionEventType,
    excluded_sources: set[EffectDispatchSource] | None = None,
) -> ScheduledEffectDispatchResult:
    dispatched: list[ScheduledEffectDispatch] = []
    remaining: list[ActiveScheduledEffect] = []
    excluded = excluded_sources or set()
    for active in active_effects:
        if active.effect.trigger != event_type or active.id in excluded:
            remaining.append(active)
            continue
        dispatched.append(ScheduledEffectDispatch(
            source=active.id,
            sourceSheetId=active.sourceSheetId,
            targetSheetId=active.targetSheetId,
            sourceLabel=active.sourceLabel,
            effect=active.effect.effect,
        ))
        remaining_count = active.remainingOccurrences if active.remainingOccurrences is not None else 1
        if remaining_count > 1:
            remaining.append(replace(active, remainingOccurrences=remaining_count - 1))
    return ScheduledEffectDispatchResult(dispatched, remaining)


def recurring_effects_for_event(
    ongoing_effects: list[ActiveOngoingEffect],
    event_type: ResolutionEventType,
) -> list[ScheduledEffectDispatch]:
    return [
        ScheduledEffectDispatch(
            source=active.id,
            sourceSheetId=active.sourceSheetId,
            targetSheetId=active.targetSheetId,
            sourceLabel=active.sourceLabel,
            effect=scheduled.effect,
        )
        for active in ongoing_effects
        for scheduled in active.effect.recurringEffects
        if scheduled.trigger == event_type
    ]


@dataclass(frozen=True)
class InstallOngoingEffect:
    effect: OngoingEffect


@dataclass(frozen=True)
class EffectChoice:
    option: DamageType | ConditionType
    effect: EffectNode


@dataclass(frozen=True)
class ChoiceEffect:
    choices: list[EffectChoice]
    minimum: int = 1
    maximum: int = 1

    def __post_init__(self) -> None:
        if self.minimum < 0 or self.maximum < self.minimum or self.maximum > len(self.choices):
            raise ValueError("Choice bounds must fit the available choices")


EffectNode: TypeAlias = (
    ApplyEffect
    | ActivatedEffect
    | SequenceEffect
    | SavingThrowEffect
    | AttackRollEffect
    | ContestedCheckEffect
    | ConditionalEffect
    | RepeatedEffect
    | ScheduledEffect
    | InstallOngoingEffect
    | ChoiceEffect
)


@dataclass(frozen=True)
class FeatureMechanics:
    activatedEffects: list[EffectNode] = field(default_factory=list)
    passiveModifiers: list[Modifier] = field(default_factory=list)
    interactions: list[Interaction] = field(default_factory=list)


class EffectExecutionStatus(Enum):
    RUNNING = auto()
    PAUSED = auto()
    COMPLETED = auto()
    CANCELLED = auto()


@dataclass(frozen=True)
class AppliedEffectResult:
    effect: AppliedEffect
    amount: int | None = None
    effectNodeId: EffectNodeId | None = None
    bindings: EffectParticipantBindings | None = None


@dataclass(frozen=True)
class EffectExecutionResult:
    status: EffectExecutionStatus
    appliedEffects: list[AppliedEffectResult] = field(default_factory=list)


class EffectFramePhase(Enum):
    PENDING = auto()
    EXECUTE = auto()
    SELECT_BRANCH = auto()
    CHILDREN = auto()
    COMMITTED = auto()
    COMPLETE = auto()


@dataclass
class EffectExecutionFrame:
    effectNodeId: EffectNodeId
    effect: EffectNode
    phase: EffectFramePhase = EffectFramePhase.PENDING
    children: list[EffectNode] = field(default_factory=list)
    childNodeIndexes: list[int] = field(default_factory=list)
    nextChildIndex: int = 0
    rollOutcome: RollOutcome | None = None
    appliedEffectStartIndex: int = 0
    bindings: EffectParticipantBindings | None = None
    dispatchSource: EffectDispatchSource | None = None
    owningAttackNodeId: EffectNodeId | None = None


@dataclass(frozen=True)
class ResolutionEventResponse:
    pendingEffect: EffectNode | None = None
    rollOutcome: RollOutcome | None = None
    additionalEffects: list[EffectNode] = field(default_factory=list)
    boundEffects: list[BoundEffect] = field(default_factory=list)


@dataclass
class EffectExecution:
    resolutionId: ResolutionId
    rootEffect: EffectNode
    stack: list[EffectExecutionFrame]
    status: EffectExecutionStatus = EffectExecutionStatus.RUNNING
    waitingFor: ResolutionEvent | None = None
    appliedEffects: list[AppliedEffectResult] = field(default_factory=list)
    injectedEffectCount: int = 0
    declarationEventType: ResolutionEventType | None = None
    declarationHandled: bool = False


EffectAdvanceResult: TypeAlias = ResolutionEvent | EffectExecutionResult


class EffectExecutionContext(Protocol):
    def bind_participants(self, bindings: EffectParticipantBindings | None) -> None: ...

    def prepare_effect(
        self,
        node_id: EffectNodeId,
        effect: EffectNode,
        owning_attack_node_id: EffectNodeId | None,
    ) -> EffectNode: ...

    def apply_effect(
        self,
        node_id: EffectNodeId,
        effect: AppliedEffect,
        previous_results: list[AppliedEffectResult],
    ) -> AppliedEffectResult: ...

    def resolve_saving_throw(self, node_id: EffectNodeId, saving_throw: SavingThrow) -> RollOutcome | None: ...

    def resolve_attack_roll(self, node_id: EffectNodeId, attack: AttackRoll) -> RollOutcome | None: ...

    def resolve_contested_check(self, node_id: EffectNodeId, contest: ContestedCheck) -> RollOutcome: ...

    def record_roll_outcome(self, node_id: EffectNodeId, effect: EffectNode, outcome: RollOutcome) -> None: ...

    def evaluate_predicates(self, node_id: EffectNodeId, predicates: list[Predicate]) -> bool: ...

    def resolve_instance_count(self, instances: InstanceScaling) -> int: ...

    def choose_effects(self, choice: ChoiceEffect) -> list[EffectNode]: ...

    def schedule_effect(self, node_id: EffectNodeId, effect: ScheduledEffect) -> None: ...

    def install_ongoing_effect(self, node_id: EffectNodeId, effect: OngoingEffect) -> None: ...


class EffectInteractionPort(Protocol):
    def before_effect(self, event: ResolutionEvent) -> EffectNode | None: ...

    def after_roll(self, event: ResolutionEvent) -> RollOutcome: ...

    def after_effect(self, event: ResolutionEvent, result: EffectExecutionResult) -> None: ...


class NoOpEffectInteractionPort:
    def before_effect(self, event: ResolutionEvent) -> EffectNode | None:
        return event.pendingEffect

    def after_roll(self, event: ResolutionEvent) -> RollOutcome:
        if event.rollOutcome is None:
            raise ValueError("A roll event requires an outcome")
        return event.rollOutcome

    def after_effect(self, event: ResolutionEvent, result: EffectExecutionResult) -> None:
        return None


class EffectEngine:
    def __init__(self, interactions: EffectInteractionPort | None = None, maximumDepth: int = 64) -> None:
        if maximumDepth < 1:
            raise ValueError("maximumDepth must be positive")
        self.interactions = interactions or NoOpEffectInteractionPort()
        self.maximumDepth = maximumDepth

    def resolve(self, effect: EffectNode, context: EffectExecutionContext) -> EffectExecutionResult:
        execution = self.start(effect)
        response: ResolutionEventResponse | None = None
        while True:
            advanced = self.advance(execution, context, response)
            response = None
            if isinstance(advanced, EffectExecutionResult):
                return advanced
            if advanced.eventType in {
                ResolutionEventType.ATTACK_ROLLED,
                ResolutionEventType.SAVE_ROLLED,
                ResolutionEventType.CHECK_ROLLED,
            }:
                response = ResolutionEventResponse(rollOutcome=self.interactions.after_roll(advanced))
            elif advanced.eventType in {
                ResolutionEventType.DAMAGE_APPLIED,
                ResolutionEventType.CONDITION_APPLIED,
                ResolutionEventType.EFFECT_COMMITTED,
                ResolutionEventType.REST_COMPLETED,
            }:
                self.interactions.after_effect(
                    advanced,
                    EffectExecutionResult(
                        EffectExecutionStatus.COMPLETED,
                        execution.appliedEffects[execution.stack[-1].appliedEffectStartIndex :],
                    ),
                )
                response = ResolutionEventResponse()
            else:
                response = ResolutionEventResponse(pendingEffect=self.interactions.before_effect(advanced))

    def start(
        self,
        effect: EffectNode,
        declaration_event_type: ResolutionEventType | None = None,
        bindings: EffectParticipantBindings | None = None,
    ) -> EffectExecution:
        resolution_id = ResolutionId(time_ns())
        return EffectExecution(
            resolutionId=resolution_id,
            rootEffect=effect,
            stack=[EffectExecutionFrame(EffectNodeId(()), effect, bindings=bindings)],
            declarationEventType=declaration_event_type,
        )

    def advance(
        self,
        execution: EffectExecution,
        context: EffectExecutionContext,
        response: ResolutionEventResponse | None = None,
    ) -> EffectAdvanceResult:
        if execution.status in {EffectExecutionStatus.COMPLETED, EffectExecutionStatus.CANCELLED}:
            return EffectExecutionResult(execution.status, list(execution.appliedEffects))
        if execution.waitingFor is not None:
            if response is None:
                execution.status = EffectExecutionStatus.PAUSED
                return execution.waitingFor
            context.bind_participants(execution.stack[-1].bindings if execution.stack else None)
            self._accept_response(execution, context, response)
            execution.waitingFor = None
            if execution.status == EffectExecutionStatus.CANCELLED:
                return EffectExecutionResult(EffectExecutionStatus.CANCELLED, list(execution.appliedEffects))
            execution.status = EffectExecutionStatus.RUNNING
        elif response is not None:
            raise ValueError("Effect execution is not waiting for a response")

        if not execution.declarationHandled and execution.declarationEventType is not None:
            execution.declarationHandled = True
            root_frame = execution.stack[0]
            return self._pause_for_event(
                execution,
                ResolutionEvent(
                    resolutionId=execution.resolutionId,
                    eventType=execution.declarationEventType,
                    pendingEffect=execution.rootEffect,
                    effectNodeId=EffectNodeId(()),
                    bindings=root_frame.bindings,
                    dispatchSource=root_frame.dispatchSource,
                ),
            )

        while execution.stack:
            if len(execution.stack) > self.maximumDepth:
                raise RecursionError("Effect tree exceeded maximum resolution depth")
            frame = execution.stack[-1]
            context.bind_participants(frame.bindings)
            if frame.phase == EffectFramePhase.PENDING:
                frame.effect = context.prepare_effect(
                    frame.effectNodeId,
                    frame.effect,
                    frame.owningAttackNodeId,
                )
                frame.phase = EffectFramePhase.EXECUTE
                return self._pause_for_event(
                    execution,
                    ResolutionEvent(
                        resolutionId=execution.resolutionId,
                        eventType=resolution_event_type(frame.effect),
                        pendingEffect=frame.effect,
                        effectNodeId=frame.effectNodeId,
                        bindings=frame.bindings,
                        dispatchSource=frame.dispatchSource,
                    ),
                )
            if frame.phase == EffectFramePhase.EXECUTE:
                event = self._execute_frame(execution, context, frame)
                if event is not None:
                    return self._pause_for_event(execution, event)
                continue
            if frame.phase == EffectFramePhase.SELECT_BRANCH:
                self._select_roll_branch(frame)
                continue
            if frame.phase == EffectFramePhase.CHILDREN:
                if frame.nextChildIndex < len(frame.children):
                    index = frame.nextChildIndex
                    frame.nextChildIndex += 1
                    execution.stack.append(
                        EffectExecutionFrame(
                            effectNodeId=frame.effectNodeId.child(frame.childNodeIndexes[index]),
                            effect=frame.children[index],
                            appliedEffectStartIndex=len(execution.appliedEffects),
                            bindings=frame.bindings,
                            dispatchSource=frame.dispatchSource,
                            owningAttackNodeId=(
                                frame.effectNodeId
                                if isinstance(frame.effect, AttackRollEffect) and frame.rollOutcome == RollOutcome.HIT
                                else frame.owningAttackNodeId
                            ),
                        )
                    )
                    continue
                frame.phase = EffectFramePhase.COMMITTED
                continue
            if frame.phase == EffectFramePhase.COMMITTED:
                frame.phase = EffectFramePhase.COMPLETE
                return self._pause_for_event(
                    execution,
                    ResolutionEvent(
                        resolutionId=execution.resolutionId,
                        eventType=committed_resolution_event_type(frame.effect),
                        pendingEffect=frame.effect,
                        effectNodeId=frame.effectNodeId,
                        bindings=frame.bindings,
                        dispatchSource=frame.dispatchSource,
                    ),
                )
            execution.stack.pop()

        execution.status = EffectExecutionStatus.COMPLETED
        return EffectExecutionResult(EffectExecutionStatus.COMPLETED, list(execution.appliedEffects))

    def _pause_for_event(self, execution: EffectExecution, event: ResolutionEvent) -> ResolutionEvent:
        execution.waitingFor = event
        execution.status = EffectExecutionStatus.PAUSED
        return event

    def _accept_response(
        self,
        execution: EffectExecution,
        context: EffectExecutionContext,
        response: ResolutionEventResponse,
    ) -> None:
        event = execution.waitingFor
        if event is None or not execution.stack:
            raise ValueError("Effect execution has no pending event")
        frame = execution.stack[-1]
        if event.eventType in {ResolutionEventType.ACTION_DECLARED, ResolutionEventType.SPELL_DECLARED}:
            if response.pendingEffect is None:
                execution.status = EffectExecutionStatus.CANCELLED
                execution.stack.clear()
                return
            frame.effect = response.pendingEffect
            execution.rootEffect = response.pendingEffect
            return
        if event.eventType in {
            ResolutionEventType.ATTACK_ROLLED,
            ResolutionEventType.SAVE_ROLLED,
            ResolutionEventType.CHECK_ROLLED,
        }:
            if response.rollOutcome is None:
                raise ValueError("A roll event response requires an outcome")
            frame.rollOutcome = response.rollOutcome
            context.record_roll_outcome(frame.effectNodeId, frame.effect, response.rollOutcome)
        elif frame.phase == EffectFramePhase.EXECUTE:
            if response.pendingEffect is None:
                if len(execution.stack) == 1:
                    execution.status = EffectExecutionStatus.CANCELLED
                    execution.stack.clear()
                else:
                    frame.phase = EffectFramePhase.COMPLETE
                return
            frame.effect = response.pendingEffect
        injected_effects = [
            BoundEffect(effect, frame.bindings, frame.dispatchSource)
            for effect in response.additionalEffects
        ]
        injected_effects.extend(response.boundEffects)
        for injected in reversed(injected_effects):
            injected_id = EffectNodeId((-1, execution.injectedEffectCount))
            execution.injectedEffectCount += 1
            execution.stack.append(
                EffectExecutionFrame(
                    effectNodeId=injected_id,
                    effect=injected.effect,
                    appliedEffectStartIndex=len(execution.appliedEffects),
                    bindings=injected.bindings,
                    dispatchSource=injected.dispatchSource,
                    owningAttackNodeId=None,
                )
            )

    def _execute_frame(
        self,
        execution: EffectExecution,
        context: EffectExecutionContext,
        frame: EffectExecutionFrame,
    ) -> ResolutionEvent | None:
        effect = frame.effect
        if isinstance(effect, ActivatedEffect):
            self._set_children(frame, [effect.effect])
        elif isinstance(effect, ApplyEffect):
            applied = context.apply_effect(frame.effectNodeId, effect.effect, execution.appliedEffects)
            execution.appliedEffects.append(
                replace(
                    applied,
                    effectNodeId=applied.effectNodeId or frame.effectNodeId,
                    bindings=frame.bindings,
                )
            )
            frame.phase = EffectFramePhase.COMMITTED
        elif isinstance(effect, SequenceEffect):
            self._set_children(frame, effect.effects)
        elif isinstance(effect, SavingThrowEffect):
            frame.phase = EffectFramePhase.SELECT_BRANCH
            return ResolutionEvent(
                execution.resolutionId,
                ResolutionEventType.SAVE_ROLLED,
                effect,
                context.resolve_saving_throw(frame.effectNodeId, effect.savingThrow),
                frame.effectNodeId,
                frame.bindings,
                frame.dispatchSource,
            )
        elif isinstance(effect, AttackRollEffect):
            frame.phase = EffectFramePhase.SELECT_BRANCH
            return ResolutionEvent(
                execution.resolutionId,
                ResolutionEventType.ATTACK_ROLLED,
                effect,
                context.resolve_attack_roll(frame.effectNodeId, effect.attack),
                frame.effectNodeId,
                frame.bindings,
                frame.dispatchSource,
            )
        elif isinstance(effect, ContestedCheckEffect):
            frame.phase = EffectFramePhase.SELECT_BRANCH
            return ResolutionEvent(
                execution.resolutionId,
                ResolutionEventType.CHECK_ROLLED,
                effect,
                context.resolve_contested_check(frame.effectNodeId, effect.contest),
                frame.effectNodeId,
                frame.bindings,
                frame.dispatchSource,
            )
        elif isinstance(effect, ConditionalEffect):
            matched = context.evaluate_predicates(frame.effectNodeId, effect.predicates)
            branch = effect.whenTrue if matched else effect.whenFalse
            self._set_children(
                frame,
                [] if branch is None else [branch],
                [] if branch is None else [0 if matched else 1],
            )
        elif isinstance(effect, RepeatedEffect):
            self._set_children(frame, [effect.effect] * max(0, context.resolve_instance_count(effect.instances)))
        elif isinstance(effect, ScheduledEffect):
            context.schedule_effect(frame.effectNodeId, effect)
            frame.phase = EffectFramePhase.COMMITTED
        elif isinstance(effect, InstallOngoingEffect):
            context.install_ongoing_effect(frame.effectNodeId, effect.effect)
            frame.phase = EffectFramePhase.COMMITTED
        elif isinstance(effect, ChoiceEffect):
            self._set_children(frame, context.choose_effects(effect))
        else:
            raise TypeError(f"Unsupported effect node: {effect.__class__.__name__}")
        return None

    @staticmethod
    def _set_children(
        frame: EffectExecutionFrame,
        children: list[EffectNode],
        node_indexes: list[int] | None = None,
    ) -> None:
        frame.children = children
        frame.childNodeIndexes = node_indexes if node_indexes is not None else list(range(len(children)))
        frame.nextChildIndex = 0
        frame.phase = EffectFramePhase.CHILDREN

    @staticmethod
    def _select_roll_branch(frame: EffectExecutionFrame) -> None:
        effect = frame.effect
        outcome = frame.rollOutcome
        if outcome is None:
            raise ValueError("A roll branch requires an outcome")
        if isinstance(effect, SavingThrowEffect):
            branch = effect.onSuccess if outcome == RollOutcome.SUCCESS else effect.onFailure
            branch_index = 1 if outcome == RollOutcome.SUCCESS else 0
        elif isinstance(effect, AttackRollEffect):
            branch = effect.onHit if outcome == RollOutcome.HIT else effect.onMiss
            branch_index = 0 if outcome == RollOutcome.HIT else 1
        elif isinstance(effect, ContestedCheckEffect):
            branch = effect.onSourceWin if outcome == RollOutcome.SUCCESS else effect.onTargetWin
            branch_index = 0 if outcome == RollOutcome.SUCCESS else 1
        else:
            raise TypeError(f"Unsupported roll branch: {effect.__class__.__name__}")
        frame.children = [] if branch is None else [branch]
        frame.childNodeIndexes = [] if branch is None else [branch_index]
        frame.nextChildIndex = 0
        frame.phase = EffectFramePhase.CHILDREN

def resolution_event_type(effect: EffectNode) -> ResolutionEventType:
    if isinstance(effect, ApplyEffect) and isinstance(effect.effect, DamageEffect):
        return ResolutionEventType.DAMAGE_PENDING
    if isinstance(effect, ApplyEffect) and isinstance(effect.effect, ConditionChangeEffect):
        return ResolutionEventType.CONDITION_PENDING
    return ResolutionEventType.EFFECT_PENDING


def committed_resolution_event_type(effect: EffectNode) -> ResolutionEventType:
    if isinstance(effect, ApplyEffect) and isinstance(effect.effect, DamageEffect):
        return ResolutionEventType.DAMAGE_APPLIED
    if isinstance(effect, ApplyEffect) and isinstance(effect.effect, ConditionChangeEffect):
        return ResolutionEventType.CONDITION_APPLIED
    return ResolutionEventType.EFFECT_COMMITTED


def multiplied_damage_effect(effect: EffectNode, numerator: int, denominator: int) -> EffectNode:
    if denominator == 0:
        raise ValueError("Damage multiplier denominator cannot be zero")
    if isinstance(effect, ActivatedEffect):
        return replace(effect, effect=multiplied_damage_effect(effect.effect, numerator, denominator))
    if isinstance(effect, ApplyEffect) and isinstance(effect.effect, DamageEffect):
        damage = effect.effect
        return ApplyEffect(
            replace(
                damage,
                multiplierNumerator=damage.multiplierNumerator * numerator,
                multiplierDenominator=damage.multiplierDenominator * denominator,
            )
        )
    if isinstance(effect, SequenceEffect):
        return SequenceEffect([multiplied_damage_effect(child, numerator, denominator) for child in effect.effects])
    if isinstance(effect, SavingThrowEffect):
        return replace(
            effect,
            onFailure=multiplied_optional_damage_effect(effect.onFailure, numerator, denominator),
            onSuccess=multiplied_optional_damage_effect(effect.onSuccess, numerator, denominator),
        )
    if isinstance(effect, AttackRollEffect):
        return replace(
            effect,
            onHit=multiplied_optional_damage_effect(effect.onHit, numerator, denominator),
            onMiss=multiplied_optional_damage_effect(effect.onMiss, numerator, denominator),
        )
    if isinstance(effect, ContestedCheckEffect):
        return replace(
            effect,
            onSourceWin=multiplied_optional_damage_effect(effect.onSourceWin, numerator, denominator),
            onTargetWin=multiplied_optional_damage_effect(effect.onTargetWin, numerator, denominator),
        )
    if isinstance(effect, ConditionalEffect):
        return replace(
            effect,
            whenTrue=multiplied_damage_effect(effect.whenTrue, numerator, denominator),
            whenFalse=multiplied_optional_damage_effect(effect.whenFalse, numerator, denominator),
        )
    if isinstance(effect, RepeatedEffect):
        return replace(effect, effect=multiplied_damage_effect(effect.effect, numerator, denominator))
    if isinstance(effect, ChoiceEffect):
        return replace(effect, choices=[
            replace(choice, effect=multiplied_damage_effect(choice.effect, numerator, denominator))
            for choice in effect.choices
        ])
    return effect


def multiplied_optional_damage_effect(
    effect: EffectNode | None,
    numerator: int,
    denominator: int,
) -> EffectNode | None:
    return multiplied_damage_effect(effect, numerator, denominator) if effect is not None else None


@dataclass(frozen=True)
class InteractionOperationResult:
    pendingEffect: EffectNode | None
    wasCancelled: bool = False
    rollOutcome: RollOutcome | None = None
    additionalEffects: list[EffectNode] = field(default_factory=list)
    scheduledEffects: list[ScheduledEffect] = field(default_factory=list)
    rollModifications: list[ModifyRoll] = field(default_factory=list)
    savingThrowRerolls: list[RerollSavingThrow] = field(default_factory=list)
    pendingDamageModifications: list[ModifyPendingDamage] = field(default_factory=list)
    actionModifications: list[ModifyAction] = field(default_factory=list)

    @property
    def cancelled(self) -> bool:
        return self.wasCancelled


def apply_interaction_operations(
    event: ResolutionEvent,
    operations: list[ResolutionOperation],
) -> InteractionOperationResult:
    result = InteractionOperationResult(pendingEffect=event.pendingEffect, rollOutcome=event.rollOutcome)
    for operation in operations:
        if isinstance(operation, CancelPendingAction):
            result = replace(result, pendingEffect=None, wasCancelled=True)
        elif isinstance(operation, ReplaceRollOutcome):
            result = replace(result, rollOutcome=operation.outcome)
        elif isinstance(operation, ModifyRoll):
            result = replace(result, rollModifications=[*result.rollModifications, operation])
        elif isinstance(operation, RerollSavingThrow):
            result = replace(result, savingThrowRerolls=[*result.savingThrowRerolls, operation])
        elif isinstance(operation, ModifyPendingDamage):
            pending_effect = result.pendingEffect
            if pending_effect is not None and operation.modification == PendingDamageModificationType.MULTIPLY:
                pending_effect = multiplied_damage_effect(pending_effect, operation.numerator, operation.denominator)
            elif pending_effect is not None and operation.modification == PendingDamageModificationType.PREVENT:
                pending_effect = multiplied_damage_effect(pending_effect, 0, 1)
            result = replace(
                result,
                pendingEffect=pending_effect,
                pendingDamageModifications=[*result.pendingDamageModifications, operation],
            )
        elif isinstance(operation, PreventCondition):
            result = replace(result, pendingEffect=effect_without_conditions(result.pendingEffect, set(operation.conditions)))
        elif isinstance(operation, ModifyAction):
            pending_effect = result.pendingEffect
            if operation.modification == ActionModificationType.DAMAGE_TYPE and operation.damageType is not None:
                pending_effect = replaced_damage_type_effect(pending_effect, operation.damageType)
            result = replace(result, pendingEffect=pending_effect, actionModifications=[*result.actionModifications, operation])
        elif isinstance(operation, ApplyEffectOperation):
            result = replace(result, additionalEffects=[*result.additionalEffects, operation.effect])
        elif isinstance(operation, ScheduleEffectOperation):
            result = replace(
                result,
                scheduledEffects=[*result.scheduledEffects, ScheduledEffect(operation.trigger, operation.effect)],
            )
        else:
            raise TypeError(f"Unsupported resolution operation: {operation.__class__.__name__}")
    return result


def replaced_damage_type_effect(effect: EffectNode | None, damage_type: DamageType) -> EffectNode | None:
    if effect is None:
        return None
    if isinstance(effect, ActivatedEffect):
        replaced = replaced_damage_type_effect(effect.effect, damage_type)
        return replace(effect, effect=replaced) if replaced is not None else None
    if isinstance(effect, ApplyEffect) and isinstance(effect.effect, DamageEffect):
        return replace(effect, effect=replace(effect.effect, damageType=damage_type))
    if isinstance(effect, SequenceEffect):
        return replace(effect, effects=[child for item in effect.effects if (child := replaced_damage_type_effect(item, damage_type)) is not None])
    if isinstance(effect, SavingThrowEffect):
        return replace(effect, onFailure=replaced_damage_type_effect(effect.onFailure, damage_type), onSuccess=replaced_damage_type_effect(effect.onSuccess, damage_type))
    if isinstance(effect, AttackRollEffect):
        return replace(effect, onHit=replaced_damage_type_effect(effect.onHit, damage_type), onMiss=replaced_damage_type_effect(effect.onMiss, damage_type))
    if isinstance(effect, ContestedCheckEffect):
        return replace(
            effect,
            onSourceWin=replaced_damage_type_effect(effect.onSourceWin, damage_type),
            onTargetWin=replaced_damage_type_effect(effect.onTargetWin, damage_type),
        )
    if isinstance(effect, ConditionalEffect):
        when_true = replaced_damage_type_effect(effect.whenTrue, damage_type)
        return replace(effect, whenTrue=when_true or effect.whenTrue, whenFalse=replaced_damage_type_effect(effect.whenFalse, damage_type))
    if isinstance(effect, RepeatedEffect):
        replaced = replaced_damage_type_effect(effect.effect, damage_type)
        return replace(effect, effect=replaced) if replaced is not None else None
    if isinstance(effect, ScheduledEffect):
        replaced = replaced_damage_type_effect(effect.effect, damage_type)
        return replace(effect, effect=replaced) if replaced is not None else None
    if isinstance(effect, ChoiceEffect):
        return replace(effect, choices=[replace(choice, effect=replaced_damage_type_effect(choice.effect, damage_type) or choice.effect) for choice in effect.choices])
    return effect


def effect_without_conditions(effect: EffectNode | None, conditions: set[ConditionType]) -> EffectNode | None:
    if effect is None:
        return None
    if isinstance(effect, ActivatedEffect):
        transformed = effect_without_conditions(effect.effect, conditions)
        return replace(effect, effect=transformed) if transformed is not None else None
    if isinstance(effect, ApplyEffect):
        if (
            isinstance(effect.effect, ConditionChangeEffect)
            and effect.effect.operation == ConditionOperation.ADD
            and effect.effect.condition in conditions
        ):
            return None
        return effect
    if isinstance(effect, SequenceEffect):
        remaining = [
            transformed
            for child in effect.effects
            if (transformed := effect_without_conditions(child, conditions)) is not None
        ]
        return SequenceEffect(remaining)
    if isinstance(effect, SavingThrowEffect):
        return replace(
            effect,
            onFailure=effect_without_conditions(effect.onFailure, conditions),
            onSuccess=effect_without_conditions(effect.onSuccess, conditions),
        )
    if isinstance(effect, AttackRollEffect):
        return replace(
            effect,
            onHit=effect_without_conditions(effect.onHit, conditions),
            onMiss=effect_without_conditions(effect.onMiss, conditions),
        )
    if isinstance(effect, ContestedCheckEffect):
        return replace(
            effect,
            onSourceWin=effect_without_conditions(effect.onSourceWin, conditions),
            onTargetWin=effect_without_conditions(effect.onTargetWin, conditions),
        )
    if isinstance(effect, ConditionalEffect):
        when_true = effect_without_conditions(effect.whenTrue, conditions)
        if when_true is None:
            return effect_without_conditions(effect.whenFalse, conditions)
        return replace(
            effect,
            whenTrue=when_true,
            whenFalse=effect_without_conditions(effect.whenFalse, conditions),
        )
    if isinstance(effect, RepeatedEffect):
        repeated = effect_without_conditions(effect.effect, conditions)
        return replace(effect, effect=repeated) if repeated is not None else None
    if isinstance(effect, ScheduledEffect):
        scheduled = effect_without_conditions(effect.effect, conditions)
        return replace(effect, effect=scheduled) if scheduled is not None else None
    if isinstance(effect, ChoiceEffect):
        choices = [
            EffectChoice(choice.option, transformed)
            for choice in effect.choices
            if (transformed := effect_without_conditions(choice.effect, conditions)) is not None
        ]
        if not choices:
            return None
        return replace(
            effect,
            choices=choices,
            minimum=min(effect.minimum, len(choices)),
            maximum=min(effect.maximum, len(choices)),
        )
    return effect


def effect_model_types() -> list[type[object]]:
    return [
        ActionModificationType,
        ActiveOngoingEffect,
        ActiveScheduledEffect,
        AbilityCheck,
        ActivatedEffect,
        AmountCalculation,
        AmountScaling,
        AppliedEffectKind,
        AppliedEffectResult,
        ApplyEffect,
        ApplyEffectOperation,
        AttackRoll,
        AttackRollEffect,
        AttackRollType,
        AttackerIsVisiblePredicate,
        CalculatedAmount,
        CalculationAbilityPredicate,
        CalculationType,
        CancelPendingAction,
        ChoiceEffect,
        CombinedAmount,
        ContestedCheck,
        ContestedCheckEffect,
        CollectionOperation,
        ConditionalEffect,
        ConditionChangeEffect,
        ConditionOperation,
        DamageDefenseEffect,
        DamageDefenseType,
        DamageEffect,
        DerivedAmount,
        DiceAmount,
        DifficultyClass,
        DifficultyClassType,
        EffectChoice,
        EffectDuration,
        EffectDurationType,
        EffectExecutionResult,
        EffectExecutionStatus,
        EffectAmountInput,
        EffectNodeId,
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
        InteractionChoice,
        InteractionDecision,
        InteractionDecisionType,
        InteractionOperationResult,
        InteractionTiming,
        InteractionPrompt,
        InteractionResponse,
        MaximumHitPointsEffect,
        MaximumHitPointsOperation,
        Modifier,
        ModifierOperation,
        ModifierScope,
        ModifyAction,
        ModifyPendingDamage,
        ModifyRoll,
        MovementEffect,
        MovementType,
        OccurrenceLimit,
        OngoingEffect,
        OngoingEffectId,
        OwnerWearsArmorPredicate,
        OwnerWearsHeavyArmorPredicate,
        OwnerWieldsExactlyOneOneHandedWeaponPredicate,
        OwnerWieldsShieldPredicate,
        OwnerWieldsWeaponOrShieldPredicate,
        PendingEffectAddsConditionPredicate,
        PendingDamageModificationType,
        PendingResolution,
        PendingResolutionStatus,
        PreventCondition,
        PromptResponder,
        RandomChancePredicate,
        RepeatedEffect,
        RerollSavingThrow,
        ReplaceRollOutcome,
        ResolutionEventType,
        ResolutionEvent,
        ResolutionId,
        RestEffect,
        RollModificationType,
        RollOutcome,
        RollOutcomePredicate,
        SavingThrow,
        SavingThrowAbilityPredicate,
        SavingThrowEffect,
        ScalingBasis,
        ScheduleEffectOperation,
        ScheduledEffect,
        ScheduledEffectId,
        SequenceEffect,
        SourceHasComponentPredicate,
        SourceHasConditionPredicate,
        SourceAttackKindPredicate,
        SourceAttackRangePredicate,
        SourceDamageAbilityModifierPredicate,
        SourceUsesTimeEconomyPredicate,
        SourceWeaponCategoryPredicate,
        SourceIsAttackPredicate,
        SourceIsSpellPredicate,
        TargetHasConditionPredicate,
        TargetHasAnyCreatureTypePredicate,
        TargetHasCreatureTypePredicate,
        TargetIsOwnerPredicate,
        TemporaryHitPointsEffect,
        WeaponHasPropertyPredicate,
        WeaponHasAnyPropertyPredicate,
        WithinDistancePredicate,
    ]
