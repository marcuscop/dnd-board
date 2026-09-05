from dataclasses import replace

import pytest

from dnd_board.character_sheet import (
    AbilityScores,
    AbilityType,
    AttackAction,
    AttackDamageAbilityModifierMode,
    CharacterClassLevel,
    ClassType,
    ConditionApplicationMode,
    ConditionEffect,
    ConditionRemovalTrigger,
    ConditionType,
    CreatureType,
    DamageType,
    DiceType,
    ArmorCategory,
    EquipmentItem,
    EquipmentSlot,
    EquipmentType,
    FightingStyleType,
    HitPoints,
    PartyManifest,
    PartyMemberConfig,
    PartyMemberSheet,
    PartyMember,
    ProficiencyLevel,
    Purse,
    RollAction,
    RollLogEntry,
    RollLogEntryType,
    RollModifierType,
    RollResolutionMode,
    SheetFeature,
    SheetSectionType,
    SpellConeArea,
    SpellCubeArea,
    SpellCylinderArea,
    SpellDuration,
    SpellDurationUnit,
    SpellId,
    SpellLineArea,
    SpellLinkedHealingAmount,
    SpellRangeType,
    RestType,
    SpellSaveOutcome,
    SpellScalingType,
    SpellTargeting,
    TimeEconomy,
    TokenKind,
    build_attack_roll_payload,
    build_character_sheet,
    build_damage_roll_payload,
    build_roll_action_payload,
    build_saving_throw_roll_payload,
    build_spell_attack_roll_payload,
    build_spell_condition_roll_payload,
    build_spell_damage_roll_payload,
    build_spell_healing_roll_payload,
    resolve_roll_against_target,
    RollSource,
    armor_item_class,
    clamped_ability_score,
    enum_value,
    enum_key,
    effective_damage_resistances,
    generated_ability_scores,
    generated_max_hp,
    optional_text,
    party_manifest_from_dict,
    positive_int,
    proficiency_multiplier,
    roll_log_entry_to_dict,
    roll_payload_to_dict,
    roll_resolution_to_dict,
    safe_int,
    sanitize_identifier,
    saving_throw_total,
    spell_area_label,
    spell_condition_effect_at,
    spell_target_range_label,
    spell_damage_effect_at,
    scaled_spell_effect_instance_count,
    text_list,
    to_float,
    typed_json_from_value,
    typed_json_to_value,
    value_matches_type,
    build_ability_check_roll_payload,
    condition_armor_class_bonus,
)
from dnd_board.rules.classes.fighter.base import FighterSubclassType
from dnd_board.rules.spells import cleric_spell_entry, spell_damage_effect, spell_entry, spell_scaling, wizard_spell_entry


