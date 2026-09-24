from types import SimpleNamespace

from dnd_board.character_sheet import (
    AbilityScores,
    AbilityType,
    ArmorCategory,
    AttackAction,
    ConditionType,
    CharacterClassLevel,
    ClassType,
    D20DisadvantageSource,
    DiceType,
    EquipmentItem,
    EquipmentSlot,
    EquipmentType,
    PartyMember,
    PartyMemberSheet,
    TokenKind,
    attack_roll_with_target_condition_modifiers,
    base_armor_class,
    build_ability_check_roll_payload,
    build_attack_roll_payload,
    build_character_sheet,
    build_saving_throw_roll_payload,
    enum_key,
    roll_payload_to_dict,
)
from dnd_board.application.action_service import response_ability_roll
from dnd_board.application.resolution_interactions import sheet_interaction_sources
from dnd_board.rules.spells import wizard_spell_entry
from dnd_board.character_sheet import SpellId
from dnd_board.rules.shared.character_effects import CharacterEffectExecutionContext
from dnd_board.rules.shared.effects import AmountCalculation, CalculatedAmount
from dnd_board.rules.feats import (
    GENERAL_FEATS,
    GeneralFeatType,
    effective_armor_training,
    general_feat_feature,
    general_feat_prerequisites_met,
    has_shield_training,
)


def eligibility(classes, feats=()):
    return SimpleNamespace(
        classes=list(classes),
        feats=[general_feat_feature(enum_key(feat)) for feat in feats],
        proficiencies=[],
        abilityScores=AbilityScores(12, 12, 12, 10, 10, 10),
    )


def test_armor_feats_derive_training_and_chained_prerequisites() -> None:
    wizard = [CharacterClassLevel(ClassType.WIZARD, 4)]
    assert general_feat_prerequisites_met(GeneralFeatType.LIGHTLY_ARMORED, eligibility(wizard))
    assert not general_feat_prerequisites_met(GeneralFeatType.MODERATELY_ARMORED, eligibility(wizard))

    lightly = eligibility(wizard, (GeneralFeatType.LIGHTLY_ARMORED,))
    armor, shields = effective_armor_training(lightly.classes, lightly.feats, lightly.proficiencies)
    assert armor == {ArmorCategory.LIGHT}
    assert shields and has_shield_training(lightly)
    assert general_feat_prerequisites_met(GeneralFeatType.MODERATELY_ARMORED, lightly)

    moderately = eligibility(wizard, (GeneralFeatType.LIGHTLY_ARMORED, GeneralFeatType.MODERATELY_ARMORED))
    assert general_feat_prerequisites_met(GeneralFeatType.HEAVILY_ARMORED, moderately)
    assert not has_shield_training(eligibility(wizard, (GeneralFeatType.MODERATELY_ARMORED,)))
    assert not general_feat_prerequisites_met(
        GeneralFeatType.LIGHTLY_ARMORED,
        eligibility([CharacterClassLevel(ClassType.WIZARD, 3)]),
    )


def test_armor_feat_asi_choices_match_2024_definitions() -> None:
    assert GENERAL_FEATS[GeneralFeatType.HEAVILY_ARMORED].abilityScoreAdjustmentChoice.candidates == (
        AbilityType.CONSTITUTION, AbilityType.STRENGTH
    )
    for feat in (GeneralFeatType.LIGHTLY_ARMORED, GeneralFeatType.MODERATELY_ARMORED):
        assert GENERAL_FEATS[feat].abilityScoreAdjustmentChoice.candidates == (
            AbilityType.STRENGTH, AbilityType.DEXTERITY
        )


def test_class_training_and_feat_training_are_projected_without_persisted_duplicates() -> None:
    classes = [CharacterClassLevel(ClassType.WIZARD, 4), CharacterClassLevel(ClassType.FIGHTER, 1)]
    armor, shields = effective_armor_training(classes, [], [])
    assert armor == {ArmorCategory.LIGHT, ArmorCategory.MEDIUM}
    assert shields

    member = PartyMember(
        id="wizard",
        name="Wizard",
        owner="player-1",
        avatarUrl=None,
        maxHp=24,
        abilityScores=AbilityScores(10, 12, 12, 16, 10, 10),
        sheet=PartyMemberSheet(
            classes=[CharacterClassLevel(ClassType.WIZARD, 4)],
            feats=[general_feat_feature(enum_key(GeneralFeatType.LIGHTLY_ARMORED))],
        ),
    )
    sheet = build_character_sheet(
        token_id="wizard",
        kind=TokenKind.CHARACTER,
        name="Wizard",
        owner="player-1",
        avatar_url=None,
        party_member=member,
        current_hp=24,
        resource_overrides={},
    )
    assert "Light armor" in sheet.proficiencies
    assert "Shields" in sheet.proficiencies
    assert member.sheet.proficiencies is None

    member.sheet.feats = []
    sheet = build_character_sheet(
        token_id="wizard",
        kind=TokenKind.CHARACTER,
        name="Wizard",
        owner="player-1",
        avatar_url=None,
        party_member=member,
        current_hp=24,
        resource_overrides={},
    )
    assert "Light armor" not in sheet.proficiencies
    assert "Shields" not in sheet.proficiencies


