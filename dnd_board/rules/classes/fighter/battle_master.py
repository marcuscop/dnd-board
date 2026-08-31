from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from dnd_board.character_sheet import (
    BattleMasterManeuverType,
    CharacterClassLevel,
    AbilityType,
    ConditionApplicationMode,
    ConditionEffect,
    ConditionType,
    RollModifierType,
    RollResolutionMode,
    SheetFeature,
    TimeEconomy,
    enum_key,
    enum_label,
)
from dnd_board.rules.shared.combat_superiority import (
    COMBAT_SUPERIORITY_PROGRESSION as BATTLE_MASTER_COMBAT_PROGRESSION,
    SUPERIOR_TECHNIQUE_DICE_BONUS,
    SUPERIOR_TECHNIQUE_STANDALONE_DIE,
    BattleMasterResourceType,
    CombatSuperiorityProgression as BattleMasterCombatProgression,
    ScoutSuperiorityActionType,
    SuperiorityActionDefinition,
    combat_superiority_progression,
    combat_superiority_resource,
    combat_superiority_subclass_progression as battle_master_combat_progression,
    scout_superiority_actions,
    selected_battle_master_maneuvers,
    superiority_action_definitions,
    superiority_resource_source,
)


class BattleMasterFeatureType(Enum):
    COMBAT_SUPERIORITY = auto()
    STUDENT_OF_WAR = auto()
    KNOW_YOUR_ENEMY = auto()
    IMPROVED_COMBAT_SUPERIORITY = auto()
    RELENTLESS = auto()


@dataclass(frozen=True)
class BattleMasterManeuverDefinition:
    maneuverType: BattleMasterManeuverType
    activation: TimeEconomy
    description: str
    resolution: RollResolutionMode = RollResolutionMode.NONE
    modifier: RollModifierType = RollModifierType.NONE
    modifierAbility: AbilityType | None = None
    conditionEffects: tuple[ConditionEffect, ...] = ()


