from dnd_board.character_sheet import (
    AbilityScores,
    AbilityType,
    CharacterClassLevel,
    ClassType,
    PartyMember,
    PartyMemberConfig,
    PartyMemberSheet,
    ProficiencyLevel,
    RestType,
    SpellId,
    SpellSource,
    TokenKind,
    build_character_sheet,
    enum_key,
    typed_json_from_value,
    typed_json_to_value,
)
from dnd_board.character_builder import CHARACTER_BUILDER_STARTING_LEVEL, character_builder_request_from_payload, fixed_max_hp
from dnd_board.rules.classes.wizard.archetypes import WizardSubclassResourceType
from dnd_board.rules.classes.wizard.base import (
    WizardResourceType,
    WizardProgression,
    WizardSubclassType,
    is_wizard_cantrip_selection_valid,
    is_wizard_prepared_spell_selection_valid,
    is_wizard_spellbook_selection_valid,
    wizard_cantrip_count,
    wizard_cantrip_options,
    wizard_cantrips,
    max_prepared_spell_level,
    wizard_prepared_spell_count,
    wizard_prepared_spell_options,
    wizard_prepared_spells,
    pruned_wizard_spellbook,
    pruned_wizard_spells,
    wizard_catalog_spell,
    wizard_configured_spell_count,
    wizard_features,
    wizard_skill_proficiency_count,
    wizard_spellbook_spell_count,
    wizard_spellbook_spell_options,
    wizard_spellbook_spells,
    wizard_subclass_label,
)
from dnd_board.rules.progression import ProgressionChoiceId, apply_progression_choice, class_hit_die, progression_choices, prune_progression_choices
from dnd_board.rules.species import SpeciesType
from dnd_board.rules.backgrounds import BackgroundType
from dnd_board.server import apply_member_wizard_cantrips, apply_member_wizard_prepared_spells, apply_member_wizard_spellbook_spells


def test_character_builder_supports_wizard_hit_die() -> None:
    scores = AbilityScores(8, 14, 15, 17, 10, 12)

    assert class_hit_die(ClassType.WIZARD) == 6
    assert fixed_max_hp(ClassType.WIZARD, CHARACTER_BUILDER_STARTING_LEVEL, scores, SpeciesType.HUMAN, BackgroundType.SAGE) == 8


def test_wizard_sheet_exposes_base_spellcasting_resources_and_saves() -> None:
    sheet = wizard_sheet(5)
    resources = {resource.id: resource for resource in sheet.resources}
    features = {feature.id: feature for feature in sheet.features}
    saves = {saving_throw.ability for saving_throw in sheet.savingThrows if saving_throw.proficient}

    assert enum_key(WizardResourceType.ARCANE_RECOVERY) in resources
    assert resources[enum_key(WizardResourceType.THIRD_LEVEL_SPELL_SLOTS)].maxUses == 2
    assert resources[enum_key(WizardResourceType.THIRD_LEVEL_SPELL_SLOTS)].reset == RestType.LONG_REST
    assert "spellcasting" in features
    assert "memorizeSpell" in features
    assert {AbilityType.INTELLIGENCE, AbilityType.WISDOM}.issubset(saves)


