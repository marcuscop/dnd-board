from __future__ import annotations

from dataclasses import dataclass

from dnd_board.character_sheet import AbilityType, ConditionType, DamageType, DiceType, SpellComponent, TimeEconomy
from dnd_board.rules.shared.effects import (
    CalculationAbilityPredicate,
    CalculatedAmount,
    CalculationType,
    CollectionOperation,
    DamageDefenseEffect,
    DamageDefenseType,
    DiceAmount,
    CombinedAmount,
    EffectDuration,
    EffectDurationType,
    EndingCondition,
    EndingConditionType,
    FixedAmount,
    Interaction,
    InteractionDecision,
    InteractionDecisionType,
    InteractionTiming,
    Modifier,
    ModifierOperation,
    ModifierScope,
    OngoingEffect,
    OwnerWearsArmorPredicate,
    PendingEffectAddsConditionPredicate,
    Predicate,
    AmountCalculation,
    PreventCondition,
    CancelPendingAction,
    PromptResponder,
    ResolutionEventType,
    SourceHasComponentPredicate,
    SourceUsesTimeEconomyPredicate,
    RandomChancePredicate,
)


@dataclass(frozen=True)
class ConditionDefinition:
    condition: ConditionType
    ongoingEffect: OngoingEffect


def modifier(
    calculation: CalculationType,
    operation: ModifierOperation,
    amount: FixedAmount | DiceAmount | None = None,
    *,
    abilities: tuple[AbilityType, ...] = (),
    scope: ModifierScope = ModifierScope.OWNER,
    numerator: int = 1,
    denominator: int = 1,
    description: str = "",
    predicates: tuple[Predicate, ...] = (),
) -> Modifier:
    modifier_predicates = [CalculationAbilityPredicate(list(abilities))] if abilities else []
    modifier_predicates.extend(predicates)
    return Modifier(
        calculation=calculation,
        operation=operation,
        amount=amount,
        predicates=modifier_predicates,
        scope=scope,
        numerator=numerator,
        denominator=denominator,
        description=description,
    )


def prevent_conditions(*conditions: ConditionType) -> Interaction:
    return Interaction(
        trigger=ResolutionEventType.CONDITION_PENDING,
        timing=InteractionTiming.BEFORE_EVENT,
        decision=InteractionDecision(InteractionDecisionType.AUTOMATIC, PromptResponder.OWNER_OR_DM),
        operations=[PreventCondition(list(conditions))],
    )


def block_action(*predicates) -> Interaction:
    return Interaction(
        trigger=ResolutionEventType.ACTION_DECLARED,
        timing=InteractionTiming.BEFORE_EVENT,
        decision=InteractionDecision(InteractionDecisionType.AUTOMATIC, PromptResponder.OWNER_OR_DM),
        predicates=list(predicates),
        operations=[CancelPendingAction()],
    )


def ongoing(
    *modifiers: Modifier,
    interactions: tuple[Interaction, ...] = (),
    defenses: tuple[DamageDefenseEffect, ...] = (),
    suppressions: tuple[ConditionType, ...] = (),
    endings: tuple[EndingCondition, ...] = (),
) -> OngoingEffect:
    return OngoingEffect(
        duration=EffectDuration(EffectDurationType.MANUAL),
        modifiers=list(modifiers),
        interactions=list(interactions),
        damageDefenses=list(defenses),
        suppressedConditions=list(suppressions),
        endingConditions=list(endings),
    )


def attack_advantage(*, incoming: bool = False) -> Modifier:
    return modifier(
        CalculationType.ATTACK_ROLL,
        ModifierOperation.ADVANTAGE,
        scope=ModifierScope.AGAINST_OWNER if incoming else ModifierScope.OWNER,
    )


def attack_disadvantage(*, incoming: bool = False) -> Modifier:
    return modifier(
        CalculationType.ATTACK_ROLL,
        ModifierOperation.DISADVANTAGE,
        scope=ModifierScope.AGAINST_OWNER if incoming else ModifierScope.OWNER,
    )


