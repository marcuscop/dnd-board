from dataclasses import replace

import pytest

from dnd_board.application.progression_service import ProgressionServiceError, apply_member_progression_rule, member_feat_eligibility_sheet, set_member_class_levels
from dnd_board.character_sheet import AbilityScores, AbilityType, ArcaneShotType, AttackAction, BattleMasterManeuverType, CharacterClassLevel, ClassOptionKind, ClassOptionSelection, ClassType, DamageType, DiceType, EquipmentItem, EquipmentSlot, EquipmentType, FightingStyleType, PartyMember, PartyMemberConfig, PartyMemberSheet, ProficiencyLevel, ProgressionChoice, ProgressionChoiceType, RuneType, SkillType, SpellId, SpellSource, SpellStatus, TimeEconomy, TokenKind, build_attack_roll_payload, build_character_sheet, enum_key, typed_json_from_value, typed_json_to_value
from dnd_board.rules.classes.fighter.base import FighterSubclassType
from dnd_board.rules.classes.rogue.base import RogueSubclassType
from dnd_board.rules.classes.fighter.archetypes import normalized_eldritch_knight_spell
from dnd_board.rules.spells import spell_entry, wizard_spell_entry
from dnd_board.rules.progression import (
    AbilityScoreGrant,
    ClassOptionGrant,
    ClassOptionKind,
    FeatGrant,
    FightingStyleGrant,
    HitPointChoiceOption,
    HitPointGrant,
    ProgressionChoiceId,
    ProgressionGrantRecord,
    ProgressionGrantSource,
    ProgressionRuleViolation,
    SkillProficiencyGrant,
    SkillSelectionIssue,
    SpellCollection,
    SpellGrant,
    SpellLevelCategory,
    apply_ability_score_progression_grants,
    apply_progression_grants,
    class_hit_die,
    evaluate_progression_rule,
    parse_enum_values,
    parse_progression_choice_id,
    prune_progression_choices,
    progression_choices,
    progression_choice_for_rule,
    progression_rule,
    selected_enum_keys,
    level_advance_allowed,
    rogue_expertise_selection_issue,
    skill_proficiency_selection_issue,
    unique_values,
    update_class_level,
    saving_throw_proficiencies_from_grants,
    SavingThrowProficiencyGrant,
)
from dnd_board.rules.feats import GENERAL_FEATS, FeatCategory, GeneralFeatType, effective_weapon_training, feat_abilities
from dnd_board.rules.equipment import CLASS_WEAPON_TRAINING, MULTICLASS_WEAPON_TRAINING, WeaponTrainingCategory
from dnd_board.rules.feats import (
    feat_hit_point_bonus,
    feat_hit_point_bonus_per_level,
    feat_speed_bonus,
    general_feat_feature,
)
from dnd_board.rules.shared.tool_types import ToolType
from dnd_board.rules.shared.effects import AbilityScoreAdjustment
from dnd_board.rules.equipment import EquipmentId


def hp_record(
    class_type: ClassType,
    *grants: HitPointGrant,
) -> ProgressionGrantRecord:
    return ProgressionGrantRecord(
        ProgressionGrantSource(ProgressionChoiceId.HIT_POINT_INCREASE, class_type),
        grants,
    )


@pytest.mark.parametrize(
    ("selection", "strength", "dexterity"),
    [(["strength"], 18, 14), (["strength", "dexterity"], 17, 15)],
)
def test_ability_score_improvement_feat_uses_two_point_grants(selection, strength, dexterity) -> None:
    member = PartyMemberConfig(
        id="fighter", name="Fighter", maxHp=36,
        abilityScores=AbilityScores(16, 14, 14, 10, 10, 10),
        sheet=PartyMemberSheet(
            classes=[CharacterClassLevel(ClassType.FIGHTER, 4)],
            progressionGrants=[ProgressionGrantRecord(
                ProgressionGrantSource(ProgressionChoiceId.FIGHTER_ABILITY_SCORE_IMPROVEMENT, ClassType.FIGHTER),
                (FeatGrant(ClassType.FIGHTER, 4, GeneralFeatType.ABILITY_SCORE_IMPROVEMENT),),
            )],
        ),
    )

    apply_member_progression_rule(member, ProgressionChoiceId.FEAT_ABILITY_SCORE_INCREASE, selection)

    assert member.abilityScores.strength == strength
    assert member.abilityScores.dexterity == dexterity
    assert GENERAL_FEATS[GeneralFeatType.ABILITY_SCORE_IMPROVEMENT].repeatable
    set_member_class_levels(member, [CharacterClassLevel(ClassType.FIGHTER, 3)])
    assert member.abilityScores.strength == 16
    assert member.abilityScores.dexterity == 14


def test_skill_expert_grants_distinct_proficiency_and_expertise_choices() -> None:
    member = PartyMemberConfig(
        id="rogue", name="Rogue", maxHp=28,
        abilityScores=AbilityScores(10, 16, 12, 10, 10, 10),
        sheet=PartyMemberSheet(
            classes=[CharacterClassLevel(ClassType.ROGUE, 4)],
            baseSkills={enum_key(SkillType.ATHLETICS): ProficiencyLevel.PROFICIENT},
            progressionGrants=[ProgressionGrantRecord(
                ProgressionGrantSource(ProgressionChoiceId.ROGUE_ABILITY_SCORE_IMPROVEMENT, ClassType.ROGUE),
                (FeatGrant(ClassType.ROGUE, 4, GeneralFeatType.SKILL_EXPERT),),
            )],
        ),
    )

    apply_member_progression_rule(member, ProgressionChoiceId.FEAT_SKILL_TRAINING, [enum_key(SkillType.ARCANA)])
    expertise = progression_rule(
        ProgressionChoiceId.FEAT_EXPERTISE,
        member.sheet.classes,
        member.sheet.skills,
        member.sheet.progressionGrants,
    )
    assert expertise is not None
    assert SkillType.ARCANA in expertise.choices[0].candidates
    apply_member_progression_rule(member, ProgressionChoiceId.FEAT_EXPERTISE, [enum_key(SkillType.ARCANA)])
    apply_member_progression_rule(member, ProgressionChoiceId.FEAT_ABILITY_SCORE_INCREASE, ["dexterity"])
    assert member.sheet.skills[enum_key(SkillType.ARCANA)] == ProficiencyLevel.EXPERTISE
    assert member.abilityScores.dexterity == 17
    assert any(record.source.rule == ProgressionChoiceId.FEAT_EXPERTISE for record in member.sheet.progressionGrants)
    set_member_class_levels(member, [CharacterClassLevel(ClassType.ROGUE, 3)])
    assert member.sheet.skills.get(enum_key(SkillType.ARCANA), ProficiencyLevel.NONE) == ProficiencyLevel.NONE
    assert member.abilityScores.dexterity == 16


def test_sheet_serializes_skill_sources_without_cached_effective_skills() -> None:
    skill = enum_key(SkillType.STEALTH)
    sheet = PartyMemberSheet(
        baseSkills={skill: ProficiencyLevel.PROFICIENT},
        progressionGrants=[ProgressionGrantRecord(
            ProgressionGrantSource(ProgressionChoiceId.ROGUE_EXPERTISE, ClassType.ROGUE),
            (SkillProficiencyGrant(SkillType.STEALTH, ProficiencyLevel.EXPERTISE),),
        )],
    )

    encoded = typed_json_from_value(sheet)
    assert "skills" not in encoded["fields"]
    assert "baseSkills" in encoded["fields"]
    restored = typed_json_to_value(encoded, PartyMemberSheet)
    assert restored.skills[skill] == ProficiencyLevel.EXPERTISE
    restored.progressionGrants = []
    assert restored.skills[skill] == ProficiencyLevel.PROFICIENT


def test_martial_weapon_training_changes_catalog_weapon_attack_proficiency(monkeypatch) -> None:
    member = PartyMemberConfig(
        id="wizard", name="Wizard", maxHp=20,
        abilityScores=AbilityScores(15, 10, 10, 16, 10, 10),
        sheet=PartyMemberSheet(
            classes=[CharacterClassLevel(ClassType.WIZARD, 4)],
            equipment=[EquipmentItem(
                id="glaive", name="Glaive", definitionId=EquipmentId.GLAIVE,
                itemType=EquipmentType.WEAPON, slot=EquipmentSlot.TWO_HANDS,
            )],
            attacks=[AttackAction("glaive", "Glaive", AbilityType.STRENGTH, 1, DiceType.D10, damageType=DamageType.SLASHING)],
        ),
    )
    def sheet():
        return build_character_sheet(
            token_id=member.id, kind=TokenKind.CHARACTER, name=member.name, owner="player-1",
            avatar_url=None,
            party_member=PartyMember(member.id, member.name, "player-1", None, member.abilityScores, member.maxHp, member.sheet),
            current_hp=None, resource_overrides={},
        )

    monkeypatch.setattr("dnd_board.character_sheet.random.randint", lambda _minimum, _maximum: 10)
    before = sheet()
    assert not before.attacks[0].proficient
    before_roll = build_attack_roll_payload(before, "player-1", before.attacks[0])
    member.sheet.progressionGrants = [ProgressionGrantRecord(
        ProgressionGrantSource(ProgressionChoiceId.WIZARD_ABILITY_SCORE_IMPROVEMENT, ClassType.WIZARD),
        (FeatGrant(ClassType.WIZARD, 4, GeneralFeatType.MARTIAL_WEAPON_TRAINING),),
    )]
    apply_member_progression_rule(member, ProgressionChoiceId.FEAT_ABILITY_SCORE_INCREASE, ["strength"])
    after = sheet()
    after_roll = build_attack_roll_payload(after, "player-1", after.attacks[0])
    assert after.attacks[0].proficient
    assert after_roll.total - before_roll.total == 1 + after.proficiencyBonus
    assert "Martial weapons" in after.proficiencies
    set_member_class_levels(member, [CharacterClassLevel(ClassType.WIZARD, 3)])
    assert not sheet().attacks[0].proficient


