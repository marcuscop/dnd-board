from types import SimpleNamespace

from dnd_board.character_sheet import (
    AbilityScores,
    AbilityType,
    ArcaneShotType,
    ArmorCategory,
    AttackRangeType,
    AttackAction,
    AttackActionType,
    AttackDamageAbilityModifierMode,
    AttackKind,
    BattleMasterManeuverType,
    CharacterClassLevel,
    ClassType,
    ConditionApplicationMode,
    DamageType,
    DiceType,
    EquipmentItem,
    EquipmentSlot,
    EquipmentType,
    FightingStyleType,
    PartyMember,
    PartyMemberSheet,
    RollModifierType,
    RollResolutionMode,
    TokenKind,
    RuneType,
    SpellCastingTime,
    SpellComponent,
    SpellDuration,
    SpellDurationUnit,
    SpellEntry,
    SpellId,
    SpellLineArea,
    SpellRadiusArea,
    SpellRangeType,
    SpellSchool,
    SpellSource,
    SpellTargeting,
    WeaponCategory,
    WeaponProperty,
    build_attack_roll_payload,
    build_character_sheet,
    build_damage_roll_payload,
    enum_key,
)
from dnd_board.rules.classes.fighter.base import FighterSubclassType
from dnd_board.rules.classes.fighter import archetypes as fighter_archetypes
from dnd_board.rules.classes.fighter.base import fighter_features, fighter_resources, subclass_description
from dnd_board.rules.feats import (
    FIGHTING_STYLE_FEATS,
    FeatEffect,
    FeatEffectType,
    GeneralFeatType,
    armor_class_bonus,
    armor_class_bonus_applies,
    attack_roll_bonus_applies,
    damage_ability_modifier_applies,
    damage_dice_reroll_applies,
    damage_roll_bonus_applies,
    feat_abilities,
    fighting_style_features,
    general_feat_feature,
    general_feat_prerequisites_met,
    parse_general_feat,
    selected_fighting_styles,
    selected_general_feat_keys,
)
from dnd_board.rules.classes.fighter.archetypes import (
    EldritchKnightSpellcastingProgression,
    FighterSubclassRollActionType,
    arcane_shot_roll_actions,
    eldritch_knight_catalog_spell,
    eldritch_knight_flexible_spell_limit,
    eldritch_knight_max_spell_level,
    fighter_subclass_abilities,
    giants_might_die,
    is_eldritch_knight_spell_selection_valid,
    pruned_eldritch_knight_spells,
    psionic_energy_die,
)
from dnd_board.rules.classes.fighter.battle_master import BATTLE_MASTER_2024_MANEUVERS, BATTLE_MASTER_MANEUVERS
from dnd_board.rules.classes.fighter.battle_master import battle_master_features
from dnd_board.rules.shared.combat_superiority import selected_battle_master_maneuvers


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
    sheet = fighter_sheet(1, fighting_style=FightingStyleType.DEFENSE, equipment=[chain_mail()])
    features = {feature.id: feature for feature in sheet.features}

    assert sheet.armorClass == 17
    assert features["defense"].source == "Fighting Style"
    assert "+1 bonus to Armor Class" in features["defense"].description


def test_fighting_style_defense_does_not_apply_without_worn_armor() -> None:
    sheet = fighter_sheet(1, fighting_style=FightingStyleType.DEFENSE)

    assert sheet.armorClass == 13


def test_fighting_style_interception_adds_rollable_ability() -> None:
    sheet = fighter_sheet(1, fighting_style=FightingStyleType.INTERCEPTION)
    abilities = {ability.id: ability for ability in sheet.abilities}

    assert "interception" in abilities
    assert abilities["interception"].activation == abilities["interception"].activation.REACTION
    assert abilities["interception"].rollActions
    assert abilities["interception"].rollActions[0].modifier.name == "PROFICIENCY_BONUS"


def test_all_fighting_styles_expose_sheet_entries() -> None:
    for fighting_style in FightingStyleType:
        sheet = fighter_sheet(1, fighting_style=fighting_style)
        sheet_entry_ids = {feature.id for feature in sheet.features} | {ability.id for ability in sheet.abilities} | {resource.id for resource in sheet.resources}

        assert any(entry_id == fighting_style_entry_id(fighting_style) for entry_id in sheet_entry_ids)


def test_fighting_style_helpers_ignore_duplicate_or_missing_definitions(monkeypatch) -> None:
    classes = [
        CharacterClassLevel(
            name=ClassType.FIGHTER,
            level=1,
            fightingStyle=FightingStyleType.DEFENSE,
            fightingStyles=[FightingStyleType.DEFENSE, FightingStyleType.INTERCEPTION, FightingStyleType.INTERCEPTION],
        )
    ]

    assert selected_fighting_styles(classes) == [FightingStyleType.DEFENSE, FightingStyleType.INTERCEPTION]

    monkeypatch.delitem(FIGHTING_STYLE_FEATS, FightingStyleType.DEFENSE)
    assert fighting_style_features(classes)[0].id == "interception"
    assert feat_abilities(classes)[0].id == "interception"
    assert armor_class_bonus(classes, [chain_mail()]) == 0


def test_general_feat_helpers_parse_duplicates_and_invalid_values() -> None:
    feats = [
        type("FeatStub", (), {"id": "alert"})(),
        type("FeatStub", (), {"id": "Alert"})(),
        type("FeatStub", (), {"id": "not-a-feat"})(),
    ]

    assert selected_general_feat_keys(feats) == ["alert"]
    assert general_feat_feature("alert").id == "alert"
    assert parse_general_feat("not-a-feat") is None
    assert general_feat_feature("not-a-feat") is None


def test_general_feat_prerequisites_are_structured_and_evaluable() -> None:
    dwarf_sheet = SimpleNamespace(
        race="Dwarf",
        background="Soldier",
        abilityScores=AbilityScores(12, 12, 12, 10, 10, 10),
        classes=[CharacterClassLevel(name=ClassType.FIGHTER, level=4)],
        proficiencies=["Light armor", "Martial Weapon"],
        feats=[],
        features=[],
        abilities=[],
        spells=[],
    )
    dragonborn_sheet = SimpleNamespace(
        race="Dragonborn",
        background="Criminal",
        abilityScores=AbilityScores(10, 14, 12, 10, 10, 10),
        classes=[CharacterClassLevel(name=ClassType.ROGUE, level=1)],
        proficiencies=[],
        feats=[],
        features=[],
        abilities=[],
        spells=[],
    )

    assert "Prerequisite: Dragonborn." in general_feat_feature("dragonFear").description
    assert "Prerequisite: Proficiency with Light armor." in general_feat_feature("moderatelyArmored").description
    assert "Prerequisite: Dexterity 13+." in general_feat_feature("defensiveDuelist").description
    assert "Prerequisite: Dwarf or Small." in general_feat_feature("squatNimbleness").description
    assert "Prerequisite: Level 4+, Strike Of The Giants Hill Strike." in general_feat_feature("vigorOfTheHillGiant").description
    assert general_feat_prerequisites_met(GeneralFeatType.SQUAT_NIMBLENESS, dwarf_sheet)
    assert general_feat_prerequisites_met(GeneralFeatType.MODERATELY_ARMORED, dwarf_sheet)
    assert not general_feat_prerequisites_met(GeneralFeatType.HEAVILY_ARMORED, dwarf_sheet)
    assert general_feat_prerequisites_met(GeneralFeatType.DEFENSIVE_DUELIST, dragonborn_sheet)
    assert general_feat_prerequisites_met(GeneralFeatType.DRAGON_FEAR, dragonborn_sheet)


