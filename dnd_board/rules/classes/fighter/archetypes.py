from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from dnd_board.character_sheet import (
    AbilityScores,
    AbilityType,
    ArcaneShotType,
    ConditionEffect,
    ConditionApplicationMode,
    ConditionType,
    DamageType,
    DiceType,
    ResourceTracker,
    RestType,
    RollAction,
    RollResolutionMode,
    RuneType,
    SheetAbility,
    SheetFeature,
    SpellCastingTime,
    SpellConeArea,
    SpellComponent,
    SpellCubeArea,
    SpellCylinderArea,
    SpellDuration,
    SpellDurationUnit,
    SpellEntry,
    SpellId,
    SpellLineArea,
    SpellRadiusArea,
    SpellRangeType,
    SpellTargeting,
    SpellSchool,
    SpellSource,
    TimeEconomy,
    ability_modifier,
    enum_key,
    enum_label,
    enum_value,
    proficiency_bonus_for_level,
)
from dnd_board.rules.classes.fighter.base import FighterSubclassType
from dnd_board.rules.classes.fighter.battle_master import battle_master_features


class ChampionFeatureType(Enum):
    IMPROVED_CRITICAL = auto()
    REMARKABLE_ATHLETE = auto()
    ADDITIONAL_FIGHTING_STYLE = auto()
    HEROIC_WARRIOR = auto()
    SUPERIOR_CRITICAL = auto()
    SURVIVOR = auto()


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


class MonsterHunterFeatureType(Enum):
    BONUS_PROFICIENCIES = auto()
    COMBAT_SUPERIORITY = auto()
    HUNTERS_MYSTICISM = auto()
    MONSTER_SLAYER = auto()
    IMPROVED_COMBAT_SUPERIORITY = auto()
    RELENTLESS = auto()


class ArcaneArcherFeatureType(Enum):
    ARCANE_ARCHER_LORE = auto()
    ARCANE_SHOT = auto()
    MAGIC_ARROW = auto()
    CURVING_SHOT = auto()
    EVER_READY_SHOT = auto()


class RuneKnightFeatureType(Enum):
    BONUS_PROFICIENCIES = auto()
    RUNE_CARVER = auto()
    GIANTS_MIGHT = auto()
    RUNIC_SHIELD = auto()
    GREAT_STATURE = auto()
    MASTER_OF_RUNES = auto()
    RUNIC_JUGGERNAUT = auto()


class EchoKnightFeatureType(Enum):
    MANIFEST_ECHO = auto()
    UNLEASH_INCARNATION = auto()
    ECHO_AVATAR = auto()
    SHADOW_MARTYR = auto()
    RECLAIM_POTENTIAL = auto()
    LEGION_OF_ONE = auto()


class PsiWarriorFeatureType(Enum):
    PSIONIC_POWER = auto()
    TELEKINETIC_ADEPT = auto()
    GUARDED_MIND = auto()
    BULWARK_OF_FORCE = auto()
    TELEKINETIC_MASTER = auto()


class EldritchKnightFeatureType(Enum):
    SPELLCASTING = auto()
    WEAPON_BOND = auto()
    WAR_MAGIC = auto()
    ELDRITCH_STRIKE = auto()
    ARCANE_CHARGE = auto()
    IMPROVED_WAR_MAGIC = auto()


class FighterSubclassResourceType(Enum):
    ARCANE_SHOT = auto()
    UNWAVERING_MARK = auto()
    WARDING_MANEUVER = auto()
    FIGHTING_SPIRIT = auto()
    STRENGTH_BEFORE_DEATH = auto()
    STEADY_AIM = auto()
    PROTECTION_FROM_EVIL_AND_GOOD = auto()
    GIANTS_MIGHT = auto()
    RUNIC_SHIELD = auto()
    CLOUD_RUNE = auto()
    FIRE_RUNE = auto()
    FROST_RUNE = auto()
    STONE_RUNE = auto()
    HILL_RUNE = auto()
    STORM_RUNE = auto()
    UNLEASH_INCARNATION = auto()
    SHADOW_MARTYR = auto()
    RECLAIM_POTENTIAL = auto()
    PSIONIC_ENERGY_DICE = auto()
    PSIONIC_ENERGY_RECOVERY = auto()
    TELEKINETIC_MOVEMENT = auto()
    PSI_POWERED_LEAP = auto()
    BULWARK_OF_FORCE = auto()
    TELEKINETIC_MASTER = auto()
    FIRST_LEVEL_SPELL_SLOTS = auto()
    SECOND_LEVEL_SPELL_SLOTS = auto()
    THIRD_LEVEL_SPELL_SLOTS = auto()
    FOURTH_LEVEL_SPELL_SLOTS = auto()


class FighterSubclassRollActionType(Enum):
    WARDING_MANEUVER = auto()
    BRUTE_FORCE = auto()
    BRUTISH_DURABILITY = auto()
    GIANTS_MIGHT_DAMAGE = auto()
    FIRE_RUNE_SHACKLES = auto()
    RECLAIM_POTENTIAL = auto()
    PROTECTIVE_FIELD = auto()
    PSIONIC_STRIKE = auto()


@dataclass(frozen=True)
class SubclassFeatureProgression:
    subclass: FighterSubclassType
    featureType: Enum
    minimum_level: int
    activation: TimeEconomy
    description: str
    conditionEffects: tuple[ConditionEffect, ...] = ()


@dataclass(frozen=True)
class BruteForceProgression:
    minimum_level: int
    die: DiceType


@dataclass(frozen=True)
class EldritchKnightSpellcastingProgression:
    fighter_level: int
    cantrips_known: int
    spells_known: int
    first_level_slots: int = 0
    second_level_slots: int = 0
    third_level_slots: int = 0
    fourth_level_slots: int = 0


BRUTE_FORCE_PROGRESSION: tuple[BruteForceProgression, ...] = (
    BruteForceProgression(minimum_level=3, die=DiceType.D4),
    BruteForceProgression(minimum_level=10, die=DiceType.D6),
    BruteForceProgression(minimum_level=16, die=DiceType.D8),
    BruteForceProgression(minimum_level=20, die=DiceType.D10),
)


ELDRITCH_KNIGHT_SPELLCASTING: dict[int, EldritchKnightSpellcastingProgression] = {
    3: EldritchKnightSpellcastingProgression(3, 2, 3, first_level_slots=2),
    4: EldritchKnightSpellcastingProgression(4, 2, 4, first_level_slots=3),
    5: EldritchKnightSpellcastingProgression(5, 2, 4, first_level_slots=3),
    6: EldritchKnightSpellcastingProgression(6, 2, 4, first_level_slots=3),
    7: EldritchKnightSpellcastingProgression(7, 2, 5, first_level_slots=4, second_level_slots=2),
    8: EldritchKnightSpellcastingProgression(8, 2, 6, first_level_slots=4, second_level_slots=2),
    9: EldritchKnightSpellcastingProgression(9, 2, 6, first_level_slots=4, second_level_slots=2),
    10: EldritchKnightSpellcastingProgression(10, 3, 7, first_level_slots=4, second_level_slots=3),
    11: EldritchKnightSpellcastingProgression(11, 3, 8, first_level_slots=4, second_level_slots=3),
    12: EldritchKnightSpellcastingProgression(12, 3, 8, first_level_slots=4, second_level_slots=3),
    13: EldritchKnightSpellcastingProgression(13, 3, 9, first_level_slots=4, second_level_slots=3, third_level_slots=2),
    14: EldritchKnightSpellcastingProgression(14, 3, 10, first_level_slots=4, second_level_slots=3, third_level_slots=2),
    15: EldritchKnightSpellcastingProgression(15, 3, 10, first_level_slots=4, second_level_slots=3, third_level_slots=2),
    16: EldritchKnightSpellcastingProgression(16, 3, 11, first_level_slots=4, second_level_slots=3, third_level_slots=3),
    17: EldritchKnightSpellcastingProgression(17, 3, 11, first_level_slots=4, second_level_slots=3, third_level_slots=3),
    18: EldritchKnightSpellcastingProgression(18, 3, 11, first_level_slots=4, second_level_slots=3, third_level_slots=3),
    19: EldritchKnightSpellcastingProgression(19, 3, 12, first_level_slots=4, second_level_slots=3, third_level_slots=3, fourth_level_slots=1),
    20: EldritchKnightSpellcastingProgression(20, 3, 13, first_level_slots=4, second_level_slots=3, third_level_slots=3, fourth_level_slots=1),
}


