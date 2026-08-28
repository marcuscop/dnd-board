from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from dnd_board.character_sheet import (
    BattleMasterManeuverType,
    CharacterClassLevel,
    ClassType,
    DiceType,
    FightingStyleType,
    ResourceTracker,
    RestType,
    RollAction,
    RollResolutionMode,
    SheetFeature,
    TimeEconomy,
    enum_key,
    enum_label,
)


class BattleMasterFeatureType(Enum):
    COMBAT_SUPERIORITY = auto()
    STUDENT_OF_WAR = auto()
    KNOW_YOUR_ENEMY = auto()
    IMPROVED_COMBAT_SUPERIORITY = auto()
    RELENTLESS = auto()


class BattleMasterResourceType(Enum):
    SUPERIORITY_DICE = auto()


@dataclass(frozen=True)
class BattleMasterManeuverDefinition:
    maneuverType: BattleMasterManeuverType
    activation: TimeEconomy
    description: str


@dataclass(frozen=True)
class BattleMasterCombatProgression:
    minimum_level: int
    superiority_dice_count: int
    superiority_die: DiceType


@dataclass(frozen=True)
class BattleMasterFeatureProgression:
    featureType: BattleMasterFeatureType
    minimum_level: int
    description: str


SUPERIOR_TECHNIQUE_DICE_BONUS = 1
SUPERIOR_TECHNIQUE_STANDALONE_DIE = DiceType.D6

BATTLE_MASTER_COMBAT_PROGRESSION: tuple[BattleMasterCombatProgression, ...] = (
    BattleMasterCombatProgression(minimum_level=3, superiority_dice_count=4, superiority_die=DiceType.D8),
    BattleMasterCombatProgression(minimum_level=7, superiority_dice_count=5, superiority_die=DiceType.D8),
    BattleMasterCombatProgression(minimum_level=10, superiority_dice_count=5, superiority_die=DiceType.D10),
    BattleMasterCombatProgression(minimum_level=15, superiority_dice_count=6, superiority_die=DiceType.D10),
    BattleMasterCombatProgression(minimum_level=18, superiority_dice_count=6, superiority_die=DiceType.D12),
)

BATTLE_MASTER_FEATURE_PROGRESSION: tuple[BattleMasterFeatureProgression, ...] = (
    BattleMasterFeatureProgression(
        featureType=BattleMasterFeatureType.COMBAT_SUPERIORITY,
        minimum_level=3,
        description="Learn Battle Master maneuvers fueled by superiority dice. Superiority dice are tracked as a resource.",
    ),
    BattleMasterFeatureProgression(
        featureType=BattleMasterFeatureType.STUDENT_OF_WAR,
        minimum_level=3,
        description="Gain proficiency with one type of artisan's tools of your choice.",
    ),
    BattleMasterFeatureProgression(
        featureType=BattleMasterFeatureType.KNOW_YOUR_ENEMY,
        minimum_level=7,
        description="After spending at least 1 minute observing or interacting with a creature outside combat, learn whether it is equal, superior, or inferior to you in two listed characteristics of your choice.",
    ),
    BattleMasterFeatureProgression(
        featureType=BattleMasterFeatureType.IMPROVED_COMBAT_SUPERIORITY,
        minimum_level=10,
        description="Your superiority dice become d10s at Fighter level 10 and d12s at Fighter level 18.",
    ),
    BattleMasterFeatureProgression(
        featureType=BattleMasterFeatureType.RELENTLESS,
        minimum_level=15,
        description="When you roll Initiative and have no superiority dice remaining, regain 1 superiority die.",
    ),
)


