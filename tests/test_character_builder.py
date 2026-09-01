import json

from fastapi.testclient import TestClient

from dnd_board import server
from dnd_board.character_builder import (
    AbilityScoreGenerationMethod,
    CharacterBuilderOptionField,
    CharacterBuilderPayloadField,
    build_party_member_config,
    character_builder_options,
    character_builder_request_from_payload,
    fixed_max_hp,
    option_key,
    payload_key,
)
from dnd_board.character_sheet import AbilityScores, AbilityType, ClassType, DamageType, PartyManifest, ProficiencyLevel, SkillType, enum_key, enum_label, typed_json_to_value
from dnd_board.rules.backgrounds import BackgroundEquipmentChoice, BackgroundFeatureType, BackgroundType, ToolType
from dnd_board.rules.feats import GeneralFeatType
from dnd_board.rules.species import SpeciesTraitType, SpeciesType


def setup_function() -> None:
    server.rooms.clear()


def test_character_builder_options_expose_creation_labels_and_background_details() -> None:
    options = character_builder_options()
    race_options = options[option_key(CharacterBuilderOptionField.RACES)]
    background_options = options[option_key(CharacterBuilderOptionField.BACKGROUNDS)]
    background_details = options[option_key(CharacterBuilderOptionField.BACKGROUND_DETAILS)]

    assert {"value": enum_key(ClassType.FIGHTER), "label": "Fighter"} in options[option_key(CharacterBuilderOptionField.CLASSES)]
    assert {"value": enum_key(ClassType.ROGUE), "label": "Rogue"} in options[option_key(CharacterBuilderOptionField.CLASSES)]
    assert len(race_options) == 24
    assert {"value": enum_key(SpeciesType.DWARF), "label": "Dwarf"} in race_options
    assert {"value": enum_key(SpeciesType.AASIMAR), "label": "Aasimar"} in race_options
    assert {"value": enum_key(SpeciesType.WARFORGED), "label": "Warforged"} in race_options
    assert {"value": enum_key(SpeciesType.LORWYN_CHANGELING), "label": "Lorwyn Changeling"} in race_options
    assert {"value": enum_key(SpeciesType.REBORN), "label": "Reborn"} in race_options
    assert len(background_options) == 61
    assert {"value": enum_key(BackgroundType.CRIMINAL), "label": "Criminal"} in background_options
    assert {"value": enum_key(BackgroundType.FARMER), "label": "Farmer"} in background_options
    assert {"value": enum_key(BackgroundType.HOUSE_CANNITH_HEIR), "label": "House Cannith Heir"} in background_options
    assert {"value": enum_key(BackgroundType.LORDS_ALLIANCE_VASSAL), "label": "Lords' Alliance Vassal"} in background_options
    assert {"value": enum_key(BackgroundType.VAMPIRE_SURVIVOR), "label": "Vampire Survivor"} in background_options
    assert options[option_key(CharacterBuilderOptionField.STANDARD_ARRAY)] == [15, 14, 13, 12, 10, 8]
    assert options[option_key(CharacterBuilderOptionField.POINT_BUY_POINTS)] == 27
    assert options[option_key(CharacterBuilderOptionField.POINT_BUY_COSTS)] == {8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 7, 15: 9}
    assert {"value": enum_key(AbilityScoreGenerationMethod.RANDOM), "label": "Random"} in options[option_key(CharacterBuilderOptionField.ABILITY_SCORE_METHODS)]
    assert background_details[enum_key(BackgroundType.CRIMINAL)]["abilityScores"] == [
        {"value": enum_key(AbilityType.DEXTERITY), "label": "Dexterity"},
        {"value": enum_key(AbilityType.CONSTITUTION), "label": "Constitution"},
        {"value": enum_key(AbilityType.INTELLIGENCE), "label": "Intelligence"},
    ]
    assert background_details[enum_key(BackgroundType.CRIMINAL)]["toolOptions"] == [{"value": enum_key(ToolType.THIEVES_TOOLS), "label": "Thieves' Tools"}]
    assert {"value": enum_key(ToolType.SMITHS_TOOLS), "label": "Smith's Tools"} in background_details[enum_key(BackgroundType.ARTISAN)]["toolOptions"]
    assert background_details[enum_key(BackgroundType.CRIMINAL)]["equipmentChoices"] == [
        {"value": enum_key(BackgroundEquipmentChoice.PACKAGE), "label": "Background Equipment"},
        {"value": enum_key(BackgroundEquipmentChoice.GOLD), "label": "50 GP"},
    ]
    assert background_details[enum_key(BackgroundType.HOUSE_CANNITH_HEIR)]["abilityScores"] == [
        {"value": enum_key(ability), "label": enum_label(ability)}
        for ability in AbilityType
    ]