def test_wizard_progression_choices_include_skills_spells_and_subclass() -> None:
    sheet = wizard_sheet(3)
    choices = {choice.id: choice for choice in sheet.pendingChoices}
    spellbook = [
        wizard_catalog_spell(SpellId.MAGIC_MISSILE),
        wizard_catalog_spell(SpellId.SHIELD),
        wizard_catalog_spell(SpellId.DETECT_MAGIC),
        wizard_catalog_spell(SpellId.SLEEP),
        wizard_catalog_spell(SpellId.FEATHER_FALL),
        wizard_catalog_spell(SpellId.MAGE_ARMOR),
        wizard_catalog_spell(SpellId.THUNDERWAVE),
        wizard_catalog_spell(SpellId.CHARM_PERSON),
        wizard_catalog_spell(SpellId.INVISIBILITY),
        wizard_catalog_spell(SpellId.SCORCHING_RAY),
    ]
    choices_after_spellbook = {
        choice.id: choice
        for choice in progression_choices(
            sheet.classes,
            sheet.spells,
            [],
            [],
            {},
            spellbook=[spell for spell in spellbook if spell is not None],
        )
    }

    assert ProgressionChoiceId.WIZARD_SKILL_PROFICIENCIES.value in choices
    assert ProgressionChoiceId.WIZARD_CANTRIPS.value in choices
    assert ProgressionChoiceId.WIZARD_SPELLBOOK_SPELLS.value in choices
    assert ProgressionChoiceId.WIZARD_PREPARED_SPELLS.value not in choices
    assert ProgressionChoiceId.WIZARD_PREPARED_SPELLS.value in choices_after_spellbook
    assert ProgressionChoiceId.WIZARD_SUBCLASS.value in choices
    assert choices[ProgressionChoiceId.WIZARD_CANTRIPS.value].minimum == 3
    assert choices[ProgressionChoiceId.WIZARD_SPELLBOOK_SPELLS.value].minimum == 10
    assert choices_after_spellbook[ProgressionChoiceId.WIZARD_PREPARED_SPELLS.value].minimum == 6
    assert [option.value for option in choices_after_spellbook[ProgressionChoiceId.WIZARD_PREPARED_SPELLS.value].options] == [
        enum_key(spell.id) for spell in spellbook if spell is not None
    ]
    assert choices[ProgressionChoiceId.WIZARD_SUBCLASS.value].options[0].label == "Abjurer"
    assert any(option.label == "Chronurgy (Legacy)" for option in choices[ProgressionChoiceId.WIZARD_SUBCLASS.value].options)


def test_wizard_subclass_features_and_resources_are_source_labeled() -> None:
    abjurer = wizard_sheet(14, WizardSubclassType.ABJURER)
    diviner = wizard_sheet(14, WizardSubclassType.DIVINER)
    bladesinger = wizard_sheet(3, WizardSubclassType.BLADESINGER)
    illusionist = wizard_sheet(10, WizardSubclassType.ILLUSIONIST)
    legacy = wizard_sheet(3, WizardSubclassType.CHRONURGY)

    assert wizard_subclass_label(WizardSubclassType.BLADESINGER) == "Bladesinger"
    assert wizard_subclass_label(WizardSubclassType.CHRONURGY) == "Chronurgy (Legacy)"
    assert "abjurerSpellResistance" in {feature.id for feature in abjurer.features}
    assert enum_key(WizardSubclassResourceType.GREATER_PORTENT) in {resource.id for resource in diviner.resources}
    assert enum_key(WizardSubclassResourceType.BLADESONG) in {resource.id for resource in bladesinger.resources}
    assert enum_key(WizardSubclassResourceType.ILLUSORY_SELF) in {resource.id for resource in illusionist.resources}
    assert "chronurgyLegacySubclassFeature" in {feature.id for feature in legacy.features}


def test_wizard_spell_selection_uses_wizard_catalog_and_round_trips() -> None:
    spells = [
        wizard_catalog_spell(SpellId.MAGE_HAND),
        wizard_catalog_spell(SpellId.FIRE_BOLT),
        wizard_catalog_spell(SpellId.LIGHT),
        wizard_catalog_spell(SpellId.MAGIC_MISSILE),
        wizard_catalog_spell(SpellId.SHIELD),
        wizard_catalog_spell(SpellId.DETECT_MAGIC),
        wizard_catalog_spell(SpellId.SLEEP),
    ]
    assert all(spell is not None for spell in spells)
    selected = [spell for spell in spells if spell is not None]

    assert is_wizard_cantrip_selection_valid(1, selected[:3])
    assert is_wizard_prepared_spell_selection_valid(1, selected[3:])
    assert not is_wizard_cantrip_selection_valid(1, selected[:2])
    assert not is_wizard_prepared_spell_selection_valid(1, [*selected[3:], selected[3]])
    assert not is_wizard_spellbook_selection_valid(1, [replace_spell_source(spell, SpellSource.MAGIC_INITIATE) for spell in selected[3:]])
    assert wizard_catalog_spell(SpellId.CURE_WOUNDS) is None
    assert SpellId.FIREBALL in {spell.id for spell in wizard_prepared_spell_options(5)}
    assert typed_json_to_value(typed_json_from_value(selected[0]), type(selected[0])) == selected[0]
    assert pruned_wizard_spells(1, [*selected, wizard_catalog_spell(SpellId.FIREBALL)]) == selected