def test_feat_predicates_return_false_for_unscoped_effects() -> None:
    attack = AttackAction(
        id="club",
        name="Club",
        ability=AbilityType.STRENGTH,
        damageDiceCount=1,
        damageDiceType=DiceType.D4,
    )
    unscoped_attack_bonus = FeatEffect(FeatEffectType.ATTACK_ROLL_BONUS)
    unscoped_damage_bonus = FeatEffect(FeatEffectType.DAMAGE_ROLL_BONUS)
    unscoped_damage_ability = FeatEffect(FeatEffectType.DAMAGE_ABILITY_MODIFIER)
    unscoped_dice_reroll = FeatEffect(FeatEffectType.DAMAGE_DICE_REROLL)

    assert attack_roll_bonus_applies(unscoped_attack_bonus, attack) is False
    assert damage_roll_bonus_applies(unscoped_damage_bonus, [], attack) is False
    assert damage_ability_modifier_applies(unscoped_damage_ability, attack) is False
    assert damage_dice_reroll_applies(unscoped_dice_reroll, attack) is False
    assert armor_class_bonus_applies(FightingStyleType.PROTECTION, []) is True


def test_fighting_style_archery_adds_attack_roll_bonus_with_breakdown(monkeypatch) -> None:
    monkeypatch.setattr("dnd_board.character_sheet.random.randint", lambda minimum, maximum: 4)
    sheet = fighter_sheet_with_attacks(
        FightingStyleType.ARCHERY,
        [
            AttackAction(
                id="longbow",
                name="Longbow",
                ability=AbilityType.DEXTERITY,
                damageDiceCount=1,
                damageDiceType=DiceType.D8,
                damageType=DamageType.PIERCING,
                attackRange=AttackRangeType.RANGED,
                weaponCategory=WeaponCategory.RANGED,
                properties=[WeaponProperty.AMMUNITION, WeaponProperty.TWO_HANDED],
            )
        ],
    )

    roll = build_attack_roll_payload(sheet, "player-1", sheet.attacks[0])

    assert roll.modifier == 6
    assert roll.total == 10
    assert [(part.source, part.value) for part in roll.modifierBreakdown] == [("Dexterity", 2), ("Archery", 2), ("Proficiency", 2)]


def test_automatic_fighting_styles_are_modeled_as_mechanical_effects() -> None:
    automatic_styles = {
        FightingStyleType.ARCHERY,
        FightingStyleType.CLOSE_QUARTERS_SHOOTER,
        FightingStyleType.DUELING,
        FightingStyleType.GREAT_WEAPON_FIGHTING,
        FightingStyleType.THROWN_WEAPON_FIGHTING,
        FightingStyleType.TWO_WEAPON_FIGHTING,
    }

    for style in automatic_styles:
        effect_types = {effect.effectType for effect in FIGHTING_STYLE_FEATS[style].effects}

        assert effect_types != {FeatEffectType.DESCRIPTION_ONLY}


def test_fighting_style_close_quarters_shooter_adds_attack_roll_bonus_with_breakdown(monkeypatch) -> None:
    monkeypatch.setattr("dnd_board.character_sheet.random.randint", lambda minimum, maximum: 4)
    sheet = fighter_sheet_with_attacks(
        FightingStyleType.CLOSE_QUARTERS_SHOOTER,
        [
            AttackAction(
                id="longbow",
                name="Longbow",
                ability=AbilityType.DEXTERITY,
                damageDiceCount=1,
                damageDiceType=DiceType.D8,
                damageType=DamageType.PIERCING,
                attackRange=AttackRangeType.RANGED,
                weaponCategory=WeaponCategory.RANGED,
                properties=[WeaponProperty.AMMUNITION, WeaponProperty.TWO_HANDED],
            )
        ],
    )

    roll = build_attack_roll_payload(sheet, "player-1", sheet.attacks[0])

    assert roll.modifier == 5
    assert roll.total == 9
    assert [(part.source, part.value) for part in roll.modifierBreakdown] == [("Dexterity", 2), ("Close Quarters Shooter", 1), ("Proficiency", 2)]


def test_fighting_style_archery_does_not_apply_to_thrown_melee_weapon(monkeypatch) -> None:
    monkeypatch.setattr("dnd_board.character_sheet.random.randint", lambda minimum, maximum: 4)
    sheet = fighter_sheet_with_attacks(
        FightingStyleType.ARCHERY,
        [
            AttackAction(
                id="thrown-handaxe",
                name="Thrown Handaxe",
                ability=AbilityType.STRENGTH,
                damageDiceCount=1,
                damageDiceType=DiceType.D6,
                damageType=DamageType.SLASHING,
                attackRange=AttackRangeType.RANGED,
                weaponCategory=WeaponCategory.MELEE,
                properties=[WeaponProperty.LIGHT, WeaponProperty.THROWN],
            )
        ],
    )

    roll = build_attack_roll_payload(sheet, "player-1", sheet.attacks[0])

    assert roll.modifier == 5
    assert [(part.source, part.value) for part in roll.modifierBreakdown] == [("Strength", 3), ("Proficiency", 2)]


def test_fighting_style_thrown_weapon_adds_damage_bonus_with_breakdown(monkeypatch) -> None:
    monkeypatch.setattr("dnd_board.character_sheet.random.randint", lambda minimum, maximum: 3)
    sheet = fighter_sheet_with_attacks(
        FightingStyleType.THROWN_WEAPON_FIGHTING,
        [
            AttackAction(
                id="handaxe",
                name="Handaxe",
                ability=AbilityType.STRENGTH,
                damageDiceCount=1,
                damageDiceType=DiceType.D6,
                damageType=DamageType.SLASHING,
                attackRange=AttackRangeType.RANGED,
                weaponCategory=WeaponCategory.MELEE,
                properties=[WeaponProperty.LIGHT, WeaponProperty.THROWN],
            )
        ],
    )

    roll = build_damage_roll_payload(sheet, "player-1", sheet.attacks[0])

    assert roll.modifier == 5
    assert roll.total == 8
    assert [(part.source, part.value) for part in roll.modifierBreakdown] == [("Strength", 3), ("Thrown Weapon Fighting", 2)]


def test_fighting_style_thrown_weapon_adds_sheet_attack() -> None:
    sheet = fighter_sheet(1, fighting_style=FightingStyleType.THROWN_WEAPON_FIGHTING)
    attack = next(attack for attack in sheet.attacks if attack.attackType == AttackActionType.THROWN_WEAPON)

    assert attack.id == "thrownWeapon"
    assert attack.attackRange == AttackRangeType.RANGED
    assert attack.weaponCategory == WeaponCategory.MELEE
    assert attack.properties == [WeaponProperty.THROWN]


def test_fighting_style_two_weapon_fighting_adds_missing_ability_modifier_to_bonus_attack(monkeypatch) -> None:
    monkeypatch.setattr("dnd_board.character_sheet.random.randint", lambda minimum, maximum: 3)
    sheet = fighter_sheet_with_attacks(
        FightingStyleType.TWO_WEAPON_FIGHTING,
        [
            AttackAction(
                id="off-hand-scimitar",
                name="Off-Hand Scimitar",
                ability=AbilityType.DEXTERITY,
                damageDiceCount=1,
                damageDiceType=DiceType.D6,
                damageType=DamageType.SLASHING,
                attackKind=AttackKind.TWO_WEAPON_FIGHTING,
                damageAbilityModifier=AttackDamageAbilityModifierMode.EXCLUDED,
                properties=[WeaponProperty.LIGHT, WeaponProperty.FINESSE],
            )
        ],
    )

    roll = build_damage_roll_payload(sheet, "player-1", sheet.attacks[0])

    assert roll.modifier == 2
    assert roll.total == 5
    assert [(part.source, part.value) for part in roll.modifierBreakdown] == [("Two Weapon Fighting", 2)]