def test_typed_party_manifest_round_trips_config_objects() -> None:
    manifest = PartyManifest(
        members=[
            PartyMemberConfig(
                id="player-1",
                name="Marina",
                maxHp=31,
                abilityScores=AbilityScores(strength=16, dexterity=14, constitution=15, intelligence=10, wisdom=12, charisma=8),
                sheet=PartyMemberSheet(
                    purse=Purse(copper=3, silver=2, gold=31),
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
    assert loaded.members[0].sheet.purse == Purse(copper=3, silver=2, gold=31)


def test_spell_summary_formatters_cover_special_ranges_and_durations() -> None:
    assert SpellDuration(SpellDurationUnit.UNTIL_DISPELLED).summary == "Until dispelled"
    assert SpellDuration(SpellDurationUnit.SPECIAL).summary == "Special"
    assert spell_target_range_label(SpellTargeting(SpellRangeType.SIGHT)) == "Sight"
    assert spell_target_range_label(SpellTargeting(SpellRangeType.UNLIMITED)) == "Unlimited"
    assert spell_target_range_label(SpellTargeting(SpellRangeType.SPECIAL)) == "Special"


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


def test_typed_json_rejects_malformed_nodes_and_converts_scalar_enum_values() -> None:
    assert typed_json_to_value({"$type": "None", "value": None}) is None
    assert typed_json_to_value({"$type": "list", "items": "bad"}, list[int]) is None
    assert typed_json_to_value({"$type": "dict", "value": "bad"}, dict[str, int]) is None
    assert typed_json_to_value({"$type": "MissingModel", "value": None}) is None
    assert typed_json_to_value({"$type": "str", "value": "dexterity"}, AbilityType) == AbilityType.DEXTERITY
    assert typed_json_to_value(
        {
            "$type": "list",
            "items": [
                {"$type": "ConditionType", "value": "PRONE"},
                {"$type": "None", "value": None},
            ],
        },
        list[ConditionType],
    ) == [ConditionType.PRONE]
    assert typed_json_to_value(
        {
            "$type": "list",
            "items": [
                {"$type": "str", "value": "kept"},
                {"$type": "None", "value": None},
            ],
        },
    ) == ["kept", None]


def test_spell_targeting_summaries_cover_structured_area_shapes() -> None:
    assert SpellTargeting(SpellRangeType.TOUCH).summary == "Touch"
    assert SpellTargeting(SpellRangeType.SELF, area=SpellConeArea(lengthFeet=15)).summary == "Self, 15 ft cone"
    assert SpellTargeting(SpellRangeType.DISTANCE, distanceFeet=60, area=SpellCubeArea(sizeFeet=10)).summary == "60 ft, 10 ft cube"

    cylinder = SpellCylinderArea(radiusFeet=10, heightFeet=20)
    assert cylinder.diameterFeet == 20
    assert SpellTargeting(SpellRangeType.DISTANCE, distanceFeet=120, area=cylinder).summary == "120 ft, 10 ft radius x 20 ft cylinder"


def test_roll_action_payloads_cover_modifier_and_condition_effect_branches(monkeypatch) -> None:
    monkeypatch.setattr("dnd_board.character_sheet.random.randint", lambda minimum, maximum: 5)
    sheet = basic_sheet()
    source = RollSource(SheetSectionType.ABILITIES, "test", "test")

    proficiency_roll = build_roll_action_payload(sheet, "player-1", source, RollAction(AbilityType.STRENGTH, AbilityType.STRENGTH, 1, DiceType.D6, modifier=RollModifierType.PROFICIENCY_BONUS))
    strength_roll = build_roll_action_payload(sheet, "player-1", source, RollAction(AbilityType.STRENGTH, AbilityType.STRENGTH, 1, DiceType.D6, modifier=RollModifierType.ABILITY_MODIFIER, modifierAbility=AbilityType.STRENGTH))
    class_level_roll = build_roll_action_payload(sheet, "player-1", source, RollAction(AbilityType.STRENGTH, AbilityType.STRENGTH, 1, DiceType.D6, modifier=RollModifierType.CLASS_LEVEL, staticModifier=1))
    condition_roll = build_roll_action_payload(
        sheet,
        "player-1",
        source,
        RollAction(
            AbilityType.STRENGTH,
            AbilityType.STRENGTH,
            1,
            DiceType.D6,
            resolution=RollResolutionMode.NONE,
            conditionEffects=[
                ConditionEffect(ConditionType.PRONE, ConditionApplicationMode.DIRECT),
                ConditionEffect(ConditionType.FRIGHTENED, ConditionApplicationMode.MANUAL),
                ConditionEffect(ConditionType.STUNNED, ConditionApplicationMode.TARGET_SAVE, savingThrow=AbilityType.WISDOM),
            ],
        ),
    )
    resolution = resolve_roll_against_target(condition_roll, sheet)

    assert proficiency_roll.modifierBreakdown[0].source == "Proficiency"
    assert strength_roll.modifierBreakdown[0].source == "Strength"
    assert class_level_roll.modifierBreakdown[0].source == "Class Level"
    assert condition_roll.conditionEffects[2].saveDc == 14
    assert ConditionType.PRONE in resolution.targetConditions
    assert "Frightened requires manual resolution" in resolution.outcome


def test_active_buff_and_debuff_conditions_modify_matching_d20_rolls(monkeypatch) -> None:
    monkeypatch.setattr("dnd_board.character_sheet.random.randint", lambda minimum, maximum: 2 if maximum == 4 else 10)
    sheet = replace(basic_sheet(), conditions=[ConditionType.BLESSED, ConditionType.GUIDANCE])
    baned_sheet = replace(basic_sheet(), conditions=[ConditionType.BANE])

    attack_roll = build_attack_roll_payload(sheet, "player-1", sheet.attacks[0])
    check_roll = build_ability_check_roll_payload(sheet, "player-1", AbilityType.STRENGTH)
    save_roll = build_saving_throw_roll_payload(sheet, "player-1", AbilityType.STRENGTH)
    baned_attack_roll = build_attack_roll_payload(baned_sheet, "player-1", baned_sheet.attacks[0])
    baned_save_roll = build_saving_throw_roll_payload(baned_sheet, "player-1", AbilityType.STRENGTH)
    slowed_sheet = replace(basic_sheet(), conditions=[ConditionType.SLOWED])
    slowed_dexterity_save_roll = build_saving_throw_roll_payload(slowed_sheet, "player-1", AbilityType.DEXTERITY)
    slowed_strength_save_roll = build_saving_throw_roll_payload(slowed_sheet, "player-1", AbilityType.STRENGTH)

    assert ("Blessed", 2) in [(part.source, part.value) for part in attack_roll.modifierBreakdown]
    assert ("Guidance", 2) not in [(part.source, part.value) for part in attack_roll.modifierBreakdown]
    assert ("Guidance", 2) in [(part.source, part.value) for part in check_roll.modifierBreakdown]
    assert ("Blessed", 2) in [(part.source, part.value) for part in save_roll.modifierBreakdown]
    assert ("Bane", -2) in [(part.source, part.value) for part in baned_attack_roll.modifierBreakdown]
    assert ("Bane", -2) in [(part.source, part.value) for part in baned_save_roll.modifierBreakdown]
    assert ("Slowed", -2) in [(part.source, part.value) for part in slowed_dexterity_save_roll.modifierBreakdown]
    assert ("Slowed", -2) not in [(part.source, part.value) for part in slowed_strength_save_roll.modifierBreakdown]
    assert condition_armor_class_bonus([ConditionType.SHIELDED]) == 5
    assert condition_armor_class_bonus([ConditionType.SHIELDED, ConditionType.SLOWED]) == 3


def test_active_damage_resistance_conditions_reduce_matching_damage_by_d4(monkeypatch) -> None:
    monkeypatch.setattr("dnd_board.character_sheet.random.randint", lambda minimum, maximum: 3 if maximum == 4 else 8)
    attacker = basic_sheet()
    target = replace(basic_sheet(), conditions=[ConditionType.RESISTANCE_FIRE])
    action = replace(attacker.attacks[0], damageDiceCount=1, damageDiceType=DiceType.D8, damageType=DamageType.FIRE, damageAbilityModifier=AttackDamageAbilityModifierMode.EXCLUDED)

    roll = build_damage_roll_payload(attacker, "player-1", action)
    resolution = resolve_roll_against_target(roll, target)

    assert roll.total == 8
    assert resolution.targetHp.current == 15
    assert resolution.outcome == "deals 5 damage after Resistance Fire reduces damage by 3"


def test_protection_from_poison_adds_true_poison_resistance_and_clears_poisoned(monkeypatch) -> None:
    monkeypatch.setattr("dnd_board.character_sheet.random.randint", lambda minimum, maximum: 8)
    attacker = basic_sheet()
    target = replace(basic_sheet(), conditions=[ConditionType.PROTECTION_FROM_POISON, ConditionType.POISONED])
    action = replace(attacker.attacks[0], damageDiceCount=1, damageDiceType=DiceType.D8, damageType=DamageType.POISON, damageAbilityModifier=AttackDamageAbilityModifierMode.EXCLUDED)
    protection_roll = RollAction(
        id=SpellId.PROTECTION_FROM_POISON,
        name=SpellId.PROTECTION_FROM_POISON,
        diceCount=0,
        diceType=DiceType.D4,
        conditionEffects=[ConditionEffect(ConditionType.PROTECTION_FROM_POISON, ConditionApplicationMode.DIRECT)],
    )

    damage_roll = build_damage_roll_payload(attacker, "player-1", action)
    damage_resolution = resolve_roll_against_target(damage_roll, target)
    condition_resolution = resolve_roll_against_target(
        build_roll_action_payload(attacker, "player-1", RollSource(SheetSectionType.SPELLS, enum_key(SpellId.PROTECTION_FROM_POISON), "effect-0"), protection_roll),
        replace(basic_sheet(), conditions=[ConditionType.POISONED]),
    )

    assert effective_damage_resistances(target) == {DamageType.POISON}
    assert damage_resolution.targetHp.current == 16
    assert damage_resolution.outcome == "deals 4 damage after Poison resistance"
    assert condition_resolution.targetConditions == [ConditionType.PROTECTION_FROM_POISON]


def test_creature_type_limited_damage_only_applies_to_matching_targets(monkeypatch) -> None:
    monkeypatch.setattr("dnd_board.character_sheet.random.randint", lambda minimum, maximum: 5)
    divine_smite = spell_entry(SpellId.DIVINE_SMITE)
    assert divine_smite is not None
    roll = build_spell_damage_roll_payload(spell_sheet(5, [divine_smite]), "player-1", divine_smite, effect_index=1)
    humanoid = basic_sheet()
    undead = replace(basic_sheet(), creatureTypes=[CreatureType.UNDEAD])

    humanoid_resolution = resolve_roll_against_target(roll, humanoid)
    undead_resolution = resolve_roll_against_target(roll, undead)

    assert humanoid_resolution.targetHp.current == humanoid.hp.current
    assert humanoid_resolution.outcome == "has no effect; target is not Fiend or Undead"
    assert undead_resolution.targetHp.current == undead.hp.current - 5
    assert undead_resolution.outcome == "deals 5 damage"


def test_shared_parsing_and_armor_helpers_cover_edge_cases() -> None:
    assert armor_item_class(EquipmentItem(id="breastplate", name="Breastplate", itemType=EquipmentType.ARMOR, slot=EquipmentSlot.ARMOR, armorCategory=ArmorCategory.MEDIUM, armorClass=14), 4) == 16
    assert clamped_ability_score("30") == 30
    assert positive_int("5") == 5
    assert positive_int("0") is None
    assert positive_int("bad") is None
    assert safe_int("bad", 7) == 7
    assert optional_text("  hello  ", 3) == "hel"
    assert optional_text("   ", 3) is None
    assert text_list(["alpha", "  ", 42]) == ["alpha", "42"]
    assert sanitize_identifier(" A Bad_ID!? ") == "abadid"
    assert to_float("2.5") == 2.5
    assert to_float(None) == 0


def test_attack_damage_save_and_resolution_branches(monkeypatch) -> None:
    monkeypatch.setattr("dnd_board.character_sheet.random.randint", lambda minimum, maximum: 10)
    sheet = basic_sheet()
    target = basic_sheet()
    target.hp = HitPoints(current=12, max=20, temporary=5)
    target.damageResistances = [DamageType.SLASHING]
    target.damageVulnerabilities = [DamageType.SLASHING]
    target.damageImmunities = [DamageType.FIRE]

    attack = AttackAction(
        id="magic-sword",
        name="Magic Sword",
        ability=AbilityType.STRENGTH,
        damageDiceCount=1,
        damageDiceType=DiceType.D8,
        toHitBonus=1,
        damageBonus=2,
    )
    attack_roll = build_attack_roll_payload(sheet, "player-1", attack)
    damage_roll = build_damage_roll_payload(sheet, "player-1", attack)
    attack_resolution = resolve_roll_against_target(attack_roll, target)
    damage_resolution = resolve_roll_against_target(damage_roll, target)

    assert ("Magic Sword Attack Bonus", 1) in [(part.source, part.value) for part in attack_roll.modifierBreakdown]
    assert ("Magic Sword Damage Bonus", 2) in [(part.source, part.value) for part in damage_roll.modifierBreakdown]
    assert attack_resolution.outcome == "hits"
    assert damage_resolution.outcome == "deals 16 damage"
    assert damage_resolution.targetHp.current == 1
    assert damage_resolution.targetHp.temporary == 0

    unproficient_attack = AttackAction(
        id="club",
        name="Club",
        ability=AbilityType.STRENGTH,
        damageDiceCount=1,
        damageDiceType=DiceType.D4,
        proficient=False,
        damageAbilityModifier=AttackDamageAbilityModifierMode.EXCLUDED,
    )
    assert [part.source for part in build_attack_roll_payload(sheet, "player-1", unproficient_attack).modifierBreakdown] == ["Strength"]
    assert build_damage_roll_payload(sheet, "player-1", unproficient_attack).modifierBreakdown == []

    target.hp = HitPoints(current=12, max=20, temporary=0)
    fire_roll = build_damage_roll_payload(sheet, "player-1", AttackAction(id="fire", name="Fire", ability=AbilityType.STRENGTH, damageDiceCount=1, damageDiceType=DiceType.D8, damageType=DamageType.FIRE))
    assert "Fire immunity" in resolve_roll_against_target(fire_roll, target).outcome

    dexterity_save = build_saving_throw_roll_payload(sheet, "player-1", AbilityType.DEXTERITY)
    strength_save = build_saving_throw_roll_payload(sheet, "player-1", AbilityType.STRENGTH)
    assert [part.source for part in dexterity_save.modifierBreakdown] == ["Dexterity"]
    assert [part.source for part in strength_save.modifierBreakdown] == ["Strength", "Proficiency"]
    assert saving_throw_total(sheet, AbilityType.DEXTERITY) == 11
    assert saving_throw_total(sheet, AbilityType.STRENGTH) == 16
    sheet.savingThrows = []
    assert [part.source for part in build_saving_throw_roll_payload(sheet, "player-1", AbilityType.STRENGTH).modifierBreakdown] == ["Strength"]


def test_resolution_branches_cover_miss_heal_temp_hp_and_defense_text(monkeypatch) -> None:
    monkeypatch.setattr("dnd_board.character_sheet.random.randint", lambda minimum, maximum: 4)
    sheet = basic_sheet()
    target = basic_sheet()
    target.armorClass = 99
    target.hp = HitPoints(current=8, max=20, temporary=10)

    miss_roll = build_attack_roll_payload(
        sheet,
        "player-1",
        AttackAction(id="club", name="Club", ability=AbilityType.STRENGTH, damageDiceCount=1, damageDiceType=DiceType.D4),
    )
    assert resolve_roll_against_target(miss_roll, target).outcome == "misses"

    heal_roll = build_roll_action_payload(
        sheet,
        "player-1",
        RollSource(SheetSectionType.ABILITIES, "heal", "heal"),
        RollAction(AbilityType.STRENGTH, AbilityType.STRENGTH, 1, DiceType.D6, resolution=RollResolutionMode.HEAL_SELF),
    )
    assert resolve_roll_against_target(heal_roll, target).targetHp.current == 12

    temp_roll = build_roll_action_payload(
        sheet,
        "player-1",
        RollSource(SheetSectionType.ABILITIES, "temp", "temp"),
        RollAction(AbilityType.STRENGTH, AbilityType.STRENGTH, 1, DiceType.D6, resolution=RollResolutionMode.APPLY_TEMPORARY_HIT_POINTS),
    )
    assert resolve_roll_against_target(temp_roll, target).outcome == "keeps 10 temporary hit points"
    target.hp = HitPoints(current=8, max=20, temporary=0)
    assert resolve_roll_against_target(temp_roll, target).outcome == "gains 4 temporary hit points"

    damage_source = RollSource(SheetSectionType.ABILITIES, "damage", "damage")
    plain_damage_roll = build_roll_action_payload(
        sheet,
        "player-1",
        damage_source,
        RollAction(AbilityType.STRENGTH, AbilityType.STRENGTH, 1, DiceType.D6, resolution=RollResolutionMode.APPLY_DAMAGE),
    )
    assert resolve_roll_against_target(plain_damage_roll, target).outcome == "deals 4 damage"

    typed_damage_roll = build_roll_action_payload(
        sheet,
        "player-1",
        damage_source,
        RollAction(AbilityType.STRENGTH, AbilityType.STRENGTH, 1, DiceType.D6, resolution=RollResolutionMode.APPLY_DAMAGE, damageType=DamageType.COLD),
    )
    assert resolve_roll_against_target(typed_damage_roll, target).outcome == "deals 4 damage"

    target.damageResistances = [DamageType.SLASHING]
    resisted = resolve_roll_against_target(
        build_roll_action_payload(
            sheet,
            "player-1",
            damage_source,
            RollAction(AbilityType.STRENGTH, AbilityType.STRENGTH, 1, DiceType.D6, resolution=RollResolutionMode.APPLY_DAMAGE, damageType=DamageType.SLASHING),
        ),
        target,
    )
    assert resisted.outcome == "deals 2 damage after Slashing resistance"

    target.damageResistances = []
    target.damageVulnerabilities = [DamageType.SLASHING]
    assert resolve_roll_against_target(
        build_roll_action_payload(
            sheet,
            "player-1",
            damage_source,
            RollAction(AbilityType.STRENGTH, AbilityType.STRENGTH, 1, DiceType.D6, resolution=RollResolutionMode.APPLY_DAMAGE, damageType=DamageType.SLASHING),
        ),
        target,
    ).outcome == "deals 8 damage after Slashing vulnerability"

    static_modifier_roll = build_roll_action_payload(
        sheet,
        "player-1",
        damage_source,
        RollAction(AbilityType.STRENGTH, AbilityType.STRENGTH, 1, DiceType.D6, staticModifier=2),
    )
    assert static_modifier_roll.modifierBreakdown[0].source == "Modifier"

    ability_check = build_ability_check_roll_payload(sheet, "player-1", AbilityType.STRENGTH)
    assert ability_check.label == "Strength Check"


def test_fire_bolt_spell_rolls_use_spellcasting_and_cantrip_scaling(monkeypatch) -> None:
    monkeypatch.setattr("dnd_board.character_sheet.random.randint", lambda minimum, maximum: 3 if maximum in (6, 10) else 10)
    fire_bolt = spell_entry(SpellId.FIRE_BOLT)
    assert fire_bolt is not None

    damage_cases = {
        1: ("1d10", 3),
        5: ("2d10", 6),
        11: ("3d10", 9),
        17: ("4d10", 12),
    }
    for level, (expected_die, expected_total) in damage_cases.items():
        sheet = spell_sheet(level, [fire_bolt])
        damage_roll = build_spell_damage_roll_payload(sheet, "player-1", fire_bolt)

        assert damage_roll.source.section == SheetSectionType.SPELLS
        assert damage_roll.source.sourceId == "fireBolt"
        assert damage_roll.source.actionId == "damage-0"
        assert damage_roll.label == "Spell Damage"
        assert damage_roll.die == expected_die
        assert damage_roll.total == expected_total
        assert damage_roll.damageType == DamageType.FIRE

    attack_roll = build_spell_attack_roll_payload(spell_sheet(1, [fire_bolt]), "player-1", fire_bolt)

    assert attack_roll.source.section == SheetSectionType.SPELLS
    assert attack_roll.source.sourceId == "fireBolt"
    assert attack_roll.resolution == RollResolutionMode.ATTACK_VS_ARMOR_CLASS
    assert attack_roll.label == "Spell Attack"
    assert attack_roll.modifier == 5
    assert attack_roll.total == 15
    assert [(part.source, part.value) for part in attack_roll.modifierBreakdown] == [("Intelligence", 3), ("Proficiency", 2)]
    assert attack_roll.damageType == DamageType.FIRE

    assert spell_damage_effect_at(fire_bolt, -1) is None
    assert spell_damage_effect_at(replace(fire_bolt, effects=None), 0) is None
    with pytest.raises(ValueError, match="Spell damage effect not found"):
        build_spell_damage_roll_payload(spell_sheet(1, [fire_bolt]), "player-1", fire_bolt, effect_index=1)

    unscaled_spell = replace(fire_bolt, effects=[spell_damage_effect(2, DiceType.D6, DamageType.FORCE)])
    unscaled_roll = build_spell_damage_roll_payload(spell_sheet(20, [unscaled_spell]), "player-1", unscaled_spell)

    assert unscaled_roll.die == "2d6"
    assert unscaled_roll.total == 6

    boosted_spell = replace(
        fire_bolt,
        effects=[
            spell_damage_effect(
                1,
                DiceType.D6,
                DamageType.FORCE,
                static_bonus=2,
                bonus_ability=AbilityType.INTELLIGENCE,
                scaling=[spell_scaling(SpellScalingType.SPELL_SLOT_LEVEL, dice_count=1, dice_type=DiceType.D6)],
            )
        ],
    )
    boosted_roll = build_spell_damage_roll_payload(spell_sheet(20, [boosted_spell]), "player-1", boosted_spell)

    assert boosted_roll.die == "1d6"
    assert boosted_roll.modifier == 5
    assert boosted_roll.total == 8
    assert [(part.source, part.value) for part in boosted_roll.modifierBreakdown] == [("Spell", 2), ("Intelligence", 3)]


def test_burning_hands_spell_damage_scales_by_spell_slot(monkeypatch) -> None:
    monkeypatch.setattr("dnd_board.character_sheet.random.randint", lambda minimum, maximum: 2)
    burning_hands = wizard_spell_entry(SpellId.BURNING_HANDS)
    assert burning_hands is not None

    sheet = spell_sheet(5, [burning_hands])
    first_level = build_spell_damage_roll_payload(sheet, "player-1", burning_hands, spell_slot_level=1)
    second_level = build_spell_damage_roll_payload(sheet, "player-1", burning_hands, spell_slot_level=2)
    third_level = build_spell_damage_roll_payload(sheet, "player-1", burning_hands, spell_slot_level=3)
    below_level = build_spell_damage_roll_payload(sheet, "player-1", burning_hands, spell_slot_level=0)

    assert first_level.source.actionId == "damage-0-slot-1"
    assert first_level.die == "3d6"
    assert first_level.total == 6
    assert second_level.die == "4d6"
    assert second_level.total == 8
    assert third_level.die == "5d6"
    assert third_level.total == 10
    assert below_level.die == "3d6"
    assert below_level.total == 6
    assert {resource.spellSlotLevel for resource in sheet.resources if resource.spellSlotLevel is not None} == {1, 2, 3}


def test_additional_spell_damage_rolls_use_saves_conditions_and_scaling(monkeypatch) -> None:
    monkeypatch.setattr("dnd_board.character_sheet.random.randint", lambda minimum, maximum: 3)
    acid_splash = wizard_spell_entry(SpellId.ACID_SPLASH)
    call_lightning = spell_entry(SpellId.CALL_LIGHTNING)
    cone_of_cold = wizard_spell_entry(SpellId.CONE_OF_COLD)
    conjure_barrage = spell_entry(SpellId.CONJURE_BARRAGE)
    guiding_bolt = cleric_spell_entry(SpellId.GUIDING_BOLT)
    eldritch_blast = spell_entry(SpellId.ELDRITCH_BLAST)
    inflict_wounds = cleric_spell_entry(SpellId.INFLICT_WOUNDS)
    lightning_bolt = wizard_spell_entry(SpellId.LIGHTNING_BOLT)
    divine_smite = spell_entry(SpellId.DIVINE_SMITE)
    magic_missile = wizard_spell_entry(SpellId.MAGIC_MISSILE)
    mass_healing_word = spell_entry(SpellId.MASS_HEALING_WORD)
    prayer_of_healing = spell_entry(SpellId.PRAYER_OF_HEALING)
    ray_of_sickness = wizard_spell_entry(SpellId.RAY_OF_SICKNESS)
    searing_orb = spell_entry(SpellId.SEARING_ORB)
    shatter = wizard_spell_entry(SpellId.SHATTER)
    thunderwave = wizard_spell_entry(SpellId.THUNDERWAVE)
    vampiric_touch = wizard_spell_entry(SpellId.VAMPIRIC_TOUCH)
    wind_wall = spell_entry(SpellId.WIND_WALL)
    assert acid_splash is not None
    assert call_lightning is not None
    assert cone_of_cold is not None
    assert conjure_barrage is not None
    assert guiding_bolt is not None
    assert eldritch_blast is not None
    assert inflict_wounds is not None
    assert lightning_bolt is not None
    assert divine_smite is not None
    assert magic_missile is not None
    assert mass_healing_word is not None
    assert prayer_of_healing is not None
    assert ray_of_sickness is not None
    assert searing_orb is not None
    assert shatter is not None
    assert thunderwave is not None
    assert vampiric_touch is not None
    assert wind_wall is not None
    ice_knife = wizard_spell_entry(SpellId.ICE_KNIFE)
    assert ice_knife is not None

    acid_roll = build_spell_damage_roll_payload(spell_sheet(11, [acid_splash]), "player-1", acid_splash)
    call_lightning_roll = build_spell_damage_roll_payload(spell_sheet(5, [call_lightning]), "player-1", call_lightning, spell_slot_level=4)
    cone_of_cold_roll = build_spell_damage_roll_payload(spell_sheet(9, [cone_of_cold]), "player-1", cone_of_cold, spell_slot_level=6)
    conjure_barrage_roll = build_spell_damage_roll_payload(spell_sheet(5, [conjure_barrage]), "player-1", conjure_barrage, spell_slot_level=4)
    guiding_roll = build_spell_damage_roll_payload(spell_sheet(5, [guiding_bolt]), "player-1", guiding_bolt, spell_slot_level=3)
    eldritch_roll = build_spell_damage_roll_payload(spell_sheet(11, [eldritch_blast]), "player-1", eldritch_blast, instance_index=2)
    inflict_roll = build_spell_damage_roll_payload(spell_sheet(5, [inflict_wounds]), "player-1", inflict_wounds, spell_slot_level=2)
    lightning_roll = build_spell_damage_roll_payload(spell_sheet(5, [lightning_bolt]), "player-1", lightning_bolt, spell_slot_level=4)
    divine_smite_roll = build_spell_damage_roll_payload(spell_sheet(5, [divine_smite]), "player-1", divine_smite, effect_index=0, spell_slot_level=3)
    divine_smite_bonus_roll = build_spell_damage_roll_payload(spell_sheet(5, [divine_smite]), "player-1", divine_smite, effect_index=1)
    ice_target_roll = build_spell_damage_roll_payload(spell_sheet(5, [ice_knife]), "player-1", ice_knife, effect_index=0)
    ice_blast_roll = build_spell_damage_roll_payload(spell_sheet(5, [ice_knife]), "player-1", ice_knife, effect_index=1, spell_slot_level=2)
    missile_roll = build_spell_damage_roll_payload(spell_sheet(5, [magic_missile]), "player-1", magic_missile, spell_slot_level=3, instance_index=4)
    mass_healing_roll = build_spell_healing_roll_payload(spell_sheet(5, [mass_healing_word]), "player-1", mass_healing_word, spell_slot_level=4)
    prayer_roll = build_spell_healing_roll_payload(spell_sheet(5, [prayer_of_healing]), "player-1", prayer_of_healing, spell_slot_level=4)
    ray_roll = build_spell_damage_roll_payload(spell_sheet(5, [ray_of_sickness]), "player-1", ray_of_sickness, spell_slot_level=3)
    searing_orb_roll = build_spell_damage_roll_payload(spell_sheet(5, [searing_orb]), "player-1", searing_orb, spell_slot_level=4)
    shatter_roll = build_spell_damage_roll_payload(spell_sheet(5, [shatter]), "player-1", shatter)
    thunderwave_roll = build_spell_damage_roll_payload(spell_sheet(5, [thunderwave]), "player-1", thunderwave, spell_slot_level=2)
    vampiric_roll = build_spell_damage_roll_payload(spell_sheet(5, [vampiric_touch]), "player-1", vampiric_touch, spell_slot_level=4)
    wind_wall_roll = build_spell_damage_roll_payload(spell_sheet(5, [wind_wall]), "player-1", wind_wall)

    assert acid_roll.die == "3d6"
    assert acid_roll.total == 9
    assert acid_roll.damageType == DamageType.ACID
    assert acid_roll.damageSavingThrow == AbilityType.DEXTERITY
    assert acid_roll.damageSaveOutcome == SpellSaveOutcome.NEGATES

    assert call_lightning_roll.label == "Bolt Damage"
    assert call_lightning_roll.die == "4d10"
    assert call_lightning_roll.total == 12
    assert call_lightning_roll.damageType == DamageType.LIGHTNING
    assert call_lightning_roll.damageSavingThrow == AbilityType.DEXTERITY
    assert call_lightning_roll.damageSaveOutcome == SpellSaveOutcome.HALF_DAMAGE

    assert cone_of_cold_roll.die == "9d8"
    assert cone_of_cold_roll.total == 27
    assert cone_of_cold_roll.damageType == DamageType.COLD
    assert cone_of_cold_roll.damageSavingThrow == AbilityType.CONSTITUTION
    assert cone_of_cold_roll.damageSaveOutcome == SpellSaveOutcome.HALF_DAMAGE

    assert conjure_barrage_roll.die == "6d8"
    assert conjure_barrage_roll.total == 18
    assert conjure_barrage_roll.damageType == DamageType.FORCE
    assert conjure_barrage_roll.damageSavingThrow == AbilityType.DEXTERITY
    assert conjure_barrage_roll.damageSaveOutcome == SpellSaveOutcome.HALF_DAMAGE

    assert guiding_roll.die == "6d6"
    assert guiding_roll.total == 18
    assert guiding_roll.damageType == DamageType.RADIANT

    assert eldritch_roll.source.actionId == "damage-0-instance-2"
    assert eldritch_roll.label == "Beam 3 Damage"
    assert eldritch_roll.die == "1d10"
    assert eldritch_roll.total == 3
    assert eldritch_roll.damageType == DamageType.FORCE
    assert eldritch_blast.effects is not None
    assert scaled_spell_effect_instance_count(eldritch_blast.effects[0], spell_sheet(1, [eldritch_blast]), eldritch_blast.level) == 1
    assert scaled_spell_effect_instance_count(eldritch_blast.effects[0], spell_sheet(5, [eldritch_blast]), eldritch_blast.level) == 2
    assert scaled_spell_effect_instance_count(eldritch_blast.effects[0], spell_sheet(11, [eldritch_blast]), eldritch_blast.level) == 3
    assert scaled_spell_effect_instance_count(eldritch_blast.effects[0], spell_sheet(17, [eldritch_blast]), eldritch_blast.level) == 4
    with pytest.raises(ValueError, match="Spell damage instance not found"):
        build_spell_damage_roll_payload(spell_sheet(11, [eldritch_blast]), "player-1", eldritch_blast, instance_index=3)

    assert inflict_roll.die == "3d10"
    assert inflict_roll.total == 9
    assert inflict_roll.damageType == DamageType.NECROTIC
    assert inflict_roll.damageSavingThrow == AbilityType.CONSTITUTION
    assert inflict_roll.damageSaveOutcome == SpellSaveOutcome.HALF_DAMAGE

    assert lightning_roll.die == "9d6"
    assert lightning_roll.total == 27
    assert lightning_roll.damageType == DamageType.LIGHTNING
    assert lightning_roll.damageSavingThrow == AbilityType.DEXTERITY
    assert lightning_roll.damageSaveOutcome == SpellSaveOutcome.HALF_DAMAGE

    assert divine_smite_roll.label == "Smite Damage"
    assert divine_smite_roll.die == "4d8"
    assert divine_smite_roll.total == 12
    assert divine_smite_roll.damageType == DamageType.RADIANT
    assert divine_smite_bonus_roll.label == "Fiend/Undead Bonus Damage"
    assert divine_smite_bonus_roll.die == "1d8"
    assert divine_smite_bonus_roll.total == 3
    assert divine_smite_bonus_roll.damageType == DamageType.RADIANT
    assert divine_smite_bonus_roll.targetCreatureTypes == [CreatureType.FIEND, CreatureType.UNDEAD]

    assert ice_target_roll.label == "Target Damage"
    assert ice_target_roll.die == "1d10"
    assert ice_target_roll.damageType == DamageType.PIERCING
    assert ice_blast_roll.label == "Blast Damage"
    assert ice_blast_roll.die == "3d6"
    assert ice_blast_roll.damageType == DamageType.COLD
    assert ice_blast_roll.damageSavingThrow == AbilityType.DEXTERITY
    assert ice_blast_roll.damageSaveOutcome == SpellSaveOutcome.NEGATES

    assert missile_roll.source.actionId == "damage-0-slot-3-instance-4"
    assert missile_roll.label == "Dart 5 Damage"
    assert missile_roll.die == "1d4"
    assert missile_roll.modifier == 1
    assert missile_roll.total == 4
    assert missile_roll.damageType == DamageType.FORCE
    assert [(part.source, part.value) for part in missile_roll.modifierBreakdown] == [("Spell", 1)]
    assert magic_missile.effects is not None
    assert scaled_spell_effect_instance_count(magic_missile.effects[0], spell_sheet(5, [magic_missile]), magic_missile.level, 3) == 5

    assert mass_healing_roll.die == "3d4"
    assert mass_healing_roll.total == 12
    assert mass_healing_roll.resolution == RollResolutionMode.HEAL_SELF

    assert prayer_roll.die == "4d8"
    assert prayer_roll.total == 15
    assert prayer_roll.resolution == RollResolutionMode.HEAL_SELF
    assert prayer_roll.restType == RestType.SHORT_REST

    assert shatter_roll.damageSavingThrow == AbilityType.CONSTITUTION
    assert shatter_roll.damageSaveDisadvantageCreatureTypes == [CreatureType.CONSTRUCT]
    with pytest.raises(ValueError, match="Spell damage instance not found"):
        build_spell_damage_roll_payload(spell_sheet(5, [magic_missile]), "player-1", magic_missile, spell_slot_level=3, instance_index=5)

    assert ray_roll.die == "4d8"
    assert ray_roll.total == 12
    assert ray_roll.damageType == DamageType.POISON
    assert ray_roll.conditionEffects is not None
    assert ray_roll.conditionEffects[0].condition == ConditionType.POISONED
    assert ray_roll.conditionEffects[0].mode == ConditionApplicationMode.DIRECT

    assert searing_orb_roll.die == "5d4"
    assert searing_orb_roll.total == 15
    assert searing_orb_roll.damageType == DamageType.RADIANT
    assert searing_orb_roll.damageSavingThrow is None
    assert searing_orb_roll.conditionEffects is None

    assert thunderwave_roll.die == "3d8"
    assert thunderwave_roll.total == 9
    assert thunderwave_roll.damageType == DamageType.THUNDER
    assert thunderwave_roll.damageSavingThrow == AbilityType.CONSTITUTION
    assert thunderwave_roll.damageSaveOutcome == SpellSaveOutcome.HALF_DAMAGE
    assert vampiric_roll.label == "Touch Damage"
    assert vampiric_roll.die == "4d6"
    assert vampiric_roll.total == 12
    assert vampiric_roll.damageType == DamageType.NECROTIC
    assert vampiric_roll.sourceHealing is not None
    assert vampiric_roll.sourceHealing.amount == SpellLinkedHealingAmount.HALF_DAMAGE_DEALT
    assert wind_wall_roll.die == "4d8"
    assert wind_wall_roll.total == 12
    assert wind_wall_roll.damageType == DamageType.BLUDGEONING
    assert wind_wall_roll.damageSavingThrow == AbilityType.STRENGTH
    assert wind_wall_roll.damageSaveOutcome == SpellSaveOutcome.HALF_DAMAGE


def test_tashas_hideous_laughter_spell_effect_roll_uses_wisdom_save_dc() -> None:
    tasha = wizard_spell_entry(SpellId.TASHA_S_HIDEOUS_LAUGHTER)
    command = spell_entry(SpellId.COMMAND)
    bless = spell_entry(SpellId.BLESS)
    blinding_smite = spell_entry(SpellId.BLINDING_SMITE)
    fear = spell_entry(SpellId.FEAR)
    hypnotic_pattern = spell_entry(SpellId.HYPNOTIC_PATTERN)
    searing_orb = spell_entry(SpellId.SEARING_ORB)
    stinking_cloud = spell_entry(SpellId.STINKING_CLOUD)
    assert tasha is not None
    assert command is not None
    assert bless is not None
    assert blinding_smite is not None
    assert fear is not None
    assert hypnotic_pattern is not None
    assert searing_orb is not None
    assert stinking_cloud is not None

    sheet = spell_sheet(5, [tasha])
    effect_roll = build_spell_condition_roll_payload(sheet, "player-1", tasha)
    command_roll = build_spell_condition_roll_payload(spell_sheet(5, [command]), "player-1", command, effect_index=3)
    bless_roll = build_spell_condition_roll_payload(spell_sheet(5, [bless]), "player-1", bless)
    blinding_roll = build_spell_condition_roll_payload(spell_sheet(5, [blinding_smite]), "player-1", blinding_smite)
    fear_roll = build_spell_condition_roll_payload(spell_sheet(5, [fear]), "player-1", fear)
    hypnotic_roll = build_spell_condition_roll_payload(spell_sheet(5, [hypnotic_pattern]), "player-1", hypnotic_pattern)
    searing_orb_roll = build_spell_condition_roll_payload(spell_sheet(5, [searing_orb]), "player-1", searing_orb)
    stinking_cloud_roll = build_spell_condition_roll_payload(spell_sheet(5, [stinking_cloud]), "player-1", stinking_cloud)

    assert effect_roll.source.section == SheetSectionType.SPELLS
    assert effect_roll.source.sourceId == "tashaSHideousLaughter"
    assert effect_roll.source.actionId == "condition-0"
    assert effect_roll.label == "Spell Effect"
    assert effect_roll.dice == []
    assert effect_roll.conditionEffects is not None
    assert [effect.condition for effect in effect_roll.conditionEffects] == [ConditionType.PRONE, ConditionType.INCAPACITATED]
    assert {effect.mode for effect in effect_roll.conditionEffects} == {ConditionApplicationMode.TARGET_SAVE}
    assert {effect.savingThrow for effect in effect_roll.conditionEffects} == {AbilityType.WISDOM}
    assert {effect.saveDc for effect in effect_roll.conditionEffects} == {14}
    assert {effect.removalTrigger for effect in effect_roll.conditionEffects} == {ConditionRemovalTrigger.AFTER_TAKING_DAMAGE}
    assert {effect.removalSavingThrow for effect in effect_roll.conditionEffects} == {AbilityType.WISDOM}
    assert {effect.removalSaveDc for effect in effect_roll.conditionEffects} == {14}
    assert {effect.removalAdvantage for effect in effect_roll.conditionEffects} == {True}
    assert command_roll.label == "Grovel Effect"
    assert command_roll.conditionEffects is not None
    assert [effect.condition for effect in command_roll.conditionEffects] == [ConditionType.COMMAND_GROVEL, ConditionType.PRONE]
    assert {effect.savingThrow for effect in command_roll.conditionEffects} == {AbilityType.WISDOM}
    assert bless_roll.label == "Bless Effect"
    assert bless_roll.conditionEffects is not None
    assert [effect.condition for effect in bless_roll.conditionEffects] == [ConditionType.BLESSED]
    assert {effect.mode for effect in bless_roll.conditionEffects} == {ConditionApplicationMode.DIRECT}
    assert {effect.savingThrow for effect in bless_roll.conditionEffects} == {None}
    assert blinding_roll.label == "Blind Effect"
    assert blinding_roll.conditionEffects is not None
    assert blinding_roll.conditionEffects[0].condition == ConditionType.BLINDED
    assert blinding_roll.conditionEffects[0].savingThrow == AbilityType.CONSTITUTION
    assert blinding_roll.conditionEffects[0].saveDc == 14
    assert fear_roll.label == "Fear Effect"
    assert fear_roll.conditionEffects is not None
    assert fear_roll.conditionEffects[0].condition == ConditionType.FRIGHTENED
    assert fear_roll.conditionEffects[0].savingThrow == AbilityType.WISDOM
    assert hypnotic_roll.label == "Pattern Effect"
    assert hypnotic_roll.conditionEffects is not None
    assert [effect.condition for effect in hypnotic_roll.conditionEffects] == [ConditionType.CHARMED, ConditionType.INCAPACITATED]
    assert {effect.savingThrow for effect in hypnotic_roll.conditionEffects} == {AbilityType.WISDOM}
    assert {effect.removalTrigger for effect in hypnotic_roll.conditionEffects} == {ConditionRemovalTrigger.AFTER_TAKING_DAMAGE}
    assert searing_orb_roll.label == "Blind Effect"
    assert searing_orb_roll.conditionEffects is not None
    assert searing_orb_roll.conditionEffects[0].condition == ConditionType.BLINDED
    assert searing_orb_roll.conditionEffects[0].mode == ConditionApplicationMode.TARGET_SAVE
    assert searing_orb_roll.conditionEffects[0].savingThrow == AbilityType.CONSTITUTION
    assert searing_orb_roll.conditionEffects[0].saveDc == 14
    assert stinking_cloud_roll.label == "Nauseate Effect"
    assert stinking_cloud_roll.conditionEffects is not None
    assert stinking_cloud_roll.conditionEffects[0].condition == ConditionType.POISONED
    assert stinking_cloud_roll.conditionEffects[0].mode == ConditionApplicationMode.TARGET_SAVE
    assert stinking_cloud_roll.conditionEffects[0].savingThrow == AbilityType.CONSTITUTION
    assert stinking_cloud_roll.conditionEffects[0].saveDc == 14

    assert spell_condition_effect_at(tasha, -1) is None
    assert spell_condition_effect_at(replace(tasha, effects=None), 0) is None
    with pytest.raises(ValueError, match="Spell condition effect not found"):
        build_spell_condition_roll_payload(sheet, "player-1", replace(tasha, effects=[]))


def test_typed_json_and_formatter_edge_cases(monkeypatch) -> None:
    assert typed_json_to_value(typed_json_from_value([1, 2]), list[int]) == [1, 2]
    assert typed_json_to_value(typed_json_from_value([1, 2])) == [1, 2]
    assert typed_json_to_value(typed_json_from_value({"one": 1}), dict[str, int]) == {"one": 1}
    assert typed_json_to_value(typed_json_from_value({"one": 1})) == {"one": 1}
    assert typed_json_to_value({"$type": "AbilityScores", "fields": "bad"}, AbilityScores) is None
    assert typed_json_to_value({"$type": "AbilityScores", "fields": {}}, AbilityScores) is None
    assert typed_json_to_value({"$type": "int", "value": "bad"}, int) is None
    assert typed_json_to_value({"$type": "str", "value": "free"}) == "free"
    assert typed_json_to_value({"$type": "float", "value": 1.5}) == 1.5
    assert typed_json_to_value({"$type": "bool", "value": True}) is True
    assert typed_json_from_value(None) == {"$type": "None", "value": None}
    assert typed_json_from_value(True) == {"$type": "bool", "value": True}
    assert typed_json_from_value(1.5) == {"$type": "float", "value": 1.5}
    assert enum_value(AbilityType, None) is None
    assert enum_value(AbilityType, "not-real") is None
    assert value_matches_type(["x"], list[str]) is True
    assert value_matches_type({"x": 1}, dict[str, int]) is True
    assert value_matches_type("x", str | int) is True
    assert value_matches_type(True, bool) is True
    assert value_matches_type(1.5, float) is True
    assert value_matches_type(1, object()) is True

    monkeypatch.setattr("dnd_board.character_sheet.typed_json_registry", lambda: {"UnsupportedModel": str})
    assert typed_json_to_value({"$type": "UnsupportedModel", "value": "x"}) is None

    try:
        typed_json_from_value(object())
    except TypeError as error:
        assert "Unsupported typed JSON value" in str(error)
    else:
        raise AssertionError("expected unsupported typed JSON values to raise TypeError")


def test_remaining_display_and_input_helpers_cover_edge_cases() -> None:
    assert proficiency_multiplier(None) == 0
    assert proficiency_multiplier(ProficiencyLevel.EXPERTISE) == 2
    assert spell_area_label(SpellLineArea(lengthFeet=30, widthFeet=5)) == "30 ft line x 5 ft"
    assert spell_area_label(object()) == ""
    with pytest.raises(ValueError):
        clamped_ability_score("31")
    assert optional_text(None, 3) is None
    assert text_list("alpha") == []


def test_sheet_configuration_and_serializers_cover_wrapper_paths(monkeypatch) -> None:
    monkeypatch.setattr("dnd_board.character_sheet.random.randint", lambda minimum, maximum: 5)
    trait = SheetFeature("trait", "Trait", "Config", TimeEconomy.PASSIVE, "Configured trait")
    feature = SheetFeature("feature", "Feature", "Config", TimeEconomy.PASSIVE, "Configured feature")
    feat = SheetFeature("feat", "Feat", "Config", TimeEconomy.PASSIVE, "Configured feat")
    sheet = build_character_sheet(
        token_id="configured",
        kind=TokenKind.CHARACTER,
        name="Configured",
        owner="player-1",
        avatar_url=None,
        party_member=PartyMember(
            id="configured",
            name="Configured",
            owner="player-1",
            avatarUrl=None,
            maxHp=12,
            abilityScores=AbilityScores(strength=10, dexterity=10, constitution=10, intelligence=10, wisdom=10, charisma=10),
            sheet=PartyMemberSheet(
                classes=[CharacterClassLevel(name=ClassType.FIGHTER, level=1)],
                traits=[trait],
                features=[feature],
                feats=[feat],
            ),
        ),
        current_hp=None,
        resource_overrides={},
    )
    roll = build_saving_throw_roll_payload(sheet, "player-1", AbilityType.STRENGTH)
    resolution = resolve_roll_against_target(roll, sheet)
    entry = RollLogEntry("entry", RollLogEntryType.ROLL_RESOLVED, 123, roll, resolution)

    assert {"trait", "feature", "feat"} <= {feature.id for feature in sheet.features}
    assert roll_payload_to_dict(roll)["source"]["section"] == "abilityScores"
    assert roll_resolution_to_dict(resolution)["targetName"] == "Configured"
    assert roll_log_entry_to_dict(entry)["entryType"] == "rollResolved"
    assert (
        build_character_sheet(
            token_id="generated",
            kind=TokenKind.ASSET,
            name="Generated",
            owner="dm",
            avatar_url=None,
            party_member=None,
            current_hp=None,
            resource_overrides={},
            equipment_slot_overrides={},
        ).characterClass.name
        == ClassType.CREATURE
    )
    assert generated_ability_scores("seed") == generated_ability_scores("seed")
    assert generated_max_hp("seed", AbilityScores(10, 10, 10, 10, 10, 10)) >= 1


def basic_sheet():
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
            maxHp=20,
            abilityScores=AbilityScores(strength=16, dexterity=12, constitution=14, intelligence=10, wisdom=10, charisma=10),
            sheet=PartyMemberSheet(classes=[CharacterClassLevel(name=ClassType.FIGHTER, level=5)]),
        ),
        current_hp=None,
        resource_overrides={},
    )


def spell_sheet(level, spells):
    return build_character_sheet(
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
            abilityScores=AbilityScores(strength=8, dexterity=12, constitution=14, intelligence=16, wisdom=10, charisma=10),
            sheet=PartyMemberSheet(classes=[CharacterClassLevel(name=ClassType.WIZARD, level=level)], spells=spells),
        ),
        current_hp=None,
        resource_overrides={},
    )
