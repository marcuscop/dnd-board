from dnd_board.character_sheet import (
    AbilityType,
    ClassType,
    ConditionType,
    ConditionRemovalTrigger,
    DamageType,
    DiceType,
    SpellAttackType,
    SpellAreaShape,
    SpellComponent,
    SpellDurationUnit,
    SpellEffectKind,
    SpellEffectTarget,
    SpellEffectTrigger,
    SpellId,
    SpellRangeType,
    SpellSaveOutcome,
    SpellScalingType,
    SpellSchool,
    SpellSource,
    TimeEconomy,
    typed_json_from_value,
    typed_json_to_value,
)
from dnd_board.rules.spells import (
    SpellListType,
    artificer_spell_entry,
    artificer_spell_entries,
    bard_spell_entry,
    bard_spell_entries,
    class_spell_list,
    cleric_spell_entry,
    cleric_spell_entries,
    druid_spell_entry,
    druid_spell_entries,
    normalized_spell_entry,
    paladin_spell_entry,
    paladin_spell_entries,
    ranger_spell_entry,
    ranger_spell_entries,
    selected_spell_entries,
    sorcerer_spell_entry,
    sorcerer_spell_entries,
    spell_condition_effect,
    spell_damage_effect,
    spell_catalog,
    spell_entry,
    spell_healing_effect,
    spell_metadata,
    spell_metadata_for_list,
    spell_save,
    spell_scaling,
    spell_temporary_hit_points_effect,
    warlock_spell_entries,
    warlock_spell_entry,
    wizard_spell_entry,
    wizard_spell_entries,
)


def test_spell_catalog_loads_full_2024_markdown_table() -> None:
    catalog = spell_catalog()
    fire_bolt_metadata = spell_metadata(SpellId.FIRE_BOLT)

    assert len(catalog) == 419
    assert catalog[SpellId.FIRE_BOLT].level == 0
    assert catalog[SpellId.FIRE_BOLT].school == SpellSchool.EVOCATION
    assert catalog[SpellId.FIRE_BOLT].id == SpellId.FIRE_BOLT
    assert fire_bolt_metadata is not None
    assert fire_bolt_metadata.spellLists == (SpellListType.ARTIFICER, SpellListType.SORCERER, SpellListType.WIZARD)
    assert fire_bolt_metadata.url == "http://dnd2024.wikidot.com/spell:fire-bolt"


def test_spell_catalog_parses_common_mechanical_fields() -> None:
    shield = spell_entry("shield")
    detect_magic = spell_entry("detectMagic")
    find_familiar = spell_metadata(SpellId.FIND_FAMILIAR)
    dream = spell_entry("dream")

    assert shield is not None
    assert shield.castingTime == TimeEconomy.REACTION
    assert shield.targeting.rangeType == SpellRangeType.SELF
    assert shield.duration.unit == SpellDurationUnit.ROUND
    assert shield.components == [SpellComponent.VERBAL, SpellComponent.SOMATIC]

    assert detect_magic is not None
    assert detect_magic.concentration is True
    assert detect_magic.ritual is True
    assert detect_magic.duration.maximum is True

    assert find_familiar is not None
    assert find_familiar.materialCost is True
    assert find_familiar.materialConsumed is True

    assert dream is not None
    assert dream.targeting.rangeType == SpellRangeType.SPECIAL


def test_spell_catalog_filters_by_spell_list_level_and_school() -> None:
    wizard_cantrips = spell_metadata_for_list(SpellListType.WIZARD, maximum_level=0)
    wizard_abjurations = spell_metadata_for_list(SpellListType.WIZARD, maximum_level=1, schools={SpellSchool.ABJURATION})

    assert SpellId.MAGE_HAND in {spell.spellId for spell in wizard_cantrips}
    assert SpellId.CURE_WOUNDS not in {spell.spellId for spell in wizard_cantrips}
    assert {SpellId.ALARM, SpellId.SHIELD}.issubset({spell.spellId for spell in wizard_abjurations})
    assert SpellId.MAGIC_MISSILE not in {spell.spellId for spell in wizard_abjurations}


def test_class_spell_list_bridge_keeps_class_identity_separate_from_spell_lists() -> None:
    assert class_spell_list(ClassType.WIZARD) == SpellListType.WIZARD
    assert class_spell_list(ClassType.CLERIC) == SpellListType.CLERIC
    assert class_spell_list(ClassType.SORCERER) == SpellListType.SORCERER
    assert class_spell_list(ClassType.FIGHTER) is None
    assert class_spell_list(ClassType.ROGUE) is None


def test_spell_catalog_uses_existing_sheet_spell_entry() -> None:
    entry = wizard_spell_entry("magicMissile", casting_ability=AbilityType.CHARISMA)

    assert entry is not None
    assert entry.id == SpellId.MAGIC_MISSILE
    assert entry.name == SpellId.MAGIC_MISSILE
    assert entry.source == SpellSource.WIZARD
    assert entry.castingAbility == AbilityType.CHARISMA
    assert entry.castingTime == TimeEconomy.ACTION
    assert entry.targeting.distanceFeet == 120
    assert "Spell lists: Sorcerer, Wizard." in entry.description
    assert wizard_spell_entry("cureWounds") is None
    assert SpellId.FIREBALL in {spell.id for spell in wizard_spell_entries(maximum_level=3)}