CONDITION_DEFINITIONS: dict[ConditionType, ConditionDefinition] = {}


def define(condition: ConditionType, effect: OngoingEffect) -> None:
    CONDITION_DEFINITIONS[condition] = ConditionDefinition(condition, effect)


for condition, die, calculations, operation in (
    (ConditionType.BANE, DiceType.D4, (CalculationType.ATTACK_ROLL, CalculationType.SAVING_THROW), ModifierOperation.SUBTRACT),
    (ConditionType.BLESSED, DiceType.D4, (CalculationType.ATTACK_ROLL, CalculationType.SAVING_THROW), ModifierOperation.ADD),
    (ConditionType.GUIDANCE, DiceType.D4, (CalculationType.ABILITY_CHECK,), ModifierOperation.ADD),
    (ConditionType.SYNAPTIC_STATIC, DiceType.D6, (CalculationType.ATTACK_ROLL, CalculationType.ABILITY_CHECK, CalculationType.CONCENTRATION_SAVE), ModifierOperation.SUBTRACT),
):
    define(
        condition,
        ongoing(*(
            modifier(calculation, operation, DiceAmount(1, die), description=f"{operation.name.title()} 1d{die.value}.")
            for calculation in calculations
        )),
    )

ALL_DAMAGE_RESISTANCES = tuple(
    DamageDefenseEffect(DamageDefenseType.RESISTANCE, damage_type, CollectionOperation.ADD)
    for damage_type in DamageType
)


define(ConditionType.WARDING_BOND, ongoing(
    modifier(CalculationType.SAVING_THROW, ModifierOperation.ADD, FixedAmount(1), description="Add 1 to saving throws."),
    modifier(CalculationType.ARMOR_CLASS, ModifierOperation.ADD, FixedAmount(1)),
    defenses=ALL_DAMAGE_RESISTANCES,
))
define(ConditionType.ENLARGED, ongoing(
    modifier(CalculationType.DAMAGE_ROLL, ModifierOperation.ADD, DiceAmount(1, DiceType.D4)),
    modifier(CalculationType.SAVING_THROW, ModifierOperation.ADVANTAGE, abilities=(AbilityType.STRENGTH,)),
    modifier(CalculationType.ABILITY_CHECK, ModifierOperation.ADVANTAGE, abilities=(AbilityType.STRENGTH,)),
))
define(ConditionType.RAY_OF_ENFEEBLEMENT, ongoing(
    modifier(CalculationType.DAMAGE_ROLL, ModifierOperation.SUBTRACT, DiceAmount(1, DiceType.D8)),
    modifier(CalculationType.SAVING_THROW, ModifierOperation.DISADVANTAGE, abilities=(AbilityType.STRENGTH,)),
    modifier(CalculationType.ABILITY_CHECK, ModifierOperation.DISADVANTAGE, abilities=(AbilityType.STRENGTH,)),
))
define(ConditionType.REDUCED, ongoing(
    modifier(CalculationType.DAMAGE_ROLL, ModifierOperation.SUBTRACT, DiceAmount(1, DiceType.D4)),
    modifier(CalculationType.DAMAGE_ROLL, ModifierOperation.MINIMUM, FixedAmount(1)),
    modifier(CalculationType.SAVING_THROW, ModifierOperation.DISADVANTAGE, abilities=(AbilityType.STRENGTH,)),
    modifier(CalculationType.ABILITY_CHECK, ModifierOperation.DISADVANTAGE, abilities=(AbilityType.STRENGTH,)),
))
define(ConditionType.BLADE_WARD, ongoing(modifier(
    CalculationType.ATTACK_ROLL,
    ModifierOperation.SUBTRACT,
    DiceAmount(1, DiceType.D4),
    scope=ModifierScope.AGAINST_OWNER,
    description="Subtract 1d4 from attack rolls against the warded target.",
)))

