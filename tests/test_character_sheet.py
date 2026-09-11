from dataclasses import replace

import pytest

from dnd_board.character_sheet import (
    AbilityScores,
    AbilityType,
    AttackAction,
    AttackDamageAbilityModifierMode,
    AttackActionType,
    CharacterClassLevel,
    ClassType,
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
    RollDamageComponent,
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
    build_spell_temporary_hit_points_roll_payload,
    build_true_strike_attack_roll_payload,
    build_true_strike_damage_roll_payload,
    resolve_roll_against_target,
    RollSource,
    ability_modifier,
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
    spell_target_range_label,
    true_strike_weapon_attacks,
    shillelagh_weapon_attacks,
    text_list,
    to_float,
    typed_json_from_value,
    typed_json_to_value,
    value_matches_type,
    build_ability_check_roll_payload,
    condition_adjusted_armor_class,
    condition_adjusted_speed,
    condition_adjusted_speed_for_exhaustion,
    condition_armor_class_bonus,
)
from dnd_board.rules.classes.fighter.base import FighterSubclassType
from dnd_board.rules.shared.character_effects import added_condition_types, condition_change_effects
from dnd_board.rules.shared.effects import (
    ApplyEffect,
    ConditionChangeEffect,
    ConditionOperation,
    DifficultyClass,
    DifficultyClassType,
    EndingConditionType,
    FeatureMechanics,
    SavingThrow,
    SavingThrowEffect,
    SequenceEffect,
)
from dnd_board.rules.spells import cleric_spell_entry, paladin_spell_entry, spell_damage_effect, spell_entry, spell_scaling, wizard_spell_entry


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


def test_roll_action_payloads_cover_modifier_and_native_effect_branches(monkeypatch) -> None:
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
            mechanics=FeatureMechanics(activatedEffects=[SavingThrowEffect(
                SavingThrow(AbilityType.WISDOM, DifficultyClass(DifficultyClassType.FIXED, fixedValue=14)),
                onFailure=SequenceEffect([
                    ApplyEffect(ConditionChangeEffect(ConditionType.PRONE, ConditionOperation.ADD)),
                    ApplyEffect(ConditionChangeEffect(ConditionType.STUNNED, ConditionOperation.ADD)),
                ]),
            )]),
        ),
    )
    condition_roll.damageSaveSucceeded = False
    resolution = resolve_roll_against_target(condition_roll, sheet)

    assert proficiency_roll.modifierBreakdown[0].source == "Proficiency"
    assert strength_roll.modifierBreakdown[0].source == "Strength"
    assert class_level_roll.modifierBreakdown[0].source == "Class Level"
    assert condition_roll.damageSaveDc == 14
    assert ConditionType.PRONE in resolution.targetConditions
    assert ConditionType.STUNNED in resolution.targetConditions


def test_roll_action_native_save_is_embedded_in_pending_effect() -> None:
    sheet = basic_sheet()
    action = RollAction(
        AbilityType.STRENGTH,
        AbilityType.STRENGTH,
        1,
        DiceType.D6,
        resolution=RollResolutionMode.APPLY_DAMAGE,
        mechanics=FeatureMechanics(activatedEffects=[SavingThrowEffect(
            SavingThrow(AbilityType.STRENGTH, DifficultyClass(DifficultyClassType.FIXED, fixedValue=14)),
            onFailure=ApplyEffect(ConditionChangeEffect(ConditionType.PRONE, ConditionOperation.ADD)),
        )]),
    )

    roll = build_roll_action_payload(sheet, "player-1", RollSource(SheetSectionType.ABILITIES, "trip", "effect"), action)

    assert roll.label == "Strength"
    assert roll.damageSavingThrow == AbilityType.STRENGTH
    assert roll.damageSaveDc == 14
    assert roll.pendingEffect is not None


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
    hasted_sheet = replace(basic_sheet(), conditions=[ConditionType.HASTED])
    hasted_dexterity_save_roll = build_saving_throw_roll_payload(hasted_sheet, "player-1", AbilityType.DEXTERITY)
    hasted_strength_save_roll = build_saving_throw_roll_payload(hasted_sheet, "player-1", AbilityType.STRENGTH)

    assert ("Blessed", 2) in [(part.source, part.value) for part in attack_roll.modifierBreakdown]
    assert ("Guidance", 2) not in [(part.source, part.value) for part in attack_roll.modifierBreakdown]
    assert ("Guidance", 2) in [(part.source, part.value) for part in check_roll.modifierBreakdown]
    assert ("Blessed", 2) in [(part.source, part.value) for part in save_roll.modifierBreakdown]
    assert ("Bane", -2) in [(part.source, part.value) for part in baned_attack_roll.modifierBreakdown]
    assert ("Bane", -2) in [(part.source, part.value) for part in baned_save_roll.modifierBreakdown]
    assert ("Slowed", -2) in [(part.source, part.value) for part in slowed_dexterity_save_roll.modifierBreakdown]
    assert ("Slowed", -2) not in [(part.source, part.value) for part in slowed_strength_save_roll.modifierBreakdown]
    assert hasted_dexterity_save_roll.die == "2d20kh1"
    assert hasted_dexterity_save_roll.dice == [10, 10]
    assert hasted_dexterity_save_roll.advantageConditions == [ConditionType.HASTED]
    assert hasted_strength_save_roll.die == "d20"
    assert hasted_strength_save_roll.advantageConditions is None
    half_cover_sheet = replace(basic_sheet(), conditions=[ConditionType.HALF_COVER])
    three_quarters_cover_sheet = replace(basic_sheet(), conditions=[ConditionType.THREE_QUARTERS_COVER])
    full_cover_sheet = replace(basic_sheet(), conditions=[ConditionType.FULL_COVER])
    half_cover_dexterity_save_roll = build_saving_throw_roll_payload(half_cover_sheet, "player-1", AbilityType.DEXTERITY)
    half_cover_strength_save_roll = build_saving_throw_roll_payload(half_cover_sheet, "player-1", AbilityType.STRENGTH)
    three_quarters_cover_dexterity_save_roll = build_saving_throw_roll_payload(three_quarters_cover_sheet, "player-1", AbilityType.DEXTERITY)
    full_cover_dexterity_save_roll = build_saving_throw_roll_payload(full_cover_sheet, "player-1", AbilityType.DEXTERITY)
    assert ("Half Cover", 2) in [(part.source, part.value) for part in half_cover_dexterity_save_roll.modifierBreakdown]
    assert ("Half Cover", 2) not in [(part.source, part.value) for part in half_cover_strength_save_roll.modifierBreakdown]
    assert ("Three Quarters Cover", 5) in [(part.source, part.value) for part in three_quarters_cover_dexterity_save_roll.modifierBreakdown]
    assert "Full Cover" not in [part.source for part in full_cover_dexterity_save_roll.modifierBreakdown]
    assert condition_armor_class_bonus([ConditionType.SHIELDED]) == 5
    assert condition_armor_class_bonus([ConditionType.SHIELDED, ConditionType.SHIELD_OF_FAITH, ConditionType.HASTED, ConditionType.SLOWED]) == 7
    assert condition_armor_class_bonus([ConditionType.HALF_COVER]) == 2
    assert condition_armor_class_bonus([ConditionType.THREE_QUARTERS_COVER]) == 5
    assert condition_armor_class_bonus([ConditionType.FULL_COVER]) == 0
    assert condition_adjusted_speed(30, [ConditionType.HASTED]) == 60
    assert condition_adjusted_speed(30, [ConditionType.SLOWED]) == 15
    assert condition_adjusted_speed(30, [ConditionType.LONGSTRIDER]) == 40
    assert condition_adjusted_speed(30, [ConditionType.HASTED, ConditionType.SLOWED, ConditionType.LONGSTRIDER]) == 40


