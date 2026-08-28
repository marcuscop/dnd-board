from dnd_board.character_sheet import (
    AbilityScores,
    AbilityType,
    ArmorCategory,
    AttackRangeType,
    AttackAction,
    AttackActionType,
    AttackDamageAbilityModifierMode,
    AttackKind,
    BattleMasterManeuverType,
    CharacterClassLevel,
    ClassType,
    DamageType,
    DiceType,
    EquipmentItem,
    EquipmentSlot,
    EquipmentType,
    FightingStyleType,
    PartyMember,
    PartyManifest,
    PartyMemberConfig,
    PartyMemberSheet,
    TokenKind,
    WeaponCategory,
    WeaponProperty,
    build_attack_roll_payload,
    build_character_sheet,
    build_damage_roll_payload,
    typed_json_from_value,
    party_manifest_from_dict,
)
from dnd_board.rules.fighter import FighterSubclassType
from dnd_board.rules.feats import FIGHTING_STYLE_FEATS, FeatEffectType
from dnd_board.rules.battle_master import BATTLE_MASTER_MANEUVERS


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


def test_fighting_style_great_weapon_fighting_rerolls_low_damage_dice(monkeypatch) -> None:
    rolls = iter([1, 6])
    monkeypatch.setattr("dnd_board.character_sheet.random.randint", lambda minimum, maximum: next(rolls))
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

    assert roll.dice == [6]
    assert roll.total == 9
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
    assert len(resource.rollActions or []) == len(BATTLE_MASTER_MANEUVERS)
    assert all(action.diceType == DiceType.D6 for action in resource.rollActions or [])
    assert all(action.consumesResource.name == "SUPERIORITY_DICE" for action in resource.rollActions or [])
    assert {"ambush", "tripAttack"} <= abilities.keys()
    assert abilities["ambush"].resourceId == "superiorityDice"
    assert abilities["ambush"].source == "Battle Master"
    assert abilities["brace"].activation.name == "REACTION"
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


def fighter_sheet(
    level: int,
    subclass: FighterSubclassType | None = None,
    fighting_style: FightingStyleType = FightingStyleType.DEFENSE,
    equipment: list[EquipmentItem] | None = None,
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
                    )
                ],
                equipment=equipment,
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
