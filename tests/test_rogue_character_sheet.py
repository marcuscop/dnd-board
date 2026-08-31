from dnd_board.character_sheet import (
    AbilityScores,
    AbilityType,
    AttackAction,
    CharacterClassLevel,
    ClassType,
    DamageType,
    DiceType,
    PartyMember,
    PartyMemberSheet,
    SpellId,
    SpellSource,
    TokenKind,
    build_character_sheet,
    enum_key,
    sheet_to_dict,
    typed_json_from_value,
    typed_json_to_value,
)
from dnd_board.rules.classes.rogue.archetypes import (
    RogueSubclassAbilityType,
    RogueSubclassAttackType,
    arcane_trickster_catalog_spell,
    arcane_trickster_spell_options,
    is_arcane_trickster_spell_selection_valid,
    pruned_arcane_trickster_spells,
    rogue_subclass_attacks,
)
from dnd_board.rules.classes.rogue.base import RogueSubclassType, subclass_description


def test_rogue_2024_progression_features_and_abilities() -> None:
    sheet = rogue_sheet(14)
    features = {feature.id for feature in sheet.features}
    abilities = {ability.id: ability for ability in sheet.abilities}

    assert {"sneakAttack", "cunningAction", "cunningStrike", "reliableTalent", "improvedCunningStrike", "deviousStrikes"} <= features
    assert abilities["sneakAttack"].rollActions[0].diceCount == 7
    assert abilities["sneakAttack"].rollActions[0].diceType == DiceType.D6
    assert {"cunningStrikePoison", "cunningStrikeTrip", "cunningStrikeDaze", "cunningStrikeKnockOut", "cunningStrikeObscure"} <= set(abilities)


def test_rogue_saving_throw_proficiencies_include_slippery_mind() -> None:
    level_1 = rogue_sheet(1)
    level_15 = rogue_sheet(15)

    assert [save.ability for save in level_1.savingThrows if save.proficient] == [AbilityType.DEXTERITY, AbilityType.INTELLIGENCE]
    assert {save.ability for save in level_15.savingThrows if save.proficient} == {
        AbilityType.DEXTERITY,
        AbilityType.INTELLIGENCE,
        AbilityType.WISDOM,
        AbilityType.CHARISMA,
    }


def test_rogue_progression_exposes_current_and_legacy_subclasses() -> None:
    sheet = rogue_sheet(3)
    subclass_choices = {choice.id: choice for choice in sheet.pendingChoices}
    subclass_labels = {option.value: option.label for option in subclass_choices["rogueSubclass"].options}

    assert subclass_labels["arcaneTrickster"] == "Arcane Trickster"
    assert subclass_labels["phantom"] == "Phantom"
    assert subclass_labels["scionOfTheThree"] == "Scion Of The Three"
    assert subclass_labels["inquisitive"] == "Inquisitive (Legacy)"
    assert subclass_labels["revived"] == "Revived (Legacy)"


def test_rogue_subclass_description_handles_nonstandard_subclass_value() -> None:
    assert subclass_description(CharacterClassLevel(name=ClassType.ROGUE, level=3, subclass=ClassType.FIGHTER)) == (
        "Fighter subclass features are included up to your Rogue level."
    )


def test_soulknife_resources_and_psychic_blade_attacks_scale() -> None:
    sheet = rogue_sheet(17, subclass=RogueSubclassType.SOULKNIFE)
    resources = {resource.id: resource for resource in sheet.resources}
    attacks = {attack.id: attack for attack in sheet.attacks}
    abilities = {ability.id: ability for ability in sheet.abilities}

    assert resources["psionicEnergyDice"].maxUses == 12
    assert resources["psionicEnergyDice"].rollActions[0].diceType == DiceType.D12
    assert resources["rendMind"].maxUses == 1
    assert attacks[enum_key(RogueSubclassAttackType.PSYCHIC_BLADE)].damageType == DamageType.PSYCHIC
    assert attacks[enum_key(RogueSubclassAttackType.PSYCHIC_BLADE_BONUS)].damageDiceType == DiceType.D4
    assert abilities[enum_key(RogueSubclassAbilityType.HOMING_STRIKES)].resourceId == "psionicEnergyDice"


def test_soulknife_attacks_do_not_duplicate_existing_psychic_blades() -> None:
    existing_main = AttackAction(
        id=enum_key(RogueSubclassAttackType.PSYCHIC_BLADE),
        name="Psychic Blade",
        ability=AbilityType.DEXTERITY,
        damageDiceCount=1,
        damageDiceType=DiceType.D6,
        damageType=DamageType.PSYCHIC,
    )
    existing_bonus = AttackAction(
        id=enum_key(RogueSubclassAttackType.PSYCHIC_BLADE_BONUS),
        name="Psychic Blade Bonus",
        ability=AbilityType.DEXTERITY,
        damageDiceCount=1,
        damageDiceType=DiceType.D4,
        damageType=DamageType.PSYCHIC,
    )
    attacks = rogue_subclass_attacks(
        [CharacterClassLevel(name=ClassType.ROGUE, level=3, subclass=RogueSubclassType.SOULKNIFE)],
        [existing_main, existing_bonus],
    )

    assert attacks == [existing_main, existing_bonus]