def test_fighting_style_two_weapon_fighting_does_not_double_apply_ability_modifier(monkeypatch) -> None:
    monkeypatch.setattr("dnd_board.character_sheet.random.randint", lambda minimum, maximum: 3)
    sheet = fighter_sheet_with_attacks(
        FightingStyleType.TWO_WEAPON_FIGHTING,
        [
            AttackAction(
                id="off-hand-scimitar",
                name="Off-Hand Scimitar",
                ability=AbilityType.DEXTERITY,
                damageDiceCount=1,
                damageDiceType=DiceType.D6,
                damageType=DamageType.SLASHING,
                attackKind=AttackKind.TWO_WEAPON_FIGHTING,
                damageAbilityModifier=AttackDamageAbilityModifierMode.INCLUDED,
                properties=[WeaponProperty.LIGHT, WeaponProperty.FINESSE],
            )
        ],
    )

    roll = build_damage_roll_payload(sheet, "player-1", sheet.attacks[0])

    assert roll.modifier == 2
    assert roll.total == 5
    assert [(part.source, part.value) for part in roll.modifierBreakdown] == [("Dexterity", 2)]


def test_fighting_style_dueling_adds_damage_bonus_to_one_handed_melee_attacks(monkeypatch) -> None:
    monkeypatch.setattr("dnd_board.character_sheet.random.randint", lambda minimum, maximum: 5)
    sheet = fighter_sheet_with_attacks(
        FightingStyleType.DUELING,
        [
            AttackAction(
                id="longsword",
                name="Longsword",
                ability=AbilityType.STRENGTH,
                damageDiceCount=1,
                damageDiceType=DiceType.D8,
                damageType=DamageType.SLASHING,
                properties=[WeaponProperty.VERSATILE],
            )
        ],
    )
    sheet.equipment = [longsword(EquipmentSlot.MAIN_HAND)]

    roll = build_damage_roll_payload(sheet, "player-1", sheet.attacks[0])

    assert roll.modifier == 5
    assert roll.total == 10
    assert ("Dueling", 2) in [(part.source, part.value) for part in roll.modifierBreakdown]


def test_fighting_style_dueling_does_not_apply_when_off_hand_weapon_is_occupied(monkeypatch) -> None:
    monkeypatch.setattr("dnd_board.character_sheet.random.randint", lambda minimum, maximum: 5)
    sheet = fighter_sheet_with_attacks(
        FightingStyleType.DUELING,
        [
            AttackAction(
                id="longsword",
                name="Longsword",
                ability=AbilityType.STRENGTH,
                damageDiceCount=1,
                damageDiceType=DiceType.D8,
                damageType=DamageType.SLASHING,
                properties=[WeaponProperty.VERSATILE],
            )
        ],
        equipment=[longsword(EquipmentSlot.MAIN_HAND), EquipmentItem(id="shortsword", name="Shortsword", itemType=EquipmentType.WEAPON, slot=EquipmentSlot.OFF_HAND)],
    )

    roll = build_damage_roll_payload(sheet, "player-1", sheet.attacks[0])

    assert roll.modifier == 3
    assert [(part.source, part.value) for part in roll.modifierBreakdown] == [("Strength", 3)]


def test_fighting_style_great_weapon_fighting_treats_low_damage_dice_as_three(monkeypatch) -> None:
    monkeypatch.setattr("dnd_board.character_sheet.random.randint", lambda minimum, maximum: 1)
    sheet = fighter_sheet_with_attacks(
        FightingStyleType.GREAT_WEAPON_FIGHTING,
        [
            AttackAction(
                id="greatsword",
                name="Greatsword",
                ability=AbilityType.STRENGTH,
                damageDiceCount=1,
                damageDiceType=DiceType.D6,
                damageType=DamageType.SLASHING,
                properties=[WeaponProperty.HEAVY, WeaponProperty.TWO_HANDED],
            )
        ],
    )

    roll = build_damage_roll_payload(sheet, "player-1", sheet.attacks[0])

    assert roll.dice == [3]
    assert roll.total == 6
    assert any(part.source == "Great Weapon Fighting" for part in roll.modifierBreakdown)


def test_fighting_style_unarmed_adds_d8_attack_when_hands_are_empty() -> None:
    sheet = fighter_sheet(1, fighting_style=FightingStyleType.UNARMED_FIGHTING)
    attack = next(attack for attack in sheet.attacks if attack.attackType == AttackActionType.UNARMED_STRIKE)

    assert attack.id == "unarmedStrike"
    assert attack.damageDiceType == DiceType.D8


def test_fighting_style_unarmed_adds_d6_attack_when_wielding_weapon_or_shield() -> None:
    sheet = fighter_sheet(1, fighting_style=FightingStyleType.UNARMED_FIGHTING, equipment=[shield(EquipmentSlot.OFF_HAND)])
    attack = next(attack for attack in sheet.attacks if attack.attackType == AttackActionType.UNARMED_STRIKE)

    assert attack.damageDiceType == DiceType.D6


def test_fighting_style_unarmed_grapple_rider_is_targetable_damage() -> None:
    sheet = fighter_sheet(1, fighting_style=FightingStyleType.UNARMED_FIGHTING)
    unarmed_fighting = next(ability for ability in sheet.abilities if ability.id == "unarmedFighting")
    action = unarmed_fighting.rollActions[0]

    assert action.diceType == DiceType.D4
    assert action.resolution == RollResolutionMode.APPLY_DAMAGE
    assert action.damageType == DamageType.BLUDGEONING


def test_fighting_style_mariner_applies_without_heavy_armor_or_shield() -> None:
    sheet = fighter_sheet(1, fighting_style=FightingStyleType.MARINER, equipment=[leather_armor()])

    assert sheet.armorClass == 13


def test_fighting_style_mariner_does_not_apply_with_heavy_armor_or_shield() -> None:
    heavy_armor_sheet = fighter_sheet(1, fighting_style=FightingStyleType.MARINER, equipment=[chain_mail()])
    shield_sheet = fighter_sheet(1, fighting_style=FightingStyleType.MARINER, equipment=[leather_armor(), shield(EquipmentSlot.OFF_HAND)])

    assert heavy_armor_sheet.armorClass == 16
    assert shield_sheet.armorClass == 14


def test_configured_armor_class_is_static_base_for_conditional_style_bonuses() -> None:
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
                armorClass=18,
                classes=[
                    CharacterClassLevel(
                        name=ClassType.FIGHTER,
                        level=1,
                        fightingStyles=[FightingStyleType.DEFENSE, FightingStyleType.MARINER],
                    )
                ],
                equipment=[chain_mail(), shield(EquipmentSlot.OFF_HAND)],
            ),
        ),
        current_hp=None,
        resource_overrides={},
    )
    empty_hands_sheet = build_character_sheet(
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
                armorClass=18,
                classes=[
                    CharacterClassLevel(
                        name=ClassType.FIGHTER,
                        level=1,
                        fightingStyles=[FightingStyleType.DEFENSE, FightingStyleType.MARINER],
                    )
                ],
                equipment=[chain_mail(), shield(EquipmentSlot.OFF_HAND)],
            ),
        ),
        current_hp=None,
        resource_overrides={},
        equipment_slot_overrides={"chain-mail": EquipmentSlot.CARRIED, "shield": EquipmentSlot.CARRIED},
    )

    assert sheet.armorClass == 19
    assert empty_hands_sheet.armorClass == 19


