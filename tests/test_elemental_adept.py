import pytest

from dnd_board.application.progression_service import ProgressionServiceError, apply_member_progression_rule, member_feat_eligibility_sheet, set_member_class_levels
from dnd_board.character_sheet import (
    AbilityScores,
    CharacterClassLevel,
    ClassType,
    DamageType,
    PartyMember,
    PartyMemberConfig,
    PartyMemberSheet,
    SpellId,
    TokenKind,
    build_character_sheet,
    build_spell_damage_roll_payload,
    resolve_roll_against_target,
    typed_json_from_value,
    typed_json_to_value,
)
from dnd_board.rules.feats import FeatOptionId, GeneralFeatType, general_feat_feature
from dnd_board.rules.progression import (
    AbilityScoreGrant,
    FeatGrant,
    ProgressionChoiceId,
    ProgressionGrantRecord,
    ProgressionGrantSource,
    progression_choices,
    progression_rule,
    spell_damage_traits_from_grants,
)
from dnd_board.rules.spells import wizard_spell_entry


def wizard_member() -> PartyMemberConfig:
    burning_hands = wizard_spell_entry(SpellId.BURNING_HANDS)
    assert burning_hands is not None
    return PartyMemberConfig(
        id="wizard",
        name="Wizard",
        maxHp=24,
        abilityScores=AbilityScores(8, 12, 14, 16, 10, 10),
        sheet=PartyMemberSheet(
            classes=[CharacterClassLevel(ClassType.WIZARD, 4)],
            spells=[burning_hands],
        ),
    )


def sheet_for(member: PartyMemberConfig, *, resist_fire=False, immune_fire=False):
    config = member.sheet or PartyMemberSheet()
    if resist_fire or immune_fire:
        config = PartyMemberSheet(
            classes=[CharacterClassLevel(ClassType.FIGHTER, 4)],
            damageResistances=[DamageType.FIRE] if resist_fire else None,
            damageImmunities=[DamageType.FIRE] if immune_fire else None,
        )
    return build_character_sheet(
        token_id=member.id,
        kind=TokenKind.CHARACTER,
        name=member.name,
        owner="player-1",
        avatar_url=None,
        party_member=PartyMember(
            id=member.id,
            name=member.name,
            owner="player-1",
            avatarUrl=None,
            maxHp=member.maxHp,
            abilityScores=member.abilityScores,
            sheet=config,
        ),
        current_hp=member.maxHp,
        resource_overrides={},
    )


def test_elemental_adept_options_are_typed_and_repeatable_by_damage_type() -> None:
    member = wizard_member()
    classes = member.sheet.classes
    choices = progression_choices(classes, member.sheet.spells, {}, feat_eligibility_sheet=None)
    asi = next(choice for choice in choices if choice.id == ProgressionChoiceId.WIZARD_ABILITY_SCORE_IMPROVEMENT.value)
    assert {option.value for option in asi.options if option.label.startswith("Elemental Adept") } == {
        "elementalAdeptAcid", "elementalAdeptCold", "elementalAdeptFire",
        "elementalAdeptLightning", "elementalAdeptThunder",
    }

    apply_member_progression_rule(member, ProgressionChoiceId.WIZARD_ABILITY_SCORE_IMPROVEMENT, ["feat:elementalAdeptFire"])
    fire_grant = next(
        grant
        for record in member.sheet.progressionGrants
        for grant in record.grants
        if isinstance(grant, FeatGrant)
    )
    assert fire_grant.option == FeatOptionId.ELEMENTAL_ADEPT_FIRE
    assert typed_json_to_value(typed_json_from_value(fire_grant)) == fire_grant
    assert spell_damage_traits_from_grants(member.sheet.progressionGrants, member.sheet.classes)[0].damageType == DamageType.FIRE

    apply_member_progression_rule(member, ProgressionChoiceId.FEAT_ABILITY_SCORE_INCREASE, ["intelligence"])
    first_asi = next(
        record for record in member.sheet.progressionGrants
        if record.source.rule == ProgressionChoiceId.FEAT_ABILITY_SCORE_INCREASE
    )
    assert first_asi.source.requiredFeatLevel == 4
    assert any(isinstance(grant, AbilityScoreGrant) for grant in first_asi.grants)

    member.sheet.classes = [CharacterClassLevel(ClassType.WIZARD, 8)]
    next_choices = progression_choices(
        member.sheet.classes,
        member.sheet.spells,
        {},
        member.sheet.feats,
        member_feat_eligibility_sheet(member),
        progression_grants=member.sheet.progressionGrants,
    )
    next_asi = next(choice for choice in next_choices if choice.id == ProgressionChoiceId.WIZARD_ABILITY_SCORE_IMPROVEMENT.value)
    assert "elementalAdeptFire" not in {option.value for option in next_asi.options}
    assert "elementalAdeptCold" in {option.value for option in next_asi.options}
    with pytest.raises(ProgressionServiceError):
        apply_member_progression_rule(member, ProgressionChoiceId.WIZARD_ABILITY_SCORE_IMPROVEMENT, ["feat:elementalAdeptFire"])
    apply_member_progression_rule(member, ProgressionChoiceId.WIZARD_ABILITY_SCORE_IMPROVEMENT, ["feat:elementalAdeptCold"])
    assert {trait.damageType for trait in spell_damage_traits_from_grants(member.sheet.progressionGrants, member.sheet.classes)} == {DamageType.FIRE, DamageType.COLD}
    next_rule = progression_rule(ProgressionChoiceId.FEAT_ABILITY_SCORE_INCREASE, member.sheet.classes, {}, member.sheet.progressionGrants)
    assert next_rule is not None
    assert next_rule.sourceFeatLevel == 8
    apply_member_progression_rule(member, ProgressionChoiceId.FEAT_ABILITY_SCORE_INCREASE, ["wisdom"])
    assert member.abilityScores.wisdom == 11
    assert {record.source.requiredFeatLevel for record in member.sheet.progressionGrants if record.source.rule == ProgressionChoiceId.FEAT_ABILITY_SCORE_INCREASE} == {4, 8}

    set_member_class_levels(member, [CharacterClassLevel(ClassType.WIZARD, 7)])
    assert {trait.damageType for trait in spell_damage_traits_from_grants(member.sheet.progressionGrants, member.sheet.classes)} == {DamageType.FIRE}
    assert member.abilityScores.wisdom == 10


