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
    TimeEconomy,
    enum_key,
    enum_label,
)


class BattleMasterResourceType(Enum):
    SUPERIORITY_DICE = auto()


class ScoutSuperiorityActionType(Enum):
    SURVIVAL_SUPERIORITY = auto()
    SCOUT_PRECISION_ATTACK = auto()
    SCOUTS_EVASION = auto()


class MonsterHunterSuperiorityActionType(Enum):
    HUNTERS_DAMAGE = auto()
    HUNTERS_WILL = auto()
    HUNTERS_EYE = auto()


@dataclass(frozen=True)
class SuperiorityActionDefinition:
    actionType: Enum
    name: Enum
    activation: TimeEconomy
    source: Enum
    description: str


@dataclass(frozen=True)
class CombatSuperiorityProgression:
    minimum_level: int
    superiority_dice_count: int
    superiority_die: DiceType


SUPERIOR_TECHNIQUE_DICE_BONUS = 1
SUPERIOR_TECHNIQUE_STANDALONE_DIE = DiceType.D6

COMBAT_SUPERIORITY_PROGRESSION: tuple[CombatSuperiorityProgression, ...] = (
    CombatSuperiorityProgression(minimum_level=3, superiority_dice_count=4, superiority_die=DiceType.D8),
    CombatSuperiorityProgression(minimum_level=7, superiority_dice_count=5, superiority_die=DiceType.D8),
    CombatSuperiorityProgression(minimum_level=10, superiority_dice_count=5, superiority_die=DiceType.D10),
    CombatSuperiorityProgression(minimum_level=15, superiority_dice_count=6, superiority_die=DiceType.D10),
    CombatSuperiorityProgression(minimum_level=18, superiority_dice_count=6, superiority_die=DiceType.D12),
)


def combat_superiority_resource(classes: list[CharacterClassLevel]) -> ResourceTracker | None:
    progression = combat_superiority_progression(classes)
    if progression is None:
        return None
    dice_count, dice_type = progression
    return ResourceTracker(
        id=enum_key(BattleMasterResourceType.SUPERIORITY_DICE),
        name="Superiority Dice",
        currentUses=dice_count,
        maxUses=dice_count,
        reset=RestType.SHORT_REST,
        activation=TimeEconomy.SPECIAL,
        description=f"Spend one superiority die ({enum_key(dice_type)}) to use a maneuver or superiority option. Save DC is 8 + Proficiency Bonus + Strength or Dexterity modifier.",
        source=superiority_resource_source(classes),
        rollActions=[
            RollAction(
                id=definition.actionType,
                name=definition.name,
                diceCount=1,
                diceType=dice_type,
                resolution=RollResolutionMode.NONE,
                consumesResource=BattleMasterResourceType.SUPERIORITY_DICE,
                description=definition.description,
                activation=definition.activation,
                source=enum_label(definition.source),
            )
            for definition in superiority_action_definitions(classes)
        ],
    )


def combat_superiority_progression(classes: list[CharacterClassLevel]) -> tuple[int, DiceType] | None:
    from dnd_board.rules.classes.fighter.base import FighterSubclassType

    fighter = next((character_class for character_class in classes if character_class.name == ClassType.FIGHTER), None)
    fighter_level = fighter.level if fighter is not None else 0
    has_subclass_superiority = fighter is not None and fighter.subclass in {
        FighterSubclassType.BATTLE_MASTER,
        FighterSubclassType.SCOUT,
        FighterSubclassType.MONSTER_HUNTER,
    }
    has_superior_technique = any(
        FightingStyleType.SUPERIOR_TECHNIQUE in (character_class.fightingStyles or [])
        or character_class.fightingStyle == FightingStyleType.SUPERIOR_TECHNIQUE
        for character_class in classes
    )
    subclass_progression = combat_superiority_subclass_progression(fighter_level) if has_subclass_superiority else None
    if subclass_progression is None and not has_superior_technique:
        return None

    dice_count = 0
    dice_type = SUPERIOR_TECHNIQUE_STANDALONE_DIE
    if subclass_progression is not None:
        dice_count = subclass_progression.superiority_dice_count
        dice_type = subclass_progression.superiority_die
    if has_superior_technique:
        dice_count += SUPERIOR_TECHNIQUE_DICE_BONUS
    return dice_count, dice_type


def combat_superiority_subclass_progression(fighter_level_value: int) -> CombatSuperiorityProgression | None:
    eligible = [progression for progression in COMBAT_SUPERIORITY_PROGRESSION if fighter_level_value >= progression.minimum_level]
    return eligible[-1] if eligible else None


def selected_battle_master_maneuvers(classes: list[CharacterClassLevel]) -> list[BattleMasterManeuverType]:
    from dnd_board.rules.classes.fighter.battle_master import BATTLE_MASTER_MANEUVERS

    maneuvers: list[BattleMasterManeuverType] = []
    for character_class in classes:
        for maneuver in character_class.maneuvers or []:
            if maneuver not in maneuvers:
                maneuvers.append(maneuver)
    if maneuvers:
        return maneuvers
    return list(BATTLE_MASTER_MANEUVERS)


