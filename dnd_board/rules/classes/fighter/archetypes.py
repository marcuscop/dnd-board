from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from dnd_board.character_sheet import (
    AbilityScores,
    DiceType,
    ResourceTracker,
    RestType,
    RollAction,
    RollResolutionMode,
    SheetAbility,
    SheetFeature,
    TimeEconomy,
    ability_modifier,
    enum_key,
    enum_label,
)
from dnd_board.rules.classes.fighter.base import FighterSubclassType
from dnd_board.rules.classes.fighter.battle_master import battle_master_features
from dnd_board.rules.classes.fighter.champion import champion_features


class BanneretFeatureType(Enum):
    RALLYING_CRY = auto()
    ROYAL_ENVOY = auto()
    INSPIRING_SURGE = auto()
    BULWARK = auto()


class CavalierFeatureType(Enum):
    BONUS_PROFICIENCY = auto()
    BORN_TO_THE_SADDLE = auto()
    UNWAVERING_MARK = auto()
    WARDING_MANEUVER = auto()
    HOLD_THE_LINE = auto()
    FEROCIOUS_CHARGER = auto()
    VIGILANT_DEFENDER = auto()


class SamuraiFeatureType(Enum):
    BONUS_PROFICIENCY = auto()
    FIGHTING_SPIRIT = auto()
    ELEGANT_COURTIER = auto()
    TIRELESS_SPIRIT = auto()
    RAPID_STRIKE = auto()
    STRENGTH_BEFORE_DEATH = auto()


class BruteFeatureType(Enum):
    BRUTE_FORCE = auto()
    BRUTISH_DURABILITY = auto()
    ADDITIONAL_FIGHTING_STYLE = auto()
    DEVASTATING_CRITICAL = auto()
    SURVIVOR = auto()


class ScoutFeatureType(Enum):
    BONUS_PROFICIENCIES = auto()
    COMBAT_SUPERIORITY = auto()
    NATURAL_EXPLORER = auto()
    IMPROVED_COMBAT_SUPERIORITY = auto()
    RELENTLESS = auto()


class SharpshooterFeatureType(Enum):
    STEADY_AIM = auto()
    CAREFUL_EYES = auto()
    CLOSE_QUARTERS_SHOOTING = auto()
    RAPID_STRIKE = auto()
    SNAP_SHOT = auto()


class FighterSubclassResourceType(Enum):
    UNWAVERING_MARK = auto()
    WARDING_MANEUVER = auto()
    FIGHTING_SPIRIT = auto()
    STRENGTH_BEFORE_DEATH = auto()
    STEADY_AIM = auto()


class FighterSubclassRollActionType(Enum):
    WARDING_MANEUVER = auto()
    BRUTE_FORCE = auto()
    BRUTISH_DURABILITY = auto()


@dataclass(frozen=True)
class SubclassFeatureProgression:
    subclass: FighterSubclassType
    featureType: Enum
    minimum_level: int
    activation: TimeEconomy
    description: str


@dataclass(frozen=True)
class BruteForceProgression:
    minimum_level: int
    die: DiceType


BRUTE_FORCE_PROGRESSION: tuple[BruteForceProgression, ...] = (
    BruteForceProgression(minimum_level=3, die=DiceType.D4),
    BruteForceProgression(minimum_level=10, die=DiceType.D6),
    BruteForceProgression(minimum_level=16, die=DiceType.D8),
    BruteForceProgression(minimum_level=20, die=DiceType.D10),
)