@pytest.mark.parametrize(
    ("character_class", "weapon", "expected"),
    [
        (ClassType.FIGHTER, EquipmentId.GLAIVE, True),
        (ClassType.ROGUE, EquipmentId.GLAIVE, False),
        (ClassType.ROGUE, EquipmentId.HAND_CROSSBOW, True),
        (ClassType.WIZARD, EquipmentId.DAGGER, True),
        (ClassType.PALADIN, EquipmentId.GLAIVE, True),
        (ClassType.RANGER, EquipmentId.GLAIVE, True),
        (ClassType.BARD, EquipmentId.GLAIVE, False),
        (ClassType.CLERIC, EquipmentId.DAGGER, True),
        (ClassType.DRUID, EquipmentId.GLAIVE, False),
        (ClassType.SORCERER, EquipmentId.DAGGER, True),
        (ClassType.WARLOCK, EquipmentId.GLAIVE, False),
        (ClassType.ARTIFICER, EquipmentId.DAGGER, True),
        (ClassType.CREATURE, EquipmentId.GLAIVE, True),
    ],
)
def test_catalog_weapon_proficiency_uses_class_training(character_class, weapon, expected) -> None:
    definition = weapon.value
    member = PartyMemberConfig(
        id="attacker", name="Attacker", maxHp=20,
        sheet=PartyMemberSheet(
            classes=[CharacterClassLevel(character_class, 1)],
            equipment=[EquipmentItem(
                id=enum_key(weapon), name=definition, definitionId=weapon,
                itemType=EquipmentType.WEAPON, slot=EquipmentSlot.MAIN_HAND,
            )],
            attacks=[AttackAction(enum_key(weapon), definition, AbilityType.DEXTERITY, 1, DiceType.D6)],
        ),
    )
    sheet = build_character_sheet(
        token_id=member.id, kind=TokenKind.CHARACTER, name=member.name, owner="player-1",
        avatar_url=None,
        party_member=PartyMember(member.id, member.name, "player-1", None, member.abilityScores, member.maxHp, member.sheet),
        current_hp=None, resource_overrides={},
    )

    assert sheet.attacks[0].proficient is expected


def test_catalog_weapon_training_ignores_display_label_and_attack_default() -> None:
    member = PartyMemberConfig(
        id="wizard", name="Wizard", maxHp=12,
        sheet=PartyMemberSheet(
            classes=[CharacterClassLevel(ClassType.WIZARD, 1)],
            proficiencies=["Martial Weapon"],
            equipment=[EquipmentItem(
                id="glaive", name="Glaive", definitionId=EquipmentId.GLAIVE,
                itemType=EquipmentType.WEAPON, slot=EquipmentSlot.TWO_HANDS,
            )],
            attacks=[AttackAction("glaive", "Glaive", AbilityType.STRENGTH, 1, DiceType.D10)],
        ),
    )
    sheet = build_character_sheet(
        token_id=member.id, kind=TokenKind.CHARACTER, name=member.name, owner="player-1",
        avatar_url=None,
        party_member=PartyMember(member.id, member.name, "player-1", None, member.abilityScores, member.maxHp, member.sheet),
        current_hp=None, resource_overrides={},
    )

    assert sheet.attacks[0].proficient is False
    roll = build_attack_roll_payload(sheet, "player-1", sheet.attacks[0])
    assert all(part.source != "Proficiency" for part in roll.modifierBreakdown)


def test_every_declared_class_has_explicit_weapon_training() -> None:
    assert set(CLASS_WEAPON_TRAINING) == set(ClassType)
    assert set(MULTICLASS_WEAPON_TRAINING) == set(ClassType)


def test_multiclass_weapon_training_uses_multiclass_grants() -> None:
    wizard_rogue = effective_weapon_training(
        [CharacterClassLevel(ClassType.WIZARD, 1), CharacterClassLevel(ClassType.ROGUE, 1)],
        [],
    )
    wizard_fighter = effective_weapon_training(
        [CharacterClassLevel(ClassType.WIZARD, 1), CharacterClassLevel(ClassType.FIGHTER, 1)],
        [],
    )

    assert wizard_rogue.categories == (WeaponTrainingCategory.SIMPLE,)
    assert not wizard_rogue.martialPropertiesAny
    assert wizard_fighter.categories == (WeaponTrainingCategory.SIMPLE, WeaponTrainingCategory.MARTIAL)


def test_hit_dice_are_explicit_for_supported_and_catalog_only_classes() -> None:
    assert class_hit_die(ClassType.FIGHTER) == 10
    assert class_hit_die(ClassType.ROGUE) == 8
    assert class_hit_die(ClassType.WIZARD) == 6
    assert class_hit_die(ClassType.CLERIC) == 8
    assert class_hit_die(ClassType.PALADIN) == 10
    assert class_hit_die(ClassType.SORCERER) == 6


def test_ability_score_progression_records_typed_grants_and_advances_entitlement() -> None:
    classes = [CharacterClassLevel(name=ClassType.FIGHTER, level=6)]
    first_rule = progression_rule(
        ProgressionChoiceId.FIGHTER_ABILITY_SCORE_IMPROVEMENT,
        classes,
        {},
    )
    assert first_rule is not None

    result = evaluate_progression_rule(
        first_rule,
        classes,
        {},
        ["strength", "dexterity"],
        ability_scores=AbilityScores(16, 14, 12, 10, 10, 8),
    )
    record = ProgressionGrantRecord(result.source, result.grants)

    assert result.grants == (
        AbilityScoreGrant(ClassType.FIGHTER, 4, AbilityScoreAdjustment(AbilityType.STRENGTH, 1, maximum=20)),
        AbilityScoreGrant(ClassType.FIGHTER, 4, AbilityScoreAdjustment(AbilityType.DEXTERITY, 1, maximum=20)),
    )
    assert apply_ability_score_progression_grants(
        AbilityScores(16, 14, 12, 10, 10, 8),
        [record],
    ) == AbilityScores(17, 15, 12, 10, 10, 8)

    next_rule = progression_rule(
        ProgressionChoiceId.FIGHTER_ABILITY_SCORE_IMPROVEMENT,
        classes,
        {},
        [record],
    )
    assert next_rule is not None
    assert next_rule.choices[0].classLevel == 6


def test_defensive_duelist_grants_a_definition_backed_dexterity_choice() -> None:
    classes = [CharacterClassLevel(name=ClassType.FIGHTER, level=4)]
    feat_record = ProgressionGrantRecord(
        ProgressionGrantSource(
            ProgressionChoiceId.FIGHTER_ABILITY_SCORE_IMPROVEMENT,
            ClassType.FIGHTER,
        ),
        (FeatGrant(ClassType.FIGHTER, 4, GeneralFeatType.DEFENSIVE_DUELIST),),
    )

    choices = progression_choices(
        classes,
        [],
        {},
        progression_grants=[feat_record],
    )
    feat_ability_choice = next(
        choice
        for choice in choices
        if choice.id == ProgressionChoiceId.FEAT_ABILITY_SCORE_INCREASE.value
    )
    rule = progression_rule(
        ProgressionChoiceId.FEAT_ABILITY_SCORE_INCREASE,
        classes,
        {},
        [feat_record],
    )

    assert feat_ability_choice.choiceType == ProgressionChoiceType.FEAT_ABILITY_SCORE_INCREASE
    assert [(option.value, option.label) for option in feat_ability_choice.options] == [
        ("dexterity", "Dexterity"),
    ]
    assert rule is not None
    result = evaluate_progression_rule(
        rule,
        classes,
        {},
        ["dexterity"],
        ability_scores=AbilityScores(10, 19, 10, 10, 10, 10),
    )
    assert result.source.requiredFeat == GeneralFeatType.DEFENSIVE_DUELIST
    assert result.grants == (
        AbilityScoreGrant(ClassType.FIGHTER, 4, AbilityScoreAdjustment(AbilityType.DEXTERITY, 1, maximum=20)),
    )