def test_fighting_style_superior_technique_adds_short_rest_superiority_die() -> None:
    sheet = fighter_sheet(1, fighting_style=FightingStyleType.SUPERIOR_TECHNIQUE)
    effect_types = {effect.effectType for effect in FIGHTING_STYLE_FEATS[FightingStyleType.SUPERIOR_TECHNIQUE].effects}
    resources = {resource.id: resource for resource in sheet.resources}
    abilities = {ability.id: ability for ability in sheet.abilities}

    assert effect_types == {FeatEffectType.RESOURCE}
    assert "superiorityDice" in resources
    resource = resources["superiorityDice"]
    assert resource.currentUses == 1
    assert resource.maxUses == 1
    assert resource.reset.name == "SHORT_REST"
    assert len(resource.rollActions or []) == len(BATTLE_MASTER_2024_MANEUVERS)
    assert all(action.diceType == DiceType.D6 for action in resource.rollActions or [])
    assert all(action.consumesResource.name == "SUPERIORITY_DICE" for action in resource.rollActions or [])
    assert {"ambush", "tripAttack"} <= abilities.keys()
    assert abilities["ambush"].resourceId == "superiorityDice"
    assert abilities["ambush"].source == "Battle Master"
    assert abilities["rally"].activation.name == "BONUS_ACTION"


def test_fighting_style_superior_technique_can_select_one_maneuver() -> None:
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
                        level=1,
                        fightingStyle=FightingStyleType.SUPERIOR_TECHNIQUE,
                        maneuvers=[BattleMasterManeuverType.TRIP_ATTACK],
                    )
                ],
            ),
        ),
        current_hp=None,
        resource_overrides={},
    )
    resources = {resource.id: resource for resource in sheet.resources}
    abilities = {ability.id: ability for ability in sheet.abilities}

    assert resources["superiorityDice"].maxUses == 1
    assert resources["superiorityDice"].rollActions
    assert [action.id for action in resources["superiorityDice"].rollActions] == [BattleMasterManeuverType.TRIP_ATTACK]
    assert "tripAttack" in abilities
    assert "ambush" not in abilities


def test_resource_roll_abilities_use_parent_rule_source() -> None:
    sheet = fighter_sheet(2, fighting_style=FightingStyleType.INTERCEPTION)
    abilities = {ability.id: ability for ability in sheet.abilities}

    assert abilities["secondWindHeal"].source == "Fighter"
    assert abilities["tacticalMind"].source == "Fighter"
    assert abilities["interception"].source == "Fighting Style"


def test_battle_master_superior_technique_adds_one_scaled_superiority_die() -> None:
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
                        level=10,
                        subclass=FighterSubclassType.BATTLE_MASTER,
                        fightingStyle=FightingStyleType.SUPERIOR_TECHNIQUE,
                        maneuvers=[BattleMasterManeuverType.PRECISION_ATTACK],
                    )
                ],
            ),
        ),
        current_hp=None,
        resource_overrides={},
    )
    resources = {resource.id: resource for resource in sheet.resources}
    features = {feature.id: feature for feature in sheet.features}
    abilities = {ability.id: ability for ability in sheet.abilities}

    assert resources["superiorityDice"].maxUses == 6
    assert resources["superiorityDice"].rollActions
    assert resources["superiorityDice"].rollActions[0].diceType == DiceType.D10
    assert "precisionAttack" in abilities
    assert "tripAttack" not in abilities
    assert {"combatSuperiority", "studentOfWar", "knowYourEnemy", "improvedCombatSuperiority"} <= features.keys()


def test_battle_master_superiority_dice_scale_by_fighter_level() -> None:
    cases = {
        3: (4, DiceType.D8),
        7: (5, DiceType.D8),
        10: (5, DiceType.D10),
        15: (6, DiceType.D10),
        18: (6, DiceType.D12),
    }

    for level, (expected_count, expected_die) in cases.items():
        sheet = fighter_sheet(level, subclass=FighterSubclassType.BATTLE_MASTER)
        resource = next(resource for resource in sheet.resources if resource.id == "superiorityDice")

        assert resource.maxUses == expected_count
        assert resource.rollActions
        assert resource.rollActions[0].diceType == expected_die


def test_fighter_roll_actions_encode_condition_effects() -> None:
    battle_master = fighter_sheet(
        3,
        subclass=FighterSubclassType.BATTLE_MASTER,
        maneuvers=[
            BattleMasterManeuverType.GRAPPLING_STRIKE,
            BattleMasterManeuverType.MENACING_ATTACK,
            BattleMasterManeuverType.TRIP_ATTACK,
        ],
    )
    superiority = next(resource for resource in battle_master.resources if resource.id == "superiorityDice")
    actions = {action.id: action for action in superiority.rollActions or []}
    arcane_archer = fighter_sheet(
        3,
        subclass=FighterSubclassType.ARCANE_ARCHER,
        arcane_shots=[ArcaneShotType.BEGUILING_ARROW, ArcaneShotType.SHADOW_ARROW],
    )
    arcane_actions = {
        action.id: action
        for ability in arcane_archer.abilities
        for action in ability.rollActions or []
    }
    rune_knight = fighter_sheet(3, subclass=FighterSubclassType.RUNE_KNIGHT, runes=[RuneType.FIRE_RUNE])
    rune_actions = {
        action.id: action
        for ability in rune_knight.abilities
        for action in ability.rollActions or []
    }

    grappling_effect = actions[BattleMasterManeuverType.GRAPPLING_STRIKE].conditionEffects[0]
    assert grappling_effect.condition.name == "GRAPPLED"
    assert grappling_effect.mode == ConditionApplicationMode.SOURCE_CHECK
    assert grappling_effect.sourceCheck == AbilityType.STRENGTH
    assert grappling_effect.contestChecks == [AbilityType.STRENGTH, AbilityType.DEXTERITY]
    assert actions[BattleMasterManeuverType.MENACING_ATTACK].conditionEffects[0].condition.name == "FRIGHTENED"
    assert actions[BattleMasterManeuverType.MENACING_ATTACK].conditionEffects[0].mode == ConditionApplicationMode.TARGET_SAVE
    assert actions[BattleMasterManeuverType.MENACING_ATTACK].conditionEffects[0].savingThrow == AbilityType.WISDOM
    assert actions[BattleMasterManeuverType.TRIP_ATTACK].conditionEffects[0].condition.name == "PRONE"
    assert actions[BattleMasterManeuverType.TRIP_ATTACK].conditionEffects[0].mode == ConditionApplicationMode.TARGET_SAVE
    assert actions[BattleMasterManeuverType.TRIP_ATTACK].conditionEffects[0].savingThrow == AbilityType.STRENGTH
    assert arcane_actions[ArcaneShotType.BEGUILING_ARROW].conditionEffects[0].condition.name == "CHARMED"
    assert arcane_actions[ArcaneShotType.SHADOW_ARROW].conditionEffects[0].condition.name == "BLINDED"
    assert rune_actions[FighterSubclassRollActionType.FIRE_RUNE_SHACKLES].conditionEffects[0].condition.name == "RESTRAINED"


