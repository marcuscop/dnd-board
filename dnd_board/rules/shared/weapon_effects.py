from __future__ import annotations

from dataclasses import replace

from dnd_board.character_sheet import (
    AttackAction,
    CharacterSheet,
    DiceType,
    EquipmentItem,
    RollDamageComponent,
    RollPayload,
    RollResolutionMode,
    RollSource,
    SheetSectionType,
    SpellEntry,
    attack_action_with_default_mechanics,
    attack_equipment_item,
    build_attack_roll_payload,
    build_damage_roll_payload,
    dice_formula,
    enum_key,
    enum_label,
    enum_value,
    spell_casting_ability,
)
from dnd_board.rules.equipment import EquipmentId
from dnd_board.rules.shared.effects import (
    ActiveOngoingEffect,
    ActivatedEffect,
    ApplyEffect,
    AttackRollEffect,
    ChoiceEffect,
    DamageEffect,
    DiceAmount,
    EffectAmountInput,
    EffectNode,
    EffectNodeId,
    EffectResolutionInputs,
    EffectSelectionInput,
    EquipmentInstanceId,
    SelectionId,
    SelectWeaponEffect,
    SequenceEffect,
    ThresholdDiceExpression,
    WeaponAbilityReference,
    WeaponAttackModification,
    WeaponAttackOption,
    WeaponAttackOptionId,
    WeaponDamageTypeReference,
    WeaponEligibility,
)


def eligible_weapon_attacks(
    sheet: CharacterSheet,
    eligibility: WeaponEligibility,
) -> tuple[AttackAction, ...]:
    return tuple(
        attack
        for attack in sheet.attacks
        if weapon_is_eligible(sheet, attack, eligibility)
    )


def weapon_is_eligible(
    sheet: CharacterSheet,
    attack: AttackAction,
    eligibility: WeaponEligibility,
) -> bool:
    item = attack_equipment_item(sheet, attack)
    if eligibility.wielded and item is None:
        return False
    if eligibility.proficient and not attack.proficient:
        return False
    if eligibility.attackKinds and attack.attackKind not in eligibility.attackKinds:
        return False
    if eligibility.properties and not set(eligibility.properties).issubset(attack.properties or []):
        return False
    if eligibility.equipmentIds:
        if item is None or equipment_definition_id(item) not in eligibility.equipmentIds:
            return False
    return attack.damageDiceCount > 0


def equipment_definition_id(item: EquipmentItem) -> EquipmentId | None:
    if item.definitionId is not None:
        return item.definitionId
    return enum_value(EquipmentId, item.id) or enum_value(EquipmentId, item.name)


def selected_weapon_attack(
    sheet: CharacterSheet,
    equipment_instance_id: str,
    eligibility: WeaponEligibility,
) -> AttackAction | None:
    return next(
        (
            attack
            for attack in eligible_weapon_attacks(sheet, eligibility)
            if attack.id == equipment_instance_id
        ),
        None,
    )


def selection_binding(
    active: ActiveOngoingEffect,
    selection: SelectionId,
) -> str | None:
    return next(
        (
            binding.equipmentInstanceId.value
            for binding in active.bindings
            if binding.selection == selection
        ),
        None,
    )


def apply_weapon_attack_modification(
    sheet: CharacterSheet,
    attack: AttackAction,
    modification: WeaponAttackModification,
    source_spell: SpellEntry | None = None,
) -> AttackAction:
    ability = attack.ability
    if modification.ability == WeaponAbilityReference.SOURCE_SPELLCASTING:
        if source_spell is None:
            raise ValueError("Spellcasting weapon modification requires its source spell")
        ability = spell_casting_ability(sheet, source_spell)

    damage_count = attack.damageDiceCount
    damage_type = attack.damageDiceType
    if modification.damageDice is not None:
        replacement = threshold_dice(sheet, modification.damageDice)
        damage_count = replacement.diceCount
        damage_type = replacement.diceType

    attack_damage_type = attack.damageType
    if modification.damageType == WeaponDamageTypeReference.FIXED:
        assert modification.fixedDamageType is not None
        attack_damage_type = modification.fixedDamageType

    return attack_action_with_default_mechanics(replace(
        attack,
        ability=ability,
        damageDiceCount=damage_count,
        damageDiceType=damage_type,
        damageType=attack_damage_type,
        mechanics=None,
    ))