def test_resilient_choices_grant_only_a_new_saving_throw_proficiency() -> None:
    feat_record = ProgressionGrantRecord(
        ProgressionGrantSource(
            ProgressionChoiceId.FIGHTER_ABILITY_SCORE_IMPROVEMENT,
            ClassType.FIGHTER,
        ),
        (FeatGrant(ClassType.FIGHTER, 4, GeneralFeatType.RESILIENT),),
    )
    member = PartyMemberConfig(
        id="fighter",
        name="Fighter",
        maxHp=36,
        abilityScores=AbilityScores(16, 14, 14, 10, 10, 10),
        sheet=PartyMemberSheet(
            classes=[CharacterClassLevel(name=ClassType.FIGHTER, level=4)],
            progressionGrants=[feat_record],
        ),
    )
    eligibility = member_feat_eligibility_sheet(member)
    choices = progression_choices(
        member.sheet.classes,
        [],
        {},
        [general_feat_feature(enum_key(GeneralFeatType.RESILIENT))],
        eligibility,
        progression_grants=[feat_record],
    )
    resilient_choice = next(choice for choice in choices if choice.id == ProgressionChoiceId.FEAT_ABILITY_SCORE_INCREASE.value)
    assert {option.value for option in resilient_choice.options} == {
        "dexterity", "intelligence", "wisdom", "charisma",
    }
    with pytest.raises(ProgressionServiceError):
        apply_member_progression_rule(member, ProgressionChoiceId.FEAT_ABILITY_SCORE_INCREASE, ["constitution"])

    apply_member_progression_rule(member, ProgressionChoiceId.FEAT_ABILITY_SCORE_INCREASE, ["wisdom"])
    assert member.abilityScores.wisdom == 11
    assert AbilityType.WISDOM in saving_throw_proficiencies_from_grants(member.sheet.progressionGrants)
    sheet = build_character_sheet(
        token_id=member.id,
        kind=TokenKind.CHARACTER,
        name=member.name,
        owner="player-1",
        avatar_url=None,
        party_member=PartyMember(member.id, member.name, "player-1", None, member.abilityScores, member.maxHp, member.sheet),
        current_hp=None,
        resource_overrides={},
    )
    assert next(save for save in sheet.savingThrows if save.ability == AbilityType.WISDOM).proficient
    assert any(
        isinstance(grant, SavingThrowProficiencyGrant) and grant.ability == AbilityType.WISDOM
        for record in member.sheet.progressionGrants
        for grant in record.grants
    )

    set_member_class_levels(member, [CharacterClassLevel(name=ClassType.FIGHTER, level=3)])
    assert member.abilityScores.wisdom == 10
    assert AbilityType.WISDOM not in saving_throw_proficiencies_from_grants(member.sheet.progressionGrants)


def test_resilient_still_grants_save_proficiency_at_ability_score_cap() -> None:
    feat_record = ProgressionGrantRecord(
        ProgressionGrantSource(ProgressionChoiceId.FIGHTER_ABILITY_SCORE_IMPROVEMENT, ClassType.FIGHTER),
        (FeatGrant(ClassType.FIGHTER, 4, GeneralFeatType.RESILIENT),),
    )
    member = PartyMemberConfig(
        id="fighter",
        name="Fighter",
        maxHp=36,
        abilityScores=AbilityScores(16, 14, 14, 10, 20, 10),
        sheet=PartyMemberSheet(
            classes=[CharacterClassLevel(ClassType.FIGHTER, 4)],
            progressionGrants=[feat_record],
        ),
    )
    apply_member_progression_rule(member, ProgressionChoiceId.FEAT_ABILITY_SCORE_INCREASE, ["wisdom"])
    assert member.abilityScores.wisdom == 20
    assert AbilityType.WISDOM in saving_throw_proficiencies_from_grants(member.sheet.progressionGrants)


def test_war_caster_ability_choice_enforces_candidates_and_score_cap() -> None:
    classes = [CharacterClassLevel(name=ClassType.WIZARD, level=4)]
    feat_record = ProgressionGrantRecord(
        ProgressionGrantSource(
            ProgressionChoiceId.WIZARD_ABILITY_SCORE_IMPROVEMENT,
            ClassType.WIZARD,
        ),
        (FeatGrant(ClassType.WIZARD, 4, GeneralFeatType.WAR_CASTER),),
    )
    rule = progression_rule(
        ProgressionChoiceId.FEAT_ABILITY_SCORE_INCREASE,
        classes,
        {},
        [feat_record],
    )

    assert rule is not None
    choice = rule.choices[0]
    assert choice.adjustment.candidates == (
        AbilityType.INTELLIGENCE,
        AbilityType.WISDOM,
        AbilityType.CHARISMA,
    )
    with pytest.raises(ProgressionRuleViolation) as invalid_ability:
        evaluate_progression_rule(
            rule,
            classes,
            {},
            ["dexterity"],
            ability_scores=AbilityScores(10, 10, 10, 18, 12, 14),
        )
    with pytest.raises(ProgressionRuleViolation) as capped_score:
        evaluate_progression_rule(
            rule,
            classes,
            {},
            ["intelligence"],
            ability_scores=AbilityScores(10, 10, 10, 20, 12, 14),
        )

    assert invalid_ability.value.issue == SkillSelectionIssue.INVALID_OPTION
    assert capped_score.value.issue == SkillSelectionIssue.INVALID_OPTION


def test_feat_ability_score_grant_is_applied_and_removed_with_its_feat() -> None:
    feat_record = ProgressionGrantRecord(
        ProgressionGrantSource(
            ProgressionChoiceId.FIGHTER_ABILITY_SCORE_IMPROVEMENT,
            ClassType.FIGHTER,
        ),
        (FeatGrant(ClassType.FIGHTER, 4, GeneralFeatType.DEFENSIVE_DUELIST),),
    )
    member = PartyMemberConfig(
        id="fighter",
        name="Fighter",
        maxHp=36,
        abilityScores=AbilityScores(16, 14, 14, 10, 10, 10),
        sheet=PartyMemberSheet(
            classes=[CharacterClassLevel(name=ClassType.FIGHTER, level=4)],
            progressionGrants=[feat_record],
        ),
    )

    apply_member_progression_rule(
        member,
        ProgressionChoiceId.FEAT_ABILITY_SCORE_INCREASE,
        ["dexterity"],
    )

    assert member.abilityScores.dexterity == 15
    feat_ability_record = next(
        record
        for record in member.sheet.progressionGrants
        if record.source.rule == ProgressionChoiceId.FEAT_ABILITY_SCORE_INCREASE
    )
    assert feat_ability_record.source.requiredFeat == GeneralFeatType.DEFENSIVE_DUELIST
    assert typed_json_to_value(typed_json_from_value(feat_ability_record)) == feat_ability_record

    set_member_class_levels(
        member,
        [CharacterClassLevel(name=ClassType.FIGHTER, level=3)],
    )

    assert member.abilityScores.dexterity == 14
    assert all(
        record.source.requiredFeat != GeneralFeatType.DEFENSIVE_DUELIST
        for record in member.sheet.progressionGrants or []
    )


@pytest.mark.parametrize(
    ("feat", "skill", "trained", "expected"),
    [
        (GeneralFeatType.KEEN_MIND, SkillType.ARCANA, False, ProficiencyLevel.PROFICIENT),
        (GeneralFeatType.KEEN_MIND, SkillType.HISTORY, True, ProficiencyLevel.EXPERTISE),
        (GeneralFeatType.OBSERVANT, SkillType.PERCEPTION, False, ProficiencyLevel.PROFICIENT),
        (GeneralFeatType.OBSERVANT, SkillType.INSIGHT, True, ProficiencyLevel.EXPERTISE),
    ],
)
def test_feat_skill_choice_grants_and_reconciles(
    feat: GeneralFeatType,
    skill: SkillType,
    trained: bool,
    expected: ProficiencyLevel,
) -> None:
    feat_record = ProgressionGrantRecord(
        ProgressionGrantSource(ProgressionChoiceId.WIZARD_ABILITY_SCORE_IMPROVEMENT, ClassType.WIZARD),
        (FeatGrant(ClassType.WIZARD, 4, feat),),
    )
    base_skills = {enum_key(skill): ProficiencyLevel.PROFICIENT} if trained else {}
    member = PartyMemberConfig(
        id="wizard",
        name="Wizard",
        maxHp=24,
        abilityScores=AbilityScores(10, 10, 10, 16, 14, 10),
        sheet=PartyMemberSheet(
            classes=[CharacterClassLevel(ClassType.WIZARD, 4)],
            baseSkills=dict(base_skills),
            progressionGrants=[feat_record],
        ),
    )
    choices = progression_choices(
        member.sheet.classes, [], member.sheet.skills,
        progression_grants=member.sheet.progressionGrants,
    )
    choice = next(choice for choice in choices if choice.id == ProgressionChoiceId.FEAT_SKILL_TRAINING.value)
    assert enum_key(skill) in {option.value for option in choice.options}

    apply_member_progression_rule(member, ProgressionChoiceId.FEAT_SKILL_TRAINING, [enum_key(skill)])
    assert member.sheet.skills[enum_key(skill)] == expected
    grant_record = next(
        record for record in member.sheet.progressionGrants
        if record.source.rule == ProgressionChoiceId.FEAT_SKILL_TRAINING
    )
    assert grant_record.source.requiredFeat == feat
    assert typed_json_to_value(typed_json_from_value(grant_record)) == grant_record

    set_member_class_levels(member, [CharacterClassLevel(ClassType.WIZARD, 3)])
    assert (member.sheet.skills or {}).get(enum_key(skill), ProficiencyLevel.NONE) == base_skills.get(
        enum_key(skill), ProficiencyLevel.NONE
    )
    assert not any(
        record.source.requiredFeat == feat for record in member.sheet.progressionGrants or []
    )


