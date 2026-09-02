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
    SpellRangeType,
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
    resolve_roll_against_target,
    RollSource,
    armor_item_class,
    clamped_ability_score,
    enum_value,
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
    text_list,
    to_float,
    typed_json_from_value,
    typed_json_to_value,
    value_matches_type,
    build_ability_check_roll_payload,
)
from dnd_board.rules.classes.fighter.base import FighterSubclassType
from dnd_board.rules.spells import spell_damage_effect, spell_entry, spell_scaling, wizard_spell_entry


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


def test_tashas_hideous_laughter_spell_effect_roll_uses_wisdom_save_dc() -> None:
    tasha = wizard_spell_entry(SpellId.TASHA_S_HIDEOUS_LAUGHTER)
    assert tasha is not None

    sheet = spell_sheet(5, [tasha])
    effect_roll = build_spell_condition_roll_payload(sheet, "player-1", tasha)

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
