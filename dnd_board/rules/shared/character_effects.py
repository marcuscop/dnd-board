from __future__ import annotations

from dataclasses import dataclass, field, replace
import random

import dnd_board.character_sheet as character_sheet
from dnd_board.character_sheet import (
    AbilityType,
    CharacterSheet,
    ConditionType,
    HitPoints,
    RollModifierBreakdown,
    RollDamageComponent,
    RollPayload,
    RollResolutionMode,
    RollSource,
    SheetSectionType,
    SpellEntry,
    SpellSaveOutcome,
    active_damage_reduction_roll,
    active_spell_damage_roll_modifier_breakdown,
    ability_modifier,
    condition_immunity_blocks,
    damage_after_defenses,
    damage_outcome,
    dice_formula,
    enum_key,
    enum_label,
    spell_damage_action_id,
    spell_condition_action_id,
    spell_healing_action_id,
    spell_casting_ability,
    spell_save_dc,
)
from dnd_board.rules.shared.effects import (
    ActivatedEffect,
    ActiveOngoingEffect,
    ActiveScheduledEffect,
    AppliedEffect,
    AppliedEffectResult,
    AmountScaling,
    ApplyEffect,
    AttackRoll,
    AttackRollEffect,
    ChoiceEffect,
    ConditionalEffect,
    ConditionChangeEffect,
    ConditionOperation,
    CollectionOperation,
    CalculatedAmount,
    CalculationAbilityPredicate,
    CalculationType,
    CombinedAmount,
    ContestedCheck,
    ContestedCheckEffect,
    DamageEffect,
    DamageDefenseEffect,
    DamageDefenseType,
    DiceAmount,
    DerivedAmount,
    EffectEngine,
    EffectExecution,
    EffectExecutionResult,
    EffectAmountInput,
    EffectNode,
    EffectNodeId,
    EffectParticipantBindings,
    EffectResolutionInputs,
    EffectResultValue,
    EndingConditionType,
    EffectTarget,
    FeatureMechanics,
    FixedAmount,
    HealingEffect,
    InstanceScaling,
    MaximumHitPointsEffect,
    MaximumHitPointsOperation,
    MovementEffect,
    MovementType,
    OngoingEffect,
    OngoingEffectId,
    Modifier,
    ModifierScope,
    OwnerWearsArmorPredicate,
    OwnerWearsHeavyArmorPredicate,
    OwnerWieldsExactlyOneOneHandedWeaponPredicate,
    OwnerWieldsShieldPredicate,
    OwnerWieldsWeaponOrShieldPredicate,
    Predicate,
    RepeatedEffect,
    RestEffect,
    ResolutionEvent,
    ResolutionEventType,
    ResolutionEventResponse,
    RollOutcome,
    SavingThrow,
    SavingThrowEffect,
    ScalingBasis,
    ScheduledEffect,
    ScheduledEffectId,
    SequenceEffect,
    TemporaryHitPointsEffect,
    TargetHasAnyCreatureTypePredicate,
    TargetHasCreatureTypePredicate,
    TargetHasConditionPredicate,
    TargetIsOwnerPredicate,
    SourceHasComponentPredicate,
    SourceHasConditionPredicate,
    SourceAttackKindPredicate,
    SourceAttackRangePredicate,
    SourceDamageAbilityModifierPredicate,
    SourceIsAttackPredicate,
    SourceIsSpellPredicate,
    SourceUsesTimeEconomyPredicate,
    SourceWeaponCategoryPredicate,
    SavingThrowAbilityPredicate,
    RollOutcomePredicate,
    RandomChancePredicate,
    WeaponHasPropertyPredicate,
    WeaponHasAnyPropertyPredicate,
    WithinDistancePredicate,
    AttackerIsVisiblePredicate,
    AmountCalculation,
)


@dataclass(frozen=True)
class ResolvedCharacterParticipant:
    sheet: CharacterSheet
    state: CharacterWorkingState


@dataclass(frozen=True)
class ResolvedCharacterEffect:
    hitPoints: HitPoints
    conditions: list[ConditionType]
    damageResistances: list[character_sheet.DamageType]
    damageVulnerabilities: list[character_sheet.DamageType]
    damageImmunities: list[character_sheet.DamageType]
    outcome: str
    appliedEffects: list[AppliedEffectResult]
    sourceHitPoints: HitPoints | None = None
    scheduledEffects: list[ActiveScheduledEffect] = field(default_factory=list)
    ongoingEffects: list[ActiveOngoingEffect] = field(default_factory=list)
    suppressedConditions: list[ConditionType] = field(default_factory=list)
    participants: list[ResolvedCharacterParticipant] = field(default_factory=list)


@dataclass
class CharacterEffectExecution:
    engine: EffectEngine
    execution: EffectExecution
    context: CharacterEffectExecutionContext


@dataclass
class CharacterWorkingState:
    hitPoints: HitPoints
    conditions: list[ConditionType]
    suppressedConditions: list[ConditionType]
    damageResistances: list[character_sheet.DamageType]
    damageVulnerabilities: list[character_sheet.DamageType]
    damageImmunities: list[character_sheet.DamageType]
    ongoingEffects: list[ActiveOngoingEffect]

    @classmethod
    def from_sheet(cls, sheet: CharacterSheet) -> CharacterWorkingState:
        return cls(
            hitPoints=sheet.hp,
            conditions=list(sheet.conditions),
            suppressedConditions=list(sheet.suppressedConditions),
            damageResistances=list(sheet.damageResistances),
            damageVulnerabilities=list(sheet.damageVulnerabilities),
            damageImmunities=list(sheet.damageImmunities),
            ongoingEffects=list(sheet.ongoingEffects),
        )


@dataclass
class PendingDamage:
    nodeId: EffectNodeId
    owningAttackNodeId: EffectNodeId | None
    sourceSheetId: str
    targetSheetId: str
    rolledAmount: int
    currentAmount: int
    effect: DamageEffect


def ability_score(sheet: CharacterSheet, ability: AbilityType) -> int:
    return {
        AbilityType.STRENGTH: sheet.abilityScores.strength,
        AbilityType.DEXTERITY: sheet.abilityScores.dexterity,
        AbilityType.CONSTITUTION: sheet.abilityScores.constitution,
        AbilityType.INTELLIGENCE: sheet.abilityScores.intelligence,
        AbilityType.WISDOM: sheet.abilityScores.wisdom,
        AbilityType.CHARISMA: sheet.abilityScores.charisma,
    }[ability]