def test_feat_skill_selection_does_not_reuse_another_feats_record() -> None:
    classes = [CharacterClassLevel(ClassType.WIZARD, 8)]
    feat_records = [
        ProgressionGrantRecord(
            ProgressionGrantSource(ProgressionChoiceId.WIZARD_ABILITY_SCORE_IMPROVEMENT, ClassType.WIZARD),
            (
                FeatGrant(ClassType.WIZARD, 4, GeneralFeatType.KEEN_MIND),
                FeatGrant(ClassType.WIZARD, 8, GeneralFeatType.OBSERVANT),
            ),
        ),
    ]
    first = progression_rule(ProgressionChoiceId.FEAT_SKILL_TRAINING, classes, {}, feat_records)
    assert first is not None and first.sourceFeat == GeneralFeatType.KEEN_MIND
    result = evaluate_progression_rule(first, classes, {}, [enum_key(SkillType.ARCANA)])
    feat_records.append(ProgressionGrantRecord(result.source, result.grants))
    second = progression_rule(ProgressionChoiceId.FEAT_SKILL_TRAINING, classes, {}, feat_records)
    assert second is not None and second.sourceFeat == GeneralFeatType.OBSERVANT
    choice = progression_choice_for_rule(second, {}, feat_records, classes=classes)
    assert choice is not None and choice.selected == []


def test_feat_skill_upgrade_recomputes_when_other_proficiency_disappears() -> None:
    skill = SkillType.INVESTIGATION
    primary = ProgressionGrantRecord(
        ProgressionGrantSource(ProgressionChoiceId.FEAT_SKILL_TRAINING, ClassType.WIZARD),
        (SkillProficiencyGrant(skill, ProficiencyLevel.PROFICIENT, promoteExistingProficiency=True),),
    )
    other = ProgressionGrantRecord(
        ProgressionGrantSource(ProgressionChoiceId.WIZARD_SKILL_PROFICIENCIES, ClassType.WIZARD),
        (SkillProficiencyGrant(skill, ProficiencyLevel.PROFICIENT),),
    )
    assert apply_progression_grants({}, [primary, other])[enum_key(skill)] == ProficiencyLevel.EXPERTISE
    assert apply_progression_grants({}, [primary])[enum_key(skill)] == ProficiencyLevel.PROFICIENT


@pytest.mark.parametrize(
    ("feat", "expected_abilities", "action_id"),
    [
        (GeneralFeatType.KEEN_MIND, {"intelligence"}, "keenMindQuickStudy"),
        (GeneralFeatType.OBSERVANT, {"intelligence", "wisdom"}, "observantQuickSearch"),
    ],
)
def test_keen_mind_and_observant_definition_choices_and_action_metadata(
    feat: GeneralFeatType,
    expected_abilities: set[str],
    action_id: str,
) -> None:
    classes = [CharacterClassLevel(ClassType.WIZARD, 4)]
    record = ProgressionGrantRecord(
        ProgressionGrantSource(ProgressionChoiceId.WIZARD_ABILITY_SCORE_IMPROVEMENT, ClassType.WIZARD),
        (FeatGrant(ClassType.WIZARD, 4, feat),),
    )
    choice = next(
        choice for choice in progression_choices(classes, [], {}, progression_grants=[record])
        if choice.id == ProgressionChoiceId.FEAT_ABILITY_SCORE_INCREASE.value
    )
    assert {option.value for option in choice.options} == expected_abilities
    action = next(
        ability for ability in feat_abilities(classes, [general_feat_feature(enum_key(feat))])
        if ability.id == action_id
    )
    assert action.activation == TimeEconomy.BONUS_ACTION


def test_skilled_mixed_training_is_typed_and_removed_with_feat() -> None:
    feat_record = ProgressionGrantRecord(
        ProgressionGrantSource(ProgressionChoiceId.FIGHTER_ABILITY_SCORE_IMPROVEMENT, ClassType.FIGHTER),
        (FeatGrant(ClassType.FIGHTER, 4, GeneralFeatType.SKILLED),),
    )
    member = PartyMemberConfig(
        id="fighter",
        name="Fighter",
        maxHp=36,
        abilityScores=AbilityScores(16, 14, 14, 10, 10, 10),
        sheet=PartyMemberSheet(
            classes=[CharacterClassLevel(ClassType.FIGHTER, 4)],
            progressionGrants=[feat_record],
        ),
    )
    selections = [enum_key(SkillType.ARCANA), enum_key(ToolType.LUTE), enum_key(ToolType.THIEVES_TOOLS)]
    rule = progression_rule(ProgressionChoiceId.FEAT_TRAINING, member.sheet.classes, {}, [feat_record])
    assert rule is not None
    with pytest.raises(ProgressionRuleViolation):
        evaluate_progression_rule(rule, member.sheet.classes, {}, selections[:2] + selections[:1])
    with pytest.raises(ProgressionRuleViolation):
        evaluate_progression_rule(rule, member.sheet.classes, {}, selections[:2] + [enum_key(ToolType.MUSICAL_INSTRUMENT)])
    apply_member_progression_rule(member, ProgressionChoiceId.FEAT_TRAINING, selections)
    assert member.sheet.skills[enum_key(SkillType.ARCANA)] == ProficiencyLevel.PROFICIENT
    training = next(
        record for record in member.sheet.progressionGrants
        if record.source.rule == ProgressionChoiceId.FEAT_TRAINING
    )
    assert typed_json_to_value(typed_json_from_value(training)) == training
    sheet = build_character_sheet(
        token_id=member.id,
        kind=TokenKind.CHARACTER,
        name=member.name,
        owner="player-1",
        avatar_url=None,
        party_member=PartyMember(member.id, member.name, "player-1", None, member.abilityScores, member.maxHp, member.sheet),
        current_hp=None,
        resource_overrides={},
    )
    assert "Lute" in sheet.proficiencies
    assert "Thieves' Tools" in sheet.proficiencies
    set_member_class_levels(member, [CharacterClassLevel(ClassType.FIGHTER, 3)])
    assert not any(record.source.rule == ProgressionChoiceId.FEAT_TRAINING for record in member.sheet.progressionGrants or [])
    assert enum_key(SkillType.ARCANA) not in (member.sheet.skills or {})


def test_repeatable_skilled_training_is_owned_by_each_acquisition() -> None:
    classes = [CharacterClassLevel(ClassType.FIGHTER, 6)]
    records = [ProgressionGrantRecord(
        ProgressionGrantSource(ProgressionChoiceId.FIGHTER_ABILITY_SCORE_IMPROVEMENT, ClassType.FIGHTER),
        (
            FeatGrant(ClassType.FIGHTER, 4, GeneralFeatType.SKILLED),
            FeatGrant(ClassType.FIGHTER, 6, GeneralFeatType.SKILLED),
        ),
    )]
    first = progression_rule(ProgressionChoiceId.FEAT_TRAINING, classes, {}, records)
    assert first is not None and first.sourceFeatLevel == 4
    assert progression_choice_for_rule(first, {}, records, classes=classes).sourceLevel == 4
    first_result = evaluate_progression_rule(first, classes, {}, [enum_key(SkillType.ARCANA), enum_key(ToolType.LUTE), enum_key(ToolType.THIEVES_TOOLS)])
    records.append(ProgressionGrantRecord(first_result.source, first_result.grants))
    second = progression_rule(ProgressionChoiceId.FEAT_TRAINING, classes, {}, records)
    assert second is not None and second.sourceFeatLevel == 6
    assert progression_choice_for_rule(second, {}, records, classes=classes).sourceLevel == 6
    second_result = evaluate_progression_rule(second, classes, {}, [enum_key(SkillType.HISTORY), enum_key(ToolType.FLUTE), enum_key(ToolType.HERBALISM_KIT)])
    records.append(ProgressionGrantRecord(second_result.source, second_result.grants))
    assert len([record for record in records if record.source.rule == ProgressionChoiceId.FEAT_TRAINING]) == 2
    assert progression_rule(ProgressionChoiceId.FEAT_TRAINING, classes, {}, records) is None
    assert typed_json_to_value(typed_json_from_value(records[-1])) == records[-1]


def test_musician_training_accepts_only_distinct_instruments() -> None:
    classes = [CharacterClassLevel(ClassType.ROGUE, 1)]
    records = [ProgressionGrantRecord(
        ProgressionGrantSource(ProgressionChoiceId.BACKGROUND_FEAT, ClassType.ROGUE),
        (FeatGrant(ClassType.ROGUE, 1, GeneralFeatType.MUSICIAN),),
    )]
    rule = progression_rule(ProgressionChoiceId.FEAT_TRAINING, classes, {}, records)
    assert rule is not None
    assert {option.value for option in progression_choice_for_rule(rule, {}, records, classes=classes).options} == {
        enum_key(tool) for tool in GENERAL_FEATS[GeneralFeatType.MUSICIAN].trainingChoice.tools
    }
    with pytest.raises(ProgressionRuleViolation):
        evaluate_progression_rule(rule, classes, {}, [enum_key(ToolType.LUTE), enum_key(ToolType.FLUTE), enum_key(SkillType.ARCANA)])
    result = evaluate_progression_rule(rule, classes, {}, [enum_key(ToolType.LUTE), enum_key(ToolType.FLUTE), enum_key(ToolType.DRUM)])
    assert len(result.grants) == 3