BATTLE_MASTER_MANEUVERS: dict[BattleMasterManeuverType, BattleMasterManeuverDefinition] = {
    BattleMasterManeuverType.AMBUSH: BattleMasterManeuverDefinition(
        maneuverType=BattleMasterManeuverType.AMBUSH,
        activation=TimeEconomy.SPECIAL,
        description="When you make a Dexterity (Stealth) check or an Initiative roll, expend one superiority die and add it to the roll, provided you are not incapacitated.",
    ),
    BattleMasterManeuverType.BAIT_AND_SWITCH: BattleMasterManeuverDefinition(
        maneuverType=BattleMasterManeuverType.BAIT_AND_SWITCH,
        activation=TimeEconomy.MOVEMENT,
        description="When you are within 5 feet of a willing, non-incapacitated creature on your turn, expend one superiority die and spend at least 5 feet of movement to switch places without provoking opportunity attacks. Add the die roll as an AC bonus to you or that creature until your next turn starts.",
    ),
    BattleMasterManeuverType.BRACE: BattleMasterManeuverDefinition(
        maneuverType=BattleMasterManeuverType.BRACE,
        activation=TimeEconomy.REACTION,
        description="When a creature you can see moves into your melee weapon reach, expend one superiority die and use your Reaction to attack with that weapon. On a hit, add the die to the damage roll.",
    ),
    BattleMasterManeuverType.COMMANDERS_STRIKE: BattleMasterManeuverDefinition(
        maneuverType=BattleMasterManeuverType.COMMANDERS_STRIKE,
        activation=TimeEconomy.BONUS_ACTION,
        description="When you take the Attack action, forgo one attack and use a Bonus Action to choose a friendly creature who can see or hear you. Expend one superiority die; that creature uses its Reaction to make one weapon attack and adds the die to the damage roll.",
    ),
    BattleMasterManeuverType.COMMANDING_PRESENCE: BattleMasterManeuverDefinition(
        maneuverType=BattleMasterManeuverType.COMMANDING_PRESENCE,
        activation=TimeEconomy.SPECIAL,
        description="When you make a Charisma (Intimidation), Charisma (Performance), or Charisma (Persuasion) check, expend one superiority die and add it to the ability check.",
    ),
    BattleMasterManeuverType.DISARMING_ATTACK: BattleMasterManeuverDefinition(
        maneuverType=BattleMasterManeuverType.DISARMING_ATTACK,
        activation=TimeEconomy.SPECIAL,
        description="When you hit with a weapon attack, expend one superiority die and add it to damage. The target makes a Strength save or drops one held item of your choice at its feet.",
    ),
    BattleMasterManeuverType.DISTRACTING_STRIKE: BattleMasterManeuverDefinition(
        maneuverType=BattleMasterManeuverType.DISTRACTING_STRIKE,
        activation=TimeEconomy.SPECIAL,
        description="When you hit with a weapon attack, expend one superiority die and add it to damage. The next attack roll against the target by someone other than you has Advantage if made before your next turn starts.",
    ),
    BattleMasterManeuverType.EVASIVE_FOOTWORK: BattleMasterManeuverDefinition(
        maneuverType=BattleMasterManeuverType.EVASIVE_FOOTWORK,
        activation=TimeEconomy.MOVEMENT,
        description="When you move, expend one superiority die and add the roll to your AC until you stop moving.",
    ),
    BattleMasterManeuverType.FEINTING_ATTACK: BattleMasterManeuverDefinition(
        maneuverType=BattleMasterManeuverType.FEINTING_ATTACK,
        activation=TimeEconomy.BONUS_ACTION,
        description="Use a Bonus Action and expend one superiority die to feint against a creature within 5 feet. You have Advantage on your next attack roll against it this turn; on a hit, add the die to damage.",
    ),
    BattleMasterManeuverType.GOADING_ATTACK: BattleMasterManeuverDefinition(
        maneuverType=BattleMasterManeuverType.GOADING_ATTACK,
        activation=TimeEconomy.SPECIAL,
        description="When you hit with a weapon attack, expend one superiority die and add it to damage. The target makes a Wisdom save or has Disadvantage on attack rolls against targets other than you until your next turn ends.",
    ),
    BattleMasterManeuverType.GRAPPLING_STRIKE: BattleMasterManeuverDefinition(
        maneuverType=BattleMasterManeuverType.GRAPPLING_STRIKE,
        activation=TimeEconomy.BONUS_ACTION,
        description="Immediately after you hit with a melee attack on your turn, expend one superiority die and try to grapple the target as a Bonus Action. Add the die to your Strength (Athletics) check.",
    ),
    BattleMasterManeuverType.LUNGING_ATTACK: BattleMasterManeuverDefinition(
        maneuverType=BattleMasterManeuverType.LUNGING_ATTACK,
        activation=TimeEconomy.SPECIAL,
        description="When you make a melee weapon attack on your turn, expend one superiority die to increase reach for that attack by 5 feet. On a hit, add the die to damage.",
    ),
    BattleMasterManeuverType.MANEUVERING_ATTACK: BattleMasterManeuverDefinition(
        maneuverType=BattleMasterManeuverType.MANEUVERING_ATTACK,
        activation=TimeEconomy.SPECIAL,
        description="When you hit with a weapon attack, expend one superiority die and add it to damage. Choose a friendly creature who can see or hear you; it can use its Reaction to move up to half Speed without provoking opportunity attacks from your target.",
    ),
    BattleMasterManeuverType.MENACING_ATTACK: BattleMasterManeuverDefinition(
        maneuverType=BattleMasterManeuverType.MENACING_ATTACK,
        activation=TimeEconomy.SPECIAL,
        description="When you hit with a weapon attack, expend one superiority die and add it to damage. The target makes a Wisdom save or is frightened of you until your next turn ends.",
    ),
    BattleMasterManeuverType.PARRY: BattleMasterManeuverDefinition(
        maneuverType=BattleMasterManeuverType.PARRY,
        activation=TimeEconomy.REACTION,
        description="When another creature damages you with a melee attack, use your Reaction and expend one superiority die to reduce the damage by the die roll plus your Dexterity modifier.",
    ),
    BattleMasterManeuverType.PRECISION_ATTACK: BattleMasterManeuverDefinition(
        maneuverType=BattleMasterManeuverType.PRECISION_ATTACK,
        activation=TimeEconomy.SPECIAL,
        description="When you make a weapon attack roll, expend one superiority die and add it to the roll before or after rolling, but before attack effects are applied.",
    ),
    BattleMasterManeuverType.PUSHING_ATTACK: BattleMasterManeuverDefinition(
        maneuverType=BattleMasterManeuverType.PUSHING_ATTACK,
        activation=TimeEconomy.SPECIAL,
        description="When you hit with a weapon attack, expend one superiority die and add it to damage. If the target is Large or smaller, it makes a Strength save or is pushed up to 15 feet away from you.",
    ),
    BattleMasterManeuverType.QUICK_TOSS: BattleMasterManeuverDefinition(
        maneuverType=BattleMasterManeuverType.QUICK_TOSS,
        activation=TimeEconomy.BONUS_ACTION,
        description="As a Bonus Action, expend one superiority die and make a ranged attack with a thrown weapon, drawing it as part of the attack. On a hit, add the die to damage.",
    ),
    BattleMasterManeuverType.RALLY: BattleMasterManeuverDefinition(
        maneuverType=BattleMasterManeuverType.RALLY,
        activation=TimeEconomy.BONUS_ACTION,
        description="On your turn, use a Bonus Action and expend one superiority die to choose a friendly creature who can see or hear you. It gains temporary hit points equal to the die roll plus your Charisma modifier.",
    ),
    BattleMasterManeuverType.RIPOSTE: BattleMasterManeuverDefinition(
        maneuverType=BattleMasterManeuverType.RIPOSTE,
        activation=TimeEconomy.REACTION,
        description="When a creature misses you with a melee attack, use your Reaction and expend one superiority die to make a melee weapon attack against it. On a hit, add the die to damage.",
    ),
    BattleMasterManeuverType.SWEEPING_ATTACK: BattleMasterManeuverDefinition(
        maneuverType=BattleMasterManeuverType.SWEEPING_ATTACK,
        activation=TimeEconomy.SPECIAL,
        description="When you hit with a melee weapon attack, expend one superiority die to damage another creature within 5 feet of the original target and within your reach if the original attack roll would hit it. The second creature takes the die roll as the original damage type.",
    ),
    BattleMasterManeuverType.TACTICAL_ASSESSMENT: BattleMasterManeuverDefinition(
        maneuverType=BattleMasterManeuverType.TACTICAL_ASSESSMENT,
        activation=TimeEconomy.SPECIAL,
        description="When you make an Intelligence (Investigation), Intelligence (History), or Wisdom (Insight) check, expend one superiority die and add it to the ability check.",
    ),
    BattleMasterManeuverType.TRIP_ATTACK: BattleMasterManeuverDefinition(
        maneuverType=BattleMasterManeuverType.TRIP_ATTACK,
        activation=TimeEconomy.SPECIAL,
        description="When you hit with a weapon attack, expend one superiority die and add it to damage. If the target is Large or smaller, it makes a Strength save or falls prone.",
    ),
}


