from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from dnd_board.character_sheet import (
    AbilityType,
    CharacterClassLevel,
    ClassType,
    ConditionApplicationMode,
    ConditionEffect,
    ConditionType,
    DamageType,
    DiceType,
    ResourceTracker,
    RestType,
    RollAction,
    RollResolutionMode,
    SheetAbility,
    SheetFeature,
    TimeEconomy,
    enum_key,
    enum_label,
)
from dnd_board.rules.sources import RuleSource, rule_source_label


class RogueFeatureType(Enum):
    EXPERTISE = auto()
    SNEAK_ATTACK = auto()
    THIEVES_CANT = auto()
    WEAPON_MASTERY = auto()
    CUNNING_ACTION = auto()
    ROGUE_SUBCLASS = auto()
    STEADY_AIM = auto()
    ABILITY_SCORE_IMPROVEMENT = auto()
    CUNNING_STRIKE = auto()
    UNCANNY_DODGE = auto()
    EVASION = auto()
    RELIABLE_TALENT = auto()
    SUBCLASS_FEATURE = auto()
    IMPROVED_CUNNING_STRIKE = auto()
    DEVIOUS_STRIKES = auto()
    SLIPPERY_MIND = auto()
    ELUSIVE = auto()
    EPIC_BOON = auto()
    STROKE_OF_LUCK = auto()


class RogueResourceType(Enum):
    STROKE_OF_LUCK = auto()


class RogueAbilityType(Enum):
    SNEAK_ATTACK = auto()
    CUNNING_STRIKE_POISON = auto()
    CUNNING_STRIKE_TRIP = auto()
    CUNNING_STRIKE_WITHDRAW = auto()
    CUNNING_STRIKE_DAZE = auto()
    CUNNING_STRIKE_KNOCK_OUT = auto()
    CUNNING_STRIKE_OBSCURE = auto()


class RogueSubclassType(Enum):
    ARCANE_TRICKSTER = auto()
    ASSASSIN = auto()
    INQUISITIVE = auto()
    MASTERMIND = auto()
    PHANTOM = auto()
    SCION_OF_THE_THREE = auto()
    SCOUT = auto()
    SOULKNIFE = auto()
    SWASHBUCKLER = auto()
    THIEF = auto()
    REVIVED = auto()


ROGUE_SUBCLASS_SOURCES: dict[RogueSubclassType, RuleSource] = {
    RogueSubclassType.ARCANE_TRICKSTER: RuleSource.PLAYERS_HANDBOOK_2024,
    RogueSubclassType.ASSASSIN: RuleSource.PLAYERS_HANDBOOK_2024,
    RogueSubclassType.PHANTOM: RuleSource.RAVENLOFT_THE_HORRORS_WITHIN_2024,
    RogueSubclassType.SCION_OF_THE_THREE: RuleSource.FORGOTTEN_REALMS_HEROES_OF_FAERUN_2024,
    RogueSubclassType.SOULKNIFE: RuleSource.PLAYERS_HANDBOOK_2024,
    RogueSubclassType.THIEF: RuleSource.PLAYERS_HANDBOOK_2024,
    RogueSubclassType.INQUISITIVE: RuleSource.XANATHARS_GUIDE_TO_EVERYTHING,
    RogueSubclassType.MASTERMIND: RuleSource.XANATHARS_GUIDE_TO_EVERYTHING,
    RogueSubclassType.SCOUT: RuleSource.XANATHARS_GUIDE_TO_EVERYTHING,
    RogueSubclassType.SWASHBUCKLER: RuleSource.XANATHARS_GUIDE_TO_EVERYTHING,
    RogueSubclassType.REVIVED: RuleSource.UNEARTHED_ARCANA,
}


def rogue_subclass_source(subclass: RogueSubclassType) -> RuleSource:
    return ROGUE_SUBCLASS_SOURCES.get(subclass, RuleSource.LEGACY)


def rogue_subclass_label(subclass: RogueSubclassType) -> str:
    label = enum_label(subclass)
    source = rogue_subclass_source(subclass)
    current_sources = {
        RuleSource.PLAYERS_HANDBOOK_2024,
        RuleSource.FORGOTTEN_REALMS_HEROES_OF_FAERUN_2024,
        RuleSource.RAVENLOFT_THE_HORRORS_WITHIN_2024,
    }
    return label if source in current_sources else f"{label} (Legacy)"