def test_fighter_features_and_abilities_encode_condition_effects() -> None:
    cavalier_features = {feature.id: feature for feature in fighter_sheet(15, subclass=FighterSubclassType.CAVALIER).features}
    echo_features = {feature.id: feature for feature in fighter_sheet(7, subclass=FighterSubclassType.ECHO_KNIGHT).features}
    psi_features = {feature.id: feature for feature in fighter_sheet(7, subclass=FighterSubclassType.PSI_WARRIOR).features}
    rune_abilities = {
        ability.id: ability
        for ability in fighter_sheet(3, subclass=FighterSubclassType.RUNE_KNIGHT, runes=[RuneType.STONE_RUNE]).abilities
    }

    ferocious_charger = cavalier_features["ferociousCharger"].conditionEffects[0]
    assert ferocious_charger.condition.name == "PRONE"
    assert ferocious_charger.mode == ConditionApplicationMode.TARGET_SAVE
    assert ferocious_charger.savingThrow == AbilityType.STRENGTH

    echo_avatar_effects = {effect.condition.name: effect for effect in echo_features["echoAvatar"].conditionEffects}
    assert echo_avatar_effects["BLINDED"].mode == ConditionApplicationMode.MANUAL
    assert echo_avatar_effects["DEAFENED"].mode == ConditionApplicationMode.MANUAL

    telekinetic_thrust = psi_features["telekineticAdept"].conditionEffects[0]
    assert telekinetic_thrust.condition.name == "PRONE"
    assert telekinetic_thrust.mode == ConditionApplicationMode.TARGET_SAVE
    assert telekinetic_thrust.savingThrow == AbilityType.STRENGTH

    stone_rune_effects = {effect.condition.name: effect for effect in rune_abilities["stoneRune"].conditionEffects}
    assert stone_rune_effects["CHARMED"].mode == ConditionApplicationMode.TARGET_SAVE
    assert stone_rune_effects["INCAPACITATED"].savingThrow == AbilityType.WISDOM


def test_fighter_roll_condition_effects_are_automatable() -> None:
    automated_modes = {
        ConditionApplicationMode.TARGET_SAVE,
        ConditionApplicationMode.SOURCE_CHECK,
        ConditionApplicationMode.DIRECT,
    }

    for subclass in FighterSubclassType:
        sheet = fighter_sheet(20, subclass=subclass)
        roll_actions = [
            *(action for resource in sheet.resources for action in resource.rollActions or []),
            *(action for ability in sheet.abilities for action in ability.rollActions or []),
            *(action for feature in sheet.features for action in feature.rollActions or []),
        ]

        for action in roll_actions:
            assert all(effect.mode in automated_modes for effect in action.conditionEffects or [])


def test_battle_master_rally_roll_applies_temporary_hp_with_half_fighter_level() -> None:
    sheet = fighter_sheet(3, subclass=FighterSubclassType.BATTLE_MASTER, maneuvers=[BattleMasterManeuverType.RALLY])
    superiority = next(resource for resource in sheet.resources if resource.id == "superiorityDice")
    rally = superiority.rollActions[0]

    assert rally.id == BattleMasterManeuverType.RALLY
    assert rally.resolution == RollResolutionMode.APPLY_TEMPORARY_HIT_POINTS
    assert rally.staticModifier == 1
    assert rally.modifier == RollModifierType.NONE
    assert rally.modifierAbility is None


def test_roll_backed_damage_features_resolve_as_damage() -> None:
    damage_maneuvers = {
        BattleMasterManeuverType.BRACE,
        BattleMasterManeuverType.COMMANDERS_STRIKE,
        BattleMasterManeuverType.DISARMING_ATTACK,
        BattleMasterManeuverType.DISTRACTING_STRIKE,
        BattleMasterManeuverType.FEINTING_ATTACK,
        BattleMasterManeuverType.GOADING_ATTACK,
        BattleMasterManeuverType.LUNGING_ATTACK,
        BattleMasterManeuverType.MANEUVERING_ATTACK,
        BattleMasterManeuverType.MENACING_ATTACK,
        BattleMasterManeuverType.PUSHING_ATTACK,
        BattleMasterManeuverType.QUICK_TOSS,
        BattleMasterManeuverType.RIPOSTE,
        BattleMasterManeuverType.SWEEPING_ATTACK,
        BattleMasterManeuverType.TRIP_ATTACK,
    }
    battle_master = fighter_sheet(
        3,
        subclass=FighterSubclassType.BATTLE_MASTER,
        maneuvers=list(damage_maneuvers),
    )
    battle_master_actions = {
        action.id: action
        for resource in battle_master.resources
        for action in resource.rollActions or []
    }
    arcane_archer = fighter_sheet(3, subclass=FighterSubclassType.ARCANE_ARCHER, arcane_shots=[ArcaneShotType.SHADOW_ARROW])
    brute = fighter_sheet(3, subclass=FighterSubclassType.BRUTE)
    monster_hunter = fighter_sheet(3, subclass=FighterSubclassType.MONSTER_HUNTER)
    psi_warrior = fighter_sheet(3, subclass=FighterSubclassType.PSI_WARRIOR)
    rune_knight = fighter_sheet(3, subclass=FighterSubclassType.RUNE_KNIGHT, runes=[RuneType.FIRE_RUNE])

    assert {action_id for action_id, action in battle_master_actions.items() if action.resolution == RollResolutionMode.APPLY_DAMAGE} == damage_maneuvers
    assert next(action for ability in arcane_archer.abilities for action in ability.rollActions or [] if action.id == ArcaneShotType.SHADOW_ARROW).resolution == RollResolutionMode.APPLY_DAMAGE
    assert next(action for ability in brute.abilities if ability.id == "bruteForce" for action in ability.rollActions or []).resolution == RollResolutionMode.APPLY_DAMAGE
    assert next(action for resource in monster_hunter.resources for action in resource.rollActions or [] if action.id.name == "HUNTERS_DAMAGE").resolution == RollResolutionMode.APPLY_DAMAGE
    assert next(action for resource in psi_warrior.resources for action in resource.rollActions or [] if action.id == FighterSubclassRollActionType.PSIONIC_STRIKE).resolution == RollResolutionMode.APPLY_DAMAGE
    assert next(action for ability in rune_knight.abilities for action in ability.rollActions or [] if action.id == FighterSubclassRollActionType.FIRE_RUNE_SHACKLES).resolution == RollResolutionMode.APPLY_DAMAGE


def test_simple_fighter_archetypes_expose_level_gated_features() -> None:
    cases = {
        FighterSubclassType.BANNERET: {"knightlyEnvoy", "groupRecovery", "teamTactics", "rallyingSurge", "sharedResilience", "inspiringCommander"},
        FighterSubclassType.CAVALIER: {"bonusProficiency", "bornToTheSaddle", "unwaveringMark", "wardingManeuver", "holdTheLine", "ferociousCharger", "vigilantDefender"},
        FighterSubclassType.SAMURAI: {"bonusProficiency", "fightingSpirit", "elegantCourtier", "tirelessSpirit", "rapidStrike", "strengthBeforeDeath"},
        FighterSubclassType.BRUTE: {"bruteForce", "brutishDurability", "additionalFightingStyle", "devastatingCritical", "survivor"},
        FighterSubclassType.SCOUT: {"bonusProficiencies", "combatSuperiority", "naturalExplorer", "improvedCombatSuperiority", "relentless"},
        FighterSubclassType.SHARPSHOOTER: {"steadyAim", "carefulEyes", "closeQuartersShooting", "rapidStrike", "snapShot"},
        FighterSubclassType.MONSTER_HUNTER: {"bonusProficiencies", "combatSuperiority", "huntersMysticism", "monsterSlayer", "improvedCombatSuperiority", "relentless"},
        FighterSubclassType.ARCANE_ARCHER: {"arcaneArcherLore", "arcaneShot", "magicArrow", "curvingShot", "everReadyShot"},
        FighterSubclassType.RUNE_KNIGHT: {"bonusProficiencies", "runeCarver", "giantsMight", "runicShield", "greatStature", "masterOfRunes", "runicJuggernaut"},
        FighterSubclassType.ECHO_KNIGHT: {"manifestEcho", "unleashIncarnation", "echoAvatar", "shadowMartyr", "reclaimPotential", "legionOfOne"},
        FighterSubclassType.PSI_WARRIOR: {"psionicPower", "telekineticAdept", "guardedMind", "bulwarkOfForce", "telekineticMaster"},
        FighterSubclassType.ELDRITCH_KNIGHT: {"spellcasting", "warBond", "warMagic", "eldritchStrike", "arcaneCharge", "improvedWarMagic"},
    }

    for subclass, expected_features in cases.items():
        features = {feature.id: feature for feature in fighter_sheet(20, subclass=subclass).features}

        assert expected_features <= features.keys()