def test_named_spell_list_helpers_use_the_shared_catalog() -> None:
    cleric_cantrips = {spell.id for spell in cleric_spell_entries(exact_level=0)}
    druid_first_level = {spell.id for spell in druid_spell_entries(exact_level=1)}
    sorcerer_cantrips = {spell.id for spell in sorcerer_spell_entries(exact_level=0)}
    warlock_first_level = {spell.id for spell in warlock_spell_entries(exact_level=1)}

    assert SpellId.GUIDANCE in cleric_cantrips
    assert SpellId.FIRE_BOLT not in cleric_cantrips
    assert SpellId.GOODBERRY in druid_first_level
    assert SpellId.FIRE_BOLT in sorcerer_cantrips
    assert SpellId.ARMOR_OF_AGATHYS in warlock_first_level
    assert cleric_spell_entry("cureWounds") is not None
    assert druid_spell_entry("magicMissile") is None


def test_all_named_spell_list_entry_helpers_and_selected_filter() -> None:
    assert artificer_spell_entry("fireBolt").source == SpellSource.ARTIFICER
    assert bard_spell_entry("viciousMockery").source == SpellSource.BARD
    assert paladin_spell_entry("divineFavor").source == SpellSource.PALADIN
    assert ranger_spell_entry("huntersMark").source == SpellSource.RANGER
    assert sorcerer_spell_entry("fireBolt").source == SpellSource.SORCERER
    assert warlock_spell_entry("hex").source == SpellSource.WARLOCK
    assert artificer_spell_entries(exact_level=0)
    assert bard_spell_entries(exact_level=0)
    assert paladin_spell_entries(exact_level=1)
    assert ranger_spell_entries(exact_level=1)
    selected = selected_spell_entries(wizard_spell_entries(exact_level=0), ["mageHand", "fireBolt"])
    normalized = normalized_spell_entry(selected[0], source=SpellSource.MAGIC_INITIATE, casting_ability=AbilityType.WISDOM)

    assert {spell.id for spell in selected} == {SpellId.MAGE_HAND, SpellId.FIRE_BOLT}
    assert normalized.source == SpellSource.MAGIC_INITIATE
    assert normalized.castingAbility == AbilityType.WISDOM


def test_spell_effect_helpers_create_typed_damage_healing_and_conditions() -> None:
    fire = spell_damage_effect(
        1,
        DiceType.D10,
        DamageType.FIRE,
        trigger=SpellEffectTrigger.ON_HIT,
        attack=SpellAttackType.RANGED_SPELL_ATTACK,
        scaling=[spell_scaling(SpellScalingType.CANTRIP_LEVEL, dice_count=1, dice_type=DiceType.D10)],
    )
    cure = spell_healing_effect(
        2,
        DiceType.D8,
        bonus_ability=AbilityType.WISDOM,
        scaling=[spell_scaling(SpellScalingType.SPELL_SLOT_LEVEL, dice_count=2, dice_type=DiceType.D8)],
    )
    held = spell_condition_effect(
        ConditionType.PARALYZED,
        saving_throw=spell_save(AbilityType.WISDOM, repeat=SpellEffectTrigger.END_OF_TURN),
        save_ends=True,
    )
    armor = spell_temporary_hit_points_effect(5, DiceType.D4, static_bonus=5, target=SpellEffectTarget.SELF)

    assert fire.kind == SpellEffectKind.DAMAGE
    assert fire.damage is not None
    assert fire.damage.damageType == DamageType.FIRE
    assert fire.damage.dice.dice == "1d10"
    assert fire.attack == SpellAttackType.RANGED_SPELL_ATTACK
    assert fire.scaling is not None
    assert fire.scaling[0].scalingType == SpellScalingType.CANTRIP_LEVEL
    assert fire.scaling[0].additionalDice is not None
    assert fire.scaling[0].additionalDice.dice == "1d10"

    assert cure.healing is not None
    assert cure.healing.dice.bonusAbility == AbilityType.WISDOM
    assert cure.healing.dice.dice == "2d8"

    assert held.savingThrow is not None
    assert held.savingThrow.ability == AbilityType.WISDOM
    assert held.savingThrow.outcome == SpellSaveOutcome.NEGATES
    assert held.savingThrow.repeat == SpellEffectTrigger.END_OF_TURN
    assert held.conditions is not None
    assert held.conditions[0].condition == ConditionType.PARALYZED
    assert held.conditions[0].saveEnds is True

    assert armor.kind == SpellEffectKind.TEMPORARY_HIT_POINTS
    assert armor.temporaryHitPoints is not None
    assert armor.temporaryHitPoints.dice == "5d4"
    assert armor.temporaryHitPoints.staticBonus == 5