def test_ability_score_progression_can_grant_a_typed_feat() -> None:
    classes = [CharacterClassLevel(name=ClassType.ROGUE, level=4)]
    rule = progression_rule(
        ProgressionChoiceId.ROGUE_ABILITY_SCORE_IMPROVEMENT,
        classes,
        {},
    )
    assert rule is not None

    result = evaluate_progression_rule(
        rule,
        classes,
        {},
        ["feat:actor"],
        ability_scores=AbilityScores(10, 16, 12, 10, 12, 10),
    )

    assert result.grants == (
        FeatGrant(ClassType.ROGUE, 4, GeneralFeatType.ACTOR),
    )
    assert typed_json_to_value(typed_json_from_value(result.grants[0])) == result.grants[0]


def test_level_nineteen_uses_epic_boon_progression_instead_of_asi() -> None:
    classes = [CharacterClassLevel(name=ClassType.WIZARD, level=19)]

    assert progression_rule(
        ProgressionChoiceId.WIZARD_ABILITY_SCORE_IMPROVEMENT,
        classes,
        {},
    ) is not None
    completed_asi_records = [ProgressionGrantRecord(
        ProgressionGrantSource(
            ProgressionChoiceId.WIZARD_ABILITY_SCORE_IMPROVEMENT,
            ClassType.WIZARD,
        ),
        tuple(
            AbilityScoreGrant(ClassType.WIZARD, level, AbilityScoreAdjustment(AbilityType.INTELLIGENCE, 1, maximum=20))
            for level in (4, 8, 12, 16)
        ),
    )]
    assert progression_rule(
        ProgressionChoiceId.WIZARD_ABILITY_SCORE_IMPROVEMENT,
        classes,
        {},
        completed_asi_records,
    ) is None

    epic_rule = progression_rule(
        ProgressionChoiceId.WIZARD_EPIC_BOON,
        classes,
        {},
        completed_asi_records,
    )
    assert epic_rule is not None
    assert epic_rule.choices[0].categories == (
        FeatCategory.EPIC_BOON,
        FeatCategory.GENERAL,
    )
    epic = evaluate_progression_rule(
        epic_rule,
        classes,
        {},
        ["boonOfFortitude"],
    )
    assert epic.grants == (
        FeatGrant(ClassType.WIZARD, 19, GeneralFeatType.BOON_OF_FORTITUDE),
    )


def test_fighting_style_progression_uses_typed_feat_grants() -> None:
    classes = [CharacterClassLevel(name=ClassType.FIGHTER, level=1)]
    rule = progression_rule(
        ProgressionChoiceId.FIGHTER_FIGHTING_STYLES,
        classes,
        {},
    )
    assert rule is not None

    result = evaluate_progression_rule(
        rule,
        classes,
        {},
        ["defense"],
    )

    assert result.grants == (
        FightingStyleGrant(ClassType.FIGHTER, 1, FightingStyleType.DEFENSE),
    )


def test_epic_boon_grant_is_removed_and_reoffered_after_level_down() -> None:
    member = PartyMemberConfig(
        id="wizard",
        name="Wizard",
        abilityScores=AbilityScores(10, 14, 14, 20, 12, 10),
        sheet=PartyMemberSheet(
            classes=[CharacterClassLevel(name=ClassType.WIZARD, level=19)],
        ),
    )

    apply_member_progression_rule(
        member,
        ProgressionChoiceId.WIZARD_EPIC_BOON,
        ["boonOfFortitude"],
    )
    assert {feat.id for feat in member.sheet.feats or []} == {"boonOfFortitude"}

    set_member_class_levels(
        member,
        [CharacterClassLevel(name=ClassType.WIZARD, level=18)],
    )
    assert member.sheet.feats is None
    set_member_class_levels(
        member,
        [CharacterClassLevel(name=ClassType.WIZARD, level=19)],
    )
    assert progression_rule(
        ProgressionChoiceId.WIZARD_EPIC_BOON,
        member.sheet.classes,
        {},
        member.sheet.progressionGrants,
    ) is not None


def test_bonus_fighting_style_is_reconciled_by_acquisition_level() -> None:
    member = PartyMemberConfig(
        id="champion",
        name="Champion",
        sheet=PartyMemberSheet(classes=[CharacterClassLevel(
            name=ClassType.FIGHTER,
            level=7,
            subclass=FighterSubclassType.CHAMPION,
            fightingStyles=[FightingStyleType.DEFENSE],
        )]),
    )

    apply_member_progression_rule(
        member,
        ProgressionChoiceId.FIGHTER_FIGHTING_STYLES,
        ["dueling"],
    )
    assert member.sheet.classes[0].fightingStyles == [
        FightingStyleType.DEFENSE,
        FightingStyleType.DUELING,
    ]

    set_member_class_levels(member, [replace(member.sheet.classes[0], level=6)])
    assert member.sheet.classes[0].fightingStyles == [FightingStyleType.DEFENSE]


def test_subclass_fighting_style_is_removed_after_subclass_change() -> None:
    member = PartyMemberConfig(
        id="champion",
        name="Champion",
        sheet=PartyMemberSheet(classes=[CharacterClassLevel(
            name=ClassType.FIGHTER,
            level=7,
            subclass=FighterSubclassType.CHAMPION,
            fightingStyles=[FightingStyleType.DEFENSE],
        )]),
    )
    apply_member_progression_rule(
        member,
        ProgressionChoiceId.FIGHTER_FIGHTING_STYLES,
        ["dueling"],
    )

    assert member.sheet is not None
    record = next(
        record
        for record in member.sheet.progressionGrants or []
        if any(
            isinstance(grant, FightingStyleGrant)
            and grant.style == FightingStyleType.DUELING
            for grant in record.grants
        )
    )
    assert record.source.requiredSubclass == FighterSubclassType.CHAMPION

    set_member_class_levels(member, [replace(
        member.sheet.classes[0],
        subclass=FighterSubclassType.BATTLE_MASTER,
    )])

    assert member.sheet.classes[0].fightingStyles == [FightingStyleType.DEFENSE]


def test_hit_point_progression_records_fixed_and_rolled_results() -> None:
    classes = [CharacterClassLevel(name=ClassType.FIGHTER, level=2)]
    rule = progression_rule(ProgressionChoiceId.HIT_POINT_INCREASE, classes, {})
    assert rule is not None

    fixed = evaluate_progression_rule(
        rule,
        classes,
        {},
        ["fixed"],
        constitution_modifier=2,
    )
    rolled = evaluate_progression_rule(
        rule,
        classes,
        {},
        ["roll"],
        constitution_modifier=2,
        hit_die_result=4,
    )

    assert fixed.grants == (
        HitPointGrant(ClassType.FIGHTER, 2, HitPointChoiceOption.FIXED, 8, 6),
    )
    assert rolled.grants == (
        HitPointGrant(ClassType.FIGHTER, 2, HitPointChoiceOption.ROLL, 6, 4),
    )


def test_hit_point_progression_targets_missing_multiclass_level() -> None:
    classes = [
        CharacterClassLevel(name=ClassType.FIGHTER, level=2),
        CharacterClassLevel(name=ClassType.ROGUE, level=2),
    ]
    records = [
        hp_record(
            ClassType.FIGHTER,
            HitPointGrant(ClassType.FIGHTER, 2, HitPointChoiceOption.FIXED, 8, 6),
        ),
        hp_record(
            ClassType.ROGUE,
            HitPointGrant(ClassType.ROGUE, 1, HitPointChoiceOption.FIXED, 7, 5),
        ),
    ]

    rule = progression_rule(
        ProgressionChoiceId.HIT_POINT_INCREASE,
        classes,
        {},
        records,
    )

    assert rule is not None
    assert rule.requirements[0].characterClass == ClassType.ROGUE
    assert rule.requirements[0].minimumLevel == 2


def test_hit_point_progression_service_appends_one_persisted_roll(monkeypatch) -> None:
    member = PartyMemberConfig(
        id="fighter",
        name="Fighter",
        maxHp=20,
        abilityScores=None,
        sheet=PartyMemberSheet(
            classes=[CharacterClassLevel(name=ClassType.FIGHTER, level=3)],
            progressionGrants=[hp_record(
                ClassType.FIGHTER,
                HitPointGrant(ClassType.FIGHTER, 2, HitPointChoiceOption.FIXED, 8, 6),
            )],
        ),
    )
    monkeypatch.setattr(
        "dnd_board.application.progression_service.random.randint",
        lambda minimum, maximum: 4,
    )

    apply_member_progression_rule(
        member,
        ProgressionChoiceId.HIT_POINT_INCREASE,
        ["roll"],
    )

    assert member.maxHp == 24
    record = next(
        record
        for record in member.sheet.progressionGrants or []
        if record.source.rule == ProgressionChoiceId.HIT_POINT_INCREASE
    )
    assert record.grants[-1] == HitPointGrant(
        ClassType.FIGHTER,
        3,
        HitPointChoiceOption.ROLL,
        4,
        4,
    )