ELDRITCH_KNIGHT_SPELL_CATALOG: dict[SpellId, SpellEntry] = {
    SpellId.BOOMING_BLADE: SpellEntry(
        id=SpellId.BOOMING_BLADE,
        name=SpellId.BOOMING_BLADE,
        source=SpellSource.WIZARD,
        level=0,
        school=SpellSchool.EVOCATION,
        castingAbility=AbilityType.INTELLIGENCE,
        castingTime=SpellCastingTime.ACTION,
        targeting=SpellTargeting(rangeType=SpellRangeType.SELF),
        duration=SpellDuration(unit=SpellDurationUnit.ROUND, amount=1),
        components=[SpellComponent.SOMATIC, SpellComponent.MATERIAL],
        description="Make a melee weapon attack; on a hit, the target takes the weapon's normal effects and is sheathed in booming energy.",
    ),
    SpellId.FIRE_BOLT: SpellEntry(
        id=SpellId.FIRE_BOLT,
        name=SpellId.FIRE_BOLT,
        source=SpellSource.WIZARD,
        level=0,
        school=SpellSchool.EVOCATION,
        castingAbility=AbilityType.INTELLIGENCE,
        castingTime=SpellCastingTime.ACTION,
        targeting=SpellTargeting(rangeType=SpellRangeType.DISTANCE, distanceFeet=120),
        duration=SpellDuration(unit=SpellDurationUnit.INSTANTANEOUS),
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
        description="Make a ranged spell attack that deals fire damage on a hit.",
    ),
    SpellId.GREEN_FLAME_BLADE: SpellEntry(
        id=SpellId.GREEN_FLAME_BLADE,
        name=SpellId.GREEN_FLAME_BLADE,
        source=SpellSource.WIZARD,
        level=0,
        school=SpellSchool.EVOCATION,
        castingAbility=AbilityType.INTELLIGENCE,
        castingTime=SpellCastingTime.ACTION,
        targeting=SpellTargeting(rangeType=SpellRangeType.SELF),
        duration=SpellDuration(unit=SpellDurationUnit.INSTANTANEOUS),
        components=[SpellComponent.SOMATIC, SpellComponent.MATERIAL],
        description="Make a melee weapon attack; green fire can leap from the target to another nearby creature.",
    ),
    SpellId.LIGHT: SpellEntry(
        id=SpellId.LIGHT,
        name=SpellId.LIGHT,
        source=SpellSource.WIZARD,
        level=0,
        school=SpellSchool.EVOCATION,
        castingAbility=AbilityType.INTELLIGENCE,
        castingTime=SpellCastingTime.ACTION,
        targeting=SpellTargeting(rangeType=SpellRangeType.TOUCH),
        duration=SpellDuration(unit=SpellDurationUnit.HOUR, amount=1),
        components=[SpellComponent.VERBAL, SpellComponent.MATERIAL],
        description="Make one touched object shed bright and dim light.",
    ),
    SpellId.MAGE_HAND: SpellEntry(
        id=SpellId.MAGE_HAND,
        name=SpellId.MAGE_HAND,
        source=SpellSource.WIZARD,
        level=0,
        school=SpellSchool.CONJURATION,
        castingAbility=AbilityType.INTELLIGENCE,
        castingTime=SpellCastingTime.ACTION,
        targeting=SpellTargeting(rangeType=SpellRangeType.DISTANCE, distanceFeet=30),
        duration=SpellDuration(unit=SpellDurationUnit.MINUTE, amount=1),
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
        description="Create a spectral hand that can manipulate objects.",
    ),
    SpellId.MINOR_ILLUSION: SpellEntry(
        id=SpellId.MINOR_ILLUSION,
        name=SpellId.MINOR_ILLUSION,
        source=SpellSource.WIZARD,
        level=0,
        school=SpellSchool.ILLUSION,
        castingAbility=AbilityType.INTELLIGENCE,
        castingTime=SpellCastingTime.ACTION,
        targeting=SpellTargeting(rangeType=SpellRangeType.DISTANCE, distanceFeet=30),
        duration=SpellDuration(unit=SpellDurationUnit.MINUTE, amount=1),
        components=[SpellComponent.SOMATIC, SpellComponent.MATERIAL],
        description="Create a sound or image illusion.",
    ),
    SpellId.PRESTIDIGITATION: SpellEntry(
        id=SpellId.PRESTIDIGITATION,
        name=SpellId.PRESTIDIGITATION,
        source=SpellSource.WIZARD,
        level=0,
        school=SpellSchool.TRANSMUTATION,
        castingAbility=AbilityType.INTELLIGENCE,
        castingTime=SpellCastingTime.ACTION,
        targeting=SpellTargeting(rangeType=SpellRangeType.DISTANCE, distanceFeet=10),
        duration=SpellDuration(unit=SpellDurationUnit.HOUR, amount=1, maximum=True),
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
        description="Perform a minor magical trick.",
    ),
    SpellId.RAY_OF_FROST: SpellEntry(
        id=SpellId.RAY_OF_FROST,
        name=SpellId.RAY_OF_FROST,
        source=SpellSource.WIZARD,
        level=0,
        school=SpellSchool.EVOCATION,
        castingAbility=AbilityType.INTELLIGENCE,
        castingTime=SpellCastingTime.ACTION,
        targeting=SpellTargeting(rangeType=SpellRangeType.DISTANCE, distanceFeet=60),
        duration=SpellDuration(unit=SpellDurationUnit.INSTANTANEOUS),
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
        description="Make a ranged spell attack that deals cold damage and slows the target.",
    ),
    SpellId.SHOCKING_GRASP: SpellEntry(
        id=SpellId.SHOCKING_GRASP,
        name=SpellId.SHOCKING_GRASP,
        source=SpellSource.WIZARD,
        level=0,
        school=SpellSchool.EVOCATION,
        castingAbility=AbilityType.INTELLIGENCE,
        castingTime=SpellCastingTime.ACTION,
        targeting=SpellTargeting(rangeType=SpellRangeType.TOUCH),
        duration=SpellDuration(unit=SpellDurationUnit.INSTANTANEOUS),
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
        description="Make a melee spell attack that deals lightning damage and can prevent reactions.",
    ),
    SpellId.ABSORB_ELEMENTS: SpellEntry(
        id=SpellId.ABSORB_ELEMENTS,
        name=SpellId.ABSORB_ELEMENTS,
        source=SpellSource.WIZARD,
        level=1,
        school=SpellSchool.ABJURATION,
        castingAbility=AbilityType.INTELLIGENCE,
        castingTime=SpellCastingTime.REACTION,
        targeting=SpellTargeting(rangeType=SpellRangeType.SELF),
        duration=SpellDuration(unit=SpellDurationUnit.ROUND, amount=1),
        components=[SpellComponent.SOMATIC],
        description="Gain resistance to incoming acid, cold, fire, lightning, or thunder damage and empower your next melee attack.",
    ),
    SpellId.BURNING_HANDS: SpellEntry(
        id=SpellId.BURNING_HANDS,
        name=SpellId.BURNING_HANDS,
        source=SpellSource.WIZARD,
        level=1,
        school=SpellSchool.EVOCATION,
        castingAbility=AbilityType.INTELLIGENCE,
        castingTime=SpellCastingTime.ACTION,
        targeting=SpellTargeting(rangeType=SpellRangeType.SELF, area=SpellConeArea(lengthFeet=15)),
        duration=SpellDuration(unit=SpellDurationUnit.INSTANTANEOUS),
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
        description="Creatures in a 15-foot cone make a Dexterity save or take fire damage.",
    ),
    SpellId.CHROMATIC_ORB: SpellEntry(
        id=SpellId.CHROMATIC_ORB,
        name=SpellId.CHROMATIC_ORB,
        source=SpellSource.WIZARD,
        level=1,
        school=SpellSchool.EVOCATION,
        castingAbility=AbilityType.INTELLIGENCE,
        castingTime=SpellCastingTime.ACTION,
        targeting=SpellTargeting(rangeType=SpellRangeType.DISTANCE, distanceFeet=90),
        duration=SpellDuration(unit=SpellDurationUnit.INSTANTANEOUS),
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
        description="Make a ranged spell attack that deals a chosen elemental damage type.",
    ),
    SpellId.FIND_FAMILIAR: SpellEntry(
        id=SpellId.FIND_FAMILIAR,
        name=SpellId.FIND_FAMILIAR,
        source=SpellSource.WIZARD,
        level=1,
        school=SpellSchool.CONJURATION,
        castingAbility=AbilityType.INTELLIGENCE,
        castingTime=SpellCastingTime.HOUR,
        targeting=SpellTargeting(rangeType=SpellRangeType.DISTANCE, distanceFeet=10),
        duration=SpellDuration(unit=SpellDurationUnit.INSTANTANEOUS),
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
        ritual=True,
        description="Gain the service of a familiar spirit in an animal form.",
    ),
    SpellId.MAGIC_MISSILE: SpellEntry(
        id=SpellId.MAGIC_MISSILE,
        name=SpellId.MAGIC_MISSILE,
        source=SpellSource.WIZARD,
        level=1,
        school=SpellSchool.EVOCATION,
        castingAbility=AbilityType.INTELLIGENCE,
        castingTime=SpellCastingTime.ACTION,
        targeting=SpellTargeting(rangeType=SpellRangeType.DISTANCE, distanceFeet=120),
        duration=SpellDuration(unit=SpellDurationUnit.INSTANTANEOUS),
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
        description="Create darts of magical force that hit automatically.",
    ),
    SpellId.PROTECTION_FROM_EVIL_AND_GOOD: SpellEntry(
        id=SpellId.PROTECTION_FROM_EVIL_AND_GOOD,
        name=SpellId.PROTECTION_FROM_EVIL_AND_GOOD,
        source=SpellSource.WIZARD,
        level=1,
        school=SpellSchool.ABJURATION,
        castingAbility=AbilityType.INTELLIGENCE,
        castingTime=SpellCastingTime.ACTION,
        targeting=SpellTargeting(rangeType=SpellRangeType.TOUCH),
        duration=SpellDuration(unit=SpellDurationUnit.MINUTE, amount=10, maximum=True),
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
        concentration=True,
        description="Protect a willing creature against several supernatural creature types.",
    ),
    SpellId.SHIELD: SpellEntry(
        id=SpellId.SHIELD,
        name=SpellId.SHIELD,
        source=SpellSource.WIZARD,
        level=1,
        school=SpellSchool.ABJURATION,
        castingAbility=AbilityType.INTELLIGENCE,
        castingTime=SpellCastingTime.REACTION,
        targeting=SpellTargeting(rangeType=SpellRangeType.SELF),
        duration=SpellDuration(unit=SpellDurationUnit.ROUND, amount=1),
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
        description="Gain +5 AC until the start of your next turn, including against the triggering attack.",
    ),
    SpellId.SLEEP: SpellEntry(
        id=SpellId.SLEEP,
        name=SpellId.SLEEP,
        source=SpellSource.WIZARD,
        level=1,
        school=SpellSchool.ENCHANTMENT,
        castingAbility=AbilityType.INTELLIGENCE,
        castingTime=SpellCastingTime.ACTION,
        targeting=SpellTargeting(rangeType=SpellRangeType.DISTANCE, distanceFeet=90, area=SpellRadiusArea(radiusFeet=20)),
        duration=SpellDuration(unit=SpellDurationUnit.MINUTE, amount=1),
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
        description="Magically send creatures into slumber, starting with the lowest current hit points.",
    ),
    SpellId.THUNDERWAVE: SpellEntry(
        id=SpellId.THUNDERWAVE,
        name=SpellId.THUNDERWAVE,
        source=SpellSource.WIZARD,
        level=1,
        school=SpellSchool.EVOCATION,
        castingAbility=AbilityType.INTELLIGENCE,
        castingTime=SpellCastingTime.ACTION,
        targeting=SpellTargeting(rangeType=SpellRangeType.SELF, area=SpellCubeArea(sizeFeet=15)),
        duration=SpellDuration(unit=SpellDurationUnit.INSTANTANEOUS),
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
        description="Creatures in a 15-foot cube make a Constitution save or take thunder damage and are pushed.",
    ),
    SpellId.WARDING_WIND: SpellEntry(
        id=SpellId.WARDING_WIND,
        name=SpellId.WARDING_WIND,
        source=SpellSource.WIZARD,
        level=2,
        school=SpellSchool.EVOCATION,
        castingAbility=AbilityType.INTELLIGENCE,
        castingTime=SpellCastingTime.ACTION,
        targeting=SpellTargeting(rangeType=SpellRangeType.SELF, area=SpellRadiusArea(radiusFeet=10)),
        duration=SpellDuration(unit=SpellDurationUnit.MINUTE, amount=10, maximum=True),
        components=[SpellComponent.VERBAL],
        concentration=True,
        description="A strong wind surrounds you, deafening the area and hindering ranged attacks and movement.",
    ),
    SpellId.SCORCHING_RAY: SpellEntry(
        id=SpellId.SCORCHING_RAY,
        name=SpellId.SCORCHING_RAY,
        source=SpellSource.WIZARD,
        level=2,
        school=SpellSchool.EVOCATION,
        castingAbility=AbilityType.INTELLIGENCE,
        castingTime=SpellCastingTime.ACTION,
        targeting=SpellTargeting(rangeType=SpellRangeType.DISTANCE, distanceFeet=120),
        duration=SpellDuration(unit=SpellDurationUnit.INSTANTANEOUS),
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
        description="Make three ranged spell attacks that deal fire damage.",
    ),
    SpellId.SHATTER: SpellEntry(
        id=SpellId.SHATTER,
        name=SpellId.SHATTER,
        source=SpellSource.WIZARD,
        level=2,
        school=SpellSchool.EVOCATION,
        castingAbility=AbilityType.INTELLIGENCE,
        castingTime=SpellCastingTime.ACTION,
        targeting=SpellTargeting(rangeType=SpellRangeType.DISTANCE, distanceFeet=60, area=SpellRadiusArea(radiusFeet=10)),
        duration=SpellDuration(unit=SpellDurationUnit.INSTANTANEOUS),
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
        description="Creatures in a 10-foot-radius sphere make a Constitution save or take thunder damage.",
    ),
    SpellId.COUNTERSPELL: SpellEntry(
        id=SpellId.COUNTERSPELL,
        name=SpellId.COUNTERSPELL,
        source=SpellSource.WIZARD,
        level=3,
        school=SpellSchool.ABJURATION,
        castingAbility=AbilityType.INTELLIGENCE,
        castingTime=SpellCastingTime.REACTION,
        targeting=SpellTargeting(rangeType=SpellRangeType.DISTANCE, distanceFeet=60),
        duration=SpellDuration(unit=SpellDurationUnit.INSTANTANEOUS),
        components=[SpellComponent.SOMATIC],
        description="Interrupt a creature casting a spell.",
    ),
    SpellId.FIREBALL: SpellEntry(
        id=SpellId.FIREBALL,
        name=SpellId.FIREBALL,
        source=SpellSource.WIZARD,
        level=3,
        school=SpellSchool.EVOCATION,
        castingAbility=AbilityType.INTELLIGENCE,
        castingTime=SpellCastingTime.ACTION,
        targeting=SpellTargeting(rangeType=SpellRangeType.DISTANCE, distanceFeet=150, area=SpellRadiusArea(radiusFeet=20)),
        duration=SpellDuration(unit=SpellDurationUnit.INSTANTANEOUS),
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
        description="Creatures in a 20-foot-radius sphere make a Dexterity save or take fire damage.",
    ),
    SpellId.LIGHTNING_BOLT: SpellEntry(
        id=SpellId.LIGHTNING_BOLT,
        name=SpellId.LIGHTNING_BOLT,
        source=SpellSource.WIZARD,
        level=3,
        school=SpellSchool.EVOCATION,
        castingAbility=AbilityType.INTELLIGENCE,
        castingTime=SpellCastingTime.ACTION,
        targeting=SpellTargeting(rangeType=SpellRangeType.SELF, area=SpellLineArea(lengthFeet=100, widthFeet=5)),
        duration=SpellDuration(unit=SpellDurationUnit.INSTANTANEOUS),
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
        description="Creatures in a 100-foot line make a Dexterity save or take lightning damage.",
    ),
    SpellId.FIRE_SHIELD: SpellEntry(
        id=SpellId.FIRE_SHIELD,
        name=SpellId.FIRE_SHIELD,
        source=SpellSource.WIZARD,
        level=4,
        school=SpellSchool.EVOCATION,
        castingAbility=AbilityType.INTELLIGENCE,
        castingTime=SpellCastingTime.ACTION,
        targeting=SpellTargeting(rangeType=SpellRangeType.SELF),
        duration=SpellDuration(unit=SpellDurationUnit.MINUTE, amount=10),
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
        description="Gain resistance and damage attackers with flame or chill energy.",
    ),
    SpellId.ICE_STORM: SpellEntry(
        id=SpellId.ICE_STORM,
        name=SpellId.ICE_STORM,
        source=SpellSource.WIZARD,
        level=4,
        school=SpellSchool.EVOCATION,
        castingAbility=AbilityType.INTELLIGENCE,
        castingTime=SpellCastingTime.ACTION,
        targeting=SpellTargeting(rangeType=SpellRangeType.DISTANCE, distanceFeet=300, area=SpellCylinderArea(radiusFeet=20, heightFeet=40)),
        duration=SpellDuration(unit=SpellDurationUnit.INSTANTANEOUS),
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
        description="Creatures in a cylinder make a Dexterity save or take bludgeoning and cold damage.",
    ),
}