def test_cavalier_samurai_and_sharpshooter_resources_are_tracked() -> None:
    cavalier = {resource.id: resource for resource in fighter_sheet(7, subclass=FighterSubclassType.CAVALIER).resources}
    samurai = {resource.id: resource for resource in fighter_sheet(18, subclass=FighterSubclassType.SAMURAI).resources}
    sharpshooter = {resource.id: resource for resource in fighter_sheet(3, subclass=FighterSubclassType.SHARPSHOOTER).resources}

    assert cavalier["unwaveringMark"].maxUses == 3
    assert cavalier["wardingManeuver"].maxUses == 2
    assert cavalier["wardingManeuver"].rollActions
    assert cavalier["wardingManeuver"].rollActions[0].diceType == DiceType.D8
    assert samurai["fightingSpirit"].maxUses == 3
    assert samurai["strengthBeforeDeath"].maxUses == 1
    assert sharpshooter["steadyAim"].maxUses == 3
    assert sharpshooter["steadyAim"].reset.name == "SHORT_REST"


def test_scout_superiority_actions_use_scaled_dice() -> None:
    sheet = fighter_sheet(10, subclass=FighterSubclassType.SCOUT)
    resource = next(resource for resource in sheet.resources if resource.id == "superiorityDice")
    abilities = {ability.id: ability for ability in sheet.abilities}

    assert resource.maxUses == 5
    assert {action.id.name for action in resource.rollActions or []} == {"SURVIVAL_SUPERIORITY", "SCOUT_PRECISION_ATTACK", "SCOUTS_EVASION"}
    assert all(action.diceType == DiceType.D10 for action in resource.rollActions or [])
    assert abilities["survivalSuperiority"].source == "Scout"
    assert abilities["scoutsEvasion"].activation.name == "REACTION"


def test_brute_rollable_riders_scale_by_level() -> None:
    level_3 = {ability.id: ability for ability in fighter_sheet(3, subclass=FighterSubclassType.BRUTE).abilities}
    level_20 = {ability.id: ability for ability in fighter_sheet(20, subclass=FighterSubclassType.BRUTE).abilities}

    assert level_3["bruteForce"].rollActions
    assert level_3["bruteForce"].rollActions[0].id == FighterSubclassRollActionType.BRUTE_FORCE
    assert level_3["bruteForce"].rollActions[0].diceType == DiceType.D4
    assert level_20["bruteForce"].rollActions[0].diceType == DiceType.D10
    assert level_20["brutishDurability"].rollActions[0].diceType == DiceType.D6


def test_monster_hunter_tracks_superiority_and_mysticism_spells() -> None:
    sheet = fighter_sheet(3, subclass=FighterSubclassType.MONSTER_HUNTER)
    resources = {resource.id: resource for resource in sheet.resources}
    spells = {spell.id: spell for spell in sheet.spells}
    superiority = resources["superiorityDice"]

    assert superiority.maxUses == 4
    assert superiority.source == "Monster Hunter"
    assert {action.id.name for action in superiority.rollActions or []} == {"HUNTERS_DAMAGE", "HUNTERS_WILL", "HUNTERS_EYE"}
    assert resources["protectionFromEvilAndGood"].maxUses == 1
    assert resources["protectionFromEvilAndGood"].reset.name == "LONG_REST"
    assert spells[SpellId.DETECT_MAGIC].ritual is True
    assert spells[SpellId.DETECT_MAGIC].source == SpellSource.MONSTER_HUNTER
    assert spells[SpellId.DETECT_MAGIC].castingAbility.name == "WISDOM"
    assert spells[SpellId.DETECT_MAGIC].castingTime == SpellCastingTime.TEN_MINUTES
    assert spells[SpellId.PROTECTION_FROM_EVIL_AND_GOOD].resourceId == "protectionFromEvilAndGood"
    assert spells[SpellId.PROTECTION_FROM_EVIL_AND_GOOD].concentration is True


def test_arcane_archer_exposes_arcane_shots_with_damage_types() -> None:
    sheet = fighter_sheet(18, subclass=FighterSubclassType.ARCANE_ARCHER)
    resources = {resource.id: resource for resource in sheet.resources}
    abilities = {ability.id: ability for ability in sheet.abilities}

    assert resources["arcaneShot"].maxUses == 2
    assert resources["arcaneShot"].reset.name == "SHORT_REST"
    assert {"banishingArrow", "beguilingArrow", "burstingArrow", "enfeeblingArrow", "graspingArrow", "piercingArrow", "seekingArrow", "shadowArrow"} <= set(abilities)
    assert abilities["burstingArrow"].rollActions
    assert abilities["burstingArrow"].rollActions[0].damageType == DamageType.FORCE
    assert abilities["shadowArrow"].rollActions[0].damageType == DamageType.PSYCHIC
    assert abilities["banishingArrow"].rollActions[0].diceCount == 2


def test_arcane_archer_respects_configured_shot_choices() -> None:
    sheet = fighter_sheet(3, subclass=FighterSubclassType.ARCANE_ARCHER, arcane_shots=[ArcaneShotType.BURSTING_ARROW, ArcaneShotType.SEEKING_ARROW])
    abilities = {ability.id: ability for ability in sheet.abilities}

    assert {"burstingArrow", "seekingArrow"} <= abilities.keys()
    assert "shadowArrow" not in abilities


def test_rune_knight_tracks_giant_rune_resources_and_damage_scaling() -> None:
    level_7 = fighter_sheet(7, subclass=FighterSubclassType.RUNE_KNIGHT, runes=[RuneType.FIRE_RUNE, RuneType.HILL_RUNE])
    level_18 = fighter_sheet(18, subclass=FighterSubclassType.RUNE_KNIGHT)
    resources = {resource.id: resource for resource in level_7.resources}
    abilities = {ability.id: ability for ability in level_7.abilities}
    level_18_abilities = {ability.id: ability for ability in level_18.abilities}
    level_18_resources = {resource.id: resource for resource in level_18.resources}

    assert resources["giantsMight"].maxUses == 3
    assert resources["runicShield"].maxUses == 3
    assert resources["fireRune"].maxUses == 1
    assert resources["hillRune"].reset.name == "SHORT_REST"
    assert abilities["fireRune"].rollActions[0].damageType == DamageType.FIRE
    assert level_18_abilities["giantsMight"].rollActions[0].diceType == DiceType.D10
    assert level_18_resources["stormRune"].maxUses == 2


def test_echo_knight_tracks_constitution_based_resources() -> None:
    sheet = fighter_sheet(15, subclass=FighterSubclassType.ECHO_KNIGHT)
    resources = {resource.id: resource for resource in sheet.resources}
    abilities = {ability.id: ability for ability in sheet.abilities}

    assert resources["unleashIncarnation"].maxUses == 2
    assert resources["shadowMartyr"].maxUses == 1
    assert resources["shadowMartyr"].reset.name == "SHORT_REST"
    assert resources["reclaimPotential"].maxUses == 2
    assert abilities["reclaimPotential"].rollActions[0].staticModifier == 2


