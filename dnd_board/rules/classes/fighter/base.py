from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from dnd_board.character_sheet import (
    CharacterClassLevel,
    ClassType,
    DiceType,
    ResourceTracker,
    RestType,
    RollAction,
    RollModifierType,
    RollResolutionMode,
    SheetFeature,
    TimeEconomy,
    enum_key,
    enum_label,
)
from dnd_board.rules.sources import RuleSource, is_legacy_source, rule_source_label


class FighterFeatureType(Enum):
    FIGHTING_STYLE = auto()
    SECOND_WIND = auto()
    WEAPON_MASTERY = auto()
    ACTION_SURGE = auto()
    TACTICAL_MIND = auto()
    FIGHTER_SUBCLASS = auto()
    ABILITY_SCORE_IMPROVEMENT = auto()
    EXTRA_ATTACK = auto()
    TACTICAL_SHIFT = auto()
    SUBCLASS_FEATURE = auto()
    INDOMITABLE = auto()
    TACTICAL_MASTER = auto()
    TWO_EXTRA_ATTACKS = auto()
    STUDIED_ATTACKS = auto()
    EPIC_BOON = auto()
    THREE_EXTRA_ATTACKS = auto()


class FighterResourceType(Enum):
    SECOND_WIND = auto()
    ACTION_SURGE = auto()
    INDOMITABLE = auto()


class FighterRollActionType(Enum):
    SECOND_WIND_HEAL = auto()
    TACTICAL_MIND = auto()


class FighterSubclassType(Enum):
    CHAMPION = auto()
    BATTLE_MASTER = auto()
    BANNERET = auto()
    CAVALIER = auto()
    SAMURAI = auto()
    BRUTE = auto()
    SCOUT = auto()
    SHARPSHOOTER = auto()
    MONSTER_HUNTER = auto()
    ARCANE_ARCHER = auto()
    RUNE_KNIGHT = auto()
    ECHO_KNIGHT = auto()
    PSI_WARRIOR = auto()
    ELDRITCH_KNIGHT = auto()


FIGHTER_SUBCLASS_SOURCES: dict[FighterSubclassType, RuleSource] = {
    FighterSubclassType.BANNERET: RuleSource.FORGOTTEN_REALMS_HEROES_OF_FAERUN_2024,
    FighterSubclassType.BATTLE_MASTER: RuleSource.PLAYERS_HANDBOOK_2024,
    FighterSubclassType.CHAMPION: RuleSource.PLAYERS_HANDBOOK_2024,
    FighterSubclassType.ELDRITCH_KNIGHT: RuleSource.PLAYERS_HANDBOOK_2024,
    FighterSubclassType.PSI_WARRIOR: RuleSource.PLAYERS_HANDBOOK_2024,
}


def fighter_subclass_label(subclass: FighterSubclassType) -> str:
    label = enum_label(subclass)
    return f"{label} (Legacy)" if is_legacy_source(fighter_subclass_source(subclass)) else label


def fighter_subclass_source(subclass: FighterSubclassType) -> RuleSource:
    return FIGHTER_SUBCLASS_SOURCES.get(subclass, RuleSource.LEGACY)


@dataclass(frozen=True)
class FighterProgression:
    level: int
    proficiency_bonus: int
    features: tuple[FighterFeatureType, ...]
    second_wind_uses: int
    weapon_mastery_count: int
    action_surge_uses: int = 0
    indomitable_uses: int = 0
    attack_count: int = 1