for condition, ability in (
    (ConditionType.ENHANCE_ABILITY_CHARISMA, AbilityType.CHARISMA),
    (ConditionType.ENHANCE_ABILITY_DEXTERITY, AbilityType.DEXTERITY),
    (ConditionType.ENHANCE_ABILITY_INTELLIGENCE, AbilityType.INTELLIGENCE),
    (ConditionType.ENHANCE_ABILITY_STRENGTH, AbilityType.STRENGTH),
    (ConditionType.ENHANCE_ABILITY_WISDOM, AbilityType.WISDOM),
):
    define(condition, ongoing(modifier(CalculationType.ABILITY_CHECK, ModifierOperation.ADVANTAGE, abilities=(ability,))))

for condition in (ConditionType.PARALYZED, ConditionType.PETRIFIED, ConditionType.STUNNED, ConditionType.UNCONSCIOUS):
    define(condition, ongoing(
        modifier(CalculationType.SAVING_THROW, ModifierOperation.FORCE_FAILURE, abilities=(AbilityType.STRENGTH, AbilityType.DEXTERITY)),
        modifier(CalculationType.SPEED, ModifierOperation.SET, FixedAmount(0)),
        attack_advantage(incoming=True),
    ))

define(
    ConditionType.PETRIFIED,
    ongoing(*CONDITION_DEFINITIONS[ConditionType.PETRIFIED].ongoingEffect.modifiers, defenses=ALL_DAMAGE_RESISTANCES),
)

for condition in (ConditionType.BLINDED,):
    define(condition, ongoing(attack_disadvantage(), attack_advantage(incoming=True)))
for condition in (ConditionType.FRIGHTENED, ConditionType.PHANTASMAL_KILLER, ConditionType.POISONED):
    define(condition, ongoing(attack_disadvantage(), modifier(CalculationType.ABILITY_CHECK, ModifierOperation.DISADVANTAGE)))
define(ConditionType.PRONE, ongoing(attack_disadvantage()))
define(ConditionType.RESTRAINED, ongoing(
    attack_disadvantage(),
    attack_advantage(incoming=True),
    modifier(CalculationType.SAVING_THROW, ModifierOperation.DISADVANTAGE, abilities=(AbilityType.DEXTERITY,)),
    modifier(CalculationType.SPEED, ModifierOperation.SET, FixedAmount(0)),
))
for condition in (ConditionType.HEAVILY_OBSCURED, ConditionType.INVISIBLE):
    define(condition, ongoing(attack_advantage(), attack_disadvantage(incoming=True)))
define(ConditionType.INVISIBLE, ongoing(
    attack_advantage(),
    attack_disadvantage(incoming=True),
    endings=(
        EndingCondition(EndingConditionType.OWNER_ATTACKS),
        EndingCondition(EndingConditionType.OWNER_CASTS_SPELL),
        EndingCondition(EndingConditionType.OWNER_DEALS_DAMAGE),
    ),
))
for condition in (ConditionType.FAERIE_FIRE,):
    define(condition, ongoing(attack_advantage(incoming=True)))
for condition in (ConditionType.BLURRED,):
    define(condition, ongoing(attack_disadvantage(incoming=True)))

for condition, bonus in (
    (ConditionType.HALF_COVER, 2),
    (ConditionType.HASTED, 2),
    (ConditionType.SHIELDED, 5),
    (ConditionType.SHIELD_OF_FAITH, 2),
    (ConditionType.SLOWED, -2),
    (ConditionType.THREE_QUARTERS_COVER, 5),
):
    existing = CONDITION_DEFINITIONS.get(condition)
    modifiers = list(existing.ongoingEffect.modifiers) if existing else []
    modifiers.append(modifier(CalculationType.ARMOR_CLASS, ModifierOperation.ADD, FixedAmount(abs(bonus))) if bonus >= 0 else modifier(CalculationType.ARMOR_CLASS, ModifierOperation.SUBTRACT, FixedAmount(abs(bonus))))
    define(condition, ongoing(*modifiers))