def combat_superiority_resource(classes: list[CharacterClassLevel]) -> ResourceTracker | None:
    from dnd_board.rules.fighter import FighterSubclassType

    progression = combat_superiority_progression(classes)
    if progression is None:
        return None
    dice_count, dice_type = progression
    selected_maneuvers = selected_battle_master_maneuvers(classes)
    return ResourceTracker(
        id=enum_key(BattleMasterResourceType.SUPERIORITY_DICE),
        name="Superiority Dice",
        currentUses=dice_count,
        maxUses=dice_count,
        reset=RestType.SHORT_REST,
        activation=TimeEconomy.SPECIAL,
        description=f"Spend one superiority die ({enum_key(dice_type)}) to use a Battle Master maneuver. Maneuver save DC is 8 + Proficiency Bonus + Strength or Dexterity modifier.",
        source=enum_label(FighterSubclassType.BATTLE_MASTER),
        rollActions=[
            RollAction(
                id=definition.maneuverType,
                name=definition.maneuverType,
                diceCount=1,
                diceType=dice_type,
                resolution=RollResolutionMode.NONE,
                consumesResource=BattleMasterResourceType.SUPERIORITY_DICE,
                description=definition.description,
                activation=definition.activation,
            )
            for definition in (BATTLE_MASTER_MANEUVERS[maneuver] for maneuver in selected_maneuvers)
        ],
    )