def test_spell_conditions_modify_ability_checks_saves_and_damage_rolls(monkeypatch) -> None:
    monkeypatch.setattr("dnd_board.character_sheet.random.randint", lambda minimum, maximum: 5 if maximum == 20 else 3)
    enhanced = replace(basic_sheet(), conditions=[ConditionType.ENHANCE_ABILITY_DEXTERITY])
    enlarged = replace(basic_sheet(), conditions=[ConditionType.ENLARGED])
    reduced = replace(basic_sheet(), conditions=[ConditionType.REDUCED])
    enfeebled = replace(basic_sheet(), conditions=[ConditionType.RAY_OF_ENFEEBLEMENT])

    enhanced_dexterity_check = build_ability_check_roll_payload(enhanced, "player-1", AbilityType.DEXTERITY)
    enhanced_strength_check = build_ability_check_roll_payload(enhanced, "player-1", AbilityType.STRENGTH)
    enlarged_strength_save = build_saving_throw_roll_payload(enlarged, "player-1", AbilityType.STRENGTH)
    reduced_strength_check = build_ability_check_roll_payload(reduced, "player-1", AbilityType.STRENGTH)
    enfeebled_strength_save = build_saving_throw_roll_payload(enfeebled, "player-1", AbilityType.STRENGTH)
    enlarged_damage = build_damage_roll_payload(enlarged, "player-1", enlarged.attacks[0])
    reduced_damage = build_damage_roll_payload(reduced, "player-1", reduced.attacks[0])
    enfeebled_damage = build_damage_roll_payload(enfeebled, "player-1", enfeebled.attacks[0])
    fire_bolt = spell_entry(SpellId.FIRE_BOLT)
    assert fire_bolt is not None
    enfeebled_spell_damage = build_spell_damage_roll_payload(replace(spell_sheet(5, [fire_bolt]), conditions=[ConditionType.RAY_OF_ENFEEBLEMENT]), "player-1", fire_bolt)

    assert enhanced_dexterity_check.die == "2d20kh1"
    assert enhanced_dexterity_check.advantageConditions == [ConditionType.ENHANCE_ABILITY_DEXTERITY]
    assert enhanced_strength_check.die == "d20"
    assert enlarged_strength_save.advantageConditions == [ConditionType.ENLARGED]
    assert reduced_strength_check.disadvantageConditions == [ConditionType.REDUCED]
    assert enfeebled_strength_save.disadvantageConditions == [ConditionType.RAY_OF_ENFEEBLEMENT]
    assert ("Enlarged", 3) in [(part.source, part.value) for part in enlarged_damage.modifierBreakdown]
    assert ("Reduced", -3) in [(part.source, part.value) for part in reduced_damage.modifierBreakdown]
    assert ("Ray Of Enfeeblement", -3) in [(part.source, part.value) for part in enfeebled_damage.modifierBreakdown]
    assert enfeebled_spell_damage.damageComponents is not None
    assert ("Ray Of Enfeeblement", -3) in [(part.source, part.value) for part in enfeebled_spell_damage.damageComponents[0].modifierBreakdown]


def test_reduced_damage_roll_keeps_minimum_one_damage(monkeypatch) -> None:
    rolls = iter([4, 2])
    monkeypatch.setattr("dnd_board.character_sheet.random.randint", lambda minimum, maximum: next(rolls))
    reduced = replace(basic_sheet(), conditions=[ConditionType.REDUCED])
    action = replace(reduced.attacks[0], damageAbilityModifier=AttackDamageAbilityModifierMode.EXCLUDED)

    roll = build_damage_roll_payload(reduced, "player-1", action)

    assert roll.total == 1
    assert [(part.source, part.value) for part in roll.modifierBreakdown[-2:]] == [("Reduced", -4), ("Reduced", 3)]
    assert roll.modifierBreakdown[-1].description == "Reduced damage can't be reduced below 1."


def test_calm_emotions_immunity_blocks_charmed_and_frightened_conditions() -> None:
    target = replace(basic_sheet(), conditions=[ConditionType.CALM_EMOTIONS_IMMUNITY])
    charmed = RollAction("charm", ConditionType.CHARMED, 0, DiceType.D4, mechanics=FeatureMechanics(activatedEffects=[ApplyEffect(ConditionChangeEffect(ConditionType.CHARMED, ConditionOperation.ADD))]))
    frightened = RollAction("fear", ConditionType.FRIGHTENED, 0, DiceType.D4, mechanics=FeatureMechanics(activatedEffects=[ApplyEffect(ConditionChangeEffect(ConditionType.FRIGHTENED, ConditionOperation.ADD))]))

    charmed_resolution = resolve_roll_against_target(build_roll_action_payload(basic_sheet(), "player-1", RollSource(SheetSectionType.ABILITIES, "charm", "effect"), charmed), target)
    frightened_resolution = resolve_roll_against_target(build_roll_action_payload(basic_sheet(), "player-1", RollSource(SheetSectionType.ABILITIES, "fear", "effect"), frightened), target)

    assert charmed_resolution.targetConditions == [ConditionType.CALM_EMOTIONS_IMMUNITY]
    assert "resists Charmed" in charmed_resolution.outcome
    assert frightened_resolution.targetConditions == [ConditionType.CALM_EMOTIONS_IMMUNITY]
    assert "resists Frightened" in frightened_resolution.outcome


def test_conditions_modify_attack_roll_advantage_and_target_resolution(monkeypatch) -> None:
    rolls = iter([5, 15, 15, 5, 15, 5, 15, 5, 15, 5, 15, 5])
    monkeypatch.setattr("dnd_board.character_sheet.random.randint", lambda minimum, maximum: next(rolls))
    attacker = basic_sheet()
    invisible_attacker = replace(basic_sheet(), conditions=[ConditionType.INVISIBLE])
    blinded_attacker = replace(basic_sheet(), conditions=[ConditionType.BLINDED])
    see_invisibility_attacker = replace(basic_sheet(), conditions=[ConditionType.SEE_INVISIBILITY])
    target = replace(basic_sheet(), armorClass=18)
    blinded_target = replace(target, conditions=[ConditionType.BLINDED])
    invisible_target = replace(target, conditions=[ConditionType.INVISIBLE])
    see_invisibility_target = replace(target, conditions=[ConditionType.SEE_INVISIBILITY])

    invisible_roll = build_attack_roll_payload(invisible_attacker, "player-1", invisible_attacker.attacks[0])
    blinded_roll = build_attack_roll_payload(blinded_attacker, "player-1", blinded_attacker.attacks[0])
    target_advantage_resolution = resolve_roll_against_target(build_attack_roll_payload(attacker, "player-1", attacker.attacks[0]), blinded_target)
    target_disadvantage_resolution = resolve_roll_against_target(build_attack_roll_payload(attacker, "player-1", attacker.attacks[0]), invisible_target)
    seen_invisible_attacker_resolution = resolve_roll_against_target(build_attack_roll_payload(invisible_attacker, "player-1", invisible_attacker.attacks[0]), see_invisibility_target)
    see_invisibility_attacker_resolution = resolve_roll_against_target(build_attack_roll_payload(see_invisibility_attacker, "player-1", see_invisibility_attacker.attacks[0]), invisible_target)

    assert invisible_roll.die == "2d20kh1"
    assert invisible_roll.dice == [5, 15]
    assert invisible_roll.advantageConditions == [ConditionType.INVISIBLE]
    assert blinded_roll.die == "2d20kl1"
    assert blinded_roll.dice == [15, 5]
    assert blinded_roll.disadvantageConditions == [ConditionType.BLINDED]
    assert target_advantage_resolution.roll.die == "2d20kh1"
    assert target_advantage_resolution.roll.dice == [15, 5]
    assert target_advantage_resolution.roll.advantageConditions == [ConditionType.BLINDED]
    assert target_advantage_resolution.outcome == "hits"
    assert target_disadvantage_resolution.roll.die == "2d20kl1"
    assert target_disadvantage_resolution.roll.dice == [15, 5]
    assert target_disadvantage_resolution.roll.disadvantageConditions == [ConditionType.INVISIBLE]
    assert target_disadvantage_resolution.outcome == "misses"
    assert seen_invisible_attacker_resolution.roll.die == "d20"
    assert seen_invisible_attacker_resolution.roll.dice == [15]
    assert seen_invisible_attacker_resolution.roll.advantageConditions is None
    assert seen_invisible_attacker_resolution.outcome == "hits"
    assert see_invisibility_attacker_resolution.roll.die == "d20"
    assert see_invisibility_attacker_resolution.roll.dice == [15]
    assert see_invisibility_attacker_resolution.roll.disadvantageConditions is None
    assert see_invisibility_attacker_resolution.outcome == "hits"