SUBCLASS_FEATURES: tuple[SubclassFeatureProgression, ...] = (
    SubclassFeatureProgression(
        subclass=FighterSubclassType.BANNERET,
        featureType=BanneretFeatureType.RALLYING_CRY,
        minimum_level=3,
        activation=TimeEconomy.SPECIAL,
        description="When you use Second Wind, choose up to three allied creatures within 60 feet that can see or hear you. Each regains hit points equal to your Fighter level.",
    ),
    SubclassFeatureProgression(
        subclass=FighterSubclassType.BANNERET,
        featureType=BanneretFeatureType.ROYAL_ENVOY,
        minimum_level=7,
        activation=TimeEconomy.PASSIVE,
        description="Gain Persuasion proficiency, or Animal Handling, Insight, Intimidation, or Performance if already proficient. Double your proficiency bonus for Persuasion checks.",
    ),
    SubclassFeatureProgression(
        subclass=FighterSubclassType.BANNERET,
        featureType=BanneretFeatureType.INSPIRING_SURGE,
        minimum_level=10,
        activation=TimeEconomy.SPECIAL,
        description="When you use Action Surge, one allied creature within 60 feet that can see or hear you can use its Reaction to make one weapon attack. At level 18, choose two allies instead.",
    ),
    SubclassFeatureProgression(
        subclass=FighterSubclassType.BANNERET,
        featureType=BanneretFeatureType.BULWARK,
        minimum_level=15,
        activation=TimeEconomy.SPECIAL,
        description="When you use Indomitable on an Intelligence, Wisdom, or Charisma save, one allied creature within 60 feet that failed the same save and can see or hear you can reroll too.",
    ),
    SubclassFeatureProgression(
        subclass=FighterSubclassType.CAVALIER,
        featureType=CavalierFeatureType.BONUS_PROFICIENCY,
        minimum_level=3,
        activation=TimeEconomy.PASSIVE,
        description="Gain Animal Handling, History, Insight, Performance, or Persuasion proficiency, or learn one language.",
    ),
    SubclassFeatureProgression(
        subclass=FighterSubclassType.CAVALIER,
        featureType=CavalierFeatureType.BORN_TO_THE_SADDLE,
        minimum_level=3,
        activation=TimeEconomy.PASSIVE,
        description="Advantage on saves to avoid falling from your mount, land on your feet from a fall of 10 feet or less if not incapacitated, and mount or dismount for only 5 feet of movement.",
    ),
    SubclassFeatureProgression(
        subclass=FighterSubclassType.CAVALIER,
        featureType=CavalierFeatureType.UNWAVERING_MARK,
        minimum_level=3,
        activation=TimeEconomy.SPECIAL,
        description="When you hit with a melee weapon attack, mark the target until your next turn ends. While within 5 feet of you, it has Disadvantage on attacks that do not target you. If it damages another creature, you can spend a use to make an advantaged Bonus Action melee weapon attack on your next turn, adding half Fighter level to weapon damage.",
    ),
    SubclassFeatureProgression(
        subclass=FighterSubclassType.CAVALIER,
        featureType=CavalierFeatureType.WARDING_MANEUVER,
        minimum_level=7,
        activation=TimeEconomy.REACTION,
        description="When you or a creature you can see within 5 feet is hit by an attack while you wield a melee weapon or shield, roll 1d8 and add it to the target's AC. If the attack still hits, the target has resistance to that attack's damage.",
    ),
    SubclassFeatureProgression(
        subclass=FighterSubclassType.CAVALIER,
        featureType=CavalierFeatureType.HOLD_THE_LINE,
        minimum_level=10,
        activation=TimeEconomy.PASSIVE,
        description="Creatures provoke an opportunity attack when they move 5 feet or more within your reach. On a hit with an opportunity attack, the target's speed is 0 until the current turn ends.",
    ),
    SubclassFeatureProgression(
        subclass=FighterSubclassType.CAVALIER,
        featureType=CavalierFeatureType.FEROCIOUS_CHARGER,
        minimum_level=15,
        activation=TimeEconomy.SPECIAL,
        description="Once on each of your turns, if you move at least 10 feet straight before hitting a creature with an attack, it must pass a Strength save or fall prone.",
    ),
    SubclassFeatureProgression(
        subclass=FighterSubclassType.CAVALIER,
        featureType=CavalierFeatureType.VIGILANT_DEFENDER,
        minimum_level=18,
        activation=TimeEconomy.REACTION,
        description="In combat, take one special Reaction on every creature's turn except yours, usable only for opportunity attacks and not on the same turn as your normal Reaction.",
    ),
    SubclassFeatureProgression(
        subclass=FighterSubclassType.SAMURAI,
        featureType=SamuraiFeatureType.BONUS_PROFICIENCY,
        minimum_level=3,
        activation=TimeEconomy.PASSIVE,
        description="Gain History, Insight, Performance, or Persuasion proficiency, or learn one language.",
    ),
    SubclassFeatureProgression(
        subclass=FighterSubclassType.SAMURAI,
        featureType=SamuraiFeatureType.FIGHTING_SPIRIT,
        minimum_level=3,
        activation=TimeEconomy.BONUS_ACTION,
        description="As a Bonus Action, gain Advantage on all weapon attack rolls until the current turn ends and gain temporary hit points: 5 at level 3, 10 at level 10, and 15 at level 15.",
    ),
    SubclassFeatureProgression(
        subclass=FighterSubclassType.SAMURAI,
        featureType=SamuraiFeatureType.ELEGANT_COURTIER,
        minimum_level=7,
        activation=TimeEconomy.PASSIVE,
        description="Add your Wisdom modifier to Charisma (Persuasion) checks. Gain Wisdom saving throw proficiency, or Intelligence or Charisma saving throw proficiency if already proficient.",
    ),
    SubclassFeatureProgression(
        subclass=FighterSubclassType.SAMURAI,
        featureType=SamuraiFeatureType.TIRELESS_SPIRIT,
        minimum_level=10,
        activation=TimeEconomy.SPECIAL,
        description="When you roll Initiative and have no uses of Fighting Spirit remaining, regain 1 use.",
    ),
    SubclassFeatureProgression(
        subclass=FighterSubclassType.SAMURAI,
        featureType=SamuraiFeatureType.RAPID_STRIKE,
        minimum_level=15,
        activation=TimeEconomy.SPECIAL,
        description="Once on your turn when you take the Attack action and have Advantage on an attack roll, forgo Advantage for that roll to make one additional weapon attack against that target as part of the same action.",
    ),
    SubclassFeatureProgression(
        subclass=FighterSubclassType.SAMURAI,
        featureType=SamuraiFeatureType.STRENGTH_BEFORE_DEATH,
        minimum_level=18,
        activation=TimeEconomy.REACTION,
        description="When damage reduces you to 0 hit points, use your Reaction to delay unconsciousness and immediately take an extra turn. Once per long rest.",
    ),
    SubclassFeatureProgression(
        subclass=FighterSubclassType.BRUTE,
        featureType=BruteFeatureType.BRUTE_FORCE,
        minimum_level=3,
        activation=TimeEconomy.SPECIAL,
        description="When you hit with a proficient weapon and deal damage, roll your Brute Force die and add it to the weapon damage.",
    ),
    SubclassFeatureProgression(
        subclass=FighterSubclassType.BRUTE,
        featureType=BruteFeatureType.BRUTISH_DURABILITY,
        minimum_level=7,
        activation=TimeEconomy.SPECIAL,
        description="Whenever you make a saving throw, roll 1d6 and add it to the total. If this raises a death saving throw to 20 or higher, gain the benefits of rolling 20 on the d20.",
    ),
    SubclassFeatureProgression(
        subclass=FighterSubclassType.BRUTE,
        featureType=BruteFeatureType.ADDITIONAL_FIGHTING_STYLE,
        minimum_level=10,
        activation=TimeEconomy.PASSIVE,
        description="Choose a second Fighting Style option.",
    ),
    SubclassFeatureProgression(
        subclass=FighterSubclassType.BRUTE,
        featureType=BruteFeatureType.DEVASTATING_CRITICAL,
        minimum_level=15,
        activation=TimeEconomy.SPECIAL,
        description="When you score a critical hit with a weapon attack, add bonus damage equal to your Fighter level.",
    ),
    SubclassFeatureProgression(
        subclass=FighterSubclassType.BRUTE,
        featureType=BruteFeatureType.SURVIVOR,
        minimum_level=18,
        activation=TimeEconomy.PASSIVE,
        description="At the start of each turn in combat, regain hit points equal to 5 + Constitution modifier, minimum 1, if you are Bloodied, above 0 HP, and below or at half HP.",
    ),
    SubclassFeatureProgression(
        subclass=FighterSubclassType.SCOUT,
        featureType=ScoutFeatureType.BONUS_PROFICIENCIES,
        minimum_level=3,
        activation=TimeEconomy.PASSIVE,
        description="Gain proficiency in three of Acrobatics, Athletics, Investigation, Medicine, Nature, Perception, Stealth, or Survival; thieves' tools can replace one choice.",
    ),
    SubclassFeatureProgression(
        subclass=FighterSubclassType.SCOUT,
        featureType=ScoutFeatureType.COMBAT_SUPERIORITY,
        minimum_level=3,
        activation=TimeEconomy.SPECIAL,
        description="Gain Scout superiority dice for Survival Superiority, Precision Attack, and Scout's Evasion. Superiority dice are tracked as a resource.",
    ),
    SubclassFeatureProgression(
        subclass=FighterSubclassType.SCOUT,
        featureType=ScoutFeatureType.NATURAL_EXPLORER,
        minimum_level=3,
        activation=TimeEconomy.PASSIVE,
        description="Choose favored terrain. Double proficiency for proficient Intelligence or Wisdom checks related to it, and gain travel benefits while moving for an hour or more in that terrain. Choose additional favored terrain at levels 7 and 15.",
    ),
    SubclassFeatureProgression(
        subclass=FighterSubclassType.SCOUT,
        featureType=ScoutFeatureType.IMPROVED_COMBAT_SUPERIORITY,
        minimum_level=10,
        activation=TimeEconomy.PASSIVE,
        description="Your Scout superiority dice become d10s at Fighter level 10 and d12s at Fighter level 18.",
    ),
    SubclassFeatureProgression(
        subclass=FighterSubclassType.SCOUT,
        featureType=ScoutFeatureType.RELENTLESS,
        minimum_level=15,
        activation=TimeEconomy.SPECIAL,
        description="When you roll Initiative and have no superiority dice remaining, regain 1 superiority die.",
    ),
    SubclassFeatureProgression(
        subclass=FighterSubclassType.SHARPSHOOTER,
        featureType=SharpshooterFeatureType.STEADY_AIM,
        minimum_level=3,
        activation=TimeEconomy.BONUS_ACTION,
        description="As a Bonus Action, aim at a creature you can see within range of a wielded ranged weapon. Until the turn ends, attacks with that weapon against the target ignore half and three-quarters cover and deal extra damage equal to 2 + half Fighter level.",
    ),
    SubclassFeatureProgression(
        subclass=FighterSubclassType.SHARPSHOOTER,
        featureType=SharpshooterFeatureType.CAREFUL_EYES,
        minimum_level=7,
        activation=TimeEconomy.BONUS_ACTION,
        description="Take the Search action as a Bonus Action. Also gain Perception, Investigation, or Survival proficiency.",
    ),
    SubclassFeatureProgression(
        subclass=FighterSubclassType.SHARPSHOOTER,
        featureType=SharpshooterFeatureType.CLOSE_QUARTERS_SHOOTING,
        minimum_level=10,
        activation=TimeEconomy.PASSIVE,
        description="Ranged attacks within 5 feet of an enemy do not have Disadvantage. If you hit a creature within 5 feet with a ranged attack on your turn, it cannot take Reactions until the turn ends.",
    ),
    SubclassFeatureProgression(
        subclass=FighterSubclassType.SHARPSHOOTER,
        featureType=SharpshooterFeatureType.RAPID_STRIKE,
        minimum_level=15,
        activation=TimeEconomy.BONUS_ACTION,
        description="If you have Advantage on a weapon attack against a target on your turn, forgo that Advantage to make one additional weapon attack against the same target as a Bonus Action.",
    ),
    SubclassFeatureProgression(
        subclass=FighterSubclassType.SHARPSHOOTER,
        featureType=SharpshooterFeatureType.SNAP_SHOT,
        minimum_level=18,
        activation=TimeEconomy.SPECIAL,
        description="If you take the Attack action on your first turn of combat, make one additional ranged weapon attack as part of that action.",
    ),
)