def equipped_sheet(class_type=ClassType.WIZARD, feats=(), armor=True, shield=True):
    equipment = []
    if armor:
        equipment.append(EquipmentItem(
            id="leather", name="Leather Armor", itemType=EquipmentType.ARMOR,
            slot=EquipmentSlot.ARMOR, armorCategory=ArmorCategory.LIGHT, armorClass=11,
        ))
    if shield:
        equipment.append(EquipmentItem(
            id="shield", name="Shield", itemType=EquipmentType.SHIELD,
            slot=EquipmentSlot.OFF_HAND, armorClassBonus=2,
        ))
    member = PartyMember(
        id="owner", name="Owner", owner="player-1", avatarUrl=None, maxHp=24,
        abilityScores=AbilityScores(14, 12, 12, 16, 10, 10),
        sheet=PartyMemberSheet(
            classes=[CharacterClassLevel(class_type, 4)],
            equipment=equipment,
            feats=[general_feat_feature(enum_key(feat)) for feat in feats],
        ),
    )
    return build_character_sheet(
        token_id="owner", kind=TokenKind.CHARACTER, name="Owner", owner="player-1",
        avatar_url=None, party_member=member, current_hp=24, resource_overrides={},
    )


def test_untrained_armor_disadvantages_strength_and_dexterity_d20_tests(monkeypatch) -> None:
    monkeypatch.setattr("dnd_board.character_sheet.random.randint", lambda _minimum, maximum: 7)
    monkeypatch.setattr("dnd_board.application.action_service.random.randint", lambda _minimum, maximum: 7)
    sheet = equipped_sheet()
    expected = [D20DisadvantageSource.UNTRAINED_ARMOR]
    for roll in (
        build_ability_check_roll_payload(sheet, "player-1", AbilityType.STRENGTH),
        build_saving_throw_roll_payload(sheet, "player-1", AbilityType.DEXTERITY),
        build_attack_roll_payload(sheet, "player-1", AttackAction("sword", "Sword", AbilityType.STRENGTH, 1, DiceType.D8)),
        response_ability_roll(
            sheet=sheet, ability=AbilityType.DEXTERITY, action_id="save", label="Save",
            source_label="Effect", modifier=1,
        ),
    ):
        assert roll.die == "2d20kl1"
        assert len(roll.dice) == 2
        assert roll.disadvantageSources == expected
        assert roll_payload_to_dict(roll)["disadvantageSourcesLabel"] == ["Untrained armor"]

    assert build_saving_throw_roll_payload(sheet, "player-1", AbilityType.CONSTITUTION).die == "d20"
    assert build_ability_check_roll_payload(sheet, "player-1", AbilityType.WISDOM).die == "d20"

    attack = build_attack_roll_payload(sheet, "player-1", AttackAction("sword", "Sword", AbilityType.STRENGTH, 1, DiceType.D8))
    target = equipped_sheet(class_type=ClassType.FIGHTER, armor=False, shield=False)
    target.conditions = [ConditionType.BLINDED]
    resolved = attack_roll_with_target_condition_modifiers(attack, target, sheet)
    assert resolved.die == "d20"
    assert resolved.disadvantageSources == expected


def test_shield_penalty_is_separate_from_armor_training() -> None:
    wizard = equipped_sheet(armor=False)
    assert wizard.armorClass == 13
    assert build_saving_throw_roll_payload(wizard, "player-1", AbilityType.DEXTERITY).die == "d20"

    trained = equipped_sheet(feats=(GeneralFeatType.LIGHTLY_ARMORED,))
    assert trained.armorClass == 14
    assert build_saving_throw_roll_payload(trained, "player-1", AbilityType.DEXTERITY).die == "d20"

    fighter = equipped_sheet(class_type=ClassType.FIGHTER)
    assert fighter.armorClass == 14
    assert build_saving_throw_roll_payload(fighter, "player-1", AbilityType.DEXTERITY).die == "d20"

    shield_item = wizard.equipment[0]
    assert base_armor_class(PartyMemberSheet(armorClass=16), [shield_item], 1, shield_trained=False) == 14
    assert base_armor_class(PartyMemberSheet(armorClass=16), [shield_item], 1, shield_trained=True) == 16


def test_untrained_armor_does_not_offer_spell_reactions() -> None:
    sheet = equipped_sheet()
    counterspell = wizard_spell_entry(SpellId.COUNTERSPELL)
    assert counterspell is not None
    sheet.spells = [counterspell]
    assert not any(source.label == "Counterspell" for source in sheet_interaction_sources(sheet))

    sheet.equipment = []
    assert any(source.label == "Counterspell" for source in sheet_interaction_sources(sheet))


def test_effect_amount_uses_only_trained_shield_bonus() -> None:
    sheet = equipped_sheet(armor=False)
    roll = build_ability_check_roll_payload(sheet, "player-1", AbilityType.WISDOM)
    amount = CalculatedAmount(AmountCalculation.SOURCE_EQUIPPED_SHIELD_ARMOR_CLASS)
    assert CharacterEffectExecutionContext(roll, sheet, sheet).resolve_runtime_amount_part(amount, sheet) == 0

    trained = equipped_sheet(feats=(GeneralFeatType.LIGHTLY_ARMORED,), armor=False)
    roll = build_ability_check_roll_payload(trained, "player-1", AbilityType.WISDOM)
    assert CharacterEffectExecutionContext(roll, trained, trained).resolve_runtime_amount_part(amount, trained) == 2
