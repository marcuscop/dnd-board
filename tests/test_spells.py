from dnd_board.character_sheet import (
    AbilityType,
    ClassType,
    ConditionType,
    DamageType,
    CreatureType,
    DiceType,
    SpellAttackType,
    SpellAreaShape,
    SpellComponent,
    SpellDurationUnit,
    SpellEffectTarget,
    SpellEffectTrigger,
    SpellId,
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
from dnd_board.rules.shared.effects import (
    AmountCalculation,
    ApplyEffect,
    AttackRollEffect,
    AttackRollType,
    CalculatedAmount,
    CombinedAmount,
    ChoiceEffect,
    ConditionChangeEffect,
    ConditionOperation,
    DamageDefenseEffect,
    DamageDefenseType,
    DamageEffect,
    DiceAmount,
    DerivedAmount,
    EffectResultValue,
    EffectTarget,
    HealingEffect,
    RepeatedEffect,
    MaximumHitPointsEffect,
    MaximumHitPointsOperation,
    MovementEffect,
    MovementType,
    SavingThrowEffect,
    ScalingBasis,
    SequenceEffect,
    TemporaryHitPointsEffect,
)
from dnd_board.rules.shared.resources import ResourceCost, ResourceId


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


def test_spell_resource_costs_only_cover_one_cast_control() -> None:
    burning_hands = wizard_spell_entry(SpellId.BURNING_HANDS)
    fire_bolt = wizard_spell_entry(SpellId.FIRE_BOLT)
    magic_missile = wizard_spell_entry(SpellId.MAGIC_MISSILE)
    acid_arrow = wizard_spell_entry(SpellId.MELF_S_ACID_ARROW)

    assert burning_hands is not None
    assert fire_bolt is not None
    assert magic_missile is not None
    assert acid_arrow is not None
    assert burning_hands.resourceCosts == (ResourceCost(ResourceId.SPELL_SLOT),)
    assert fire_bolt.resourceCosts == ()
    assert magic_missile.resourceCosts == ()
    assert acid_arrow.resourceCosts == ()


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
    fire = spell_damage_effect(1, DiceType.D10, DamageType.FIRE, attack=SpellAttackType.RANGED_SPELL_ATTACK)
    cure = spell_healing_effect(2, DiceType.D8, bonus_ability=AbilityType.WISDOM)
    held = spell_condition_effect(ConditionType.PARALYZED, saving_throw=spell_save(AbilityType.WISDOM))
    armor = spell_temporary_hit_points_effect(5, DiceType.D4, static_bonus=5, target=SpellEffectTarget.SELF)

    assert isinstance(fire, AttackRollEffect)
    assert isinstance(fire.onHit, ApplyEffect)
    assert isinstance(fire.onHit.effect, DamageEffect)
    assert fire.onHit.effect.damageType == DamageType.FIRE
    assert isinstance(cure, ApplyEffect) and isinstance(cure.effect, HealingEffect)
    assert isinstance(cure.effect.amount, CombinedAmount)
    assert isinstance(held, SavingThrowEffect)
    assert held.savingThrow.ability == AbilityType.WISDOM
    assert isinstance(armor, ApplyEffect) and isinstance(armor.effect, TemporaryHitPointsEffect)
    assert armor.effect.target == EffectTarget.SOURCE


def test_catalog_spell_effects_round_trip_through_typed_json() -> None:
    fireball = spell_entry(SpellId.FIREBALL)

    assert fireball is not None
    restored = typed_json_to_value(typed_json_from_value(fireball))
    assert restored == fireball
    assert restored.mechanics is not None
    effect = restored.mechanics.activatedEffects[0]
    assert isinstance(effect, SavingThrowEffect)
    assert isinstance(effect.onSuccess, ApplyEffect)
    assert isinstance(effect.onSuccess.effect, DamageEffect)
    assert effect.onSuccess.effect.multiplierDenominator == 2


def test_catalog_spell_effects_capture_representative_2024_mechanics() -> None:
    implemented = [spell for spell in spell_catalog().values() if spell.mechanics is not None]

    assert len(implemented) == 156
    assert all(spell.mechanics.activatedEffects or spell.mechanics.interactions for spell in implemented)
    assert all(typed_json_to_value(typed_json_from_value(spell.mechanics), type(spell.mechanics)) == spell.mechanics for spell in implemented)


def test_catalog_spell_effects_capture_verified_level_two_mechanics() -> None:
    implemented = [spell for spell in spell_catalog().values() if spell.level == 2 and spell.mechanics is not None]
    assert implemented
    assert all(spell.mechanics.activatedEffects for spell in implemented)


def test_catalog_spell_effects_capture_verified_level_three_mechanics() -> None:
    implemented = [spell for spell in spell_catalog().values() if spell.level == 3 and spell.mechanics is not None]
    assert implemented
    assert all(spell.mechanics.activatedEffects or spell.mechanics.interactions for spell in implemented)


def test_catalog_spell_effects_capture_verified_higher_level_mechanics() -> None:
    implemented = [spell for spell in spell_catalog().values() if spell.level >= 4 and spell.mechanics is not None]
    assert implemented
    assert all(spell.mechanics.activatedEffects for spell in implemented)


def test_catalog_spell_effects_capture_additional_level_zero_and_one_mechanics() -> None:
    implemented = [spell for spell in spell_catalog().values() if spell.level <= 1 and spell.mechanics is not None]
    assert implemented
    assert all(spell.mechanics.activatedEffects or spell.mechanics.interactions for spell in implemented)


def test_catalog_spell_mechanics_are_cloned() -> None:
    first = spell_entry(SpellId.FIRE_BOLT)
    second = spell_entry(SpellId.FIRE_BOLT)
    wizard = wizard_spell_entry(SpellId.FIRE_BOLT)

    assert first is not None and second is not None and wizard is not None
    assert first.mechanics is not None and second.mechanics is not None and wizard.mechanics is not None
    assert first.mechanics is not second.mechanics
    assert first.mechanics.activatedEffects is not second.mechanics.activatedEffects
    assert wizard.mechanics is not first.mechanics