def combat_superiority_progression(classes: list[CharacterClassLevel]) -> tuple[int, DiceType] | None:
    from dnd_board.rules.fighter import FighterSubclassType

    fighter = next((character_class for character_class in classes if character_class.name == ClassType.FIGHTER), None)
    fighter_level = fighter.level if fighter is not None else 0
    is_battle_master = fighter is not None and fighter.subclass == FighterSubclassType.BATTLE_MASTER
    has_superior_technique = any(
        FightingStyleType.SUPERIOR_TECHNIQUE in (character_class.fightingStyles or [])
        or character_class.fightingStyle == FightingStyleType.SUPERIOR_TECHNIQUE
        for character_class in classes
    )
    battle_master_progression = battle_master_combat_progression(fighter_level) if is_battle_master else None
    if battle_master_progression is None and not has_superior_technique:
        return None

    dice_count = 0
    dice_type = SUPERIOR_TECHNIQUE_STANDALONE_DIE
    if battle_master_progression is not None:
        dice_count = battle_master_progression.superiority_dice_count
        dice_type = battle_master_progression.superiority_die
    if has_superior_technique:
        dice_count += SUPERIOR_TECHNIQUE_DICE_BONUS
    return dice_count, dice_type


def battle_master_combat_progression(fighter_level_value: int) -> BattleMasterCombatProgression | None:
    eligible = [progression for progression in BATTLE_MASTER_COMBAT_PROGRESSION if fighter_level_value >= progression.minimum_level]
    return eligible[-1] if eligible else None


def selected_battle_master_maneuvers(classes: list[CharacterClassLevel]) -> list[BattleMasterManeuverType]:
    maneuvers: list[BattleMasterManeuverType] = []
    for character_class in classes:
        for maneuver in character_class.maneuvers or []:
            if maneuver not in maneuvers:
                maneuvers.append(maneuver)
    if maneuvers:
        return maneuvers
    return list(BATTLE_MASTER_MANEUVERS)


def battle_master_features(character_class: CharacterClassLevel, fighter_level_value: int) -> list[SheetFeature]:
    from dnd_board.rules.fighter import FighterSubclassType

    if character_class.subclass != FighterSubclassType.BATTLE_MASTER:
        return []

    return [
        battle_master_feature(progression)
        for progression in BATTLE_MASTER_FEATURE_PROGRESSION
        if fighter_level_value >= progression.minimum_level
    ]


def battle_master_feature(progression: BattleMasterFeatureProgression) -> SheetFeature:
    from dnd_board.rules.fighter import FighterSubclassType

    return SheetFeature(
        id=enum_key(progression.featureType),
        name=enum_label(progression.featureType),
        source=enum_label(FighterSubclassType.BATTLE_MASTER),
        activation=TimeEconomy.PASSIVE,
        description=progression.description,
    )