def test_constitution_asi_and_level_down_rederive_hit_points() -> None:
    member = PartyMemberConfig(
        id="fighter",
        name="Fighter",
        maxHp=36,
        abilityScores=AbilityScores(16, 14, 14, 10, 12, 8),
        baseAbilityScores=AbilityScores(16, 14, 14, 10, 12, 8),
        sheet=PartyMemberSheet(
            classes=[CharacterClassLevel(name=ClassType.FIGHTER, level=4)],
            progressionGrants=[hp_record(
                ClassType.FIGHTER,
                HitPointGrant(ClassType.FIGHTER, 2, HitPointChoiceOption.FIXED, 8, 6),
                HitPointGrant(ClassType.FIGHTER, 3, HitPointChoiceOption.FIXED, 8, 6),
                HitPointGrant(ClassType.FIGHTER, 4, HitPointChoiceOption.FIXED, 8, 6),
            )],
        ),
    )

    apply_member_progression_rule(
        member,
        ProgressionChoiceId.FIGHTER_ABILITY_SCORE_IMPROVEMENT,
        ["constitution", "constitution"],
    )
    assert member.maxHp == 40

    set_member_class_levels(member, [replace(member.sheet.classes[0], level=3)])

    assert member.abilityScores.constitution == 14
    assert member.maxHp == 28


def test_hit_point_derivation_applies_the_per_level_minimum() -> None:
    member = PartyMemberConfig(
        id="wizard",
        name="Wizard",
        maxHp=2,
        baseMaxHp=6,
        abilityScores=AbilityScores(8, 10, 1, 16, 12, 10),
        baseAbilityScores=AbilityScores(8, 10, 1, 16, 12, 10),
        sheet=PartyMemberSheet(
            classes=[CharacterClassLevel(name=ClassType.WIZARD, level=2)],
            progressionGrants=[hp_record(
                ClassType.WIZARD,
                HitPointGrant(ClassType.WIZARD, 2, HitPointChoiceOption.FIXED, 1, 4),
            )],
        ),
    )

    set_member_class_levels(member, member.sheet.classes)

    assert member.maxHp == 2


def test_manual_max_hit_point_adjustment_survives_level_changes() -> None:
    member = PartyMemberConfig(
        id="fighter",
        name="Fighter",
        maxHp=35,
        abilityScores=AbilityScores(16, 14, 14, 10, 12, 8),
        baseAbilityScores=AbilityScores(16, 14, 14, 10, 12, 8),
        sheet=PartyMemberSheet(
            classes=[CharacterClassLevel(name=ClassType.FIGHTER, level=3)],
            progressionGrants=[hp_record(
                ClassType.FIGHTER,
                HitPointGrant(ClassType.FIGHTER, 2, HitPointChoiceOption.FIXED, 8, 6),
                HitPointGrant(ClassType.FIGHTER, 3, HitPointChoiceOption.FIXED, 8, 6),
            )],
        ),
    )

    set_member_class_levels(member, [replace(member.sheet.classes[0], level=2)])

    assert member.manualMaxHpAdjustment == 7
    assert member.maxHp == 27


def test_persistent_feat_modifiers_drive_hit_points_and_speed() -> None:
    feats = [
        general_feat_feature("tough"),
        general_feat_feature("boonOfFortitude"),
        general_feat_feature("speedy"),
    ]

    assert feat_hit_point_bonus_per_level(feats) == 2
    assert feat_hit_point_bonus(feats, 5) == 50
    assert feat_speed_bonus(feats) == 10


def test_updating_wizard_cantrips_does_not_duplicate_eldritch_knight_spells() -> None:
    wizard_cantrip = wizard_spell_entry(SpellId.FIRE_BOLT)
    eldritch_cantrip = wizard_spell_entry(SpellId.MAGE_HAND)
    assert wizard_cantrip is not None
    assert eldritch_cantrip is not None
    eldritch_cantrip = normalized_eldritch_knight_spell(eldritch_cantrip)
    member = PartyMemberConfig(
        id="multiclass",
        name="Multiclass",
        sheet=PartyMemberSheet(
            classes=[
                CharacterClassLevel(name=ClassType.WIZARD, level=1),
                CharacterClassLevel(
                    name=ClassType.FIGHTER,
                    level=3,
                    subclass=FighterSubclassType.ELDRITCH_KNIGHT,
                ),
            ],
            spells=[wizard_cantrip, eldritch_cantrip],
            progressionGrants=[
                ProgressionGrantRecord(
                    ProgressionGrantSource(ProgressionChoiceId.WIZARD_CANTRIPS, ClassType.WIZARD),
                    (SpellGrant(
                        SpellId.FIRE_BOLT,
                        SpellCollection.KNOWN,
                        SpellSource.WIZARD,
                        SpellLevelCategory.CANTRIP,
                    ),),
                ),
                ProgressionGrantRecord(
                    ProgressionGrantSource(ProgressionChoiceId.ELDRITCH_KNIGHT_SPELLS, ClassType.FIGHTER),
                    (SpellGrant(
                        SpellId.MAGE_HAND,
                        SpellCollection.KNOWN,
                        SpellSource.ELDRITCH_KNIGHT,
                        SpellLevelCategory.CANTRIP,
                        3,
                    ),),
                ),
            ],
        ),
    )

    apply_member_progression_rule(
        member,
        ProgressionChoiceId.WIZARD_CANTRIPS,
        ["fireBolt", "light", "minorIllusion"],
    )

    assert member.sheet is not None
    assert sum(
        spell.id == SpellId.MAGE_HAND and spell.source == SpellSource.ELDRITCH_KNIGHT
        for spell in member.sheet.spells or []
    ) == 1


def test_declarative_skill_rule_evaluates_and_applies_sourced_grants() -> None:
    classes = [CharacterClassLevel(name=ClassType.ROGUE, level=1)]
    base_skills = {"deception": ProficiencyLevel.PROFICIENT}
    skill_rule = progression_rule(
        ProgressionChoiceId.ROGUE_SKILL_PROFICIENCIES,
        classes,
        base_skills,
    )
    assert skill_rule is not None

    skill_result = evaluate_progression_rule(
        skill_rule,
        classes,
        base_skills,
        ["acrobatics", "athletics", "perception", "stealth"],
    )
    skill_record = ProgressionGrantRecord(skill_result.source, skill_result.grants)
    skills = apply_progression_grants(base_skills, [skill_record])
    expertise_rule = progression_rule(
        ProgressionChoiceId.ROGUE_EXPERTISE,
        classes,
        skills,
    )
    assert expertise_rule is not None

    expertise_result = evaluate_progression_rule(
        expertise_rule,
        classes,
        skills,
        ["perception", "stealth"],
    )
    derived = apply_progression_grants(
        base_skills,
        [skill_record, ProgressionGrantRecord(expertise_result.source, expertise_result.grants)],
    )

    assert derived["deception"] == ProficiencyLevel.PROFICIENT
    assert derived["athletics"] == ProficiencyLevel.PROFICIENT
    assert derived["perception"] == ProficiencyLevel.EXPERTISE
    assert derived["stealth"] == ProficiencyLevel.EXPERTISE


def test_progression_service_reconciles_sourced_skills_without_removing_base_skills() -> None:
    member = PartyMemberConfig(
        id="rogue",
        name="Rogue",
        sheet=PartyMemberSheet(
            classes=[CharacterClassLevel(name=ClassType.ROGUE, level=1)],
            baseSkills={"deception": ProficiencyLevel.PROFICIENT},
        ),
    )
    apply_member_progression_rule(
        member,
        ProgressionChoiceId.ROGUE_SKILL_PROFICIENCIES,
        ["acrobatics", "athletics", "perception", "stealth"],
    )
    apply_member_progression_rule(
        member,
        ProgressionChoiceId.ROGUE_EXPERTISE,
        ["perception", "stealth"],
    )

    assert member.sheet is not None
    assert member.sheet.skills["stealth"] == ProficiencyLevel.EXPERTISE
    apply_member_progression_rule(
        member,
        ProgressionChoiceId.ROGUE_SKILL_PROFICIENCIES,
        ["acrobatics", "athletics", "investigation", "sleightOfHand"],
    )
    assert member.sheet.progressionGrants is not None
    assert [record.source.rule for record in member.sheet.progressionGrants] == [
        ProgressionChoiceId.ROGUE_SKILL_PROFICIENCIES,
    ]
    assert "stealth" not in member.sheet.skills
    set_member_class_levels(
        member,
        [CharacterClassLevel(name=ClassType.FIGHTER, level=1)],
    )

    assert member.sheet.skills == {"deception": ProficiencyLevel.PROFICIENT}
    assert member.sheet.progressionGrants is None