define(ConditionType.HASTED, ongoing(
    *CONDITION_DEFINITIONS[ConditionType.HASTED].ongoingEffect.modifiers,
    modifier(CalculationType.SAVING_THROW, ModifierOperation.ADVANTAGE, abilities=(AbilityType.DEXTERITY,)),
    modifier(CalculationType.SPEED, ModifierOperation.MULTIPLY, numerator=2),
))
define(ConditionType.SLOWED, ongoing(
    *CONDITION_DEFINITIONS[ConditionType.SLOWED].ongoingEffect.modifiers,
    modifier(CalculationType.SAVING_THROW, ModifierOperation.SUBTRACT, FixedAmount(2), abilities=(AbilityType.DEXTERITY,)),
    modifier(CalculationType.SPEED, ModifierOperation.MULTIPLY, numerator=1, denominator=2),
    interactions=(
        block_action(SourceUsesTimeEconomyPredicate(TimeEconomy.REACTION)),
        block_action(SourceHasComponentPredicate(SpellComponent.SOMATIC), RandomChancePredicate(1, 4)),
    ),
))
define(ConditionType.LONGSTRIDER, ongoing(modifier(CalculationType.SPEED, ModifierOperation.ADD, FixedAmount(10))))
for condition in (ConditionType.GRAPPLED, ConditionType.DEAD):
    define(condition, ongoing(modifier(CalculationType.SPEED, ModifierOperation.SET, FixedAmount(0))))

for condition in (
    ConditionType.BANISHED,
    ConditionType.DEAD,
    ConditionType.INCAPACITATED,
    ConditionType.PARALYZED,
    ConditionType.PETRIFIED,
    ConditionType.STUNNED,
    ConditionType.UNCONSCIOUS,
):
    current = CONDITION_DEFINITIONS.get(condition)
    define(condition, ongoing(
        *(current.ongoingEffect.modifiers if current else []),
        interactions=(*(current.ongoingEffect.interactions if current else []), block_action()),
        defenses=tuple(current.ongoingEffect.damageDefenses if current else []),
    ))

define(ConditionType.HEROISM, ongoing(interactions=(prevent_conditions(ConditionType.FRIGHTENED),)))
define(ConditionType.CALM_EMOTIONS_IMMUNITY, ongoing(
    interactions=(prevent_conditions(ConditionType.CHARMED, ConditionType.FRIGHTENED),),
    suppressions=(ConditionType.CHARMED, ConditionType.FRIGHTENED),
))
define(ConditionType.PROTECTION_FROM_POISON, ongoing(
    modifier(
        CalculationType.SAVING_THROW,
        ModifierOperation.ADVANTAGE,
        abilities=(AbilityType.CONSTITUTION,),
        predicates=(PendingEffectAddsConditionPredicate(ConditionType.POISONED),),
    ),
    interactions=(prevent_conditions(ConditionType.POISONED),),
    defenses=(DamageDefenseEffect(DamageDefenseType.RESISTANCE, DamageType.POISON, operation=CollectionOperation.ADD),),
))

define(ConditionType.BARKSKIN, ongoing(modifier(CalculationType.ARMOR_CLASS, ModifierOperation.MINIMUM, FixedAmount(17))))
define(ConditionType.MAGE_ARMOR, ongoing(Modifier(
    calculation=CalculationType.ARMOR_CLASS,
    operation=ModifierOperation.MINIMUM,
    amount=CombinedAmount([
        FixedAmount(13),
        CalculatedAmount(AmountCalculation.SOURCE_ABILITY_MODIFIER, ability=AbilityType.DEXTERITY),
        CalculatedAmount(AmountCalculation.SOURCE_EQUIPPED_SHIELD_ARMOR_CLASS),
    ]),
    predicates=[OwnerWearsArmorPredicate(False)],
)))

