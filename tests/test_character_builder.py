import json

import pytest
from fastapi.testclient import TestClient

from dnd_board import server
from dnd_board.character_builder import (
    AbilityScoreGenerationMethod,
    CharacterBuilderOptionField,
    CharacterBuilderPayloadField,
    build_party_member_config,
    character_builder_options,
    character_builder_request_from_payload,
    fixed_hit_point_increases,
    fixed_max_hp,
    option_key,
    payload_key,
    selected_tool_from_payload,
)
from dnd_board.character_sheet import AbilityScores, AbilityType, ClassType, DamageType, EquipmentType, PartyManifest, ProficiencyLevel, RestType, SkillType, SpellId, SpellSource, enum_key, enum_label, typed_json_to_value
from dnd_board.rules.backgrounds import BackgroundEquipmentChoice, BackgroundFeatureType, BackgroundType, ToolType, background_definition, background_equipment, background_feats, background_skill_proficiencies, background_tool_options
from dnd_board.rules.feats import GeneralFeatType
from dnd_board.rules.progression import ProgressionChoiceId
from dnd_board.rules.species import SpeciesTraitType, SpeciesType


def setup_function() -> None:
    server.rooms.clear()


def test_character_builder_options_expose_creation_labels_and_background_details() -> None:
    options = character_builder_options()
    race_options = options[option_key(CharacterBuilderOptionField.RACES)]
    background_options = options[option_key(CharacterBuilderOptionField.BACKGROUNDS)]
    background_details = options[option_key(CharacterBuilderOptionField.BACKGROUND_DETAILS)]
    tool_details = options[option_key(CharacterBuilderOptionField.TOOL_DETAILS)]

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
        {"value": enum_key(AbilityType.STRENGTH), "label": "Strength"},
        {"value": enum_key(AbilityType.DEXTERITY), "label": "Dexterity"},
        {"value": enum_key(AbilityType.INTELLIGENCE), "label": "Intelligence"},
    ]
    sage_spell_choices = background_details[enum_key(BackgroundType.SAGE)]["magicInitiateSpellChoices"]
    criminal_spell_choices = background_details[enum_key(BackgroundType.CRIMINAL)]["magicInitiateSpellChoices"]
    assert sage_spell_choices["spellList"] == "Wizard"
    assert sage_spell_choices["cantripsKnown"] == 2
    assert sage_spell_choices["firstLevelSpellsKnown"] == 1
    assert {"value": enum_key(SpellId.MAGE_HAND), "label": "Mage Hand", "school": "conjuration", "level": 0, "castingTime": "action", "castingTimeLabel": "Action", "range": "30 ft", "duration": "1 minute", "components": ["Verbal", "Somatic"]} in sage_spell_choices["cantrips"]
    assert any(option["value"] == enum_key(SpellId.MAGIC_MISSILE) for option in sage_spell_choices["firstLevelSpells"])
    assert criminal_spell_choices is None
    assert tool_details[enum_key(ToolType.THIEVES_TOOLS)]["ability"] == enum_key(AbilityType.DEXTERITY)
    assert tool_details[enum_key(ToolType.THIEVES_TOOLS)]["utilizeActions"] == [
        {"description": "Pick a lock", "dc": 15},
        {"description": "Disarm a trap", "dc": 15},
    ]
    assert tool_details[enum_key(ToolType.POISONERS_KIT)]["craftOutputs"] == ["Basic Poison"]


def test_all_2024_background_definitions_are_populated() -> None:
    for background_type in BackgroundType:
        definition = background_definition(background_type)

        assert len(definition.abilityScores) == 3
        assert len(definition.skillProficiencies) == 2
        assert definition.feat is not None
        assert definition.toolProficiency is not None
        assert definition.equipmentPackage
        assert background_skill_proficiencies(background_type)
        assert background_tool_options(background_type)
        assert background_feats(background_type)
        assert background_equipment(background_type, BackgroundEquipmentChoice.PACKAGE)


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
    assert member.sheet.equipment
    equipment = {item.name: item for item in member.sheet.equipment}
    assert equipment["Dagger"].quantity == 2
    assert equipment["Dagger"].itemType == EquipmentType.WEAPON
    assert equipment["Thieves' Tools"].name == "Thieves' Tools"
    assert equipment["Crowbar"].quantity == 1
    assert "GP" not in equipment
    assert member.sheet.purse.gold == 16
    assert member.sheet.purse.silver == 0
    assert member.sheet.purse.copper == 0


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
    assert member.sheet.equipment is None
    assert member.sheet.purse.gold == 50
    assert member.sheet.purse.silver == 0
    assert member.sheet.purse.copper == 0