def test_character_builder_builds_level_one_rogue_with_background_tool_and_package() -> None:
    request = character_builder_request_from_payload(
        {
            payload_key(CharacterBuilderPayloadField.MEMBER_ID): "player-2",
            payload_key(CharacterBuilderPayloadField.NAME): "Dwarf Rogue",
            payload_key(CharacterBuilderPayloadField.CLASS_NAME): enum_key(ClassType.ROGUE),
            payload_key(CharacterBuilderPayloadField.RACE): enum_key(SpeciesType.DWARF),
            payload_key(CharacterBuilderPayloadField.BACKGROUND): enum_key(BackgroundType.CRIMINAL),
            payload_key(CharacterBuilderPayloadField.BASE_ABILITY_SCORES): {
                enum_key(AbilityType.STRENGTH): 8,
                enum_key(AbilityType.DEXTERITY): 15,
                enum_key(AbilityType.CONSTITUTION): 14,
                enum_key(AbilityType.INTELLIGENCE): 13,
                enum_key(AbilityType.WISDOM): 10,
                enum_key(AbilityType.CHARISMA): 12,
            },
            payload_key(CharacterBuilderPayloadField.BACKGROUND_ABILITY_INCREASES): {
                enum_key(AbilityType.DEXTERITY): 2,
                enum_key(AbilityType.CONSTITUTION): 1,
            },
            payload_key(CharacterBuilderPayloadField.TOOL_PROFICIENCY): enum_key(ToolType.THIEVES_TOOLS),
            payload_key(CharacterBuilderPayloadField.EQUIPMENT_CHOICE): enum_key(BackgroundEquipmentChoice.PACKAGE),
        },
        default_member_id="player-1",
        default_owner="player-1",
    )
    member = build_party_member_config(request)

    assert request.race == SpeciesType.DWARF
    assert request.background == BackgroundType.CRIMINAL
    assert request.tool_proficiency == ToolType.THIEVES_TOOLS
    assert request.equipment_choice == BackgroundEquipmentChoice.PACKAGE
    assert member.id == "player-2"
    assert member.name == "Dwarf Rogue"
    assert member.abilityScores == AbilityScores(8, 17, 15, 13, 10, 12)
    assert member.maxHp == fixed_max_hp(ClassType.ROGUE, 1, AbilityScores(8, 17, 15, 13, 10, 12), SpeciesType.DWARF, BackgroundType.CRIMINAL)
    assert member.maxHp == 11
    assert member.sheet.race == "Dwarf"
    assert member.sheet.background == "Criminal"
    assert member.sheet.speed == 30
    assert member.sheet.skills == {enum_key(SkillType.SLEIGHT_OF_HAND): ProficiencyLevel.PROFICIENT, enum_key(SkillType.STEALTH): ProficiencyLevel.PROFICIENT}
    assert member.sheet.damageResistances == [DamageType.POISON]
    assert member.sheet.proficiencies == ["Thieves' Tools"]
    assert {trait.name for trait in member.sheet.traits or []} >= {enum_label(SpeciesTraitType.DARKVISION), enum_label(SpeciesTraitType.DWARVEN_RESILIENCE), enum_label(SpeciesTraitType.DWARVEN_TOUGHNESS), enum_label(SpeciesTraitType.STONECUNNING)}
    assert {feature.name for feature in member.sheet.features or []} == {enum_label(BackgroundFeatureType.TOOL_PROFICIENCY)}
    assert {feature.description for feature in member.sheet.features or []} == {"Gain proficiency with Thieves' Tools."}
    assert {feat.name for feat in member.sheet.feats or []} == {enum_label(GeneralFeatType.ALERT)}
    assert member.sheet.classes[0].name == ClassType.ROGUE
    assert member.sheet.classes[0].level == 1
    assert member.sheet.classes[0].subclass is None
    assert member.sheet.hitPointIncreases is None
    assert member.sheet.abilityScoreImprovements is None
    assert member.sheet.equipment and member.sheet.equipment[0].name == "Criminal Equipment Package"