FIGHTER_LEVELS: dict[int, FighterProgression] = {
    1: FighterProgression(
        level=1,
        proficiency_bonus=2,
        features=(FighterFeatureType.FIGHTING_STYLE, FighterFeatureType.SECOND_WIND, FighterFeatureType.WEAPON_MASTERY),
        second_wind_uses=2,
        weapon_mastery_count=3,
    ),
    2: FighterProgression(
        level=2,
        proficiency_bonus=2,
        features=(FighterFeatureType.ACTION_SURGE, FighterFeatureType.TACTICAL_MIND),
        second_wind_uses=2,
        weapon_mastery_count=3,
        action_surge_uses=1,
    ),
    3: FighterProgression(
        level=3,
        proficiency_bonus=2,
        features=(FighterFeatureType.FIGHTER_SUBCLASS,),
        second_wind_uses=2,
        weapon_mastery_count=3,
        action_surge_uses=1,
    ),
    4: FighterProgression(
        level=4,
        proficiency_bonus=2,
        features=(FighterFeatureType.ABILITY_SCORE_IMPROVEMENT,),
        second_wind_uses=3,
        weapon_mastery_count=4,
        action_surge_uses=1,
    ),
    5: FighterProgression(
        level=5,
        proficiency_bonus=3,
        features=(FighterFeatureType.EXTRA_ATTACK, FighterFeatureType.TACTICAL_SHIFT),
        second_wind_uses=3,
        weapon_mastery_count=4,
        action_surge_uses=1,
        attack_count=2,
    ),
    6: FighterProgression(
        level=6,
        proficiency_bonus=3,
        features=(FighterFeatureType.ABILITY_SCORE_IMPROVEMENT,),
        second_wind_uses=3,
        weapon_mastery_count=4,
        action_surge_uses=1,
        attack_count=2,
    ),
    7: FighterProgression(
        level=7,
        proficiency_bonus=3,
        features=(FighterFeatureType.SUBCLASS_FEATURE,),
        second_wind_uses=3,
        weapon_mastery_count=4,
        action_surge_uses=1,
        attack_count=2,
    ),
    8: FighterProgression(
        level=8,
        proficiency_bonus=3,
        features=(FighterFeatureType.ABILITY_SCORE_IMPROVEMENT,),
        second_wind_uses=3,
        weapon_mastery_count=4,
        action_surge_uses=1,
        attack_count=2,
    ),
    9: FighterProgression(
        level=9,
        proficiency_bonus=4,
        features=(FighterFeatureType.INDOMITABLE, FighterFeatureType.TACTICAL_MASTER),
        second_wind_uses=3,
        weapon_mastery_count=4,
        action_surge_uses=1,
        indomitable_uses=1,
        attack_count=2,
    ),
    10: FighterProgression(
        level=10,
        proficiency_bonus=4,
        features=(FighterFeatureType.SUBCLASS_FEATURE,),
        second_wind_uses=4,
        weapon_mastery_count=5,
        action_surge_uses=1,
        indomitable_uses=1,
        attack_count=2,
    ),
    11: FighterProgression(
        level=11,
        proficiency_bonus=4,
        features=(FighterFeatureType.TWO_EXTRA_ATTACKS,),
        second_wind_uses=4,
        weapon_mastery_count=5,
        action_surge_uses=1,
        indomitable_uses=1,
        attack_count=3,
    ),
    12: FighterProgression(
        level=12,
        proficiency_bonus=4,
        features=(FighterFeatureType.ABILITY_SCORE_IMPROVEMENT,),
        second_wind_uses=4,
        weapon_mastery_count=5,
        action_surge_uses=1,
        indomitable_uses=1,
        attack_count=3,
    ),
    13: FighterProgression(
        level=13,
        proficiency_bonus=5,
        features=(FighterFeatureType.INDOMITABLE, FighterFeatureType.STUDIED_ATTACKS),
        second_wind_uses=4,
        weapon_mastery_count=5,
        action_surge_uses=1,
        indomitable_uses=2,
        attack_count=3,
    ),
    14: FighterProgression(
        level=14,
        proficiency_bonus=5,
        features=(FighterFeatureType.ABILITY_SCORE_IMPROVEMENT,),
        second_wind_uses=4,
        weapon_mastery_count=5,
        action_surge_uses=1,
        indomitable_uses=2,
        attack_count=3,
    ),
    15: FighterProgression(
        level=15,
        proficiency_bonus=5,
        features=(FighterFeatureType.SUBCLASS_FEATURE,),
        second_wind_uses=4,
        weapon_mastery_count=5,
        action_surge_uses=1,
        indomitable_uses=2,
        attack_count=3,
    ),
    16: FighterProgression(
        level=16,
        proficiency_bonus=5,
        features=(FighterFeatureType.ABILITY_SCORE_IMPROVEMENT,),
        second_wind_uses=4,
        weapon_mastery_count=6,
        action_surge_uses=1,
        indomitable_uses=2,
        attack_count=3,
    ),
    17: FighterProgression(
        level=17,
        proficiency_bonus=6,
        features=(FighterFeatureType.ACTION_SURGE, FighterFeatureType.INDOMITABLE),
        second_wind_uses=4,
        weapon_mastery_count=6,
        action_surge_uses=2,
        indomitable_uses=3,
        attack_count=3,
    ),
    18: FighterProgression(
        level=18,
        proficiency_bonus=6,
        features=(FighterFeatureType.SUBCLASS_FEATURE,),
        second_wind_uses=4,
        weapon_mastery_count=6,
        action_surge_uses=2,
        indomitable_uses=3,
        attack_count=3,
    ),
    19: FighterProgression(
        level=19,
        proficiency_bonus=6,
        features=(FighterFeatureType.EPIC_BOON,),
        second_wind_uses=4,
        weapon_mastery_count=6,
        action_surge_uses=2,
        indomitable_uses=3,
        attack_count=3,
    ),
    20: FighterProgression(
        level=20,
        proficiency_bonus=6,
        features=(FighterFeatureType.THREE_EXTRA_ATTACKS,),
        second_wind_uses=4,
        weapon_mastery_count=6,
        action_surge_uses=2,
        indomitable_uses=3,
        attack_count=4,
    ),
}