def test_character_builder_adds_magic_initiate_spells_from_background() -> None:
    request = character_builder_request_from_payload(
        {
            payload_key(CharacterBuilderPayloadField.CLASS_NAME): enum_key(ClassType.ROGUE),
            payload_key(CharacterBuilderPayloadField.RACE): enum_key(SpeciesType.HUMAN),
            payload_key(CharacterBuilderPayloadField.BACKGROUND): enum_key(BackgroundType.SAGE),
            payload_key(CharacterBuilderPayloadField.BASE_ABILITY_SCORES): {
                enum_key(AbilityType.STRENGTH): 8,
                enum_key(AbilityType.DEXTERITY): 15,
                enum_key(AbilityType.CONSTITUTION): 14,
                enum_key(AbilityType.INTELLIGENCE): 13,
                enum_key(AbilityType.WISDOM): 10,
                enum_key(AbilityType.CHARISMA): 12,
            },
            payload_key(CharacterBuilderPayloadField.BACKGROUND_ABILITY_INCREASES): {
                enum_key(AbilityType.INTELLIGENCE): 2,
                enum_key(AbilityType.WISDOM): 1,
            },
            payload_key(CharacterBuilderPayloadField.MAGIC_INITIATE_SPELLS): [
                enum_key(SpellId.MAGE_HAND),
                enum_key(SpellId.PRESTIDIGITATION),
                enum_key(SpellId.MAGIC_MISSILE),
            ],
        },
        default_member_id="player-1",
        default_owner="player-1",
    )
    member = build_party_member_config(request)

    assert request.magic_initiate_spells == (SpellId.MAGE_HAND, SpellId.PRESTIDIGITATION, SpellId.MAGIC_MISSILE)
    assert member.sheet.spells is not None
    spells = {spell.id: spell for spell in member.sheet.spells}
    assert set(spells) == {SpellId.MAGE_HAND, SpellId.PRESTIDIGITATION, SpellId.MAGIC_MISSILE}
    assert all(spell.source == SpellSource.MAGIC_INITIATE for spell in spells.values())
    assert all(spell.castingAbility == AbilityType.INTELLIGENCE for spell in spells.values())
    assert spells[SpellId.MAGE_HAND].resourceId is None
    assert spells[SpellId.PRESTIDIGITATION].resourceId is None
    assert spells[SpellId.MAGIC_MISSILE].resourceId == "magicInitiateMagicMissileFreeCast"
    assert spells[SpellId.MAGIC_MISSILE].reset == RestType.LONG_REST
    assert member.sheet.resources is not None
    assert [(resource.id, resource.currentUses, resource.maxUses, resource.reset) for resource in member.sheet.resources] == [
        ("magicInitiateMagicMissileFreeCast", 1, 1, RestType.LONG_REST)
    ]