def test_catalog_spell_effects_round_trip_through_typed_json() -> None:
    fireball = spell_entry(SpellId.FIREBALL)

    assert fireball is not None
    restored = typed_json_to_value(typed_json_from_value(fireball))
    assert restored == fireball
    assert restored.effects is not None
    assert restored.effects[0].savingThrow is not None
    assert restored.effects[0].savingThrow.outcome == SpellSaveOutcome.HALF_DAMAGE


def test_catalog_spell_effects_capture_representative_2024_mechanics() -> None:
    fire_bolt = spell_entry(SpellId.FIRE_BOLT)
    burning_hands = spell_entry(SpellId.BURNING_HANDS)
    cure_wounds = spell_entry(SpellId.CURE_WOUNDS)
    hold_person = spell_entry(SpellId.HOLD_PERSON)
    tasha = spell_entry(SpellId.TASHA_S_HIDEOUS_LAUGHTER)
    web = spell_entry(SpellId.WEB)

    assert fire_bolt is not None and fire_bolt.effects is not None
    assert fire_bolt.effects[0].damage is not None
    assert fire_bolt.effects[0].damage.damageType == DamageType.FIRE
    assert fire_bolt.effects[0].attack == SpellAttackType.RANGED_SPELL_ATTACK
    assert fire_bolt.effects[0].scaling is not None
    assert fire_bolt.effects[0].scaling[0].scalingType == SpellScalingType.CANTRIP_LEVEL

    assert burning_hands is not None and burning_hands.effects is not None
    assert burning_hands.targeting.area.shape == SpellAreaShape.CONE
    assert burning_hands.effects[0].damage is not None
    assert burning_hands.effects[0].damage.dice.dice == "3d6"
    assert burning_hands.effects[0].damage.damageType == DamageType.FIRE
    assert burning_hands.effects[0].savingThrow is not None
    assert burning_hands.effects[0].savingThrow.ability == AbilityType.DEXTERITY
    assert burning_hands.effects[0].savingThrow.outcome == SpellSaveOutcome.HALF_DAMAGE
    assert burning_hands.effects[0].scaling is not None
    assert burning_hands.effects[0].scaling[0].scalingType == SpellScalingType.SPELL_SLOT_LEVEL

    assert cure_wounds is not None and cure_wounds.effects is not None
    assert cure_wounds.effects[0].healing is not None
    assert cure_wounds.effects[0].healing.dice.dice == "2d8"
    assert cure_wounds.effects[0].healing.dice.bonusAbility == AbilityType.INTELLIGENCE
    assert cure_wounds.effects[0].scaling is not None
    assert cure_wounds.effects[0].scaling[0].additionalDice is not None
    assert cure_wounds.effects[0].scaling[0].additionalDice.dice == "2d8"

    assert hold_person is not None and hold_person.effects is not None
    assert hold_person.effects[0].conditions is not None
    assert hold_person.effects[0].conditions[0].condition == ConditionType.PARALYZED
    assert hold_person.effects[0].savingThrow is not None
    assert hold_person.effects[0].savingThrow.ability == AbilityType.WISDOM
    assert hold_person.effects[0].savingThrow.repeat == SpellEffectTrigger.END_OF_TURN

    assert tasha is not None and tasha.effects is not None
    assert tasha.effects[0].kind == SpellEffectKind.CONDITION
    assert tasha.effects[0].savingThrow is not None
    assert tasha.effects[0].savingThrow.ability == AbilityType.WISDOM
    assert tasha.effects[0].savingThrow.repeat == SpellEffectTrigger.END_OF_TURN
    assert tasha.effects[0].conditions is not None
    assert [condition.condition for condition in tasha.effects[0].conditions] == [ConditionType.PRONE, ConditionType.INCAPACITATED]
    assert {condition.removalTrigger for condition in tasha.effects[0].conditions} == {ConditionRemovalTrigger.AFTER_TAKING_DAMAGE}
    assert {condition.removalAdvantage for condition in tasha.effects[0].conditions} == {True}
    assert tasha.effects[0].scaling is not None
    assert tasha.effects[0].scaling[0].scalingType == SpellScalingType.SPELL_SLOT_LEVEL

    assert web is not None and web.effects is not None
    assert web.targeting.area.shape == SpellAreaShape.CUBE
    assert web.effects[0].target == SpellEffectTarget.AREA
    assert web.effects[0].conditions is not None
    assert web.effects[0].conditions[0].condition == ConditionType.RESTRAINED
    assert web.effects[1].damage is not None
    assert web.effects[1].damage.dice.dice == "2d4"


def test_catalog_spell_effect_lists_are_cloned() -> None:
    first = spell_entry(SpellId.FIRE_BOLT)
    second = spell_entry(SpellId.FIRE_BOLT)
    wizard = wizard_spell_entry(SpellId.FIRE_BOLT)

    assert first is not None and second is not None and wizard is not None
    assert first.effects is not None and second.effects is not None and wizard.effects is not None
    assert first.effects is not second.effects
    assert first.effects[0].scaling is not None and second.effects[0].scaling is not None
    assert first.effects[0].scaling is not second.effects[0].scaling
    assert wizard.effects is not first.effects