def fighter_level(classes: list[CharacterClassLevel]) -> int:
    return sum(character_class.level for character_class in classes if character_class.name == ClassType.FIGHTER)


def fighter_class(classes: list[CharacterClassLevel]) -> CharacterClassLevel | None:
    return next((character_class for character_class in classes if character_class.name == ClassType.FIGHTER), None)


def fighter_progression(classes: list[CharacterClassLevel]) -> FighterProgression | None:
    level = fighter_level(classes)
    if level <= 0:
        return None
    return FIGHTER_LEVELS[min(level, max(FIGHTER_LEVELS))]


def fighter_resources(classes: list[CharacterClassLevel]) -> list[ResourceTracker]:
    progression = fighter_progression(classes)
    if progression is None:
        return []

    second_wind_roll_actions = [
        RollAction(
            id=FighterRollActionType.SECOND_WIND_HEAL,
            name=FighterResourceType.SECOND_WIND,
            diceCount=1,
            diceType=DiceType.D10,
            modifier=RollModifierType.CLASS_LEVEL,
            resolution=RollResolutionMode.HEAL_SELF,
            consumesResource=FighterResourceType.SECOND_WIND,
        )
    ]
    if progression.level >= 2:
        second_wind_roll_actions.append(
            RollAction(
                id=FighterRollActionType.TACTICAL_MIND,
                name=FighterRollActionType.TACTICAL_MIND,
                diceCount=1,
                diceType=DiceType.D10,
                resolution=RollResolutionMode.NONE,
                consumesResource=FighterResourceType.SECOND_WIND,
            )
        )

    resources = [
        ResourceTracker(
            id=enum_key(FighterResourceType.SECOND_WIND),
            name=enum_label(FighterResourceType.SECOND_WIND),
            currentUses=progression.second_wind_uses,
            maxUses=progression.second_wind_uses,
            reset=RestType.SHORT_REST,
            activation=TimeEconomy.BONUS_ACTION,
            description="Regain 1d10 plus Fighter level hit points, or spend a use for Tactical Mind.",
            rollActions=second_wind_roll_actions,
            source=enum_label(ClassType.FIGHTER),
        )
    ]
    if progression.action_surge_uses > 0:
        resources.append(
            ResourceTracker(
                id=enum_key(FighterResourceType.ACTION_SURGE),
                name=enum_label(FighterResourceType.ACTION_SURGE),
                currentUses=progression.action_surge_uses,
                maxUses=progression.action_surge_uses,
                reset=RestType.SHORT_REST,
                activation=TimeEconomy.SPECIAL,
                description="Take one additional non-Magic action on your turn.",
                source=enum_label(ClassType.FIGHTER),
            )
        )
    if progression.indomitable_uses > 0:
        resources.append(
            ResourceTracker(
                id=enum_key(FighterResourceType.INDOMITABLE),
                name=enum_label(FighterResourceType.INDOMITABLE),
                currentUses=progression.indomitable_uses,
                maxUses=progression.indomitable_uses,
                reset=RestType.LONG_REST,
                activation=TimeEconomy.SPECIAL,
                description="Reroll a failed saving throw with a bonus equal to Fighter level.",
                source=enum_label(ClassType.FIGHTER),
            )
        )
    return resources