def fighter_subclass_features(subclass: FighterSubclassType | None, fighter_level_value: int) -> list[SheetFeature]:
    if subclass is None:
        return []
    if subclass == FighterSubclassType.CHAMPION:
        return champion_features(subclass_character_class(subclass, fighter_level_value), fighter_level_value)
    if subclass == FighterSubclassType.BATTLE_MASTER:
        return battle_master_features(subclass_character_class(subclass, fighter_level_value), fighter_level_value)
    return [
        SheetFeature(
            id=enum_key(progression.featureType),
            name=enum_label(progression.featureType),
            source=enum_label(progression.subclass),
            activation=progression.activation,
            description=progression.description,
        )
        for progression in SUBCLASS_FEATURES
        if progression.subclass == subclass and fighter_level_value >= progression.minimum_level
    ]


def fighter_subclass_resources(classes, ability_scores: AbilityScores | None) -> list[ResourceTracker]:
    character_class = fighter_subclass_class(classes)
    if character_class is None:
        return []
    subclass = character_class.subclass
    fighter_level_value = character_class.level
    resources: list[ResourceTracker] = []
    if subclass == FighterSubclassType.CAVALIER and fighter_level_value >= 3:
        resources.append(
            ResourceTracker(
                id=enum_key(FighterSubclassResourceType.UNWAVERING_MARK),
                name=enum_label(FighterSubclassResourceType.UNWAVERING_MARK),
                currentUses=max(1, ability_modifier(ability_scores.strength if ability_scores else 10)),
                maxUses=max(1, ability_modifier(ability_scores.strength if ability_scores else 10)),
                reset=RestType.LONG_REST,
                activation=TimeEconomy.BONUS_ACTION,
                description="Spend a use to make the special Unwavering Mark Bonus Action attack after a marked creature damages someone other than you.",
                source=enum_label(FighterSubclassType.CAVALIER),
            )
        )
    if subclass == FighterSubclassType.CAVALIER and fighter_level_value >= 7:
        uses = max(1, ability_modifier(ability_scores.constitution if ability_scores else 10))
        resources.append(
            ResourceTracker(
                id=enum_key(FighterSubclassResourceType.WARDING_MANEUVER),
                name=enum_label(FighterSubclassResourceType.WARDING_MANEUVER),
                currentUses=uses,
                maxUses=uses,
                reset=RestType.LONG_REST,
                activation=TimeEconomy.REACTION,
                description="Roll 1d8 and add it to the target's AC against the triggering attack.",
                rollActions=[
                    RollAction(
                        id=FighterSubclassRollActionType.WARDING_MANEUVER,
                        name=FighterSubclassRollActionType.WARDING_MANEUVER,
                        diceCount=1,
                        diceType=DiceType.D8,
                        resolution=RollResolutionMode.NONE,
                        consumesResource=FighterSubclassResourceType.WARDING_MANEUVER,
                        activation=TimeEconomy.REACTION,
                        source=enum_label(FighterSubclassType.CAVALIER),
                    )
                ],
                source=enum_label(FighterSubclassType.CAVALIER),
            )
        )
    if subclass == FighterSubclassType.SAMURAI and fighter_level_value >= 3:
        resources.append(
            ResourceTracker(
                id=enum_key(FighterSubclassResourceType.FIGHTING_SPIRIT),
                name=enum_label(FighterSubclassResourceType.FIGHTING_SPIRIT),
                currentUses=3,
                maxUses=3,
                reset=RestType.LONG_REST,
                activation=TimeEconomy.BONUS_ACTION,
                description="Gain Advantage on weapon attacks until turn end and temporary hit points from Fighting Spirit.",
                source=enum_label(FighterSubclassType.SAMURAI),
            )
        )
    if subclass == FighterSubclassType.SAMURAI and fighter_level_value >= 18:
        resources.append(
            ResourceTracker(
                id=enum_key(FighterSubclassResourceType.STRENGTH_BEFORE_DEATH),
                name=enum_label(FighterSubclassResourceType.STRENGTH_BEFORE_DEATH),
                currentUses=1,
                maxUses=1,
                reset=RestType.LONG_REST,
                activation=TimeEconomy.REACTION,
                description="Use when damage reduces you to 0 HP to take an extra turn before falling unconscious.",
                source=enum_label(FighterSubclassType.SAMURAI),
            )
        )
    if subclass == FighterSubclassType.SHARPSHOOTER and fighter_level_value >= 3:
        resources.append(
            ResourceTracker(
                id=enum_key(FighterSubclassResourceType.STEADY_AIM),
                name=enum_label(FighterSubclassResourceType.STEADY_AIM),
                currentUses=3,
                maxUses=3,
                reset=RestType.SHORT_REST,
                activation=TimeEconomy.BONUS_ACTION,
                description=f"Aim at a visible target; ranged weapon hits against it deal {2 + fighter_level_value // 2} extra damage this turn.",
                source=enum_label(FighterSubclassType.SHARPSHOOTER),
            )
        )
    return resources