def test_character_builder_applies_species_speed_background_tough_hp_and_gold() -> None:
    request = character_builder_request_from_payload(
        {
            payload_key(CharacterBuilderPayloadField.CLASS_NAME): enum_key(ClassType.FIGHTER),
            payload_key(CharacterBuilderPayloadField.RACE): enum_key(SpeciesType.GOLIATH),
            payload_key(CharacterBuilderPayloadField.BACKGROUND): enum_key(BackgroundType.FARMER),
            payload_key(CharacterBuilderPayloadField.BASE_ABILITY_SCORES): {
                enum_key(AbilityType.STRENGTH): 15,
                enum_key(AbilityType.DEXTERITY): 10,
                enum_key(AbilityType.CONSTITUTION): 14,
                enum_key(AbilityType.INTELLIGENCE): 8,
                enum_key(AbilityType.WISDOM): 13,
                enum_key(AbilityType.CHARISMA): 12,
            },
            payload_key(CharacterBuilderPayloadField.BACKGROUND_ABILITY_INCREASES): {
                enum_key(AbilityType.STRENGTH): 2,
                enum_key(AbilityType.CONSTITUTION): 1,
            },
            payload_key(CharacterBuilderPayloadField.EQUIPMENT_CHOICE): enum_key(BackgroundEquipmentChoice.GOLD),
        },
        default_member_id="player-1",
        default_owner="player-1",
    )
    member = build_party_member_config(request)

    assert member.abilityScores == AbilityScores(17, 10, 15, 8, 13, 12)
    assert member.maxHp == fixed_max_hp(ClassType.FIGHTER, 1, AbilityScores(17, 10, 15, 8, 13, 12), SpeciesType.GOLIATH, BackgroundType.FARMER)
    assert member.maxHp == 14
    assert member.sheet.speed == 35
    assert member.sheet.skills == {enum_key(SkillType.ANIMAL_HANDLING): ProficiencyLevel.PROFICIENT, enum_key(SkillType.NATURE): ProficiencyLevel.PROFICIENT}
    assert member.sheet.proficiencies == ["Carpenter's Tools"]
    assert {feat.name for feat in member.sheet.feats or []} == {enum_label(GeneralFeatType.TOUGH)}
    assert {trait.name for trait in member.sheet.traits or []} >= {enum_label(SpeciesTraitType.GIANT_ANCESTRY), enum_label(SpeciesTraitType.LARGE_FORM), enum_label(SpeciesTraitType.POWERFUL_BUILD)}
    assert member.sheet.equipment and member.sheet.equipment[0].name == "50 GP"
    assert member.sheet.equipment[0].quantity == 50