def test_character_builder_rejects_invalid_magic_initiate_spells() -> None:
    base_payload = {
        payload_key(CharacterBuilderPayloadField.CLASS_NAME): enum_key(ClassType.ROGUE),
        payload_key(CharacterBuilderPayloadField.RACE): enum_key(SpeciesType.HUMAN),
        payload_key(CharacterBuilderPayloadField.BACKGROUND): enum_key(BackgroundType.ACOLYTE),
        payload_key(CharacterBuilderPayloadField.BASE_ABILITY_SCORES): {
            enum_key(AbilityType.STRENGTH): 8,
            enum_key(AbilityType.DEXTERITY): 15,
            enum_key(AbilityType.CONSTITUTION): 14,
            enum_key(AbilityType.INTELLIGENCE): 13,
            enum_key(AbilityType.WISDOM): 10,
            enum_key(AbilityType.CHARISMA): 12,
        },
        payload_key(CharacterBuilderPayloadField.BACKGROUND_ABILITY_INCREASES): {
            enum_key(AbilityType.INTELLIGENCE): 1,
            enum_key(AbilityType.WISDOM): 2,
        },
    }
    wrong_type = {**base_payload, payload_key(CharacterBuilderPayloadField.MAGIC_INITIATE_SPELLS): "bad"}
    wrong_spell = {**base_payload, payload_key(CharacterBuilderPayloadField.MAGIC_INITIATE_SPELLS): ["not-a-spell"]}
    duplicate_spell = {**base_payload, payload_key(CharacterBuilderPayloadField.MAGIC_INITIATE_SPELLS): [enum_key(SpellId.GUIDANCE), enum_key(SpellId.GUIDANCE), enum_key(SpellId.CURE_WOUNDS)]}
    wrong_list = {**base_payload, payload_key(CharacterBuilderPayloadField.MAGIC_INITIATE_SPELLS): [enum_key(SpellId.MAGE_HAND), enum_key(SpellId.LIGHT), enum_key(SpellId.CURE_WOUNDS)]}
    wrong_count = {**base_payload, payload_key(CharacterBuilderPayloadField.MAGIC_INITIATE_SPELLS): [enum_key(SpellId.GUIDANCE), enum_key(SpellId.CURE_WOUNDS)]}

    for payload in (wrong_type, wrong_spell, duplicate_spell, wrong_list, wrong_count):
        try:
            character_builder_request_from_payload(payload, default_member_id="player-1", default_owner="player-1")
        except ValueError as error:
            assert "Magic Initiate" in str(error)
        else:
            raise AssertionError("Expected invalid Magic Initiate spells to be rejected")