def test_arcane_trickster_tracks_spell_slots_and_required_mage_hand() -> None:
    sheet = rogue_sheet(3, subclass=RogueSubclassType.ARCANE_TRICKSTER)
    resources = {resource.id: resource for resource in sheet.resources}
    choices = {choice.id: choice for choice in sheet.pendingChoices}
    spell_choice = choices["arcaneTricksterSpells"]
    option_values = {option.value for option in spell_choice.options}

    assert resources["arcaneTricksterFirstLevelSpellSlots"].maxUses == 2
    assert spell_choice.minimum == 6
    assert {"mageHand", "mindSliver", "shield", "charmPerson"} <= option_values
    assert "shatter" not in option_values


def test_arcane_trickster_spell_options_expand_with_level() -> None:
    level_3_options = {enum_key(spell.id) for spell in arcane_trickster_spell_options(3)}
    level_7_options = {enum_key(spell.id) for spell in arcane_trickster_spell_options(7)}

    assert "shatter" not in level_3_options
    assert "shatter" in level_7_options


def test_arcane_trickster_rejects_unknown_spell_and_prunes_to_level() -> None:
    spells = [
        arcane_trickster_catalog_spell("fireBolt"),
        arcane_trickster_catalog_spell("mageHand"),
        arcane_trickster_catalog_spell("mindSliver"),
        arcane_trickster_catalog_spell("shield"),
        arcane_trickster_catalog_spell("magicMissile"),
        arcane_trickster_catalog_spell("charmPerson"),
        arcane_trickster_catalog_spell("disguiseSelf"),
        arcane_trickster_catalog_spell("fogCloud"),
    ]

    assert arcane_trickster_catalog_spell("notASpell") is None
    assert [spell.id for spell in pruned_arcane_trickster_spells(3, [spell for spell in spells if spell is not None])] == [
        SpellId.FIRE_BOLT,
        SpellId.MAGE_HAND,
        SpellId.MIND_SLIVER,
        SpellId.SHIELD,
        SpellId.MAGIC_MISSILE,
        SpellId.CHARM_PERSON,
    ]
    assert is_arcane_trickster_spell_selection_valid(3, [spell for spell in spells if spell is not None][:6]) is True


def test_arcane_trickster_uses_configured_spells_with_intelligence() -> None:
    sheet = rogue_sheet(
        3,
        subclass=RogueSubclassType.ARCANE_TRICKSTER,
        spells=[arcane_trickster_catalog_spell("mageHand")],
    )

    assert sheet.spells[0].id == SpellId.MAGE_HAND
    assert sheet.spells[0].castingAbility == AbilityType.INTELLIGENCE
    assert sheet.spells[0].source == SpellSource.ARCANE_TRICKSTER


def test_all_rogue_subclasses_build_at_every_level_and_round_trip() -> None:
    for subclass in RogueSubclassType:
        for level in range(1, 21):
            sheet = rogue_sheet(level, subclass=subclass if level >= 3 else None)
            feature_ids = [feature.id for feature in sheet.features]
            ability_ids = [ability.id for ability in sheet.abilities]
            resource_ids = [resource.id for resource in sheet.resources]
            attack_ids = [attack.id for attack in sheet.attacks]

            assert len(feature_ids) == len(set(feature_ids)), f"{subclass.name} level {level} duplicated features"
            assert len(ability_ids) == len(set(ability_ids)), f"{subclass.name} level {level} duplicated abilities"
            assert len(resource_ids) == len(set(resource_ids)), f"{subclass.name} level {level} duplicated resources"
            assert len(attack_ids) == len(set(attack_ids)), f"{subclass.name} level {level} duplicated attacks"
            assert sheet_to_dict(sheet)["classes"][0]["name"] == "rogue"
            assert typed_json_to_value(typed_json_from_value(sheet.classes[0]), CharacterClassLevel).name == ClassType.ROGUE


def rogue_sheet(level: int, subclass: RogueSubclassType | None = None, spells=None):
    return build_character_sheet(
        token_id="rogue",
        kind=TokenKind.CHARACTER,
        name="Rogue",
        owner="player-1",
        avatar_url=None,
        party_member=PartyMember(
            id="rogue",
            name="Rogue",
            owner="player-1",
            avatarUrl=None,
            maxHp=10,
            abilityScores=AbilityScores(strength=10, dexterity=16, constitution=14, intelligence=14, wisdom=12, charisma=10),
            sheet=PartyMemberSheet(
                classes=[CharacterClassLevel(name=ClassType.ROGUE, level=level, subclass=subclass)],
                spells=spells,
            ),
        ),
        current_hp=None,
        resource_overrides={},
    )