def test_character_builder_supports_point_buy_and_random_score_methods() -> None:
    point_buy_request = character_builder_request_from_payload(
        {
            payload_key(CharacterBuilderPayloadField.CLASS_NAME): enum_key(ClassType.ROGUE),
            payload_key(CharacterBuilderPayloadField.RACE): enum_key(SpeciesType.HUMAN),
            payload_key(CharacterBuilderPayloadField.BACKGROUND): enum_key(BackgroundType.WAYFARER),
            payload_key(CharacterBuilderPayloadField.ABILITY_SCORE_METHOD): enum_key(AbilityScoreGenerationMethod.POINT_BUY),
            payload_key(CharacterBuilderPayloadField.BASE_ABILITY_SCORES): {
                enum_key(AbilityType.STRENGTH): 8,
                enum_key(AbilityType.DEXTERITY): 15,
                enum_key(AbilityType.CONSTITUTION): 14,
                enum_key(AbilityType.INTELLIGENCE): 10,
                enum_key(AbilityType.WISDOM): 10,
                enum_key(AbilityType.CHARISMA): 8,
            },
            payload_key(CharacterBuilderPayloadField.BACKGROUND_ABILITY_INCREASES): {
                enum_key(AbilityType.DEXTERITY): 2,
                enum_key(AbilityType.WISDOM): 1,
            },
        },
        default_member_id="player-1",
        default_owner="player-1",
    )
    random_request = character_builder_request_from_payload(
        {
            payload_key(CharacterBuilderPayloadField.CLASS_NAME): enum_key(ClassType.FIGHTER),
            payload_key(CharacterBuilderPayloadField.RACE): enum_key(SpeciesType.HUMAN),
            payload_key(CharacterBuilderPayloadField.BACKGROUND): enum_key(BackgroundType.SOLDIER),
            payload_key(CharacterBuilderPayloadField.ABILITY_SCORE_METHOD): enum_key(AbilityScoreGenerationMethod.RANDOM),
            payload_key(CharacterBuilderPayloadField.ROLLED_ABILITY_SCORES): [16, 14, 14, 11, 10, 7],
            payload_key(CharacterBuilderPayloadField.BASE_ABILITY_SCORES): {
                enum_key(AbilityType.STRENGTH): 16,
                enum_key(AbilityType.DEXTERITY): 14,
                enum_key(AbilityType.CONSTITUTION): 14,
                enum_key(AbilityType.INTELLIGENCE): 11,
                enum_key(AbilityType.WISDOM): 10,
                enum_key(AbilityType.CHARISMA): 7,
            },
            payload_key(CharacterBuilderPayloadField.BACKGROUND_ABILITY_INCREASES): {
                enum_key(AbilityType.STRENGTH): 2,
                enum_key(AbilityType.CONSTITUTION): 1,
            },
        },
        default_member_id="player-1",
        default_owner="player-1",
    )

    assert point_buy_request.ability_score_method == AbilityScoreGenerationMethod.POINT_BUY
    assert point_buy_request.ability_scores == AbilityScores(8, 17, 14, 10, 11, 8)
    assert random_request.ability_score_method == AbilityScoreGenerationMethod.RANDOM
    assert random_request.ability_scores == AbilityScores(18, 14, 15, 11, 10, 7)