def test_wizard_split_spell_helpers_filter_counts_and_levels() -> None:
    level_one = CharacterClassLevel(name=ClassType.WIZARD, level=1)
    invalid = CharacterClassLevel(name=ClassType.WIZARD, level=0)
    spells = [
        wizard_catalog_spell(SpellId.MAGE_HAND),
        wizard_catalog_spell(SpellId.FIRE_BOLT),
        wizard_catalog_spell(SpellId.MAGIC_MISSILE),
    ]
    selected = [spell for spell in spells if spell is not None]

    assert wizard_cantrip_count(invalid) == 0
    assert wizard_cantrip_count(level_one) == 3
    assert wizard_prepared_spell_count(invalid) == 0
    assert wizard_prepared_spell_count(level_one) == 4
    assert wizard_spellbook_spell_count(invalid) == 0
    assert wizard_spellbook_spell_count(level_one) == 6
    assert wizard_configured_spell_count(level_one) == 7
    assert all(spell.level == 0 for spell in wizard_cantrip_options(1))
    assert all(spell.level > 0 for spell in wizard_prepared_spell_options(1))
    assert wizard_spellbook_spell_options(1) == wizard_prepared_spell_options(1)
    assert wizard_cantrips(selected) == selected[:2]
    assert wizard_prepared_spells(selected) == selected[2:]
    assert wizard_spellbook_spells(selected) == selected[2:]


def test_apply_wizard_subclass_progression_choice() -> None:
    classes = [CharacterClassLevel(name=ClassType.WIZARD, level=3)]

    updated = apply_progression_choice(classes, ProgressionChoiceId.WIZARD_SUBCLASS, ["illusionist"])

    assert updated[0].subclass == WizardSubclassType.ILLUSIONIST


def test_wizard_defensive_progression_paths() -> None:
    low_level = prune_progression_choices([CharacterClassLevel(name=ClassType.WIZARD, level=2, subclass=WizardSubclassType.ABJURER)])[0]
    nonstandard = wizard_features([CharacterClassLevel(name=ClassType.WIZARD, level=3, subclass=ClassType.ROGUE)])
    complete_skills = progression_choices(
        [CharacterClassLevel(name=ClassType.WIZARD, level=1)],
        [],
        [],
        [],
        {"arcana": ProficiencyLevel.PROFICIENT, "history": ProficiencyLevel.PROFICIENT},
    )
    complete_spells = progression_choices(
        [CharacterClassLevel(name=ClassType.WIZARD, level=1)],
        [
            wizard_catalog_spell(SpellId.MAGE_HAND),
            wizard_catalog_spell(SpellId.FIRE_BOLT),
            wizard_catalog_spell(SpellId.LIGHT),
            wizard_catalog_spell(SpellId.MAGIC_MISSILE),
            wizard_catalog_spell(SpellId.SHIELD),
            wizard_catalog_spell(SpellId.DETECT_MAGIC),
            wizard_catalog_spell(SpellId.SLEEP),
        ],
        [],
        [],
        {},
        spellbook=[
            wizard_catalog_spell(SpellId.MAGIC_MISSILE),
            wizard_catalog_spell(SpellId.SHIELD),
            wizard_catalog_spell(SpellId.DETECT_MAGIC),
            wizard_catalog_spell(SpellId.SLEEP),
            wizard_catalog_spell(SpellId.FEATHER_FALL),
            wizard_catalog_spell(SpellId.MAGE_ARMOR),
        ],
    )

    assert low_level.subclass is None
    assert wizard_configured_spell_count(CharacterClassLevel(name=ClassType.WIZARD, level=0)) == 0
    assert wizard_skill_proficiency_count(CharacterClassLevel(name=ClassType.WIZARD, level=0)) == 0
    assert max_prepared_spell_level(WizardProgression(0, 2, (), 0, 0, (0, 0, 0, 0, 0, 0, 0, 0, 0))) == 1
    assert "Rogue subclass features are included up to your Wizard level." in {feature.description for feature in nonstandard}
    assert ProgressionChoiceId.WIZARD_SKILL_PROFICIENCIES.value not in {choice.id for choice in complete_skills}
    assert ProgressionChoiceId.WIZARD_CANTRIPS.value not in {choice.id for choice in complete_spells}
    assert ProgressionChoiceId.WIZARD_SPELLBOOK_SPELLS.value not in {choice.id for choice in complete_spells}
    assert ProgressionChoiceId.WIZARD_PREPARED_SPELLS.value not in {choice.id for choice in complete_spells}