@dataclass(frozen=True)
class RogueProgression:
    level: int
    proficiency_bonus: int
    features: tuple[RogueFeatureType, ...]
    sneak_attack_dice_count: int
    weapon_mastery_count: int = 2


ROGUE_LEVELS: dict[int, RogueProgression] = {
    1: RogueProgression(1, 2, (RogueFeatureType.EXPERTISE, RogueFeatureType.SNEAK_ATTACK, RogueFeatureType.THIEVES_CANT, RogueFeatureType.WEAPON_MASTERY), 1),
    2: RogueProgression(2, 2, (RogueFeatureType.CUNNING_ACTION,), 1),
    3: RogueProgression(3, 2, (RogueFeatureType.ROGUE_SUBCLASS, RogueFeatureType.STEADY_AIM), 2),
    4: RogueProgression(4, 2, (RogueFeatureType.ABILITY_SCORE_IMPROVEMENT,), 2),
    5: RogueProgression(5, 3, (RogueFeatureType.CUNNING_STRIKE, RogueFeatureType.UNCANNY_DODGE), 3),
    6: RogueProgression(6, 3, (RogueFeatureType.EXPERTISE,), 3),
    7: RogueProgression(7, 3, (RogueFeatureType.EVASION, RogueFeatureType.RELIABLE_TALENT), 4),
    8: RogueProgression(8, 3, (RogueFeatureType.ABILITY_SCORE_IMPROVEMENT,), 4),
    9: RogueProgression(9, 4, (RogueFeatureType.SUBCLASS_FEATURE,), 5),
    10: RogueProgression(10, 4, (RogueFeatureType.ABILITY_SCORE_IMPROVEMENT,), 5),
    11: RogueProgression(11, 4, (RogueFeatureType.IMPROVED_CUNNING_STRIKE,), 6),
    12: RogueProgression(12, 4, (RogueFeatureType.ABILITY_SCORE_IMPROVEMENT,), 6),
    13: RogueProgression(13, 5, (RogueFeatureType.SUBCLASS_FEATURE,), 7),
    14: RogueProgression(14, 5, (RogueFeatureType.DEVIOUS_STRIKES,), 7),
    15: RogueProgression(15, 5, (RogueFeatureType.SLIPPERY_MIND,), 8),
    16: RogueProgression(16, 5, (RogueFeatureType.ABILITY_SCORE_IMPROVEMENT,), 8),
    17: RogueProgression(17, 6, (RogueFeatureType.SUBCLASS_FEATURE,), 9),
    18: RogueProgression(18, 6, (RogueFeatureType.ELUSIVE,), 9),
    19: RogueProgression(19, 6, (RogueFeatureType.EPIC_BOON,), 10),
    20: RogueProgression(20, 6, (RogueFeatureType.STROKE_OF_LUCK,), 10),
}


def rogue_level(classes: list[CharacterClassLevel]) -> int:
    return sum(character_class.level for character_class in classes if character_class.name == ClassType.ROGUE)


def rogue_class(classes: list[CharacterClassLevel]) -> CharacterClassLevel | None:
    return next((character_class for character_class in classes if character_class.name == ClassType.ROGUE), None)


def rogue_progression(classes: list[CharacterClassLevel]) -> RogueProgression | None:
    level = rogue_level(classes)
    if level <= 0:
        return None
    return ROGUE_LEVELS[min(level, max(ROGUE_LEVELS))]


def rogue_resources(classes: list[CharacterClassLevel]) -> list[ResourceTracker]:
    progression = rogue_progression(classes)
    if progression is None or progression.level < 20:
        return []
    return [
        ResourceTracker(
            id=enum_key(RogueResourceType.STROKE_OF_LUCK),
            name=enum_label(RogueResourceType.STROKE_OF_LUCK),
            currentUses=1,
            maxUses=1,
            reset=RestType.SHORT_REST,
            activation=TimeEconomy.SPECIAL,
            description="If you fail a d20 Test, turn the roll into a 20.",
            source=enum_label(ClassType.ROGUE),
        )
    ]