def test_character_builder_create_endpoint_writes_room_campaign_manifest(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(server, "CAMPAIGN_DIR", tmp_path)
    client = TestClient(server.app)

    response = client.post(
        "/api/rooms/builder-campaign/characters?playerKey=dm",
        json={
            payload_key(CharacterBuilderPayloadField.MEMBER_ID): "player-5",
            payload_key(CharacterBuilderPayloadField.NAME): "Dwarf Rogue",
            payload_key(CharacterBuilderPayloadField.CLASS_NAME): enum_key(ClassType.ROGUE),
            payload_key(CharacterBuilderPayloadField.RACE): enum_key(SpeciesType.DWARF),
            payload_key(CharacterBuilderPayloadField.BACKGROUND): enum_key(BackgroundType.CRIMINAL),
            payload_key(CharacterBuilderPayloadField.BASE_ABILITY_SCORES): {
                enum_key(AbilityType.STRENGTH): 8,
                enum_key(AbilityType.DEXTERITY): 15,
                enum_key(AbilityType.CONSTITUTION): 14,
                enum_key(AbilityType.INTELLIGENCE): 13,
                enum_key(AbilityType.WISDOM): 10,
                enum_key(AbilityType.CHARISMA): 12,
            },
            payload_key(CharacterBuilderPayloadField.BACKGROUND_ABILITY_INCREASES): {
                enum_key(AbilityType.DEXTERITY): 2,
                enum_key(AbilityType.CONSTITUTION): 1,
            },
        },
    )

    assert response.status_code == 200
    sheet = next(sheet for sheet in response.json()["sheets"] if sheet["id"] == "player-5")
    assert sheet["name"] == "Dwarf Rogue"
    assert sheet["race"] == "Dwarf"
    assert sheet["background"] == "Criminal"
    assert sheet["characterClass"] == {"name": "rogue", "nameLabel": "Rogue", "level": 1}
    assert "subclass" not in sheet["classes"][0]
    assert sheet["pendingChoices"] == []

    manifest_path = tmp_path / "builder-campaign" / "party" / "party.json"
    manifest = typed_json_to_value(json.loads(manifest_path.read_text(encoding="utf-8")), PartyManifest)
    assert manifest.members[0].id == "player-5"
    assert manifest.members[0].sheet.classes[0].name == ClassType.ROGUE


def test_player_slot_url_can_create_character_for_empty_slot(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(server, "CAMPAIGN_DIR", tmp_path)
    client = TestClient(server.app)

    response = client.post(
        "/api/rooms/player-slot-builder-campaign/characters?playerKey=player-7",
        json={
            payload_key(CharacterBuilderPayloadField.MEMBER_ID): "player-7",
            payload_key(CharacterBuilderPayloadField.NAME): "Player Seven",
            payload_key(CharacterBuilderPayloadField.CLASS_NAME): enum_key(ClassType.ROGUE),
            payload_key(CharacterBuilderPayloadField.RACE): enum_key(SpeciesType.DWARF),
            payload_key(CharacterBuilderPayloadField.BACKGROUND): enum_key(BackgroundType.CRIMINAL),
            payload_key(CharacterBuilderPayloadField.BASE_ABILITY_SCORES): {
                enum_key(AbilityType.STRENGTH): 8,
                enum_key(AbilityType.DEXTERITY): 15,
                enum_key(AbilityType.CONSTITUTION): 14,
                enum_key(AbilityType.INTELLIGENCE): 13,
                enum_key(AbilityType.WISDOM): 10,
                enum_key(AbilityType.CHARISMA): 12,
            },
            payload_key(CharacterBuilderPayloadField.BACKGROUND_ABILITY_INCREASES): {
                enum_key(AbilityType.DEXTERITY): 2,
                enum_key(AbilityType.CONSTITUTION): 1,
            },
        },
    )

    assert response.status_code == 200
    assert response.json()["playerKey"] == "player-7"
    sheet = next(sheet for sheet in response.json()["sheets"] if sheet["id"] == "player-7")
    assert sheet["name"] == "Player Seven"
    assert sheet["owner"] == "player-7"
    assert sheet["characterClass"] == {"name": "rogue", "nameLabel": "Rogue", "level": 1}


def test_character_builder_created_rogue_can_be_leveled_by_dm(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(server, "CAMPAIGN_DIR", tmp_path)
    client = TestClient(server.app)
    payload = {
        payload_key(CharacterBuilderPayloadField.MEMBER_ID): "player-5",
        payload_key(CharacterBuilderPayloadField.NAME): "Dwarf Rogue",
        payload_key(CharacterBuilderPayloadField.CLASS_NAME): enum_key(ClassType.ROGUE),
        payload_key(CharacterBuilderPayloadField.RACE): enum_key(SpeciesType.DWARF),
        payload_key(CharacterBuilderPayloadField.BACKGROUND): enum_key(BackgroundType.CRIMINAL),
        payload_key(CharacterBuilderPayloadField.BASE_ABILITY_SCORES): {
            enum_key(AbilityType.STRENGTH): 8,
            enum_key(AbilityType.DEXTERITY): 15,
            enum_key(AbilityType.CONSTITUTION): 14,
            enum_key(AbilityType.INTELLIGENCE): 13,
            enum_key(AbilityType.WISDOM): 10,
            enum_key(AbilityType.CHARISMA): 12,
        },
        payload_key(CharacterBuilderPayloadField.BACKGROUND_ABILITY_INCREASES): {
            enum_key(AbilityType.DEXTERITY): 2,
            enum_key(AbilityType.CONSTITUTION): 1,
        },
    }

    created = client.post("/api/rooms/builder-level-campaign/characters?playerKey=dm", json=payload)
    duplicate = client.post("/api/rooms/builder-level-campaign/characters?playerKey=dm", json=payload)
    leveled = client.post("/api/rooms/builder-level-campaign/sheet/player-5/level?playerKey=dm&delta=1&className=rogue")

    assert created.status_code == 200
    assert duplicate.status_code == 400
    assert duplicate.json()["detail"] == "That player slot is already in the game"
    assert leveled.status_code == 200
    sheet = leveled.json()["sheet"]
    assert sheet["characterClass"] == {"name": "rogue", "nameLabel": "Rogue", "level": 2}
    assert sheet["classes"] == [{"name": "rogue", "nameLabel": "Rogue", "level": 2}]


def test_character_builder_create_endpoint_limits_player_permissions(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(server, "CAMPAIGN_DIR", tmp_path)
    client = TestClient(server.app)

    forbidden = client.post("/api/rooms/builder-permission/characters?playerKey=player-1", json={payload_key(CharacterBuilderPayloadField.MEMBER_ID): "player-2", payload_key(CharacterBuilderPayloadField.NAME): "Other"})
    occupied_slot = client.post("/api/rooms/builder-permission/characters?playerKey=dm", json={payload_key(CharacterBuilderPayloadField.MEMBER_ID): "player-1", payload_key(CharacterBuilderPayloadField.NAME): "Existing"})
    invalid_slot = client.post("/api/rooms/builder-permission/characters?playerKey=dm", json={payload_key(CharacterBuilderPayloadField.MEMBER_ID): "not-a-player", payload_key(CharacterBuilderPayloadField.NAME): "Bad"})
    invalid_class = client.post("/api/rooms/builder-permission/characters?playerKey=dm", json={payload_key(CharacterBuilderPayloadField.MEMBER_ID): "player-5", payload_key(CharacterBuilderPayloadField.CLASS_NAME): "wizard"})

    assert forbidden.status_code == 403
    assert occupied_slot.status_code == 400
    assert occupied_slot.json()["detail"] == "That player slot is already in the game"
    assert invalid_slot.status_code == 400
    assert invalid_class.status_code == 400


def test_character_builder_rejects_invalid_standard_array_and_background_choices() -> None:
    base_payload = {
        payload_key(CharacterBuilderPayloadField.CLASS_NAME): enum_key(ClassType.ROGUE),
        payload_key(CharacterBuilderPayloadField.RACE): enum_key(SpeciesType.DWARF),
        payload_key(CharacterBuilderPayloadField.BACKGROUND): enum_key(BackgroundType.CRIMINAL),
        payload_key(CharacterBuilderPayloadField.BASE_ABILITY_SCORES): {
            enum_key(AbilityType.STRENGTH): 8,
            enum_key(AbilityType.DEXTERITY): 15,
            enum_key(AbilityType.CONSTITUTION): 14,
            enum_key(AbilityType.INTELLIGENCE): 13,
            enum_key(AbilityType.WISDOM): 10,
            enum_key(AbilityType.CHARISMA): 12,
        },
        payload_key(CharacterBuilderPayloadField.BACKGROUND_ABILITY_INCREASES): {
            enum_key(AbilityType.DEXTERITY): 2,
            enum_key(AbilityType.CONSTITUTION): 1,
        },
    }

    duplicate_standard_array = dict(base_payload)
    duplicate_standard_array[payload_key(CharacterBuilderPayloadField.BASE_ABILITY_SCORES)] = {
        **base_payload[payload_key(CharacterBuilderPayloadField.BASE_ABILITY_SCORES)],
        enum_key(AbilityType.CHARISMA): 10,
    }
    invalid_background_increase = dict(base_payload)
    invalid_background_increase[payload_key(CharacterBuilderPayloadField.BACKGROUND_ABILITY_INCREASES)] = {
        enum_key(AbilityType.DEXTERITY): 2,
        enum_key(AbilityType.WISDOM): 1,
    }
    invalid_tool = dict(base_payload)
    invalid_tool[payload_key(CharacterBuilderPayloadField.TOOL_PROFICIENCY)] = enum_key(ToolType.SMITHS_TOOLS)
    invalid_point_buy = dict(base_payload)
    invalid_point_buy[payload_key(CharacterBuilderPayloadField.ABILITY_SCORE_METHOD)] = enum_key(AbilityScoreGenerationMethod.POINT_BUY)
    invalid_point_buy[payload_key(CharacterBuilderPayloadField.BASE_ABILITY_SCORES)] = {
        enum_key(AbilityType.STRENGTH): 15,
        enum_key(AbilityType.DEXTERITY): 15,
        enum_key(AbilityType.CONSTITUTION): 15,
        enum_key(AbilityType.INTELLIGENCE): 15,
        enum_key(AbilityType.WISDOM): 15,
        enum_key(AbilityType.CHARISMA): 15,
    }
    invalid_random_assignment = dict(base_payload)
    invalid_random_assignment[payload_key(CharacterBuilderPayloadField.ABILITY_SCORE_METHOD)] = enum_key(AbilityScoreGenerationMethod.RANDOM)
    invalid_random_assignment[payload_key(CharacterBuilderPayloadField.ROLLED_ABILITY_SCORES)] = [16, 14, 14, 11, 10, 7]

    for payload in (duplicate_standard_array, invalid_background_increase, invalid_tool, invalid_point_buy, invalid_random_assignment):
        try:
            character_builder_request_from_payload(payload, default_member_id="player-1", default_owner="player-1")
        except ValueError:
            pass
        else:
            raise AssertionError("Expected invalid character builder payload to fail")
