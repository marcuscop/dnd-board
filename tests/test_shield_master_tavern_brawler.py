from dataclasses import replace

from dnd_board.character_sheet import (
    AbilityScores,
    AbilityType,
    AttackActionType,
    CharacterClassLevel,
    ClassType,
    DiceType,
    EquipmentItem,
    EquipmentSlot,
    EquipmentType,
    PartyMember,
    PartyMemberSheet,
    SpellSaveOutcome,
    TokenKind,
    build_character_sheet,
    build_combined_attack_roll_payload,
    build_damage_roll_payload,
    enum_key,
    typed_json_from_value,
    typed_json_to_value,
)
from dnd_board.rules.feats import (
    FeatCategory,
    GENERAL_FEATS,
    GeneralFeatType,
    general_feat_feature,
    general_feat_prerequisites_met,
    has_weapon_proficiency,
)
from dnd_board.rules.equipment import WeaponTrainingCategory
from dnd_board.rules.shared.character_effects import CharacterEffectExecutionContext
from dnd_board.rules.shared.effects import EffectNodeId


def sheet_with_feat(feat: GeneralFeatType, *, level: int = 5, shield: bool = False):
    feature = general_feat_feature(enum_key(feat))
    assert feature is not None
    equipment = [
        EquipmentItem(
            id="shield",
            name="Shield",
            itemType=EquipmentType.SHIELD,
            slot=EquipmentSlot.OFF_HAND,
            armorClassBonus=2,
        )
    ] if shield else []
    return build_character_sheet(
        token_id="fighter",
        kind=TokenKind.CHARACTER,
        name="Fighter",
        owner="player-1",
        avatar_url=None,
        party_member=PartyMember(
            id="fighter",
            name="Fighter",
            owner="player-1",
            avatarUrl=None,
            maxHp=30,
            abilityScores=AbilityScores(16, 12, 14, 10, 10, 10),
            sheet=PartyMemberSheet(
                classes=[CharacterClassLevel(ClassType.FIGHTER, level)],
                feats=[feature],
                equipment=equipment,
            ),
        ),
        current_hp=None,
        resource_overrides={},
    )


def matches(sheet, roll, predicates):
    return CharacterEffectExecutionContext(roll, sheet, sheet, owner=sheet).evaluate_predicates(
        EffectNodeId(()), predicates
    )


def test_shield_master_prerequisite_and_interpose_require_successful_dex_half_save() -> None:
    sheet = sheet_with_feat(GeneralFeatType.SHIELD_MASTER, shield=True)
    assert general_feat_prerequisites_met(GeneralFeatType.SHIELD_MASTER, sheet)
    assert GENERAL_FEATS[GeneralFeatType.SHIELD_MASTER].abilityScoreAdjustmentChoice.candidates == (AbilityType.STRENGTH,)
    reaction = GENERAL_FEATS[GeneralFeatType.SHIELD_MASTER].mechanics.interactions[0]
    roll = build_damage_roll_payload(sheet, "player-1", sheet.attacks[0])
    succeeded = replace(
        roll,
        damageSavingThrow=AbilityType.DEXTERITY,
        damageSaveOutcome=SpellSaveOutcome.HALF_DAMAGE,
        damageSaveSucceeded=True,
    )
    assert matches(sheet, succeeded, reaction.predicates)
    assert not matches(sheet, replace(succeeded, damageSaveSucceeded=False), reaction.predicates)
    assert not matches(sheet, replace(succeeded, damageSavingThrow=AbilityType.CONSTITUTION), reaction.predicates)
    assert not matches(sheet, replace(succeeded, damageSaveOutcome=SpellSaveOutcome.NEGATES), reaction.predicates)
    sheet.equipment.clear()
    assert not matches(sheet, succeeded, reaction.predicates)
    assert not general_feat_prerequisites_met(GeneralFeatType.SHIELD_MASTER, sheet_with_feat(GeneralFeatType.SHIELD_MASTER, level=3))


def test_tavern_brawler_grants_unarmed_damage_and_only_rerolls_ones(monkeypatch) -> None:
    sheet = sheet_with_feat(GeneralFeatType.TAVERN_BRAWLER)
    definition = GENERAL_FEATS[GeneralFeatType.TAVERN_BRAWLER]
    assert definition.category == FeatCategory.ORIGIN
    assert definition.abilityScoreAdjustmentChoice is None
    assert has_weapon_proficiency(sheet, WeaponTrainingCategory.IMPROVISED)
    unarmed = next(attack for attack in sheet.attacks if attack.attackType == AttackActionType.UNARMED_STRIKE)
    assert (unarmed.damageDiceCount, unarmed.damageDiceType, unarmed.ability) == (1, DiceType.D4, AbilityType.STRENGTH)

    monkeypatch.setattr("dnd_board.character_sheet.random.randint", lambda _minimum, _maximum: 1)
    roll = build_combined_attack_roll_payload(sheet, "player-1", unarmed)
    reroll, push = definition.mechanics.interactions
    assert matches(sheet, roll, reroll.predicates)
    assert matches(sheet, roll, push.predicates)
    not_one = replace(roll, damageComponents=[replace(roll.damageComponents[0], dice=[2])])
    assert not matches(sheet, not_one, reroll.predicates)
    assert matches(sheet, not_one, push.predicates)


def test_new_feat_predicates_survive_typed_json_round_trip() -> None:
    for feat in (GeneralFeatType.SHIELD_MASTER, GeneralFeatType.TAVERN_BRAWLER):
        mechanics = GENERAL_FEATS[feat].mechanics
        assert typed_json_to_value(typed_json_from_value(mechanics)) == mechanics