def fighter_subclass_abilities(classes) -> list[SheetAbility]:
    character_class = fighter_subclass_class(classes)
    if character_class is None:
        return []
    subclass = character_class.subclass
    fighter_level_value = character_class.level
    abilities: list[SheetAbility] = []
    if subclass == FighterSubclassType.BRUTE and fighter_level_value >= 3:
        die = brute_force_die(fighter_level_value)
        if die is not None:
            abilities.append(
                SheetAbility(
                    id=enum_key(FighterSubclassRollActionType.BRUTE_FORCE),
                    name=enum_label(FighterSubclassRollActionType.BRUTE_FORCE),
                    source=enum_label(FighterSubclassType.BRUTE),
                    activation=TimeEconomy.SPECIAL,
                    description="Roll this extra damage after hitting with a proficient weapon.",
                    rollActions=[
                        RollAction(
                            id=FighterSubclassRollActionType.BRUTE_FORCE,
                            name=FighterSubclassRollActionType.BRUTE_FORCE,
                            diceCount=1,
                            diceType=die,
                            resolution=RollResolutionMode.NONE,
                            source=enum_label(FighterSubclassType.BRUTE),
                        )
                    ],
                )
            )
    if subclass == FighterSubclassType.BRUTE and fighter_level_value >= 7:
        abilities.append(
            SheetAbility(
                id=enum_key(FighterSubclassRollActionType.BRUTISH_DURABILITY),
                name=enum_label(FighterSubclassRollActionType.BRUTISH_DURABILITY),
                source=enum_label(FighterSubclassType.BRUTE),
                activation=TimeEconomy.SPECIAL,
                description="Roll this bonus whenever you make a saving throw.",
                rollActions=[
                    RollAction(
                        id=FighterSubclassRollActionType.BRUTISH_DURABILITY,
                        name=FighterSubclassRollActionType.BRUTISH_DURABILITY,
                        diceCount=1,
                        diceType=DiceType.D6,
                        resolution=RollResolutionMode.NONE,
                        source=enum_label(FighterSubclassType.BRUTE),
                    )
                ],
            )
        )
    return abilities


def brute_force_die(fighter_level_value: int) -> DiceType | None:
    eligible = [progression for progression in BRUTE_FORCE_PROGRESSION if fighter_level_value >= progression.minimum_level]
    return eligible[-1].die if eligible else None


def fighter_subclass_class(classes):
    return next((character_class for character_class in classes if character_class.subclass in set(FighterSubclassType)), None)


def subclass_character_class(subclass: FighterSubclassType, fighter_level_value: int):
    from dnd_board.character_sheet import ClassType, CharacterClassLevel

    return CharacterClassLevel(name=ClassType.FIGHTER, level=fighter_level_value, subclass=subclass)
