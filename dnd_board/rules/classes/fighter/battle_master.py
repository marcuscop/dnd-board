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
    ULTIMATE_COMBAT_SUPERIORITY = auto()


BATTLE_MASTER_2024_MANEUVERS: frozenset[BattleMasterManeuverType] = frozenset(
    {
        BattleMasterManeuverType.AMBUSH,
        BattleMasterManeuverType.BAIT_AND_SWITCH,
        BattleMasterManeuverType.COMMANDERS_STRIKE,
        BattleMasterManeuverType.COMMANDING_PRESENCE,
        BattleMasterManeuverType.DISARMING_ATTACK,
        BattleMasterManeuverType.DISTRACTING_STRIKE,
        BattleMasterManeuverType.EVASIVE_FOOTWORK,
        BattleMasterManeuverType.FEINTING_ATTACK,
        BattleMasterManeuverType.GOADING_ATTACK,
        BattleMasterManeuverType.LUNGING_ATTACK,
        BattleMasterManeuverType.MANEUVERING_ATTACK,
        BattleMasterManeuverType.MENACING_ATTACK,
        BattleMasterManeuverType.PARRY,
        BattleMasterManeuverType.PRECISION_ATTACK,
        BattleMasterManeuverType.PUSHING_ATTACK,
        BattleMasterManeuverType.RALLY,
        BattleMasterManeuverType.RIPOSTE,
        BattleMasterManeuverType.SWEEPING_ATTACK,
        BattleMasterManeuverType.TACTICAL_ASSESSMENT,
        BattleMasterManeuverType.TRIP_ATTACK,
    }
)


def battle_master_maneuver_label(maneuver: BattleMasterManeuverType) -> str:
    label = enum_label(maneuver)
    return label if maneuver in BATTLE_MASTER_2024_MANEUVERS else f"{label} (Legacy)"


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
        description="Gain proficiency with one type of artisan's tools and one skill from the Fighter level 1 skill list.",
    ),
    BattleMasterFeatureProgression(
        featureType=BattleMasterFeatureType.KNOW_YOUR_ENEMY,
        minimum_level=7,
        description="As a Bonus Action, learn whether a visible creature within 30 feet has damage immunities, resistances, or vulnerabilities, and what they are. Once per Long Rest, or restore the use by expending one Superiority Die.",
    ),
    BattleMasterFeatureProgression(
        featureType=BattleMasterFeatureType.IMPROVED_COMBAT_SUPERIORITY,
        minimum_level=10,
        description="Your superiority dice become d10s at Fighter level 10 and d12s at Fighter level 18.",
    ),
    BattleMasterFeatureProgression(
        featureType=BattleMasterFeatureType.RELENTLESS,
        minimum_level=15,
        description="Once per turn when you use a maneuver, you can roll 1d8 and use that roll instead of expending a Superiority Die.",
    ),
    BattleMasterFeatureProgression(
        featureType=BattleMasterFeatureType.ULTIMATE_COMBAT_SUPERIORITY,
        minimum_level=18,
        description="Your Superiority Die becomes a d12.",
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
        activation=TimeEconomy.SPECIAL,
        description="When you take the Attack action, replace one attack to direct a willing creature who can see or hear you. Expend one Superiority Die; that creature immediately uses its Reaction to make one weapon or Unarmed Strike attack and adds the die to damage on a hit.",
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
        activation=TimeEconomy.BONUS_ACTION,
        description="As a Bonus Action, expend one Superiority Die and take the Disengage action. Add the die roll to your AC until the start of your next turn.",
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
        activation=TimeEconomy.BONUS_ACTION,
        description="As a Bonus Action, expend one Superiority Die and take the Dash action. If you move at least 5 feet straight before hitting with a melee attack as part of this turn's Attack action, add the die to damage.",
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
        description="When another creature damages you with a melee attack roll, use your Reaction and expend one Superiority Die to reduce the damage by the die roll plus your Strength or Dexterity modifier.",
    ),
    BattleMasterManeuverType.PRECISION_ATTACK: BattleMasterManeuverDefinition(
        maneuverType=BattleMasterManeuverType.PRECISION_ATTACK,
        activation=TimeEconomy.SPECIAL,
        description="When you miss with an attack roll, expend one Superiority Die and add it to the attack roll, potentially causing the attack to hit.",
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
        description="As a Bonus Action, expend one Superiority Die and choose an ally within 30 feet who can see or hear you. It gains temporary hit points equal to the die roll plus half your Fighter level.",
        resolution=RollResolutionMode.APPLY_TEMPORARY_HIT_POINTS,
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
    from dnd_board.rules.classes.fighter.base import FighterSubclassType, fighter_subclass_label

    return SheetFeature(
        id=enum_key(progression.featureType),
        name=enum_label(progression.featureType),
        source=fighter_subclass_label(FighterSubclassType.BATTLE_MASTER),
        activation=TimeEconomy.PASSIVE,
        description=progression.description,
    )