def test_rogue_level_down_keeps_only_level_one_expertise_grants() -> None:
    member = PartyMemberConfig(
        id="rogue",
        name="Rogue",
        sheet=PartyMemberSheet(
            classes=[CharacterClassLevel(name=ClassType.ROGUE, level=6)],
            baseSkills={},
        ),
    )
    apply_member_progression_rule(
        member,
        ProgressionChoiceId.ROGUE_SKILL_PROFICIENCIES,
        ["acrobatics", "athletics", "perception", "stealth"],
    )
    apply_member_progression_rule(
        member,
        ProgressionChoiceId.ROGUE_EXPERTISE,
        ["acrobatics", "athletics", "perception", "stealth"],
    )

    set_member_class_levels(
        member,
        [CharacterClassLevel(name=ClassType.ROGUE, level=5)],
    )

    assert member.sheet is not None
    assert member.sheet.skills["acrobatics"] == ProficiencyLevel.EXPERTISE
    assert member.sheet.skills["athletics"] == ProficiencyLevel.EXPERTISE
    assert member.sheet.skills["perception"] == ProficiencyLevel.PROFICIENT
    assert member.sheet.skills["stealth"] == ProficiencyLevel.PROFICIENT
    expertise = next(
        record
        for record in member.sheet.progressionGrants or []
        if record.source.rule == ProgressionChoiceId.ROGUE_EXPERTISE
    )
    assert len(expertise.grants) == 2


def test_arcane_trickster_spell_grants_require_mage_hand_and_reconcile_by_level() -> None:
    level_four = CharacterClassLevel(
        name=ClassType.ROGUE,
        level=4,
        subclass=RogueSubclassType.ARCANE_TRICKSTER,
    )
    selected = [
        SpellId.FIRE_BOLT,
        SpellId.MAGE_HAND,
        SpellId.MIND_SLIVER,
        SpellId.SHIELD,
        SpellId.MAGIC_MISSILE,
        SpellId.CHARM_PERSON,
        SpellId.DISGUISE_SELF,
    ]
    member = PartyMemberConfig(
        id="rogue",
        name="Rogue",
        sheet=PartyMemberSheet(classes=[level_four]),
    )
    apply_member_progression_rule(
        member,
        ProgressionChoiceId.ARCANE_TRICKSTER_SPELLS,
        [enum_key(spell_id) for spell_id in selected],
    )

    assert member.sheet is not None
    assert len(member.sheet.spells or []) == 7
    set_member_class_levels(member, [
        CharacterClassLevel(
            name=ClassType.ROGUE,
            level=3,
            subclass=RogueSubclassType.ARCANE_TRICKSTER,
        )
    ])
    assert len(member.sheet.spells or []) == 6

    try:
        apply_member_progression_rule(
            PartyMemberConfig(
                id="rogue",
                name="Rogue",
                sheet=PartyMemberSheet(classes=[CharacterClassLevel(
                    name=ClassType.ROGUE,
                    level=3,
                    subclass=RogueSubclassType.ARCANE_TRICKSTER,
                )]),
            ),
            ProgressionChoiceId.ARCANE_TRICKSTER_SPELLS,
            ["fireBolt", "mindSliver", "minorIllusion", "shield", "magicMissile", "charmPerson"],
        )
    except ProgressionServiceError as error:
        assert error.detail == "Choose legal Arcane Trickster cantrips and wizard spells"
    else:
        raise AssertionError("Expected Arcane Trickster selection without Mage Hand to fail")


def test_subclass_change_removes_only_subclass_spell_grants() -> None:
    guidance = spell_entry(SpellId.GUIDANCE)
    assert guidance is not None
    feat_guidance = replace(
        guidance,
        status=SpellStatus(
            source=SpellSource.MAGIC_INITIATE,
            castingAbility=guidance.castingAbility,
        ),
    )
    cases = (
        (
            CharacterClassLevel(
                name=ClassType.FIGHTER,
                level=3,
                subclass=FighterSubclassType.ELDRITCH_KNIGHT,
            ),
            ProgressionChoiceId.ELDRITCH_KNIGHT_SPELLS,
            ["fireBolt", "mageHand", "shield", "magicMissile", "findFamiliar"],
            CharacterClassLevel(
                name=ClassType.FIGHTER,
                level=3,
                subclass=FighterSubclassType.CHAMPION,
            ),
            SpellSource.ELDRITCH_KNIGHT,
        ),
        (
            CharacterClassLevel(
                name=ClassType.ROGUE,
                level=3,
                subclass=RogueSubclassType.ARCANE_TRICKSTER,
            ),
            ProgressionChoiceId.ARCANE_TRICKSTER_SPELLS,
            ["fireBolt", "mageHand", "mindSliver", "shield", "magicMissile", "charmPerson"],
            CharacterClassLevel(
                name=ClassType.ROGUE,
                level=3,
                subclass=RogueSubclassType.THIEF,
            ),
            SpellSource.ARCANE_TRICKSTER,
        ),
    )

    for original_class, choice_id, selections, replacement_class, removed_source in cases:
        member = PartyMemberConfig(
            id=enum_key(original_class.name),
            name=enum_key(original_class.name).title(),
            sheet=PartyMemberSheet(classes=[original_class], spells=[feat_guidance]),
        )
        apply_member_progression_rule(member, choice_id, selections)

        set_member_class_levels(member, [replacement_class])

        assert member.sheet is not None
        assert [spell.source for spell in member.sheet.spells or []] == [SpellSource.MAGIC_INITIATE]
        assert all(
            record.source.rule != choice_id
            for record in member.sheet.progressionGrants or []
        )
        assert removed_source not in {spell.source for spell in member.sheet.spells or []}


def test_progression_eligibility_rules_are_authoritative() -> None:
    pending = [ProgressionChoice("choice", ProgressionChoiceType.SKILL_PROFICIENCIES, "Choice", "", 1, 1, [], [])]
    rogue = CharacterClassLevel(name=ClassType.ROGUE, level=1)
    skills = {"stealth": ProficiencyLevel.PROFICIENT}

    assert level_advance_allowed([])
    assert not level_advance_allowed(pending)
    assert skill_proficiency_selection_issue(
        [SkillType.ATHLETICS],
        [SkillType.ATHLETICS, SkillType.PERCEPTION],
        1,
    ) is None
    assert skill_proficiency_selection_issue(
        [SkillType.STEALTH],
        [SkillType.ATHLETICS],
        1,
    ) == SkillSelectionIssue.INVALID_OPTION
    assert rogue_expertise_selection_issue(
        rogue,
        skills,
        [SkillType.PERCEPTION],
    ) == SkillSelectionIssue.REQUIRES_PROFICIENCY


def test_declarative_fighter_subclass_options_record_acquisition_levels() -> None:
    cases = (
        (
            CharacterClassLevel(name=ClassType.FIGHTER, level=7, subclass=FighterSubclassType.BATTLE_MASTER),
            ProgressionChoiceId.BATTLE_MASTER_MANEUVERS,
            ["ambush", "commandersStrike", "tripAttack", "rally", "precisionAttack"],
            ClassOptionKind.MANEUVER,
            (3, 3, 3, 7, 7),
        ),
        (
            CharacterClassLevel(name=ClassType.FIGHTER, level=15, subclass=FighterSubclassType.ARCANE_ARCHER),
            ProgressionChoiceId.ARCANE_ARCHER_SHOTS,
            ["banishingArrow", "graspingArrow", "seekingArrow", "shadowArrow"],
            ClassOptionKind.ARCANE_SHOT,
            (3, 3, 7, 15),
        ),
        (
            CharacterClassLevel(name=ClassType.FIGHTER, level=7, subclass=FighterSubclassType.RUNE_KNIGHT),
            ProgressionChoiceId.RUNE_KNIGHT_RUNES,
            ["cloudRune", "fireRune", "hillRune"],
            ClassOptionKind.RUNE,
            (3, 3, 7),
        ),
    )

    for fighter, choice_id, values, kind, levels in cases:
        rule = progression_rule(choice_id, [fighter], {})
        assert rule is not None
        result = evaluate_progression_rule(rule, [fighter], {}, values)

        assert all(isinstance(grant, ClassOptionGrant) for grant in result.grants)
        assert tuple(grant.kind for grant in result.grants) == (kind,) * len(values)
        assert tuple(grant.minimumClassLevel for grant in result.grants) == levels


def test_declarative_rune_options_enforce_level_requirements() -> None:
    fighter = CharacterClassLevel(
        name=ClassType.FIGHTER,
        level=3,
        subclass=FighterSubclassType.RUNE_KNIGHT,
    )
    rule = progression_rule(ProgressionChoiceId.RUNE_KNIGHT_RUNES, [fighter], {})
    assert rule is not None

    try:
        evaluate_progression_rule(rule, [fighter], {}, ["hillRune", "stormRune"])
    except ProgressionRuleViolation as error:
        assert error.issue == SkillSelectionIssue.INVALID_OPTION
    else:
        raise AssertionError("Level 3 Rune Knight accepted level 7 runes")