def fighter_features(classes: list[CharacterClassLevel]) -> list[SheetFeature]:
    progression = fighter_progression(classes)
    character_class = fighter_class(classes)
    if progression is None or character_class is None:
        return []
    from dnd_board.rules.feats import fighting_style_features

    features: list[SheetFeature] = []
    for level in range(1, progression.level + 1):
        level_progression = FIGHTER_LEVELS[level]
        features.extend(feature_for_type(feature_type, level_progression, character_class) for feature_type in level_progression.features)

    features.append(feature_for_type(FighterFeatureType.WEAPON_MASTERY, progression, character_class))
    features.extend(fighting_style_features(classes))
    from dnd_board.rules.classes.fighter.archetypes import fighter_subclass_features

    features.extend(fighter_subclass_features(character_class.subclass, progression.level))
    return dedupe_features(features)


def feature_for_type(feature_type: FighterFeatureType, progression: FighterProgression, character_class: CharacterClassLevel) -> SheetFeature:
    descriptions = {
        FighterFeatureType.FIGHTING_STYLE: "Gain a Fighting Style feat. It can be replaced when you gain a Fighter level.",
        FighterFeatureType.SECOND_WIND: "Tracked as a resource.",
        FighterFeatureType.WEAPON_MASTERY: f"Use mastery properties for {progression.weapon_mastery_count} weapon choices.",
        FighterFeatureType.ACTION_SURGE: "Tracked as a resource.",
        FighterFeatureType.TACTICAL_MIND: "Spend Second Wind to add 1d10 to a failed ability check; keep the use if it still fails.",
        FighterFeatureType.FIGHTER_SUBCLASS: subclass_description(character_class),
        FighterFeatureType.ABILITY_SCORE_IMPROVEMENT: "Gain Ability Score Improvement or another feat for which you qualify.",
        FighterFeatureType.EXTRA_ATTACK: f"Attack {progression.attack_count} times when taking the Attack action.",
        FighterFeatureType.TACTICAL_SHIFT: "When using Second Wind as a Bonus Action, move up to half Speed without provoking Opportunity Attacks.",
        FighterFeatureType.SUBCLASS_FEATURE: subclass_description(character_class),
        FighterFeatureType.INDOMITABLE: "Tracked as a resource.",
        FighterFeatureType.TACTICAL_MASTER: "With an eligible mastered weapon, use Push, Sap, or Slow for that attack.",
        FighterFeatureType.TWO_EXTRA_ATTACKS: f"Attack {progression.attack_count} times when taking the Attack action.",
        FighterFeatureType.STUDIED_ATTACKS: "After missing an attack roll against a creature, gain Advantage on your next attack roll against it before the end of your next turn.",
        FighterFeatureType.EPIC_BOON: "Gain an Epic Boon feat or another feat for which you qualify.",
        FighterFeatureType.THREE_EXTRA_ATTACKS: f"Attack {progression.attack_count} times when taking the Attack action.",
    }
    return SheetFeature(
        id=enum_key(feature_type),
        name=enum_label(feature_type),
        source=enum_label(ClassType.FIGHTER),
        activation=feature_activation(feature_type),
        description=descriptions[feature_type],
    )


def feature_activation(feature_type: FighterFeatureType) -> TimeEconomy:
    if feature_type == FighterFeatureType.SECOND_WIND:
        return TimeEconomy.BONUS_ACTION
    return TimeEconomy.SPECIAL if feature_type in {FighterFeatureType.ACTION_SURGE, FighterFeatureType.INDOMITABLE} else TimeEconomy.PASSIVE


def subclass_description(character_class: CharacterClassLevel) -> str:
    if character_class.subclass is None:
        return "Choose a Fighter subclass."
    if isinstance(character_class.subclass, FighterSubclassType):
        source = rule_source_label(fighter_subclass_source(character_class.subclass))
        return f"{fighter_subclass_label(character_class.subclass)} subclass features ({source}) are included up to your Fighter level."
    return f"{enum_label(character_class.subclass)} subclass features are included up to your Fighter level."


def dedupe_features(features: list[SheetFeature]) -> list[SheetFeature]:
    deduped: dict[str, SheetFeature] = {}
    for feature in features:
        deduped[feature.id] = feature
    return list(deduped.values())
