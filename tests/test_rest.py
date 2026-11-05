import pytest

from dnd_board.character_sheet import (
    AbilityScores,
    CharacterClassLevel,
    ClassType,
    PartyMember,
    PartyMemberSheet,
    RestType,
    TokenKind,
    build_character_sheet,
)
from dnd_board.application.rest_service import prepare_rest
from dnd_board.rules.feats import GeneralFeatType, general_feat_feature, selected_general_feat_types
from dnd_board.rules.rest import HitDieSpend, roll_hit_dice_for_rest
from dnd_board.rules.shared.resources import ResourceId


def test_rest_handles_feats_with_numeric_and_named_enum_values() -> None:
    sheet = build_character_sheet(
        token_id="bard",
        kind=TokenKind.CHARACTER,
        name="Bard",
        owner="player-1",
        avatar_url=None,
        party_member=PartyMember(
            id="bard",
            name="Bard",
            owner="player-1",
            avatarUrl=None,
            maxHp=12,
            abilityScores=AbilityScores(10, 10, 10, 10, 10, 10),
            sheet=PartyMemberSheet(
                classes=[CharacterClassLevel(ClassType.FIGHTER, 1)],
                feats=[
                    general_feat_feature("alert"),
                    general_feat_feature("musician"),
                ],
            ),
        ),
        current_hp=12,
        resource_overrides={},
    )

    assert {GeneralFeatType.ALERT, GeneralFeatType.MUSICIAN} <= selected_general_feat_types(sheet.features)
    assert prepare_rest([sheet], RestType.LONG_REST, "dm", {}).restType == RestType.LONG_REST


def test_short_rest_hit_dice_apply_constitution_with_one_hp_minimum(monkeypatch) -> None:
    sheet = build_character_sheet(
        token_id="wizard",
        kind=TokenKind.CHARACTER,
        name="Wizard",
        owner="player-1",
        avatar_url=None,
        party_member=PartyMember(
            id="wizard",
            name="Wizard",
            owner="player-1",
            avatarUrl=None,
            maxHp=20,
            abilityScores=AbilityScores(10, 10, 4, 10, 10, 10),
            sheet=PartyMemberSheet(classes=[CharacterClassLevel(ClassType.WIZARD, 2)]),
        ),
        current_hp=10,
        resource_overrides={},
    )
    monkeypatch.setattr("dnd_board.rules.rest.random.randint", lambda _minimum, _maximum: 1)

    hp, results = roll_hit_dice_for_rest(sheet, [HitDieSpend(ResourceId.HIT_DIE_D6, 2)])

    assert hp == 12
    assert results[0].rolls == (1, 1)
    assert results[0].healing == 2
    assert results[0].remaining == 0
    with pytest.raises(ValueError, match="only 2"):
        roll_hit_dice_for_rest(sheet, [HitDieSpend(ResourceId.HIT_DIE_D6, 3)])
    with pytest.raises(ValueError, match="does not have"):
        roll_hit_dice_for_rest(sheet, [HitDieSpend(ResourceId.SECOND_WIND, 1)])
