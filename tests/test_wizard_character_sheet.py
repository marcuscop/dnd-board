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
    SkillType,
    SpellId,
    SpellSource,
    SpellStatus,
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
    wizard_cantrip_count,
    wizard_cantrip_options,
    max_prepared_spell_level,
    wizard_prepared_spell_count,
    wizard_prepared_spell_options,
    wizard_catalog_spell,
    wizard_configured_spell_count,
    wizard_features,
    wizard_skill_proficiency_count,
    wizard_spellbook_spell_count,
    wizard_spellbook_spell_options,
    wizard_subclass_label,
)
from dnd_board.rules.shared.resources import RESOURCE_DEFINITIONS, ResourceId
from dnd_board.rules.progression import (
    ProgressionChoiceId,
    ProgressionGrantRecord,
    SpellCollection,
    SpellGrant,
    class_hit_die,
    progression_choices,
    prune_progression_choices,
)
from dnd_board.rules.species import SpeciesType
from dnd_board.rules.backgrounds import BackgroundType
from dnd_board.application.progression_service import (
    ProgressionServiceError,
    apply_member_progression_rule,
    set_member_class_levels,
)


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
    assert resources[enum_key(WizardResourceType.THIRD_LEVEL_SPELL_SLOTS)].recoveries == RESOURCE_DEFINITIONS[ResourceId.THIRD_LEVEL_SPELL_SLOTS].recoveries
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

    assert wizard_catalog_spell(SpellId.CURE_WOUNDS) is None
    assert SpellId.FIREBALL in {spell.id for spell in wizard_prepared_spell_options(5)}
    assert typed_json_to_value(typed_json_from_value(selected[0]), type(selected[0])) == selected[0]


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


def test_apply_wizard_subclass_progression_choice() -> None:
    member = PartyMemberConfig(
        id="wizard",
        name="Wizard",
        sheet=PartyMemberSheet(
            classes=[CharacterClassLevel(name=ClassType.WIZARD, level=3)],
        ),
    )

    apply_member_progression_rule(
        member,
        ProgressionChoiceId.WIZARD_SUBCLASS,
        ["illusionist"],
    )

    assert member.sheet.classes[0].subclass == WizardSubclassType.ILLUSIONIST