def test_character_builder_created_fighter_can_choose_class_skills(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(server, "CAMPAIGN_DIR", tmp_path)
    client = TestClient(server.app)
    create_response = client.post(
        "/api/rooms/fighter-skill-campaign/characters?playerKey=dm",
        json={
            payload_key(CharacterBuilderPayloadField.MEMBER_ID): "player-5",
            payload_key(CharacterBuilderPayloadField.NAME): "Goliath Fighter",
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
        },
    )

    assert create_response.status_code == 200
    created_sheet = next(sheet for sheet in create_response.json()["sheets"] if sheet["id"] == "player-5")
    assert created_sheet["pendingChoices"][0]["id"] == ProgressionChoiceId.FIGHTER_SKILL_PROFICIENCIES.value
    assert created_sheet["pendingChoices"][0]["choiceType"] == "skillProficiencies"
    assert created_sheet["pendingChoices"][0]["minimum"] == 2
    assert created_sheet["pendingChoices"][0]["maximum"] == 2
    assert created_sheet["pendingChoices"][0]["selected"] == [enum_key(SkillType.ANIMAL_HANDLING)]

    skill_response = client.post(
        f"/api/rooms/fighter-skill-campaign/sheet/player-5/choices/{ProgressionChoiceId.FIGHTER_SKILL_PROFICIENCIES.value}?playerKey=dm",
        json={"values": [enum_key(SkillType.ANIMAL_HANDLING), enum_key(SkillType.ATHLETICS)]},
    )

    assert skill_response.status_code == 200
    skill_sheet = skill_response.json()["sheet"]
    skill_proficiencies = {skill["name"]: skill["proficiency"] for skill in skill_sheet["skills"]}
    assert skill_proficiencies[enum_key(SkillType.ANIMAL_HANDLING)] == "proficient"
    assert skill_proficiencies[enum_key(SkillType.ATHLETICS)] == "proficient"
    assert skill_sheet["pendingChoices"][0]["id"] == ProgressionChoiceId.FIGHTER_FIGHTING_STYLES.value


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
    assert sheet["pendingChoices"][0]["id"] == ProgressionChoiceId.ROGUE_SKILL_PROFICIENCIES.value
    assert sheet["pendingChoices"][0]["choiceType"] == "skillProficiencies"
    assert sheet["pendingChoices"][0]["minimum"] == 4
    assert sheet["pendingChoices"][0]["maximum"] == 4
    assert sheet["pendingChoices"][0]["selected"] == [enum_key(SkillType.SLEIGHT_OF_HAND), enum_key(SkillType.STEALTH)]

    manifest_path = tmp_path / "builder-campaign" / "party" / "party.json"
    manifest = typed_json_to_value(json.loads(manifest_path.read_text(encoding="utf-8")), PartyManifest)
    assert manifest.members[0].id == "player-5"
    assert manifest.members[0].sheet.classes[0].name == ClassType.ROGUE


def test_character_builder_created_rogue_can_choose_class_skills_and_expertise(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(server, "CAMPAIGN_DIR", tmp_path)
    client = TestClient(server.app)
    create_response = client.post(
        "/api/rooms/rogue-skill-campaign/characters?playerKey=dm",
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

    assert create_response.status_code == 200
    skill_response = client.post(
        f"/api/rooms/rogue-skill-campaign/sheet/player-5/choices/{ProgressionChoiceId.ROGUE_SKILL_PROFICIENCIES.value}?playerKey=dm",
        json={"values": [enum_key(SkillType.SLEIGHT_OF_HAND), enum_key(SkillType.STEALTH), enum_key(SkillType.PERCEPTION), enum_key(SkillType.INVESTIGATION)]},
    )

    assert skill_response.status_code == 200
    skill_sheet = skill_response.json()["sheet"]
    assert skill_sheet["pendingChoices"][0]["id"] == ProgressionChoiceId.ROGUE_EXPERTISE.value
    assert skill_sheet["pendingChoices"][0]["choiceType"] == "expertise"
    assert skill_sheet["pendingChoices"][0]["minimum"] == 2
    assert skill_sheet["pendingChoices"][0]["maximum"] == 2
    assert {option["value"] for option in skill_sheet["pendingChoices"][0]["options"]} >= {enum_key(SkillType.SLEIGHT_OF_HAND), enum_key(SkillType.STEALTH), enum_key(SkillType.PERCEPTION), enum_key(SkillType.INVESTIGATION)}

    expertise_response = client.post(
        f"/api/rooms/rogue-skill-campaign/sheet/player-5/choices/{ProgressionChoiceId.ROGUE_EXPERTISE.value}?playerKey=dm",
        json={"values": [enum_key(SkillType.STEALTH), enum_key(SkillType.PERCEPTION)]},
    )

    assert expertise_response.status_code == 200
    expertise_sheet = expertise_response.json()["sheet"]
    skill_proficiencies = {skill["name"]: skill["proficiency"] for skill in expertise_sheet["skills"]}
    assert skill_proficiencies[enum_key(SkillType.STEALTH)] == "expertise"
    assert skill_proficiencies[enum_key(SkillType.PERCEPTION)] == "expertise"
    assert skill_proficiencies[enum_key(SkillType.INVESTIGATION)] == "proficient"
    assert expertise_sheet["pendingChoices"] == []


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
    skill_response = client.post(
        f"/api/rooms/builder-level-campaign/sheet/player-5/choices/{ProgressionChoiceId.ROGUE_SKILL_PROFICIENCIES.value}?playerKey=dm",
        json={"values": [enum_key(SkillType.SLEIGHT_OF_HAND), enum_key(SkillType.STEALTH), enum_key(SkillType.PERCEPTION), enum_key(SkillType.INVESTIGATION)]},
    )
    expertise_response = client.post(
        f"/api/rooms/builder-level-campaign/sheet/player-5/choices/{ProgressionChoiceId.ROGUE_EXPERTISE.value}?playerKey=dm",
        json={"values": [enum_key(SkillType.STEALTH), enum_key(SkillType.PERCEPTION)]},
    )
    leveled = client.post("/api/rooms/builder-level-campaign/sheet/player-5/level?playerKey=dm&delta=1&className=rogue")

    assert created.status_code == 200
    assert duplicate.status_code == 400
    assert duplicate.json()["detail"] == "That player slot is already in the game"
    assert skill_response.status_code == 200
    assert expertise_response.status_code == 200
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


def valid_character_builder_payload() -> dict:
    return {
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


@pytest.mark.parametrize(
    ("mutator", "message"),
    [
        (lambda payload: payload.update({payload_key(CharacterBuilderPayloadField.BASE_ABILITY_SCORES): []}), "Assign base scores"),
        (lambda payload: payload[payload_key(CharacterBuilderPayloadField.BASE_ABILITY_SCORES)].update({enum_key(AbilityType.STRENGTH): "bad"}), "Assign base scores"),
        (lambda payload: payload.update({payload_key(CharacterBuilderPayloadField.ABILITY_SCORE_METHOD): enum_key(AbilityScoreGenerationMethod.POINT_BUY), payload_key(CharacterBuilderPayloadField.BASE_ABILITY_SCORES): {enum_key(ability): 16 for ability in AbilityType}}), "between 8 and 15"),
        (lambda payload: payload.update({payload_key(CharacterBuilderPayloadField.ABILITY_SCORE_METHOD): enum_key(AbilityScoreGenerationMethod.RANDOM), payload_key(CharacterBuilderPayloadField.ROLLED_ABILITY_SCORES): "bad"}), "rolled score pool"),
        (lambda payload: payload.update({payload_key(CharacterBuilderPayloadField.ABILITY_SCORE_METHOD): enum_key(AbilityScoreGenerationMethod.RANDOM), payload_key(CharacterBuilderPayloadField.ROLLED_ABILITY_SCORES): ["bad"] * 6}), "valid rolled values"),
        (lambda payload: payload.update({payload_key(CharacterBuilderPayloadField.ABILITY_SCORE_METHOD): enum_key(AbilityScoreGenerationMethod.RANDOM), payload_key(CharacterBuilderPayloadField.ROLLED_ABILITY_SCORES): [19, 14, 13, 12, 10, 8]}), "six scores"),
        (lambda payload: payload.update({payload_key(CharacterBuilderPayloadField.BACKGROUND_ABILITY_INCREASES): []}), "Choose background ability"),
        (lambda payload: payload.update({payload_key(CharacterBuilderPayloadField.BACKGROUND_ABILITY_INCREASES): {enum_key(AbilityType.DEXTERITY): "bad"}}), "Choose valid background ability"),
        (lambda payload: payload.update({payload_key(CharacterBuilderPayloadField.BACKGROUND_ABILITY_INCREASES): {enum_key(AbilityType.DEXTERITY): 3}}), "0, 1, or 2"),
        (lambda payload: payload.update({payload_key(CharacterBuilderPayloadField.BACKGROUND_ABILITY_INCREASES): {enum_key(AbilityType.DEXTERITY): 1}}), "Background ability increases"),
    ],
)
def test_character_builder_validation_error_branches(mutator, message) -> None:
    payload = valid_character_builder_payload()
    mutator(payload)

    with pytest.raises(ValueError, match=message):
        character_builder_request_from_payload(payload, default_member_id="player-1", default_owner="player-1")


def test_character_builder_non_magic_background_ignores_magic_initiate_payload_and_defaults() -> None:
    payload = valid_character_builder_payload()
    payload[payload_key(CharacterBuilderPayloadField.MAGIC_INITIATE_SPELLS)] = ["not-a-spell"]
    request = character_builder_request_from_payload(payload, default_member_id="player-1", default_owner="player-1")

    assert request.magic_initiate_spells == ()


def test_character_builder_default_tool_and_fixed_hp_edge_branches(monkeypatch) -> None:
    monkeypatch.setattr("dnd_board.character_builder.background_tool_options", lambda _background: ())

    assert selected_tool_from_payload(BackgroundType.CRIMINAL, enum_key(ToolType.THIEVES_TOOLS)) is None
    assert fixed_hit_point_increases(ClassType.ROGUE, 3, AbilityScores(8, 14, 12, 10, 10, 10)) == [6, 6]