def rogue_features(classes: list[CharacterClassLevel]) -> list[SheetFeature]:
    progression = rogue_progression(classes)
    character_class = rogue_class(classes)
    if progression is None or character_class is None:
        return []

    features: list[SheetFeature] = []
    for level in range(1, progression.level + 1):
        level_progression = ROGUE_LEVELS[level]
        features.extend(feature_for_type(feature_type, level_progression, character_class) for feature_type in level_progression.features)
    features.append(feature_for_type(RogueFeatureType.WEAPON_MASTERY, progression, character_class))

    from dnd_board.rules.classes.rogue.archetypes import rogue_subclass_features

    features.extend(rogue_subclass_features(character_class.subclass, progression.level))
    return dedupe_features(features)


def rogue_abilities(classes: list[CharacterClassLevel]) -> list[SheetAbility]:
    progression = rogue_progression(classes)
    if progression is None:
        return []
    abilities = [
        SheetAbility(
            id=enum_key(RogueAbilityType.SNEAK_ATTACK),
            name=enum_label(RogueAbilityType.SNEAK_ATTACK),
            source=enum_label(ClassType.ROGUE),
            activation=TimeEconomy.SPECIAL,
            description="Once per turn, deal extra damage with an eligible Finesse or Ranged weapon attack.",
            rollActions=[
                RollAction(
                    id=RogueAbilityType.SNEAK_ATTACK,
                    name=RogueAbilityType.SNEAK_ATTACK,
                    diceCount=progression.sneak_attack_dice_count,
                    diceType=DiceType.D6,
                    resolution=RollResolutionMode.APPLY_DAMAGE,
                    damageType=DamageType.PIERCING,
                    source=enum_label(ClassType.ROGUE),
                )
            ],
        )
    ]
    if progression.level >= 5:
        abilities.extend(cunning_strike_abilities(include_devious=progression.level >= 14))
    return abilities


def cunning_strike_abilities(include_devious: bool) -> list[SheetAbility]:
    definitions = [
        (RogueAbilityType.CUNNING_STRIKE_POISON, AbilityType.CONSTITUTION, ConditionType.POISONED, "Cost 1d6. With a Poisoner's Kit, target makes a Constitution save or is Poisoned for 1 minute."),
        (RogueAbilityType.CUNNING_STRIKE_TRIP, AbilityType.DEXTERITY, ConditionType.PRONE, "Cost 1d6. Large or smaller target makes a Dexterity save or falls Prone."),
        (RogueAbilityType.CUNNING_STRIKE_WITHDRAW, None, None, "Cost 1d6. Immediately after the attack, move up to half Speed without provoking Opportunity Attacks."),
    ]
    if include_devious:
        definitions.extend(
            [
                (RogueAbilityType.CUNNING_STRIKE_DAZE, AbilityType.CONSTITUTION, None, "Cost 2d6. Target makes a Constitution save or on its next turn can only move, take an action, or take a Bonus Action."),
                (RogueAbilityType.CUNNING_STRIKE_KNOCK_OUT, AbilityType.CONSTITUTION, ConditionType.UNCONSCIOUS, "Cost 6d6. Target makes a Constitution save or is Unconscious for 1 minute or until damaged."),
                (RogueAbilityType.CUNNING_STRIKE_OBSCURE, AbilityType.DEXTERITY, ConditionType.BLINDED, "Cost 3d6. Target makes a Dexterity save or is Blinded until the end of its next turn."),
            ]
        )
    return [
        SheetAbility(
            id=enum_key(ability_type),
            name=enum_label(ability_type),
            source=enum_label(ClassType.ROGUE),
            activation=TimeEconomy.SPECIAL,
            description=description,
            conditionEffects=[
                ConditionEffect(
                    condition=condition,
                    mode=ConditionApplicationMode.TARGET_SAVE,
                    savingThrow=saving_throw,
                    saveDcAbility=AbilityType.DEXTERITY,
                    description=description,
                )
            ]
            if saving_throw is not None
            else None,
        )
        for ability_type, saving_throw, condition, description in definitions
    ]