def test_conditions_apply_speed_resistance_and_save_effects(monkeypatch) -> None:
    monkeypatch.setattr("dnd_board.character_sheet.random.randint", lambda minimum, maximum: 12)
    restrained = replace(basic_sheet(), conditions=[ConditionType.RESTRAINED])
    paralyzed = replace(basic_sheet(), conditions=[ConditionType.PARALYZED])
    petrified = replace(basic_sheet(), conditions=[ConditionType.PETRIFIED])
    poisoned = replace(basic_sheet(), conditions=[ConditionType.POISONED])
    warded = replace(basic_sheet(), conditions=[ConditionType.WARDING_BOND])

    restrained_dexterity_save = build_saving_throw_roll_payload(restrained, "player-1", AbilityType.DEXTERITY)
    restrained_strength_save = build_saving_throw_roll_payload(restrained, "player-1", AbilityType.STRENGTH)
    paralyzed_dexterity_save = build_saving_throw_roll_payload(paralyzed, "player-1", AbilityType.DEXTERITY)
    poisoned_check = build_ability_check_roll_payload(poisoned, "player-1", AbilityType.STRENGTH)
    warded_wisdom_save = build_saving_throw_roll_payload(warded, "player-1", AbilityType.WISDOM)

    assert condition_adjusted_speed(30, [ConditionType.HASTED, ConditionType.GRAPPLED]) == 0
    assert condition_adjusted_speed(30, [ConditionType.LONGSTRIDER, ConditionType.RESTRAINED]) == 0
    assert condition_adjusted_speed(30, [ConditionType.PARALYZED]) == 0
    assert restrained_dexterity_save.die == "2d20kl1"
    assert restrained_dexterity_save.disadvantageConditions == [ConditionType.RESTRAINED]
    assert restrained_strength_save.die == "d20"
    assert paralyzed_dexterity_save.modifierBreakdown[-1].source == "Paralyzed"
    assert "Automatically fails Dexterity saving throws." in paralyzed_dexterity_save.modifierBreakdown[-1].description
    assert poisoned_check.die == "2d20kl1"
    assert poisoned_check.disadvantageConditions == [ConditionType.POISONED]
    assert effective_damage_resistances(petrified) == set(DamageType)
    assert condition_armor_class_bonus([ConditionType.WARDING_BOND]) == 1
    assert warded_wisdom_save.modifierBreakdown[-1].source == "Warding Bond"
    assert warded_wisdom_save.modifierBreakdown[-1].value == 1
    assert effective_damage_resistances(warded) == set(DamageType)


def test_exhaustion_levels_modify_rolls_and_speed(monkeypatch) -> None:
    monkeypatch.setattr("dnd_board.character_sheet.random.randint", lambda minimum, maximum: 12)
    level_one = replace(basic_sheet(), conditions=[ConditionType.EXHAUSTION], exhaustionLevel=1)
    level_three = replace(basic_sheet(), conditions=[ConditionType.EXHAUSTION], exhaustionLevel=3)

    check_roll = build_ability_check_roll_payload(level_one, "player-1", AbilityType.STRENGTH)
    attack_roll = build_attack_roll_payload(level_three, "player-1", level_three.attacks[0])
    save_roll = build_saving_throw_roll_payload(level_three, "player-1", AbilityType.WISDOM)

    assert check_roll.die == "d20"
    assert check_roll.modifierBreakdown[-1].source == "Exhaustion"
    assert check_roll.modifierBreakdown[-1].value == -2
    assert attack_roll.die == "d20"
    assert attack_roll.modifierBreakdown[-1].source == "Exhaustion"
    assert attack_roll.modifierBreakdown[-1].value == -6
    assert save_roll.die == "d20"
    assert save_roll.modifierBreakdown[-1].source == "Exhaustion"
    assert save_roll.modifierBreakdown[-1].value == -6
    assert condition_adjusted_speed_for_exhaustion(30, [], 1) == 25
    assert condition_adjusted_speed_for_exhaustion(30, [], 2) == 20
    assert condition_adjusted_speed_for_exhaustion(30, [ConditionType.LONGSTRIDER], 2) == 30
    assert condition_adjusted_speed_for_exhaustion(30, [ConditionType.HASTED], 2) == 50
    assert condition_adjusted_speed_for_exhaustion(30, [ConditionType.LONGSTRIDER], 6) == 10


def test_mage_armor_condition_uses_spell_armor_class_only_without_worn_armor() -> None:
    sheet = replace(basic_sheet(), conditions=[ConditionType.MAGE_ARMOR])
    armored = replace(
        sheet,
        equipment=[EquipmentItem(id="leather", name="Leather", itemType=EquipmentType.ARMOR, slot=EquipmentSlot.ARMOR, armorCategory=ArmorCategory.LIGHT, armorClass=11)],
    )
    barkskin = replace(basic_sheet(), armorClass=14, conditions=[ConditionType.BARKSKIN])
    high_ac_barkskin = replace(basic_sheet(), armorClass=18, conditions=[ConditionType.BARKSKIN])

    assert condition_adjusted_armor_class(sheet) == max(sheet.armorClass, 13 + ability_modifier(sheet.abilityScores.dexterity))
    assert condition_adjusted_armor_class(armored) == armored.armorClass
    assert condition_adjusted_armor_class(barkskin) == 17
    assert condition_adjusted_armor_class(high_ac_barkskin) == 18


def test_blade_ward_subtracts_d4_from_incoming_attack_roll(monkeypatch) -> None:
    monkeypatch.setattr("dnd_board.character_sheet.random.randint", lambda minimum, maximum: 3 if maximum == 4 else 12)
    attacker = basic_sheet()
    target = replace(basic_sheet(), armorClass=16, conditions=[ConditionType.BLADE_WARD])

    resolution = resolve_roll_against_target(build_attack_roll_payload(attacker, "player-1", attacker.attacks[0]), target)

    assert resolution.roll.dice == [12]
    assert resolution.roll.modifierBreakdown[-1].source == "Blade Ward"
    assert resolution.roll.modifierBreakdown[-1].value == -3
    assert resolution.roll.total == 15
    assert resolution.outcome == "misses"


def test_active_damage_resistance_conditions_reduce_matching_damage_by_d4(monkeypatch) -> None:
    monkeypatch.setattr("dnd_board.character_sheet.random.randint", lambda minimum, maximum: 3 if maximum == 4 else 8)
    attacker = basic_sheet()
    target = replace(basic_sheet(), conditions=[ConditionType.RESISTANCE_FIRE])
    action = replace(attacker.attacks[0], damageDiceCount=1, damageDiceType=DiceType.D8, damageType=DamageType.FIRE, damageAbilityModifier=AttackDamageAbilityModifierMode.EXCLUDED, mechanics=None)

    roll = build_damage_roll_payload(attacker, "player-1", action)
    resolution = resolve_roll_against_target(roll, target)

    assert roll.total == 8
    assert resolution.targetHp.current == 15
    assert resolution.outcome == "deals 5 damage after Resistance Fire reduces damage by 3"


def test_true_damage_resistance_condition_halves_matching_damage(monkeypatch) -> None:
    monkeypatch.setattr("dnd_board.character_sheet.random.randint", lambda minimum, maximum: 8)
    attacker = basic_sheet()
    target = replace(basic_sheet(), conditions=[ConditionType.RESISTANT_FIRE])
    action = replace(attacker.attacks[0], damageDiceCount=1, damageDiceType=DiceType.D8, damageType=DamageType.FIRE, damageAbilityModifier=AttackDamageAbilityModifierMode.EXCLUDED, mechanics=None)

    roll = build_damage_roll_payload(attacker, "player-1", action)
    resolution = resolve_roll_against_target(roll, target)

    assert effective_damage_resistances(target) == {DamageType.FIRE}
    assert roll.total == 8
    assert resolution.targetHp.current == 16
    assert resolution.outcome == "deals 4 damage after Fire resistance"


