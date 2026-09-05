from dnd_board.character_sheet import (
    AbilityType,
    ClassType,
    ConditionType,
    ConditionRemovalTrigger,
    DamageType,
    CreatureType,
    DiceType,
    RollModifierEffectOperation,
    RollModifierEffectTarget,
    SpellAttackType,
    SpellAreaShape,
    SpellComponent,
    SpellDurationUnit,
    SpellEffectKind,
    SpellEffectTarget,
    SpellEffectTrigger,
    SpellId,
    SpellLinkedHealingAmount,
    SpellRangeType,
    SpellSaveOutcome,
    SpellScalingType,
    SpellSchool,
    SpellSource,
    RestType,
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
    acid_splash = spell_entry(SpellId.ACID_SPLASH)
    fire_bolt = spell_entry(SpellId.FIRE_BOLT)
    armor_of_agathys = spell_entry(SpellId.ARMOR_OF_AGATHYS)
    arms_of_hadar = spell_entry(SpellId.ARMS_OF_HADAR)
    burning_hands = spell_entry(SpellId.BURNING_HANDS)
    charm_person = spell_entry(SpellId.CHARM_PERSON)
    chill_touch = spell_entry(SpellId.CHILL_TOUCH)
    color_spray = spell_entry(SpellId.COLOR_SPRAY)
    cure_wounds = spell_entry(SpellId.CURE_WOUNDS)
    dissonant_whispers = spell_entry(SpellId.DISSONANT_WHISPERS)
    divine_smite = spell_entry(SpellId.DIVINE_SMITE)
    eldritch_blast = spell_entry(SpellId.ELDRITCH_BLAST)
    entangle = spell_entry(SpellId.ENTANGLE)
    false_life = spell_entry(SpellId.FALSE_LIFE)
    grease = spell_entry(SpellId.GREASE)
    guiding_bolt = spell_entry(SpellId.GUIDING_BOLT)
    healing_word = spell_entry(SpellId.HEALING_WORD)
    hellish_rebuke = spell_entry(SpellId.HELLISH_REBUKE)
    hold_person = spell_entry(SpellId.HOLD_PERSON)
    ice_knife = spell_entry(SpellId.ICE_KNIFE)
    inflict_wounds = spell_entry(SpellId.INFLICT_WOUNDS)
    magic_missile = spell_entry(SpellId.MAGIC_MISSILE)
    mind_sliver = spell_entry(SpellId.MIND_SLIVER)
    poison_spray = spell_entry(SpellId.POISON_SPRAY)
    ray_of_frost = spell_entry(SpellId.RAY_OF_FROST)
    ray_of_sickness = spell_entry(SpellId.RAY_OF_SICKNESS)
    sacred_flame = spell_entry(SpellId.SACRED_FLAME)
    shocking_grasp = spell_entry(SpellId.SHOCKING_GRASP)
    starry_wisp = spell_entry(SpellId.STARRY_WISP)
    tasha = spell_entry(SpellId.TASHA_S_HIDEOUS_LAUGHTER)
    thunderclap = spell_entry(SpellId.THUNDERCLAP)
    thunderwave = spell_entry(SpellId.THUNDERWAVE)
    vicious_mockery = spell_entry(SpellId.VICIOUS_MOCKERY)
    web = spell_entry(SpellId.WEB)
    witch_bolt = spell_entry(SpellId.WITCH_BOLT)
    word_of_radiance = spell_entry(SpellId.WORD_OF_RADIANCE)

    assert acid_splash is not None and acid_splash.effects is not None
    assert acid_splash.targeting.area.shape == SpellAreaShape.RADIUS
    assert acid_splash.effects[0].damage is not None
    assert acid_splash.effects[0].damage.damageType == DamageType.ACID
    assert acid_splash.effects[0].savingThrow is not None
    assert acid_splash.effects[0].savingThrow.ability == AbilityType.DEXTERITY
    assert acid_splash.effects[0].savingThrow.outcome == SpellSaveOutcome.NEGATES
    assert acid_splash.effects[0].scaling is not None
    assert acid_splash.effects[0].scaling[0].scalingType == SpellScalingType.CANTRIP_LEVEL

    assert fire_bolt is not None and fire_bolt.effects is not None
    assert fire_bolt.effects[0].damage is not None
    assert fire_bolt.effects[0].damage.damageType == DamageType.FIRE
    assert fire_bolt.effects[0].attack == SpellAttackType.RANGED_SPELL_ATTACK
    assert fire_bolt.effects[0].scaling is not None
    assert fire_bolt.effects[0].scaling[0].scalingType == SpellScalingType.CANTRIP_LEVEL

    assert armor_of_agathys is not None and armor_of_agathys.effects is not None
    assert armor_of_agathys.effects[0].temporaryHitPoints is not None
    assert armor_of_agathys.effects[0].temporaryHitPoints.staticBonus == 5
    assert armor_of_agathys.effects[0].scaling is not None
    assert armor_of_agathys.effects[0].scaling[0].additionalStaticBonus == 5
    assert armor_of_agathys.effects[1].damage is not None
    assert armor_of_agathys.effects[1].damage.damageType == DamageType.COLD
    assert armor_of_agathys.effects[1].trigger == SpellEffectTrigger.SPECIAL

    assert arms_of_hadar is not None and arms_of_hadar.effects is not None
    assert arms_of_hadar.targeting.area.shape == SpellAreaShape.RADIUS
    assert arms_of_hadar.effects[0].damage is not None
    assert arms_of_hadar.effects[0].damage.dice.dice == "2d6"
    assert arms_of_hadar.effects[0].damage.damageType == DamageType.NECROTIC
    assert arms_of_hadar.effects[0].savingThrow is not None
    assert arms_of_hadar.effects[0].savingThrow.ability == AbilityType.STRENGTH
    assert arms_of_hadar.effects[0].savingThrow.outcome == SpellSaveOutcome.HALF_DAMAGE

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

    assert charm_person is not None and charm_person.effects is not None
    assert charm_person.effects[0].conditions is not None
    assert charm_person.effects[0].conditions[0].condition == ConditionType.CHARMED
    assert charm_person.effects[0].savingThrow is not None
    assert charm_person.effects[0].savingThrow.ability == AbilityType.WISDOM
    assert charm_person.effects[0].scaling is not None
    assert charm_person.effects[0].scaling[0].scalingType == SpellScalingType.SPELL_SLOT_LEVEL

    assert chill_touch is not None and chill_touch.effects is not None
    assert chill_touch.effects[0].damage is not None
    assert chill_touch.effects[0].damage.dice.dice == "1d10"
    assert chill_touch.effects[0].damage.damageType == DamageType.NECROTIC
    assert chill_touch.effects[0].attack == SpellAttackType.MELEE_SPELL_ATTACK
    assert chill_touch.effects[0].scaling is not None
    assert chill_touch.effects[0].scaling[0].scalingType == SpellScalingType.CANTRIP_LEVEL

    assert color_spray is not None and color_spray.effects is not None
    assert color_spray.targeting.area.shape == SpellAreaShape.CONE
    assert color_spray.effects[0].conditions is not None
    assert color_spray.effects[0].conditions[0].condition == ConditionType.BLINDED
    assert color_spray.effects[0].savingThrow is not None
    assert color_spray.effects[0].savingThrow.ability == AbilityType.CONSTITUTION
    assert color_spray.effects[0].scaling is None

    assert cure_wounds is not None and cure_wounds.effects is not None
    assert cure_wounds.effects[0].healing is not None
    assert cure_wounds.effects[0].healing.dice.dice == "2d8"
    assert cure_wounds.effects[0].healing.dice.bonusSpellcastingAbility is True
    assert cure_wounds.effects[0].scaling is not None
    assert cure_wounds.effects[0].scaling[0].additionalDice is not None
    assert cure_wounds.effects[0].scaling[0].additionalDice.dice == "2d8"

    assert dissonant_whispers is not None and dissonant_whispers.effects is not None
    assert dissonant_whispers.effects[0].damage is not None
    assert dissonant_whispers.effects[0].damage.damageType == DamageType.PSYCHIC
    assert dissonant_whispers.effects[0].savingThrow is not None
    assert dissonant_whispers.effects[0].savingThrow.ability == AbilityType.WISDOM
    assert dissonant_whispers.effects[0].savingThrow.outcome == SpellSaveOutcome.HALF_DAMAGE
    assert dissonant_whispers.effects[0].scaling is not None
    assert dissonant_whispers.effects[0].scaling[0].scalingType == SpellScalingType.SPELL_SLOT_LEVEL

    assert divine_smite is not None and divine_smite.effects is not None
    assert divine_smite.effects[0].damage is not None
    assert divine_smite.effects[0].damage.dice.dice == "2d8"
    assert divine_smite.effects[0].damage.damageType == DamageType.RADIANT
    assert divine_smite.effects[0].trigger == SpellEffectTrigger.ON_HIT
    assert divine_smite.effects[0].actionLabel == "Smite"
    assert divine_smite.effects[0].scaling is not None
    assert divine_smite.effects[0].scaling[0].additionalDice is not None
    assert divine_smite.effects[0].scaling[0].additionalDice.dice == "1d8"
    assert divine_smite.effects[1].damage is not None
    assert divine_smite.effects[1].damage.dice.dice == "1d8"
    assert divine_smite.effects[1].damage.damageType == DamageType.RADIANT
    assert divine_smite.effects[1].trigger == SpellEffectTrigger.SPECIAL
    assert divine_smite.effects[1].targetCreatureTypes == [CreatureType.FIEND, CreatureType.UNDEAD]
    assert divine_smite.effects[1].actionLabel == "Fiend/Undead Bonus"

    assert eldritch_blast is not None and eldritch_blast.effects is not None
    assert eldritch_blast.effects[0].damage is not None
    assert eldritch_blast.effects[0].damage.dice.dice == "1d10"
    assert eldritch_blast.effects[0].damage.damageType == DamageType.FORCE
    assert eldritch_blast.effects[0].attack == SpellAttackType.RANGED_SPELL_ATTACK
    assert eldritch_blast.effects[0].instances == 1
    assert eldritch_blast.effects[0].instanceLabel == "Beam"
    assert eldritch_blast.effects[0].scaling is not None
    assert eldritch_blast.effects[0].scaling[0].scalingType == SpellScalingType.CANTRIP_LEVEL
    assert eldritch_blast.effects[0].scaling[0].additionalInstances == 1

    assert entangle is not None and entangle.effects is not None
    assert entangle.targeting.area.shape == SpellAreaShape.CUBE
    assert entangle.effects[0].conditions is not None
    assert entangle.effects[0].conditions[0].condition == ConditionType.RESTRAINED
    assert entangle.effects[0].savingThrow is not None
    assert entangle.effects[0].savingThrow.ability == AbilityType.STRENGTH

    assert false_life is not None and false_life.effects is not None
    assert false_life.effects[0].temporaryHitPoints is not None
    assert false_life.effects[0].temporaryHitPoints.dice == "2d4"
    assert false_life.effects[0].temporaryHitPoints.staticBonus == 4
    assert false_life.effects[0].scaling is not None
    assert false_life.effects[0].scaling[0].additionalStaticBonus == 5

    assert grease is not None and grease.effects is not None
    assert grease.targeting.area.shape == SpellAreaShape.CUBE
    assert grease.effects[0].conditions is not None
    assert grease.effects[0].conditions[0].condition == ConditionType.PRONE
    assert grease.effects[0].savingThrow is not None
    assert grease.effects[0].savingThrow.ability == AbilityType.DEXTERITY

    assert guiding_bolt is not None and guiding_bolt.effects is not None
    assert guiding_bolt.effects[0].damage is not None
    assert guiding_bolt.effects[0].damage.dice.dice == "4d6"
    assert guiding_bolt.effects[0].damage.damageType == DamageType.RADIANT
    assert guiding_bolt.effects[0].attack == SpellAttackType.RANGED_SPELL_ATTACK
    assert guiding_bolt.effects[0].scaling is not None
    assert guiding_bolt.effects[0].scaling[0].additionalDice is not None
    assert guiding_bolt.effects[0].scaling[0].additionalDice.dice == "1d6"

    assert healing_word is not None and healing_word.effects is not None
    assert healing_word.effects[0].healing is not None
    assert healing_word.effects[0].healing.dice.dice == "2d4"
    assert healing_word.effects[0].healing.dice.bonusSpellcastingAbility is True

    assert hellish_rebuke is not None and hellish_rebuke.effects is not None
    assert hellish_rebuke.effects[0].damage is not None
    assert hellish_rebuke.effects[0].damage.dice.dice == "2d10"
    assert hellish_rebuke.effects[0].damage.damageType == DamageType.FIRE
    assert hellish_rebuke.effects[0].savingThrow is not None
    assert hellish_rebuke.effects[0].savingThrow.ability == AbilityType.DEXTERITY
    assert hellish_rebuke.effects[0].savingThrow.outcome == SpellSaveOutcome.HALF_DAMAGE

    assert hold_person is not None and hold_person.effects is not None
    assert hold_person.effects[0].conditions is not None
    assert hold_person.effects[0].conditions[0].condition == ConditionType.PARALYZED
    assert hold_person.effects[0].savingThrow is not None
    assert hold_person.effects[0].savingThrow.ability == AbilityType.WISDOM
    assert hold_person.effects[0].savingThrow.repeat == SpellEffectTrigger.END_OF_TURN

    assert ice_knife is not None and ice_knife.effects is not None
    assert ice_knife.targeting.area.shape == SpellAreaShape.RADIUS
    assert ice_knife.effects[0].damage is not None
    assert ice_knife.effects[0].damage.damageType == DamageType.PIERCING
    assert ice_knife.effects[0].attack == SpellAttackType.RANGED_SPELL_ATTACK
    assert ice_knife.effects[0].actionLabel == "Target"
    assert ice_knife.effects[1].damage is not None
    assert ice_knife.effects[1].damage.damageType == DamageType.COLD
    assert ice_knife.effects[1].actionLabel == "Blast"
    assert ice_knife.effects[1].savingThrow is not None
    assert ice_knife.effects[1].savingThrow.ability == AbilityType.DEXTERITY
    assert ice_knife.effects[1].savingThrow.outcome == SpellSaveOutcome.NEGATES
    assert ice_knife.effects[1].scaling is not None
    assert ice_knife.effects[1].scaling[0].additionalDice is not None
    assert ice_knife.effects[1].scaling[0].additionalDice.dice == "1d6"

    assert inflict_wounds is not None and inflict_wounds.effects is not None
    assert inflict_wounds.effects[0].damage is not None
    assert inflict_wounds.effects[0].damage.dice.dice == "2d10"
    assert inflict_wounds.effects[0].damage.damageType == DamageType.NECROTIC
    assert inflict_wounds.effects[0].savingThrow is not None
    assert inflict_wounds.effects[0].savingThrow.ability == AbilityType.CONSTITUTION
    assert inflict_wounds.effects[0].savingThrow.outcome == SpellSaveOutcome.HALF_DAMAGE

    assert magic_missile is not None and magic_missile.effects is not None
    assert magic_missile.effects[0].damage is not None
    assert magic_missile.effects[0].damage.dice.dice == "1d4"
    assert magic_missile.effects[0].damage.dice.staticBonus == 1
    assert magic_missile.effects[0].damage.damageType == DamageType.FORCE
    assert magic_missile.effects[0].instances == 3
    assert magic_missile.effects[0].instanceLabel == "Dart"
    assert magic_missile.effects[0].scaling is not None
    assert magic_missile.effects[0].scaling[0].additionalInstances == 1

    assert mind_sliver is not None and mind_sliver.effects is not None
    assert mind_sliver.effects[0].damage is not None
    assert mind_sliver.effects[0].damage.damageType == DamageType.PSYCHIC
    assert mind_sliver.effects[0].savingThrow is not None
    assert mind_sliver.effects[0].savingThrow.ability == AbilityType.INTELLIGENCE
    assert mind_sliver.effects[0].scaling is not None
    assert mind_sliver.effects[0].scaling[0].scalingType == SpellScalingType.CANTRIP_LEVEL

    assert poison_spray is not None and poison_spray.effects is not None
    assert poison_spray.effects[0].damage is not None
    assert poison_spray.effects[0].damage.dice.dice == "1d12"
    assert poison_spray.effects[0].damage.damageType == DamageType.POISON
    assert poison_spray.effects[0].savingThrow is not None
    assert poison_spray.effects[0].savingThrow.ability == AbilityType.CONSTITUTION
    assert poison_spray.effects[0].savingThrow.outcome == SpellSaveOutcome.NEGATES

    assert ray_of_frost is not None and ray_of_frost.effects is not None
    assert ray_of_frost.effects[0].damage is not None
    assert ray_of_frost.effects[0].damage.damageType == DamageType.COLD
    assert ray_of_frost.effects[0].attack == SpellAttackType.RANGED_SPELL_ATTACK
    assert ray_of_frost.effects[0].scaling is not None
    assert ray_of_frost.effects[0].scaling[0].scalingType == SpellScalingType.CANTRIP_LEVEL

    assert ray_of_sickness is not None and ray_of_sickness.effects is not None
    assert ray_of_sickness.effects[0].damage is not None
    assert ray_of_sickness.effects[0].damage.damageType == DamageType.POISON
    assert ray_of_sickness.effects[0].attack == SpellAttackType.RANGED_SPELL_ATTACK
    assert ray_of_sickness.effects[0].conditions is not None
    assert ray_of_sickness.effects[0].conditions[0].condition == ConditionType.POISONED
    assert ray_of_sickness.effects[0].scaling is not None
    assert ray_of_sickness.effects[0].scaling[0].scalingType == SpellScalingType.SPELL_SLOT_LEVEL

    assert sacred_flame is not None and sacred_flame.effects is not None
    assert sacred_flame.effects[0].damage is not None
    assert sacred_flame.effects[0].damage.damageType == DamageType.RADIANT
    assert sacred_flame.effects[0].savingThrow is not None
    assert sacred_flame.effects[0].savingThrow.ability == AbilityType.DEXTERITY
    assert sacred_flame.effects[0].scaling is not None
    assert sacred_flame.effects[0].scaling[0].scalingType == SpellScalingType.CANTRIP_LEVEL

    assert shocking_grasp is not None and shocking_grasp.effects is not None
    assert shocking_grasp.effects[0].damage is not None
    assert shocking_grasp.effects[0].damage.damageType == DamageType.LIGHTNING
    assert shocking_grasp.effects[0].attack == SpellAttackType.MELEE_SPELL_ATTACK

    assert starry_wisp is not None and starry_wisp.effects is not None
    assert starry_wisp.effects[0].damage is not None
    assert starry_wisp.effects[0].damage.damageType == DamageType.RADIANT
    assert starry_wisp.effects[0].attack == SpellAttackType.RANGED_SPELL_ATTACK
    assert starry_wisp.effects[0].scaling is not None
    assert starry_wisp.effects[0].scaling[0].scalingType == SpellScalingType.CANTRIP_LEVEL

    assert tasha is not None and tasha.effects is not None
    assert tasha.effects[0].kind == SpellEffectKind.CONDITION
    assert tasha.effects[0].savingThrow is not None
    assert tasha.effects[0].savingThrow.ability == AbilityType.WISDOM
    assert tasha.effects[0].savingThrow.repeat == SpellEffectTrigger.END_OF_TURN
    assert tasha.effects[0].conditions is not None
    assert [condition.condition for condition in tasha.effects[0].conditions] == [ConditionType.PRONE, ConditionType.INCAPACITATED]
    assert {condition.removalTrigger for condition in tasha.effects[0].conditions} == {ConditionRemovalTrigger.AFTER_TAKING_DAMAGE}

    assert word_of_radiance is not None and word_of_radiance.effects is not None
    assert word_of_radiance.targeting.area.shape == SpellAreaShape.RADIUS
    assert word_of_radiance.effects[0].damage is not None
    assert word_of_radiance.effects[0].damage.damageType == DamageType.RADIANT
    assert word_of_radiance.effects[0].savingThrow is not None
    assert word_of_radiance.effects[0].savingThrow.ability == AbilityType.CONSTITUTION
    assert {condition.removalAdvantage for condition in tasha.effects[0].conditions} == {True}
    assert tasha.effects[0].scaling is not None
    assert tasha.effects[0].scaling[0].scalingType == SpellScalingType.SPELL_SLOT_LEVEL

    assert thunderclap is not None and thunderclap.effects is not None
    assert thunderclap.targeting.area.shape == SpellAreaShape.RADIUS
    assert thunderclap.effects[0].damage is not None
    assert thunderclap.effects[0].damage.damageType == DamageType.THUNDER
    assert thunderclap.effects[0].savingThrow is not None
    assert thunderclap.effects[0].savingThrow.ability == AbilityType.CONSTITUTION
    assert thunderclap.effects[0].scaling is not None
    assert thunderclap.effects[0].scaling[0].scalingType == SpellScalingType.CANTRIP_LEVEL

    assert thunderwave is not None and thunderwave.effects is not None
    assert thunderwave.targeting.area.shape == SpellAreaShape.CUBE
    assert thunderwave.effects[0].damage is not None
    assert thunderwave.effects[0].damage.damageType == DamageType.THUNDER
    assert thunderwave.effects[0].target == SpellEffectTarget.AREA
    assert thunderwave.effects[0].savingThrow is not None
    assert thunderwave.effects[0].savingThrow.ability == AbilityType.CONSTITUTION
    assert thunderwave.effects[0].savingThrow.outcome == SpellSaveOutcome.HALF_DAMAGE
    assert thunderwave.effects[0].scaling is not None
    assert thunderwave.effects[0].scaling[0].scalingType == SpellScalingType.SPELL_SLOT_LEVEL

    assert vicious_mockery is not None and vicious_mockery.effects is not None
    assert vicious_mockery.effects[0].damage is not None
    assert vicious_mockery.effects[0].damage.damageType == DamageType.PSYCHIC
    assert vicious_mockery.effects[0].savingThrow is not None
    assert vicious_mockery.effects[0].savingThrow.ability == AbilityType.WISDOM
    assert vicious_mockery.effects[0].scaling is not None
    assert vicious_mockery.effects[0].scaling[0].scalingType == SpellScalingType.CANTRIP_LEVEL

    assert web is not None and web.effects is not None
    assert web.targeting.area.shape == SpellAreaShape.CUBE
    assert web.effects[0].target == SpellEffectTarget.AREA
    assert web.effects[0].conditions is not None
    assert web.effects[0].conditions[0].condition == ConditionType.RESTRAINED

    assert witch_bolt is not None and witch_bolt.effects is not None
    assert witch_bolt.effects[0].damage is not None
    assert witch_bolt.effects[0].damage.dice.dice == "2d12"
    assert witch_bolt.effects[0].damage.damageType == DamageType.LIGHTNING
    assert witch_bolt.effects[0].attack == SpellAttackType.RANGED_SPELL_ATTACK
    assert witch_bolt.effects[0].scaling is not None
    assert witch_bolt.effects[0].scaling[0].additionalDice is not None
    assert witch_bolt.effects[0].scaling[0].additionalDice.dice == "1d12"
    assert web.effects[1].damage is not None
    assert web.effects[1].damage.dice.dice == "2d4"


def test_catalog_spell_effects_capture_verified_level_two_mechanics() -> None:
    blindness_deafness = spell_entry(SpellId.BLINDNESS_DEAFNESS)
    cloud_of_daggers = spell_entry(SpellId.CLOUD_OF_DAGGERS)
    flaming_sphere = spell_entry(SpellId.FLAMING_SPHERE)
    heat_metal = spell_entry(SpellId.HEAT_METAL)
    invisibility = spell_entry(SpellId.INVISIBILITY)
    melfs_acid_arrow = spell_entry(SpellId.MELF_S_ACID_ARROW)
    mind_spike = spell_entry(SpellId.MIND_SPIKE)
    moonbeam = spell_entry(SpellId.MOONBEAM)
    prayer_of_healing = spell_entry(SpellId.PRAYER_OF_HEALING)
    protection_from_poison = spell_entry(SpellId.PROTECTION_FROM_POISON)
    scorching_ray = spell_entry(SpellId.SCORCHING_RAY)
    searing_orb = spell_entry(SpellId.SEARING_ORB)
    shatter = spell_entry(SpellId.SHATTER)
    spike_growth = spell_entry(SpellId.SPIKE_GROWTH)
    spiritual_weapon = spell_entry(SpellId.SPIRITUAL_WEAPON)

    assert blindness_deafness is not None and blindness_deafness.effects is not None
    assert [effect.conditions[0].condition for effect in blindness_deafness.effects if effect.conditions] == [ConditionType.BLINDED, ConditionType.DEAFENED]
    assert all(effect.savingThrow is not None and effect.savingThrow.ability == AbilityType.CONSTITUTION for effect in blindness_deafness.effects)
    assert all(effect.savingThrow is not None and effect.savingThrow.repeat == SpellEffectTrigger.END_OF_TURN for effect in blindness_deafness.effects)
    assert all(effect.scaling is not None and effect.scaling[0].scalingType == SpellScalingType.SPELL_SLOT_LEVEL for effect in blindness_deafness.effects)

    assert cloud_of_daggers is not None and cloud_of_daggers.effects is not None
    assert cloud_of_daggers.effects[0].damage is not None
    assert cloud_of_daggers.effects[0].damage.dice.dice == "4d4"
    assert cloud_of_daggers.effects[0].damage.damageType == DamageType.SLASHING
    assert cloud_of_daggers.effects[0].scaling is not None
    assert cloud_of_daggers.effects[0].scaling[0].additionalDice is not None
    assert cloud_of_daggers.effects[0].scaling[0].additionalDice.dice == "2d4"

    assert flaming_sphere is not None and flaming_sphere.effects is not None
    assert flaming_sphere.effects[0].damage is not None
    assert flaming_sphere.effects[0].damage.dice.dice == "2d6"
    assert flaming_sphere.effects[0].damage.damageType == DamageType.FIRE
    assert flaming_sphere.effects[0].savingThrow is not None
    assert flaming_sphere.effects[0].savingThrow.ability == AbilityType.DEXTERITY
    assert flaming_sphere.effects[0].savingThrow.outcome == SpellSaveOutcome.HALF_DAMAGE

    assert heat_metal is not None and heat_metal.effects is not None
    assert heat_metal.effects[0].damage is not None
    assert heat_metal.effects[0].damage.dice.dice == "2d8"
    assert heat_metal.effects[0].damage.damageType == DamageType.FIRE
    assert heat_metal.effects[0].scaling is not None
    assert heat_metal.effects[0].scaling[0].additionalDice is not None
    assert heat_metal.effects[0].scaling[0].additionalDice.dice == "1d8"

    assert invisibility is not None and invisibility.effects is not None
    assert invisibility.effects[0].conditions is not None
    assert invisibility.effects[0].conditions[0].condition == ConditionType.INVISIBLE
    assert invisibility.effects[0].scaling is not None
    assert invisibility.effects[0].scaling[0].scalingType == SpellScalingType.SPELL_SLOT_LEVEL

    assert melfs_acid_arrow is not None and melfs_acid_arrow.effects is not None
    assert [effect.actionLabel for effect in melfs_acid_arrow.effects] == ["Hit", "Later"]
    assert melfs_acid_arrow.effects[0].damage is not None
    assert melfs_acid_arrow.effects[0].damage.dice.dice == "4d4"
    assert melfs_acid_arrow.effects[0].attack == SpellAttackType.RANGED_SPELL_ATTACK
    assert melfs_acid_arrow.effects[1].damage is not None
    assert melfs_acid_arrow.effects[1].damage.dice.dice == "2d4"
    assert all(effect.damage is not None and effect.damage.damageType == DamageType.ACID for effect in melfs_acid_arrow.effects)

    assert mind_spike is not None and mind_spike.effects is not None
    assert mind_spike.effects[0].damage is not None
    assert mind_spike.effects[0].damage.dice.dice == "3d8"
    assert mind_spike.effects[0].damage.damageType == DamageType.PSYCHIC
    assert mind_spike.effects[0].savingThrow is not None
    assert mind_spike.effects[0].savingThrow.ability == AbilityType.WISDOM
    assert mind_spike.effects[0].savingThrow.outcome == SpellSaveOutcome.HALF_DAMAGE

    assert moonbeam is not None and moonbeam.effects is not None
    assert moonbeam.effects[0].damage is not None
    assert moonbeam.effects[0].damage.dice.dice == "2d10"
    assert moonbeam.effects[0].damage.damageType == DamageType.RADIANT
    assert moonbeam.effects[0].savingThrow is not None
    assert moonbeam.effects[0].savingThrow.ability == AbilityType.CONSTITUTION
    assert moonbeam.effects[0].savingThrow.outcome == SpellSaveOutcome.HALF_DAMAGE

    assert prayer_of_healing is not None and prayer_of_healing.effects is not None
    assert prayer_of_healing.effects[0].healing is not None
    assert prayer_of_healing.effects[0].healing.dice.dice == "2d8"
    assert prayer_of_healing.effects[0].restType == RestType.SHORT_REST
    assert prayer_of_healing.effects[0].scaling is not None
    assert prayer_of_healing.effects[0].scaling[0].additionalDice is not None
    assert prayer_of_healing.effects[0].scaling[0].additionalDice.dice == "1d8"

    assert protection_from_poison is not None and protection_from_poison.effects is not None
    assert protection_from_poison.effects[0].conditions is not None
    assert protection_from_poison.effects[0].conditions[0].condition == ConditionType.PROTECTION_FROM_POISON
    assert searing_orb is not None and searing_orb.effects is not None
    assert searing_orb.targeting.area.shape == SpellAreaShape.RADIUS
    assert searing_orb.targeting.area.radiusFeet == 10
    assert searing_orb.effects[0].damage is not None
    assert searing_orb.effects[0].damage.dice.dice == "3d4"
    assert searing_orb.effects[0].damage.damageType == DamageType.RADIANT
    assert searing_orb.effects[0].attack == SpellAttackType.RANGED_SPELL_ATTACK
    assert searing_orb.effects[0].scaling is not None
    assert searing_orb.effects[0].scaling[0].additionalDice is not None
    assert searing_orb.effects[0].scaling[0].additionalDice.dice == "1d4"
    assert searing_orb.effects[1].conditions is not None
    assert searing_orb.effects[1].conditions[0].condition == ConditionType.BLINDED
    assert searing_orb.effects[1].savingThrow is not None
    assert searing_orb.effects[1].savingThrow.ability == AbilityType.CONSTITUTION

    assert scorching_ray is not None and scorching_ray.effects is not None
    assert scorching_ray.effects[0].damage is not None
    assert scorching_ray.effects[0].damage.dice.dice == "2d6"
    assert scorching_ray.effects[0].damage.damageType == DamageType.FIRE
    assert scorching_ray.effects[0].instances == 3
    assert scorching_ray.effects[0].scaling is not None
    assert scorching_ray.effects[0].scaling[0].additionalInstances == 1

    assert shatter is not None and shatter.effects is not None
    assert shatter.effects[0].damage is not None
    assert shatter.effects[0].damage.dice.dice == "3d8"
    assert shatter.effects[0].damage.damageType == DamageType.THUNDER
    assert shatter.effects[0].savingThrow is not None
    assert shatter.effects[0].savingThrow.ability == AbilityType.CONSTITUTION
    assert shatter.effects[0].savingThrow.outcome == SpellSaveOutcome.HALF_DAMAGE
    assert shatter.effects[0].savingThrow.disadvantageCreatureTypes == [CreatureType.CONSTRUCT]
    assert "Constructs have Disadvantage" in shatter.effects[0].description

    assert spike_growth is not None and spike_growth.effects is not None
    assert spike_growth.effects[0].damage is not None
    assert spike_growth.effects[0].damage.dice.dice == "2d4"
    assert spike_growth.effects[0].damage.damageType == DamageType.PIERCING

    assert spiritual_weapon is not None and spiritual_weapon.effects is not None
    assert spiritual_weapon.effects[0].damage is not None
    assert spiritual_weapon.effects[0].damage.dice.dice == "1d8"
    assert spiritual_weapon.effects[0].damage.dice.bonusSpellcastingAbility is True
    assert spiritual_weapon.effects[0].damage.damageType == DamageType.FORCE
    assert spiritual_weapon.effects[0].attack == SpellAttackType.MELEE_SPELL_ATTACK
    assert spiritual_weapon.effects[0].scaling is not None
    assert spiritual_weapon.effects[0].scaling[0].additionalDice is not None
    assert spiritual_weapon.effects[0].scaling[0].additionalDice.dice == "1d8"


def test_catalog_spell_effects_capture_verified_level_three_mechanics() -> None:
    aura_of_vitality = spell_entry(SpellId.AURA_OF_VITALITY)
    blinding_smite = spell_entry(SpellId.BLINDING_SMITE)
    call_lightning = spell_entry(SpellId.CALL_LIGHTNING)
    conjure_barrage = spell_entry(SpellId.CONJURE_BARRAGE)
    fear = spell_entry(SpellId.FEAR)
    fly = spell_entry(SpellId.FLY)
    haste = spell_entry(SpellId.HASTE)
    hypnotic_pattern = spell_entry(SpellId.HYPNOTIC_PATTERN)
    lightning_bolt = spell_entry(SpellId.LIGHTNING_BOLT)
    mass_healing_word = spell_entry(SpellId.MASS_HEALING_WORD)
    spirit_guardians = spell_entry(SpellId.SPIRIT_GUARDIANS)
    stinking_cloud = spell_entry(SpellId.STINKING_CLOUD)
    vampiric_touch = spell_entry(SpellId.VAMPIRIC_TOUCH)
    wind_wall = spell_entry(SpellId.WIND_WALL)

    assert aura_of_vitality is not None and aura_of_vitality.effects is not None
    assert aura_of_vitality.targeting.area.shape == SpellAreaShape.RADIUS
    assert aura_of_vitality.targeting.area.radiusFeet == 30
    assert aura_of_vitality.effects[0].healing is not None
    assert aura_of_vitality.effects[0].healing.dice.dice == "2d6"

    assert blinding_smite is not None and blinding_smite.effects is not None
    assert blinding_smite.effects[0].damage is not None
    assert blinding_smite.effects[0].damage.dice.dice == "3d8"
    assert blinding_smite.effects[0].damage.damageType == DamageType.RADIANT
    assert blinding_smite.effects[0].trigger == SpellEffectTrigger.ON_HIT
    assert blinding_smite.effects[0].scaling is not None
    assert blinding_smite.effects[0].scaling[0].additionalDice is not None
    assert blinding_smite.effects[0].scaling[0].additionalDice.dice == "1d8"
    assert blinding_smite.effects[1].conditions is not None
    assert blinding_smite.effects[1].conditions[0].condition == ConditionType.BLINDED
    assert blinding_smite.effects[1].savingThrow is not None
    assert blinding_smite.effects[1].savingThrow.ability == AbilityType.CONSTITUTION
    assert blinding_smite.effects[1].savingThrow.repeat == SpellEffectTrigger.END_OF_TURN

    assert call_lightning is not None and call_lightning.effects is not None
    assert call_lightning.targeting.area.shape == SpellAreaShape.RADIUS
    assert call_lightning.targeting.area.radiusFeet == 5
    assert call_lightning.effects[0].damage is not None
    assert call_lightning.effects[0].damage.dice.dice == "3d10"
    assert call_lightning.effects[0].damage.damageType == DamageType.LIGHTNING
    assert call_lightning.effects[0].savingThrow is not None
    assert call_lightning.effects[0].savingThrow.ability == AbilityType.DEXTERITY
    assert call_lightning.effects[0].savingThrow.outcome == SpellSaveOutcome.HALF_DAMAGE
    assert call_lightning.effects[0].scaling is not None
    assert call_lightning.effects[0].scaling[0].additionalDice is not None
    assert call_lightning.effects[0].scaling[0].additionalDice.dice == "1d10"

    assert conjure_barrage is not None and conjure_barrage.effects is not None
    assert conjure_barrage.targeting.area.shape == SpellAreaShape.CONE
    assert conjure_barrage.targeting.area.lengthFeet == 60
    assert conjure_barrage.effects[0].damage is not None
    assert conjure_barrage.effects[0].damage.dice.dice == "5d8"
    assert conjure_barrage.effects[0].damage.damageType == DamageType.FORCE
    assert conjure_barrage.effects[0].savingThrow is not None
    assert conjure_barrage.effects[0].savingThrow.ability == AbilityType.DEXTERITY

    assert fear is not None and fear.effects is not None
    assert fear.targeting.area.shape == SpellAreaShape.CONE
    assert fear.effects[0].conditions is not None
    assert fear.effects[0].conditions[0].condition == ConditionType.FRIGHTENED
    assert fear.effects[0].savingThrow is not None
    assert fear.effects[0].savingThrow.ability == AbilityType.WISDOM

    assert fly is not None and fly.effects is not None
    assert fly.effects[0].conditions is not None
    assert fly.effects[0].conditions[0].condition == ConditionType.FLYING
    assert fly.effects[0].scaling is not None
    assert fly.effects[0].scaling[0].scalingType == SpellScalingType.SPELL_SLOT_LEVEL

    assert haste is not None and haste.effects is not None
    assert haste.effects[0].conditions is not None
    assert haste.effects[0].conditions[0].condition == ConditionType.HASTED

    assert hypnotic_pattern is not None and hypnotic_pattern.effects is not None
    assert hypnotic_pattern.targeting.area.shape == SpellAreaShape.CUBE
    assert hypnotic_pattern.effects[0].conditions is not None
    assert [condition.condition for condition in hypnotic_pattern.effects[0].conditions] == [ConditionType.CHARMED, ConditionType.INCAPACITATED]
    assert {condition.removalTrigger for condition in hypnotic_pattern.effects[0].conditions} == {ConditionRemovalTrigger.AFTER_TAKING_DAMAGE}
    assert hypnotic_pattern.effects[0].savingThrow is not None
    assert hypnotic_pattern.effects[0].savingThrow.ability == AbilityType.WISDOM

    assert lightning_bolt is not None and lightning_bolt.effects is not None
    assert lightning_bolt.targeting.area.shape == SpellAreaShape.LINE
    assert lightning_bolt.targeting.area.lengthFeet == 100
    assert lightning_bolt.targeting.area.widthFeet == 5
    assert lightning_bolt.effects[0].damage is not None
    assert lightning_bolt.effects[0].damage.dice.dice == "8d6"
    assert lightning_bolt.effects[0].damage.damageType == DamageType.LIGHTNING
    assert lightning_bolt.effects[0].savingThrow is not None
    assert lightning_bolt.effects[0].savingThrow.ability == AbilityType.DEXTERITY
    assert lightning_bolt.effects[0].savingThrow.outcome == SpellSaveOutcome.HALF_DAMAGE

    assert mass_healing_word is not None and mass_healing_word.effects is not None
    assert mass_healing_word.effects[0].healing is not None
    assert mass_healing_word.effects[0].healing.dice.dice == "2d4"
    assert mass_healing_word.effects[0].healing.dice.bonusSpellcastingAbility is True
    assert mass_healing_word.effects[0].scaling is not None
    assert mass_healing_word.effects[0].scaling[0].additionalDice is not None
    assert mass_healing_word.effects[0].scaling[0].additionalDice.dice == "1d4"

    assert spirit_guardians is not None and spirit_guardians.effects is not None
    assert spirit_guardians.targeting.area.shape == SpellAreaShape.RADIUS
    assert spirit_guardians.targeting.area.radiusFeet == 15
    assert [effect.damage.damageType for effect in spirit_guardians.effects if effect.damage] == [DamageType.RADIANT, DamageType.NECROTIC]
    assert all(effect.damage is not None and effect.damage.dice.dice == "3d8" for effect in spirit_guardians.effects)
    assert all(effect.savingThrow is not None and effect.savingThrow.ability == AbilityType.WISDOM for effect in spirit_guardians.effects)
    assert all(effect.savingThrow is not None and effect.savingThrow.outcome == SpellSaveOutcome.HALF_DAMAGE for effect in spirit_guardians.effects)

    assert stinking_cloud is not None and stinking_cloud.effects is not None
    assert stinking_cloud.targeting.area.shape == SpellAreaShape.RADIUS
    assert stinking_cloud.targeting.area.radiusFeet == 20
    assert stinking_cloud.effects[0].conditions is not None
    assert stinking_cloud.effects[0].conditions[0].condition == ConditionType.POISONED
    assert stinking_cloud.effects[0].trigger == SpellEffectTrigger.START_OF_TURN
    assert stinking_cloud.effects[0].savingThrow is not None
    assert stinking_cloud.effects[0].savingThrow.ability == AbilityType.CONSTITUTION

    assert vampiric_touch is not None and vampiric_touch.effects is not None
    assert vampiric_touch.effects[0].damage is not None
    assert vampiric_touch.effects[0].damage.dice.dice == "3d6"
    assert vampiric_touch.effects[0].damage.damageType == DamageType.NECROTIC
    assert vampiric_touch.effects[0].attack == SpellAttackType.MELEE_SPELL_ATTACK
    assert vampiric_touch.effects[0].sourceHealing is not None
    assert vampiric_touch.effects[0].sourceHealing.amount == SpellLinkedHealingAmount.HALF_DAMAGE_DEALT
    assert vampiric_touch.effects[0].scaling is not None
    assert vampiric_touch.effects[0].scaling[0].additionalDice is not None
    assert vampiric_touch.effects[0].scaling[0].additionalDice.dice == "1d6"

    assert wind_wall is not None and wind_wall.effects is not None
    assert wind_wall.targeting.area.shape == SpellAreaShape.LINE
    assert wind_wall.targeting.area.lengthFeet == 50
    assert wind_wall.targeting.area.widthFeet == 1
    assert wind_wall.effects[0].damage is not None
    assert wind_wall.effects[0].damage.dice.dice == "4d8"
    assert wind_wall.effects[0].damage.damageType == DamageType.BLUDGEONING
    assert wind_wall.effects[0].savingThrow is not None
    assert wind_wall.effects[0].savingThrow.ability == AbilityType.STRENGTH
    assert wind_wall.effects[0].savingThrow.outcome == SpellSaveOutcome.HALF_DAMAGE


def test_catalog_spell_effects_capture_verified_higher_level_mechanics() -> None:
    cone_of_cold = spell_entry(SpellId.CONE_OF_COLD)
    fire_shield = spell_entry(SpellId.FIRE_SHIELD)
    greater_invisibility = spell_entry(SpellId.GREATER_INVISIBILITY)
    ice_storm = spell_entry(SpellId.ICE_STORM)
    phantasmal_killer = spell_entry(SpellId.PHANTASMAL_KILLER)
    staggering_smite = spell_entry(SpellId.STAGGERING_SMITE)
    stoneskin = spell_entry(SpellId.STONESKIN)
    vitriolic_sphere = spell_entry(SpellId.VITRIOLIC_SPHERE)
    wall_of_fire = spell_entry(SpellId.WALL_OF_FIRE)

    assert cone_of_cold is not None and cone_of_cold.effects is not None
    assert cone_of_cold.targeting.area.shape == SpellAreaShape.CONE
    assert cone_of_cold.targeting.area.lengthFeet == 60
    assert cone_of_cold.effects[0].damage is not None
    assert cone_of_cold.effects[0].damage.dice.dice == "8d8"
    assert cone_of_cold.effects[0].damage.damageType == DamageType.COLD
    assert cone_of_cold.effects[0].savingThrow is not None
    assert cone_of_cold.effects[0].savingThrow.ability == AbilityType.CONSTITUTION
    assert cone_of_cold.effects[0].savingThrow.outcome == SpellSaveOutcome.HALF_DAMAGE
    assert cone_of_cold.effects[0].scaling is not None
    assert cone_of_cold.effects[0].scaling[0].additionalDice is not None
    assert cone_of_cold.effects[0].scaling[0].additionalDice.dice == "1d8"

    assert greater_invisibility is not None and greater_invisibility.effects is not None
    assert greater_invisibility.effects[0].conditions is not None
    assert greater_invisibility.effects[0].conditions[0].condition == ConditionType.INVISIBLE

    assert ice_storm is not None and ice_storm.effects is not None
    assert ice_storm.targeting.area.shape == SpellAreaShape.CYLINDER
    assert ice_storm.targeting.area.radiusFeet == 20
    assert ice_storm.targeting.area.heightFeet == 40
    assert ice_storm.effects[0].savingThrow is not None
    assert ice_storm.effects[0].savingThrow.ability == AbilityType.DEXTERITY
    assert ice_storm.effects[0].savingThrow.outcome == SpellSaveOutcome.HALF_DAMAGE
    assert ice_storm.effects[0].damageComponents is not None
    assert [component.dice.dice for component in ice_storm.effects[0].damageComponents] == ["2d10", "4d6"]
    assert [component.damageType for component in ice_storm.effects[0].damageComponents] == [DamageType.BLUDGEONING, DamageType.COLD]
    assert ice_storm.effects[0].damageComponents[0].scaling is not None
    assert ice_storm.effects[0].damageComponents[0].scaling[0].additionalDice is not None
    assert ice_storm.effects[0].damageComponents[0].scaling[0].additionalDice.dice == "1d10"
    assert ice_storm.effects[0].damageComponents[1].scaling is None

    assert fire_shield is not None and fire_shield.effects is not None
    assert [effect.actionLabel for effect in fire_shield.effects] == ["Warm Shield", "Warm Retaliation", "Chill Shield", "Chill Retaliation"]
    assert fire_shield.effects[0].conditions is not None
    assert fire_shield.effects[0].conditions[0].condition == ConditionType.RESISTANCE_COLD
    assert fire_shield.effects[1].damage is not None
    assert fire_shield.effects[1].damage.dice.dice == "2d8"
    assert fire_shield.effects[1].damage.damageType == DamageType.FIRE
    assert fire_shield.effects[2].conditions is not None
    assert fire_shield.effects[2].conditions[0].condition == ConditionType.RESISTANCE_FIRE
    assert fire_shield.effects[3].damage is not None
    assert fire_shield.effects[3].damage.damageType == DamageType.COLD

    assert phantasmal_killer is not None and phantasmal_killer.effects is not None
    assert phantasmal_killer.effects[0].damage is not None
    assert phantasmal_killer.effects[0].damage.dice.dice == "4d10"
    assert phantasmal_killer.effects[0].damage.damageType == DamageType.PSYCHIC
    assert phantasmal_killer.effects[0].savingThrow is not None
    assert phantasmal_killer.effects[0].savingThrow.ability == AbilityType.WISDOM
    assert phantasmal_killer.effects[0].savingThrow.outcome == SpellSaveOutcome.HALF_DAMAGE
    assert phantasmal_killer.effects[0].scaling is not None
    assert phantasmal_killer.effects[0].scaling[0].additionalDice is not None
    assert phantasmal_killer.effects[0].scaling[0].additionalDice.dice == "1d10"
    assert phantasmal_killer.effects[1].conditions is not None
    assert phantasmal_killer.effects[1].conditions[0].condition == ConditionType.PHANTASMAL_KILLER

    assert staggering_smite is not None and staggering_smite.effects is not None
    assert staggering_smite.effects[0].damage is not None
    assert staggering_smite.effects[0].damage.dice.dice == "4d6"
    assert staggering_smite.effects[0].damage.damageType == DamageType.PSYCHIC
    assert staggering_smite.effects[0].scaling is not None
    assert staggering_smite.effects[0].scaling[0].additionalDice is not None
    assert staggering_smite.effects[0].scaling[0].additionalDice.dice == "1d6"
    assert staggering_smite.effects[1].conditions is not None
    assert staggering_smite.effects[1].conditions[0].condition == ConditionType.STUNNED
    assert staggering_smite.effects[1].savingThrow is not None
    assert staggering_smite.effects[1].savingThrow.ability == AbilityType.WISDOM

    assert stoneskin is not None and stoneskin.effects is not None
    assert stoneskin.effects[0].conditions is not None
    assert [condition.condition for condition in stoneskin.effects[0].conditions] == [
        ConditionType.RESISTANCE_BLUDGEONING,
        ConditionType.RESISTANCE_PIERCING,
        ConditionType.RESISTANCE_SLASHING,
    ]

    assert vitriolic_sphere is not None and vitriolic_sphere.effects is not None
    assert vitriolic_sphere.targeting.area.shape == SpellAreaShape.RADIUS
    assert vitriolic_sphere.targeting.area.radiusFeet == 20
    assert [effect.actionLabel for effect in vitriolic_sphere.effects] == ["Initial", "Later"]
    assert vitriolic_sphere.effects[0].damage is not None
    assert vitriolic_sphere.effects[0].damage.dice.dice == "10d4"
    assert vitriolic_sphere.effects[0].damage.damageType == DamageType.ACID
    assert vitriolic_sphere.effects[0].savingThrow is not None
    assert vitriolic_sphere.effects[0].savingThrow.ability == AbilityType.DEXTERITY
    assert vitriolic_sphere.effects[0].savingThrow.outcome == SpellSaveOutcome.HALF_DAMAGE
    assert vitriolic_sphere.effects[0].scaling is not None
    assert vitriolic_sphere.effects[0].scaling[0].additionalDice is not None
    assert vitriolic_sphere.effects[0].scaling[0].additionalDice.dice == "2d4"
    assert vitriolic_sphere.effects[1].damage is not None
    assert vitriolic_sphere.effects[1].damage.dice.dice == "5d4"

    assert wall_of_fire is not None and wall_of_fire.effects is not None
    assert [effect.actionLabel for effect in wall_of_fire.effects] == ["Appears", "Hot Side"]
    assert all(effect.damage is not None and effect.damage.dice.dice == "5d8" for effect in wall_of_fire.effects)
    assert all(effect.damage is not None and effect.damage.damageType == DamageType.FIRE for effect in wall_of_fire.effects)
    assert wall_of_fire.effects[0].savingThrow is not None
    assert wall_of_fire.effects[0].savingThrow.ability == AbilityType.DEXTERITY
    assert wall_of_fire.effects[0].savingThrow.outcome == SpellSaveOutcome.HALF_DAMAGE
    assert wall_of_fire.effects[1].savingThrow is None


def test_catalog_spell_effects_capture_additional_level_zero_and_one_mechanics() -> None:
    produce_flame = spell_entry(SpellId.PRODUCE_FLAME)
    sorcerous_burst = spell_entry(SpellId.SORCEROUS_BURST)
    thorn_whip = spell_entry(SpellId.THORN_WHIP)
    toll_the_dead = spell_entry(SpellId.TOLL_THE_DEAD)
    animal_friendship = spell_entry(SpellId.ANIMAL_FRIENDSHIP)
    bane = spell_entry(SpellId.BANE)
    bless = spell_entry(SpellId.BLESS)
    chromatic_orb = spell_entry(SpellId.CHROMATIC_ORB)
    command = spell_entry(SpellId.COMMAND)
    divine_favor = spell_entry(SpellId.DIVINE_FAVOR)
    ensnaring_strike = spell_entry(SpellId.ENSNARING_STRIKE)
    faerie_fire = spell_entry(SpellId.FAERIE_FIRE)
    goodberry = spell_entry(SpellId.GOODBERRY)
    guidance = spell_entry(SpellId.GUIDANCE)
    hail_of_thorns = spell_entry(SpellId.HAIL_OF_THORNS)
    hex_spell = spell_entry(SpellId.HEX)
    hunters_mark = spell_entry(SpellId.HUNTER_S_MARK)
    longstrider = spell_entry(SpellId.LONGSTRIDER)
    mage_armor = spell_entry(SpellId.MAGE_ARMOR)
    searing_smite = spell_entry(SpellId.SEARING_SMITE)
    resistance = spell_entry(SpellId.RESISTANCE)
    shield_of_faith = spell_entry(SpellId.SHIELD_OF_FAITH)
    sleep = spell_entry(SpellId.SLEEP)
    spellfire_flare = spell_entry(SpellId.SPELLFIRE_FLARE)
    thunderous_smite = spell_entry(SpellId.THUNDEROUS_SMITE)
    wrathful_smite = spell_entry(SpellId.WRATHFUL_SMITE)

    assert produce_flame is not None and produce_flame.effects is not None
    assert produce_flame.effects[0].actionLabel == "Hurl"
    assert produce_flame.effects[0].damage is not None
    assert produce_flame.effects[0].damage.dice.dice == "1d8"
    assert produce_flame.effects[0].attack == SpellAttackType.RANGED_SPELL_ATTACK

    assert sorcerous_burst is not None and sorcerous_burst.effects is not None
    assert {effect.damage.damageType for effect in sorcerous_burst.effects if effect.damage is not None} == {
        DamageType.ACID,
        DamageType.COLD,
        DamageType.FIRE,
        DamageType.LIGHTNING,
        DamageType.POISON,
        DamageType.PSYCHIC,
        DamageType.THUNDER,
    }
    assert {effect.actionLabel for effect in sorcerous_burst.effects} == {
        "Acid",
        "Bonus Acid",
        "Bonus Cold",
        "Bonus Fire",
        "Bonus Lightning",
        "Bonus Poison",
        "Bonus Psychic",
        "Bonus Thunder",
        "Cold",
        "Fire",
        "Lightning",
        "Poison",
        "Psychic",
        "Thunder",
    }
    assert {effect.trigger for effect in sorcerous_burst.effects if effect.actionLabel.startswith("Bonus")} == {SpellEffectTrigger.SPECIAL}

    assert thorn_whip is not None and thorn_whip.effects is not None
    assert thorn_whip.effects[0].damage is not None
    assert thorn_whip.effects[0].damage.damageType == DamageType.PIERCING
    assert thorn_whip.effects[0].attack == SpellAttackType.MELEE_SPELL_ATTACK

    assert toll_the_dead is not None and toll_the_dead.effects is not None
    assert [effect.actionLabel for effect in toll_the_dead.effects] == ["Healthy", "Wounded"]
    assert [effect.damage.dice.dice for effect in toll_the_dead.effects if effect.damage is not None] == ["1d8", "1d12"]
    assert {effect.savingThrow.ability for effect in toll_the_dead.effects if effect.savingThrow is not None} == {AbilityType.WISDOM}

    assert animal_friendship is not None and animal_friendship.effects is not None
    assert animal_friendship.effects[0].conditions is not None
    assert animal_friendship.effects[0].conditions[0].condition == ConditionType.CHARMED
    assert animal_friendship.effects[0].savingThrow is not None
    assert animal_friendship.effects[0].savingThrow.ability == AbilityType.WISDOM

    assert bane is not None and bane.effects is not None
    assert bane.effects[0].conditions is not None
    assert bane.effects[0].conditions[0].condition == ConditionType.BANE
    assert bane.effects[0].savingThrow is not None
    assert bane.effects[0].savingThrow.ability == AbilityType.CHARISMA
    assert bane.effects[0].rollModifier is not None
    assert bane.effects[0].rollModifier.operation == RollModifierEffectOperation.SUBTRACT
    assert set(bane.effects[0].rollModifier.targets) == {RollModifierEffectTarget.ATTACK_ROLL, RollModifierEffectTarget.SAVING_THROW}

    assert bless is not None and bless.effects is not None
    assert bless.effects[0].conditions is not None
    assert bless.effects[0].conditions[0].condition == ConditionType.BLESSED
    assert bless.effects[0].savingThrow is None
    assert bless.effects[0].rollModifier is not None
    assert bless.effects[0].rollModifier.operation == RollModifierEffectOperation.ADD
    assert set(bless.effects[0].rollModifier.targets) == {RollModifierEffectTarget.ATTACK_ROLL, RollModifierEffectTarget.SAVING_THROW}

    shield = spell_entry(SpellId.SHIELD)
    assert shield is not None and shield.effects is not None
    assert shield.castingTime == TimeEconomy.REACTION
    assert shield.effects[0].conditions is not None
    assert shield.effects[0].conditions[0].condition == ConditionType.SHIELDED

    assert longstrider is not None and longstrider.effects is not None
    assert longstrider.effects[0].conditions is not None
    assert longstrider.effects[0].conditions[0].condition == ConditionType.LONGSTRIDER
    assert longstrider.effects[0].scaling is not None

    assert mage_armor is not None and mage_armor.effects is not None
    assert mage_armor.effects[0].conditions is not None
    assert mage_armor.effects[0].conditions[0].condition == ConditionType.MAGE_ARMOR

    assert shield_of_faith is not None and shield_of_faith.effects is not None
    assert shield_of_faith.effects[0].conditions is not None
    assert shield_of_faith.effects[0].conditions[0].condition == ConditionType.SHIELD_OF_FAITH

    assert chromatic_orb is not None and chromatic_orb.effects is not None
    assert len(chromatic_orb.effects) == 6
    assert {effect.damage.damageType for effect in chromatic_orb.effects if effect.damage is not None} == {
        DamageType.ACID,
        DamageType.COLD,
        DamageType.FIRE,
        DamageType.LIGHTNING,
        DamageType.POISON,
        DamageType.THUNDER,
    }
    assert {effect.attack for effect in chromatic_orb.effects} == {SpellAttackType.RANGED_SPELL_ATTACK}

    assert command is not None and command.effects is not None
    assert [effect.actionLabel for effect in command.effects] == ["Approach", "Drop", "Flee", "Grovel", "Halt"]
    assert [effect.conditions[0].condition for effect in command.effects if effect.conditions is not None] == [
        ConditionType.COMMAND_APPROACH,
        ConditionType.COMMAND_DROP,
        ConditionType.COMMAND_FLEE,
        ConditionType.COMMAND_GROVEL,
        ConditionType.COMMAND_HALT,
    ]
    assert command.effects[3].conditions is not None
    assert [condition.condition for condition in command.effects[3].conditions] == [ConditionType.COMMAND_GROVEL, ConditionType.PRONE]
    assert {effect.savingThrow.ability for effect in command.effects if effect.savingThrow is not None} == {AbilityType.WISDOM}

    assert divine_favor is not None and divine_favor.effects is not None
    assert divine_favor.effects[0].actionLabel == "Weapon Bonus"
    assert divine_favor.effects[0].damage is not None
    assert divine_favor.effects[0].damage.damageType == DamageType.RADIANT

    assert ensnaring_strike is not None and ensnaring_strike.effects is not None
    assert ensnaring_strike.effects[0].conditions is not None
    assert ensnaring_strike.effects[0].conditions[0].condition == ConditionType.RESTRAINED
    assert ensnaring_strike.effects[1].damage is not None
    assert ensnaring_strike.effects[1].trigger == SpellEffectTrigger.START_OF_TURN

    assert faerie_fire is not None and faerie_fire.effects is not None
    assert faerie_fire.targeting.area.shape == SpellAreaShape.CUBE
    assert faerie_fire.effects[0].kind == SpellEffectKind.CONDITION
    assert faerie_fire.effects[0].conditions is not None
    assert faerie_fire.effects[0].conditions[0].condition == ConditionType.FAERIE_FIRE
    assert faerie_fire.effects[0].savingThrow is not None
    assert faerie_fire.effects[0].savingThrow.ability == AbilityType.DEXTERITY

    assert goodberry is not None and goodberry.effects is not None
    assert goodberry.effects[0].healing is not None
    assert goodberry.effects[0].healing.dice.staticBonus == 1

    assert guidance is not None and guidance.effects is not None
    assert guidance.effects[0].conditions is not None
    assert guidance.effects[0].conditions[0].condition == ConditionType.GUIDANCE
    assert guidance.effects[0].rollModifier is not None
    assert guidance.effects[0].rollModifier.targets == [RollModifierEffectTarget.ABILITY_CHECK]

    assert hail_of_thorns is not None and hail_of_thorns.effects is not None
    assert hail_of_thorns.targeting.area.shape == SpellAreaShape.RADIUS
    assert hail_of_thorns.effects[0].damage is not None
    assert hail_of_thorns.effects[0].savingThrow is not None
    assert hail_of_thorns.effects[0].savingThrow.outcome == SpellSaveOutcome.HALF_DAMAGE

    assert hex_spell is not None and hex_spell.effects is not None
    assert hex_spell.effects[0].actionLabel == "Hex Bonus"
    assert hex_spell.effects[0].damage is not None
    assert hex_spell.effects[0].damage.damageType == DamageType.NECROTIC

    assert hunters_mark is not None and hunters_mark.effects is not None
    assert hunters_mark.effects[0].actionLabel == "Mark Bonus"
    assert hunters_mark.effects[0].damage is not None
    assert hunters_mark.effects[0].damage.damageType == DamageType.FORCE

    assert searing_smite is not None and searing_smite.effects is not None
    assert [effect.actionLabel for effect in searing_smite.effects] == ["Hit", "Burn"]
    assert [effect.damage.dice.dice for effect in searing_smite.effects if effect.damage is not None] == ["1d6", "1d6"]
    assert {effect.scaling[0].additionalDice.dice for effect in searing_smite.effects if effect.scaling and effect.scaling[0].additionalDice is not None} == {"1d6"}

    assert resistance is not None and resistance.effects is not None
    assert len(resistance.effects) == len(DamageType)
    assert [effect.actionLabel for effect in resistance.effects] == [
        "Acid",
        "Bludgeoning",
        "Cold",
        "Fire",
        "Force",
        "Lightning",
        "Necrotic",
        "Piercing",
        "Poison",
        "Psychic",
        "Radiant",
        "Slashing",
        "Thunder",
    ]
    assert [effect.conditions[0].condition for effect in resistance.effects if effect.conditions is not None] == [
        ConditionType.RESISTANCE_ACID,
        ConditionType.RESISTANCE_BLUDGEONING,
        ConditionType.RESISTANCE_COLD,
        ConditionType.RESISTANCE_FIRE,
        ConditionType.RESISTANCE_FORCE,
        ConditionType.RESISTANCE_LIGHTNING,
        ConditionType.RESISTANCE_NECROTIC,
        ConditionType.RESISTANCE_PIERCING,
        ConditionType.RESISTANCE_POISON,
        ConditionType.RESISTANCE_PSYCHIC,
        ConditionType.RESISTANCE_RADIANT,
        ConditionType.RESISTANCE_SLASHING,
        ConditionType.RESISTANCE_THUNDER,
    ]
    assert all(effect.rollModifier is None for effect in resistance.effects)

    assert sleep is not None and sleep.effects is not None
    assert sleep.targeting.area.shape == SpellAreaShape.RADIUS
    assert [effect.actionLabel for effect in sleep.effects] == ["Drowsy", "Asleep"]
    assert [effect.conditions[0].condition for effect in sleep.effects if effect.conditions is not None] == [ConditionType.INCAPACITATED, ConditionType.UNCONSCIOUS]

    assert spellfire_flare is not None and spellfire_flare.effects is not None
    assert spellfire_flare.effects[0].damage is not None
    assert spellfire_flare.effects[0].instances == 1
    assert spellfire_flare.effects[0].instanceLabel == "Blast"
    assert spellfire_flare.effects[0].scaling is not None
    assert spellfire_flare.effects[0].scaling[0].additionalInstances == 1

    assert thunderous_smite is not None and thunderous_smite.effects is not None
    assert thunderous_smite.effects[0].damage is not None
    assert thunderous_smite.effects[0].damage.damageType == DamageType.THUNDER
    assert thunderous_smite.effects[1].conditions is not None
    assert thunderous_smite.effects[1].conditions[0].condition == ConditionType.PRONE

    assert wrathful_smite is not None and wrathful_smite.effects is not None
    assert wrathful_smite.effects[0].damage is not None
    assert wrathful_smite.effects[0].damage.damageType == DamageType.NECROTIC
    assert wrathful_smite.effects[1].conditions is not None
    assert wrathful_smite.effects[1].conditions[0].condition == ConditionType.FRIGHTENED
    assert wrathful_smite.effects[1].conditions[0].saveEnds is True


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