SUBCLASS_FEATURES: tuple[SubclassFeatureProgression, ...] = (
    SubclassFeatureProgression(
        subclass=FighterSubclassType.CHAMPION,
        featureType=ChampionFeatureType.IMPROVED_CRITICAL,
        minimum_level=3,
        activation=TimeEconomy.PASSIVE,
        description="Weapon and Unarmed Strike attacks score a Critical Hit on a d20 roll of 19 or 20.",
    ),
    SubclassFeatureProgression(
        subclass=FighterSubclassType.CHAMPION,
        featureType=ChampionFeatureType.REMARKABLE_ATHLETE,
        minimum_level=3,
        activation=TimeEconomy.PASSIVE,
        description="Advantage on Initiative rolls and Strength (Athletics) checks; after scoring a Critical Hit, move up to half Speed without provoking Opportunity Attacks.",
    ),
    SubclassFeatureProgression(
        subclass=FighterSubclassType.CHAMPION,
        featureType=ChampionFeatureType.ADDITIONAL_FIGHTING_STYLE,
        minimum_level=7,
        activation=TimeEconomy.PASSIVE,
        description="Gain another Fighting Style feat.",
    ),
    SubclassFeatureProgression(
        subclass=FighterSubclassType.CHAMPION,
        featureType=ChampionFeatureType.HEROIC_WARRIOR,
        minimum_level=10,
        activation=TimeEconomy.PASSIVE,
        description="During combat, gain Heroic Inspiration when starting your turn without it.",
    ),
    SubclassFeatureProgression(
        subclass=FighterSubclassType.CHAMPION,
        featureType=ChampionFeatureType.SUPERIOR_CRITICAL,
        minimum_level=15,
        activation=TimeEconomy.PASSIVE,
        description="Weapon and Unarmed Strike attacks score a Critical Hit on a d20 roll of 18-20.",
    ),
    SubclassFeatureProgression(
        subclass=FighterSubclassType.CHAMPION,
        featureType=ChampionFeatureType.SURVIVOR,
        minimum_level=18,
        activation=TimeEconomy.PASSIVE,
        description="Gain death save resilience and regain hit points at the start of your turn while Bloodied and above 0 HP.",
    ),
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
        conditionEffects=(
            ConditionEffect(
                condition=ConditionType.PRONE,
                mode=ConditionApplicationMode.TARGET_SAVE,
                savingThrow=AbilityType.STRENGTH,
                saveDcAbility=AbilityType.STRENGTH,
                description="After you move 10 feet straight and hit, the target falls prone on a failed Strength save.",
            ),
        ),
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
    SubclassFeatureProgression(
        subclass=FighterSubclassType.MONSTER_HUNTER,
        featureType=MonsterHunterFeatureType.BONUS_PROFICIENCIES,
        minimum_level=3,
        activation=TimeEconomy.PASSIVE,
        description="Gain proficiency in two of Arcana, History, Insight, Investigation, Nature, or Perception. A tool proficiency can replace one skill choice.",
    ),
    SubclassFeatureProgression(
        subclass=FighterSubclassType.MONSTER_HUNTER,
        featureType=MonsterHunterFeatureType.COMBAT_SUPERIORITY,
        minimum_level=3,
        activation=TimeEconomy.SPECIAL,
        description="Gain Monster Hunter superiority dice for Hunter's Damage, Hunter's Will, and Hunter's Eye. Superiority dice are tracked as a resource.",
    ),
    SubclassFeatureProgression(
        subclass=FighterSubclassType.MONSTER_HUNTER,
        featureType=MonsterHunterFeatureType.HUNTERS_MYSTICISM,
        minimum_level=3,
        activation=TimeEconomy.SPECIAL,
        description="Cast Detect Magic as a ritual and Protection from Evil and Good once per long rest. Wisdom is your spellcasting ability for these spells. Also learn Abyssal, Celestial, or Infernal.",
    ),
    SubclassFeatureProgression(
        subclass=FighterSubclassType.MONSTER_HUNTER,
        featureType=MonsterHunterFeatureType.MONSTER_SLAYER,
        minimum_level=7,
        activation=TimeEconomy.SPECIAL,
        description="When you expend superiority dice for damage, you can expend up to two dice. Against aberrations, fey, fiends, or undead, those dice deal maximum damage.",
    ),
    SubclassFeatureProgression(
        subclass=FighterSubclassType.MONSTER_HUNTER,
        featureType=MonsterHunterFeatureType.IMPROVED_COMBAT_SUPERIORITY,
        minimum_level=10,
        activation=TimeEconomy.PASSIVE,
        description="Your Monster Hunter superiority dice become d10s at Fighter level 10 and d12s at Fighter level 18.",
    ),
    SubclassFeatureProgression(
        subclass=FighterSubclassType.MONSTER_HUNTER,
        featureType=MonsterHunterFeatureType.RELENTLESS,
        minimum_level=15,
        activation=TimeEconomy.SPECIAL,
        description="When you roll Initiative and have no superiority dice remaining, regain 1 superiority die.",
    ),
    SubclassFeatureProgression(
        subclass=FighterSubclassType.ARCANE_ARCHER,
        featureType=ArcaneArcherFeatureType.ARCANE_ARCHER_LORE,
        minimum_level=3,
        activation=TimeEconomy.PASSIVE,
        description="Gain Arcana or Nature proficiency and learn either Prestidigitation or Druidcraft.",
    ),
    SubclassFeatureProgression(
        subclass=FighterSubclassType.ARCANE_ARCHER,
        featureType=ArcaneArcherFeatureType.ARCANE_SHOT,
        minimum_level=3,
        activation=TimeEconomy.SPECIAL,
        description="Apply an Arcane Shot option to a shortbow or longbow arrow. Save DC is 8 + Proficiency Bonus + Intelligence modifier.",
    ),
    SubclassFeatureProgression(
        subclass=FighterSubclassType.ARCANE_ARCHER,
        featureType=ArcaneArcherFeatureType.MAGIC_ARROW,
        minimum_level=7,
        activation=TimeEconomy.PASSIVE,
        description="Nonmagical shortbow and longbow arrows count as magical for overcoming resistance and immunity.",
    ),
    SubclassFeatureProgression(
        subclass=FighterSubclassType.ARCANE_ARCHER,
        featureType=ArcaneArcherFeatureType.CURVING_SHOT,
        minimum_level=7,
        activation=TimeEconomy.BONUS_ACTION,
        description="When you miss with a magic arrow, reroll the attack against a different target within 60 feet of the original target.",
    ),
    SubclassFeatureProgression(
        subclass=FighterSubclassType.ARCANE_ARCHER,
        featureType=ArcaneArcherFeatureType.EVER_READY_SHOT,
        minimum_level=15,
        activation=TimeEconomy.SPECIAL,
        description="When you roll Initiative and have no Arcane Shot uses remaining, regain 1 use.",
    ),
    SubclassFeatureProgression(
        subclass=FighterSubclassType.RUNE_KNIGHT,
        featureType=RuneKnightFeatureType.BONUS_PROFICIENCIES,
        minimum_level=3,
        activation=TimeEconomy.PASSIVE,
        description="Gain smith's tools proficiency and learn Giant.",
    ),
    SubclassFeatureProgression(
        subclass=FighterSubclassType.RUNE_KNIGHT,
        featureType=RuneKnightFeatureType.RUNE_CARVER,
        minimum_level=3,
        activation=TimeEconomy.SPECIAL,
        description="Inscribe known runes on eligible objects after a long rest. Rune Magic save DC is 8 + Proficiency Bonus + Constitution modifier.",
    ),
    SubclassFeatureProgression(
        subclass=FighterSubclassType.RUNE_KNIGHT,
        featureType=RuneKnightFeatureType.GIANTS_MIGHT,
        minimum_level=3,
        activation=TimeEconomy.BONUS_ACTION,
        description="Become Large if possible for 1 minute, gain Advantage on Strength checks and saves, and add extra weapon or unarmed strike damage once on each turn.",
    ),
    SubclassFeatureProgression(
        subclass=FighterSubclassType.RUNE_KNIGHT,
        featureType=RuneKnightFeatureType.RUNIC_SHIELD,
        minimum_level=7,
        activation=TimeEconomy.REACTION,
        description="When another creature within 60 feet is hit by an attack roll, force the attacker to reroll the d20 and use the new roll.",
    ),
    SubclassFeatureProgression(
        subclass=FighterSubclassType.RUNE_KNIGHT,
        featureType=RuneKnightFeatureType.GREAT_STATURE,
        minimum_level=10,
        activation=TimeEconomy.PASSIVE,
        description="Grow 3d4 inches, and Giant's Might extra damage becomes 1d8.",
    ),
    SubclassFeatureProgression(
        subclass=FighterSubclassType.RUNE_KNIGHT,
        featureType=RuneKnightFeatureType.MASTER_OF_RUNES,
        minimum_level=15,
        activation=TimeEconomy.PASSIVE,
        description="Invoke each known rune twice between rests instead of once.",
    ),
    SubclassFeatureProgression(
        subclass=FighterSubclassType.RUNE_KNIGHT,
        featureType=RuneKnightFeatureType.RUNIC_JUGGERNAUT,
        minimum_level=18,
        activation=TimeEconomy.PASSIVE,
        description="Giant's Might extra damage becomes 1d10; you can become Huge and gain 5 feet of reach while Huge.",
    ),
    SubclassFeatureProgression(
        subclass=FighterSubclassType.ECHO_KNIGHT,
        featureType=EchoKnightFeatureType.MANIFEST_ECHO,
        minimum_level=3,
        activation=TimeEconomy.BONUS_ACTION,
        description="Manifest a magical echo in an unoccupied space within 15 feet. It has AC 14 + Proficiency Bonus, 1 HP, and can move up to 30 feet on your turn.",
    ),
    SubclassFeatureProgression(
        subclass=FighterSubclassType.ECHO_KNIGHT,
        featureType=EchoKnightFeatureType.UNLEASH_INCARNATION,
        minimum_level=3,
        activation=TimeEconomy.SPECIAL,
        description="When you take the Attack action, make one additional melee attack from the echo's position.",
    ),
    SubclassFeatureProgression(
        subclass=FighterSubclassType.ECHO_KNIGHT,
        featureType=EchoKnightFeatureType.ECHO_AVATAR,
        minimum_level=7,
        activation=TimeEconomy.ACTION,
        description="See and hear through your echo for up to 10 minutes while you are deafened and blinded; during this use, the echo can be up to 1,000 feet away.",
        conditionEffects=(
            ConditionEffect(
                condition=ConditionType.DEAFENED,
                mode=ConditionApplicationMode.MANUAL,
                description="While seeing and hearing through your echo, you are deafened to your own senses.",
            ),
            ConditionEffect(
                condition=ConditionType.BLINDED,
                mode=ConditionApplicationMode.MANUAL,
                description="While seeing and hearing through your echo, you are blinded to your own senses.",
            ),
        ),
    ),
    SubclassFeatureProgression(
        subclass=FighterSubclassType.ECHO_KNIGHT,
        featureType=EchoKnightFeatureType.SHADOW_MARTYR,
        minimum_level=10,
        activation=TimeEconomy.REACTION,
        description="Before an attack roll against another creature, teleport your echo near the target and have the attack target the echo instead.",
    ),
    SubclassFeatureProgression(
        subclass=FighterSubclassType.ECHO_KNIGHT,
        featureType=EchoKnightFeatureType.RECLAIM_POTENTIAL,
        minimum_level=15,
        activation=TimeEconomy.SPECIAL,
        description="When your echo is destroyed by damage and you have no temporary HP, gain 2d6 + Constitution modifier temporary hit points.",
    ),
    SubclassFeatureProgression(
        subclass=FighterSubclassType.ECHO_KNIGHT,
        featureType=EchoKnightFeatureType.LEGION_OF_ONE,
        minimum_level=18,
        activation=TimeEconomy.BONUS_ACTION,
        description="Manifest two echoes at once, and regain 1 Unleash Incarnation use when rolling Initiative with none remaining.",
    ),
    SubclassFeatureProgression(
        subclass=FighterSubclassType.PSI_WARRIOR,
        featureType=PsiWarriorFeatureType.PSIONIC_POWER,
        minimum_level=3,
        activation=TimeEconomy.SPECIAL,
        description="Use Psionic Energy dice for Protective Field, Psionic Strike, and Telekinetic Movement. Save DC is 8 + Proficiency Bonus + Intelligence modifier.",
    ),
    SubclassFeatureProgression(
        subclass=FighterSubclassType.PSI_WARRIOR,
        featureType=PsiWarriorFeatureType.TELEKINETIC_ADEPT,
        minimum_level=7,
        activation=TimeEconomy.SPECIAL,
        description="Gain Psi-Powered Leap and Telekinetic Thrust. Telekinetic Thrust can knock a Psionic Strike target prone or move it on a failed Strength save.",
        conditionEffects=(
            ConditionEffect(
                condition=ConditionType.PRONE,
                mode=ConditionApplicationMode.TARGET_SAVE,
                savingThrow=AbilityType.STRENGTH,
                saveDcAbility=AbilityType.INTELLIGENCE,
                description="After Psionic Strike deals damage, Telekinetic Thrust can knock the target prone on a failed Strength save.",
            ),
        ),
    ),
    SubclassFeatureProgression(
        subclass=FighterSubclassType.PSI_WARRIOR,
        featureType=PsiWarriorFeatureType.GUARDED_MIND,
        minimum_level=10,
        activation=TimeEconomy.SPECIAL,
        description="Gain resistance to psychic damage, and expend one Psionic Energy die to end charm or frighten effects on yourself at the start of your turn.",
    ),
    SubclassFeatureProgression(
        subclass=FighterSubclassType.PSI_WARRIOR,
        featureType=PsiWarriorFeatureType.BULWARK_OF_FORCE,
        minimum_level=15,
        activation=TimeEconomy.BONUS_ACTION,
        description="Protect visible creatures within 30 feet, up to Intelligence modifier minimum one, with half cover for 1 minute.",
    ),
    SubclassFeatureProgression(
        subclass=FighterSubclassType.PSI_WARRIOR,
        featureType=PsiWarriorFeatureType.TELEKINETIC_MASTER,
        minimum_level=18,
        activation=TimeEconomy.ACTION,
        description="Cast Telekinesis without components using Intelligence as your spellcasting ability, and make one weapon attack as a Bonus Action on each turn while concentrating.",
    ),
    SubclassFeatureProgression(
        subclass=FighterSubclassType.ELDRITCH_KNIGHT,
        featureType=EldritchKnightFeatureType.SPELLCASTING,
        minimum_level=3,
        activation=TimeEconomy.SPECIAL,
        description="Cast wizard spells using Intelligence. Spell save DC is 8 + Proficiency Bonus + Intelligence modifier; spell attack modifier is Proficiency Bonus + Intelligence modifier. Most spells known must be abjuration or evocation, except the flexible choices gained at Fighter levels 3, 8, 14, and 20.",
    ),
    SubclassFeatureProgression(
        subclass=FighterSubclassType.ELDRITCH_KNIGHT,
        featureType=EldritchKnightFeatureType.WEAPON_BOND,
        minimum_level=3,
        activation=TimeEconomy.BONUS_ACTION,
        description="Bond with up to two weapons by ritual. You cannot be disarmed of a bonded weapon while conscious, and can summon one bonded weapon to your hand as a Bonus Action if it is on the same plane.",
    ),
    SubclassFeatureProgression(
        subclass=FighterSubclassType.ELDRITCH_KNIGHT,
        featureType=EldritchKnightFeatureType.WAR_MAGIC,
        minimum_level=7,
        activation=TimeEconomy.BONUS_ACTION,
        description="When you use your Action to cast a cantrip, make one weapon attack as a Bonus Action.",
    ),
    SubclassFeatureProgression(
        subclass=FighterSubclassType.ELDRITCH_KNIGHT,
        featureType=EldritchKnightFeatureType.ELDRITCH_STRIKE,
        minimum_level=10,
        activation=TimeEconomy.SPECIAL,
        description="When you hit a creature with a weapon attack, it has Disadvantage on the next saving throw it makes against a spell you cast before the end of your next turn.",
    ),
    SubclassFeatureProgression(
        subclass=FighterSubclassType.ELDRITCH_KNIGHT,
        featureType=EldritchKnightFeatureType.ARCANE_CHARGE,
        minimum_level=15,
        activation=TimeEconomy.SPECIAL,
        description="When you use Action Surge, teleport up to 30 feet to an unoccupied space you can see before or after the additional action.",
    ),
    SubclassFeatureProgression(
        subclass=FighterSubclassType.ELDRITCH_KNIGHT,
        featureType=EldritchKnightFeatureType.IMPROVED_WAR_MAGIC,
        minimum_level=18,
        activation=TimeEconomy.BONUS_ACTION,
        description="When you use your Action to cast a spell, make one weapon attack as a Bonus Action.",
    ),
)