def feature_for_type(feature_type: RogueFeatureType, progression: RogueProgression, character_class: CharacterClassLevel) -> SheetFeature:
    descriptions = {
        RogueFeatureType.EXPERTISE: "Gain Expertise in two skill proficiencies; gain two more at Rogue level 6.",
        RogueFeatureType.SNEAK_ATTACK: f"Tracked as a rollable ability. Extra damage is {progression.sneak_attack_dice_count}d6.",
        RogueFeatureType.THIEVES_CANT: "Know Thieves' Cant and one other language of your choice.",
        RogueFeatureType.WEAPON_MASTERY: f"Use mastery properties for {progression.weapon_mastery_count} proficient weapon choices.",
        RogueFeatureType.CUNNING_ACTION: "Take Dash, Disengage, or Hide as a Bonus Action.",
        RogueFeatureType.ROGUE_SUBCLASS: subclass_description(character_class),
        RogueFeatureType.STEADY_AIM: "As a Bonus Action, gain Advantage on your next attack roll this turn if you have not moved; your Speed becomes 0 until the end of the turn.",
        RogueFeatureType.ABILITY_SCORE_IMPROVEMENT: "Gain Ability Score Improvement or another feat for which you qualify.",
        RogueFeatureType.CUNNING_STRIKE: "When you deal Sneak Attack damage, forgo Sneak Attack dice to add Poison, Trip, or Withdraw.",
        RogueFeatureType.UNCANNY_DODGE: "When an attacker you can see hits you with an attack roll, use your Reaction to halve the damage.",
        RogueFeatureType.EVASION: "On Dexterity saves for half damage, take no damage on success and half damage on failure while not Incapacitated.",
        RogueFeatureType.RELIABLE_TALENT: "Treat a d20 roll of 9 or lower as 10 for ability checks using skill or tool proficiencies.",
        RogueFeatureType.SUBCLASS_FEATURE: subclass_description(character_class),
        RogueFeatureType.IMPROVED_CUNNING_STRIKE: "Use up to two Cunning Strike effects when you deal Sneak Attack damage, paying each die cost.",
        RogueFeatureType.DEVIOUS_STRIKES: "Add Daze, Knock Out, and Obscure to your Cunning Strike options.",
        RogueFeatureType.SLIPPERY_MIND: "Gain proficiency in Wisdom and Charisma saving throws.",
        RogueFeatureType.ELUSIVE: "No attack roll can have Advantage against you unless you have the Incapacitated condition.",
        RogueFeatureType.EPIC_BOON: "Gain an Epic Boon feat or another feat for which you qualify.",
        RogueFeatureType.STROKE_OF_LUCK: "Tracked as a resource.",
    }
    return SheetFeature(
        id=enum_key(feature_type),
        name=enum_label(feature_type),
        source=enum_label(ClassType.ROGUE),
        activation=feature_activation(feature_type),
        description=descriptions[feature_type],
    )


def feature_activation(feature_type: RogueFeatureType) -> TimeEconomy:
    if feature_type in {RogueFeatureType.CUNNING_ACTION, RogueFeatureType.STEADY_AIM}:
        return TimeEconomy.BONUS_ACTION
    if feature_type == RogueFeatureType.UNCANNY_DODGE:
        return TimeEconomy.REACTION
    return TimeEconomy.SPECIAL if feature_type == RogueFeatureType.STROKE_OF_LUCK else TimeEconomy.PASSIVE


def subclass_description(character_class: CharacterClassLevel) -> str:
    if character_class.subclass is None:
        return "Choose a Rogue subclass."
    if isinstance(character_class.subclass, RogueSubclassType):
        source = rule_source_label(rogue_subclass_source(character_class.subclass))
        return f"{rogue_subclass_label(character_class.subclass)} subclass features ({source}) are included up to your Rogue level."
    return f"{enum_label(character_class.subclass)} subclass features are included up to your Rogue level."


def dedupe_features(features: list[SheetFeature]) -> list[SheetFeature]:
    deduped: dict[str, SheetFeature] = {}
    for feature in features:
        deduped[feature.id] = feature
    return list(deduped.values())