def test_wizard_defensive_progression_paths() -> None:
    low_level = prune_progression_choices([CharacterClassLevel(name=ClassType.WIZARD, level=2, subclass=WizardSubclassType.ABJURER)])[0]
    nonstandard = wizard_features([CharacterClassLevel(name=ClassType.WIZARD, level=3, subclass=ClassType.ROGUE)])
    complete_skills = progression_choices(
        [CharacterClassLevel(name=ClassType.WIZARD, level=1)],
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

    apply_member_progression_rule(member, ProgressionChoiceId.WIZARD_CANTRIPS, [enum_key(spell_id) for spell_id in cantrips])
    apply_member_progression_rule(member, ProgressionChoiceId.WIZARD_SPELLBOOK_SPELLS, [enum_key(spell_id) for spell_id in spellbook])
    apply_member_progression_rule(
        member,
        ProgressionChoiceId.WIZARD_PREPARED_SPELLS,
        [enum_key(spell_id) for spell_id in prepared],
    )

    assert member.sheet is not None
    assert [spell.id for spell in member.sheet.spellbook] == spellbook
    assert [spell.id for spell in member.sheet.spells if spell.level == 0] == cantrips
    assert [spell.id for spell in member.sheet.spells if spell.level > 0] == prepared


def test_wizard_prepared_spell_rule_rejects_spells_outside_the_spellbook() -> None:
    member = PartyMemberConfig(
        id="wizard",
        name="Merlin",
        sheet=PartyMemberSheet(classes=[CharacterClassLevel(name=ClassType.WIZARD, level=1)]),
    )
    spellbook = [SpellId.MAGIC_MISSILE, SpellId.SHIELD, SpellId.DETECT_MAGIC, SpellId.SLEEP, SpellId.FEATHER_FALL, SpellId.MAGE_ARMOR]
    apply_member_progression_rule(
        member,
        ProgressionChoiceId.WIZARD_SPELLBOOK_SPELLS,
        [enum_key(spell_id) for spell_id in spellbook],
    )

    try:
        apply_member_progression_rule(
            member,
            ProgressionChoiceId.WIZARD_PREPARED_SPELLS,
            [
                enum_key(SpellId.MAGIC_MISSILE),
                enum_key(SpellId.SHIELD),
                enum_key(SpellId.DETECT_MAGIC),
                enum_key(SpellId.THUNDERWAVE),
            ],
        )
    except ProgressionServiceError as error:
        assert error.detail == "Prepared Wizard spells must be legal spells from your spellbook"
    else:
        raise AssertionError("Expected a prepared spell outside the spellbook to be rejected")


def test_lazy_wizard_prepared_migration_preserves_existing_skills() -> None:
    level_one = CharacterClassLevel(name=ClassType.WIZARD, level=1)
    spellbook = wizard_spellbook_spell_options(1)[:wizard_spellbook_spell_count(level_one)]
    member = PartyMemberConfig(
        id="wizard",
        name="Merlin",
        sheet=PartyMemberSheet(
            classes=[level_one],
            skills={
                enum_key(SkillType.ARCANA): ProficiencyLevel.PROFICIENT,
                enum_key(SkillType.HISTORY): ProficiencyLevel.PROFICIENT,
            },
            spells=spellbook[:wizard_prepared_spell_count(level_one)],
            spellbook=spellbook,
        ),
    )

    set_member_class_levels(member, [CharacterClassLevel(name=ClassType.WIZARD, level=2)])

    assert member.sheet is not None
    assert member.sheet.baseSkills == {
        enum_key(SkillType.ARCANA): ProficiencyLevel.PROFICIENT,
        enum_key(SkillType.HISTORY): ProficiencyLevel.PROFICIENT,
    }
    assert member.sheet.skills == member.sheet.baseSkills


def test_wizard_skill_submission_migrates_and_preserves_prepared_spells() -> None:
    level_one = CharacterClassLevel(name=ClassType.WIZARD, level=1)
    spellbook = wizard_spellbook_spell_options(1)[:wizard_spellbook_spell_count(level_one)]
    prepared = spellbook[:wizard_prepared_spell_count(level_one)]
    member = PartyMemberConfig(
        id="wizard",
        name="Merlin",
        sheet=PartyMemberSheet(
            classes=[level_one],
            spells=prepared,
            spellbook=spellbook,
        ),
    )

    apply_member_progression_rule(
        member,
        ProgressionChoiceId.WIZARD_SKILL_PROFICIENCIES,
        [enum_key(SkillType.ARCANA), enum_key(SkillType.HISTORY)],
    )

    assert member.sheet is not None
    assert [
        spell.id
        for spell in member.sheet.spells or []
        if spell.source == SpellSource.WIZARD and spell.level > 0
    ] == [spell.id for spell in prepared]
    assert {
        record.source.rule
        for record in member.sheet.progressionGrants or []
    } == {
        ProgressionChoiceId.WIZARD_SKILL_PROFICIENCIES,
        ProgressionChoiceId.WIZARD_SPELLBOOK_SPELLS,
        ProgressionChoiceId.WIZARD_PREPARED_SPELLS,
    }


def test_wizard_prepared_grants_preserve_lineage_and_reconcile_to_destination_level() -> None:
    level_four = CharacterClassLevel(name=ClassType.WIZARD, level=4)
    spellbook = wizard_spellbook_spell_options(4)[:wizard_spellbook_spell_count(level_four)]
    prepared = spellbook[:wizard_prepared_spell_count(level_four)]
    initiate_copy = replace_spell_source(prepared[0], SpellSource.MAGIC_INITIATE)
    member = PartyMemberConfig(
        id="wizard",
        name="Merlin",
        sheet=PartyMemberSheet(
            classes=[level_four],
            spells=[initiate_copy],
            spellbook=spellbook,
        ),
    )
    apply_member_progression_rule(
        member,
        ProgressionChoiceId.WIZARD_PREPARED_SPELLS,
        [enum_key(spell.id) for spell in prepared],
    )

    assert member.sheet is not None
    assert len([spell for spell in member.sheet.spells if spell.id == prepared[0].id]) == 2
    prepared_record = next(
        record
        for record in member.sheet.progressionGrants or []
        if record.source.rule == ProgressionChoiceId.WIZARD_PREPARED_SPELLS
    )
    assert all(
        isinstance(grant, SpellGrant)
        and grant.destination == SpellCollection.PREPARED
        and grant.source == SpellSource.WIZARD
        for grant in prepared_record.grants
    )
    assert typed_json_to_value(
        typed_json_from_value(prepared_record),
        ProgressionGrantRecord,
    ) == prepared_record

    set_member_class_levels(member, [CharacterClassLevel(name=ClassType.WIZARD, level=3)])
    choices = progression_choices(
        member.sheet.classes,
        member.sheet.spells or [],
        member.sheet.skills or {},
        spellbook=member.sheet.spellbook,
        progression_grants=member.sheet.progressionGrants,
    )
    prepared_choice = next(
        choice
        for choice in choices
        if choice.id == ProgressionChoiceId.WIZARD_PREPARED_SPELLS.value
    )

    assert prepared_choice.minimum == wizard_prepared_spell_count(member.sheet.classes[0])
    assert len(prepared_choice.selected) == wizard_prepared_spell_count(level_four)
    assert len([spell for spell in member.sheet.spells or [] if spell.source == SpellSource.WIZARD and spell.level > 0]) == prepared_choice.minimum

    apply_member_progression_rule(
        member,
        ProgressionChoiceId.WIZARD_SKILL_PROFICIENCIES,
        [enum_key(SkillType.ARCANA), enum_key(SkillType.HISTORY)],
    )
    assert len([
        spell
        for spell in member.sheet.spells or []
        if spell.source == SpellSource.WIZARD and spell.level > 0
    ]) == prepared_choice.minimum
    retained_prepared_record = next(
        record
        for record in member.sheet.progressionGrants or []
        if record.source.rule == ProgressionChoiceId.WIZARD_PREPARED_SPELLS
    )
    assert len(retained_prepared_record.grants) == wizard_prepared_spell_count(level_four)

    apply_member_progression_rule(
        member,
        ProgressionChoiceId.WIZARD_PREPARED_SPELLS,
        prepared_choice.selected[:prepared_choice.minimum],
    )
    completed = progression_choices(
        member.sheet.classes,
        member.sheet.spells or [],
        member.sheet.skills or {},
        spellbook=member.sheet.spellbook,
        progression_grants=member.sheet.progressionGrants,
    )
    assert ProgressionChoiceId.WIZARD_PREPARED_SPELLS.value not in {choice.id for choice in completed}

    set_member_class_levels(member, [CharacterClassLevel(name=ClassType.ROGUE, level=3)])
    assert all(spell.source != SpellSource.WIZARD for spell in member.sheet.spells or [])
    assert initiate_copy in (member.sheet.spells or [])


def test_wizard_cantrip_and_spellbook_grants_track_acquisition_levels() -> None:
    level_one = CharacterClassLevel(name=ClassType.WIZARD, level=1)
    member = PartyMemberConfig(
        id="wizard",
        name="Merlin",
        sheet=PartyMemberSheet(classes=[level_one]),
    )
    level_one_cantrips = wizard_cantrip_options(1)[:wizard_cantrip_count(level_one)]
    level_one_spellbook = wizard_spellbook_spell_options(1)[:wizard_spellbook_spell_count(level_one)]
    apply_member_progression_rule(
        member,
        ProgressionChoiceId.WIZARD_CANTRIPS,
        [enum_key(spell.id) for spell in level_one_cantrips],
    )
    apply_member_progression_rule(
        member,
        ProgressionChoiceId.WIZARD_SPELLBOOK_SPELLS,
        [enum_key(spell.id) for spell in level_one_spellbook],
    )

    level_four = CharacterClassLevel(name=ClassType.WIZARD, level=4)
    set_member_class_levels(member, [level_four])
    level_four_cantrips = wizard_cantrip_options(4)[:wizard_cantrip_count(level_four)]
    level_four_spellbook = wizard_spellbook_spell_options(4)[:wizard_spellbook_spell_count(level_four)]
    apply_member_progression_rule(
        member,
        ProgressionChoiceId.WIZARD_CANTRIPS,
        [enum_key(spell.id) for spell in level_four_cantrips],
    )
    apply_member_progression_rule(
        member,
        ProgressionChoiceId.WIZARD_SPELLBOOK_SPELLS,
        [enum_key(spell.id) for spell in level_four_spellbook],
    )

    assert member.sheet is not None
    cantrip_record = next(
        record
        for record in member.sheet.progressionGrants or []
        if record.source.rule == ProgressionChoiceId.WIZARD_CANTRIPS
    )
    spellbook_record = next(
        record
        for record in member.sheet.progressionGrants or []
        if record.source.rule == ProgressionChoiceId.WIZARD_SPELLBOOK_SPELLS
    )
    assert [grant.minimumClassLevel for grant in cantrip_record.grants] == [1, 1, 1, 4]
    assert [grant.minimumClassLevel for grant in spellbook_record.grants] == [
        1, 1, 1, 1, 1, 1, 2, 2, 3, 3, 4, 4,
    ]

    level_three = CharacterClassLevel(name=ClassType.WIZARD, level=3)
    set_member_class_levels(member, [level_three])
    assert len([spell for spell in member.sheet.spells or [] if spell.source == SpellSource.WIZARD and spell.level == 0]) == 3
    assert len(member.sheet.spellbook or []) == 10

    set_member_class_levels(member, [level_four])
    choices = {
        choice.id: choice
        for choice in progression_choices(
            member.sheet.classes,
            member.sheet.spells or [],
            member.sheet.skills or {},
            spellbook=member.sheet.spellbook,
            progression_grants=member.sheet.progressionGrants,
        )
    }
    assert len(choices[ProgressionChoiceId.WIZARD_CANTRIPS.value].selected) == 3
    assert len(choices[ProgressionChoiceId.WIZARD_SPELLBOOK_SPELLS.value].selected) == 10


def test_character_builder_rejects_unsupported_class_directly() -> None:
    try:
        character_builder_request_from_payload({"className": "bard"}, default_member_id="player-1", default_owner="player-1")
    except ValueError as error:
        assert str(error) == "Choose Fighter, Rogue, or Wizard"
    else:
        raise AssertionError("Expected unsupported class to fail")


def replace_spell_source(spell, source: SpellSource):
    from dataclasses import replace

    return replace(spell, status=SpellStatus(source=source, castingAbility=spell.castingAbility, resourceId=spell.resourceId, reset=spell.reset))


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