for condition, damage_type in (
    (ConditionType.RESISTANT_ACID, DamageType.ACID),
    (ConditionType.RESISTANT_BLUDGEONING, DamageType.BLUDGEONING),
    (ConditionType.RESISTANT_COLD, DamageType.COLD),
    (ConditionType.RESISTANT_FIRE, DamageType.FIRE),
    (ConditionType.RESISTANT_FORCE, DamageType.FORCE),
    (ConditionType.RESISTANT_LIGHTNING, DamageType.LIGHTNING),
    (ConditionType.RESISTANT_NECROTIC, DamageType.NECROTIC),
    (ConditionType.RESISTANT_PIERCING, DamageType.PIERCING),
    (ConditionType.RESISTANT_POISON, DamageType.POISON),
    (ConditionType.RESISTANT_PSYCHIC, DamageType.PSYCHIC),
    (ConditionType.RESISTANT_RADIANT, DamageType.RADIANT),
    (ConditionType.RESISTANT_SLASHING, DamageType.SLASHING),
    (ConditionType.RESISTANT_THUNDER, DamageType.THUNDER),
):
    define(condition, ongoing(defenses=(DamageDefenseEffect(DamageDefenseType.RESISTANCE, damage_type, operation=CollectionOperation.ADD),)))


def condition_definition(condition: ConditionType) -> ConditionDefinition | None:
    return CONDITION_DEFINITIONS.get(condition)


def condition_ongoing_effects(
    conditions: list[ConditionType],
    explicit_suppressions: list[ConditionType] | None = None,
) -> list[tuple[ConditionType, OngoingEffect]]:
    suppressed = suppressed_conditions(conditions) | set(explicit_suppressions or [])
    return [
        (condition, definition.ongoingEffect)
        for condition in conditions
        if condition not in suppressed
        and (definition := condition_definition(condition)) is not None
    ]


def condition_modifiers(
    conditions: list[ConditionType],
    calculation: CalculationType,
    *,
    scope: ModifierScope = ModifierScope.OWNER,
    ability: AbilityType | None = None,
    explicit_suppressions: list[ConditionType] | None = None,
    pending_conditions: list[ConditionType] | None = None,
) -> list[tuple[ConditionType, Modifier]]:
    matches: list[tuple[ConditionType, Modifier]] = []
    suppressed = suppressed_conditions(conditions) | set(explicit_suppressions or [])
    for condition in conditions:
        if condition in suppressed:
            continue
        definition = condition_definition(condition)
        if definition is None:
            continue
        for entry in definition.ongoingEffect.modifiers:
            if entry.calculation != calculation or entry.scope != scope:
                continue
            ability_predicates = [predicate for predicate in entry.predicates if isinstance(predicate, CalculationAbilityPredicate)]
            if ability_predicates and (ability is None or not all(ability in predicate.abilities for predicate in ability_predicates)):
                continue
            pending_predicates = [predicate for predicate in entry.predicates if isinstance(predicate, PendingEffectAddsConditionPredicate)]
            if pending_predicates and not all(predicate.condition in (pending_conditions or []) for predicate in pending_predicates):
                continue
            matches.append((condition, entry))
    return matches


def prevented_conditions(
    conditions: list[ConditionType],
    explicit_suppressions: list[ConditionType] | None = None,
) -> set[ConditionType]:
    prevented: set[ConditionType] = set()
    suppressed = suppressed_conditions(conditions) | set(explicit_suppressions or [])
    for condition in conditions:
        if condition in suppressed:
            continue
        definition = condition_definition(condition)
        if definition is None:
            continue
        for interaction in definition.ongoingEffect.interactions:
            for operation in interaction.operations:
                if isinstance(operation, PreventCondition):
                    prevented.update(operation.conditions)
    return prevented


def preventing_condition(
    conditions: list[ConditionType],
    prevented_condition: ConditionType,
    explicit_suppressions: list[ConditionType] | None = None,
) -> ConditionType | None:
    suppressed = suppressed_conditions(conditions) | set(explicit_suppressions or [])
    for condition in conditions:
        if condition in suppressed:
            continue
        definition = condition_definition(condition)
        if definition is None:
            continue
        for interaction in definition.ongoingEffect.interactions:
            for operation in interaction.operations:
                if isinstance(operation, PreventCondition) and prevented_condition in operation.conditions:
                    return condition
    return None