def ongoing_weapon_attack(
    sheet: CharacterSheet,
    attack: AttackAction,
    weapon_option: str | None = None,
) -> AttackAction:
    effective = attack
    for active in sheet.ongoingEffects:
        bound_weapon = selection_binding(active, SelectionId.WEAPON)
        if bound_weapon != attack.id:
            continue
        source_spell = next(
            (
                spell
                for spell in [*sheet.spells, *sheet.spellbook]
                if active.sourceSpellId is not None and spell.id == active.sourceSpellId
            ),
            None,
        )
        for modification in active.effect.weaponAttackModifications:
            effective = apply_weapon_attack_modification(sheet, effective, modification, source_spell)
        if active.effect.weaponAttackOptions:
            option_id = enum_value(WeaponAttackOptionId, weapon_option)
            option = next(
                (
                    option
                    for option in active.effect.weaponAttackOptions
                    if option.id == option_id
                ),
                active.effect.weaponAttackOptions[0],
            )
            effective = apply_weapon_attack_modification(
                sheet,
                effective,
                option.modification,
                source_spell,
            )
    return effective


def projected_weapon_attack(sheet: CharacterSheet, attack: AttackAction) -> AttackAction:
    options: list[WeaponAttackOption] = []
    active_spells = list(attack.activeSpellConditions or [])
    for active in sheet.ongoingEffects:
        if selection_binding(active, SelectionId.WEAPON) != attack.id:
            continue
        options.extend(active.effect.weaponAttackOptions)
        if active.sourceSpellId is not None and active.sourceSpellId not in active_spells:
            active_spells.append(active.sourceSpellId)
    return replace(
        attack,
        weaponAttackOptions=options or None,
        activeSpellConditions=active_spells or None,
    )


def threshold_dice(
    sheet: CharacterSheet,
    expression: ThresholdDiceExpression,
) -> DiceAmount:
    level = sum(character_class.level for character_class in sheet.classes) or 1
    eligible = [
        threshold.dice
        for threshold in expression.thresholds
        if level >= threshold.minimumLevel
    ]
    if not eligible:
        raise ValueError("No weapon damage dice threshold applies")
    return eligible[-1]


def weapon_selection_effect(
    effect: EffectNode | None,
    node_id: EffectNodeId = EffectNodeId(()),
) -> tuple[EffectNodeId, SelectWeaponEffect] | None:
    if isinstance(effect, ActivatedEffect):
        return weapon_selection_effect(effect.effect, node_id.child(0))
    if isinstance(effect, SelectWeaponEffect):
        return node_id, effect
    return None


def selected_weapon_effect(
    root: EffectNode,
    choice_index: int | None,
) -> tuple[EffectNode, EffectNodeId, SelectWeaponEffect, EffectNode]:
    found = weapon_selection_effect(root)
    if found is None:
        raise ValueError("Spell has no weapon selection")
    node_id, selection = found
    selected: EffectNode = selection.effect
    if isinstance(selected, ChoiceEffect):
        index = choice_index if choice_index is not None else 0
        if index < 0 or index >= len(selected.choices):
            raise ValueError("Spell effect choice not found")
        selected = selected.choices[index].effect
    replacement = replace(selection, effect=selected)
    selected_root = replace(root, effect=replacement) if isinstance(root, ActivatedEffect) else replacement
    return selected_root, node_id, selection, selected