def test_psi_warrior_tracks_psionic_dice_scaling_and_telekinesis() -> None:
    sheet = fighter_sheet(18, subclass=FighterSubclassType.PSI_WARRIOR)
    resources = {resource.id: resource for resource in sheet.resources}
    abilities = {ability.id: ability for ability in sheet.abilities}
    spells = {spell.id: spell for spell in sheet.spells}

    assert resources["psionicEnergyDice"].maxUses == 12
    assert resources["psionicEnergyDice"].rollActions[0].diceType == DiceType.D12
    assert resources["psionicEnergyDice"].rollActions[1].damageType == DamageType.FORCE
    assert resources["psionicEnergyRecovery"].reset.name == "SHORT_REST"
    assert resources["telekineticMaster"].reset.name == "LONG_REST"
    assert "guardedMind" in abilities
    assert spells[SpellId.TELEKINESIS].name == SpellId.TELEKINESIS
    assert spells[SpellId.TELEKINESIS].source == SpellSource.PSI_WARRIOR
    assert spells[SpellId.TELEKINESIS].castingAbility == AbilityType.INTELLIGENCE


def test_eldritch_knight_tracks_spell_slots_and_known_counts() -> None:
    level_3 = fighter_sheet(3, subclass=FighterSubclassType.ELDRITCH_KNIGHT)
    level_20 = fighter_sheet(20, subclass=FighterSubclassType.ELDRITCH_KNIGHT)
    level_3_resources = {resource.id: resource for resource in level_3.resources}
    level_20_resources = {resource.id: resource for resource in level_20.resources}
    level_20_abilities = {ability.id: ability for ability in level_20.abilities}
    spellcasting = next(feature for feature in level_20.features if feature.id == "spellcasting")

    assert level_3_resources["firstLevelSpellSlots"].maxUses == 2
    assert "secondLevelSpellSlots" not in level_3_resources
    assert level_20_resources["firstLevelSpellSlots"].maxUses == 4
    assert level_20_resources["secondLevelSpellSlots"].maxUses == 3
    assert level_20_resources["thirdLevelSpellSlots"].maxUses == 3
    assert level_20_resources["fourthLevelSpellSlots"].maxUses == 1
    assert level_20_abilities["fourthLevelSpellSlots"].resourceId == "fourthLevelSpellSlots"
    assert "3 cantrips and prepare 13 leveled spells" in spellcasting.description


def test_eldritch_knight_spell_progression_exposes_curated_spell_choices() -> None:
    sheet = fighter_sheet(3, subclass=FighterSubclassType.ELDRITCH_KNIGHT)
    choices = {choice.id: choice for choice in sheet.pendingChoices}
    spell_choice = choices["eldritchKnightSpells"]
    option_values = {option.value for option in spell_choice.options}

    assert spell_choice.minimum == 5
    assert spell_choice.maximum == 5
    assert {"fireBolt", "shield", "magicMissile"} <= option_values
    assert "shatter" not in option_values


def test_eldritch_knight_spell_progression_limits_flexible_school_choices() -> None:
    from dnd_board.rules.classes.fighter.archetypes import eldritch_knight_spell_options

    level_3_options = {enum_key(spell.id) for spell in eldritch_knight_spell_options(3)}
    level_3_after_flexible = {enum_key(spell.id) for spell in eldritch_knight_spell_options(3, ["findFamiliar"])}
    level_8_after_flexible = {enum_key(spell.id) for spell in eldritch_knight_spell_options(8, ["findFamiliar"])}

    assert "findFamiliar" in level_3_options
    assert "sleep" in level_3_options
    assert "shield" in level_3_after_flexible
    assert "sleep" not in level_3_after_flexible
    assert "sleep" in level_8_after_flexible


def test_eldritch_knight_spell_helpers_cover_low_level_and_pruning_branches() -> None:
    spells = [
        eldritch_knight_catalog_spell("fireBolt"),
        eldritch_knight_catalog_spell("mageHand"),
        eldritch_knight_catalog_spell("minorIllusion"),
        eldritch_knight_catalog_spell("shield"),
        eldritch_knight_catalog_spell("magicMissile"),
        eldritch_knight_catalog_spell("findFamiliar"),
        eldritch_knight_catalog_spell("sleep"),
        eldritch_knight_catalog_spell("shatter"),
    ]

    assert eldritch_knight_max_spell_level(1) == 0
    assert eldritch_knight_max_spell_level(7) == 2
    assert eldritch_knight_max_spell_level(13) == 3
    assert eldritch_knight_flexible_spell_limit(2) == 0
    assert is_eldritch_knight_spell_selection_valid(2, []) is True
    assert is_eldritch_knight_spell_selection_valid(2, [eldritch_knight_catalog_spell("fireBolt")]) is False
    assert pruned_eldritch_knight_spells(2, [spell for spell in spells if spell is not None]) == []
    assert [spell.id for spell in pruned_eldritch_knight_spells(3, [spell for spell in spells if spell is not None])] == [
        SpellId.FIRE_BOLT,
        SpellId.MAGE_HAND,
        SpellId.SHIELD,
        SpellId.MAGIC_MISSILE,
        SpellId.FIND_FAMILIAR,
    ]
    assert [spell.id for spell in pruned_eldritch_knight_spells(3, [spell for spell in spells if spell is not None][:4])] == [
        SpellId.FIRE_BOLT,
        SpellId.MAGE_HAND,
        SpellId.SHIELD,
    ]
    assert [spell.id for spell in pruned_eldritch_knight_spells(3, [spell for spell in spells if spell is not None][3:])] == [
        SpellId.SHIELD,
        SpellId.MAGIC_MISSILE,
        SpellId.FIND_FAMILIAR,
    ]
    assert [spell.id for spell in pruned_eldritch_knight_spells(3, [spell for spell in [spells[3], spells[5], spells[6], spells[6]] if spell is not None])] == [
        SpellId.SHIELD,
        SpellId.FIND_FAMILIAR,
    ]


def test_fighter_helpers_handle_missing_or_nonstandard_fighter_state() -> None:
    assert fighter_resources([]) == []
    assert fighter_features([]) == []
    assert battle_master_features(CharacterClassLevel(name=ClassType.FIGHTER, level=3, subclass=FighterSubclassType.CHAMPION), 3) == []
    assert subclass_description(CharacterClassLevel(name=ClassType.FIGHTER, level=3, subclass=ClassType.ROGUE)) == (
        "Rogue subclass features are included up to your Fighter level."
    )


def test_eldritch_knight_selection_and_defensive_slot_fallback(monkeypatch) -> None:
    shield = eldritch_knight_catalog_spell(SpellId.SHIELD)
    magic_missile = eldritch_knight_catalog_spell(SpellId.MAGIC_MISSILE)
    find_familiar = eldritch_knight_catalog_spell(SpellId.FIND_FAMILIAR)
    fire_bolt = eldritch_knight_catalog_spell(SpellId.FIRE_BOLT)
    mage_hand = eldritch_knight_catalog_spell(SpellId.MAGE_HAND)
    assert all(spell is not None for spell in [shield, magic_missile, find_familiar, fire_bolt, mage_hand])

    assert is_eldritch_knight_spell_selection_valid(3, [fire_bolt, mage_hand, shield, magic_missile, find_familiar]) is True

    monkeypatch.setitem(
        fighter_archetypes.ELDRITCH_KNIGHT_SPELLCASTING,
        3,
        EldritchKnightSpellcastingProgression(
            fighter_level=3,
            cantrips_known=0,
            spells_known=0,
            first_level_slots=0,
            second_level_slots=0,
            third_level_slots=0,
            fourth_level_slots=0,
        ),
    )
    assert eldritch_knight_max_spell_level(3) == 0


def test_arcane_shot_roll_actions_skip_unavailable_low_level_banishing_arrow() -> None:
    assert arcane_shot_roll_actions(ArcaneShotType.BANISHING_ARROW, 3) is None