def test_fighter_class_option_grants_apply_and_reconcile_on_level_down() -> None:
    member = PartyMemberConfig(
        id="fighter",
        name="Fighter",
        sheet=PartyMemberSheet(classes=[CharacterClassLevel(
            name=ClassType.FIGHTER,
            level=7,
            subclass=FighterSubclassType.BATTLE_MASTER,
        )]),
    )
    selected = ["ambush", "commandersStrike", "tripAttack", "rally", "precisionAttack"]

    apply_member_progression_rule(
        member,
        ProgressionChoiceId.BATTLE_MASTER_MANEUVERS,
        selected,
    )

    assert member.sheet is not None
    assert member.sheet.classes[0].selected_options(ClassOptionKind.MANEUVER) == [
        BattleMasterManeuverType.AMBUSH,
        BattleMasterManeuverType.COMMANDERS_STRIKE,
        BattleMasterManeuverType.TRIP_ATTACK,
        BattleMasterManeuverType.RALLY,
        BattleMasterManeuverType.PRECISION_ATTACK,
    ]

    set_member_class_levels(member, [replace(member.sheet.classes[0], level=6)])

    assert member.sheet.classes[0].selected_options(ClassOptionKind.MANEUVER) == [
        BattleMasterManeuverType.AMBUSH,
        BattleMasterManeuverType.COMMANDERS_STRIKE,
        BattleMasterManeuverType.TRIP_ATTACK,
    ]
    pending = progression_choices(
        member.sheet.classes,
        member.sheet.spells or [],
        member.sheet.skills or {},
        progression_grants=member.sheet.progressionGrants,
    )
    assert ProgressionChoiceId.BATTLE_MASTER_MANEUVERS.value not in {
        choice.id for choice in pending
    }

    set_member_class_levels(member, [replace(member.sheet.classes[0], level=7)])
    pending = progression_choices(
        member.sheet.classes,
        member.sheet.spells or [],
        member.sheet.skills or {},
        progression_grants=member.sheet.progressionGrants,
    )
    maneuver_choice = next(
        choice
        for choice in pending
        if choice.id == ProgressionChoiceId.BATTLE_MASTER_MANEUVERS.value
    )
    assert maneuver_choice.selected == selected[:3]
    assert maneuver_choice.minimum == 5


def test_fighter_class_option_grants_are_removed_on_subclass_change() -> None:
    member = PartyMemberConfig(
        id="fighter",
        name="Fighter",
        sheet=PartyMemberSheet(classes=[CharacterClassLevel(
            name=ClassType.FIGHTER,
            level=7,
            subclass=FighterSubclassType.ARCANE_ARCHER,
        )]),
    )
    apply_member_progression_rule(
        member,
        ProgressionChoiceId.ARCANE_ARCHER_SHOTS,
        ["banishingArrow", "graspingArrow", "seekingArrow"],
    )

    assert member.sheet is not None
    set_member_class_levels(member, [replace(
        member.sheet.classes[0],
        subclass=FighterSubclassType.CHAMPION,
    )])

    assert member.sheet.classes[0].selected_options(ClassOptionKind.ARCANE_SHOT) == []
    assert all(
        record.source.rule != ProgressionChoiceId.ARCANE_ARCHER_SHOTS
        for record in member.sheet.progressionGrants or []
    )


def test_superior_technique_maneuver_survives_losing_battle_master() -> None:
    member = PartyMemberConfig(
        id="fighter",
        name="Fighter",
        sheet=PartyMemberSheet(classes=[CharacterClassLevel(
            name=ClassType.FIGHTER,
            level=3,
            subclass=FighterSubclassType.BATTLE_MASTER,
            fightingStyles=[FightingStyleType.SUPERIOR_TECHNIQUE],
        )]),
    )
    selected = ["ambush", "commandersStrike", "tripAttack", "rally"]
    apply_member_progression_rule(
        member,
        ProgressionChoiceId.BATTLE_MASTER_MANEUVERS,
        selected,
    )

    assert member.sheet is not None
    record = next(
        record
        for record in member.sheet.progressionGrants or []
        if record.source.rule == ProgressionChoiceId.BATTLE_MASTER_MANEUVERS
    )
    assert tuple(grant.minimumClassLevel for grant in record.grants) == (1, 3, 3, 3)

    set_member_class_levels(member, [replace(
        member.sheet.classes[0],
        subclass=FighterSubclassType.CHAMPION,
    )])

    assert member.sheet.classes[0].selected_options(ClassOptionKind.MANEUVER) == [BattleMasterManeuverType.AMBUSH]


def test_progression_parser_and_level_update_reject_unknown_values() -> None:
    classes = [CharacterClassLevel(name=ClassType.ROGUE, level=4)]

    assert parse_progression_choice_id("not-a-choice") is None
    assert parse_progression_choice_id("fighter-subclass") == ProgressionChoiceId.FIGHTER_SUBCLASS
    assert update_class_level(classes, ClassType.FIGHTER, 1) == classes


def test_apply_and_prune_progression_edge_paths() -> None:
    fighter = CharacterClassLevel(
        name=ClassType.FIGHTER,
        level=3,
        subclass=FighterSubclassType.ARCANE_ARCHER,
        classOptions=[
            ClassOptionSelection(ClassOptionKind.ARCANE_SHOT, ArcaneShotType.BANISHING_ARROW),
            ClassOptionSelection(ClassOptionKind.RUNE, RuneType.CLOUD_RUNE),
        ],
    )
    low_level_fighter = prune_progression_choices([CharacterClassLevel(name=ClassType.FIGHTER, level=2, subclass=FighterSubclassType.ARCANE_ARCHER, classOptions=[ClassOptionSelection(ClassOptionKind.ARCANE_SHOT, ArcaneShotType.BANISHING_ARROW), ClassOptionSelection(ClassOptionKind.RUNE, RuneType.CLOUD_RUNE)])])[0]
    low_level_rogue = prune_progression_choices([CharacterClassLevel(name=ClassType.ROGUE, level=2, subclass=RogueSubclassType.SOULKNIFE)])[0]

    assert low_level_fighter.subclass is None
    assert low_level_fighter.selected_options(ClassOptionKind.ARCANE_SHOT) == [ArcaneShotType.BANISHING_ARROW]
    assert low_level_fighter.selected_options(ClassOptionKind.RUNE) == [RuneType.CLOUD_RUNE]
    assert low_level_rogue.subclass is None
    assert update_class_level([CharacterClassLevel(name=ClassType.FIGHTER, level=20)], ClassType.FIGHTER, 1)[0].level == 20
    assert update_class_level([CharacterClassLevel(name=ClassType.FIGHTER, level=1)], ClassType.FIGHTER, -1)[0].level == 1


def test_declarative_subclass_rule_applies_typed_grant() -> None:
    member = PartyMemberConfig(
        id="rogue",
        name="Rogue",
        sheet=PartyMemberSheet(
            classes=[CharacterClassLevel(name=ClassType.ROGUE, level=3)],
        ),
    )

    apply_member_progression_rule(
        member,
        ProgressionChoiceId.ROGUE_SUBCLASS,
        ["soulknife"],
    )

    assert member.sheet is not None
    assert member.sheet.classes[0].subclass == RogueSubclassType.SOULKNIFE
    record = next(
        record
        for record in member.sheet.progressionGrants or []
        if record.source.rule == ProgressionChoiceId.ROGUE_SUBCLASS
    )
    assert record.grants[0].subclass == RogueSubclassType.SOULKNIFE

    restored = typed_json_to_value(
        typed_json_from_value(member.sheet),
        PartyMemberSheet,
    )
    assert restored.progressionGrants[0].grants[0].subclass == RogueSubclassType.SOULKNIFE


def test_declarative_subclass_rule_rejects_unknown_subclass() -> None:
    member = PartyMemberConfig(
        id="fighter",
        name="Fighter",
        sheet=PartyMemberSheet(
            classes=[CharacterClassLevel(name=ClassType.FIGHTER, level=3)],
        ),
    )

    try:
        apply_member_progression_rule(
            member,
            ProgressionChoiceId.FIGHTER_SUBCLASS,
            ["notASubclass"],
        )
    except ProgressionServiceError as error:
        assert error.detail == "Choose a legal Fighter subclass"
    else:
        raise AssertionError("Expected unknown Fighter subclass to fail")


def test_progression_value_helpers_filter_duplicates_and_invalid_values() -> None:
    assert selected_enum_keys([FightingStyleType.DEFENSE, FightingStyleType.DEFENSE, FightingStyleType.DUELING]) == ["defense", "dueling"]
    assert parse_enum_values(FightingStyleType, ["defense", "defense", "not-real"]) == [FightingStyleType.DEFENSE]
    assert unique_values(["a", "a", "b"]) == ["a", "b"]


def test_wizard_progression_choices_ignore_invalid_hidden_cantrip_selections() -> None:
    guidance = spell_entry(SpellId.GUIDANCE)
    resistance = spell_entry(SpellId.RESISTANCE)
    shillelagh = spell_entry(SpellId.SHILLELAGH)
    fire_bolt = wizard_spell_entry(SpellId.FIRE_BOLT)
    assert guidance is not None
    assert resistance is not None
    assert shillelagh is not None
    assert fire_bolt is not None
    stale_cantrips = [
        replace(spell, status=SpellStatus(source=SpellSource.WIZARD, castingAbility=spell.castingAbility))
        for spell in (guidance, resistance, shillelagh)
    ]

    choices = progression_choices(
        [CharacterClassLevel(name=ClassType.WIZARD, level=4)],
        [*stale_cantrips, fire_bolt],
        {},
    )
    cantrip_choice = next(choice for choice in choices if choice.id == "wizardCantrips")

    assert cantrip_choice.maximum == 4
    assert cantrip_choice.selected == ["fireBolt"]