def test_elemental_adept_adjusts_spell_dice_and_ignores_resistance_but_not_immunity(monkeypatch) -> None:
    member = wizard_member()
    member.sheet.progressionGrants = [ProgressionGrantRecord(
        ProgressionGrantSource(ProgressionChoiceId.WIZARD_ABILITY_SCORE_IMPROVEMENT, ClassType.WIZARD),
        (FeatGrant(ClassType.WIZARD, 4, GeneralFeatType.ELEMENTAL_ADEPT, FeatOptionId.ELEMENTAL_ADEPT_FIRE),),
    )]
    member.sheet.feats = [general_feat_feature("elementalAdept")]
    caster = sheet_for(member)
    target_member = PartyMemberConfig("target", "Target", maxHp=20, abilityScores=AbilityScores(10, 10, 10, 10, 10, 10))
    resistant = sheet_for(target_member, resist_fire=True)
    immune = sheet_for(target_member, immune_fire=True)
    monkeypatch.setattr("dnd_board.character_sheet.random.randint", lambda _minimum, _maximum: 1)
    roll = build_spell_damage_roll_payload(caster, "player-1", member.sheet.spells[0], damage_save_succeeded=False)

    assert roll.dice == [1, 1, 1]
    assert roll.total == 6
    assert any(part.source == "Elemental Adept" and part.value == 3 for part in roll.modifierBreakdown)
    resisted_resolution = resolve_roll_against_target(roll, resistant, caster)
    assert resisted_resolution.targetHp.current == 14
    assert "ignoring Fire resistance" in resisted_resolution.outcome
    assert resolve_roll_against_target(roll, immune, caster).targetHp.current == 20

    member.sheet.progressionGrants = None
    ordinary = sheet_for(member)
    ordinary_roll = build_spell_damage_roll_payload(ordinary, "player-1", member.sheet.spells[0], damage_save_succeeded=False)
    assert ordinary_roll.total == 3
    assert resolve_roll_against_target(ordinary_roll, resistant, ordinary).targetHp.current == 19


def test_elemental_adept_applies_only_to_matching_component_of_a_spell(monkeypatch) -> None:
    member = wizard_member()
    ice_storm = wizard_spell_entry(SpellId.ICE_STORM)
    assert ice_storm is not None
    member.sheet.classes = [CharacterClassLevel(ClassType.WIZARD, 8)]
    member.sheet.spells = [ice_storm]
    member.sheet.progressionGrants = [ProgressionGrantRecord(
        ProgressionGrantSource(ProgressionChoiceId.WIZARD_ABILITY_SCORE_IMPROVEMENT, ClassType.WIZARD),
        (FeatGrant(ClassType.WIZARD, 4, GeneralFeatType.ELEMENTAL_ADEPT, FeatOptionId.ELEMENTAL_ADEPT_COLD),),
    )]
    caster = sheet_for(member)
    monkeypatch.setattr("dnd_board.character_sheet.random.randint", lambda _minimum, _maximum: 1)
    roll = build_spell_damage_roll_payload(caster, "player-1", ice_storm, spell_slot_level=4, damage_save_succeeded=False)
    components = {component.damageType: component for component in roll.damageComponents or []}
    assert DamageType.COLD in components
    assert DamageType.BLUDGEONING in components
    assert components[DamageType.COLD].total == 2 * len(components[DamageType.COLD].dice)
    assert components[DamageType.BLUDGEONING].total == len(components[DamageType.BLUDGEONING].dice)
