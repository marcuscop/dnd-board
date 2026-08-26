from dnd_board.character_sheet import (
    AbilityScores,
    CharacterClassLevel,
    ClassType,
    FightingStyleType,
    PartyMember,
    PartyManifest,
    PartyMemberConfig,
    PartyMemberSheet,
    TokenKind,
    build_character_sheet,
    typed_json_from_value,
    party_manifest_from_dict,
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


def test_fighting_style_defense_adds_armor_class_and_feature() -> None:
    sheet = fighter_sheet(1, fighting_style=FightingStyleType.DEFENSE)
    features = {feature.id: feature for feature in sheet.features}

    assert sheet.armorClass == 14
    assert features["defense"].source == "Fighting Style"
    assert "+1 bonus to Armor Class" in features["defense"].description


def test_fighting_style_interception_adds_rollable_ability() -> None:
    sheet = fighter_sheet(1, fighting_style=FightingStyleType.INTERCEPTION)
    abilities = {ability.id: ability for ability in sheet.abilities}

    assert "interception" in abilities
    assert abilities["interception"].activation == abilities["interception"].activation.REACTION
    assert abilities["interception"].rollActions
    assert abilities["interception"].rollActions[0].modifier.name == "PROFICIENCY_BONUS"


def test_fighter_can_have_multiple_fighting_styles() -> None:
    sheet = build_character_sheet(
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
            maxHp=12,
            abilityScores=AbilityScores(strength=16, dexterity=12, constitution=14, intelligence=10, wisdom=10, charisma=10),
            sheet=PartyMemberSheet(
                classes=[
                    CharacterClassLevel(
                        name=ClassType.FIGHTER,
                        level=7,
                        subclass=FighterSubclassType.CHAMPION,
                        fightingStyles=[FightingStyleType.DEFENSE, FightingStyleType.INTERCEPTION],
                    )
                ]
            ),
        ),
        current_hp=None,
        resource_overrides={},
    )
    features = {feature.id: feature for feature in sheet.features}
    abilities = {ability.id: ability for ability in sheet.abilities}

    assert sheet.armorClass == 14
    assert {"defense", "interception"} <= features.keys()
    assert "interception" in abilities


def test_typed_party_manifest_round_trips_config_objects() -> None:
    manifest = PartyManifest(
        members=[
            PartyMemberConfig(
                id="player-1",
                name="Marina",
                maxHp=31,
                abilityScores=AbilityScores(strength=16, dexterity=14, constitution=15, intelligence=10, wisdom=12, charisma=8),
                sheet=PartyMemberSheet(
                    classes=[
                        CharacterClassLevel(
                            name=ClassType.FIGHTER,
                            level=7,
                            subclass=FighterSubclassType.CHAMPION,
                            fightingStyles=[FightingStyleType.DEFENSE, FightingStyleType.INTERCEPTION],
                        )
                    ]
                ),
            )
        ]
    )

    loaded = party_manifest_from_dict(typed_json_from_value(manifest))

    assert loaded is not None
    assert loaded.members[0].sheet is not None
    assert loaded.members[0].sheet.classes is not None
    assert loaded.members[0].sheet.classes[0].name == ClassType.FIGHTER
    assert loaded.members[0].sheet.classes[0].subclass == FighterSubclassType.CHAMPION
    assert loaded.members[0].sheet.classes[0].fightingStyles == [FightingStyleType.DEFENSE, FightingStyleType.INTERCEPTION]


def test_untyped_party_member_sheet_is_not_loaded() -> None:
    assert party_manifest_from_dict({"members": []}) is None


def test_typed_party_manifest_rejects_mismatched_field_type() -> None:
    loaded = party_manifest_from_dict(
        {
            "$type": "PartyManifest",
            "fields": {
                "members": {
                    "$type": "list",
                    "items": [
                        {
                            "$type": "PartyMemberConfig",
                            "fields": {
                                "id": {"$type": "str", "value": "player-1"},
                                "name": {"$type": "str", "value": "Marina"},
                                "maxHp": {"$type": "str", "value": "31"},
                            },
                        }
                    ],
                }
            },
        }
    )

    assert loaded is not None
    assert loaded.members[0].maxHp is None


def fighter_sheet(level: int, subclass: FighterSubclassType | None = None, fighting_style: FightingStyleType = FightingStyleType.DEFENSE):
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
            maxHp=12,
            abilityScores=AbilityScores(strength=16, dexterity=12, constitution=14, intelligence=10, wisdom=10, charisma=10),
            sheet=PartyMemberSheet(
                classes=[
                    CharacterClassLevel(
                        name=ClassType.FIGHTER,
                        level=level,
                        subclass=subclass,
                        fightingStyle=fighting_style,
                    )
                ]
            ),
        ),
        current_hp=None,
        resource_overrides={},
    )