def test_protection_from_poison_adds_true_poison_resistance_and_clears_poisoned(monkeypatch) -> None:
    monkeypatch.setattr("dnd_board.character_sheet.random.randint", lambda minimum, maximum: 8)
    attacker = basic_sheet()
    target = replace(basic_sheet(), conditions=[ConditionType.PROTECTION_FROM_POISON, ConditionType.POISONED])
    action = replace(attacker.attacks[0], damageDiceCount=1, damageDiceType=DiceType.D8, damageType=DamageType.POISON, damageAbilityModifier=AttackDamageAbilityModifierMode.EXCLUDED, mechanics=None)
    protection_roll = RollAction(
        id=SpellId.PROTECTION_FROM_POISON,
        name=SpellId.PROTECTION_FROM_POISON,
        diceCount=0,
        diceType=DiceType.D4,
        mechanics=spell_entry(SpellId.PROTECTION_FROM_POISON).mechanics,
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


def test_creature_type_limited_condition_only_applies_to_matching_targets() -> None:
    friends = spell_entry(SpellId.FRIENDS)
    assert friends is not None
    roll = build_spell_condition_roll_payload(spell_sheet(5, [friends]), "player-1", friends)
    undead = replace(basic_sheet(), creatureTypes=[CreatureType.UNDEAD])

    resolution = resolve_roll_against_target(roll, undead)

    assert roll.targetCreatureTypes == [CreatureType.HUMANOID]
    assert resolution.targetConditions == []
    assert resolution.outcome == "has no effect; target is not Humanoid"


def test_true_strike_uses_spellcasting_ability_with_proficient_weapon_and_scaling_bonus(monkeypatch) -> None:
    rolls = iter([10, 5, 3, 8, 4])
    monkeypatch.setattr("dnd_board.character_sheet.random.randint", lambda minimum, maximum: next(rolls))
    true_strike = wizard_spell_entry(SpellId.TRUE_STRIKE)
    assert true_strike is not None
    longsword = AttackAction("longsword", "Longsword", AbilityType.STRENGTH, 1, DiceType.D8, damageType=DamageType.SLASHING)
    unarmed = AttackAction("unarmed", "Unarmed Strike", AbilityType.STRENGTH, 1, DiceType.D4, damageType=DamageType.BLUDGEONING, attackType=AttackActionType.UNARMED_STRIKE)
    sheet = replace(
        spell_sheet(5, [true_strike]),
        attacks=[longsword, replace(longsword, id="club", name="Club", proficient=False), unarmed],
        equipment=[EquipmentItem(id="longsword", name="Longsword", itemType=EquipmentType.WEAPON, slot=EquipmentSlot.MAIN_HAND)],
    )

    eligible_attacks = true_strike_weapon_attacks(sheet)
    attack_roll = build_true_strike_attack_roll_payload(sheet, "player-1", true_strike, longsword, DamageType.RADIANT)
    damage_roll = build_true_strike_damage_roll_payload(sheet, "player-1", true_strike, longsword, DamageType.SLASHING)
    radiant_damage_roll = build_true_strike_damage_roll_payload(sheet, "player-1", true_strike, longsword, DamageType.RADIANT)

    assert [attack.id for attack in eligible_attacks] == ["longsword"]
    assert attack_roll.source.section == SheetSectionType.SPELLS
    assert attack_roll.source.sourceId == "trueStrike"
    assert attack_roll.label == "Attack Longsword"
    assert attack_roll.damageType == DamageType.RADIANT
    assert [(part.source, part.value) for part in attack_roll.modifierBreakdown] == [("Intelligence", 3), ("Proficiency", 3)]
    assert attack_roll.total == 16
    assert damage_roll.source.sourceId == "trueStrike"
    assert damage_roll.label == "Damage Longsword"
    assert damage_roll.damageType == DamageType.SLASHING
    assert damage_roll.die == "1d8+1d6"
    assert damage_roll.total == 11
    assert damage_roll.damageComponents is not None
    assert [(component.damageType, component.total) for component in damage_roll.damageComponents] == [(DamageType.SLASHING, 8), (DamageType.RADIANT, 3)]
    assert radiant_damage_roll.damageType == DamageType.RADIANT
    assert radiant_damage_roll.total == 15
    assert radiant_damage_roll.damageComponents is not None
    assert [(component.damageType, component.total) for component in radiant_damage_roll.damageComponents] == [(DamageType.RADIANT, 11), (DamageType.RADIANT, 4)]


def test_shillelagh_projects_to_wielded_proficient_club_or_quarterstaff(monkeypatch) -> None:
    rolls = iter([10, 5])
    monkeypatch.setattr("dnd_board.character_sheet.random.randint", lambda minimum, maximum: next(rolls))
    shillelagh = spell_entry(SpellId.SHILLELAGH)
    assert shillelagh is not None
    club = AttackAction("club", "Club", AbilityType.STRENGTH, 1, DiceType.D4, damageType=DamageType.BLUDGEONING)
    carried_staff = AttackAction("quarterstaff", "Quarterstaff", AbilityType.STRENGTH, 1, DiceType.D6, damageType=DamageType.BLUDGEONING)
    sheet = replace(
        spell_sheet(11, [shillelagh]),
        conditions=[ConditionType.SHILLELAGH],
        attacks=[club, carried_staff],
        equipment=[
            EquipmentItem(id="club", name="Club", itemType=EquipmentType.WEAPON, slot=EquipmentSlot.MAIN_HAND),
            EquipmentItem(id="quarterstaff", name="Quarterstaff", itemType=EquipmentType.WEAPON, slot=EquipmentSlot.CARRIED),
        ],
    )

    attack_roll = build_attack_roll_payload(sheet, "player-1", club)
    damage_roll = build_damage_roll_payload(sheet, "player-1", club)

    assert [attack.id for attack in shillelagh_weapon_attacks(sheet)] == ["club"]
    assert attack_roll.damageType == DamageType.FORCE
    assert [(part.source, part.value) for part in attack_roll.modifierBreakdown] == [("Intelligence", 3), ("Proficiency", 4)]
    assert attack_roll.total == 17
    assert damage_roll.damageType == DamageType.FORCE
    assert damage_roll.die == "1d12"
    assert damage_roll.total == 8


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

    target.hp = HitPoints(current=30, max=30, temporary=0)
    target.damageResistances = [DamageType.BLUDGEONING]
    target.damageVulnerabilities = [DamageType.COLD]
    mixed_damage_roll = replace(
        typed_damage_roll,
        total=20,
        damageType=DamageType.BLUDGEONING,
        damageSaveOutcome=SpellSaveOutcome.HALF_DAMAGE,
        damageSaveSucceeded=True,
        damageComponents=[
            RollDamageComponent(DamageType.BLUDGEONING, [5, 5], DiceType.D10, "2d10", 0, [], 10),
            RollDamageComponent(DamageType.COLD, [2, 2, 3, 3], DiceType.D6, "4d6", 0, [], 10),
        ],
    )
    mixed_resolution = resolve_roll_against_target(mixed_damage_roll, target)
    assert mixed_resolution.targetHp.current == 18
    assert mixed_resolution.outcome == "deals 12 damage (Bludgeoning 2 after successful save, resistance; Cold 10 after successful save, vulnerability)"

    rider = SavingThrowEffect(
        SavingThrow(AbilityType.DEXTERITY, DifficultyClass(DifficultyClassType.FIXED, fixedValue=14)),
        onFailure=ApplyEffect(ConditionChangeEffect(ConditionType.PRONE, ConditionOperation.ADD)),
    )
    passed_rider_roll = replace(typed_damage_roll, damageSaveOutcome=SpellSaveOutcome.HALF_DAMAGE, damageSaveSucceeded=True, pendingEffect=rider)
    failed_rider_roll = replace(passed_rider_roll, damageSaveSucceeded=False)
    assert ConditionType.PRONE not in resolve_roll_against_target(passed_rider_roll, target).targetConditions
    assert ConditionType.PRONE in resolve_roll_against_target(failed_rider_roll, target).targetConditions

    static_modifier_roll = build_roll_action_payload(
        sheet,
        "player-1",
        damage_source,
        RollAction(AbilityType.STRENGTH, AbilityType.STRENGTH, 1, DiceType.D6, staticModifier=2),
    )
    assert static_modifier_roll.modifierBreakdown[0].source == "Modifier"

    ability_check = build_ability_check_roll_payload(sheet, "player-1", AbilityType.STRENGTH)
    assert ability_check.label == "Strength Check"


def test_burning_hands_damage_uses_save_branch_and_slot_scaled_roll(monkeypatch) -> None:
    monkeypatch.setattr("dnd_board.character_sheet.random.randint", lambda minimum, maximum: 4)
    burning_hands = wizard_spell_entry(SpellId.BURNING_HANDS)
    assert burning_hands is not None
    sheet = spell_sheet(3, [burning_hands])
    target = basic_sheet()
    target.hp = HitPoints(current=30, max=30, temporary=0)
    damage_roll = replace(
        build_spell_damage_roll_payload(sheet, "player-1", burning_hands, spell_slot_level=2),
        damageSaveSucceeded=True,
    )

    resolution = resolve_roll_against_target(damage_roll, target)

    assert damage_roll.die == "4d6"
    assert damage_roll.total == 16
    assert resolution.targetHp.current == 22
    assert resolution.outcome == "deals 8 damage after successful save"


def test_wrathful_smite_save_only_controls_frightened_rider(monkeypatch) -> None:
    monkeypatch.setattr("dnd_board.character_sheet.random.randint", lambda minimum, maximum: 4)
    wrathful_smite = paladin_spell_entry(SpellId.WRATHFUL_SMITE)
    assert wrathful_smite is not None
    caster = spell_sheet(3, [wrathful_smite])
    target = replace(basic_sheet(), hp=HitPoints(current=30, max=30, temporary=0))

    passed_roll = replace(
        build_spell_damage_roll_payload(caster, "player-1", wrathful_smite),
        damageSaveSucceeded=True,
    )
    failed_roll = replace(passed_roll, damageSaveSucceeded=False)
    passed = resolve_roll_against_target(passed_roll, target, caster)
    failed = resolve_roll_against_target(failed_roll, target, caster)

    assert passed_roll.damageSaveOutcome == SpellSaveOutcome.PARTIAL
    assert passed.targetHp.current == 26
    assert ConditionType.FRIGHTENED not in passed.targetConditions
    assert failed.targetHp.current == 26
    assert ConditionType.FRIGHTENED in failed.targetConditions


def test_direct_cure_wounds_and_color_spray_execute_through_effect_context(monkeypatch) -> None:
    monkeypatch.setattr("dnd_board.character_sheet.random.randint", lambda minimum, maximum: 4)
    cure_wounds = spell_entry(SpellId.CURE_WOUNDS)
    color_spray = wizard_spell_entry(SpellId.COLOR_SPRAY)
    assert cure_wounds is not None
    assert color_spray is not None
    caster = spell_sheet(3, [cure_wounds, color_spray])

    healing_roll = build_spell_healing_roll_payload(caster, "player-1", cure_wounds, spell_slot_level=2)
    wounded_target = basic_sheet()
    wounded_target.hp = HitPoints(current=1, max=20, temporary=0)
    healing_resolution = resolve_roll_against_target(healing_roll, wounded_target)

    assert healing_roll.die == "4d8"
    assert healing_roll.total == 19
    assert healing_resolution.targetHp.current == 20
    assert healing_resolution.outcome == "heals 19 hit points"

    condition_roll = build_spell_condition_roll_payload(caster, "player-1", color_spray)
    failed_resolution = resolve_roll_against_target(replace(condition_roll, damageSaveSucceeded=False), basic_sheet())
    passed_resolution = resolve_roll_against_target(replace(condition_roll, damageSaveSucceeded=True), basic_sheet())

    assert ConditionType.BLINDED in failed_resolution.targetConditions
    assert ConditionType.BLINDED not in passed_resolution.targetConditions


def test_direct_healing_word_and_false_life_scale_and_apply(monkeypatch) -> None:
    monkeypatch.setattr("dnd_board.character_sheet.random.randint", lambda minimum, maximum: 4)
    healing_word = spell_entry(SpellId.HEALING_WORD)
    false_life = wizard_spell_entry(SpellId.FALSE_LIFE)
    assert healing_word is not None
    assert false_life is not None
    caster = spell_sheet(3, [healing_word, false_life])

    healing_roll = build_spell_healing_roll_payload(caster, "player-1", healing_word, spell_slot_level=2)
    temporary_roll = build_spell_temporary_hit_points_roll_payload(caster, "player-1", false_life, spell_slot_level=2)
    wounded_target = basic_sheet()
    wounded_target.hp = HitPoints(current=1, max=30, temporary=0)

    healing_resolution = resolve_roll_against_target(healing_roll, wounded_target)
    temporary_resolution = resolve_roll_against_target(temporary_roll, wounded_target)
    source_resolution = resolve_roll_against_target(temporary_roll, caster)

    assert healing_roll.die == "4d4"
    assert healing_roll.total == 19
    assert healing_resolution.targetHp.current == 20
    assert temporary_roll.die == "2d4"
    assert temporary_roll.total == 17
    assert temporary_resolution.targetHp.temporary == 0
    assert temporary_resolution.outcome == "has no effect; effect targets its source"
    assert source_resolution.targetHp.temporary == 17


def test_direct_protection_from_poison_removes_poison_and_adds_resistance() -> None:
    protection = spell_entry(SpellId.PROTECTION_FROM_POISON)
    assert protection is not None
    caster = spell_sheet(3, [protection])
    target = basic_sheet()
    target.conditions = [ConditionType.POISONED]

    roll = build_spell_condition_roll_payload(caster, "player-1", protection)
    resolution = resolve_roll_against_target(roll, target)

    assert ConditionType.POISONED not in resolution.targetConditions
    assert ConditionType.PROTECTION_FROM_POISON in resolution.targetConditions
    assert resolution.sheetUpdates is not None
    assert resolution.sheetUpdates[0].damageResistances == [DamageType.POISON]
    assert "gains resistance to Poison damage" in resolution.outcome


def test_direct_protection_from_energy_uses_selected_typed_damage_choice() -> None:
    protection = spell_entry(SpellId.PROTECTION_FROM_ENERGY)
    assert protection is not None
    caster = spell_sheet(5, [protection])
    target = basic_sheet()

    roll = build_spell_condition_roll_payload(caster, "player-1", protection, choice_index=2)
    resolution = resolve_roll_against_target(roll, target)

    assert ConditionType.RESISTANT_FIRE in resolution.targetConditions
    assert resolution.sheetUpdates is not None
    assert resolution.sheetUpdates[0].damageResistances == [DamageType.FIRE]
    with pytest.raises(ValueError, match="Spell effect choice not found"):
        build_spell_condition_roll_payload(caster, "player-1", protection, choice_index=5)


def test_direct_aid_increases_maximum_and_current_hit_points_with_slot_scaling() -> None:
    aid = spell_entry(SpellId.AID)
    assert aid is not None
    caster = spell_sheet(5, [aid])
    target = basic_sheet()
    target.hp = HitPoints(current=7, max=20, temporary=2)

    roll = build_spell_healing_roll_payload(caster, "player-1", aid, spell_slot_level=3)
    resolution = resolve_roll_against_target(roll, target)

    assert roll.die == "0d4"
    assert roll.total == 10
    assert resolution.targetHp == HitPoints(current=17, max=30, temporary=2)
    assert resolution.sheetUpdates is not None
    assert [applied.amount for applied in resolution.sheetUpdates[0].appliedEffects or []] == [10, 10]
    assert resolution.outcome == "increases Hit Point maximum by 10; heals 10 hit points"


def test_direct_thunderwave_applies_movement_only_after_failed_save(monkeypatch) -> None:
    monkeypatch.setattr("dnd_board.character_sheet.random.randint", lambda minimum, maximum: 4)
    thunderwave = spell_entry(SpellId.THUNDERWAVE)
    assert thunderwave is not None
    caster = spell_sheet(3, [thunderwave])
    target = basic_sheet()
    target.hp = HitPoints(current=30, max=30, temporary=0)
    roll = build_spell_damage_roll_payload(caster, "player-1", thunderwave, spell_slot_level=2)

    failed = resolve_roll_against_target(replace(roll, damageSaveSucceeded=False), target)
    succeeded = resolve_roll_against_target(replace(roll, damageSaveSucceeded=True), target)

    assert roll.die == "3d8"
    assert roll.total == 12
    assert failed.targetHp.current == 18
    assert "is pushed 10 feet" in failed.outcome
    assert succeeded.targetHp.current == 24
    assert "is pushed" not in succeeded.outcome


def test_direct_vampiric_touch_heals_source_from_damage_after_resistance(monkeypatch) -> None:
    monkeypatch.setattr("dnd_board.character_sheet.random.randint", lambda minimum, maximum: 15 if maximum == 20 else 3)
    vampiric_touch = spell_entry(SpellId.VAMPIRIC_TOUCH)
    assert vampiric_touch is not None
    caster = spell_sheet(5, [vampiric_touch])
    caster.hp = HitPoints(current=10, max=30, temporary=0)
    target = basic_sheet()
    target.hp = HitPoints(current=30, max=30, temporary=0)
    target.damageResistances = [DamageType.NECROTIC]

    roll = build_spell_damage_roll_payload(caster, "player-1", vampiric_touch, spell_slot_level=4)
    resolution = resolve_roll_against_target(roll, target, caster)

    assert roll.die == "d20"
    assert roll.damageComponents is not None
    assert roll.damageComponents[0].die == "4d6"
    assert roll.damageComponents[0].total == 12
    assert resolution.targetHp.current == 24
    assert resolution.sheetUpdates is not None
    source_update = next(update for update in resolution.sheetUpdates if update.sheetId == caster.id)
    assert source_update.hp == HitPoints(current=13, max=30, temporary=0)
    assert "heals 3 hit points" in resolution.outcome


def test_direct_vampiric_touch_skips_damage_on_miss_and_doubles_damage_dice_on_critical(monkeypatch) -> None:
    vampiric_touch = spell_entry(SpellId.VAMPIRIC_TOUCH)
    assert vampiric_touch is not None
    caster = spell_sheet(5, [vampiric_touch])
    caster.hp = HitPoints(current=10, max=30, temporary=0)
    target = basic_sheet()
    target.hp = HitPoints(current=30, max=30, temporary=0)

    monkeypatch.setattr("dnd_board.character_sheet.random.randint", lambda minimum, maximum: 1 if maximum == 20 else 2)
    miss_roll = build_spell_damage_roll_payload(caster, "player-1", vampiric_touch, spell_slot_level=3)
    miss = resolve_roll_against_target(miss_roll, target, caster)

    assert miss.outcome == "misses"
    assert miss.targetHp == target.hp
    assert miss.sheetUpdates is not None
    assert len(miss.sheetUpdates) == 1

    monkeypatch.setattr("dnd_board.character_sheet.random.randint", lambda minimum, maximum: 20 if maximum == 20 else 2)
    critical_roll = build_spell_damage_roll_payload(caster, "player-1", vampiric_touch, spell_slot_level=3)
    critical = resolve_roll_against_target(critical_roll, target, caster)

    assert critical.roll.criticalHit is True
    assert critical.roll.damageComponents is not None
    assert critical.roll.damageComponents[0].die == "6d6"
    assert critical.roll.damageComponents[0].total == 12
    assert critical.targetHp.current == 18
    source_update = next(update for update in critical.sheetUpdates or [] if update.sheetId == caster.id)
    assert source_update.hp == HitPoints(current=16, max=30, temporary=0)
    assert critical.outcome.startswith("critically hits; deals 12 damage")


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
        assert damage_roll.label == "Fire Bolt"
        assert damage_roll.die == "d20"
        assert damage_roll.damageComponents is not None
        assert damage_roll.damageComponents[0].die == expected_die
        assert damage_roll.damageComponents[0].total == expected_total
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

    with pytest.raises(ValueError, match="Spell damage effect not found"):
        build_spell_damage_roll_payload(spell_sheet(1, [fire_bolt]), "player-1", fire_bolt, effect_index=1)

    unscaled_spell = replace(
        fire_bolt,
        mechanics=FeatureMechanics(activatedEffects=[spell_damage_effect(2, DiceType.D6, DamageType.FORCE)]),
    )
    unscaled_roll = build_spell_damage_roll_payload(spell_sheet(20, [unscaled_spell]), "player-1", unscaled_spell)

    assert unscaled_roll.die == "2d6"
    assert unscaled_roll.total == 6

    boosted_spell = replace(
        fire_bolt,
        mechanics=FeatureMechanics(
            activatedEffects=[
                spell_damage_effect(
                    1,
                    DiceType.D6,
                    DamageType.FORCE,
                    static_bonus=2,
                    bonus_ability=AbilityType.INTELLIGENCE,
                    scaling=[spell_scaling(SpellScalingType.SPELL_SLOT_LEVEL, dice_count=1, dice_type=DiceType.D6)],
                )
            ]
        ),
    )
    boosted_roll = build_spell_damage_roll_payload(spell_sheet(20, [boosted_spell]), "player-1", boosted_spell)

    assert boosted_roll.die == "1d6"
    assert boosted_roll.modifier == 5
    assert boosted_roll.total == 8
    assert [(part.source, part.value) for part in boosted_roll.modifierBreakdown] == [("Spell", 2), ("Intelligence", 3)]


def test_chromatic_orb_uses_selected_typed_damage_choice(monkeypatch) -> None:
    monkeypatch.setattr("dnd_board.character_sheet.random.randint", lambda minimum, maximum: 4 if maximum == 8 else 12)
    chromatic_orb = wizard_spell_entry(SpellId.CHROMATIC_ORB)
    assert chromatic_orb is not None
    sheet = spell_sheet(5, [chromatic_orb])

    roll = build_spell_damage_roll_payload(sheet, "player-1", chromatic_orb, spell_slot_level=2, choice_index=2)

    assert roll.label == "Chromatic Orb"
    assert roll.damageType == DamageType.FIRE
    assert roll.damageComponents is not None
    assert roll.damageComponents[0].die == "4d8"
    assert roll.damageComponents[0].total == 16
    with pytest.raises(ValueError, match="Spell effect choice not found"):
        build_spell_damage_roll_payload(sheet, "player-1", chromatic_orb, choice_index=6)


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


def test_spell_damage_roll_carries_its_save_and_effect_tree() -> None:
    burning_hands = wizard_spell_entry(SpellId.BURNING_HANDS)
    assert burning_hands is not None
    sheet = spell_sheet(1, [burning_hands])

    damage = build_spell_damage_roll_payload(sheet, "player-1", burning_hands)

    assert damage.resolution == RollResolutionMode.APPLY_DAMAGE
    assert damage.damageSavingThrow == AbilityType.DEXTERITY
    assert damage.damageSaveDc == 13
    assert damage.damageSaveSucceeded is None
    assert damage.pendingEffect is not None


def test_additional_spell_damage_rolls_use_saves_conditions_and_scaling(monkeypatch) -> None:
    monkeypatch.setattr("dnd_board.character_sheet.random.randint", lambda minimum, maximum: 3)
    acid_splash = wizard_spell_entry(SpellId.ACID_SPLASH)
    call_lightning = spell_entry(SpellId.CALL_LIGHTNING)
    cone_of_cold = wizard_spell_entry(SpellId.CONE_OF_COLD)
    conjure_barrage = spell_entry(SpellId.CONJURE_BARRAGE)
    guiding_bolt = cleric_spell_entry(SpellId.GUIDING_BOLT)
    eldritch_blast = spell_entry(SpellId.ELDRITCH_BLAST)
    inflict_wounds = cleric_spell_entry(SpellId.INFLICT_WOUNDS)
    ice_storm = spell_entry(SpellId.ICE_STORM)
    lightning_bolt = wizard_spell_entry(SpellId.LIGHTNING_BOLT)
    flame_strike = spell_entry(SpellId.FLAME_STRIKE)
    divine_smite = spell_entry(SpellId.DIVINE_SMITE)
    magic_missile = wizard_spell_entry(SpellId.MAGIC_MISSILE)
    mass_cure_wounds = spell_entry(SpellId.MASS_CURE_WOUNDS)
    mass_healing_word = spell_entry(SpellId.MASS_HEALING_WORD)
    prayer_of_healing = spell_entry(SpellId.PRAYER_OF_HEALING)
    ray_of_sickness = wizard_spell_entry(SpellId.RAY_OF_SICKNESS)
    searing_orb = spell_entry(SpellId.SEARING_ORB)
    shatter = wizard_spell_entry(SpellId.SHATTER)
    thunderwave = wizard_spell_entry(SpellId.THUNDERWAVE)
    vampiric_touch = wizard_spell_entry(SpellId.VAMPIRIC_TOUCH)
    wind_wall = spell_entry(SpellId.WIND_WALL)
    steel_wind_strike = spell_entry(SpellId.STEEL_WIND_STRIKE)
    destructive_wave = spell_entry(SpellId.DESTRUCTIVE_WAVE)
    assert acid_splash is not None
    assert call_lightning is not None
    assert cone_of_cold is not None
    assert conjure_barrage is not None
    assert guiding_bolt is not None
    assert eldritch_blast is not None
    assert inflict_wounds is not None
    assert ice_storm is not None
    assert lightning_bolt is not None
    assert flame_strike is not None
    assert divine_smite is not None
    assert magic_missile is not None
    assert mass_cure_wounds is not None
    assert mass_healing_word is not None
    assert prayer_of_healing is not None
    assert ray_of_sickness is not None
    assert searing_orb is not None
    assert shatter is not None
    assert thunderwave is not None
    assert vampiric_touch is not None
    assert wind_wall is not None
    assert steel_wind_strike is not None
    assert destructive_wave is not None
    ice_knife = wizard_spell_entry(SpellId.ICE_KNIFE)
    assert ice_knife is not None

    acid_roll = build_spell_damage_roll_payload(spell_sheet(11, [acid_splash]), "player-1", acid_splash)
    call_lightning_roll = build_spell_damage_roll_payload(spell_sheet(5, [call_lightning]), "player-1", call_lightning, spell_slot_level=4)
    cone_of_cold_roll = build_spell_damage_roll_payload(spell_sheet(9, [cone_of_cold]), "player-1", cone_of_cold, spell_slot_level=6)
    conjure_barrage_roll = build_spell_damage_roll_payload(spell_sheet(5, [conjure_barrage]), "player-1", conjure_barrage, spell_slot_level=4)
    guiding_roll = build_spell_damage_roll_payload(spell_sheet(5, [guiding_bolt]), "player-1", guiding_bolt, spell_slot_level=3)
    eldritch_roll = build_spell_damage_roll_payload(spell_sheet(11, [eldritch_blast]), "player-1", eldritch_blast, instance_index=2)
    inflict_roll = build_spell_damage_roll_payload(spell_sheet(5, [inflict_wounds]), "player-1", inflict_wounds, spell_slot_level=2)
    ice_storm_roll = build_spell_damage_roll_payload(spell_sheet(7, [ice_storm]), "player-1", ice_storm, spell_slot_level=5)
    lightning_roll = build_spell_damage_roll_payload(spell_sheet(5, [lightning_bolt]), "player-1", lightning_bolt, spell_slot_level=4)
    flame_strike_roll = build_spell_damage_roll_payload(spell_sheet(9, [flame_strike]), "player-1", flame_strike, spell_slot_level=6)
    divine_smite_roll = build_spell_damage_roll_payload(spell_sheet(5, [divine_smite]), "player-1", divine_smite, effect_index=0, spell_slot_level=3)
    divine_smite_bonus_roll = build_spell_damage_roll_payload(spell_sheet(5, [divine_smite]), "player-1", divine_smite, effect_index=1)
    ice_target_roll = build_spell_damage_roll_payload(spell_sheet(5, [ice_knife]), "player-1", ice_knife, effect_index=0, spell_slot_level=2)
    missile_roll = build_spell_damage_roll_payload(spell_sheet(5, [magic_missile]), "player-1", magic_missile, spell_slot_level=3, instance_index=4)
    mass_cure_roll = build_spell_healing_roll_payload(spell_sheet(9, [mass_cure_wounds]), "player-1", mass_cure_wounds, spell_slot_level=6)
    mass_healing_roll = build_spell_healing_roll_payload(spell_sheet(5, [mass_healing_word]), "player-1", mass_healing_word, spell_slot_level=4)
    prayer_roll = build_spell_healing_roll_payload(spell_sheet(5, [prayer_of_healing]), "player-1", prayer_of_healing, spell_slot_level=4)
    ray_roll = build_spell_damage_roll_payload(spell_sheet(5, [ray_of_sickness]), "player-1", ray_of_sickness, spell_slot_level=3)
    searing_orb_roll = build_spell_damage_roll_payload(spell_sheet(5, [searing_orb]), "player-1", searing_orb, spell_slot_level=4)
    shatter_roll = build_spell_damage_roll_payload(spell_sheet(5, [shatter]), "player-1", shatter)
    thunderwave_roll = build_spell_damage_roll_payload(spell_sheet(5, [thunderwave]), "player-1", thunderwave, spell_slot_level=2)
    vampiric_roll = build_spell_damage_roll_payload(spell_sheet(5, [vampiric_touch]), "player-1", vampiric_touch, spell_slot_level=4)
    wind_wall_roll = build_spell_damage_roll_payload(spell_sheet(5, [wind_wall]), "player-1", wind_wall)
    steel_wind_roll = build_spell_damage_roll_payload(spell_sheet(9, [steel_wind_strike]), "player-1", steel_wind_strike, instance_index=4)
    destructive_wave_roll = build_spell_damage_roll_payload(spell_sheet(9, [destructive_wave]), "player-1", destructive_wave, effect_index=1)

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

    assert guiding_roll.die == "d20"
    assert guiding_roll.damageComponents is not None
    assert guiding_roll.damageComponents[0].die == "6d6"
    assert guiding_roll.damageComponents[0].total == 18
    assert guiding_roll.damageType == DamageType.RADIANT

    assert eldritch_roll.source.actionId == "damage-0-instance-2"
    assert eldritch_roll.label == "Eldritch Blast"
    assert eldritch_roll.die == "d20"
    assert eldritch_roll.damageComponents is not None
    assert eldritch_roll.damageComponents[0].die == "1d10"
    assert eldritch_roll.damageComponents[0].total == 3
    assert eldritch_roll.damageType == DamageType.FORCE
    build_spell_damage_roll_payload(spell_sheet(1, [eldritch_blast]), "player-1", eldritch_blast, instance_index=0)
    build_spell_damage_roll_payload(spell_sheet(5, [eldritch_blast]), "player-1", eldritch_blast, instance_index=1)
    build_spell_damage_roll_payload(spell_sheet(17, [eldritch_blast]), "player-1", eldritch_blast, instance_index=3)
    with pytest.raises(ValueError, match="Spell damage instance not found"):
        build_spell_damage_roll_payload(spell_sheet(11, [eldritch_blast]), "player-1", eldritch_blast, instance_index=3)

    assert inflict_roll.die == "3d10"
    assert inflict_roll.total == 9
    assert inflict_roll.damageType == DamageType.NECROTIC
    assert inflict_roll.damageSavingThrow == AbilityType.CONSTITUTION
    assert inflict_roll.damageSaveOutcome == SpellSaveOutcome.HALF_DAMAGE

    assert ice_storm_roll.label == "Storm Damage"
    assert ice_storm_roll.die == "3d10+4d6"
    assert ice_storm_roll.total == 21
    assert ice_storm_roll.damageType == DamageType.BLUDGEONING
    assert ice_storm_roll.damageSavingThrow == AbilityType.DEXTERITY
    assert ice_storm_roll.damageSaveOutcome == SpellSaveOutcome.HALF_DAMAGE
    assert ice_storm_roll.damageComponents is not None
    assert [component.damageType for component in ice_storm_roll.damageComponents] == [DamageType.BLUDGEONING, DamageType.COLD]
    assert [component.die for component in ice_storm_roll.damageComponents] == ["3d10", "4d6"]
    assert [component.total for component in ice_storm_roll.damageComponents] == [9, 12]

    assert lightning_roll.die == "9d6"
    assert lightning_roll.total == 27
    assert lightning_roll.damageType == DamageType.LIGHTNING
    assert lightning_roll.damageSavingThrow == AbilityType.DEXTERITY
    assert lightning_roll.damageSaveOutcome == SpellSaveOutcome.HALF_DAMAGE

    assert flame_strike_roll.die == "6d6+6d6"
    assert flame_strike_roll.total == 36
    assert flame_strike_roll.damageComponents is not None
    assert [component.damageType for component in flame_strike_roll.damageComponents] == [DamageType.FIRE, DamageType.RADIANT]
    assert [component.total for component in flame_strike_roll.damageComponents] == [18, 18]

    assert divine_smite_roll.label == "Smite Damage"
    assert divine_smite_roll.die == "4d8"
    assert divine_smite_roll.total == 12
    assert divine_smite_roll.damageType == DamageType.RADIANT
    assert divine_smite_bonus_roll.label == "Fiend/Undead Bonus Damage"
    assert divine_smite_bonus_roll.die == "1d8"
    assert divine_smite_bonus_roll.total == 3
    assert divine_smite_bonus_roll.damageType == DamageType.RADIANT
    assert divine_smite_bonus_roll.targetCreatureTypes == [CreatureType.FIEND, CreatureType.UNDEAD]

    assert ice_target_roll.label == "Ice Knife"
    assert ice_target_roll.die == "d20"
    assert ice_target_roll.damageType == DamageType.PIERCING
    assert ice_target_roll.damageComponents is not None
    assert [component.die for component in ice_target_roll.damageComponents] == ["1d10", "3d6"]
    assert [component.damageType for component in ice_target_roll.damageComponents] == [DamageType.PIERCING, DamageType.COLD]
    assert ice_target_roll.damageSavingThrow == AbilityType.DEXTERITY
    assert ice_target_roll.damageSaveOutcome == SpellSaveOutcome.PARTIAL

    assert missile_roll.source.actionId == "damage-0-slot-3-instance-4"
    assert missile_roll.label == "Dart 5 Damage"
    assert missile_roll.die == "1d4"
    assert missile_roll.modifier == 1
    assert missile_roll.total == 4
    assert missile_roll.damageType == DamageType.FORCE
    assert [(part.source, part.value) for part in missile_roll.modifierBreakdown] == [("Spell", 1)]
    assert magic_missile.mechanics is not None

    assert mass_cure_roll.die == "6d8"
    assert mass_cure_roll.total == 21
    assert mass_cure_roll.modifier == 3

    assert mass_healing_roll.die == "3d4"
    assert mass_healing_roll.total == 12
    assert mass_healing_roll.resolution == RollResolutionMode.HEAL_SELF

    assert prayer_roll.die == "4d8"
    assert prayer_roll.total == 15
    assert prayer_roll.resolution == RollResolutionMode.HEAL_SELF
    assert prayer_roll.pendingEffect is not None

    assert shatter_roll.damageSavingThrow == AbilityType.CONSTITUTION
    assert shatter_roll.damageSaveDisadvantageCreatureTypes == [CreatureType.CONSTRUCT]
    with pytest.raises(ValueError, match="Spell damage instance not found"):
        build_spell_damage_roll_payload(spell_sheet(5, [magic_missile]), "player-1", magic_missile, spell_slot_level=3, instance_index=5)

    assert ray_roll.die == "d20"
    assert ray_roll.damageComponents is not None
    assert ray_roll.damageComponents[0].die == "4d8"
    assert ray_roll.damageComponents[0].total == 12
    assert ray_roll.damageType == DamageType.POISON
    assert ray_roll.pendingEffect is not None

    assert searing_orb_roll.die == "d20"
    assert searing_orb_roll.damageComponents is not None
    assert searing_orb_roll.damageComponents[0].die == "5d4"
    assert searing_orb_roll.damageComponents[0].total == 15
    assert searing_orb_roll.damageType == DamageType.RADIANT
    assert searing_orb_roll.damageSavingThrow == AbilityType.CONSTITUTION
    assert searing_orb_roll.pendingEffect is not None

    assert thunderwave_roll.die == "3d8"
    assert thunderwave_roll.total == 9
    assert thunderwave_roll.damageType == DamageType.THUNDER
    assert thunderwave_roll.damageSavingThrow == AbilityType.CONSTITUTION
    assert thunderwave_roll.damageSaveOutcome == SpellSaveOutcome.HALF_DAMAGE
    assert vampiric_roll.label == "Vampiric Touch"
    assert vampiric_roll.die == "d20"
    assert vampiric_roll.damageComponents is not None
    assert vampiric_roll.damageComponents[0].die == "4d6"
    assert vampiric_roll.damageComponents[0].total == 12
    assert vampiric_roll.damageType == DamageType.NECROTIC
    assert wind_wall_roll.die == "4d8"
    assert wind_wall_roll.total == 12
    assert wind_wall_roll.damageType == DamageType.BLUDGEONING
    assert wind_wall_roll.damageSavingThrow == AbilityType.STRENGTH
    assert wind_wall_roll.damageSaveOutcome == SpellSaveOutcome.HALF_DAMAGE

    assert steel_wind_roll.source.actionId == "damage-0-instance-4"
    assert steel_wind_roll.label == "Steel Wind Strike"
    assert steel_wind_roll.die == "d20"
    assert steel_wind_roll.damageComponents is not None
    assert steel_wind_roll.damageComponents[0].die == "6d10"
    assert steel_wind_roll.damageComponents[0].total == 18
    assert steel_wind_roll.damageType == DamageType.FORCE

    assert destructive_wave_roll.label == "Necrotic Wave Damage"
    assert destructive_wave_roll.die == "5d6+5d6"
    assert destructive_wave_roll.damageComponents is not None
    assert [component.damageType for component in destructive_wave_roll.damageComponents] == [DamageType.THUNDER, DamageType.NECROTIC]
    assert destructive_wave_roll.damageSavingThrow == AbilityType.CONSTITUTION
    assert added_condition_types(destructive_wave_roll.pendingEffect) == [ConditionType.PRONE]


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
    with pytest.raises(ValueError, match="Spell condition effect not found"):
        build_spell_condition_roll_payload(spell_sheet(5, [searing_orb]), "player-1", searing_orb)
    stinking_cloud_roll = build_spell_condition_roll_payload(spell_sheet(5, [stinking_cloud]), "player-1", stinking_cloud)

    assert effect_roll.source.section == SheetSectionType.SPELLS
    assert effect_roll.source.sourceId == "tashaSHideousLaughter"
    assert effect_roll.source.actionId == "condition-0"
    assert effect_roll.label == "Spell Effect"
    assert effect_roll.dice == []
    assert effect_roll.damageSavingThrow == AbilityType.WISDOM
    assert effect_roll.damageSaveDc == 14
    assert effect_roll.pendingEffect is not None
    assert added_condition_types(effect_roll.pendingEffect) == [ConditionType.PRONE, ConditionType.INCAPACITATED]
    tasha_changes = condition_change_effects(effect_roll.pendingEffect)
    assert all(change.endingConditions[0].endingCondition == EndingConditionType.TARGET_TAKES_DAMAGE for change in tasha_changes)
    assert all(change.endingConditions[0].advantage for change in tasha_changes)
    assert command_roll.label == "Grovel"
    assert added_condition_types(command_roll.pendingEffect) == [ConditionType.COMMAND_GROVEL, ConditionType.PRONE]
    assert command_roll.damageSavingThrow == AbilityType.WISDOM
    assert bless_roll.label == "Bless"
    assert added_condition_types(bless_roll.pendingEffect) == [ConditionType.BLESSED]
    assert bless_roll.damageSavingThrow is None
    assert blinding_roll.label == "Blind"
    assert added_condition_types(blinding_roll.pendingEffect) == [ConditionType.BLINDED]
    assert blinding_roll.damageSavingThrow == AbilityType.CONSTITUTION
    assert blinding_roll.damageSaveDc == 14
    assert fear_roll.label == "Fear"
    assert added_condition_types(fear_roll.pendingEffect) == [ConditionType.FRIGHTENED]
    assert fear_roll.damageSavingThrow == AbilityType.WISDOM
    assert hypnotic_roll.label == "Pattern"
    assert added_condition_types(hypnotic_roll.pendingEffect) == [ConditionType.CHARMED, ConditionType.INCAPACITATED]
    assert hypnotic_roll.damageSavingThrow == AbilityType.WISDOM
    assert stinking_cloud_roll.label == "Nauseate"
    assert added_condition_types(stinking_cloud_roll.pendingEffect) == [ConditionType.POISONED]
    assert stinking_cloud_roll.damageSavingThrow == AbilityType.CONSTITUTION
    assert stinking_cloud_roll.damageSaveDc == 14



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