def fighter_subclass_features(subclass: FighterSubclassType | None, fighter_level_value: int) -> list[SheetFeature]:
    if subclass is None:
        return []
    if subclass == FighterSubclassType.BATTLE_MASTER:
        return battle_master_features(subclass_character_class(subclass, fighter_level_value), fighter_level_value)
    return [
        subclass_feature(progression, fighter_level_value)
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
    if subclass == FighterSubclassType.ELDRITCH_KNIGHT and fighter_level_value >= 3:
        progression = eldritch_knight_spellcasting(fighter_level_value)
        for resource_type, slot_level, max_uses in eldritch_knight_spell_slot_resources(progression):
            resources.append(
                ResourceTracker(
                    id=enum_key(resource_type),
                    name=enum_label(resource_type),
                    currentUses=max_uses,
                    maxUses=max_uses,
                    reset=RestType.LONG_REST,
                    activation=TimeEconomy.ACTION,
                    description=f"Spend to cast an Eldritch Knight spell using a level {slot_level} spell slot.",
                    source=enum_label(FighterSubclassType.ELDRITCH_KNIGHT),
                )
            )
    if subclass == FighterSubclassType.ARCANE_ARCHER and fighter_level_value >= 3:
        resources.append(
            ResourceTracker(
                id=enum_key(FighterSubclassResourceType.ARCANE_SHOT),
                name=enum_label(FighterSubclassResourceType.ARCANE_SHOT),
                currentUses=2,
                maxUses=2,
                reset=RestType.SHORT_REST,
                activation=TimeEconomy.SPECIAL,
                description="Spend a use to apply one Arcane Shot option to a shortbow or longbow arrow.",
                source=enum_label(FighterSubclassType.ARCANE_ARCHER),
            )
        )
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
    if subclass == FighterSubclassType.MONSTER_HUNTER and fighter_level_value >= 3:
        resources.append(
            ResourceTracker(
                id=enum_key(FighterSubclassResourceType.PROTECTION_FROM_EVIL_AND_GOOD),
                name=enum_label(FighterSubclassResourceType.PROTECTION_FROM_EVIL_AND_GOOD),
                currentUses=1,
                maxUses=1,
                reset=RestType.LONG_REST,
                activation=TimeEconomy.ACTION,
                description="Cast Protection from Evil and Good with Wisdom as your spellcasting ability.",
                source=enum_label(FighterSubclassType.MONSTER_HUNTER),
            )
        )
    if subclass == FighterSubclassType.RUNE_KNIGHT and fighter_level_value >= 3:
        resources.append(
            ResourceTracker(
                id=enum_key(FighterSubclassResourceType.GIANTS_MIGHT),
                name=enum_label(FighterSubclassResourceType.GIANTS_MIGHT),
                currentUses=proficiency_bonus_for_level(fighter_level_value),
                maxUses=proficiency_bonus_for_level(fighter_level_value),
                reset=RestType.LONG_REST,
                activation=TimeEconomy.BONUS_ACTION,
                description="Become Large if possible and gain Giant's Might benefits for 1 minute.",
                source=enum_label(FighterSubclassType.RUNE_KNIGHT),
            )
        )
        for rune in selected_runes(character_class, fighter_level_value):
            resources.append(
                ResourceTracker(
                    id=enum_key(rune),
                    name=enum_label(rune),
                    currentUses=rune_uses(fighter_level_value),
                    maxUses=rune_uses(fighter_level_value),
                    reset=RestType.SHORT_REST,
                    activation=rune_activation(rune),
                    description=rune_resource_description(rune),
                    source=enum_label(FighterSubclassType.RUNE_KNIGHT),
                )
            )
    if subclass == FighterSubclassType.RUNE_KNIGHT and fighter_level_value >= 7:
        resources.append(
            ResourceTracker(
                id=enum_key(FighterSubclassResourceType.RUNIC_SHIELD),
                name=enum_label(FighterSubclassResourceType.RUNIC_SHIELD),
                currentUses=proficiency_bonus_for_level(fighter_level_value),
                maxUses=proficiency_bonus_for_level(fighter_level_value),
                reset=RestType.LONG_REST,
                activation=TimeEconomy.REACTION,
                description="Force an attacker to reroll a hit against another creature within 60 feet.",
                source=enum_label(FighterSubclassType.RUNE_KNIGHT),
            )
        )
    if subclass == FighterSubclassType.ECHO_KNIGHT and fighter_level_value >= 3:
        uses = max(1, ability_modifier(ability_scores.constitution if ability_scores else 10))
        resources.append(
            ResourceTracker(
                id=enum_key(FighterSubclassResourceType.UNLEASH_INCARNATION),
                name=enum_label(FighterSubclassResourceType.UNLEASH_INCARNATION),
                currentUses=uses,
                maxUses=uses,
                reset=RestType.LONG_REST,
                activation=TimeEconomy.SPECIAL,
                description="Make one additional melee attack from your echo's position when you take the Attack action.",
                source=enum_label(FighterSubclassType.ECHO_KNIGHT),
            )
        )
    if subclass == FighterSubclassType.ECHO_KNIGHT and fighter_level_value >= 10:
        resources.append(
            ResourceTracker(
                id=enum_key(FighterSubclassResourceType.SHADOW_MARTYR),
                name=enum_label(FighterSubclassResourceType.SHADOW_MARTYR),
                currentUses=1,
                maxUses=1,
                reset=RestType.SHORT_REST,
                activation=TimeEconomy.REACTION,
                description="Redirect an attack against another creature to your echo.",
                source=enum_label(FighterSubclassType.ECHO_KNIGHT),
            )
        )
    if subclass == FighterSubclassType.ECHO_KNIGHT and fighter_level_value >= 15:
        uses = max(1, ability_modifier(ability_scores.constitution if ability_scores else 10))
        resources.append(
            ResourceTracker(
                id=enum_key(FighterSubclassResourceType.RECLAIM_POTENTIAL),
                name=enum_label(FighterSubclassResourceType.RECLAIM_POTENTIAL),
                currentUses=uses,
                maxUses=uses,
                reset=RestType.LONG_REST,
                activation=TimeEconomy.SPECIAL,
                description="Gain 2d6 + Constitution modifier temporary hit points when your echo is destroyed by damage.",
                rollActions=[
                    RollAction(
                        id=FighterSubclassRollActionType.RECLAIM_POTENTIAL,
                        name=FighterSubclassRollActionType.RECLAIM_POTENTIAL,
                        diceCount=2,
                        diceType=DiceType.D6,
                        staticModifier=ability_modifier(ability_scores.constitution if ability_scores else 10),
                        resolution=RollResolutionMode.APPLY_TEMPORARY_HIT_POINTS,
                        consumesResource=FighterSubclassResourceType.RECLAIM_POTENTIAL,
                        source=enum_label(FighterSubclassType.ECHO_KNIGHT),
                    )
                ],
                source=enum_label(FighterSubclassType.ECHO_KNIGHT),
            )
        )
    if subclass == FighterSubclassType.PSI_WARRIOR and fighter_level_value >= 3:
        psi_die = psionic_energy_die(fighter_level_value)
        intelligence_modifier = ability_modifier(ability_scores.intelligence if ability_scores else 10)
        resources.append(
            ResourceTracker(
                id=enum_key(FighterSubclassResourceType.PSIONIC_ENERGY_DICE),
                name=enum_label(FighterSubclassResourceType.PSIONIC_ENERGY_DICE),
                currentUses=2 * proficiency_bonus_for_level(fighter_level_value),
                maxUses=2 * proficiency_bonus_for_level(fighter_level_value),
                reset=RestType.LONG_REST,
                activation=TimeEconomy.SPECIAL,
                description=f"Spend Psionic Energy dice ({enum_key(psi_die)}) to fuel Psi Warrior powers.",
                rollActions=[
                    RollAction(
                        id=FighterSubclassRollActionType.PROTECTIVE_FIELD,
                        name=FighterSubclassRollActionType.PROTECTIVE_FIELD,
                        diceCount=1,
                        diceType=psi_die,
                        staticModifier=intelligence_modifier,
                        consumesResource=FighterSubclassResourceType.PSIONIC_ENERGY_DICE,
                        activation=TimeEconomy.REACTION,
                        source=enum_label(FighterSubclassType.PSI_WARRIOR),
                    ),
                    RollAction(
                        id=FighterSubclassRollActionType.PSIONIC_STRIKE,
                        name=FighterSubclassRollActionType.PSIONIC_STRIKE,
                        diceCount=1,
                        diceType=psi_die,
                        staticModifier=intelligence_modifier,
                        consumesResource=FighterSubclassResourceType.PSIONIC_ENERGY_DICE,
                        activation=TimeEconomy.SPECIAL,
                        source=enum_label(FighterSubclassType.PSI_WARRIOR),
                        resolution=RollResolutionMode.APPLY_DAMAGE,
                        damageType=DamageType.FORCE,
                        conditionEffects=psionic_strike_condition_effects(fighter_level_value),
                    ),
                ],
                source=enum_label(FighterSubclassType.PSI_WARRIOR),
            )
        )
        resources.extend(
            [
                ResourceTracker(
                    id=enum_key(FighterSubclassResourceType.PSIONIC_ENERGY_RECOVERY),
                    name=enum_label(FighterSubclassResourceType.PSIONIC_ENERGY_RECOVERY),
                    currentUses=1,
                    maxUses=1,
                    reset=RestType.SHORT_REST,
                    activation=TimeEconomy.BONUS_ACTION,
                    description="Regain one expended Psionic Energy die.",
                    source=enum_label(FighterSubclassType.PSI_WARRIOR),
                ),
                ResourceTracker(
                    id=enum_key(FighterSubclassResourceType.TELEKINETIC_MOVEMENT),
                    name=enum_label(FighterSubclassResourceType.TELEKINETIC_MOVEMENT),
                    currentUses=1,
                    maxUses=1,
                    reset=RestType.SHORT_REST,
                    activation=TimeEconomy.ACTION,
                    description="Move a willing creature or loose object within 30 feet. Spend a Psionic Energy die to use again.",
                    source=enum_label(FighterSubclassType.PSI_WARRIOR),
                ),
            ]
        )
    if subclass == FighterSubclassType.PSI_WARRIOR and fighter_level_value >= 7:
        resources.append(
            ResourceTracker(
                id=enum_key(FighterSubclassResourceType.PSI_POWERED_LEAP),
                name=enum_label(FighterSubclassResourceType.PSI_POWERED_LEAP),
                currentUses=1,
                maxUses=1,
                reset=RestType.SHORT_REST,
                activation=TimeEconomy.BONUS_ACTION,
                description="Gain a flying speed equal to twice your walking speed until the end of the turn. Spend a Psionic Energy die to use again.",
                source=enum_label(FighterSubclassType.PSI_WARRIOR),
            )
        )
    if subclass == FighterSubclassType.PSI_WARRIOR and fighter_level_value >= 15:
        resources.append(
            ResourceTracker(
                id=enum_key(FighterSubclassResourceType.BULWARK_OF_FORCE),
                name=enum_label(FighterSubclassResourceType.BULWARK_OF_FORCE),
                currentUses=1,
                maxUses=1,
                reset=RestType.LONG_REST,
                activation=TimeEconomy.BONUS_ACTION,
                description="Grant half cover for 1 minute to visible creatures within 30 feet, up to Intelligence modifier minimum one. Spend a Psionic Energy die to use again.",
                source=enum_label(FighterSubclassType.PSI_WARRIOR),
            )
        )
    if subclass == FighterSubclassType.PSI_WARRIOR and fighter_level_value >= 18:
        resources.append(
            ResourceTracker(
                id=enum_key(FighterSubclassResourceType.TELEKINETIC_MASTER),
                name=enum_label(FighterSubclassResourceType.TELEKINETIC_MASTER),
                currentUses=1,
                maxUses=1,
                reset=RestType.LONG_REST,
                activation=TimeEconomy.ACTION,
                description="Cast Telekinesis without components. Spend a Psionic Energy die to use again.",
                source=enum_label(FighterSubclassType.PSI_WARRIOR),
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
    if subclass == FighterSubclassType.ELDRITCH_KNIGHT and fighter_level_value >= 3:
        progression = eldritch_knight_spellcasting(fighter_level_value)
        for resource_type, slot_level, _max_uses in eldritch_knight_spell_slot_resources(progression):
            abilities.append(
                resource_ability(
                    resource_type,
                    FighterSubclassType.ELDRITCH_KNIGHT,
                    TimeEconomy.ACTION,
                    f"Track level {slot_level} Eldritch Knight spell slots. Regain expended slots on a long rest.",
                )
            )
    if subclass == FighterSubclassType.ARCANE_ARCHER and fighter_level_value >= 3:
        for arcane_shot in selected_arcane_shots(character_class):
            abilities.append(
                SheetAbility(
                    id=enum_key(arcane_shot),
                    name=enum_label(arcane_shot),
                    source=enum_label(FighterSubclassType.ARCANE_ARCHER),
                    activation=TimeEconomy.SPECIAL,
                    description=arcane_shot_description(arcane_shot, fighter_level_value),
                    resourceId=enum_key(FighterSubclassResourceType.ARCANE_SHOT),
                    rollActions=arcane_shot_roll_actions(arcane_shot, fighter_level_value),
                )
            )
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
                            resolution=RollResolutionMode.APPLY_DAMAGE,
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
    if subclass == FighterSubclassType.RUNE_KNIGHT and fighter_level_value >= 3:
        giant_die = giants_might_die(fighter_level_value)
        abilities.append(
            SheetAbility(
                id=enum_key(FighterSubclassResourceType.GIANTS_MIGHT),
                name=enum_label(FighterSubclassResourceType.GIANTS_MIGHT),
                source=enum_label(FighterSubclassType.RUNE_KNIGHT),
                activation=TimeEconomy.BONUS_ACTION,
                description="Activate Giant's Might, then roll this extra damage once on each of your turns when a weapon or unarmed strike hits.",
                resourceId=enum_key(FighterSubclassResourceType.GIANTS_MIGHT),
                rollActions=[
                    RollAction(
                        id=FighterSubclassRollActionType.GIANTS_MIGHT_DAMAGE,
                        name=FighterSubclassRollActionType.GIANTS_MIGHT_DAMAGE,
                        diceCount=1,
                        diceType=giant_die,
                        resolution=RollResolutionMode.APPLY_DAMAGE,
                        source=enum_label(FighterSubclassType.RUNE_KNIGHT),
                    )
                ],
            )
        )
        for rune in selected_runes(character_class, fighter_level_value):
            abilities.append(
                SheetAbility(
                    id=enum_key(rune),
                    name=enum_label(rune),
                    source=enum_label(FighterSubclassType.RUNE_KNIGHT),
                    activation=rune_activation(rune),
                    description=rune_ability_description(rune),
                    resourceId=enum_key(rune),
                    rollActions=rune_roll_actions(rune),
                    conditionEffects=rune_condition_effects(rune),
                )
            )
    if subclass == FighterSubclassType.RUNE_KNIGHT and fighter_level_value >= 7:
        abilities.append(
            resource_ability(
                FighterSubclassResourceType.RUNIC_SHIELD,
                FighterSubclassType.RUNE_KNIGHT,
                TimeEconomy.REACTION,
                "Force an attacker to reroll a hit against another creature within 60 feet and use the new roll.",
            )
        )
    if subclass == FighterSubclassType.ECHO_KNIGHT and fighter_level_value >= 3:
        abilities.append(
            resource_ability(
                FighterSubclassResourceType.UNLEASH_INCARNATION,
                FighterSubclassType.ECHO_KNIGHT,
                TimeEconomy.SPECIAL,
                "Make one additional melee attack from your echo's position when you take the Attack action.",
            )
        )
    if subclass == FighterSubclassType.ECHO_KNIGHT and fighter_level_value >= 10:
        abilities.append(
            resource_ability(
                FighterSubclassResourceType.SHADOW_MARTYR,
                FighterSubclassType.ECHO_KNIGHT,
                TimeEconomy.REACTION,
                "Before an attack roll against another creature, teleport your echo near that creature and have the attack target the echo instead.",
            )
        )
    if subclass == FighterSubclassType.PSI_WARRIOR and fighter_level_value >= 3:
        abilities.extend(
            [
                resource_ability(
                    FighterSubclassResourceType.PSIONIC_ENERGY_RECOVERY,
                    FighterSubclassType.PSI_WARRIOR,
                    TimeEconomy.BONUS_ACTION,
                    "Regain one expended Psionic Energy die.",
                ),
                resource_ability(
                    FighterSubclassResourceType.TELEKINETIC_MOVEMENT,
                    FighterSubclassType.PSI_WARRIOR,
                    TimeEconomy.ACTION,
                    "Move a willing creature or loose object within 30 feet; spend a Psionic Energy die to use again.",
                ),
            ]
        )
    if subclass == FighterSubclassType.PSI_WARRIOR and fighter_level_value >= 7:
        abilities.append(
            resource_ability(
                FighterSubclassResourceType.PSI_POWERED_LEAP,
                FighterSubclassType.PSI_WARRIOR,
                TimeEconomy.BONUS_ACTION,
                "Gain a flying speed equal to twice your walking speed until the end of the turn; spend a Psionic Energy die to use again.",
            )
        )
    if subclass == FighterSubclassType.PSI_WARRIOR and fighter_level_value >= 10:
        abilities.append(
            resource_ability(
                FighterSubclassResourceType.PSIONIC_ENERGY_DICE,
                FighterSubclassType.PSI_WARRIOR,
                TimeEconomy.SPECIAL,
                "Spend one Psionic Energy die to end every charm or frighten effect on yourself at the start of your turn.",
                ability_id="guardedMind",
                ability_name="Guarded Mind",
            )
        )
    if subclass == FighterSubclassType.PSI_WARRIOR and fighter_level_value >= 15:
        abilities.append(
            resource_ability(
                FighterSubclassResourceType.BULWARK_OF_FORCE,
                FighterSubclassType.PSI_WARRIOR,
                TimeEconomy.BONUS_ACTION,
                "Grant half cover for 1 minute to visible creatures within 30 feet, up to Intelligence modifier minimum one; spend a Psionic Energy die to use again.",
            )
        )
    if subclass == FighterSubclassType.PSI_WARRIOR and fighter_level_value >= 18:
        abilities.append(
            resource_ability(
                FighterSubclassResourceType.TELEKINETIC_MASTER,
                FighterSubclassType.PSI_WARRIOR,
                TimeEconomy.ACTION,
                "Cast Telekinesis without components; spend a Psionic Energy die to use again.",
            )
        )
    return abilities


def fighter_subclass_spells(classes) -> list[SpellEntry]:
    character_class = fighter_subclass_class(classes)
    if character_class is None:
        return []
    if character_class.subclass == FighterSubclassType.MONSTER_HUNTER and character_class.level >= 3:
        return [
            SpellEntry(
                id=SpellId.DETECT_MAGIC,
                name=SpellId.DETECT_MAGIC,
                source=SpellSource.MONSTER_HUNTER,
                level=1,
                school=SpellSchool.DIVINATION,
                castingAbility=AbilityType.WISDOM,
                castingTime=SpellCastingTime.TEN_MINUTES,
                targeting=SpellTargeting(rangeType=SpellRangeType.SELF, area=SpellRadiusArea(radiusFeet=30)),
                duration=SpellDuration(unit=SpellDurationUnit.MINUTE, amount=10, maximum=True),
                components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
                ritual=True,
                concentration=True,
                description="For the duration, sense magic within 30 feet and use an Action to see a faint aura around visible magical creatures or objects.",
            ),
            SpellEntry(
                id=SpellId.PROTECTION_FROM_EVIL_AND_GOOD,
                name=SpellId.PROTECTION_FROM_EVIL_AND_GOOD,
                source=SpellSource.MONSTER_HUNTER,
                level=1,
                school=SpellSchool.ABJURATION,
                castingAbility=AbilityType.WISDOM,
                castingTime=SpellCastingTime.ACTION,
                targeting=SpellTargeting(rangeType=SpellRangeType.TOUCH),
                duration=SpellDuration(unit=SpellDurationUnit.MINUTE, amount=10, maximum=True),
                components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
                concentration=True,
                resourceId=enum_key(FighterSubclassResourceType.PROTECTION_FROM_EVIL_AND_GOOD),
                reset=RestType.LONG_REST,
                description="One willing creature is protected against aberrations, celestials, elementals, fey, fiends, and undead.",
            ),
        ]
    if character_class.subclass == FighterSubclassType.PSI_WARRIOR and character_class.level >= 18:
        return [
            SpellEntry(
                id=SpellId.TELEKINESIS,
                name=SpellId.TELEKINESIS,
                source=SpellSource.PSI_WARRIOR,
                level=5,
                school=SpellSchool.TRANSMUTATION,
                castingAbility=AbilityType.INTELLIGENCE,
                castingTime=SpellCastingTime.ACTION,
                targeting=SpellTargeting(rangeType=SpellRangeType.DISTANCE, distanceFeet=60),
                duration=SpellDuration(unit=SpellDurationUnit.MINUTE, amount=10, maximum=True),
                components=[],
                concentration=True,
                resourceId=enum_key(FighterSubclassResourceType.TELEKINETIC_MASTER),
                reset=RestType.LONG_REST,
                description="Move or manipulate creatures and objects with sustained telekinetic force. While concentrating, make one weapon attack as a Bonus Action on each of your turns.",
            )
        ]
    return []


def normalized_spellcasting_spells(classes, spells: list[SpellEntry]) -> list[SpellEntry]:
    character_class = fighter_subclass_class(classes)
    if character_class is None or character_class.subclass != FighterSubclassType.ELDRITCH_KNIGHT:
        return spells
    return [
        normalized_eldritch_knight_spell(spell)
        for spell in spells
    ]


def normalized_eldritch_knight_spell(spell: SpellEntry) -> SpellEntry:
    return SpellEntry(
        id=spell.id,
        name=spell.name,
        source=spell.source or SpellSource.ELDRITCH_KNIGHT,
        level=spell.level,
        school=spell.school,
        castingAbility=AbilityType.INTELLIGENCE,
        castingTime=spell.castingTime,
        targeting=spell.targeting,
        duration=spell.duration,
        components=list(spell.components),
        description=spell.description,
        concentration=spell.concentration,
        ritual=spell.ritual,
        resourceId=spell.resourceId,
        reset=spell.reset,
    )


def eldritch_knight_spell_options(fighter_level_value: int, selected_spell_ids: list[str] | None = None) -> list[SpellEntry]:
    selected = set(selected_spell_ids or [])
    max_spell_level = eldritch_knight_max_spell_level(fighter_level_value)
    flexible_slots_used = eldritch_knight_flexible_spell_count([
        spell
        for spell_id in selected
        if (spell_key := enum_value(SpellId, spell_id)) is not None
        if (spell := ELDRITCH_KNIGHT_SPELL_CATALOG.get(spell_key)) is not None
    ])
    flexible_slots_available = eldritch_knight_flexible_spell_limit(fighter_level_value)
    return [
        normalized_eldritch_knight_spell(spell)
        for spell in ELDRITCH_KNIGHT_SPELL_CATALOG.values()
        if (spell.level == 0 or spell.level <= max_spell_level)
        and (
            enum_key(spell.id) in selected
            or spell.level == 0
            or is_eldritch_knight_school_spell(spell)
            or flexible_slots_used < flexible_slots_available
        )
    ]


def eldritch_knight_catalog_spell(spell_id: str | SpellId) -> SpellEntry | None:
    spell_key = spell_id if isinstance(spell_id, SpellId) else enum_value(SpellId, spell_id)
    spell = ELDRITCH_KNIGHT_SPELL_CATALOG.get(spell_key)
    return normalized_eldritch_knight_spell(spell) if spell is not None else None


def eldritch_knight_max_spell_level(fighter_level_value: int) -> int:
    progression = eldritch_knight_spellcasting(fighter_level_value)
    if progression.fourth_level_slots:
        return 4
    if progression.third_level_slots:
        return 3
    if progression.second_level_slots:
        return 2
    if progression.first_level_slots:
        return 1
    return 0


def eldritch_knight_flexible_spell_limit(fighter_level_value: int) -> int:
    if fighter_level_value < 3:
        return 0
    return 1 + sum(1 for level in (8, 14, 20) if fighter_level_value >= level)


def eldritch_knight_flexible_spell_count(spells: list[SpellEntry]) -> int:
    return sum(1 for spell in spells if spell.level > 0 and not is_eldritch_knight_school_spell(spell))


def is_eldritch_knight_spell_selection_valid(fighter_level_value: int, spells: list[SpellEntry]) -> bool:
    if fighter_level_value < 3:
        return not spells
    progression = eldritch_knight_spellcasting(fighter_level_value)
    max_spell_level = eldritch_knight_max_spell_level(fighter_level_value)
    cantrips = [spell for spell in spells if spell.level == 0]
    leveled_spells = [spell for spell in spells if spell.level > 0]
    return (
        len(cantrips) == progression.cantrips_known
        and len(leveled_spells) == progression.spells_known
        and all(spell.level <= max_spell_level for spell in leveled_spells)
        and eldritch_knight_flexible_spell_count(leveled_spells) <= eldritch_knight_flexible_spell_limit(fighter_level_value)
    )


def pruned_eldritch_knight_spells(fighter_level_value: int, spells: list[SpellEntry]) -> list[SpellEntry]:
    if fighter_level_value < 3:
        return []
    progression = eldritch_knight_spellcasting(fighter_level_value)
    max_spell_level = eldritch_knight_max_spell_level(fighter_level_value)
    flexible_limit = eldritch_knight_flexible_spell_limit(fighter_level_value)
    cantrips: list[SpellEntry] = []
    leveled_spells: list[SpellEntry] = []
    flexible_count = 0
    for spell in spells:
        if spell.level == 0:
            if len(cantrips) < progression.cantrips_known:
                cantrips.append(spell)
            continue
        if spell.level > max_spell_level or len(leveled_spells) >= progression.spells_known:
            continue
        if is_eldritch_knight_school_spell(spell):
            leveled_spells.append(spell)
            continue
        if flexible_count < flexible_limit:
            leveled_spells.append(spell)
            flexible_count += 1
    return [*cantrips, *leveled_spells]


def is_eldritch_knight_school_spell(spell: SpellEntry) -> bool:
    return spell.school in {SpellSchool.ABJURATION, SpellSchool.EVOCATION}


def resource_ability(
    resource_type: FighterSubclassResourceType,
    subclass: FighterSubclassType,
    activation: TimeEconomy,
    description: str,
    *,
    ability_id: str | None = None,
    ability_name: str | None = None,
    conditionEffects: list[ConditionEffect] | None = None,
) -> SheetAbility:
    return SheetAbility(
        id=ability_id or enum_key(resource_type),
        name=ability_name or enum_label(resource_type),
        source=enum_label(subclass),
        activation=activation,
        description=description,
        resourceId=enum_key(resource_type),
        conditionEffects=conditionEffects,
    )


def selected_arcane_shots(character_class) -> list[ArcaneShotType]:
    return character_class.arcaneShots or list(ArcaneShotType)


def eldritch_knight_spellcasting(fighter_level_value: int) -> EldritchKnightSpellcastingProgression:
    eligible_level = max(level for level in ELDRITCH_KNIGHT_SPELLCASTING if fighter_level_value >= level)
    return ELDRITCH_KNIGHT_SPELLCASTING[eligible_level]


def eldritch_knight_spell_slot_resources(
    progression: EldritchKnightSpellcastingProgression,
) -> list[tuple[FighterSubclassResourceType, int, int]]:
    return [
        slot_resource
        for slot_resource in [
            (FighterSubclassResourceType.FIRST_LEVEL_SPELL_SLOTS, 1, progression.first_level_slots),
            (FighterSubclassResourceType.SECOND_LEVEL_SPELL_SLOTS, 2, progression.second_level_slots),
            (FighterSubclassResourceType.THIRD_LEVEL_SPELL_SLOTS, 3, progression.third_level_slots),
            (FighterSubclassResourceType.FOURTH_LEVEL_SPELL_SLOTS, 4, progression.fourth_level_slots),
        ]
        if slot_resource[2] > 0
    ]


def subclass_feature(progression: SubclassFeatureProgression, fighter_level_value: int) -> SheetFeature:
    description = progression.description
    if progression.subclass == FighterSubclassType.ELDRITCH_KNIGHT and progression.featureType == EldritchKnightFeatureType.SPELLCASTING:
        spellcasting = eldritch_knight_spellcasting(fighter_level_value)
        description = f"{description} You know {spellcasting.cantrips_known} cantrips and {spellcasting.spells_known} leveled spells."
    return SheetFeature(
        id=enum_key(progression.featureType),
        name=enum_label(progression.featureType),
        source=enum_label(progression.subclass),
        activation=progression.activation,
        description=description,
        conditionEffects=list(progression.conditionEffects) or None,
    )


def arcane_shot_roll_actions(arcane_shot: ArcaneShotType, fighter_level_value: int) -> list[RollAction] | None:
    damage_type = arcane_shot_damage_type(arcane_shot)
    dice_count = arcane_shot_dice_count(arcane_shot, fighter_level_value)
    if damage_type is None or dice_count <= 0:
        return None
    return [
        RollAction(
            id=arcane_shot,
            name=arcane_shot,
            diceCount=dice_count,
            diceType=DiceType.D6,
            consumesResource=FighterSubclassResourceType.ARCANE_SHOT,
            source=enum_label(FighterSubclassType.ARCANE_ARCHER),
            resolution=RollResolutionMode.APPLY_DAMAGE,
            damageType=damage_type,
            conditionEffects=arcane_shot_condition_effects(arcane_shot),
        )
    ]


def arcane_shot_dice_count(arcane_shot: ArcaneShotType, fighter_level_value: int) -> int:
    if arcane_shot == ArcaneShotType.BANISHING_ARROW:
        return 2 if fighter_level_value >= 18 else 0
    if arcane_shot in {ArcaneShotType.PIERCING_ARROW, ArcaneShotType.SEEKING_ARROW}:
        return 2 if fighter_level_value >= 18 else 1
    return 4 if fighter_level_value >= 18 else 2


def arcane_shot_damage_type(arcane_shot: ArcaneShotType) -> DamageType | None:
    return {
        ArcaneShotType.BANISHING_ARROW: DamageType.FORCE,
        ArcaneShotType.BEGUILING_ARROW: DamageType.PSYCHIC,
        ArcaneShotType.BURSTING_ARROW: DamageType.FORCE,
        ArcaneShotType.ENFEEBLING_ARROW: DamageType.NECROTIC,
        ArcaneShotType.GRASPING_ARROW: DamageType.POISON,
        ArcaneShotType.PIERCING_ARROW: DamageType.PIERCING,
        ArcaneShotType.SEEKING_ARROW: DamageType.FORCE,
        ArcaneShotType.SHADOW_ARROW: DamageType.PSYCHIC,
    }.get(arcane_shot)


def arcane_shot_condition_effects(arcane_shot: ArcaneShotType) -> list[ConditionEffect] | None:
    effects = {
        ArcaneShotType.BANISHING_ARROW: [
            ConditionEffect(
                condition=None,
                mode=ConditionApplicationMode.TARGET_SAVE,
                savingThrow=AbilityType.CHARISMA,
                saveDcAbility=AbilityType.INTELLIGENCE,
                description="On a failed Charisma save, the target is banished until the end of its next turn.",
            )
        ],
        ArcaneShotType.BEGUILING_ARROW: [
            ConditionEffect(
                condition=ConditionType.CHARMED,
                mode=ConditionApplicationMode.TARGET_SAVE,
                savingThrow=AbilityType.WISDOM,
                saveDcAbility=AbilityType.INTELLIGENCE,
                description="On a failed Wisdom save, the target is charmed by an ally until the start of your next turn.",
            )
        ],
        ArcaneShotType.ENFEEBLING_ARROW: [
            ConditionEffect(
                condition=None,
                mode=ConditionApplicationMode.TARGET_SAVE,
                savingThrow=AbilityType.CONSTITUTION,
                saveDcAbility=AbilityType.INTELLIGENCE,
                description="On a failed Constitution save, the target's weapon attack damage is halved until your next turn.",
            )
        ],
        ArcaneShotType.PIERCING_ARROW: [
            ConditionEffect(
                condition=None,
                mode=ConditionApplicationMode.TARGET_SAVE,
                savingThrow=AbilityType.DEXTERITY,
                saveDcAbility=AbilityType.INTELLIGENCE,
                description="On a successful Dexterity save, the target takes half damage.",
            )
        ],
        ArcaneShotType.SEEKING_ARROW: [
            ConditionEffect(
                condition=None,
                mode=ConditionApplicationMode.TARGET_SAVE,
                savingThrow=AbilityType.DEXTERITY,
                saveDcAbility=AbilityType.INTELLIGENCE,
                description="On a successful Dexterity save, the target takes half damage.",
            )
        ],
        ArcaneShotType.SHADOW_ARROW: [
            ConditionEffect(
                condition=ConditionType.BLINDED,
                mode=ConditionApplicationMode.TARGET_SAVE,
                savingThrow=AbilityType.WISDOM,
                saveDcAbility=AbilityType.INTELLIGENCE,
                description="On a failed Wisdom save, the target cannot see farther than 5 feet until the start of your next turn.",
            )
        ],
    }
    return effects.get(arcane_shot)


def psionic_strike_condition_effects(fighter_level_value: int) -> list[ConditionEffect] | None:
    if fighter_level_value < 7:
        return None
    return [
        ConditionEffect(
            condition=ConditionType.PRONE,
            mode=ConditionApplicationMode.TARGET_SAVE,
            savingThrow=AbilityType.STRENGTH,
            saveDcAbility=AbilityType.INTELLIGENCE,
            description="After Psionic Strike deals damage, Telekinetic Thrust can knock the target prone on a failed Strength save.",
        )
    ]


def arcane_shot_description(arcane_shot: ArcaneShotType, fighter_level_value: int) -> str:
    save_dc = "Arcane Shot save DC is 8 + Proficiency Bonus + Intelligence modifier."
    descriptions = {
        ArcaneShotType.BANISHING_ARROW: "Hit target makes a Charisma save or is banished until the end of its next turn. At Fighter 18, the hit also deals force damage.",
        ArcaneShotType.BEGUILING_ARROW: "Hit target takes psychic damage and makes a Wisdom save or is charmed by an ally until the start of your next turn.",
        ArcaneShotType.BURSTING_ARROW: "After the arrow hits, the target and each creature within 10 feet take force damage.",
        ArcaneShotType.ENFEEBLING_ARROW: "Hit target takes necrotic damage and makes a Constitution save or its weapon attack damage is halved until your next turn.",
        ArcaneShotType.GRASPING_ARROW: "Hit target takes poison damage, has speed reduced, and takes slashing damage the first time each turn it moves without teleporting.",
        ArcaneShotType.PIERCING_ARROW: "No attack roll; creatures in a 30-foot line make a Dexterity save, taking weapon damage plus piercing damage on failure or half on success.",
        ArcaneShotType.SEEKING_ARROW: "No attack roll; a seen target makes a Dexterity save, taking weapon damage plus force damage on failure or half on success.",
        ArcaneShotType.SHADOW_ARROW: "Hit target takes psychic damage and makes a Wisdom save or cannot see beyond 5 feet until your next turn.",
    }
    return f"{descriptions[arcane_shot]} {save_dc}"


def selected_runes(character_class, fighter_level_value: int) -> list[RuneType]:
    configured = character_class.runes or list(RuneType)
    return [rune for rune in configured if rune_minimum_level(rune) <= fighter_level_value]


def rune_minimum_level(rune: RuneType) -> int:
    return 7 if rune in {RuneType.HILL_RUNE, RuneType.STORM_RUNE} else 3


def rune_uses(fighter_level_value: int) -> int:
    return 2 if fighter_level_value >= 15 else 1


def rune_activation(rune: RuneType) -> TimeEconomy:
    if rune in {RuneType.CLOUD_RUNE, RuneType.STONE_RUNE, RuneType.STORM_RUNE}:
        return TimeEconomy.REACTION
    return TimeEconomy.BONUS_ACTION if rune in {RuneType.FROST_RUNE, RuneType.HILL_RUNE} else TimeEconomy.SPECIAL


def rune_resource_description(rune: RuneType) -> str:
    return f"Invoke {enum_label(rune)}. Rune Magic save DC is 8 + Proficiency Bonus + Constitution modifier."


def rune_ability_description(rune: RuneType) -> str:
    descriptions = {
        RuneType.CLOUD_RUNE: "Reaction when you or a visible creature within 30 feet is hit by an attack: redirect the attack to another creature within 30 feet.",
        RuneType.FIRE_RUNE: "When you hit with a weapon attack, deal extra fire damage and force a Strength save or restrain the target with fiery shackles.",
        RuneType.FROST_RUNE: "Bonus Action for 10 minutes: gain +2 to Strength and Constitution ability checks and saving throws.",
        RuneType.STONE_RUNE: "Reaction when a visible creature ends its turn within 30 feet: force a Wisdom save or charm and incapacitate it with speed 0.",
        RuneType.HILL_RUNE: "Bonus Action for 1 minute: gain resistance to bludgeoning, piercing, and slashing damage.",
        RuneType.STORM_RUNE: "Bonus Action for 1 minute: use Reactions to give visible creatures within 60 feet Advantage or Disadvantage on attacks, saves, or checks.",
    }
    return descriptions[rune]


def rune_condition_effects(rune: RuneType) -> list[ConditionEffect] | None:
    if rune != RuneType.STONE_RUNE:
        return None
    return [
        ConditionEffect(
            condition=ConditionType.CHARMED,
            mode=ConditionApplicationMode.TARGET_SAVE,
            savingThrow=AbilityType.WISDOM,
            saveDcAbility=AbilityType.CONSTITUTION,
            description="On a failed Wisdom save, the target is charmed by Stone Rune for 1 minute.",
        ),
        ConditionEffect(
            condition=ConditionType.INCAPACITATED,
            mode=ConditionApplicationMode.TARGET_SAVE,
            savingThrow=AbilityType.WISDOM,
            saveDcAbility=AbilityType.CONSTITUTION,
            description="On a failed Wisdom save, the target is incapacitated by Stone Rune for 1 minute.",
        ),
    ]


def rune_roll_actions(rune: RuneType) -> list[RollAction] | None:
    if rune != RuneType.FIRE_RUNE:
        return None
    return [
        RollAction(
            id=FighterSubclassRollActionType.FIRE_RUNE_SHACKLES,
            name=FighterSubclassRollActionType.FIRE_RUNE_SHACKLES,
            diceCount=2,
            diceType=DiceType.D6,
            consumesResource=RuneType.FIRE_RUNE,
            source=enum_label(FighterSubclassType.RUNE_KNIGHT),
            resolution=RollResolutionMode.APPLY_DAMAGE,
            damageType=DamageType.FIRE,
            conditionEffects=[
                ConditionEffect(
                    condition=ConditionType.RESTRAINED,
                    mode=ConditionApplicationMode.TARGET_SAVE,
                    savingThrow=AbilityType.STRENGTH,
                    saveDcAbility=AbilityType.CONSTITUTION,
                    description="On a failed Strength save, the target is restrained by fiery shackles.",
                )
            ],
        )
    ]


def giants_might_die(fighter_level_value: int) -> DiceType:
    if fighter_level_value >= 18:
        return DiceType.D10
    if fighter_level_value >= 10:
        return DiceType.D8
    return DiceType.D6


def psionic_energy_die(fighter_level_value: int) -> DiceType:
    if fighter_level_value >= 17:
        return DiceType.D12
    if fighter_level_value >= 11:
        return DiceType.D10
    if fighter_level_value >= 5:
        return DiceType.D8
    return DiceType.D6


def brute_force_die(fighter_level_value: int) -> DiceType | None:
    eligible = [progression for progression in BRUTE_FORCE_PROGRESSION if fighter_level_value >= progression.minimum_level]
    return eligible[-1].die if eligible else None


def fighter_subclass_class(classes):
    return next((character_class for character_class in classes if character_class.subclass in set(FighterSubclassType)), None)


def subclass_character_class(subclass: FighterSubclassType, fighter_level_value: int):
    from dnd_board.character_sheet import ClassType, CharacterClassLevel

    return CharacterClassLevel(name=ClassType.FIGHTER, level=fighter_level_value, subclass=subclass)