def test_wizard_cantrips_and_prepared_spells_apply_independently() -> None:
    member = PartyMemberConfig(
        id="wizard",
        name="Merlin",
        abilityScores=AbilityScores(8, 14, 14, 17, 12, 10),
        maxHp=8,
        sheet=PartyMemberSheet(classes=[CharacterClassLevel(name=ClassType.WIZARD, level=1)]),
    )
    cantrips = [SpellId.MAGE_HAND, SpellId.FIRE_BOLT, SpellId.LIGHT]
    spellbook = [SpellId.MAGIC_MISSILE, SpellId.SHIELD, SpellId.DETECT_MAGIC, SpellId.SLEEP, SpellId.FEATHER_FALL, SpellId.MAGE_ARMOR]
    prepared = spellbook[:4]

    apply_member_wizard_cantrips(member, [enum_key(spell_id) for spell_id in cantrips])
    apply_member_wizard_spellbook_spells(member, [enum_key(spell_id) for spell_id in spellbook])
    apply_member_wizard_prepared_spells(member, [enum_key(spell_id) for spell_id in prepared])

    assert member.sheet is not None
    assert [spell.id for spell in member.sheet.spellbook] == spellbook
    assert [spell.id for spell in member.sheet.spells if spell.level == 0] == cantrips
    assert [spell.id for spell in member.sheet.spells if spell.level > 0] == prepared
    assert pruned_wizard_spellbook(1, [*member.sheet.spellbook, wizard_catalog_spell(SpellId.FIREBALL)]) == member.sheet.spellbook


def test_character_builder_rejects_unsupported_class_directly() -> None:
    try:
        character_builder_request_from_payload({"className": "bard"}, default_member_id="player-1", default_owner="player-1")
    except ValueError as error:
        assert str(error) == "Choose Fighter, Rogue, or Wizard"
    else:
        raise AssertionError("Expected unsupported class to fail")


def replace_spell_source(spell, source: SpellSource):
    from dataclasses import replace

    return replace(spell, source=source)


def wizard_sheet(level: int, subclass: WizardSubclassType | None = None):
    return build_character_sheet(
        token_id="wizard",
        kind=TokenKind.CHARACTER,
        name="Merlin",
        owner="player-1",
        avatar_url=None,
        party_member=PartyMember(
            id="wizard",
            name="Merlin",
            owner="player-1",
            avatarUrl=None,
            abilityScores=AbilityScores(8, 14, 14, 17, 12, 10),
            maxHp=6 + 2 + max(0, level - 1) * 5,
            sheet=PartyMemberSheet(
                classes=[CharacterClassLevel(name=ClassType.WIZARD, level=level, subclass=subclass)],
                skills={},
            ),
        ),
        current_hp=None,
        resource_overrides={},
    )