def superiority_action_definitions(classes: list[CharacterClassLevel]) -> list[SuperiorityActionDefinition]:
    from dnd_board.rules.classes.fighter.base import FighterSubclassType
    from dnd_board.rules.classes.fighter.battle_master import BATTLE_MASTER_MANEUVERS

    fighter = next((character_class for character_class in classes if character_class.name == ClassType.FIGHTER), None)
    definitions: list[SuperiorityActionDefinition] = []
    if fighter is not None and fighter.subclass == FighterSubclassType.SCOUT:
        definitions.extend(scout_superiority_actions())
    if fighter is not None and fighter.subclass == FighterSubclassType.MONSTER_HUNTER:
        definitions.extend(monster_hunter_superiority_actions())
    has_battle_master_maneuvers = (
        fighter is not None and fighter.subclass == FighterSubclassType.BATTLE_MASTER
    ) or any(
        FightingStyleType.SUPERIOR_TECHNIQUE in (character_class.fightingStyles or [])
        or character_class.fightingStyle == FightingStyleType.SUPERIOR_TECHNIQUE
        for character_class in classes
    )
    if has_battle_master_maneuvers:
        definitions.extend(
            SuperiorityActionDefinition(
                actionType=definition.maneuverType,
                name=definition.maneuverType,
                activation=definition.activation,
                source=FighterSubclassType.BATTLE_MASTER,
                description=definition.description,
            )
            for definition in (BATTLE_MASTER_MANEUVERS[maneuver] for maneuver in selected_battle_master_maneuvers(classes))
        )
    return definitions


def scout_superiority_actions() -> list[SuperiorityActionDefinition]:
    from dnd_board.rules.classes.fighter.base import FighterSubclassType

    return [
        SuperiorityActionDefinition(
            actionType=ScoutSuperiorityActionType.SURVIVAL_SUPERIORITY,
            name=ScoutSuperiorityActionType.SURVIVAL_SUPERIORITY,
            activation=TimeEconomy.SPECIAL,
            source=FighterSubclassType.SCOUT,
            description="When you make an Athletics, Nature, Perception, Stealth, or Survival check using proficiency, expend one superiority die and add half the roll, rounded up, before learning whether the check succeeds.",
        ),
        SuperiorityActionDefinition(
            actionType=ScoutSuperiorityActionType.SCOUT_PRECISION_ATTACK,
            name=BattleMasterManeuverType.PRECISION_ATTACK,
            activation=TimeEconomy.SPECIAL,
            source=FighterSubclassType.SCOUT,
            description="When you make a weapon attack against a creature, expend one superiority die and add it to the attack roll before or after rolling, but before attack effects are applied.",
        ),
        SuperiorityActionDefinition(
            actionType=ScoutSuperiorityActionType.SCOUTS_EVASION,
            name=ScoutSuperiorityActionType.SCOUTS_EVASION,
            activation=TimeEconomy.REACTION,
            source=FighterSubclassType.SCOUT,
            description="If you are hit by an attack while wearing light or medium armor, expend one superiority die as a Reaction and add the roll to your AC. If the attack still hits, take half damage.",
        ),
    ]


def monster_hunter_superiority_actions() -> list[SuperiorityActionDefinition]:
    from dnd_board.rules.classes.fighter.base import FighterSubclassType

    return [
        SuperiorityActionDefinition(
            actionType=MonsterHunterSuperiorityActionType.HUNTERS_DAMAGE,
            name=MonsterHunterSuperiorityActionType.HUNTERS_DAMAGE,
            activation=TimeEconomy.SPECIAL,
            source=FighterSubclassType.MONSTER_HUNTER,
            description="When you damage a creature with a weapon attack, expend one superiority die and add it to the damage roll. If the attack causes a concentration save, the target has Disadvantage on that save.",
        ),
        SuperiorityActionDefinition(
            actionType=MonsterHunterSuperiorityActionType.HUNTERS_WILL,
            name=MonsterHunterSuperiorityActionType.HUNTERS_WILL,
            activation=TimeEconomy.SPECIAL,
            source=FighterSubclassType.MONSTER_HUNTER,
            description="When you make an Intelligence, Wisdom, or Charisma saving throw, expend one superiority die and add it before learning whether the save succeeds.",
        ),
        SuperiorityActionDefinition(
            actionType=MonsterHunterSuperiorityActionType.HUNTERS_EYE,
            name=MonsterHunterSuperiorityActionType.HUNTERS_EYE,
            activation=TimeEconomy.SPECIAL,
            source=FighterSubclassType.MONSTER_HUNTER,
            description="When you make a Wisdom (Perception) check to detect a hidden creature or object, or a Wisdom (Insight) check to determine whether someone is lying, expend one superiority die and add it before learning whether the check succeeds.",
        ),
    ]


def superiority_resource_source(classes: list[CharacterClassLevel]) -> str:
    from dnd_board.rules.classes.fighter.base import FighterSubclassType

    fighter = next((character_class for character_class in classes if character_class.name == ClassType.FIGHTER), None)
    if fighter is not None and fighter.subclass == FighterSubclassType.SCOUT:
        return enum_label(FighterSubclassType.SCOUT)
    if fighter is not None and fighter.subclass == FighterSubclassType.MONSTER_HUNTER:
        return enum_label(FighterSubclassType.MONSTER_HUNTER)
    return enum_label(FighterSubclassType.BATTLE_MASTER)