class CharacterEffectExecutionContext:
    def __init__(
        self,
        roll: RollPayload,
        target: CharacterSheet,
        source: CharacterSheet | None = None,
        *,
        owner: CharacterSheet | None = None,
        saving_throw_outcomes: dict[EffectNodeId, RollOutcome] | None = None,
        attack_roll_outcomes: dict[EffectNodeId, RollOutcome] | None = None,
        distance_feet: int | None = None,
        attacker_visible: bool | None = None,
    ) -> None:
        self.roll = roll
        self._baseTarget = target
        self._baseSource = source or (target if target.id == roll.sheetId else None)
        self._baseOwner = owner or target
        self._bindings = EffectParticipantBindings(
            sourceSheetId=self._baseSource.id if self._baseSource is not None else target.id,
            targetSheetId=target.id,
            ownerSheetId=self._baseOwner.id,
        )
        self.sheets = {sheet.id: sheet for sheet in (target, self._baseSource, self._baseOwner) if sheet is not None}
        self.participants = {
            sheet_id: CharacterWorkingState.from_sheet(sheet)
            for sheet_id, sheet in self.sheets.items()
        }
        self.outcomes: list[str] = []
        authored_rolls = {entry.effectNodeId: entry.outcome for entry in roll.effectInputs.rolls} if roll.effectInputs else {}
        self.savingThrowOutcomes = {**authored_rolls, **(saving_throw_outcomes or {})}
        self.unaddressedSavingThrowOutcome = (
            RollOutcome.SUCCESS if roll.damageSaveSucceeded else RollOutcome.FAILURE
        ) if not authored_rolls and roll.damageSaveSucceeded is not None else None
        self.attackRollOutcomes = {**authored_rolls, **(attack_roll_outcomes or {})}
        self.attackRollPayloads: dict[EffectNodeId, RollPayload] = {}
        self.unaddressedAttackRoll = roll if roll.resolution == RollResolutionMode.ATTACK_VS_ARMOR_CLASS else None
        self.criticalAttackNodes: set[EffectNodeId] = set()
        self.criticalDamagePreparedNodes: set[EffectNodeId] = set()
        self.pendingDamages: dict[EffectNodeId, PendingDamage] = {}
        self.amountInputs = {entry.effectNodeId: entry.amount for entry in roll.effectInputs.amounts} if roll.effectInputs else {}
        self.distanceFeet = distance_feet
        self.attackerVisible = attacker_visible
        self.lastSavingThrow: SavingThrow | None = None
        self.lastRollOutcome: RollOutcome | None = None
        self.scheduledEffects: list[ActiveScheduledEffect] = []

    @property
    def target(self) -> CharacterSheet:
        return self.sheets[self._bindings.targetSheetId]

    @property
    def source(self) -> CharacterSheet | None:
        return self.sheets.get(self._bindings.sourceSheetId)

    @property
    def owner(self) -> CharacterSheet:
        return self.sheets[self._bindings.ownerSheetId]

    def register_participant(self, sheet: CharacterSheet) -> None:
        self.sheets.setdefault(sheet.id, sheet)
        self.participants.setdefault(sheet.id, CharacterWorkingState.from_sheet(sheet))

    def bind_participants(self, bindings: EffectParticipantBindings | None) -> None:
        self._bindings = bindings or EffectParticipantBindings(
            sourceSheetId=self._baseSource.id if self._baseSource is not None else self._baseTarget.id,
            targetSheetId=self._baseTarget.id,
            ownerSheetId=self._baseOwner.id,
        )
        missing = {
            self._bindings.sourceSheetId,
            self._bindings.targetSheetId,
            self._bindings.ownerSheetId,
        }.difference(self.participants)
        if missing:
            raise ValueError(f"Effect bindings reference unknown participants: {', '.join(sorted(missing))}")

    def prepare_effect(
        self,
        node_id: EffectNodeId,
        effect: EffectNode,
        owning_attack_node_id: EffectNodeId | None,
    ) -> EffectNode:
        if not isinstance(effect, ApplyEffect) or not isinstance(effect.effect, DamageEffect):
            return effect
        existing = self.pendingDamages.get(node_id)
        if existing is not None:
            return ApplyEffect(replace(existing.effect, amount=FixedAmount(existing.currentAmount), scaling=[]))

        damage = effect.effect
        if node_id in self.amountInputs:
            amount = self.amountInputs[node_id]
        elif isinstance(damage.amount, FixedAmount):
            amount = damage.amount.value
        elif isinstance(damage.amount, DerivedAmount):
            return effect
        else:
            amount = self.resolve_runtime_amount(node_id, damage.amount, damage.scaling)
            self.amountInputs[node_id] = amount
        if (
            owning_attack_node_id in self.criticalAttackNodes
            and node_id not in self.criticalDamagePreparedNodes
        ):
            amount += self.resolve_critical_dice(damage.amount, damage.scaling)
            self.amountInputs[node_id] = amount
        prepared = replace(damage, amount=FixedAmount(amount), scaling=[])
        self.pendingDamages[node_id] = PendingDamage(
            nodeId=node_id,
            owningAttackNodeId=owning_attack_node_id,
            sourceSheetId=self.source.id if self.source is not None else self.target.id,
            targetSheetId=self.target.id,
            rolledAmount=amount,
            currentAmount=amount,
            effect=prepared,
        )
        return ApplyEffect(prepared)

    def update_pending_damage(
        self,
        node_id: EffectNodeId,
        pending_effect: EffectNode | None,
        amount: int | None,
    ) -> None:
        pending = self.pendingDamages.get(node_id)
        if pending is None:
            return
        updated_damage = first_damage_effect(pending_effect) if pending_effect is not None else None
        if amount is not None and amount != pending.currentAmount:
            pending.currentAmount = amount
            if updated_damage is not None:
                pending.effect = replace(updated_damage, amount=FixedAmount(amount), scaling=[])
            return
        if updated_damage is not None:
            pending.effect = updated_damage
            if isinstance(updated_damage.amount, FixedAmount):
                pending.currentAmount = updated_damage.amount.value
                return
        if amount is not None:
            pending.currentAmount = amount

    def resolve_critical_dice(
        self,
        amount: FixedAmount | DiceAmount | CalculatedAmount | CombinedAmount | DerivedAmount,
        scaling: list[AmountScaling],
    ) -> int:
        parts = amount.amounts if isinstance(amount, CombinedAmount) else [amount]
        total = sum(
            sum(character_sheet.random.randint(1, part.diceType.value) for _ in range(part.diceCount))
            for part in parts
            if isinstance(part, DiceAmount)
        )
        source = self.source or self.target
        source_spell = self.source_spell()
        for scale in scaling:
            increments = effect_scaling_increments(scale, source, source_spell.level if source_spell else 1, None)
            if scale.additionalDice is not None:
                total += sum(
                    character_sheet.random.randint(1, scale.additionalDice.diceType.value)
                    for _ in range(increments * scale.additionalDice.diceCount)
                )
        return total

    @property
    def targetState(self) -> CharacterWorkingState:
        return self.participants[self.target.id]

    @property
    def sourceState(self) -> CharacterWorkingState | None:
        return self.participants.get(self.source.id) if self.source is not None else None

    @property
    def hitPoints(self) -> HitPoints:
        return self.targetState.hitPoints

    @hitPoints.setter
    def hitPoints(self, value: HitPoints) -> None:
        self.targetState.hitPoints = value

    @property
    def sourceHitPoints(self) -> HitPoints | None:
        return self.sourceState.hitPoints if self.sourceState is not None else None

    @sourceHitPoints.setter
    def sourceHitPoints(self, value: HitPoints) -> None:
        if self.sourceState is None:
            raise ValueError("Source-targeted state requires a source character")
        self.sourceState.hitPoints = value

    @property
    def conditions(self) -> list[ConditionType]:
        return self.targetState.conditions

    @conditions.setter
    def conditions(self, value: list[ConditionType]) -> None:
        self.targetState.conditions = value

    @property
    def suppressedConditions(self) -> list[ConditionType]:
        return self.targetState.suppressedConditions

    @suppressedConditions.setter
    def suppressedConditions(self, value: list[ConditionType]) -> None:
        self.targetState.suppressedConditions = value

    @property
    def damageResistances(self) -> list[character_sheet.DamageType]:
        return self.targetState.damageResistances

    @property
    def damageVulnerabilities(self) -> list[character_sheet.DamageType]:
        return self.targetState.damageVulnerabilities

    @property
    def damageImmunities(self) -> list[character_sheet.DamageType]:
        return self.targetState.damageImmunities

    @property
    def ongoingEffects(self) -> list[ActiveOngoingEffect]:
        return self.targetState.ongoingEffects

    def current_target(self) -> CharacterSheet:
        state = self.targetState
        return replace(
            self.target,
            hp=state.hitPoints,
            conditions=state.conditions,
            suppressedConditions=state.suppressedConditions,
            damageResistances=state.damageResistances,
            damageVulnerabilities=state.damageVulnerabilities,
            damageImmunities=state.damageImmunities,
            ongoingEffects=state.ongoingEffects,
        )

    def apply_effect(
        self,
        node_id: EffectNodeId,
        effect: AppliedEffect,
        previous_results: list[AppliedEffectResult],
    ) -> AppliedEffectResult:
        if isinstance(effect, DamageEffect) and node_id in self.pendingDamages:
            pending_damage = self.pendingDamages[node_id]
            effect = replace(pending_damage.effect, amount=FixedAmount(pending_damage.currentAmount), scaling=[])
        elif node_id in self.amountInputs and isinstance(
            effect,
            (DamageEffect, HealingEffect, TemporaryHitPointsEffect, MaximumHitPointsEffect),
        ) and not isinstance(effect.amount, DerivedAmount):
            effect = replace(effect, amount=FixedAmount(self.amountInputs[node_id]), scaling=[])
        elif isinstance(effect, (DamageEffect, HealingEffect, TemporaryHitPointsEffect, MaximumHitPointsEffect)) and not isinstance(
            effect.amount,
            (FixedAmount, DerivedAmount),
        ):
            amount = self.resolve_runtime_amount(node_id, effect.amount, effect.scaling)
            self.amountInputs[node_id] = amount
            effect = replace(effect, amount=FixedAmount(amount), scaling=[])
        if isinstance(effect, DamageEffect) and isinstance(effect.amount, FixedAmount):
            raw_damage = max(0, effect.amount.value)
            current_target = self.current_target()
            reduction = active_damage_reduction_roll(effect.damageType, current_target)
            adjusted_damage = damage_after_defenses(raw_damage, effect.damageType, current_target, reduction)
            adjusted_damage = max(0, adjusted_damage * effect.multiplierNumerator // effect.multiplierDenominator)
            remaining_damage = adjusted_damage
            next_temporary = max(0, self.hitPoints.temporary - remaining_damage)
            remaining_damage = max(0, remaining_damage - self.hitPoints.temporary)
            self.hitPoints = HitPoints(
                current=max(0, self.hitPoints.current - remaining_damage),
                max=self.hitPoints.max,
                temporary=next_temporary,
            )
            self.outcomes.append(
                damage_outcome(
                    raw_damage,
                    adjusted_damage,
                    effect.damageType,
                    current_target,
                    reduction,
                    effect.multiplierDenominator > effect.multiplierNumerator,
                )
            )
            return AppliedEffectResult(effect=effect, amount=adjusted_damage, effectNodeId=node_id)
        if isinstance(effect, HealingEffect) and isinstance(effect.amount, (FixedAmount, DerivedAmount)):
            healing = max(0, resolved_applied_amount(effect.amount, previous_results))
            if effect.target == EffectTarget.SOURCE:
                if self.sourceHitPoints is None:
                    raise ValueError("Source-targeted healing requires a source character")
                next_current = min(self.sourceHitPoints.max, self.sourceHitPoints.current + healing)
                applied = next_current - self.sourceHitPoints.current
                self.sourceHitPoints = replace(self.sourceHitPoints, current=next_current)
                outcome = f"{self.source.name} heals {applied} hit points" if self.source is not None else f"heals {applied} hit points"
            else:
                next_current = min(self.hitPoints.max, self.hitPoints.current + healing)
                applied = next_current - self.hitPoints.current
                self.hitPoints = replace(self.hitPoints, current=next_current)
                outcome = f"heals {applied} hit points"
            self.outcomes.append(outcome)
            return AppliedEffectResult(effect=effect, amount=applied, effectNodeId=node_id)
        if isinstance(effect, TemporaryHitPointsEffect) and isinstance(effect.amount, FixedAmount):
            temporary = max(0, effect.amount.value)
            self.hitPoints = replace(self.hitPoints, temporary=max(self.hitPoints.temporary, temporary))
            self.outcomes.append(f"gains {temporary} temporary hit points")
            return AppliedEffectResult(effect=effect, amount=temporary, effectNodeId=node_id)
        if isinstance(effect, MaximumHitPointsEffect) and isinstance(effect.amount, (FixedAmount, DerivedAmount)):
            amount = max(0, resolved_applied_amount(effect.amount, previous_results))
            if effect.operation == MaximumHitPointsOperation.INCREASE:
                self.hitPoints = replace(self.hitPoints, max=self.hitPoints.max + amount)
                self.outcomes.append(f"increases Hit Point maximum by {amount}")
            else:
                next_max = max(1, self.hitPoints.max - amount)
                self.hitPoints = replace(self.hitPoints, current=min(self.hitPoints.current, next_max), max=next_max)
                self.outcomes.append(f"reduces Hit Point maximum by {amount}")
            return AppliedEffectResult(effect=effect, amount=amount, effectNodeId=node_id)
        if isinstance(effect, RestEffect):
            self.outcomes.append(f"gains the benefits of a {enum_label(effect.rest)}")
            return AppliedEffectResult(effect=effect, effectNodeId=node_id)
        if isinstance(effect, ConditionChangeEffect):
            label = enum_label(effect.condition)
            if effect.operation == ConditionOperation.ADD:
                if condition_immunity_blocks(self.current_target(), effect.condition):
                    from dnd_board.rules.shared.condition_effects import preventing_condition

                    source_condition = preventing_condition(self.conditions, effect.condition, self.suppressedConditions)
                    suffix = f" due to {enum_label(source_condition)}" if source_condition is not None else ""
                    self.outcomes.append(f"resists {label}{suffix}")
                elif effect.condition not in self.conditions:
                    self.conditions.append(effect.condition)
                    self.outcomes.append(f"gains {label}")
            elif effect.operation == ConditionOperation.REMOVE:
                self.conditions = [condition for condition in self.conditions if condition != effect.condition]
                self.suppressedConditions = [condition for condition in self.suppressedConditions if condition != effect.condition]
                self.outcomes.append(f"loses {label}")
            else:
                if effect.condition in self.conditions and effect.condition not in self.suppressedConditions:
                    self.suppressedConditions.append(effect.condition)
                self.outcomes.append(f"suppresses {label}")
            return AppliedEffectResult(effect=effect, effectNodeId=node_id)
        if isinstance(effect, DamageDefenseEffect):
            defenses = self.damage_defenses(effect.defense)
            if effect.operation == CollectionOperation.ADD and effect.damageType not in defenses:
                defenses.append(effect.damageType)
                self.outcomes.append(f"gains {enum_label(effect.defense).lower()} to {enum_label(effect.damageType)} damage")
            elif effect.operation == CollectionOperation.REMOVE:
                defenses[:] = [damage_type for damage_type in defenses if damage_type != effect.damageType]
                self.outcomes.append(f"loses {enum_label(effect.defense).lower()} to {enum_label(effect.damageType)} damage")
            return AppliedEffectResult(effect=effect, effectNodeId=node_id)
        if isinstance(effect, MovementEffect):
            movement = "is pushed" if effect.movementType == MovementType.FORCED else "teleports"
            self.outcomes.append(f"{movement} {effect.distanceFeet} feet")
            return AppliedEffectResult(effect=effect, amount=effect.distanceFeet, effectNodeId=node_id)
        raise TypeError(f"Character effect context cannot apply {effect.__class__.__name__}")

    def damage_defenses(self, defense: DamageDefenseType) -> list[character_sheet.DamageType]:
        if defense == DamageDefenseType.RESISTANCE:
            return self.damageResistances
        if defense == DamageDefenseType.VULNERABILITY:
            return self.damageVulnerabilities
        return self.damageImmunities

    def resolve_saving_throw(self, node_id: EffectNodeId, saving_throw: SavingThrow) -> RollOutcome | None:
        outcome = self.savingThrowOutcomes.get(node_id)
        if outcome is None and self.unaddressedSavingThrowOutcome is not None:
            outcome = self.unaddressedSavingThrowOutcome
            self.unaddressedSavingThrowOutcome = None
        self.lastSavingThrow = saving_throw
        self.lastRollOutcome = outcome
        return outcome

    def resolve_attack_roll(self, node_id: EffectNodeId, attack: AttackRoll) -> RollOutcome | None:
        outcome = self.attackRollOutcomes.get(node_id)
        if outcome is None and self.unaddressedAttackRoll is not None:
            attack_roll = self.unaddressedAttackRoll
            self.unaddressedAttackRoll = None
            self.attackRollPayloads[node_id] = attack_roll
            natural_roll = resolved_d20(attack_roll)
            hit = natural_roll == 20 or (natural_roll != 1 and attack_roll.total >= self.target.armorClass)
            outcome = RollOutcome.HIT if hit else RollOutcome.MISS
            self.attackRollOutcomes[node_id] = outcome
        self.lastRollOutcome = outcome
        return outcome

    def resolve_runtime_amount(
        self,
        node_id: EffectNodeId,
        amount: DiceAmount | CalculatedAmount | CombinedAmount,
        scaling: list[AmountScaling],
    ) -> int:
        source = self.source or self.target
        parts = amount.amounts if isinstance(amount, CombinedAmount) else [amount]
        total = sum(self.resolve_runtime_amount_part(part, source) for part in parts)
        for scale in scaling:
            increments = effect_scaling_increments(scale, source, self.source_spell().level if self.source_spell() else 1, None)
            if scale.additionalDice is not None:
                total += increments * self.resolve_runtime_amount_part(scale.additionalDice, source)
            total += increments * scale.additionalFixedAmount
        return total

    def resolve_runtime_amount_part(
        self,
        amount: FixedAmount | DiceAmount | CalculatedAmount | DerivedAmount,
        source: CharacterSheet,
    ) -> int:
        if isinstance(amount, FixedAmount):
            return amount.value
        if isinstance(amount, DiceAmount):
            return sum(character_sheet.random.randint(1, amount.diceType.value) for _ in range(amount.diceCount)) + amount.staticBonus
        if isinstance(amount, DerivedAmount):
            raise TypeError("Derived runtime amounts require a preceding applied result")
        if amount.calculation == AmountCalculation.SOURCE_ABILITY_MODIFIER and amount.ability is not None:
            score = ability_score(source, amount.ability)
            value = ability_modifier(score)
        elif amount.calculation == AmountCalculation.SOURCE_SPELLCASTING_MODIFIER:
            spell = self.source_spell()
            if spell is None:
                raise ValueError("Spellcasting modifier amount requires a source spell")
            value = ability_modifier(ability_score(source, spell_casting_ability(source, spell)))
        elif amount.calculation == AmountCalculation.SOURCE_CLASS_LEVEL and amount.characterClass is not None:
            value = sum(level.level for level in source.classes if level.name == amount.characterClass)
        elif amount.calculation == AmountCalculation.SOURCE_CHARACTER_LEVEL:
            value = sum(level.level for level in source.classes)
        elif amount.calculation == AmountCalculation.SOURCE_PROFICIENCY_BONUS:
            value = source.proficiencyBonus
        elif amount.calculation == AmountCalculation.SOURCE_EQUIPPED_SHIELD_ARMOR_CLASS:
            value = max((item.armorClass or 0 for item in source.equipment if item.slot == character_sheet.EquipmentSlot.OFF_HAND), default=0)
        else:
            raise ValueError(f"Incomplete calculated amount: {amount.calculation.name}")
        value *= amount.multiplier
        return max(amount.minimum, value) if amount.minimum is not None else value

    def resolve_contested_check(self, node_id: EffectNodeId, contest: ContestedCheck) -> RollOutcome:
        outcome = self.savingThrowOutcomes.get(node_id)
        if outcome is None:
            raise ValueError("A contested check outcome must be resolved before applying its effect")
        self.lastRollOutcome = outcome
        return outcome

    def record_roll_outcome(self, node_id: EffectNodeId, effect: EffectNode, outcome: RollOutcome) -> None:
        self.lastRollOutcome = outcome
        if isinstance(effect, AttackRollEffect):
            attack_roll = self.attackRollPayloads.get(node_id, self.roll)
            self.outcomes.append(
                "critically hits"
                if outcome == RollOutcome.HIT and attack_roll.criticalHit
                else "hits"
                if outcome == RollOutcome.HIT
                else "misses"
            )

    def evaluate_predicates(self, node_id: EffectNodeId, predicates: list[Predicate]) -> bool:
        for predicate in predicates:
            if isinstance(predicate, TargetIsOwnerPredicate):
                if (self.target.id == self.owner.id) != predicate.expected:
                    return False
            elif isinstance(predicate, SourceIsAttackPredicate):
                if self.roll.source.section != SheetSectionType.ATTACKS and self.roll.resolution != RollResolutionMode.ATTACK_VS_ARMOR_CLASS:
                    return False
            elif isinstance(predicate, SourceIsSpellPredicate):
                if self.roll.source.section != SheetSectionType.SPELLS:
                    return False
            elif isinstance(predicate, SourceHasComponentPredicate):
                source_spell = self.source_spell()
                if source_spell is None or predicate.component not in source_spell.components:
                    return False
            elif isinstance(predicate, TargetHasConditionPredicate):
                if predicate.condition not in self.conditions or predicate.condition in self.suppressedConditions:
                    return False
            elif isinstance(predicate, SourceHasConditionPredicate):
                if (
                    self.source is None
                    or predicate.condition not in self.source.conditions
                    or predicate.condition in self.source.suppressedConditions
                ):
                    return False
            elif isinstance(predicate, TargetHasCreatureTypePredicate):
                if predicate.creatureType not in self.target.creatureTypes:
                    return False
            elif isinstance(predicate, TargetHasAnyCreatureTypePredicate):
                if not any(creature_type in self.target.creatureTypes for creature_type in predicate.creatureTypes):
                    return False
            elif isinstance(predicate, SavingThrowAbilityPredicate):
                ability = self.lastSavingThrow.ability if self.lastSavingThrow is not None else self.roll.damageSavingThrow
                if ability not in predicate.abilities:
                    return False
            elif isinstance(predicate, CalculationAbilityPredicate):
                ability = self.lastSavingThrow.ability if self.lastSavingThrow is not None else self.roll.damageSavingThrow
                if ability not in predicate.abilities:
                    return False
            elif isinstance(predicate, RollOutcomePredicate):
                outcome = self.lastRollOutcome
                if outcome is None and self.roll.damageSaveSucceeded is not None:
                    outcome = RollOutcome.SUCCESS if self.roll.damageSaveSucceeded else RollOutcome.FAILURE
                if outcome != predicate.outcome:
                    return False
            elif isinstance(predicate, WeaponHasPropertyPredicate):
                source_attack = self.source_attack()
                if source_attack is None or predicate.property not in (source_attack.properties or []):
                    return False
            elif isinstance(predicate, WeaponHasAnyPropertyPredicate):
                source_attack = self.source_attack()
                if source_attack is None or not set(predicate.properties).intersection(source_attack.properties or []):
                    return False
            elif isinstance(predicate, SourceAttackRangePredicate):
                source_attack = self.source_attack()
                if source_attack is None or source_attack.attackRange != predicate.attackRange:
                    return False
            elif isinstance(predicate, SourceWeaponCategoryPredicate):
                source_attack = self.source_attack()
                if source_attack is None or source_attack.weaponCategory != predicate.weaponCategory:
                    return False
            elif isinstance(predicate, SourceAttackKindPredicate):
                source_attack = self.source_attack()
                if source_attack is None or source_attack.attackKind != predicate.attackKind:
                    return False
            elif isinstance(predicate, SourceDamageAbilityModifierPredicate):
                source_attack = self.source_attack()
                if source_attack is None or source_attack.damageAbilityModifier != predicate.mode:
                    return False
            elif isinstance(predicate, WithinDistancePredicate):
                # Target selection remains the manual geometry boundary until a board geometry engine exists.
                if self.distanceFeet is not None and self.distanceFeet > predicate.distanceFeet:
                    return False
            elif isinstance(predicate, AttackerIsVisiblePredicate):
                visible = self.attackerVisible
                if visible is None:
                    source_is_invisible = (
                        self.source is not None
                        and ConditionType.INVISIBLE in self.source.conditions
                        and ConditionType.INVISIBLE not in self.source.suppressedConditions
                    )
                    target_sees_invisible = (
                        ConditionType.SEE_INVISIBILITY in self.target.conditions
                        and ConditionType.SEE_INVISIBILITY not in self.target.suppressedConditions
                    )
                    visible = not source_is_invisible or target_sees_invisible
                if not visible:
                    return False
            elif isinstance(predicate, OwnerWearsArmorPredicate):
                if bool(character_sheet.worn_armor(self.owner.equipment)) != predicate.expected:
                    return False
            elif isinstance(predicate, OwnerWearsHeavyArmorPredicate):
                wears_heavy = any(
                    item.itemType == character_sheet.EquipmentType.ARMOR
                    and item.slot == character_sheet.EquipmentSlot.ARMOR
                    and item.armorCategory == character_sheet.ArmorCategory.HEAVY
                    for item in self.owner.equipment
                )
                if wears_heavy != predicate.expected:
                    return False
            elif isinstance(predicate, OwnerWieldsShieldPredicate):
                wields_shield = any(
                    item.itemType == character_sheet.EquipmentType.SHIELD
                    and item.slot in {character_sheet.EquipmentSlot.MAIN_HAND, character_sheet.EquipmentSlot.OFF_HAND}
                    for item in self.owner.equipment
                )
                if wields_shield != predicate.expected:
                    return False
            elif isinstance(predicate, OwnerWieldsExactlyOneOneHandedWeaponPredicate):
                weapons = [
                    item for item in self.owner.equipment
                    if item.itemType == character_sheet.EquipmentType.WEAPON
                    and item.slot in {character_sheet.EquipmentSlot.MAIN_HAND, character_sheet.EquipmentSlot.OFF_HAND, character_sheet.EquipmentSlot.TWO_HANDS}
                ]
                if len(weapons) != 1 or weapons[0].slot == character_sheet.EquipmentSlot.TWO_HANDS:
                    return False
            elif isinstance(predicate, OwnerWieldsWeaponOrShieldPredicate):
                if not any(
                    item.itemType in {character_sheet.EquipmentType.WEAPON, character_sheet.EquipmentType.SHIELD}
                    and item.slot in {character_sheet.EquipmentSlot.MAIN_HAND, character_sheet.EquipmentSlot.OFF_HAND, character_sheet.EquipmentSlot.TWO_HANDS}
                    for item in self.owner.equipment
                ):
                    return False
            elif isinstance(predicate, SourceUsesTimeEconomyPredicate):
                if self.source_time_economy() != predicate.timeEconomy:
                    return False
            elif isinstance(predicate, RandomChancePredicate):
                if random.randint(1, predicate.denominator) > predicate.numerator:
                    return False
        return True

    def source_spell(self) -> SpellEntry | None:
        if self.source is None or self.roll.source.section != SheetSectionType.SPELLS:
            return None
        return next(
            (
                spell
                for spell in [*self.source.spells, *self.source.spellbook]
                if enum_key(spell.id) == self.roll.source.sourceId
            ),
            None,
        )

    def source_attack(self):
        if self.source is None:
            return None
        return next((attack for attack in self.source.attacks if attack.id == self.roll.source.sourceId), None)

    def source_time_economy(self):
        spell = self.source_spell()
        if spell is not None:
            return spell.castingTime
        attack = self.source_attack()
        return attack.activation if attack is not None else None

    def resolve_instance_count(self, instances: InstanceScaling) -> int:
        raise TypeError("Damage instances must be selected before rolling")

    def choose_effects(self, choice: ChoiceEffect) -> list[EffectNode]:
        raise TypeError("Effect choices must be selected before rolling")

    def schedule_effect(self, node_id: EffectNodeId, effect: ScheduledEffect) -> None:
        source_sheet_id = self.source.id if self.source is not None else self.target.id
        self.scheduledEffects.append(ActiveScheduledEffect(
            id=ScheduledEffectId(self.roll.createdAt, node_id),
            sourceSheetId=source_sheet_id,
            targetSheetId=self.target.id,
            sourceLabel=self.roll.sourceLabel,
            effect=effect,
            remainingOccurrences=effect.occurrences.count if effect.occurrences is not None else None,
        ))

    def install_ongoing_effect(self, node_id: EffectNodeId, effect: OngoingEffect) -> None:
        source_sheet_id = self.source.id if self.source is not None else self.target.id
        self.ongoingEffects.append(ActiveOngoingEffect(
            id=OngoingEffectId(self.roll.createdAt, node_id),
            sourceSheetId=source_sheet_id,
            targetSheetId=self.target.id,
            sourceLabel=self.roll.sourceLabel,
            effect=effect,
        ))


def execute_pending_character_effect(
    roll: RollPayload,
    target: CharacterSheet,
    source: CharacterSheet | None = None,
) -> ResolvedCharacterEffect:
    if roll.pendingEffect is None:
        raise ValueError("Roll has no pending effect")
    context = CharacterEffectExecutionContext(roll, target, source)
    result = EffectEngine().resolve(roll.pendingEffect, context)
    return resolved_character_effect(context, result)


def start_character_effect_execution(
    roll: RollPayload,
    target: CharacterSheet,
    source: CharacterSheet | None = None,
) -> CharacterEffectExecution:
    if roll.pendingEffect is None:
        raise ValueError("Roll has no pending effect")
    engine = EffectEngine()
    context = CharacterEffectExecutionContext(roll, target, source)
    bindings = EffectParticipantBindings(
        sourceSheetId=context.source.id if context.source is not None else target.id,
        targetSheetId=target.id,
        ownerSheetId=context.owner.id,
    )
    return CharacterEffectExecution(
        engine=engine,
        execution=engine.start(
            roll.pendingEffect,
            ResolutionEventType.SPELL_DECLARED
            if roll.source.section == SheetSectionType.SPELLS
            else ResolutionEventType.ACTION_DECLARED,
            bindings,
        ),
        context=context,
    )


def advance_character_effect_execution(
    active: CharacterEffectExecution,
    response: ResolutionEventResponse | None = None,
) -> ResolutionEvent | ResolvedCharacterEffect:
    advanced = active.engine.advance(active.execution, active.context, response)
    if isinstance(advanced, EffectExecutionResult):
        return resolved_character_effect(active.context, advanced)
    return advanced


def resolved_character_effect(
    context: CharacterEffectExecutionContext,
    result: EffectExecutionResult,
) -> ResolvedCharacterEffect:
    from dnd_board.rules.shared.condition_effects import suppressed_conditions

    derived_suppressions = suppressed_conditions(context.conditions)
    context.suppressedConditions = list(dict.fromkeys([
        *context.suppressedConditions,
        *(condition for condition in context.conditions if condition in derived_suppressions),
    ]))
    return ResolvedCharacterEffect(
        hitPoints=context.hitPoints,
        conditions=context.conditions,
        damageResistances=context.damageResistances,
        damageVulnerabilities=context.damageVulnerabilities,
        damageImmunities=context.damageImmunities,
        outcome="; ".join(context.outcomes) if context.outcomes else "has no effect",
        appliedEffects=result.appliedEffects,
        sourceHitPoints=context.sourceHitPoints,
        scheduledEffects=context.scheduledEffects,
        ongoingEffects=context.ongoingEffects,
        suppressedConditions=context.suppressedConditions,
        participants=[
            ResolvedCharacterParticipant(context.sheets[sheet_id], state)
            for sheet_id, state in context.participants.items()
        ],
    )


def resolved_applied_amount(amount: FixedAmount | DerivedAmount, previous_results: list[AppliedEffectResult]) -> int:
    if isinstance(amount, FixedAmount):
        return amount.value
    if amount.result not in {EffectResultValue.DAMAGE_ROLLED, EffectResultValue.DAMAGE_APPLIED}:
        raise TypeError(f"Character healing cannot derive from {amount.result.name}")
    source_result = next(
        (result for result in reversed(previous_results) if isinstance(result.effect, DamageEffect) and result.amount is not None),
        None,
    )
    if source_result is None or source_result.amount is None:
        raise ValueError("Derived healing requires a previous damage result")
    return source_result.amount * amount.numerator // amount.denominator


def active_ongoing_modifiers(
    sheet: CharacterSheet,
    calculation: CalculationType,
    *,
    scope: ModifierScope = ModifierScope.OWNER,
    ability: character_sheet.AbilityType | None = None,
) -> list[tuple[ActiveOngoingEffect, Modifier]]:
    matches: list[tuple[ActiveOngoingEffect, Modifier]] = []
    for active in sheet.ongoingEffects:
        for modifier in active.effect.modifiers:
            if modifier.calculation != calculation or modifier.scope != scope:
                continue
            ability_predicates = [predicate for predicate in modifier.predicates if isinstance(predicate, CalculationAbilityPredicate)]
            if ability_predicates and (ability is None or not all(ability in predicate.abilities for predicate in ability_predicates)):
                continue
            matches.append((active, modifier))
    return matches


def ongoing_effects_after_ending(
    active_effects: list[ActiveOngoingEffect],
    ending: EndingConditionType,
    *,
    source_sheet_id: str | None = None,
    target_sheet_id: str | None = None,
) -> list[ActiveOngoingEffect]:
    return [
        active
        for active in active_effects
        if not (
            (source_sheet_id is None or active.sourceSheetId == source_sheet_id)
            and (target_sheet_id is None or active.targetSheetId == target_sheet_id)
            and any(condition.endingCondition == ending for condition in active.effect.endingConditions)
        )
    ]


def resolved_d20(roll: RollPayload) -> int:
    if not roll.dice:
        return 0
    if roll.die == "2d20kh1":
        return max(roll.dice)
    if roll.die == "2d20kl1":
        return min(roll.dice)
    return roll.dice[0]
def direct_damage_effect_at(mechanics: FeatureMechanics, effect_index: int) -> DamageEffect | None:
    root = direct_damage_action_at(mechanics, effect_index)
    return first_damage_effect(root)


def direct_damage_action_at(mechanics: FeatureMechanics, effect_index: int) -> EffectNode | None:
    return direct_action_at(mechanics, effect_index, DamageEffect)


def activated_effect_node(effect: EffectNode | None) -> EffectNode | None:
    return effect.effect if isinstance(effect, ActivatedEffect) else effect


def activated_effect_label(effect: EffectNode | None, fallback: str) -> str:
    return effect.label if isinstance(effect, ActivatedEffect) and effect.label else fallback


def direct_target_creature_types(effect: EffectNode | None) -> list[character_sheet.CreatureType] | None:
    if isinstance(effect, ActivatedEffect):
        return direct_target_creature_types(effect.effect)
    if isinstance(effect, ConditionalEffect):
        for predicate in effect.predicates:
            if isinstance(predicate, TargetHasCreatureTypePredicate):
                return [predicate.creatureType]
            if isinstance(predicate, TargetHasAnyCreatureTypePredicate):
                return list(predicate.creatureTypes)
        return direct_target_creature_types(effect.whenTrue)
    return None


def direct_action_at(mechanics: FeatureMechanics, effect_index: int, effect_type: type[AppliedEffect]) -> EffectNode | None:
    actions = [
        root
        for root in mechanics.activatedEffects
        if first_applied_effect(root, effect_type) is not None
        and not (effect_type is ConditionChangeEffect and first_applied_effect(root, DamageEffect) is not None)
    ]
    if effect_index < 0 or effect_index >= len(actions):
        return None
    return actions[effect_index]


def first_damage_effect(effect: EffectNode | None) -> DamageEffect | None:
    applied = first_applied_effect(effect, DamageEffect)
    return applied if isinstance(applied, DamageEffect) else None


def first_saving_throw_effect(effect: EffectNode | None) -> SavingThrowEffect | None:
    if isinstance(effect, ActivatedEffect):
        return first_saving_throw_effect(effect.effect)
    if isinstance(effect, SavingThrowEffect):
        return effect
    children: list[EffectNode | None] = []
    if isinstance(effect, SequenceEffect):
        children = list(effect.effects)
    elif isinstance(effect, AttackRollEffect):
        children = [effect.onHit, effect.onMiss]
    elif isinstance(effect, ConditionalEffect):
        children = [effect.whenTrue, effect.whenFalse]
    elif isinstance(effect, ContestedCheckEffect):
        children = [effect.onSourceWin, effect.onTargetWin]
    elif isinstance(effect, RepeatedEffect):
        children = [effect.effect]
    elif isinstance(effect, ChoiceEffect):
        children = [choice.effect for choice in effect.choices]
    for child in children:
        if (saving_throw := first_saving_throw_effect(child)) is not None:
            return saving_throw
    return None


def next_unresolved_saving_throw(
    effect: EffectNode | None,
    outcomes: dict[EffectNodeId, RollOutcome],
    *,
    attack_outcome: RollOutcome | None = None,
    predicate_matches=None,
    node_id: EffectNodeId = EffectNodeId(()),
) -> tuple[EffectNodeId, SavingThrowEffect] | None:
    if isinstance(effect, ActivatedEffect):
        return next_unresolved_saving_throw(
            effect.effect,
            outcomes,
            attack_outcome=attack_outcome,
            predicate_matches=predicate_matches,
            node_id=node_id.child(0),
        )
    if isinstance(effect, SavingThrowEffect):
        outcome = outcomes.get(node_id)
        if outcome is None:
            return node_id, effect
        branch_index = 1 if outcome == RollOutcome.SUCCESS else 0
        branch = effect.onSuccess if branch_index == 1 else effect.onFailure
        return next_unresolved_saving_throw(
            branch,
            outcomes,
            attack_outcome=attack_outcome,
            predicate_matches=predicate_matches,
            node_id=node_id.child(branch_index),
        )
    if isinstance(effect, SequenceEffect):
        for index, child in enumerate(effect.effects):
            found = next_unresolved_saving_throw(
                child,
                outcomes,
                attack_outcome=attack_outcome,
                predicate_matches=predicate_matches,
                node_id=node_id.child(index),
            )
            if found is not None:
                return found
        return None
    if isinstance(effect, AttackRollEffect):
        outcome = outcomes.get(node_id, attack_outcome)
        if outcome is None:
            return None
        branch_index = 0 if outcome == RollOutcome.HIT else 1
        branch = effect.onHit if branch_index == 0 else effect.onMiss
        return next_unresolved_saving_throw(
            branch,
            outcomes,
            attack_outcome=attack_outcome,
            predicate_matches=predicate_matches,
            node_id=node_id.child(branch_index),
        )
    if isinstance(effect, ContestedCheckEffect):
        outcome = outcomes.get(node_id)
        if outcome is None:
            return None
        branch_index = 0 if outcome == RollOutcome.SUCCESS else 1
        branch = effect.onSourceWin if branch_index == 0 else effect.onTargetWin
        return next_unresolved_saving_throw(
            branch,
            outcomes,
            attack_outcome=attack_outcome,
            predicate_matches=predicate_matches,
            node_id=node_id.child(branch_index),
        )
    if isinstance(effect, ConditionalEffect):
        if predicate_matches is None:
            return None
        matched = predicate_matches(node_id, effect.predicates)
        branch = effect.whenTrue if matched else effect.whenFalse
        return next_unresolved_saving_throw(
            branch,
            outcomes,
            attack_outcome=attack_outcome,
            predicate_matches=predicate_matches,
            node_id=node_id.child(0 if matched else 1),
        )
    if isinstance(effect, RepeatedEffect):
        return next_unresolved_saving_throw(
            effect.effect,
            outcomes,
            attack_outcome=attack_outcome,
            predicate_matches=predicate_matches,
            node_id=node_id.child(0),
        )
    return None


def first_attack_roll_effect(effect: EffectNode | None) -> AttackRollEffect | None:
    if isinstance(effect, ActivatedEffect):
        return first_attack_roll_effect(effect.effect)
    if isinstance(effect, AttackRollEffect):
        return effect
    children: list[EffectNode | None] = []
    if isinstance(effect, SequenceEffect):
        children = list(effect.effects)
    elif isinstance(effect, SavingThrowEffect):
        children = [effect.onFailure, effect.onSuccess]
    elif isinstance(effect, ConditionalEffect):
        children = [effect.whenTrue, effect.whenFalse]
    elif isinstance(effect, ContestedCheckEffect):
        children = [effect.onSourceWin, effect.onTargetWin]
    elif isinstance(effect, RepeatedEffect):
        children = [effect.effect]
    elif isinstance(effect, ChoiceEffect):
        children = [choice.effect for choice in effect.choices]
    for child in children:
        if (attack := first_attack_roll_effect(child)) is not None:
            return attack
    return None


def first_contested_check_effect(
    effect: EffectNode | None,
    node_id: EffectNodeId = EffectNodeId(()),
) -> tuple[EffectNodeId, ContestedCheckEffect] | None:
    if isinstance(effect, ActivatedEffect):
        return first_contested_check_effect(effect.effect, node_id.child(0))
    if isinstance(effect, ContestedCheckEffect):
        return node_id, effect
    children: list[tuple[int, EffectNode | None]] = []
    if isinstance(effect, SequenceEffect):
        children = list(enumerate(effect.effects))
    elif isinstance(effect, SavingThrowEffect):
        children = [(0, effect.onFailure), (1, effect.onSuccess)]
    elif isinstance(effect, AttackRollEffect):
        children = [(0, effect.onHit), (1, effect.onMiss)]
    elif isinstance(effect, ConditionalEffect):
        children = [(0, effect.whenTrue), (1, effect.whenFalse)]
    elif isinstance(effect, RepeatedEffect):
        children = [(0, effect.effect)]
    elif isinstance(effect, ChoiceEffect):
        children = [(index, choice.effect) for index, choice in enumerate(effect.choices)]
    for index, child in children:
        if (found := first_contested_check_effect(child, node_id.child(index))) is not None:
            return found
    return None


def distinct_damage_effects(effect: EffectNode | None) -> list[DamageEffect]:
    found: list[DamageEffect] = []

    def visit(node: EffectNode | None) -> None:
        if isinstance(node, ActivatedEffect):
            visit(node.effect)
        elif isinstance(node, ApplyEffect) and isinstance(node.effect, DamageEffect):
            if not any(
                existing.damageType == node.effect.damageType
                and existing.amount == node.effect.amount
                and existing.scaling == node.effect.scaling
                for existing in found
            ):
                found.append(node.effect)
        elif isinstance(node, SequenceEffect):
            for child in node.effects:
                visit(child)
        elif isinstance(node, SavingThrowEffect):
            visit(node.onFailure)
            visit(node.onSuccess)
        elif isinstance(node, AttackRollEffect):
            visit(node.onHit)
            visit(node.onMiss)
        elif isinstance(node, ConditionalEffect):
            visit(node.whenTrue)
            visit(node.whenFalse)
        elif isinstance(node, ContestedCheckEffect):
            visit(node.onSourceWin)
            visit(node.onTargetWin)
        elif isinstance(node, RepeatedEffect):
            visit(node.effect)

    visit(effect)
    return found


def damage_effect_nodes(
    effect: EffectNode | None,
    node_id: EffectNodeId = EffectNodeId(()),
) -> list[tuple[EffectNodeId, DamageEffect]]:
    if isinstance(effect, ActivatedEffect):
        return damage_effect_nodes(effect.effect, node_id.child(0))
    if isinstance(effect, ApplyEffect) and isinstance(effect.effect, DamageEffect):
        return [(node_id, effect.effect)]
    children: list[tuple[int, EffectNode | None]] = []
    if isinstance(effect, SequenceEffect):
        children = list(enumerate(effect.effects))
    elif isinstance(effect, SavingThrowEffect):
        children = [(0, effect.onFailure), (1, effect.onSuccess)]
    elif isinstance(effect, AttackRollEffect):
        children = [(0, effect.onHit), (1, effect.onMiss)]
    elif isinstance(effect, ConditionalEffect):
        children = [(0, effect.whenTrue), (1, effect.whenFalse)]
    elif isinstance(effect, ContestedCheckEffect):
        children = [(0, effect.onSourceWin), (1, effect.onTargetWin)]
    elif isinstance(effect, RepeatedEffect):
        children = [(0, effect.effect)]
    elif isinstance(effect, ChoiceEffect):
        children = [(index, choice.effect) for index, choice in enumerate(effect.choices)]
    return [
        found
        for index, child in children
        for found in damage_effect_nodes(child, node_id.child(index))
    ]


def damage_effect_roll_groups(
    effect: EffectNode | None,
    node_id: EffectNodeId = EffectNodeId(()),
) -> list[tuple[list[EffectNodeId], DamageEffect]]:
    if isinstance(effect, ActivatedEffect):
        return damage_effect_roll_groups(effect.effect, node_id.child(0))
    if isinstance(effect, ApplyEffect) and isinstance(effect.effect, DamageEffect):
        return [([node_id], effect.effect)]
    if isinstance(effect, SequenceEffect):
        return [
            group
            for index, child in enumerate(effect.effects)
            for group in damage_effect_roll_groups(child, node_id.child(index))
        ]
    branches: list[tuple[int, EffectNode | None]] = []
    if isinstance(effect, SavingThrowEffect):
        branches = [(0, effect.onFailure), (1, effect.onSuccess)]
    elif isinstance(effect, AttackRollEffect):
        branches = [(0, effect.onHit), (1, effect.onMiss)]
    elif isinstance(effect, ConditionalEffect):
        branches = [(0, effect.whenTrue), (1, effect.whenFalse)]
    elif isinstance(effect, ContestedCheckEffect):
        branches = [(0, effect.onSourceWin), (1, effect.onTargetWin)]
    elif isinstance(effect, ChoiceEffect):
        branches = [(index, choice.effect) for index, choice in enumerate(effect.choices)]
    elif isinstance(effect, RepeatedEffect):
        return damage_effect_roll_groups(effect.effect, node_id.child(0))
    groups: list[tuple[list[EffectNodeId], DamageEffect]] = []
    for index, branch in branches:
        for addresses, damage in damage_effect_roll_groups(branch, node_id.child(index)):
            matching_index = next(
                (
                    position
                    for position, (_existing, candidate) in enumerate(groups)
                    if damage_roll_spec_matches(candidate, damage)
                ),
                None,
            )
            if matching_index is None:
                groups.append((addresses, damage))
            else:
                existing_addresses, existing_damage = groups[matching_index]
                groups[matching_index] = ([*existing_addresses, *addresses], existing_damage)
    return groups


def damage_roll_spec_matches(left: DamageEffect, right: DamageEffect) -> bool:
    return (
        left.amount == right.amount
        and left.damageType == right.damageType
        and left.scaling == right.scaling
        and left.target == right.target
    )


def first_applied_effect(effect: EffectNode | None, effect_type: type[AppliedEffect]) -> AppliedEffect | None:
    if isinstance(effect, ActivatedEffect):
        return first_applied_effect(effect.effect, effect_type)
    if isinstance(effect, ApplyEffect) and isinstance(effect.effect, effect_type):
        return effect.effect
    if isinstance(effect, SequenceEffect):
        return next((applied for child in effect.effects if (applied := first_applied_effect(child, effect_type)) is not None), None)
    if isinstance(effect, SavingThrowEffect):
        return first_applied_effect(effect.onFailure, effect_type) or first_applied_effect(effect.onSuccess, effect_type)
    if isinstance(effect, AttackRollEffect):
        return first_applied_effect(effect.onHit, effect_type) or first_applied_effect(effect.onMiss, effect_type)
    if isinstance(effect, ConditionalEffect):
        return first_applied_effect(effect.whenTrue, effect_type) or first_applied_effect(effect.whenFalse, effect_type)
    if isinstance(effect, ContestedCheckEffect):
        return first_applied_effect(effect.onSourceWin, effect_type) or first_applied_effect(effect.onTargetWin, effect_type)
    if isinstance(effect, RepeatedEffect):
        return first_applied_effect(effect.effect, effect_type)
    if isinstance(effect, ChoiceEffect):
        return next(
            (
                applied
                for choice in effect.choices
                if (applied := first_applied_effect(choice.effect, effect_type)) is not None
            ),
            None,
        )
    return None


def effect_targets_only_source(effect: EffectNode) -> bool:
    targets = applied_effect_targets(effect)
    return bool(targets) and targets == {EffectTarget.SOURCE}


def applied_effect_targets(effect: EffectNode | None) -> set[EffectTarget]:
    if isinstance(effect, ActivatedEffect):
        return applied_effect_targets(effect.effect)
    if isinstance(effect, ApplyEffect):
        return {effect.effect.target}
    if isinstance(effect, SequenceEffect):
        return set().union(*(applied_effect_targets(child) for child in effect.effects))
    if isinstance(effect, SavingThrowEffect):
        return applied_effect_targets(effect.onFailure) | applied_effect_targets(effect.onSuccess)
    if isinstance(effect, AttackRollEffect):
        return applied_effect_targets(effect.onHit) | applied_effect_targets(effect.onMiss)
    if isinstance(effect, ConditionalEffect):
        return applied_effect_targets(effect.whenTrue) | applied_effect_targets(effect.whenFalse)
    if isinstance(effect, ContestedCheckEffect):
        return applied_effect_targets(effect.onSourceWin) | applied_effect_targets(effect.onTargetWin)
    if isinstance(effect, RepeatedEffect):
        return applied_effect_targets(effect.effect)
    if isinstance(effect, ChoiceEffect):
        return set().union(*(applied_effect_targets(choice.effect) for choice in effect.choices))
    return set()


def added_condition_types(effect: EffectNode | None) -> list[ConditionType]:
    conditions: list[ConditionType] = []

    def visit(node: EffectNode | None) -> None:
        if isinstance(node, ActivatedEffect):
            visit(node.effect)
        elif isinstance(node, ApplyEffect) and isinstance(node.effect, ConditionChangeEffect):
            if node.effect.operation == ConditionOperation.ADD and node.effect.condition not in conditions:
                conditions.append(node.effect.condition)
        elif isinstance(node, SequenceEffect):
            for child in node.effects:
                visit(child)
        elif isinstance(node, SavingThrowEffect):
            visit(node.onFailure)
            visit(node.onSuccess)
        elif isinstance(node, AttackRollEffect):
            visit(node.onHit)
            visit(node.onMiss)
        elif isinstance(node, ConditionalEffect):
            visit(node.whenTrue)
            visit(node.whenFalse)
        elif isinstance(node, ContestedCheckEffect):
            visit(node.onSourceWin)
            visit(node.onTargetWin)
        elif isinstance(node, RepeatedEffect):
            visit(node.effect)
        elif isinstance(node, ChoiceEffect):
            for choice in node.choices:
                visit(choice.effect)

    visit(effect)
    return conditions


def condition_change_effects(effect: EffectNode | None) -> list[ConditionChangeEffect]:
    changes: list[ConditionChangeEffect] = []

    def visit(node: EffectNode | None) -> None:
        if isinstance(node, ActivatedEffect):
            visit(node.effect)
        elif isinstance(node, ApplyEffect) and isinstance(node.effect, ConditionChangeEffect):
            changes.append(node.effect)
        elif isinstance(node, SequenceEffect):
            for child in node.effects:
                visit(child)
        elif isinstance(node, SavingThrowEffect):
            visit(node.onFailure)
            visit(node.onSuccess)
        elif isinstance(node, AttackRollEffect):
            visit(node.onHit)
            visit(node.onMiss)
        elif isinstance(node, ConditionalEffect):
            visit(node.whenTrue)
            visit(node.whenFalse)
        elif isinstance(node, ContestedCheckEffect):
            visit(node.onSourceWin)
            visit(node.onTargetWin)
        elif isinstance(node, RepeatedEffect):
            visit(node.effect)
        elif isinstance(node, ChoiceEffect):
            for choice in node.choices:
                visit(choice.effect)

    visit(effect)
    return changes


def resolved_damage_effect_node(effect: EffectNode, rolled_damage: int) -> EffectNode:
    return resolved_amount_effect_node(effect, rolled_damage)


def reduced_damage_effect_node(effect: EffectNode, reduction: int) -> EffectNode:
    reduced, _remaining = _reduced_damage_effect_node(effect, max(0, reduction))
    return reduced


def _reduced_damage_effect_node(effect: EffectNode, remaining: int) -> tuple[EffectNode, int]:
    if isinstance(effect, ActivatedEffect):
        child, remaining = _reduced_damage_effect_node(effect.effect, remaining)
        return replace(effect, effect=child), remaining
    if isinstance(effect, ApplyEffect) and isinstance(effect.effect, DamageEffect) and isinstance(effect.effect.amount, FixedAmount):
        reduction = min(max(0, effect.effect.amount.value), remaining)
        return ApplyEffect(replace(effect.effect, amount=FixedAmount(effect.effect.amount.value - reduction))), remaining - reduction
    if isinstance(effect, SequenceEffect):
        children: list[EffectNode] = []
        for child in effect.effects:
            reduced, remaining = _reduced_damage_effect_node(child, remaining)
            children.append(reduced)
        return replace(effect, effects=children), remaining
    if isinstance(effect, SavingThrowEffect):
        failure, _ = _reduced_optional_damage_effect(effect.onFailure, remaining)
        success, _ = _reduced_optional_damage_effect(effect.onSuccess, remaining)
        return replace(effect, onFailure=failure, onSuccess=success), remaining
    if isinstance(effect, AttackRollEffect):
        hit, hit_remaining = _reduced_optional_damage_effect(effect.onHit, remaining)
        return replace(effect, onHit=hit), hit_remaining
    if isinstance(effect, ContestedCheckEffect):
        source_win, _ = _reduced_optional_damage_effect(effect.onSourceWin, remaining)
        target_win, _ = _reduced_optional_damage_effect(effect.onTargetWin, remaining)
        return replace(effect, onSourceWin=source_win, onTargetWin=target_win), remaining
    if isinstance(effect, ConditionalEffect):
        when_true, _ = _reduced_damage_effect_node(effect.whenTrue, remaining)
        when_false, _ = _reduced_optional_damage_effect(effect.whenFalse, remaining)
        return replace(effect, whenTrue=when_true, whenFalse=when_false), remaining
    if isinstance(effect, RepeatedEffect):
        child, remaining = _reduced_damage_effect_node(effect.effect, remaining)
        return replace(effect, effect=child), remaining
    if isinstance(effect, ChoiceEffect):
        return replace(effect, choices=[
            replace(choice, effect=_reduced_damage_effect_node(choice.effect, remaining)[0])
            for choice in effect.choices
        ]), remaining
    return effect, remaining


def _reduced_optional_damage_effect(effect: EffectNode | None, remaining: int) -> tuple[EffectNode | None, int]:
    return _reduced_damage_effect_node(effect, remaining) if effect is not None else (None, remaining)


def resolved_damage_totals_effect_node(effect: EffectNode, totals: dict[character_sheet.DamageType, int]) -> EffectNode:
    if isinstance(effect, ActivatedEffect):
        return replace(effect, effect=resolved_damage_totals_effect_node(effect.effect, totals))
    if isinstance(effect, ApplyEffect) and isinstance(effect.effect, DamageEffect):
        total = totals.get(effect.effect.damageType)
        return ApplyEffect(replace(effect.effect, amount=FixedAmount(total), scaling=[])) if total is not None else effect
    if isinstance(effect, SequenceEffect):
        return replace(effect, effects=[resolved_damage_totals_effect_node(child, totals) for child in effect.effects])
    if isinstance(effect, SavingThrowEffect):
        return replace(
            effect,
            onFailure=resolved_optional_damage_totals_effect(effect.onFailure, totals),
            onSuccess=resolved_optional_damage_totals_effect(effect.onSuccess, totals),
        )
    if isinstance(effect, AttackRollEffect):
        return replace(
            effect,
            onHit=resolved_optional_damage_totals_effect(effect.onHit, totals),
            onMiss=resolved_optional_damage_totals_effect(effect.onMiss, totals),
        )
    if isinstance(effect, ContestedCheckEffect):
        return replace(
            effect,
            onSourceWin=resolved_optional_damage_totals_effect(effect.onSourceWin, totals),
            onTargetWin=resolved_optional_damage_totals_effect(effect.onTargetWin, totals),
        )
    if isinstance(effect, ConditionalEffect):
        return replace(
            effect,
            whenTrue=resolved_damage_totals_effect_node(effect.whenTrue, totals),
            whenFalse=resolved_optional_damage_totals_effect(effect.whenFalse, totals),
        )
    if isinstance(effect, RepeatedEffect):
        return replace(effect, effect=resolved_damage_totals_effect_node(effect.effect, totals))
    if isinstance(effect, ChoiceEffect):
        return replace(effect, choices=[
            replace(choice, effect=resolved_damage_totals_effect_node(choice.effect, totals))
            for choice in effect.choices
        ])
    return effect


def resolved_optional_damage_totals_effect(
    effect: EffectNode | None,
    totals: dict[character_sheet.DamageType, int],
) -> EffectNode | None:
    return resolved_damage_totals_effect_node(effect, totals) if effect is not None else None


def resolved_amount_effect_node(effect: EffectNode, rolled_amount: int) -> EffectNode:
    if isinstance(effect, ActivatedEffect):
        return replace(effect, effect=resolved_amount_effect_node(effect.effect, rolled_amount))
    if isinstance(effect, ApplyEffect) and isinstance(
        effect.effect,
        (DamageEffect, HealingEffect, TemporaryHitPointsEffect, MaximumHitPointsEffect),
    ):
        if isinstance(effect.effect.amount, DerivedAmount):
            return effect
        return ApplyEffect(replace(effect.effect, amount=FixedAmount(rolled_amount), scaling=[]))
    if isinstance(effect, SequenceEffect):
        return replace(effect, effects=[resolved_amount_effect_node(child, rolled_amount) for child in effect.effects])
    if isinstance(effect, SavingThrowEffect):
        return replace(
            effect,
            onFailure=resolved_optional_amount_effect(effect.onFailure, rolled_amount),
            onSuccess=resolved_optional_amount_effect(effect.onSuccess, rolled_amount),
        )
    if isinstance(effect, AttackRollEffect):
        return replace(
            effect,
            onHit=resolved_optional_amount_effect(effect.onHit, rolled_amount),
            onMiss=resolved_optional_amount_effect(effect.onMiss, rolled_amount),
        )
    if isinstance(effect, ContestedCheckEffect):
        return replace(
            effect,
            onSourceWin=resolved_optional_amount_effect(effect.onSourceWin, rolled_amount),
            onTargetWin=resolved_optional_amount_effect(effect.onTargetWin, rolled_amount),
        )
    if isinstance(effect, ConditionalEffect):
        return replace(
            effect,
            whenTrue=resolved_amount_effect_node(effect.whenTrue, rolled_amount),
            whenFalse=resolved_optional_amount_effect(effect.whenFalse, rolled_amount),
        )
    if isinstance(effect, RepeatedEffect):
        return replace(effect, effect=resolved_amount_effect_node(effect.effect, rolled_amount))
    if isinstance(effect, ChoiceEffect):
        return replace(effect, choices=[
            replace(choice, effect=resolved_amount_effect_node(choice.effect, rolled_amount))
            for choice in effect.choices
        ])
    return effect


def resolved_optional_damage_effect(effect: EffectNode | None, rolled_damage: int) -> EffectNode | None:
    return resolved_optional_amount_effect(effect, rolled_damage)


def resolved_optional_amount_effect(effect: EffectNode | None, rolled_amount: int) -> EffectNode | None:
    return resolved_amount_effect_node(effect, rolled_amount) if effect is not None else None


def build_direct_spell_damage_roll_payload(
    sheet: CharacterSheet,
    roller: str,
    spell: SpellEntry,
    effect_index: int,
    spell_slot_level: int | None,
    instance_index: int | None,
    damage_save_succeeded: bool | None,
    choice_index: int | None = None,
) -> RollPayload:
    if spell.mechanics is None:
        raise ValueError("Spell has no direct mechanics")
    root = direct_damage_action_at(spell.mechanics, effect_index)
    authored_label = activated_effect_label(root, "")
    action_label = f"{authored_label} Damage" if authored_label else "Spell Damage"
    core_root = activated_effect_node(root)
    if isinstance(core_root, ChoiceEffect):
        selected_index = choice_index if choice_index is not None else 0
        if selected_index < 0 or selected_index >= len(core_root.choices):
            raise ValueError("Spell effect choice not found")
        root = core_root.choices[selected_index].effect
        core_root = root
    if isinstance(core_root, RepeatedEffect):
        instance_count = scaled_instance_count(core_root.instances, sheet, spell.level, spell_slot_level)
        selected_instance = instance_index if instance_index is not None else 0
        if selected_instance < 0 or selected_instance >= instance_count:
            raise ValueError("Spell damage instance not found")
        if authored_label:
            action_label = f"{authored_label} {selected_instance + 1} Damage"
        root = core_root.effect
        core_root = root
    damage_groups = damage_effect_roll_groups(root)
    if root is None or not damage_groups:
        raise ValueError("Spell damage effect not found")
    components: list[RollDamageComponent] = []
    amount_inputs: list[EffectAmountInput] = []
    for node_ids, damage in damage_groups:
        dice, dice_type, modifier_breakdown, rolled_total = roll_effect_amount(
            damage.amount,
            damage.scaling,
            sheet,
            spell,
            spell_slot_level,
        )
        active_modifiers = active_spell_damage_roll_modifier_breakdown(sheet)
        modifier_breakdown.extend(active_modifiers)
        modifier = sum(part.value for part in modifier_breakdown)
        components.append(RollDamageComponent(
            damageType=damage.damageType,
            dice=dice,
            diceType=dice_type,
            die=dice_formula(len(dice), dice_type),
            modifier=modifier,
            modifierBreakdown=modifier_breakdown,
            total=rolled_total + sum(part.value for part in active_modifiers),
            effectNodeIds=node_ids,
        ))
        amount_inputs.extend(EffectAmountInput(node_id, components[-1].total) for node_id in node_ids)
    primary = components[0]
    total = sum(component.total for component in components)
    saving_throw_effect = first_saving_throw_effect(root)
    saving_throw = saving_throw_effect.savingThrow if saving_throw_effect is not None else None
    created_at = character_sheet.time_ns()
    action_id = spell_damage_action_id(effect_index, spell_slot_level)
    if instance_index is not None:
        action_id = f"{action_id}-instance-{instance_index}"
    pending_effect = root
    effect_inputs = EffectResolutionInputs(amounts=amount_inputs)
    if isinstance(core_root, AttackRollEffect):
        attack_roll = character_sheet.build_spell_attack_roll_payload(sheet, roller, spell)
        return replace(
            attack_roll,
            source=RollSource(
                section=SheetSectionType.SPELLS,
                sourceId=enum_key(spell.id),
                actionId=action_id,
            ),
            label=(f"{authored_label} Damage" if authored_label else enum_label(spell.name)),
            damageType=primary.damageType,
            damageComponents=components,
            damageSavingThrow=saving_throw.ability if saving_throw is not None else None,
            damageSaveDc=spell_save_dc(sheet, spell) if saving_throw is not None else None,
            damageSaveOutcome=direct_damage_save_outcome(root, saving_throw_effect) if saving_throw_effect is not None else None,
            damageSaveSucceeded=damage_save_succeeded,
            damageSaveDisadvantageCreatureTypes=saving_throw.disadvantageCreatureTypes or None if saving_throw is not None else None,
            damageSaveForcedFailureCreatureTypes=saving_throw.forcedFailureCreatureTypes or None if saving_throw is not None else None,
            targetCreatureTypes=direct_target_creature_types(root),
            pendingEffect=pending_effect,
            effectInputs=effect_inputs,
        )
    return RollPayload(
        id=f"roll-{created_at}",
        sheetId=sheet.id,
        tokenId=sheet.tokenId,
        roller=roller,
        source=RollSource(
            section=SheetSectionType.SPELLS,
            sourceId=enum_key(spell.id),
            actionId=action_id,
        ),
        sourceLabel=enum_label(spell.name),
        resolution=RollResolutionMode.APPLY_DAMAGE,
        label=action_label,
        iconUrl=None,
        dice=primary.dice,
        diceType=primary.diceType,
        die="+".join(component.die for component in components),
        modifier=sum(component.modifier for component in components),
        modifierBreakdown=[part for component in components for part in component.modifierBreakdown],
        total=total,
        createdAt=created_at,
        damageType=primary.damageType,
        damageComponents=components if len(components) > 1 else None,
        damageSavingThrow=saving_throw.ability if saving_throw is not None else None,
        damageSaveDc=spell_save_dc(sheet, spell) if saving_throw is not None else None,
        damageSaveOutcome=direct_damage_save_outcome(root, saving_throw_effect) if saving_throw_effect is not None else None,
        damageSaveSucceeded=damage_save_succeeded,
        damageSaveDisadvantageCreatureTypes=saving_throw.disadvantageCreatureTypes or None if saving_throw is not None else None,
        damageSaveForcedFailureCreatureTypes=saving_throw.forcedFailureCreatureTypes or None if saving_throw is not None else None,
        targetCreatureTypes=direct_target_creature_types(root),
        pendingEffect=pending_effect,
        effectInputs=effect_inputs,
    )




def build_direct_spell_healing_roll_payload(
    sheet: CharacterSheet,
    roller: str,
    spell: SpellEntry,
    effect_index: int,
    spell_slot_level: int | None,
) -> RollPayload:
    if spell.mechanics is None:
        raise ValueError("Spell has no direct mechanics")
    root = direct_action_at(spell.mechanics, effect_index, HealingEffect)
    healing = first_applied_effect(root, HealingEffect)
    if root is None or not isinstance(healing, HealingEffect):
        raise ValueError("Spell healing effect not found")
    dice, dice_type, modifier_breakdown, total = roll_effect_amount(
        healing.amount,
        healing.scaling,
        sheet,
        spell,
        spell_slot_level,
    )
    created_at = character_sheet.time_ns()
    return RollPayload(
        id=f"roll-{created_at}",
        sheetId=sheet.id,
        tokenId=sheet.tokenId,
        roller=roller,
        source=RollSource(
            section=SheetSectionType.SPELLS,
            sourceId=enum_key(spell.id),
            actionId=spell_healing_action_id(effect_index, spell_slot_level),
        ),
        sourceLabel=enum_label(spell.name),
        resolution=RollResolutionMode.HEAL_SELF,
        label=activated_effect_label(root, "Healing"),
        iconUrl=None,
        dice=dice,
        diceType=dice_type,
        die=dice_formula(len(dice), dice_type),
        modifier=sum(part.value for part in modifier_breakdown),
        modifierBreakdown=modifier_breakdown,
        total=total,
        createdAt=created_at,
        pendingEffect=resolved_amount_effect_node(root, total),
    )


def build_direct_spell_condition_roll_payload(
    sheet: CharacterSheet,
    roller: str,
    spell: SpellEntry,
    effect_index: int,
    choice_index: int | None = None,
) -> RollPayload:
    if spell.mechanics is None:
        raise ValueError("Spell has no direct mechanics")
    root = direct_action_at(spell.mechanics, effect_index, ConditionChangeEffect)
    action_label = activated_effect_label(root, "Spell Effect")
    core_root = activated_effect_node(root)
    if isinstance(core_root, ChoiceEffect):
        selected_index = choice_index if choice_index is not None else 0
        if selected_index < 0 or selected_index >= len(core_root.choices):
            raise ValueError("Spell effect choice not found")
        root = core_root.choices[selected_index].effect
    condition = first_applied_effect(root, ConditionChangeEffect)
    if root is None or not isinstance(condition, ConditionChangeEffect):
        raise ValueError("Spell condition effect not found")
    saving_throw_effect = first_saving_throw_effect(root)
    saving_throw = saving_throw_effect.savingThrow if saving_throw_effect is not None else None
    created_at = character_sheet.time_ns()
    return RollPayload(
        id=f"roll-{created_at}",
        sheetId=sheet.id,
        tokenId=sheet.tokenId,
        roller=roller,
        source=RollSource(
            section=SheetSectionType.SPELLS,
            sourceId=enum_key(spell.id),
            actionId=spell_condition_action_id(effect_index),
        ),
        sourceLabel=enum_label(spell.name),
        resolution=RollResolutionMode.NONE,
        label=action_label,
        iconUrl=None,
        dice=[],
        diceType=character_sheet.DiceType.D20,
        die="",
        modifier=0,
        modifierBreakdown=[],
        total=0,
        createdAt=created_at,
        damageSavingThrow=saving_throw.ability if saving_throw is not None else None,
        damageSaveDc=spell_save_dc(sheet, spell) if saving_throw is not None else None,
        damageSaveOutcome=SpellSaveOutcome.NEGATES if saving_throw is not None else None,
        damageSaveDisadvantageCreatureTypes=saving_throw.disadvantageCreatureTypes or None if saving_throw is not None else None,
        damageSaveForcedFailureCreatureTypes=saving_throw.forcedFailureCreatureTypes or None if saving_throw is not None else None,
        targetCreatureTypes=direct_target_creature_types(root),
        pendingEffect=root,
    )


def build_direct_spell_temporary_hit_points_roll_payload(
    sheet: CharacterSheet,
    roller: str,
    spell: SpellEntry,
    effect_index: int,
    spell_slot_level: int | None,
) -> RollPayload:
    if spell.mechanics is None:
        raise ValueError("Spell has no direct mechanics")
    root = direct_action_at(spell.mechanics, effect_index, TemporaryHitPointsEffect)
    temporary = first_applied_effect(root, TemporaryHitPointsEffect)
    if root is None or not isinstance(temporary, TemporaryHitPointsEffect):
        raise ValueError("Spell temporary hit point effect not found")
    dice, dice_type, modifier_breakdown, total = roll_effect_amount(
        temporary.amount,
        temporary.scaling,
        sheet,
        spell,
        spell_slot_level,
    )
    created_at = character_sheet.time_ns()
    return RollPayload(
        id=f"roll-{created_at}",
        sheetId=sheet.id,
        tokenId=sheet.tokenId,
        roller=roller,
        source=RollSource(
            section=SheetSectionType.SPELLS,
            sourceId=enum_key(spell.id),
            actionId=f"temporary-hit-points-{effect_index}",
        ),
        sourceLabel=enum_label(spell.name),
        resolution=RollResolutionMode.APPLY_TEMPORARY_HIT_POINTS,
        label="Temporary Hit Points",
        iconUrl=None,
        dice=dice,
        diceType=dice_type,
        die=dice_formula(len(dice), dice_type),
        modifier=sum(part.value for part in modifier_breakdown),
        modifierBreakdown=modifier_breakdown,
        total=total,
        createdAt=created_at,
        pendingEffect=resolved_amount_effect_node(root, total),
    )


def roll_effect_amount(
    amount: FixedAmount | DiceAmount | CalculatedAmount | CombinedAmount,
    scaling: list[AmountScaling],
    sheet: CharacterSheet,
    spell: SpellEntry,
    spell_slot_level: int | None,
) -> tuple[list[int], character_sheet.DiceType, list[RollModifierBreakdown], int]:
    amounts = amount.amounts if isinstance(amount, CombinedAmount) else [amount]
    dice: list[int] = []
    dice_type = character_sheet.DiceType.D4
    modifier_breakdown: list[RollModifierBreakdown] = []
    scaling_increments = [
        (scale, effect_scaling_increments(scale, sheet, spell.level, spell_slot_level))
        for scale in scaling
    ]
    for part in amounts:
        if isinstance(part, DiceAmount):
            dice_type = part.diceType
            dice_count = part.diceCount
            static_bonus = part.staticBonus
            dice.extend(character_sheet.random.randint(1, dice_type.value) for _ in range(dice_count))
            if static_bonus:
                modifier_breakdown.append(RollModifierBreakdown(source="Spell", value=static_bonus))
        elif isinstance(part, FixedAmount):
            modifier_breakdown.append(RollModifierBreakdown(source="Spell", value=part.value))
        elif isinstance(part, CalculatedAmount):
            if part.calculation == AmountCalculation.SOURCE_SPELLCASTING_MODIFIER:
                ability = spell_casting_ability(sheet, spell)
                value = ability_modifier(getattr(sheet.abilityScores, enum_key(ability)))
                source = enum_label(ability)
            elif part.calculation == AmountCalculation.SOURCE_ABILITY_MODIFIER and part.ability is not None:
                value = ability_modifier(getattr(sheet.abilityScores, enum_key(part.ability)))
                source = enum_label(part.ability)
            elif part.calculation == AmountCalculation.SOURCE_CLASS_LEVEL and part.characterClass is not None:
                value = sum(level.level for level in sheet.classes if level.name == part.characterClass)
                source = enum_label(part.characterClass)
            elif part.calculation == AmountCalculation.SOURCE_CHARACTER_LEVEL:
                value = sum(level.level for level in sheet.classes)
                source = "Character Level"
            elif part.calculation == AmountCalculation.SOURCE_PROFICIENCY_BONUS:
                value = sheet.proficiencyBonus
                source = "Proficiency"
            else:
                raise ValueError(f"Incomplete calculated amount: {part.calculation.name}")
            value *= part.multiplier
            if part.minimum is not None:
                value = max(part.minimum, value)
            modifier_breakdown.append(RollModifierBreakdown(source=source, value=value))
        else:
            raise TypeError(f"Unsupported rolled effect amount: {part.__class__.__name__}")
    for scale, increments in scaling_increments:
        if scale.additionalDice is not None:
            dice_type = scale.additionalDice.diceType
            dice.extend(
                character_sheet.random.randint(1, dice_type.value)
                for _ in range(increments * scale.additionalDice.diceCount)
            )
            scaled_static_bonus = increments * scale.additionalDice.staticBonus
            if scaled_static_bonus:
                modifier_breakdown.append(RollModifierBreakdown(source="Effect", value=scaled_static_bonus))
        scaled_fixed_amount = increments * scale.additionalFixedAmount
        if scaled_fixed_amount:
            modifier_breakdown.append(RollModifierBreakdown(source="Effect", value=scaled_fixed_amount))
    modifier = sum(part.value for part in modifier_breakdown)
    return dice, dice_type, modifier_breakdown, sum(dice) + modifier


def scaled_dice_amount(
    damage: DamageEffect,
    sheet: CharacterSheet,
    spell_level: int,
    spell_slot_level: int | None,
) -> tuple[int, int]:
    if not isinstance(damage.amount, DiceAmount):
        raise TypeError("Damage amount is not dice")
    dice_count = damage.amount.diceCount
    static_bonus = damage.amount.staticBonus
    for scaling in damage.scaling:
        increments = effect_scaling_increments(scaling, sheet, spell_level, spell_slot_level)
        if scaling.additionalDice is not None:
            dice_count += increments * scaling.additionalDice.diceCount
            static_bonus += increments * scaling.additionalDice.staticBonus
        static_bonus += increments * scaling.additionalFixedAmount
    return dice_count, static_bonus


def effect_scaling_increments(
    scaling: AmountScaling,
    sheet: CharacterSheet,
    spell_level: int,
    spell_slot_level: int | None,
) -> int:
    if scaling.basis == ScalingBasis.SPELL_SLOT_LEVEL:
        return 0 if spell_slot_level is None else max(0, spell_slot_level - spell_level) // scaling.interval
    level = sum(character_class.level for character_class in sheet.classes) or 1
    if scaling.thresholds:
        return sum(level >= threshold for threshold in scaling.thresholds)
    return max(0, level - 1) // scaling.interval


def scaled_instance_count(
    scaling: InstanceScaling,
    sheet: CharacterSheet,
    spell_level: int,
    spell_slot_level: int | None,
) -> int:
    if scaling.basis is None:
        return scaling.baseInstances
    if scaling.basis == ScalingBasis.SPELL_SLOT_LEVEL:
        increments = 0 if spell_slot_level is None else max(0, spell_slot_level - spell_level) // scaling.interval
    else:
        level = sum(character_class.level for character_class in sheet.classes) or 1
        increments = sum(level >= threshold for threshold in scaling.thresholds) if scaling.thresholds else max(0, level - 1) // scaling.interval
    return scaling.baseInstances + increments * scaling.additionalInstances


def direct_save_outcome(effect: EffectNode) -> SpellSaveOutcome | None:
    if isinstance(effect, ActivatedEffect):
        return direct_save_outcome(effect.effect)
    if not isinstance(effect, SavingThrowEffect):
        return None
    success_damage = first_damage_effect(effect.onSuccess)
    if success_damage is None:
        return SpellSaveOutcome.NEGATES
    if success_damage.multiplierNumerator == 1 and success_damage.multiplierDenominator == 2:
        return SpellSaveOutcome.HALF_DAMAGE
    return SpellSaveOutcome.PARTIAL


def direct_damage_save_outcome(root: EffectNode, saving_throw: SavingThrowEffect) -> SpellSaveOutcome:
    node = activated_effect_node(root)
    while isinstance(node, (RepeatedEffect, ConditionalEffect, AttackRollEffect)):
        if isinstance(node, RepeatedEffect):
            node = node.effect
        elif isinstance(node, ConditionalEffect):
            node = node.whenTrue
        else:
            node = node.onHit
    if node is saving_throw:
        return direct_save_outcome(saving_throw) or SpellSaveOutcome.PARTIAL
    return SpellSaveOutcome.PARTIAL