@dataclass(frozen=True)
class BattleMasterFeatureProgression:
    featureType: BattleMasterFeatureType
    minimum_level: int
    description: str


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
        resolution=RollResolutionMode.APPLY_DAMAGE,
    ),
    BattleMasterManeuverType.COMMANDERS_STRIKE: BattleMasterManeuverDefinition(
        maneuverType=BattleMasterManeuverType.COMMANDERS_STRIKE,
        activation=TimeEconomy.BONUS_ACTION,
        description="When you take the Attack action, forgo one attack and use a Bonus Action to choose a friendly creature who can see or hear you. Expend one superiority die; that creature uses its Reaction to make one weapon attack and adds the die to the damage roll.",
        resolution=RollResolutionMode.APPLY_DAMAGE,
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
        resolution=RollResolutionMode.APPLY_DAMAGE,
        conditionEffects=(
            ConditionEffect(
                condition=None,
                mode=ConditionApplicationMode.TARGET_SAVE,
                savingThrow=AbilityType.STRENGTH,
                description="On a failed Strength save, the target drops one held item of your choice.",
            ),
        ),
    ),
    BattleMasterManeuverType.DISTRACTING_STRIKE: BattleMasterManeuverDefinition(
        maneuverType=BattleMasterManeuverType.DISTRACTING_STRIKE,
        activation=TimeEconomy.SPECIAL,
        description="When you hit with a weapon attack, expend one superiority die and add it to damage. The next attack roll against the target by someone other than you has Advantage if made before your next turn starts.",
        resolution=RollResolutionMode.APPLY_DAMAGE,
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
        resolution=RollResolutionMode.APPLY_DAMAGE,
    ),
    BattleMasterManeuverType.GOADING_ATTACK: BattleMasterManeuverDefinition(
        maneuverType=BattleMasterManeuverType.GOADING_ATTACK,
        activation=TimeEconomy.SPECIAL,
        description="When you hit with a weapon attack, expend one superiority die and add it to damage. The target makes a Wisdom save or has Disadvantage on attack rolls against targets other than you until your next turn ends.",
        resolution=RollResolutionMode.APPLY_DAMAGE,
        conditionEffects=(
            ConditionEffect(
                condition=None,
                mode=ConditionApplicationMode.TARGET_SAVE,
                savingThrow=AbilityType.WISDOM,
                description="On a failed Wisdom save, the target has Disadvantage on attack rolls against targets other than you until your next turn ends.",
            ),
        ),
    ),
    BattleMasterManeuverType.GRAPPLING_STRIKE: BattleMasterManeuverDefinition(
        maneuverType=BattleMasterManeuverType.GRAPPLING_STRIKE,
        activation=TimeEconomy.BONUS_ACTION,
        description="Immediately after you hit with a melee attack on your turn, expend one superiority die and try to grapple the target as a Bonus Action. Add the die to your Strength (Athletics) check.",
        conditionEffects=(
            ConditionEffect(
                condition=ConditionType.GRAPPLED,
                mode=ConditionApplicationMode.SOURCE_CHECK,
                sourceCheck=AbilityType.STRENGTH,
                contestChecks=[AbilityType.STRENGTH, AbilityType.DEXTERITY],
                description="Source makes a Strength (Athletics) check with the superiority die; target contests with Strength (Athletics) or Dexterity (Acrobatics). On success, target is grappled.",
            ),
        ),
    ),
    BattleMasterManeuverType.LUNGING_ATTACK: BattleMasterManeuverDefinition(
        maneuverType=BattleMasterManeuverType.LUNGING_ATTACK,
        activation=TimeEconomy.SPECIAL,
        description="When you make a melee weapon attack on your turn, expend one superiority die to increase reach for that attack by 5 feet. On a hit, add the die to damage.",
        resolution=RollResolutionMode.APPLY_DAMAGE,
    ),
    BattleMasterManeuverType.MANEUVERING_ATTACK: BattleMasterManeuverDefinition(
        maneuverType=BattleMasterManeuverType.MANEUVERING_ATTACK,
        activation=TimeEconomy.SPECIAL,
        description="When you hit with a weapon attack, expend one superiority die and add it to damage. Choose a friendly creature who can see or hear you; it can use its Reaction to move up to half Speed without provoking opportunity attacks from your target.",
        resolution=RollResolutionMode.APPLY_DAMAGE,
    ),
    BattleMasterManeuverType.MENACING_ATTACK: BattleMasterManeuverDefinition(
        maneuverType=BattleMasterManeuverType.MENACING_ATTACK,
        activation=TimeEconomy.SPECIAL,
        description="When you hit with a weapon attack, expend one superiority die and add it to damage. The target makes a Wisdom save or is frightened of you until your next turn ends.",
        resolution=RollResolutionMode.APPLY_DAMAGE,
        conditionEffects=(
            ConditionEffect(
                condition=ConditionType.FRIGHTENED,
                mode=ConditionApplicationMode.TARGET_SAVE,
                savingThrow=AbilityType.WISDOM,
                description="On a failed Wisdom save, the target is frightened of you until your next turn ends.",
            ),
        ),
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
        resolution=RollResolutionMode.APPLY_DAMAGE,
        conditionEffects=(
            ConditionEffect(
                condition=None,
                mode=ConditionApplicationMode.TARGET_SAVE,
                savingThrow=AbilityType.STRENGTH,
                description="On a failed Strength save, the target is pushed up to 15 feet away from you.",
            ),
        ),
    ),
    BattleMasterManeuverType.QUICK_TOSS: BattleMasterManeuverDefinition(
        maneuverType=BattleMasterManeuverType.QUICK_TOSS,
        activation=TimeEconomy.BONUS_ACTION,
        description="As a Bonus Action, expend one superiority die and make a ranged attack with a thrown weapon, drawing it as part of the attack. On a hit, add the die to damage.",
        resolution=RollResolutionMode.APPLY_DAMAGE,
    ),
    BattleMasterManeuverType.RALLY: BattleMasterManeuverDefinition(
        maneuverType=BattleMasterManeuverType.RALLY,
        activation=TimeEconomy.BONUS_ACTION,
        description="On your turn, use a Bonus Action and expend one superiority die to choose a friendly creature who can see or hear you. It gains temporary hit points equal to the die roll plus your Charisma modifier.",
        resolution=RollResolutionMode.APPLY_TEMPORARY_HIT_POINTS,
        modifier=RollModifierType.ABILITY_MODIFIER,
        modifierAbility=AbilityType.CHARISMA,
    ),
    BattleMasterManeuverType.RIPOSTE: BattleMasterManeuverDefinition(
        maneuverType=BattleMasterManeuverType.RIPOSTE,
        activation=TimeEconomy.REACTION,
        description="When a creature misses you with a melee attack, use your Reaction and expend one superiority die to make a melee weapon attack against it. On a hit, add the die to damage.",
        resolution=RollResolutionMode.APPLY_DAMAGE,
    ),
    BattleMasterManeuverType.SWEEPING_ATTACK: BattleMasterManeuverDefinition(
        maneuverType=BattleMasterManeuverType.SWEEPING_ATTACK,
        activation=TimeEconomy.SPECIAL,
        description="When you hit with a melee weapon attack, expend one superiority die to damage another creature within 5 feet of the original target and within your reach if the original attack roll would hit it. The second creature takes the die roll as the original damage type.",
        resolution=RollResolutionMode.APPLY_DAMAGE,
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
        resolution=RollResolutionMode.APPLY_DAMAGE,
        conditionEffects=(
            ConditionEffect(
                condition=ConditionType.PRONE,
                mode=ConditionApplicationMode.TARGET_SAVE,
                savingThrow=AbilityType.STRENGTH,
                description="On a failed Strength save, the target falls prone.",
            ),
        ),
    ),
}


def battle_master_features(character_class: CharacterClassLevel, fighter_level_value: int) -> list[SheetFeature]:
    from dnd_board.rules.classes.fighter.base import FighterSubclassType

    if character_class.subclass != FighterSubclassType.BATTLE_MASTER:
        return []

    return [
        battle_master_feature(progression)
        for progression in BATTLE_MASTER_FEATURE_PROGRESSION
        if fighter_level_value >= progression.minimum_level
    ]


def battle_master_feature(progression: BattleMasterFeatureProgression) -> SheetFeature:
    from dnd_board.rules.classes.fighter.base import FighterSubclassType

    return SheetFeature(
        id=enum_key(progression.featureType),
        name=enum_label(progression.featureType),
        source=enum_label(FighterSubclassType.BATTLE_MASTER),
        activation=TimeEconomy.PASSIVE,
        description=progression.description,
    )