def build_bound_weapon_spell_attack_payload(
    sheet: CharacterSheet,
    roller: str,
    spell: SpellEntry,
    effect_index: int,
    equipment_instance_id: str,
    choice_index: int | None,
) -> RollPayload:
    if spell.mechanics is None or effect_index < 0 or effect_index >= len(spell.mechanics.activatedEffects):
        raise ValueError("Spell weapon effect not found")
    authored_root = spell.mechanics.activatedEffects[effect_index]
    _selected_root, selection_node_id, selection, selected = selected_weapon_effect(authored_root, choice_index)
    if not isinstance(selected, AttackRollEffect) or selected.weaponSelection != selection.selection:
        raise ValueError("Selected spell effect is not a bound weapon attack")
    selected_attack = selected_weapon_attack(sheet, equipment_instance_id, selection.eligibility)
    if selected_attack is None:
        raise ValueError("Selected weapon is not eligible for this spell")
    attack = ongoing_weapon_attack(sheet, selected_attack)
    modified_attack = apply_weapon_attack_modification(
        sheet,
        attack,
        selected.weaponModification or WeaponAttackModification(),
        spell,
    )
    base_damage = ApplyEffect(DamageEffect(
        DiceAmount(modified_attack.damageDiceCount, modified_attack.damageDiceType),
        modified_attack.damageType,
    ))
    resolved_attack = replace(
        selected,
        onHit=base_damage if selected.onHit is None else SequenceEffect([base_damage, selected.onHit]),
    )
    resolved_selection = replace(selection, effect=resolved_attack)
    pending_effect = (
        replace(authored_root, effect=resolved_selection)
        if isinstance(authored_root, ActivatedEffect)
        else resolved_selection
    )

    attack_roll = build_attack_roll_payload(sheet, roller, modified_attack)
    base_roll = build_damage_roll_payload(sheet, roller, modified_attack)
    from dnd_board.rules.shared.character_effects import damage_effect_nodes, roll_effect_amount

    damage_nodes = damage_effect_nodes(pending_effect)
    if not damage_nodes:
        raise ValueError("Bound weapon attack has no damage effect")
    components = [RollDamageComponent(
        damageType=base_roll.damageType or modified_attack.damageType,
        dice=base_roll.dice,
        diceType=base_roll.diceType,
        die=base_roll.die,
        modifier=base_roll.modifier,
        modifierBreakdown=base_roll.modifierBreakdown,
        total=base_roll.total,
        effectNodeIds=[damage_nodes[0][0]],
    )]
    amount_inputs = [EffectAmountInput(damage_nodes[0][0], base_roll.total)]
    for node_id, damage in damage_nodes[1:]:
        dice, dice_type, breakdown, total = roll_effect_amount(
            damage.amount,
            damage.scaling,
            sheet,
            spell,
            None,
        )
        amount_inputs.append(EffectAmountInput(node_id, total))
        if dice or total:
            components.append(RollDamageComponent(
                damageType=damage.damageType,
                dice=dice,
                diceType=dice_type,
                die=dice_formula(len(dice), dice_type),
                modifier=sum(part.value for part in breakdown),
                modifierBreakdown=breakdown,
                total=total,
                effectNodeIds=[node_id],
            ))
    return replace(
        attack_roll,
        source=RollSource(SheetSectionType.SPELLS, enum_key(spell.id), f"weapon-attack-{effect_index}"),
        sourceLabel=f"{enum_label(spell.name)}: {attack.name}",
        label=enum_label(spell.name),
        damageType=components[0].damageType,
        damageComponents=components,
        boundAttackId=attack.id,
        pendingEffect=pending_effect,
        effectInputs=EffectResolutionInputs(
            amounts=amount_inputs,
            selections=[EffectSelectionInput(
                selection_node_id,
                selection.selection,
                EquipmentInstanceId(equipment_instance_id),
            )],
        ),
    )


def build_bound_weapon_spell_effect_payload(
    sheet: CharacterSheet,
    roller: str,
    spell: SpellEntry,
    effect_index: int,
    equipment_instance_id: str,
) -> RollPayload:
    if spell.mechanics is None or effect_index < 0 or effect_index >= len(spell.mechanics.activatedEffects):
        raise ValueError("Spell weapon effect not found")
    root = spell.mechanics.activatedEffects[effect_index]
    found = weapon_selection_effect(root)
    if found is None:
        raise ValueError("Spell has no weapon selection")
    node_id, selection = found
    if selected_weapon_attack(sheet, equipment_instance_id, selection.eligibility) is None:
        raise ValueError("Selected weapon is not eligible for this spell")
    from time import time_ns

    created_at = time_ns()
    return RollPayload(
        id=f"roll-{created_at}",
        sheetId=sheet.id,
        tokenId=sheet.tokenId,
        roller=roller,
        source=RollSource(SheetSectionType.SPELLS, enum_key(spell.id), f"weapon-effect-{effect_index}"),
        sourceLabel=enum_label(spell.name),
        resolution=RollResolutionMode.NONE,
        label=enum_label(spell.name),
        iconUrl=None,
        dice=[],
        diceType=DiceType.D20,
        die="",
        modifier=0,
        modifierBreakdown=[],
        total=0,
        createdAt=created_at,
        boundAttackId=equipment_instance_id,
        pendingEffect=root,
        effectInputs=EffectResolutionInputs(selections=[EffectSelectionInput(
            node_id,
            selection.selection,
            EquipmentInstanceId(equipment_instance_id),
        )]),
    )