def test_fighter_subclass_and_superiority_helpers_handle_duplicate_or_missing_progression(monkeypatch) -> None:
    monkeypatch.setattr(fighter_archetypes, "brute_force_die", lambda fighter_level_value: None)

    brute_abilities = fighter_subclass_abilities([CharacterClassLevel(name=ClassType.FIGHTER, level=3, subclass=FighterSubclassType.BRUTE)])
    selected_maneuvers = selected_battle_master_maneuvers(
        [
            CharacterClassLevel(
                name=ClassType.FIGHTER,
                level=3,
                subclass=FighterSubclassType.BATTLE_MASTER,
                maneuvers=[BattleMasterManeuverType.AMBUSH, BattleMasterManeuverType.AMBUSH, BattleMasterManeuverType.TRIP_ATTACK],
            )
        ]
    )

    assert all(ability.id != enum_key(FighterSubclassRollActionType.BRUTE_FORCE) for ability in brute_abilities)
    assert selected_maneuvers == [BattleMasterManeuverType.AMBUSH, BattleMasterManeuverType.TRIP_ATTACK]


def test_fighter_subclass_dice_helpers_cover_scaling_breakpoints() -> None:
    assert giants_might_die(3) == DiceType.D6
    assert giants_might_die(10) == DiceType.D8
    assert giants_might_die(18) == DiceType.D10
    assert psionic_energy_die(3) == DiceType.D6
    assert psionic_energy_die(5) == DiceType.D8
    assert psionic_energy_die(11) == DiceType.D10
    assert psionic_energy_die(17) == DiceType.D12


def test_eldritch_knight_uses_configured_spells_with_intelligence() -> None:
    sheet = fighter_sheet(
        7,
        subclass=FighterSubclassType.ELDRITCH_KNIGHT,
        spells=[
            SpellEntry(
                id=SpellId.SHIELD,
                name=SpellId.SHIELD,
                source=SpellSource.WIZARD,
                level=1,
                school=SpellSchool.ABJURATION,
                castingAbility=AbilityType.WISDOM,
                castingTime=SpellCastingTime.REACTION,
                targeting=SpellTargeting(rangeType=SpellRangeType.SELF),
                duration=SpellDuration(unit=SpellDurationUnit.ROUND, amount=1),
                components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
                description="Raise AC until the start of your next turn.",
            )
        ],
    )

    assert sheet.spells[0].name == SpellId.SHIELD
    assert sheet.spells[0].castingAbility == AbilityType.INTELLIGENCE
    assert sheet.spells[0].source == SpellSource.WIZARD


def test_spell_targeting_models_range_and_area_geometry() -> None:
    from dnd_board.rules.classes.fighter.archetypes import eldritch_knight_catalog_spell

    fireball = eldritch_knight_catalog_spell("fireball")
    lightning_bolt = eldritch_knight_catalog_spell("lightningBolt")

    assert fireball.targeting.rangeType == SpellRangeType.DISTANCE
    assert fireball.targeting.distanceFeet == 150
    assert isinstance(fireball.targeting.area, SpellRadiusArea)
    assert fireball.targeting.area.radiusFeet == 20
    assert fireball.targeting.area.diameterFeet == 40
    assert fireball.targeting.summary == "150 ft, 20 ft radius"
    assert fireball.duration.unit == SpellDurationUnit.INSTANTANEOUS
    assert lightning_bolt.targeting.rangeType == SpellRangeType.SELF
    assert isinstance(lightning_bolt.targeting.area, SpellLineArea)
    assert lightning_bolt.targeting.area.lengthFeet == 100
    assert lightning_bolt.targeting.area.widthFeet == 5


def test_fighter_level_progression_exposes_hit_point_and_asi_choices() -> None:
    choices = {choice.id: choice for choice in fighter_sheet(4).pendingChoices}

    assert choices["hitPointIncrease"].choiceType.name == "HIT_POINTS"
    assert [option.value for option in choices["hitPointIncrease"].options] == ["fixed", "roll"]
    assert choices["fighterAbilityScoreImprovement"].choiceType.name == "ABILITY_SCORE_IMPROVEMENT"
    assert "alert" in {option.value for option in choices["fighterAbilityScoreImprovement"].options}
    assert "warCaster" not in {option.value for option in choices["fighterAbilityScoreImprovement"].options}


def test_fighter_progression_labels_legacy_options() -> None:
    subclass_choices = {choice.id: choice for choice in fighter_sheet(3).pendingChoices}
    subclass_labels = {option.value: option.label for option in subclass_choices["fighterSubclass"].options}
    style_sheet = build_character_sheet(
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
            sheet=PartyMemberSheet(classes=[CharacterClassLevel(name=ClassType.FIGHTER, level=1)]),
        ),
        current_hp=None,
        resource_overrides={},
    )
    style_choices = {choice.id: choice for choice in style_sheet.pendingChoices}
    style_labels = {option.value: option.label for option in style_choices["fighterFightingStyles"].options}

    assert subclass_labels["battleMaster"] == "Battle Master"
    assert subclass_labels["runeKnight"] == "Rune Knight (Legacy)"
    assert style_labels["defense"] == "Defense"
    assert style_labels["superiorTechnique"] == "Superior Technique (Legacy)"
    assert style_labels["packFighting"] == "Pack Fighting"


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
                ],
                equipment=[chain_mail()],
            ),
        ),
        current_hp=None,
        resource_overrides={},
    )
    features = {feature.id: feature for feature in sheet.features}
    abilities = {ability.id: ability for ability in sheet.abilities}

    assert sheet.armorClass == 17
    assert {"defense", "interception"} <= features.keys()
    assert "interception" in abilities


def fighter_sheet(
    level: int,
    subclass: FighterSubclassType | None = None,
    fighting_style: FightingStyleType = FightingStyleType.DEFENSE,
    equipment: list[EquipmentItem] | None = None,
    arcane_shots: list[ArcaneShotType] | None = None,
    runes: list[RuneType] | None = None,
    maneuvers: list[BattleMasterManeuverType] | None = None,
    spells: list[SpellEntry] | None = None,
):
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
                        maneuvers=maneuvers,
                        arcaneShots=arcane_shots,
                        runes=runes,
                    )
                ],
                equipment=equipment,
                spells=spells,
            ),
        ),
        current_hp=None,
        resource_overrides={},
    )


def fighter_sheet_with_attacks(fighting_style: FightingStyleType, attacks: list[AttackAction], equipment: list[EquipmentItem] | None = None):
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
            abilityScores=AbilityScores(strength=16, dexterity=14, constitution=14, intelligence=10, wisdom=10, charisma=10),
            sheet=PartyMemberSheet(
                classes=[CharacterClassLevel(name=ClassType.FIGHTER, level=1, fightingStyle=fighting_style)],
                attacks=attacks,
                equipment=equipment,
            ),
        ),
        current_hp=None,
        resource_overrides={},
    )


def fighting_style_entry_id(fighting_style: FightingStyleType) -> str:
    words = fighting_style.name.lower().split("_")
    return words[0] + "".join(word.capitalize() for word in words[1:])


def chain_mail() -> EquipmentItem:
    return EquipmentItem(
        id="chain-mail",
        name="Chain Mail",
        itemType=EquipmentType.ARMOR,
        slot=EquipmentSlot.ARMOR,
        armorCategory=ArmorCategory.HEAVY,
        armorClass=16,
    )


def leather_armor() -> EquipmentItem:
    return EquipmentItem(
        id="leather",
        name="Leather Armor",
        itemType=EquipmentType.ARMOR,
        slot=EquipmentSlot.ARMOR,
        armorCategory=ArmorCategory.LIGHT,
        armorClass=11,
    )


def shield(slot: EquipmentSlot) -> EquipmentItem:
    return EquipmentItem(id="shield", name="Shield", itemType=EquipmentType.SHIELD, slot=slot, armorClassBonus=2)


def longsword(slot: EquipmentSlot) -> EquipmentItem:
    return EquipmentItem(id="longsword", name="Longsword", itemType=EquipmentType.WEAPON, slot=slot)
