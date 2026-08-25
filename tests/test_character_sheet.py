from dnd_board.character_sheet import (
    AbilityScores,
    CharacterClassLevel,
    ClassType,
    FightingStyleType,
    PartyMember,
    PartyMemberSheet,
    build_character_sheet,
)
from dnd_board.rules.fighter import FighterSubclassType


def test_fighter_progression_resources_level_1_to_20() -> None:
    cases = {
        1: {"secondWind": 2},
        4: {"secondWind": 3, "actionSurge": 1},
        9: {"secondWind": 3, "actionSurge": 1, "indomitable": 1},
        10: {"secondWind": 4, "actionSurge": 1, "indomitable": 1},
        12: {"secondWind": 4, "actionSurge": 1, "indomitable": 1},
        13: {"secondWind": 4, "actionSurge": 1, "indomitable": 2},
        17: {"secondWind": 4, "actionSurge": 2, "indomitable": 3},
        20: {"secondWind": 4, "actionSurge": 2, "indomitable": 3},
    }

    for level, expected_resources in cases.items():
        sheet = fighter_sheet(level)

        assert {resource.id: resource.maxUses for resource in sheet.resources} == expected_resources


def test_fighter_progression_features_level_1_to_20() -> None:
    level_features = {
        1: {"fightingStyle", "secondWind", "weaponMastery"},
        2: {"actionSurge", "tacticalMind"},
        5: {"extraAttack", "tacticalShift"},
        9: {"indomitable", "tacticalMaster"},
        11: {"twoExtraAttacks"},
        12: {"abilityScoreImprovement"},
        13: {"studiedAttacks"},
        19: {"epicBoon"},
        20: {"threeExtraAttacks"},
    }

    for level, expected_features in level_features.items():
        feature_ids = {feature.id for feature in fighter_sheet(level).features}

        assert expected_features <= feature_ids


def test_champion_features_are_added_through_level_10() -> None:
    feature_ids = {feature.id for feature in fighter_sheet(10, subclass=FighterSubclassType.CHAMPION).features}

    assert {"improvedCritical", "remarkableAthlete", "additionalFightingStyle", "heroicWarrior"} <= feature_ids


def test_champion_features_are_added_through_level_20() -> None:
    feature_ids = {feature.id for feature in fighter_sheet(20, subclass=FighterSubclassType.CHAMPION).features}

    assert {"superiorCritical", "survivor"} <= feature_ids


def test_level_20_fighter_scaled_feature_text_uses_final_counts() -> None:
    features = {feature.id: feature for feature in fighter_sheet(20).features}

    assert "6 weapon choices" in features["weaponMastery"].description
    assert "4 times" in features["threeExtraAttacks"].description


def fighter_sheet(level: int, subclass: FighterSubclassType | None = None):
    return build_character_sheet(
        token_id="fighter",
        kind="character",
        name="Fighter",
        owner="player-1",
        avatar_url=None,
        party_member=PartyMember(
            id="fighter",
            name="Fighter",
            owner="player-1",
            avatarUrl=None,
            maxHp=12,
            abilityScores=AbilityScores(strength=16, dexterity=12, constitution=14, intelligence=10, wisdom=10, charisma=10),
            sheet=PartyMemberSheet(
                classes=[
                    CharacterClassLevel(
                        name=ClassType.FIGHTER,
                        level=level,
                        subclass=subclass,
                        fightingStyle=FightingStyleType.DEFENSE,
                    )
                ]
            ),
        ),
        current_hp=None,
        resource_overrides={},
    )