def condition_damage_resistances(
    conditions: list[ConditionType],
    explicit_suppressions: list[ConditionType] | None = None,
) -> list[DamageType]:
    result: list[DamageType] = []
    suppressed = suppressed_conditions(conditions) | set(explicit_suppressions or [])
    for condition in conditions:
        if condition in suppressed:
            continue
        definition = condition_definition(condition)
        if definition is None:
            continue
        for defense in definition.ongoingEffect.damageDefenses:
            if defense.defense == DamageDefenseType.RESISTANCE and defense.damageType not in result:
                result.append(defense.damageType)
    return result


def suppressed_conditions(conditions: list[ConditionType]) -> set[ConditionType]:
    suppressed: set[ConditionType] = set()
    for condition in conditions:
        definition = condition_definition(condition)
        if definition is not None:
            suppressed.update(definition.ongoingEffect.suppressedConditions)
    return suppressed


def activation_blocking_condition(
    conditions: list[ConditionType],
    activation: TimeEconomy | None,
    components: list[SpellComponent] | None = None,
    *,
    include_random: bool = False,
) -> ConditionType | None:
    for condition, effect in condition_ongoing_effects(conditions):
        for interaction in effect.interactions:
            if interaction.trigger != ResolutionEventType.ACTION_DECLARED or not any(isinstance(operation, CancelPendingAction) for operation in interaction.operations):
                continue
            matches = True
            for predicate in interaction.predicates:
                if isinstance(predicate, SourceUsesTimeEconomyPredicate) and predicate.timeEconomy != activation:
                    matches = False
                elif isinstance(predicate, SourceHasComponentPredicate) and predicate.component not in (components or []):
                    matches = False
                elif isinstance(predicate, RandomChancePredicate) and not include_random:
                    matches = False
            if matches:
                return condition
    return None


def condition_blocks_all_actions(condition: ConditionType) -> bool:
    definition = condition_definition(condition)
    if definition is None:
        return False
    return any(
        interaction.trigger == ResolutionEventType.ACTION_DECLARED
        and not interaction.predicates
        and any(isinstance(operation, CancelPendingAction) for operation in interaction.operations)
        for interaction in definition.ongoingEffect.interactions
    )


def action_failure_chance(
    conditions: list[ConditionType],
    activation: TimeEconomy | None,
    components: list[SpellComponent],
) -> tuple[ConditionType, RandomChancePredicate] | None:
    for condition, effect in condition_ongoing_effects(conditions):
        for interaction in effect.interactions:
            if interaction.trigger != ResolutionEventType.ACTION_DECLARED or not any(isinstance(operation, CancelPendingAction) for operation in interaction.operations):
                continue
            chance = next((predicate for predicate in interaction.predicates if isinstance(predicate, RandomChancePredicate)), None)
            if chance is None:
                continue
            if any(isinstance(predicate, SourceUsesTimeEconomyPredicate) and predicate.timeEconomy != activation for predicate in interaction.predicates):
                continue
            if any(isinstance(predicate, SourceHasComponentPredicate) and predicate.component not in components for predicate in interaction.predicates):
                continue
            return condition, chance
    return None


def conditions_ending_on_event(
    conditions: list[ConditionType],
    event: ResolutionEventType,
    *,
    is_attack: bool = False,
    is_spell: bool = False,
    deals_damage: bool = False,
) -> list[ConditionType]:
    ending_types: set[EndingConditionType] = set()
    if event == ResolutionEventType.ACTION_DECLARED and is_attack:
        ending_types.add(EndingConditionType.OWNER_ATTACKS)
    if event == ResolutionEventType.SPELL_DECLARED and is_spell:
        ending_types.add(EndingConditionType.OWNER_CASTS_SPELL)
    if event == ResolutionEventType.DAMAGE_APPLIED and deals_damage:
        ending_types.add(EndingConditionType.OWNER_DEALS_DAMAGE)
    return [
        condition
        for condition, effect in condition_ongoing_effects(conditions)
        if any(ending.endingCondition in ending_types for ending in effect.endingConditions)
    ]
