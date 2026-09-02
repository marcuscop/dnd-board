from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from dnd_board.character_sheet import (
    AbilityType,
    ArmorCategory,
    AttackAction,
    AttackActionType,
    AttackDamageAbilityModifierMode,
    AttackKind,
    AttackRangeType,
    CharacterClassLevel,
    DamageType,
    DiceType,
    EquipmentItem,
    EquipmentSlot,
    EquipmentType,
    FightingStyleType,
    ResourceTracker,
    RestType,
    RollAction,
    RollModifierBreakdown,
    RollModifierType,
    RollResolutionMode,
    SheetAbility,
    TimeEconomy,
    WeaponCategory,
    WeaponProperty,
    enum_key,
    enum_label,
)
from dnd_board.rules.sources import RuleSource, is_legacy_source, rule_source_label
from dnd_board.rules.species import SpeciesType


class FeatCategory(Enum):
    ORIGIN = auto()
    GENERAL = auto()
    FIGHTING_STYLE = auto()
    EPIC_BOON = auto()
    DRAGONMARK = auto()
    GREATER_DRAGONMARK = auto()
    PLANAR_PACT = auto()
    GREATER_PLANAR_PACT = auto()
    DARK_GIFT = auto()


class FeatSheetField(Enum):
    ABILITIES = "abilities"
    ABILITY_SCORES = "abilityScores"
    BACKGROUND = "background"
    CHARACTER_CLASS = "characterClass"
    CLASSES = "classes"
    FEATS = "feats"
    FEATURES = "features"
    PROFICIENCIES = "proficiencies"
    RACE = "race"
    SPELLS = "spells"


class FeatFeatureField(Enum):
    DESCRIPTION = "description"
    ID = "id"
    NAME = "name"


class FeatResourceId(Enum):
    LUCK_POINTS = "luckPoints"
    BOON_OF_COMBAT_PROWESS = "boonOfCombatProwess"
    BOON_OF_DIMENSIONAL_TRAVEL = "boonOfDimensionalTravel"
    BOON_OF_FATE = "boonOfFate"
    BOON_OF_RECOVERY = "boonOfRecovery"


class FeatAbilityId(Enum):
    HEALER = "healer"
    LUCKY_ADVANTAGE = "luckyAdvantage"
    LUCKY_DISADVANTAGE = "luckyDisadvantage"
    OBSERVANT_QUICK_SEARCH = "observantQuickSearch"
    TELEKINETIC_SHOVE = "telekineticShove"
    BOON_OF_COMBAT_PROWESS = "boonOfCombatProwess"
    BOON_OF_DIMENSIONAL_TRAVEL = "boonOfDimensionalTravel"
    BOON_OF_FATE = "boonOfFate"
    BOON_OF_RECOVERY = "boonOfRecovery"


class FeatCharacterClassField(Enum):
    LEVEL = "level"


class GeneralFeatType(Enum):
    ACTOR = auto()
    ALERT = auto()
    ARTIFICER_INITIATE = auto()
    ATHLETE = auto()
    BOUNTIFUL_LUCK = auto()
    CHARGER = auto()
    CHEF = auto()
    CROSSBOW_EXPERT = auto()
    CRAFTER = auto()
    CRUSHER = auto()
    DEFENSIVE_DUELIST = auto()
    DRAGON_FEAR = auto()
    DRAGON_HIDE = auto()
    DROW_HIGH_MAGIC = auto()
    DUAL_WIELDER = auto()
    DUNGEON_DELVER = auto()
    DURABLE = auto()
    DWARF_FORTITUDE = auto()
    ELDRITCH_ADEPT = auto()
    ELEMENTAL_ADEPT = auto()
    ELVEN_ACCURACY = auto()
    EMBER_OF_THE_FIRE_GIANT = auto()
    FADE_AWAY = auto()
    FEY_TELEPORTATION = auto()
    FEY_TOUCHED = auto()
    FIGHTING_INITIATE = auto()
    FLAMES_OF_PHLEGETHOS = auto()
    FURY_OF_THE_FROST_GIANT = auto()
    GIFT_OF_THE_CHROMATIC_DRAGON = auto()
    GIFT_OF_THE_GEM_DRAGON = auto()
    GIFT_OF_THE_METALLIC_DRAGON = auto()
    GRAPPLER = auto()
    GREAT_WEAPON_MASTER = auto()
    GUILE_OF_THE_CLOUD_GIANT = auto()
    GUNNER = auto()
    HEALER = auto()
    HEAVILY_ARMORED = auto()
    HEAVY_ARMOR_MASTER = auto()
    INFERNAL_CONSTITUTION = auto()
    INSPIRING_LEADER = auto()
    KEEN_MIND = auto()
    KEENNESS_OF_THE_STONE_GIANT = auto()
    LIGHTLY_ARMORED = auto()
    LINGUIST = auto()
    LUCKY = auto()
    MAGE_SLAYER = auto()
    MAGIC_INITIATE = auto()
    MARTIAL_ADEPT = auto()
    MEDIUM_ARMOR_MASTER = auto()
    METAMAGIC_ADEPT = auto()
    MOBILE = auto()
    MODERATELY_ARMORED = auto()
    MOUNTED_COMBATANT = auto()
    MUSICIAN = auto()
    OBSERVANT = auto()
    ORCISH_FURY = auto()
    PIERCER = auto()
    POISONER = auto()
    POLEARM_MASTER = auto()
    PRODIGY = auto()
    RESILIENT = auto()
    RITUAL_CASTER = auto()
    RUNE_SHAPER = auto()
    SAVAGE_ATTACKER = auto()
    SECOND_CHANCE = auto()
    SENTINEL = auto()
    SHADOW_TOUCHED = auto()
    SHARPSHOOTER = auto()
    SHIELD_MASTER = auto()
    SKILL_EXPERT = auto()
    SKILLED = auto()
    SKULKER = auto()
    SLASHER = auto()
    SOUL_OF_THE_STORM_GIANT = auto()
    SPELL_SNIPER = auto()
    SQUAT_NIMBLENESS = auto()
    STRIKE_OF_THE_GIANTS = auto()
    TAVERN_BRAWLER = auto()
    TELEKINETIC = auto()
    TELEPATHIC = auto()
    TOUGH = auto()
    VIGOR_OF_THE_HILL_GIANT = auto()
    WAR_CASTER = auto()
    WEAPON_MASTER = auto()
    WOOD_ELF_MAGIC = auto()
    SHARP_EYE = "Sharp Eye"
    SURVIVOR = "Survivor"
    CULT_OF_THE_DRAGON_INITIATE = "Cult of the Dragon Initiate"
    EMERALD_ENCLAVE_FLEDGLING = "Emerald Enclave Fledgling"
    HARPER_AGENT = "Harper Agent"
    LORDS_ALLIANCE_AGENT = "Lords' Alliance Agent"
    PURPLE_DRAGON_ROOK = "Purple Dragon Rook"
    SPELLFIRE_SPARK = "Spellfire Spark"
    TYRO_OF_THE_GAUNTLET = "Tyro of the Gauntlet"
    ZHENTARIM_RUFFIAN = "Zhentarim Ruffian"
    CHILD_OF_THE_SUN = "Child of the Sun"
    SHADOWMOOR_HEXER = "Shadowmoor Hexer"
    TIRELESS_REVELER = "Tireless Reveler"
    VAMPIRE_HUNTER = "Vampire Hunter"
    VAMPIRE_S_PLAYTHING = "Vampire's Plaything"
    ABILITY_SCORE_IMPROVEMENT = "Ability Score Improvement"
    MARTIAL_WEAPON_TRAINING = "Martial Weapon Training"
    SHIFTING_COMBATANT = "Shifting Combatant"
    SPEEDY = "Speedy"
    TACTICAL_COMBATANT = "Tactical Combatant"
    COLD_CASTER = "Cold Caster"
    DRAGONSCARRED = "Dragonscarred"
    ENCLAVE_MAGIC = "Enclave Magic"
    FAIRY_TRICKSTER = "Fairy Trickster"
    GENIE_MAGIC = "Genie Magic"
    HARPER_TEAMWORK = "Harper Teamwork"
    LORDLY_RESOLVE = "Lordly Resolve"
    MYTHAL_TOUCHED = "Mythal Touched"
    ORDER_S_RESILIENCE = "Order's Resilience"
    PURPLE_DRAGON_COMMANDANT = "Purple Dragon Commandant"
    SPELLFIRE_ADEPT = "Spellfire Adept"
    STREET_JUSTICE = "Street Justice"
    ZHENTARIM_TACTICS = "Zhentarim Tactics"
    BLOODLUST = "Bloodlust"
    BOMBER = "Bomber"
    CLOYING_MISTS = "Cloying Mists"
    DELICIOUS_PAIN = "Delicious Pain"
    LIGHT_BRINGER = "Light Bringer"
    LOVE_BITES = "Love Bites"
    PUTREFY = "Putrefy"
    REBUKE = "Rebuke"
    TREACHEROUS_ALLURE = "Treacherous Allure"
    VAMPIRE_TOUCHED = "Vampire Touched"
    BOON_OF_COMBAT_PROWESS = "Boon of Combat Prowess"
    BOON_OF_DIMENSIONAL_TRAVEL = "Boon of Dimensional Travel"
    BOON_OF_ENERGY_RESISTANCE = "Boon of Energy Resistance"
    BOON_OF_FATE = "Boon of Fate"
    BOON_OF_FORTITUDE = "Boon of Fortitude"
    BOON_OF_IRRESISTIBLE_OFFENSE = "Boon of Irresistible Offense"
    BOON_OF_RECOVERY = "Boon of Recovery"
    BOON_OF_SKILL = "Boon of Skill"
    BOON_OF_SPEED = "Boon of Speed"
    BOON_OF_SPELL_RECALL = "Boon of Spell Recall"
    BOON_OF_THE_NIGHT_SPIRIT = "Boon of the Night Spirit"
    BOON_OF_TRUESIGHT = "Boon of Truesight"
    BOON_OF_SIBERYS = "Boon of Siberys"
    BOON_OF_BLOODSHED = "Boon of Bloodshed"
    BOON_OF_BOUNTIFUL_HEALTH = "Boon of Bountiful Health"
    BOON_OF_COMMUNICATION = "Boon of Communication"
    BOON_OF_DESPERATE_RESILIENCE = "Boon of Desperate Resilience"
    BOON_OF_EXQUISITE_RADIANCE = "Boon of Exquisite Radiance"
    BOON_OF_FLUID_FORMS = "Boon of Fluid Forms"
    BOON_OF_FORTUNE_S_FAVOR = "Boon of Fortune's Favor"
    BOON_OF_POISON_MASTERY = "Boon of Poison Mastery"
    BOON_OF_REVELRY = "Boon of Revelry"
    BOON_OF_TERROR = "Boon of Terror"
    BOON_OF_THE_BRIGHT_SUN = "Boon of the Bright Sun"
    BOON_OF_THE_FURIOUS_STORM = "Boon of the Furious Storm"
    BOON_OF_THE_SOUL_DRINKER = "Boon of the Soul Drinker"
    BOON_OF_BLAZING_DAWN = "Boon of Blazing Dawn"
    BOON_OF_LOOMING_SHADOWS = "Boon of Looming Shadows"
    BOON_OF_MISTY_ESCAPE = "Boon of Misty Escape"
    ABERRANT_DRAGONMARK = "Aberrant Dragonmark"
    MARK_OF_DETECTION = "Mark of Detection"
    MARK_OF_FINDING = "Mark of Finding"
    MARK_OF_HANDLING = "Mark of Handling"
    MARK_OF_HEALING = "Mark of Healing"
    MARK_OF_HOSPITALITY = "Mark of Hospitality"
    MARK_OF_MAKING = "Mark of Making"
    MARK_OF_PASSAGE = "Mark of Passage"
    MARK_OF_SCRIBING = "Mark of Scribing"
    MARK_OF_SENTINEL = "Mark of Sentinel"
    MARK_OF_SHADOW = "Mark of Shadow"
    MARK_OF_STORM = "Mark of Storm"
    MARK_OF_WARDING = "Mark of Warding"
    GREATER_ABERRANT_MARK = "Greater Aberrant Mark"
    GREATER_MARK_OF_DETECTION = "Greater Mark of Detection"
    GREATER_MARK_OF_FINDING = "Greater Mark of Finding"
    GREATER_MARK_OF_HANDLING = "Greater Mark of Handling"
    GREATER_MARK_OF_HEALING = "Greater Mark of Healing"
    GREATER_MARK_OF_HOSPITALITY = "Greater Mark of Hospitality"
    GREATER_MARK_OF_MAKING = "Greater Mark of Making"
    GREATER_MARK_OF_PASSAGE = "Greater Mark of Passage"
    GREATER_MARK_OF_SCRIBING = "Greater Mark of Scribing"
    GREATER_MARK_OF_SENTINEL = "Greater Mark of Sentinel"
    GREATER_MARK_OF_SHADOW = "Greater Mark of Shadow"
    GREATER_MARK_OF_STORM = "Greater Mark of Storm"
    GREATER_MARK_OF_WARDING = "Greater Mark of Warding"
    POTENT_DRAGONMARK = "Potent Dragonmark"
    FEY_PACT = "Fey Pact"
    INFERNAL_PACT = "Infernal Pact"
    FEY_SENTINEL = "Fey Sentinel"
    FEY_TORMENTOR = "Fey Tormentor"
    INFERNAL_BULWARK = "Infernal Bulwark"
    INFERNAL_DRAGOON = "Infernal Dragoon"
    ABERRANT_ANATOMY = "Aberrant Anatomy"
    ECHOING_SOUL = "Echoing Soul"
    GATHERED_WHISPERS = "Gathered Whispers"
    LIVING_SHADOW = "Living Shadow"
    MIST_WALKER = "Mist Walker"
    SECOND_SKIN = "Second Skin"
    SYMBIOTIC_BEING = "Symbiotic Being"
    TOUCH_OF_DEATH = "Touch of Death"
    WATCHERS = "Watchers"


class FeatEffectType(Enum):
    ARMOR_CLASS_BONUS = auto()
    ATTACK_ROLL_BONUS = auto()
    DAMAGE_DICE_REROLL = auto()
    DAMAGE_ABILITY_MODIFIER = auto()
    DAMAGE_ROLL_BONUS = auto()
    ROLL_ABILITY = auto()
    SHEET_ABILITY = auto()
    DESCRIPTION_ONLY = auto()
    RESOURCE = auto()


class FeatAttackRollBonusScope(Enum):
    RANGED_ATTACK = auto()
    RANGED_WEAPON_ATTACK = auto()


class FeatDamageRollBonusScope(Enum):
    ONE_HANDED_MELEE_WEAPON_ATTACK = auto()
    THROWN_RANGED_ATTACK = auto()


class FeatDamageAbilityModifierScope(Enum):
    TWO_WEAPON_FIGHTING_ATTACK = auto()


class FeatDamageDiceRerollScope(Enum):
    TWO_HANDED_OR_VERSATILE_MELEE_WEAPON_ATTACK = auto()


class FeatPrerequisiteType(Enum):
    ABILITY_SCORE = auto()
    ARMOR_PROFICIENCY = auto()
    BACKGROUND = auto()
    CHARACTER_LEVEL = auto()
    CHARACTER_FEATURE = auto()
    FEAT = auto()
    SPECIES = auto()
    SPECIES_SIZE = auto()
    SPELLCASTING = auto()
    WEAPON_PROFICIENCY = auto()


class FeatCharacterFeatureType(Enum):
    FIGHTING_STYLE = "Fighting Style Feature"
    PACT_MAGIC = "Pact Magic Feature"
    RUNE_CARVER = "Rune Carver Background"
    SPELLCASTING = "Spellcasting Feature"


class FeatSpeciesSize(Enum):
    SMALL = "Small"


class WeaponProficiencyType(Enum):
    MARTIAL = "Martial Weapon"


class GiantStrikeType(Enum):
    CLOUD_STRIKE = "Cloud Strike"
    FIRE_STRIKE = "Fire Strike"
    FROST_STRIKE = "Frost Strike"
    HILL_STRIKE = "Hill Strike"
    STONE_STRIKE = "Stone Strike"
    STORM_STRIKE = "Storm Strike"


class BackgroundPrerequisiteType(Enum):
    GIANT_FOUNDLING = "Giant Foundling"


@dataclass(frozen=True)
class FeatPrerequisite:
    prerequisiteType: FeatPrerequisiteType
    minimumLevel: int = 0
    minimumScore: int = 0
    abilities: tuple[AbilityType, ...] = ()
    species: tuple[SpeciesType, ...] = ()
    speciesSizes: tuple[FeatSpeciesSize, ...] = ()
    armorCategories: tuple[ArmorCategory, ...] = ()
    weaponProficiencies: tuple[WeaponProficiencyType, ...] = ()
    features: tuple[FeatCharacterFeatureType, ...] = ()
    feats: tuple[GeneralFeatType, ...] = ()
    giantStrikes: tuple[GiantStrikeType, ...] = ()
    backgrounds: tuple[BackgroundPrerequisiteType, ...] = ()


@dataclass(frozen=True)
class FeatEffect:
    effectType: FeatEffectType
    value: int = 0
    attackRollBonusScope: FeatAttackRollBonusScope | None = None
    damageAbilityModifierScope: FeatDamageAbilityModifierScope | None = None
    damageRollBonusScope: FeatDamageRollBonusScope | None = None
    damageDiceRerollScope: FeatDamageDiceRerollScope | None = None
    rollAction: RollAction | None = None
    activation: TimeEconomy = TimeEconomy.PASSIVE
    description: str = ""


@dataclass(frozen=True)
class FeatDefinition:
    featType: FightingStyleType
    category: FeatCategory
    repeatable: bool
    description: str
    effects: tuple[FeatEffect, ...]
    source: RuleSource = RuleSource.PLAYERS_HANDBOOK_2024


FIGHTING_STYLE_SOURCES: dict[FightingStyleType, RuleSource] = {
    FightingStyleType.ARCHERY: RuleSource.PLAYERS_HANDBOOK_2024,
    FightingStyleType.BLIND_FIGHTING: RuleSource.PLAYERS_HANDBOOK_2024,
    FightingStyleType.DEFENSE: RuleSource.PLAYERS_HANDBOOK_2024,
    FightingStyleType.DUELING: RuleSource.PLAYERS_HANDBOOK_2024,
    FightingStyleType.GREAT_WEAPON_FIGHTING: RuleSource.PLAYERS_HANDBOOK_2024,
    FightingStyleType.INTERCEPTION: RuleSource.PLAYERS_HANDBOOK_2024,
    FightingStyleType.PACK_FIGHTING: RuleSource.DND_BEYOND_DROPS_2026,
    FightingStyleType.PRONE_FIGHTING: RuleSource.DND_BEYOND_DROPS_2026,
    FightingStyleType.PROTECTION: RuleSource.PLAYERS_HANDBOOK_2024,
    FightingStyleType.THROWN_WEAPON_FIGHTING: RuleSource.PLAYERS_HANDBOOK_2024,
    FightingStyleType.TWO_WEAPON_FIGHTING: RuleSource.PLAYERS_HANDBOOK_2024,
    FightingStyleType.UNARMED_FIGHTING: RuleSource.PLAYERS_HANDBOOK_2024,
}


def fighting_style_label(style: FightingStyleType) -> str:
    label = enum_label(style)
    return f"{label} (Legacy)" if is_legacy_source(fighting_style_source(style)) else label


def fighting_style_source(style: FightingStyleType) -> RuleSource:
    return FIGHTING_STYLE_SOURCES.get(style, RuleSource.LEGACY)


@dataclass(frozen=True)
class GeneralFeatDefinition:
    featType: GeneralFeatType
    source: RuleSource
    category: FeatCategory
    prerequisites: tuple[FeatPrerequisite, ...]
    description: str
    repeatable: bool = False


def general_feat(feat_type: GeneralFeatType, source: RuleSource, description: str, prerequisites: tuple[FeatPrerequisite, ...] = (), repeatable: bool = False, category: FeatCategory = FeatCategory.GENERAL) -> GeneralFeatDefinition:
    return GeneralFeatDefinition(featType=feat_type, source=source, category=category, prerequisites=prerequisites, description=description, repeatable=repeatable)


def level_prerequisite(minimum_level: int) -> FeatPrerequisite:
    return FeatPrerequisite(FeatPrerequisiteType.CHARACTER_LEVEL, minimumLevel=minimum_level)


def ability_prerequisite(minimum_score: int, *abilities: AbilityType) -> FeatPrerequisite:
    return FeatPrerequisite(FeatPrerequisiteType.ABILITY_SCORE, minimumScore=minimum_score, abilities=abilities)


def species_prerequisite(*species: SpeciesType) -> FeatPrerequisite:
    return FeatPrerequisite(FeatPrerequisiteType.SPECIES, species=species)


def small_species_prerequisite() -> FeatPrerequisite:
    return FeatPrerequisite(FeatPrerequisiteType.SPECIES_SIZE, speciesSizes=(FeatSpeciesSize.SMALL,))


def species_or_size_prerequisite(*species: SpeciesType, sizes: tuple[FeatSpeciesSize, ...]) -> FeatPrerequisite:
    return FeatPrerequisite(FeatPrerequisiteType.SPECIES, species=species, speciesSizes=sizes)


def armor_prerequisite(*armor_categories: ArmorCategory) -> FeatPrerequisite:
    return FeatPrerequisite(FeatPrerequisiteType.ARMOR_PROFICIENCY, armorCategories=armor_categories)


def weapon_prerequisite(*weapon_proficiencies: WeaponProficiencyType) -> FeatPrerequisite:
    return FeatPrerequisite(FeatPrerequisiteType.WEAPON_PROFICIENCY, weaponProficiencies=weapon_proficiencies)


def feature_prerequisite(*features: FeatCharacterFeatureType) -> FeatPrerequisite:
    return FeatPrerequisite(FeatPrerequisiteType.CHARACTER_FEATURE, features=features)


def spellcasting_prerequisite() -> FeatPrerequisite:
    return FeatPrerequisite(FeatPrerequisiteType.SPELLCASTING, features=(FeatCharacterFeatureType.SPELLCASTING, FeatCharacterFeatureType.PACT_MAGIC))


def feat_prerequisite(feat_type: GeneralFeatType, *giant_strikes: GiantStrikeType) -> FeatPrerequisite:
    return FeatPrerequisite(FeatPrerequisiteType.FEAT, feats=(feat_type,), giantStrikes=giant_strikes)


def background_prerequisite(*backgrounds: BackgroundPrerequisiteType) -> FeatPrerequisite:
    return FeatPrerequisite(FeatPrerequisiteType.BACKGROUND, backgrounds=backgrounds)


def weapon_or_background_prerequisite(weapon_proficiency: WeaponProficiencyType, background: BackgroundPrerequisiteType) -> FeatPrerequisite:
    return FeatPrerequisite(FeatPrerequisiteType.WEAPON_PROFICIENCY, weaponProficiencies=(weapon_proficiency,), backgrounds=(background,))


GENERAL_FEATS: dict[GeneralFeatType, GeneralFeatDefinition] = {
    GeneralFeatType.ACTOR: general_feat(GeneralFeatType.ACTOR, RuleSource.PLAYERS_HANDBOOK_2024, "+1 Charisma; improve deception, performance, and mimicry."),
    GeneralFeatType.ALERT: general_feat(GeneralFeatType.ALERT, RuleSource.PLAYERS_HANDBOOK_2024, "+5 initiative, cannot be surprised, and unseen attackers do not gain advantage."),
    GeneralFeatType.ARTIFICER_INITIATE: general_feat(GeneralFeatType.ARTIFICER_INITIATE, RuleSource.TASHAS_CAULDRON_OF_EVERYTHING, "Learn artificer magic and one artisan tool proficiency."),
    GeneralFeatType.ATHLETE: general_feat(GeneralFeatType.ATHLETE, RuleSource.PLAYERS_HANDBOOK_2024, "+1 Strength or Dexterity; improve climbing, standing, and jumping."),
    GeneralFeatType.BOUNTIFUL_LUCK: general_feat(GeneralFeatType.BOUNTIFUL_LUCK, RuleSource.XANATHARS_GUIDE_TO_EVERYTHING, "Let a nearby ally reroll a 1 on a d20.", (species_prerequisite(SpeciesType.HALFLING),)),
    GeneralFeatType.CHARGER: general_feat(GeneralFeatType.CHARGER, RuleSource.PLAYERS_HANDBOOK_2024, "Dash into a melee attack with an added bonus after moving far enough."),
    GeneralFeatType.CHEF: general_feat(GeneralFeatType.CHEF, RuleSource.TASHAS_CAULDRON_OF_EVERYTHING, "+1 Constitution or Wisdom; gain cook's utensils and prepare restorative food."),
    GeneralFeatType.CROSSBOW_EXPERT: general_feat(GeneralFeatType.CROSSBOW_EXPERT, RuleSource.PLAYERS_HANDBOOK_2024, "Improve crossbow handling and close-range ranged attacks."),
    GeneralFeatType.CRAFTER: general_feat(GeneralFeatType.CRAFTER, RuleSource.PLAYERS_HANDBOOK_2024, "Gain proficiency with three Artisan's Tools and craft mundane items faster."),
    GeneralFeatType.CRUSHER: general_feat(GeneralFeatType.CRUSHER, RuleSource.TASHAS_CAULDRON_OF_EVERYTHING, "+1 Strength or Constitution; add control and critical riders to bludgeoning hits."),
    GeneralFeatType.DEFENSIVE_DUELIST: general_feat(GeneralFeatType.DEFENSIVE_DUELIST, RuleSource.PLAYERS_HANDBOOK_2024, "Use a reaction with a finesse weapon to add proficiency bonus to AC.", (ability_prerequisite(13, AbilityType.DEXTERITY),)),
    GeneralFeatType.DRAGON_FEAR: general_feat(GeneralFeatType.DRAGON_FEAR, RuleSource.XANATHARS_GUIDE_TO_EVERYTHING, "+1 Strength, Constitution, or Charisma; turn Breath Weapon into fear.", (species_prerequisite(SpeciesType.DRAGONBORN),)),
    GeneralFeatType.DRAGON_HIDE: general_feat(GeneralFeatType.DRAGON_HIDE, RuleSource.XANATHARS_GUIDE_TO_EVERYTHING, "+1 Strength, Constitution, or Charisma; gain natural armor and claws.", (species_prerequisite(SpeciesType.DRAGONBORN),)),
    GeneralFeatType.DROW_HIGH_MAGIC: general_feat(GeneralFeatType.DROW_HIGH_MAGIC, RuleSource.XANATHARS_GUIDE_TO_EVERYTHING, "Gain drow innate spells.", (species_prerequisite(SpeciesType.ELF),)),
    GeneralFeatType.DUAL_WIELDER: general_feat(GeneralFeatType.DUAL_WIELDER, RuleSource.PLAYERS_HANDBOOK_2024, "Improve AC, weapon options, and drawing weapons while dual wielding."),
    GeneralFeatType.DUNGEON_DELVER: general_feat(GeneralFeatType.DUNGEON_DELVER, RuleSource.PLAYERS_HANDBOOK_2024, "Improve trap detection, trap saves, and dungeon exploration."),
    GeneralFeatType.DURABLE: general_feat(GeneralFeatType.DURABLE, RuleSource.PLAYERS_HANDBOOK_2024, "+1 Constitution; improve healing from Hit Dice."),
    GeneralFeatType.DWARF_FORTITUDE: general_feat(GeneralFeatType.DWARF_FORTITUDE, RuleSource.XANATHARS_GUIDE_TO_EVERYTHING, "+1 Constitution; spend a Hit Die when taking the Dodge action.", (species_prerequisite(SpeciesType.DWARF),)),
    GeneralFeatType.ELDRITCH_ADEPT: general_feat(GeneralFeatType.ELDRITCH_ADEPT, RuleSource.TASHAS_CAULDRON_OF_EVERYTHING, "Learn one Eldritch Invocation.", (spellcasting_prerequisite(),)),
    GeneralFeatType.ELEMENTAL_ADEPT: general_feat(GeneralFeatType.ELEMENTAL_ADEPT, RuleSource.PLAYERS_HANDBOOK_2024, "Choose a damage type for spells to ignore resistance and improve low damage dice.", (spellcasting_prerequisite(),)),
    GeneralFeatType.ELVEN_ACCURACY: general_feat(GeneralFeatType.ELVEN_ACCURACY, RuleSource.XANATHARS_GUIDE_TO_EVERYTHING, "+1 Dexterity, Intelligence, Wisdom, or Charisma; improve advantaged attack rolls.", (species_prerequisite(SpeciesType.ELF),)),
    GeneralFeatType.EMBER_OF_THE_FIRE_GIANT: general_feat(GeneralFeatType.EMBER_OF_THE_FIRE_GIANT, RuleSource.GLORY_OF_THE_GIANTS, "+1 Strength, Constitution, or Wisdom; fire resistance and fire-blind burst.", (level_prerequisite(4), feat_prerequisite(GeneralFeatType.STRIKE_OF_THE_GIANTS, GiantStrikeType.FIRE_STRIKE))),
    GeneralFeatType.FADE_AWAY: general_feat(GeneralFeatType.FADE_AWAY, RuleSource.XANATHARS_GUIDE_TO_EVERYTHING, "+1 Dexterity or Intelligence; turn invisible after taking damage.", (species_prerequisite(SpeciesType.GNOME),)),
    GeneralFeatType.FEY_TELEPORTATION: general_feat(GeneralFeatType.FEY_TELEPORTATION, RuleSource.XANATHARS_GUIDE_TO_EVERYTHING, "+1 Intelligence or Charisma; gain Sylvan and misty step.", (species_prerequisite(SpeciesType.ELF),)),
    GeneralFeatType.FEY_TOUCHED: general_feat(GeneralFeatType.FEY_TOUCHED, RuleSource.TASHAS_CAULDRON_OF_EVERYTHING, "+1 Intelligence, Wisdom, or Charisma; learn misty step and another spell."),
    GeneralFeatType.FIGHTING_INITIATE: general_feat(GeneralFeatType.FIGHTING_INITIATE, RuleSource.TASHAS_CAULDRON_OF_EVERYTHING, "Learn one Fighting Style option from the fighter class.", (weapon_prerequisite(WeaponProficiencyType.MARTIAL),)),
    GeneralFeatType.FLAMES_OF_PHLEGETHOS: general_feat(GeneralFeatType.FLAMES_OF_PHLEGETHOS, RuleSource.XANATHARS_GUIDE_TO_EVERYTHING, "+1 Intelligence or Charisma; improve fire spells and fiery retaliation.", (species_prerequisite(SpeciesType.TIEFLING),)),
    GeneralFeatType.FURY_OF_THE_FROST_GIANT: general_feat(GeneralFeatType.FURY_OF_THE_FROST_GIANT, RuleSource.GLORY_OF_THE_GIANTS, "+1 Strength, Constitution, or Wisdom; cold resistance and frost retaliation.", (level_prerequisite(4), feat_prerequisite(GeneralFeatType.STRIKE_OF_THE_GIANTS, GiantStrikeType.FROST_STRIKE))),
    GeneralFeatType.GIFT_OF_THE_CHROMATIC_DRAGON: general_feat(GeneralFeatType.GIFT_OF_THE_CHROMATIC_DRAGON, RuleSource.FIZBANS_TREASURY_OF_DRAGONS, "Add elemental weapon damage and gain reactive elemental resistance."),
    GeneralFeatType.GIFT_OF_THE_GEM_DRAGON: general_feat(GeneralFeatType.GIFT_OF_THE_GEM_DRAGON, RuleSource.FIZBANS_TREASURY_OF_DRAGONS, "+1 Intelligence, Wisdom, or Charisma; telekinetic retaliation."),
    GeneralFeatType.GIFT_OF_THE_METALLIC_DRAGON: general_feat(GeneralFeatType.GIFT_OF_THE_METALLIC_DRAGON, RuleSource.FIZBANS_TREASURY_OF_DRAGONS, "Learn cure wounds and protect with a reactive AC bonus."),
    GeneralFeatType.GRAPPLER: general_feat(GeneralFeatType.GRAPPLER, RuleSource.SYSTEM_REFERENCE_DOCUMENT, "Improve attacks and restraint options against grappled creatures.", (ability_prerequisite(13, AbilityType.STRENGTH),)),
    GeneralFeatType.GREAT_WEAPON_MASTER: general_feat(GeneralFeatType.GREAT_WEAPON_MASTER, RuleSource.PLAYERS_HANDBOOK_2024, "Gain heavy-weapon damage tradeoffs and bonus attacks after key hits."),
    GeneralFeatType.GUILE_OF_THE_CLOUD_GIANT: general_feat(GeneralFeatType.GUILE_OF_THE_CLOUD_GIANT, RuleSource.GLORY_OF_THE_GIANTS, "+1 Strength, Constitution, or Wisdom; reduce damage and teleport.", (level_prerequisite(4), feat_prerequisite(GeneralFeatType.STRIKE_OF_THE_GIANTS, GiantStrikeType.CLOUD_STRIKE))),
    GeneralFeatType.GUNNER: general_feat(GeneralFeatType.GUNNER, RuleSource.TASHAS_CAULDRON_OF_EVERYTHING, "+1 Dexterity; firearm proficiency and improved firearm attacks."),
    GeneralFeatType.HEALER: general_feat(GeneralFeatType.HEALER, RuleSource.PLAYERS_HANDBOOK_2024, "Use a healer's kit to stabilize or restore hit points."),
    GeneralFeatType.HEAVILY_ARMORED: general_feat(GeneralFeatType.HEAVILY_ARMORED, RuleSource.PLAYERS_HANDBOOK_2024, "+1 Strength; gain heavy armor proficiency.", (armor_prerequisite(ArmorCategory.MEDIUM),)),
    GeneralFeatType.HEAVY_ARMOR_MASTER: general_feat(GeneralFeatType.HEAVY_ARMOR_MASTER, RuleSource.PLAYERS_HANDBOOK_2024, "+1 Strength; reduce mundane weapon damage while wearing heavy armor.", (armor_prerequisite(ArmorCategory.HEAVY),)),
    GeneralFeatType.INFERNAL_CONSTITUTION: general_feat(GeneralFeatType.INFERNAL_CONSTITUTION, RuleSource.XANATHARS_GUIDE_TO_EVERYTHING, "+1 Constitution; gain cold and poison resilience.", (species_prerequisite(SpeciesType.TIEFLING),)),
    GeneralFeatType.INSPIRING_LEADER: general_feat(GeneralFeatType.INSPIRING_LEADER, RuleSource.PLAYERS_HANDBOOK_2024, "Give temporary hit points to a small group after a speech.", (ability_prerequisite(13, AbilityType.CHARISMA),)),
    GeneralFeatType.KEEN_MIND: general_feat(GeneralFeatType.KEEN_MIND, RuleSource.PLAYERS_HANDBOOK_2024, "+1 Intelligence; improve recall and orientation."),
    GeneralFeatType.KEENNESS_OF_THE_STONE_GIANT: general_feat(GeneralFeatType.KEENNESS_OF_THE_STONE_GIANT, RuleSource.GLORY_OF_THE_GIANTS, "+1 Strength, Constitution, or Wisdom; darkvision and stone strike.", (level_prerequisite(4), feat_prerequisite(GeneralFeatType.STRIKE_OF_THE_GIANTS, GiantStrikeType.STONE_STRIKE))),
    GeneralFeatType.LIGHTLY_ARMORED: general_feat(GeneralFeatType.LIGHTLY_ARMORED, RuleSource.PLAYERS_HANDBOOK_2024, "+1 Strength or Dexterity; gain light armor proficiency."),
    GeneralFeatType.LINGUIST: general_feat(GeneralFeatType.LINGUIST, RuleSource.PLAYERS_HANDBOOK_2024, "+1 Intelligence; learn languages and make ciphers."),
    GeneralFeatType.LUCKY: general_feat(GeneralFeatType.LUCKY, RuleSource.PLAYERS_HANDBOOK_2024, "Spend luck points to affect d20 rolls."),
    GeneralFeatType.MAGE_SLAYER: general_feat(GeneralFeatType.MAGE_SLAYER, RuleSource.PLAYERS_HANDBOOK_2024, "Punish nearby spellcasters and resist close-range spells."),
    GeneralFeatType.MAGIC_INITIATE: general_feat(GeneralFeatType.MAGIC_INITIATE, RuleSource.PLAYERS_HANDBOOK_2024, "Learn two cantrips and one 1st-level spell from a class list."),
    GeneralFeatType.MARTIAL_ADEPT: general_feat(GeneralFeatType.MARTIAL_ADEPT, RuleSource.PLAYERS_HANDBOOK_2024, "Learn Battle Master maneuvers and gain a superiority die."),
    GeneralFeatType.MEDIUM_ARMOR_MASTER: general_feat(GeneralFeatType.MEDIUM_ARMOR_MASTER, RuleSource.PLAYERS_HANDBOOK_2024, "Improve medium armor stealth and Dexterity AC cap.", (armor_prerequisite(ArmorCategory.MEDIUM),)),
    GeneralFeatType.METAMAGIC_ADEPT: general_feat(GeneralFeatType.METAMAGIC_ADEPT, RuleSource.TASHAS_CAULDRON_OF_EVERYTHING, "Learn metamagic and gain sorcery points.", (spellcasting_prerequisite(),)),
    GeneralFeatType.MOBILE: general_feat(GeneralFeatType.MOBILE, RuleSource.PLAYERS_HANDBOOK_2024, "Increase speed and improve difficult-terrain dashes and skirmishing."),
    GeneralFeatType.MODERATELY_ARMORED: general_feat(GeneralFeatType.MODERATELY_ARMORED, RuleSource.PLAYERS_HANDBOOK_2024, "+1 Strength or Dexterity; gain medium armor and shield proficiency.", (armor_prerequisite(ArmorCategory.LIGHT),)),
    GeneralFeatType.MOUNTED_COMBATANT: general_feat(GeneralFeatType.MOUNTED_COMBATANT, RuleSource.PLAYERS_HANDBOOK_2024, "Improve mounted attacks and protect your mount."),
    GeneralFeatType.MUSICIAN: general_feat(GeneralFeatType.MUSICIAN, RuleSource.PLAYERS_HANDBOOK_2024, "Gain proficiency with three Musical Instruments and grant Heroic Inspiration after a Short or Long Rest."),
    GeneralFeatType.OBSERVANT: general_feat(GeneralFeatType.OBSERVANT, RuleSource.PLAYERS_HANDBOOK_2024, "+1 Intelligence or Wisdom; read lips and improve passive Investigation/Perception."),
    GeneralFeatType.ORCISH_FURY: general_feat(GeneralFeatType.ORCISH_FURY, RuleSource.XANATHARS_GUIDE_TO_EVERYTHING, "+1 Strength or Constitution; add weapon damage and retaliate after endurance.", (species_prerequisite(SpeciesType.ORC),)),
    GeneralFeatType.PIERCER: general_feat(GeneralFeatType.PIERCER, RuleSource.TASHAS_CAULDRON_OF_EVERYTHING, "+1 Strength or Dexterity; improve piercing damage dice and criticals."),
    GeneralFeatType.POISONER: general_feat(GeneralFeatType.POISONER, RuleSource.TASHAS_CAULDRON_OF_EVERYTHING, "Gain poisoner tools, faster poison application, and better poison attacks."),
    GeneralFeatType.POLEARM_MASTER: general_feat(GeneralFeatType.POLEARM_MASTER, RuleSource.PLAYERS_HANDBOOK_2024, "Make extra polearm attacks and opportunity attacks when foes enter reach."),
    GeneralFeatType.PRODIGY: general_feat(GeneralFeatType.PRODIGY, RuleSource.XANATHARS_GUIDE_TO_EVERYTHING, "Gain a skill, tool, language, and expertise.", (species_prerequisite(SpeciesType.HUMAN, SpeciesType.ORC, SpeciesType.ELF),)),
    GeneralFeatType.RESILIENT: general_feat(GeneralFeatType.RESILIENT, RuleSource.PLAYERS_HANDBOOK_2024, "+1 in one ability and proficiency in that ability's saving throws."),
    GeneralFeatType.RITUAL_CASTER: general_feat(GeneralFeatType.RITUAL_CASTER, RuleSource.PLAYERS_HANDBOOK_2024, "Gain a ritual book and cast ritual spells.", (ability_prerequisite(13, AbilityType.INTELLIGENCE, AbilityType.WISDOM),)),
    GeneralFeatType.RUNE_SHAPER: general_feat(GeneralFeatType.RUNE_SHAPER, RuleSource.GLORY_OF_THE_GIANTS, "Learn rune magic spells.", (feature_prerequisite(FeatCharacterFeatureType.SPELLCASTING, FeatCharacterFeatureType.RUNE_CARVER),)),
    GeneralFeatType.SAVAGE_ATTACKER: general_feat(GeneralFeatType.SAVAGE_ATTACKER, RuleSource.PLAYERS_HANDBOOK_2024, "Reroll melee weapon damage once per turn."),
    GeneralFeatType.SECOND_CHANCE: general_feat(GeneralFeatType.SECOND_CHANCE, RuleSource.XANATHARS_GUIDE_TO_EVERYTHING, "+1 Dexterity, Constitution, or Charisma; force an attacker to reroll.", (species_prerequisite(SpeciesType.HALFLING),)),
    GeneralFeatType.SENTINEL: general_feat(GeneralFeatType.SENTINEL, RuleSource.PLAYERS_HANDBOOK_2024, "Improve opportunity attacks and lock down nearby enemies."),
    GeneralFeatType.SHADOW_TOUCHED: general_feat(GeneralFeatType.SHADOW_TOUCHED, RuleSource.TASHAS_CAULDRON_OF_EVERYTHING, "+1 Intelligence, Wisdom, or Charisma; learn invisibility and another spell."),
    GeneralFeatType.SHARPSHOOTER: general_feat(GeneralFeatType.SHARPSHOOTER, RuleSource.PLAYERS_HANDBOOK_2024, "Ignore common ranged penalties and trade accuracy for damage."),
    GeneralFeatType.SHIELD_MASTER: general_feat(GeneralFeatType.SHIELD_MASTER, RuleSource.PLAYERS_HANDBOOK_2024, "Add shield tactics to attacks and Dexterity saves."),
    GeneralFeatType.SKILL_EXPERT: general_feat(GeneralFeatType.SKILL_EXPERT, RuleSource.TASHAS_CAULDRON_OF_EVERYTHING, "+1 in one ability; gain one skill proficiency and one expertise."),
    GeneralFeatType.SKILLED: general_feat(GeneralFeatType.SKILLED, RuleSource.PLAYERS_HANDBOOK_2024, "Gain proficiency with three skills or tools."),
    GeneralFeatType.SKULKER: general_feat(GeneralFeatType.SKULKER, RuleSource.PLAYERS_HANDBOOK_2024, "Improve hiding and ranged stealth.", (ability_prerequisite(13, AbilityType.DEXTERITY),)),
    GeneralFeatType.SLASHER: general_feat(GeneralFeatType.SLASHER, RuleSource.TASHAS_CAULDRON_OF_EVERYTHING, "+1 Strength or Dexterity; add control and critical riders to slashing hits."),
    GeneralFeatType.SOUL_OF_THE_STORM_GIANT: general_feat(GeneralFeatType.SOUL_OF_THE_STORM_GIANT, RuleSource.GLORY_OF_THE_GIANTS, "+1 Strength, Constitution, or Wisdom; lightning/thunder resilience and storm aura.", (level_prerequisite(4), feat_prerequisite(GeneralFeatType.STRIKE_OF_THE_GIANTS, GiantStrikeType.STORM_STRIKE))),
    GeneralFeatType.SPELL_SNIPER: general_feat(GeneralFeatType.SPELL_SNIPER, RuleSource.PLAYERS_HANDBOOK_2024, "Improve ranged spell attacks and learn an attack cantrip.", (spellcasting_prerequisite(),)),
    GeneralFeatType.SQUAT_NIMBLENESS: general_feat(GeneralFeatType.SQUAT_NIMBLENESS, RuleSource.XANATHARS_GUIDE_TO_EVERYTHING, "+1 Strength or Dexterity; improve speed and escape checks.", (species_or_size_prerequisite(SpeciesType.DWARF, sizes=(FeatSpeciesSize.SMALL,)),)),
    GeneralFeatType.STRIKE_OF_THE_GIANTS: general_feat(GeneralFeatType.STRIKE_OF_THE_GIANTS, RuleSource.GLORY_OF_THE_GIANTS, "Choose a giant strike option for extra weapon damage and riders.", (weapon_or_background_prerequisite(WeaponProficiencyType.MARTIAL, BackgroundPrerequisiteType.GIANT_FOUNDLING),)),
    GeneralFeatType.TAVERN_BRAWLER: general_feat(GeneralFeatType.TAVERN_BRAWLER, RuleSource.PLAYERS_HANDBOOK_2024, "+1 Strength or Constitution; improve improvised weapons, unarmed strikes, and grapples."),
    GeneralFeatType.TELEKINETIC: general_feat(GeneralFeatType.TELEKINETIC, RuleSource.TASHAS_CAULDRON_OF_EVERYTHING, "+1 Intelligence, Wisdom, or Charisma; improve mage hand and shove telekinetically."),
    GeneralFeatType.TELEPATHIC: general_feat(GeneralFeatType.TELEPATHIC, RuleSource.TASHAS_CAULDRON_OF_EVERYTHING, "+1 Intelligence, Wisdom, or Charisma; speak telepathically and cast detect thoughts."),
    GeneralFeatType.TOUGH: general_feat(GeneralFeatType.TOUGH, RuleSource.PLAYERS_HANDBOOK_2024, "Increase hit point maximum by 2 per level."),
    GeneralFeatType.VIGOR_OF_THE_HILL_GIANT: general_feat(GeneralFeatType.VIGOR_OF_THE_HILL_GIANT, RuleSource.GLORY_OF_THE_GIANTS, "+1 Strength, Constitution, or Wisdom; improve prone resistance and Hit Dice healing.", (level_prerequisite(4), feat_prerequisite(GeneralFeatType.STRIKE_OF_THE_GIANTS, GiantStrikeType.HILL_STRIKE))),
    GeneralFeatType.WAR_CASTER: general_feat(GeneralFeatType.WAR_CASTER, RuleSource.PLAYERS_HANDBOOK_2024, "Improve concentration saves, somatic casting, and reaction spellcasting.", (spellcasting_prerequisite(),)),
    GeneralFeatType.WEAPON_MASTER: general_feat(GeneralFeatType.WEAPON_MASTER, RuleSource.PLAYERS_HANDBOOK_2024, "+1 Strength or Dexterity; gain weapon proficiencies."),
    GeneralFeatType.WOOD_ELF_MAGIC: general_feat(GeneralFeatType.WOOD_ELF_MAGIC, RuleSource.XANATHARS_GUIDE_TO_EVERYTHING, "Learn druid magic and wood elf spells.", (species_prerequisite(SpeciesType.ELF),)),
}

SUPPLEMENTAL_2024_FEATS: dict[GeneralFeatType, GeneralFeatDefinition] = {
    GeneralFeatType.SHARP_EYE: general_feat(GeneralFeatType.SHARP_EYE, RuleSource.PLAYERS_HANDBOOK_2024, 'Sharp Eye 2024 Origin feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', category=FeatCategory.ORIGIN),
    GeneralFeatType.SURVIVOR: general_feat(GeneralFeatType.SURVIVOR, RuleSource.PLAYERS_HANDBOOK_2024, 'Survivor 2024 Origin feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', category=FeatCategory.ORIGIN),
    GeneralFeatType.CULT_OF_THE_DRAGON_INITIATE: general_feat(GeneralFeatType.CULT_OF_THE_DRAGON_INITIATE, RuleSource.FORGOTTEN_REALMS_HEROES_OF_FAERUN_2024, 'Cult of the Dragon Initiate 2024 Origin feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', category=FeatCategory.ORIGIN),
    GeneralFeatType.EMERALD_ENCLAVE_FLEDGLING: general_feat(GeneralFeatType.EMERALD_ENCLAVE_FLEDGLING, RuleSource.FORGOTTEN_REALMS_HEROES_OF_FAERUN_2024, 'Emerald Enclave Fledgling 2024 Origin feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', category=FeatCategory.ORIGIN),
    GeneralFeatType.HARPER_AGENT: general_feat(GeneralFeatType.HARPER_AGENT, RuleSource.FORGOTTEN_REALMS_HEROES_OF_FAERUN_2024, 'Harper Agent 2024 Origin feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', category=FeatCategory.ORIGIN),
    GeneralFeatType.LORDS_ALLIANCE_AGENT: general_feat(GeneralFeatType.LORDS_ALLIANCE_AGENT, RuleSource.FORGOTTEN_REALMS_HEROES_OF_FAERUN_2024, "Lords' Alliance Agent 2024 Origin feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.", category=FeatCategory.ORIGIN),
    GeneralFeatType.PURPLE_DRAGON_ROOK: general_feat(GeneralFeatType.PURPLE_DRAGON_ROOK, RuleSource.FORGOTTEN_REALMS_HEROES_OF_FAERUN_2024, 'Purple Dragon Rook 2024 Origin feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', category=FeatCategory.ORIGIN),
    GeneralFeatType.SPELLFIRE_SPARK: general_feat(GeneralFeatType.SPELLFIRE_SPARK, RuleSource.FORGOTTEN_REALMS_HEROES_OF_FAERUN_2024, 'Spellfire Spark 2024 Origin feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', category=FeatCategory.ORIGIN),
    GeneralFeatType.TYRO_OF_THE_GAUNTLET: general_feat(GeneralFeatType.TYRO_OF_THE_GAUNTLET, RuleSource.FORGOTTEN_REALMS_HEROES_OF_FAERUN_2024, 'Tyro of the Gauntlet 2024 Origin feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', category=FeatCategory.ORIGIN),
    GeneralFeatType.ZHENTARIM_RUFFIAN: general_feat(GeneralFeatType.ZHENTARIM_RUFFIAN, RuleSource.FORGOTTEN_REALMS_HEROES_OF_FAERUN_2024, 'Zhentarim Ruffian 2024 Origin feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', category=FeatCategory.ORIGIN),
    GeneralFeatType.CHILD_OF_THE_SUN: general_feat(GeneralFeatType.CHILD_OF_THE_SUN, RuleSource.DND_BEYOND_DROPS_2026, 'Child of the Sun 2024 Origin feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', category=FeatCategory.ORIGIN),
    GeneralFeatType.SHADOWMOOR_HEXER: general_feat(GeneralFeatType.SHADOWMOOR_HEXER, RuleSource.DND_BEYOND_DROPS_2026, 'Shadowmoor Hexer 2024 Origin feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', category=FeatCategory.ORIGIN),
    GeneralFeatType.TIRELESS_REVELER: general_feat(GeneralFeatType.TIRELESS_REVELER, RuleSource.DND_BEYOND_DROPS_2026, 'Tireless Reveler 2024 Origin feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', category=FeatCategory.ORIGIN),
    GeneralFeatType.VAMPIRE_HUNTER: general_feat(GeneralFeatType.VAMPIRE_HUNTER, RuleSource.DND_BEYOND_DROPS_2026, 'Vampire Hunter 2024 Origin feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', category=FeatCategory.ORIGIN),
    GeneralFeatType.VAMPIRE_S_PLAYTHING: general_feat(GeneralFeatType.VAMPIRE_S_PLAYTHING, RuleSource.DND_BEYOND_DROPS_2026, "Vampire's Plaything 2024 Origin feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.", category=FeatCategory.ORIGIN),
    GeneralFeatType.ABILITY_SCORE_IMPROVEMENT: general_feat(GeneralFeatType.ABILITY_SCORE_IMPROVEMENT, RuleSource.PLAYERS_HANDBOOK_2024, 'Ability Score Improvement 2024 General feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', (level_prerequisite(4),), category=FeatCategory.GENERAL),
    GeneralFeatType.MARTIAL_WEAPON_TRAINING: general_feat(GeneralFeatType.MARTIAL_WEAPON_TRAINING, RuleSource.PLAYERS_HANDBOOK_2024, 'Martial Weapon Training 2024 General feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', (level_prerequisite(4),), category=FeatCategory.GENERAL),
    GeneralFeatType.SHIFTING_COMBATANT: general_feat(GeneralFeatType.SHIFTING_COMBATANT, RuleSource.PLAYERS_HANDBOOK_2024, 'Shifting Combatant 2024 General feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', (level_prerequisite(4),), category=FeatCategory.GENERAL),
    GeneralFeatType.SPEEDY: general_feat(GeneralFeatType.SPEEDY, RuleSource.PLAYERS_HANDBOOK_2024, 'Speedy 2024 General feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', (level_prerequisite(4),), category=FeatCategory.GENERAL),
    GeneralFeatType.TACTICAL_COMBATANT: general_feat(GeneralFeatType.TACTICAL_COMBATANT, RuleSource.PLAYERS_HANDBOOK_2024, 'Tactical Combatant 2024 General feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', (level_prerequisite(4),), category=FeatCategory.GENERAL),
    GeneralFeatType.COLD_CASTER: general_feat(GeneralFeatType.COLD_CASTER, RuleSource.FORGOTTEN_REALMS_HEROES_OF_FAERUN_2024, 'Cold Caster 2024 General feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', (level_prerequisite(4),), category=FeatCategory.GENERAL),
    GeneralFeatType.DRAGONSCARRED: general_feat(GeneralFeatType.DRAGONSCARRED, RuleSource.FORGOTTEN_REALMS_HEROES_OF_FAERUN_2024, 'Dragonscarred 2024 General feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', (level_prerequisite(4),), category=FeatCategory.GENERAL),
    GeneralFeatType.ENCLAVE_MAGIC: general_feat(GeneralFeatType.ENCLAVE_MAGIC, RuleSource.FORGOTTEN_REALMS_HEROES_OF_FAERUN_2024, 'Enclave Magic 2024 General feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', (level_prerequisite(4),), category=FeatCategory.GENERAL),
    GeneralFeatType.FAIRY_TRICKSTER: general_feat(GeneralFeatType.FAIRY_TRICKSTER, RuleSource.FORGOTTEN_REALMS_HEROES_OF_FAERUN_2024, 'Fairy Trickster 2024 General feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', (level_prerequisite(4),), category=FeatCategory.GENERAL),
    GeneralFeatType.GENIE_MAGIC: general_feat(GeneralFeatType.GENIE_MAGIC, RuleSource.FORGOTTEN_REALMS_HEROES_OF_FAERUN_2024, 'Genie Magic 2024 General feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', (level_prerequisite(4),), category=FeatCategory.GENERAL),
    GeneralFeatType.HARPER_TEAMWORK: general_feat(GeneralFeatType.HARPER_TEAMWORK, RuleSource.FORGOTTEN_REALMS_HEROES_OF_FAERUN_2024, 'Harper Teamwork 2024 General feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', (level_prerequisite(4),), category=FeatCategory.GENERAL),
    GeneralFeatType.LORDLY_RESOLVE: general_feat(GeneralFeatType.LORDLY_RESOLVE, RuleSource.FORGOTTEN_REALMS_HEROES_OF_FAERUN_2024, 'Lordly Resolve 2024 General feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', (level_prerequisite(4),), category=FeatCategory.GENERAL),
    GeneralFeatType.MYTHAL_TOUCHED: general_feat(GeneralFeatType.MYTHAL_TOUCHED, RuleSource.FORGOTTEN_REALMS_HEROES_OF_FAERUN_2024, 'Mythal Touched 2024 General feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', (level_prerequisite(4),), category=FeatCategory.GENERAL),
    GeneralFeatType.ORDER_S_RESILIENCE: general_feat(GeneralFeatType.ORDER_S_RESILIENCE, RuleSource.FORGOTTEN_REALMS_HEROES_OF_FAERUN_2024, "Order's Resilience 2024 General feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.", (level_prerequisite(4),), category=FeatCategory.GENERAL),
    GeneralFeatType.PURPLE_DRAGON_COMMANDANT: general_feat(GeneralFeatType.PURPLE_DRAGON_COMMANDANT, RuleSource.FORGOTTEN_REALMS_HEROES_OF_FAERUN_2024, 'Purple Dragon Commandant 2024 General feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', (level_prerequisite(4),), category=FeatCategory.GENERAL),
    GeneralFeatType.SPELLFIRE_ADEPT: general_feat(GeneralFeatType.SPELLFIRE_ADEPT, RuleSource.FORGOTTEN_REALMS_HEROES_OF_FAERUN_2024, 'Spellfire Adept 2024 General feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', (level_prerequisite(4),), category=FeatCategory.GENERAL),
    GeneralFeatType.STREET_JUSTICE: general_feat(GeneralFeatType.STREET_JUSTICE, RuleSource.FORGOTTEN_REALMS_HEROES_OF_FAERUN_2024, 'Street Justice 2024 General feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', (level_prerequisite(4),), category=FeatCategory.GENERAL),
    GeneralFeatType.ZHENTARIM_TACTICS: general_feat(GeneralFeatType.ZHENTARIM_TACTICS, RuleSource.FORGOTTEN_REALMS_HEROES_OF_FAERUN_2024, 'Zhentarim Tactics 2024 General feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', (level_prerequisite(4),), category=FeatCategory.GENERAL),
    GeneralFeatType.BLOODLUST: general_feat(GeneralFeatType.BLOODLUST, RuleSource.RAVENLOFT_THE_HORRORS_WITHIN_2024, 'Bloodlust 2024 General feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', (level_prerequisite(4),), category=FeatCategory.GENERAL),
    GeneralFeatType.BOMBER: general_feat(GeneralFeatType.BOMBER, RuleSource.RAVENLOFT_THE_HORRORS_WITHIN_2024, 'Bomber 2024 General feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', (level_prerequisite(4),), category=FeatCategory.GENERAL),
    GeneralFeatType.CLOYING_MISTS: general_feat(GeneralFeatType.CLOYING_MISTS, RuleSource.RAVENLOFT_THE_HORRORS_WITHIN_2024, 'Cloying Mists 2024 General feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', (level_prerequisite(4),), category=FeatCategory.GENERAL),
    GeneralFeatType.DELICIOUS_PAIN: general_feat(GeneralFeatType.DELICIOUS_PAIN, RuleSource.RAVENLOFT_THE_HORRORS_WITHIN_2024, 'Delicious Pain 2024 General feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', (level_prerequisite(4),), category=FeatCategory.GENERAL),
    GeneralFeatType.LIGHT_BRINGER: general_feat(GeneralFeatType.LIGHT_BRINGER, RuleSource.RAVENLOFT_THE_HORRORS_WITHIN_2024, 'Light Bringer 2024 General feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', (level_prerequisite(4),), category=FeatCategory.GENERAL),
    GeneralFeatType.LOVE_BITES: general_feat(GeneralFeatType.LOVE_BITES, RuleSource.RAVENLOFT_THE_HORRORS_WITHIN_2024, 'Love Bites 2024 General feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', (level_prerequisite(4),), category=FeatCategory.GENERAL),
    GeneralFeatType.PUTREFY: general_feat(GeneralFeatType.PUTREFY, RuleSource.RAVENLOFT_THE_HORRORS_WITHIN_2024, 'Putrefy 2024 General feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', (level_prerequisite(4),), category=FeatCategory.GENERAL),
    GeneralFeatType.REBUKE: general_feat(GeneralFeatType.REBUKE, RuleSource.RAVENLOFT_THE_HORRORS_WITHIN_2024, 'Rebuke 2024 General feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', (level_prerequisite(4),), category=FeatCategory.GENERAL),
    GeneralFeatType.TREACHEROUS_ALLURE: general_feat(GeneralFeatType.TREACHEROUS_ALLURE, RuleSource.RAVENLOFT_THE_HORRORS_WITHIN_2024, 'Treacherous Allure 2024 General feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', (level_prerequisite(4),), category=FeatCategory.GENERAL),
    GeneralFeatType.VAMPIRE_TOUCHED: general_feat(GeneralFeatType.VAMPIRE_TOUCHED, RuleSource.RAVENLOFT_THE_HORRORS_WITHIN_2024, 'Vampire Touched 2024 General feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', (level_prerequisite(4),), category=FeatCategory.GENERAL),
    GeneralFeatType.BOON_OF_COMBAT_PROWESS: general_feat(GeneralFeatType.BOON_OF_COMBAT_PROWESS, RuleSource.PLAYERS_HANDBOOK_2024, 'Boon of Combat Prowess 2024 Epic Boon feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', (level_prerequisite(19),), category=FeatCategory.EPIC_BOON),
    GeneralFeatType.BOON_OF_DIMENSIONAL_TRAVEL: general_feat(GeneralFeatType.BOON_OF_DIMENSIONAL_TRAVEL, RuleSource.PLAYERS_HANDBOOK_2024, 'Boon of Dimensional Travel 2024 Epic Boon feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', (level_prerequisite(19),), category=FeatCategory.EPIC_BOON),
    GeneralFeatType.BOON_OF_ENERGY_RESISTANCE: general_feat(GeneralFeatType.BOON_OF_ENERGY_RESISTANCE, RuleSource.PLAYERS_HANDBOOK_2024, 'Boon of Energy Resistance 2024 Epic Boon feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', (level_prerequisite(19),), category=FeatCategory.EPIC_BOON),
    GeneralFeatType.BOON_OF_FATE: general_feat(GeneralFeatType.BOON_OF_FATE, RuleSource.PLAYERS_HANDBOOK_2024, 'Boon of Fate 2024 Epic Boon feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', (level_prerequisite(19),), category=FeatCategory.EPIC_BOON),
    GeneralFeatType.BOON_OF_FORTITUDE: general_feat(GeneralFeatType.BOON_OF_FORTITUDE, RuleSource.PLAYERS_HANDBOOK_2024, 'Boon of Fortitude 2024 Epic Boon feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', (level_prerequisite(19),), category=FeatCategory.EPIC_BOON),
    GeneralFeatType.BOON_OF_IRRESISTIBLE_OFFENSE: general_feat(GeneralFeatType.BOON_OF_IRRESISTIBLE_OFFENSE, RuleSource.PLAYERS_HANDBOOK_2024, 'Boon of Irresistible Offense 2024 Epic Boon feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', (level_prerequisite(19),), category=FeatCategory.EPIC_BOON),
    GeneralFeatType.BOON_OF_RECOVERY: general_feat(GeneralFeatType.BOON_OF_RECOVERY, RuleSource.PLAYERS_HANDBOOK_2024, 'Boon of Recovery 2024 Epic Boon feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', (level_prerequisite(19),), category=FeatCategory.EPIC_BOON),
    GeneralFeatType.BOON_OF_SKILL: general_feat(GeneralFeatType.BOON_OF_SKILL, RuleSource.PLAYERS_HANDBOOK_2024, 'Boon of Skill 2024 Epic Boon feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', (level_prerequisite(19),), category=FeatCategory.EPIC_BOON),
    GeneralFeatType.BOON_OF_SPEED: general_feat(GeneralFeatType.BOON_OF_SPEED, RuleSource.PLAYERS_HANDBOOK_2024, 'Boon of Speed 2024 Epic Boon feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', (level_prerequisite(19),), category=FeatCategory.EPIC_BOON),
    GeneralFeatType.BOON_OF_SPELL_RECALL: general_feat(GeneralFeatType.BOON_OF_SPELL_RECALL, RuleSource.PLAYERS_HANDBOOK_2024, 'Boon of Spell Recall 2024 Epic Boon feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', (level_prerequisite(19),), category=FeatCategory.EPIC_BOON),
    GeneralFeatType.BOON_OF_THE_NIGHT_SPIRIT: general_feat(GeneralFeatType.BOON_OF_THE_NIGHT_SPIRIT, RuleSource.PLAYERS_HANDBOOK_2024, 'Boon of the Night Spirit 2024 Epic Boon feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', (level_prerequisite(19),), category=FeatCategory.EPIC_BOON),
    GeneralFeatType.BOON_OF_TRUESIGHT: general_feat(GeneralFeatType.BOON_OF_TRUESIGHT, RuleSource.PLAYERS_HANDBOOK_2024, 'Boon of Truesight 2024 Epic Boon feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', (level_prerequisite(19),), category=FeatCategory.EPIC_BOON),
    GeneralFeatType.BOON_OF_SIBERYS: general_feat(GeneralFeatType.BOON_OF_SIBERYS, RuleSource.EBERRON_FORGE_OF_THE_ARTIFICER_2024, 'Boon of Siberys 2024 Epic Boon feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', (level_prerequisite(19),), category=FeatCategory.EPIC_BOON),
    GeneralFeatType.BOON_OF_BLOODSHED: general_feat(GeneralFeatType.BOON_OF_BLOODSHED, RuleSource.FORGOTTEN_REALMS_HEROES_OF_FAERUN_2024, 'Boon of Bloodshed 2024 Epic Boon feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', (level_prerequisite(19),), category=FeatCategory.EPIC_BOON),
    GeneralFeatType.BOON_OF_BOUNTIFUL_HEALTH: general_feat(GeneralFeatType.BOON_OF_BOUNTIFUL_HEALTH, RuleSource.FORGOTTEN_REALMS_HEROES_OF_FAERUN_2024, 'Boon of Bountiful Health 2024 Epic Boon feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', (level_prerequisite(19),), category=FeatCategory.EPIC_BOON),
    GeneralFeatType.BOON_OF_COMMUNICATION: general_feat(GeneralFeatType.BOON_OF_COMMUNICATION, RuleSource.FORGOTTEN_REALMS_HEROES_OF_FAERUN_2024, 'Boon of Communication 2024 Epic Boon feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', (level_prerequisite(19),), category=FeatCategory.EPIC_BOON),
    GeneralFeatType.BOON_OF_DESPERATE_RESILIENCE: general_feat(GeneralFeatType.BOON_OF_DESPERATE_RESILIENCE, RuleSource.FORGOTTEN_REALMS_HEROES_OF_FAERUN_2024, 'Boon of Desperate Resilience 2024 Epic Boon feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', (level_prerequisite(19),), category=FeatCategory.EPIC_BOON),
    GeneralFeatType.BOON_OF_EXQUISITE_RADIANCE: general_feat(GeneralFeatType.BOON_OF_EXQUISITE_RADIANCE, RuleSource.FORGOTTEN_REALMS_HEROES_OF_FAERUN_2024, 'Boon of Exquisite Radiance 2024 Epic Boon feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', (level_prerequisite(19),), category=FeatCategory.EPIC_BOON),
    GeneralFeatType.BOON_OF_FLUID_FORMS: general_feat(GeneralFeatType.BOON_OF_FLUID_FORMS, RuleSource.FORGOTTEN_REALMS_HEROES_OF_FAERUN_2024, 'Boon of Fluid Forms 2024 Epic Boon feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', (level_prerequisite(19),), category=FeatCategory.EPIC_BOON),
    GeneralFeatType.BOON_OF_FORTUNE_S_FAVOR: general_feat(GeneralFeatType.BOON_OF_FORTUNE_S_FAVOR, RuleSource.FORGOTTEN_REALMS_HEROES_OF_FAERUN_2024, "Boon of Fortune's Favor 2024 Epic Boon feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.", (level_prerequisite(19),), category=FeatCategory.EPIC_BOON),
    GeneralFeatType.BOON_OF_POISON_MASTERY: general_feat(GeneralFeatType.BOON_OF_POISON_MASTERY, RuleSource.FORGOTTEN_REALMS_HEROES_OF_FAERUN_2024, 'Boon of Poison Mastery 2024 Epic Boon feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', (level_prerequisite(19),), category=FeatCategory.EPIC_BOON),
    GeneralFeatType.BOON_OF_REVELRY: general_feat(GeneralFeatType.BOON_OF_REVELRY, RuleSource.FORGOTTEN_REALMS_HEROES_OF_FAERUN_2024, 'Boon of Revelry 2024 Epic Boon feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', (level_prerequisite(19),), category=FeatCategory.EPIC_BOON),
    GeneralFeatType.BOON_OF_TERROR: general_feat(GeneralFeatType.BOON_OF_TERROR, RuleSource.FORGOTTEN_REALMS_HEROES_OF_FAERUN_2024, 'Boon of Terror 2024 Epic Boon feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', (level_prerequisite(19),), category=FeatCategory.EPIC_BOON),
    GeneralFeatType.BOON_OF_THE_BRIGHT_SUN: general_feat(GeneralFeatType.BOON_OF_THE_BRIGHT_SUN, RuleSource.FORGOTTEN_REALMS_HEROES_OF_FAERUN_2024, 'Boon of the Bright Sun 2024 Epic Boon feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', (level_prerequisite(19),), category=FeatCategory.EPIC_BOON),
    GeneralFeatType.BOON_OF_THE_FURIOUS_STORM: general_feat(GeneralFeatType.BOON_OF_THE_FURIOUS_STORM, RuleSource.FORGOTTEN_REALMS_HEROES_OF_FAERUN_2024, 'Boon of the Furious Storm 2024 Epic Boon feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', (level_prerequisite(19),), category=FeatCategory.EPIC_BOON),
    GeneralFeatType.BOON_OF_THE_SOUL_DRINKER: general_feat(GeneralFeatType.BOON_OF_THE_SOUL_DRINKER, RuleSource.FORGOTTEN_REALMS_HEROES_OF_FAERUN_2024, 'Boon of the Soul Drinker 2024 Epic Boon feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', (level_prerequisite(19),), category=FeatCategory.EPIC_BOON),
    GeneralFeatType.BOON_OF_BLAZING_DAWN: general_feat(GeneralFeatType.BOON_OF_BLAZING_DAWN, RuleSource.DND_BEYOND_DROPS_2026, 'Boon of Blazing Dawn 2024 Epic Boon feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', (level_prerequisite(19),), category=FeatCategory.EPIC_BOON),
    GeneralFeatType.BOON_OF_LOOMING_SHADOWS: general_feat(GeneralFeatType.BOON_OF_LOOMING_SHADOWS, RuleSource.DND_BEYOND_DROPS_2026, 'Boon of Looming Shadows 2024 Epic Boon feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', (level_prerequisite(19),), category=FeatCategory.EPIC_BOON),
    GeneralFeatType.BOON_OF_MISTY_ESCAPE: general_feat(GeneralFeatType.BOON_OF_MISTY_ESCAPE, RuleSource.DND_BEYOND_DROPS_2026, 'Boon of Misty Escape 2024 Epic Boon feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', (level_prerequisite(19),), category=FeatCategory.EPIC_BOON),
    GeneralFeatType.ABERRANT_DRAGONMARK: general_feat(GeneralFeatType.ABERRANT_DRAGONMARK, RuleSource.EBERRON_FORGE_OF_THE_ARTIFICER_2024, 'Aberrant Dragonmark 2024 Dragonmark feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', category=FeatCategory.DRAGONMARK),
    GeneralFeatType.MARK_OF_DETECTION: general_feat(GeneralFeatType.MARK_OF_DETECTION, RuleSource.EBERRON_FORGE_OF_THE_ARTIFICER_2024, 'Mark of Detection 2024 Dragonmark feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', category=FeatCategory.DRAGONMARK),
    GeneralFeatType.MARK_OF_FINDING: general_feat(GeneralFeatType.MARK_OF_FINDING, RuleSource.EBERRON_FORGE_OF_THE_ARTIFICER_2024, 'Mark of Finding 2024 Dragonmark feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', category=FeatCategory.DRAGONMARK),
    GeneralFeatType.MARK_OF_HANDLING: general_feat(GeneralFeatType.MARK_OF_HANDLING, RuleSource.EBERRON_FORGE_OF_THE_ARTIFICER_2024, 'Mark of Handling 2024 Dragonmark feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', category=FeatCategory.DRAGONMARK),
    GeneralFeatType.MARK_OF_HEALING: general_feat(GeneralFeatType.MARK_OF_HEALING, RuleSource.EBERRON_FORGE_OF_THE_ARTIFICER_2024, 'Mark of Healing 2024 Dragonmark feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', category=FeatCategory.DRAGONMARK),
    GeneralFeatType.MARK_OF_HOSPITALITY: general_feat(GeneralFeatType.MARK_OF_HOSPITALITY, RuleSource.EBERRON_FORGE_OF_THE_ARTIFICER_2024, 'Mark of Hospitality 2024 Dragonmark feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', category=FeatCategory.DRAGONMARK),
    GeneralFeatType.MARK_OF_MAKING: general_feat(GeneralFeatType.MARK_OF_MAKING, RuleSource.EBERRON_FORGE_OF_THE_ARTIFICER_2024, 'Mark of Making 2024 Dragonmark feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', category=FeatCategory.DRAGONMARK),
    GeneralFeatType.MARK_OF_PASSAGE: general_feat(GeneralFeatType.MARK_OF_PASSAGE, RuleSource.EBERRON_FORGE_OF_THE_ARTIFICER_2024, 'Mark of Passage 2024 Dragonmark feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', category=FeatCategory.DRAGONMARK),
    GeneralFeatType.MARK_OF_SCRIBING: general_feat(GeneralFeatType.MARK_OF_SCRIBING, RuleSource.EBERRON_FORGE_OF_THE_ARTIFICER_2024, 'Mark of Scribing 2024 Dragonmark feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', category=FeatCategory.DRAGONMARK),
    GeneralFeatType.MARK_OF_SENTINEL: general_feat(GeneralFeatType.MARK_OF_SENTINEL, RuleSource.EBERRON_FORGE_OF_THE_ARTIFICER_2024, 'Mark of Sentinel 2024 Dragonmark feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', category=FeatCategory.DRAGONMARK),
    GeneralFeatType.MARK_OF_SHADOW: general_feat(GeneralFeatType.MARK_OF_SHADOW, RuleSource.EBERRON_FORGE_OF_THE_ARTIFICER_2024, 'Mark of Shadow 2024 Dragonmark feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', category=FeatCategory.DRAGONMARK),
    GeneralFeatType.MARK_OF_STORM: general_feat(GeneralFeatType.MARK_OF_STORM, RuleSource.EBERRON_FORGE_OF_THE_ARTIFICER_2024, 'Mark of Storm 2024 Dragonmark feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', category=FeatCategory.DRAGONMARK),
    GeneralFeatType.MARK_OF_WARDING: general_feat(GeneralFeatType.MARK_OF_WARDING, RuleSource.EBERRON_FORGE_OF_THE_ARTIFICER_2024, 'Mark of Warding 2024 Dragonmark feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', category=FeatCategory.DRAGONMARK),
    GeneralFeatType.GREATER_ABERRANT_MARK: general_feat(GeneralFeatType.GREATER_ABERRANT_MARK, RuleSource.EBERRON_FORGE_OF_THE_ARTIFICER_2024, 'Greater Aberrant Mark 2024 Greater Dragonmark feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', category=FeatCategory.GREATER_DRAGONMARK),
    GeneralFeatType.GREATER_MARK_OF_DETECTION: general_feat(GeneralFeatType.GREATER_MARK_OF_DETECTION, RuleSource.EBERRON_FORGE_OF_THE_ARTIFICER_2024, 'Greater Mark of Detection 2024 Greater Dragonmark feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', category=FeatCategory.GREATER_DRAGONMARK),
    GeneralFeatType.GREATER_MARK_OF_FINDING: general_feat(GeneralFeatType.GREATER_MARK_OF_FINDING, RuleSource.EBERRON_FORGE_OF_THE_ARTIFICER_2024, 'Greater Mark of Finding 2024 Greater Dragonmark feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', category=FeatCategory.GREATER_DRAGONMARK),
    GeneralFeatType.GREATER_MARK_OF_HANDLING: general_feat(GeneralFeatType.GREATER_MARK_OF_HANDLING, RuleSource.EBERRON_FORGE_OF_THE_ARTIFICER_2024, 'Greater Mark of Handling 2024 Greater Dragonmark feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', category=FeatCategory.GREATER_DRAGONMARK),
    GeneralFeatType.GREATER_MARK_OF_HEALING: general_feat(GeneralFeatType.GREATER_MARK_OF_HEALING, RuleSource.EBERRON_FORGE_OF_THE_ARTIFICER_2024, 'Greater Mark of Healing 2024 Greater Dragonmark feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', category=FeatCategory.GREATER_DRAGONMARK),
    GeneralFeatType.GREATER_MARK_OF_HOSPITALITY: general_feat(GeneralFeatType.GREATER_MARK_OF_HOSPITALITY, RuleSource.EBERRON_FORGE_OF_THE_ARTIFICER_2024, 'Greater Mark of Hospitality 2024 Greater Dragonmark feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', category=FeatCategory.GREATER_DRAGONMARK),
    GeneralFeatType.GREATER_MARK_OF_MAKING: general_feat(GeneralFeatType.GREATER_MARK_OF_MAKING, RuleSource.EBERRON_FORGE_OF_THE_ARTIFICER_2024, 'Greater Mark of Making 2024 Greater Dragonmark feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', category=FeatCategory.GREATER_DRAGONMARK),
    GeneralFeatType.GREATER_MARK_OF_PASSAGE: general_feat(GeneralFeatType.GREATER_MARK_OF_PASSAGE, RuleSource.EBERRON_FORGE_OF_THE_ARTIFICER_2024, 'Greater Mark of Passage 2024 Greater Dragonmark feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', category=FeatCategory.GREATER_DRAGONMARK),
    GeneralFeatType.GREATER_MARK_OF_SCRIBING: general_feat(GeneralFeatType.GREATER_MARK_OF_SCRIBING, RuleSource.EBERRON_FORGE_OF_THE_ARTIFICER_2024, 'Greater Mark of Scribing 2024 Greater Dragonmark feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', category=FeatCategory.GREATER_DRAGONMARK),
    GeneralFeatType.GREATER_MARK_OF_SENTINEL: general_feat(GeneralFeatType.GREATER_MARK_OF_SENTINEL, RuleSource.EBERRON_FORGE_OF_THE_ARTIFICER_2024, 'Greater Mark of Sentinel 2024 Greater Dragonmark feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', category=FeatCategory.GREATER_DRAGONMARK),
    GeneralFeatType.GREATER_MARK_OF_SHADOW: general_feat(GeneralFeatType.GREATER_MARK_OF_SHADOW, RuleSource.EBERRON_FORGE_OF_THE_ARTIFICER_2024, 'Greater Mark of Shadow 2024 Greater Dragonmark feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', category=FeatCategory.GREATER_DRAGONMARK),
    GeneralFeatType.GREATER_MARK_OF_STORM: general_feat(GeneralFeatType.GREATER_MARK_OF_STORM, RuleSource.EBERRON_FORGE_OF_THE_ARTIFICER_2024, 'Greater Mark of Storm 2024 Greater Dragonmark feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', category=FeatCategory.GREATER_DRAGONMARK),
    GeneralFeatType.GREATER_MARK_OF_WARDING: general_feat(GeneralFeatType.GREATER_MARK_OF_WARDING, RuleSource.EBERRON_FORGE_OF_THE_ARTIFICER_2024, 'Greater Mark of Warding 2024 Greater Dragonmark feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', category=FeatCategory.GREATER_DRAGONMARK),
    GeneralFeatType.POTENT_DRAGONMARK: general_feat(GeneralFeatType.POTENT_DRAGONMARK, RuleSource.EBERRON_FORGE_OF_THE_ARTIFICER_2024, 'Potent Dragonmark 2024 Greater Dragonmark feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', category=FeatCategory.GREATER_DRAGONMARK),
    GeneralFeatType.FEY_PACT: general_feat(GeneralFeatType.FEY_PACT, RuleSource.DND_BEYOND_DROPS_2026, 'Fey Pact 2024 Planar Pact feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', category=FeatCategory.PLANAR_PACT),
    GeneralFeatType.INFERNAL_PACT: general_feat(GeneralFeatType.INFERNAL_PACT, RuleSource.DND_BEYOND_DROPS_2026, 'Infernal Pact 2024 Planar Pact feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', category=FeatCategory.PLANAR_PACT),
    GeneralFeatType.FEY_SENTINEL: general_feat(GeneralFeatType.FEY_SENTINEL, RuleSource.DND_BEYOND_DROPS_2026, 'Fey Sentinel 2024 Greater Planar Pact feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', category=FeatCategory.GREATER_PLANAR_PACT),
    GeneralFeatType.FEY_TORMENTOR: general_feat(GeneralFeatType.FEY_TORMENTOR, RuleSource.DND_BEYOND_DROPS_2026, 'Fey Tormentor 2024 Greater Planar Pact feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', category=FeatCategory.GREATER_PLANAR_PACT),
    GeneralFeatType.INFERNAL_BULWARK: general_feat(GeneralFeatType.INFERNAL_BULWARK, RuleSource.DND_BEYOND_DROPS_2026, 'Infernal Bulwark 2024 Greater Planar Pact feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', category=FeatCategory.GREATER_PLANAR_PACT),
    GeneralFeatType.INFERNAL_DRAGOON: general_feat(GeneralFeatType.INFERNAL_DRAGOON, RuleSource.DND_BEYOND_DROPS_2026, 'Infernal Dragoon 2024 Greater Planar Pact feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', category=FeatCategory.GREATER_PLANAR_PACT),
    GeneralFeatType.ABERRANT_ANATOMY: general_feat(GeneralFeatType.ABERRANT_ANATOMY, RuleSource.RAVENLOFT_THE_HORRORS_WITHIN_2024, 'Aberrant Anatomy 2024 Dark Gift feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', category=FeatCategory.DARK_GIFT),
    GeneralFeatType.ECHOING_SOUL: general_feat(GeneralFeatType.ECHOING_SOUL, RuleSource.RAVENLOFT_THE_HORRORS_WITHIN_2024, 'Echoing Soul 2024 Dark Gift feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', category=FeatCategory.DARK_GIFT),
    GeneralFeatType.GATHERED_WHISPERS: general_feat(GeneralFeatType.GATHERED_WHISPERS, RuleSource.RAVENLOFT_THE_HORRORS_WITHIN_2024, 'Gathered Whispers 2024 Dark Gift feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', category=FeatCategory.DARK_GIFT),
    GeneralFeatType.LIVING_SHADOW: general_feat(GeneralFeatType.LIVING_SHADOW, RuleSource.RAVENLOFT_THE_HORRORS_WITHIN_2024, 'Living Shadow 2024 Dark Gift feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', category=FeatCategory.DARK_GIFT),
    GeneralFeatType.MIST_WALKER: general_feat(GeneralFeatType.MIST_WALKER, RuleSource.RAVENLOFT_THE_HORRORS_WITHIN_2024, 'Mist Walker 2024 Dark Gift feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', category=FeatCategory.DARK_GIFT),
    GeneralFeatType.SECOND_SKIN: general_feat(GeneralFeatType.SECOND_SKIN, RuleSource.RAVENLOFT_THE_HORRORS_WITHIN_2024, 'Second Skin 2024 Dark Gift feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', category=FeatCategory.DARK_GIFT),
    GeneralFeatType.SYMBIOTIC_BEING: general_feat(GeneralFeatType.SYMBIOTIC_BEING, RuleSource.RAVENLOFT_THE_HORRORS_WITHIN_2024, 'Symbiotic Being 2024 Dark Gift feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', category=FeatCategory.DARK_GIFT),
    GeneralFeatType.TOUCH_OF_DEATH: general_feat(GeneralFeatType.TOUCH_OF_DEATH, RuleSource.RAVENLOFT_THE_HORRORS_WITHIN_2024, 'Touch of Death 2024 Dark Gift feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', category=FeatCategory.DARK_GIFT),
    GeneralFeatType.WATCHERS: general_feat(GeneralFeatType.WATCHERS, RuleSource.RAVENLOFT_THE_HORRORS_WITHIN_2024, 'Watchers 2024 Dark Gift feat. Mechanical choices and special-case automation are pending; use the linked source text for table play details.', category=FeatCategory.DARK_GIFT),
}

GENERAL_FEATS.update(SUPPLEMENTAL_2024_FEATS)


ORIGIN_FEAT_TYPES = {
    GeneralFeatType.ALERT,
    GeneralFeatType.CRAFTER,
    GeneralFeatType.HEALER,
    GeneralFeatType.LUCKY,
    GeneralFeatType.MAGIC_INITIATE,
    GeneralFeatType.MUSICIAN,
    GeneralFeatType.SAVAGE_ATTACKER,
    GeneralFeatType.SHARP_EYE,
    GeneralFeatType.SKILLED,
    GeneralFeatType.SURVIVOR,
    GeneralFeatType.TAVERN_BRAWLER,
    GeneralFeatType.TOUGH,
    GeneralFeatType.CULT_OF_THE_DRAGON_INITIATE,
    GeneralFeatType.EMERALD_ENCLAVE_FLEDGLING,
    GeneralFeatType.HARPER_AGENT,
    GeneralFeatType.LORDS_ALLIANCE_AGENT,
    GeneralFeatType.PURPLE_DRAGON_ROOK,
    GeneralFeatType.SPELLFIRE_SPARK,
    GeneralFeatType.TYRO_OF_THE_GAUNTLET,
    GeneralFeatType.ZHENTARIM_RUFFIAN,
    GeneralFeatType.CHILD_OF_THE_SUN,
    GeneralFeatType.SHADOWMOOR_HEXER,
    GeneralFeatType.TIRELESS_REVELER,
    GeneralFeatType.VAMPIRE_HUNTER,
    GeneralFeatType.VAMPIRE_S_PLAYTHING,
}


def general_feat_category(feat_type: GeneralFeatType) -> FeatCategory:
    if feat_type in ORIGIN_FEAT_TYPES:
        return FeatCategory.ORIGIN
    return GENERAL_FEATS[feat_type].category


FIGHTING_STYLE_FEATS: dict[FightingStyleType, FeatDefinition] = {
    FightingStyleType.ARCHERY: FeatDefinition(
        featType=FightingStyleType.ARCHERY,
        category=FeatCategory.FIGHTING_STYLE,
        repeatable=False,
        description="Gain a +2 bonus to attack rolls you make with ranged weapons.",
        effects=(
            FeatEffect(
                effectType=FeatEffectType.ATTACK_ROLL_BONUS,
                value=2,
                attackRollBonusScope=FeatAttackRollBonusScope.RANGED_WEAPON_ATTACK,
                description="Ranged weapon attack bonus.",
            ),
        ),
    ),
    FightingStyleType.BLIND_FIGHTING: FeatDefinition(
        featType=FightingStyleType.BLIND_FIGHTING,
        category=FeatCategory.FIGHTING_STYLE,
        repeatable=False,
        description="You have blindsight with a range of 10 feet, letting you effectively see anything in range that is not behind total cover.",
        effects=(FeatEffect(effectType=FeatEffectType.DESCRIPTION_ONLY),),
    ),
    FightingStyleType.CLOSE_QUARTERS_SHOOTER: FeatDefinition(
        featType=FightingStyleType.CLOSE_QUARTERS_SHOOTER,
        category=FeatCategory.FIGHTING_STYLE,
        repeatable=False,
        description="Ranged attacks do not have Disadvantage within 5 feet of a hostile creature, ignore half and three-quarters cover within 30 feet, and gain a +1 attack bonus.",
        effects=(
            FeatEffect(
                effectType=FeatEffectType.ATTACK_ROLL_BONUS,
                value=1,
                attackRollBonusScope=FeatAttackRollBonusScope.RANGED_ATTACK,
                description="Ranged attack bonus.",
            ),
        ),
        source=RuleSource.LEGACY,
    ),
    FightingStyleType.DEFENSE: FeatDefinition(
        featType=FightingStyleType.DEFENSE,
        category=FeatCategory.FIGHTING_STYLE,
        repeatable=False,
        description="While wearing armor, gain a +1 bonus to Armor Class.",
        effects=(FeatEffect(effectType=FeatEffectType.ARMOR_CLASS_BONUS, value=1),),
    ),
    FightingStyleType.DUELING: FeatDefinition(
        featType=FightingStyleType.DUELING,
        category=FeatCategory.FIGHTING_STYLE,
        repeatable=False,
        description="When wielding a melee weapon in one hand and no other weapons, gain a +2 bonus to damage rolls with that weapon.",
        effects=(
            FeatEffect(
                effectType=FeatEffectType.DAMAGE_ROLL_BONUS,
                value=2,
                damageRollBonusScope=FeatDamageRollBonusScope.ONE_HANDED_MELEE_WEAPON_ATTACK,
                description="Eligible one-handed melee weapon damage bonus.",
            ),
        ),
    ),
    FightingStyleType.GREAT_WEAPON_FIGHTING: FeatDefinition(
        featType=FightingStyleType.GREAT_WEAPON_FIGHTING,
        category=FeatCategory.FIGHTING_STYLE,
        repeatable=False,
        description="When rolling damage with an eligible two-handed or versatile melee weapon, treat any 1 or 2 on a damage die as a 3.",
        effects=(
            FeatEffect(
                effectType=FeatEffectType.DAMAGE_DICE_REROLL,
                damageDiceRerollScope=FeatDamageDiceRerollScope.TWO_HANDED_OR_VERSATILE_MELEE_WEAPON_ATTACK,
                description="Treat damage dice of 1 or 2 as 3.",
            ),
        ),
    ),
    FightingStyleType.MARINER: FeatDefinition(
        featType=FightingStyleType.MARINER,
        category=FeatCategory.FIGHTING_STYLE,
        repeatable=False,
        description="While not wearing heavy armor or using a shield, gain a swimming speed and climbing speed equal to your Speed, and gain a +1 bonus to Armor Class.",
        effects=(FeatEffect(effectType=FeatEffectType.ARMOR_CLASS_BONUS, value=1),),
        source=RuleSource.LEGACY,
    ),
    FightingStyleType.PACK_FIGHTING: FeatDefinition(
        featType=FightingStyleType.PACK_FIGHTING,
        category=FeatCategory.FIGHTING_STYLE,
        repeatable=False,
        description="When you make a melee attack with a weapon or Unarmed Strike against a creature, gain +1 damage if at least one non-incapacitated ally is within 5 feet of it; +2 if such an ally also has this feat.",
        effects=(
            FeatEffect(
                effectType=FeatEffectType.DESCRIPTION_ONLY,
                description="Conditional damage bonus; apply manually when an ally is within 5 feet of the target.",
            ),
        ),
        source=RuleSource.DND_BEYOND_DROPS_2026,
    ),
    FightingStyleType.PRONE_FIGHTING: FeatDefinition(
        featType=FightingStyleType.PRONE_FIGHTING,
        category=FeatCategory.FIGHTING_STYLE,
        repeatable=False,
        description="When you have the Prone condition, you do not have Disadvantage on attack rolls from being Prone, and attack rolls against you do not have Advantage from you being Prone.",
        effects=(FeatEffect(effectType=FeatEffectType.DESCRIPTION_ONLY),),
        source=RuleSource.DND_BEYOND_DROPS_2026,
    ),
    FightingStyleType.PROTECTION: FeatDefinition(
        featType=FightingStyleType.PROTECTION,
        category=FeatCategory.FIGHTING_STYLE,
        repeatable=False,
        description="Use a Reaction while wielding a shield to impose Disadvantage when a creature you can see attacks another target within 5 feet of you.",
        effects=(
            FeatEffect(
                effectType=FeatEffectType.SHEET_ABILITY,
                activation=TimeEconomy.REACTION,
                description="Impose Disadvantage on an attack against a nearby target other than you while wielding a shield.",
            ),
        ),
    ),
    FightingStyleType.SUPERIOR_TECHNIQUE: FeatDefinition(
        featType=FightingStyleType.SUPERIOR_TECHNIQUE,
        category=FeatCategory.FIGHTING_STYLE,
        repeatable=False,
        description="Learn one Battle Master maneuver and gain one superiority die, which is a d6 unless added to Battle Master superiority dice from another source. The die fuels your maneuver and returns when you finish a short or long rest. Maneuver save DC is 8 + Proficiency Bonus + Strength or Dexterity modifier.",
        effects=(FeatEffect(effectType=FeatEffectType.RESOURCE),),
        source=RuleSource.LEGACY,
    ),
    FightingStyleType.THROWN_WEAPON_FIGHTING: FeatDefinition(
        featType=FightingStyleType.THROWN_WEAPON_FIGHTING,
        category=FeatCategory.FIGHTING_STYLE,
        repeatable=False,
        description="You can draw a thrown weapon as part of the attack, and gain a +2 damage bonus when you hit with a ranged attack using a thrown weapon.",
        effects=(
            FeatEffect(
                effectType=FeatEffectType.DAMAGE_ROLL_BONUS,
                value=2,
                damageRollBonusScope=FeatDamageRollBonusScope.THROWN_RANGED_ATTACK,
                description="Thrown weapon ranged attack damage bonus.",
            ),
        ),
    ),
    FightingStyleType.TUNNEL_FIGHTER: FeatDefinition(
        featType=FightingStyleType.TUNNEL_FIGHTER,
        category=FeatCategory.FIGHTING_STYLE,
        repeatable=False,
        description="Use a Bonus Action to enter a defensive stance until the start of your next turn, enabling extra opportunity control.",
        effects=(
            FeatEffect(
                effectType=FeatEffectType.SHEET_ABILITY,
                activation=TimeEconomy.BONUS_ACTION,
                description="Enter a defensive stance until your next turn: opportunity attacks do not use your Reaction, and you can use your Reaction to attack a creature that moves more than 5 feet within your reach.",
            ),
        ),
        source=RuleSource.LEGACY,
    ),
    FightingStyleType.INTERCEPTION: FeatDefinition(
        featType=FightingStyleType.INTERCEPTION,
        category=FeatCategory.FIGHTING_STYLE,
        repeatable=False,
        description="Use a Reaction to reduce damage to a nearby target by 1d10 plus your Proficiency Bonus.",
        effects=(
            FeatEffect(
                effectType=FeatEffectType.ROLL_ABILITY,
                rollAction=RollAction(
                    id=FightingStyleType.INTERCEPTION,
                    name=FightingStyleType.INTERCEPTION,
                    diceCount=1,
                    diceType=DiceType.D10,
                    modifier=RollModifierType.PROFICIENCY_BONUS,
                    resolution=RollResolutionMode.NONE,
                ),
                activation=TimeEconomy.REACTION,
                description="Reduce damage by 1d10 plus Proficiency Bonus.",
            ),
        ),
    ),
    FightingStyleType.TWO_WEAPON_FIGHTING: FeatDefinition(
        featType=FightingStyleType.TWO_WEAPON_FIGHTING,
        category=FeatCategory.FIGHTING_STYLE,
        repeatable=False,
        description="When making the extra attack from a Light weapon, add your ability modifier to the damage if it is not already included.",
        effects=(
            FeatEffect(
                effectType=FeatEffectType.DAMAGE_ABILITY_MODIFIER,
                damageAbilityModifierScope=FeatDamageAbilityModifierScope.TWO_WEAPON_FIGHTING_ATTACK,
                description="Add the attack ability modifier to two-weapon fighting bonus attack damage.",
            ),
        ),
    ),
    FightingStyleType.UNARMED_FIGHTING: FeatDefinition(
        featType=FightingStyleType.UNARMED_FIGHTING,
        category=FeatCategory.FIGHTING_STYLE,
        repeatable=False,
        description="Your Unarmed Strikes deal improved damage; you can also deal 1d4 damage to a creature grappled by you.",
        effects=(
            FeatEffect(
                effectType=FeatEffectType.ROLL_ABILITY,
                rollAction=RollAction(
                    id=FightingStyleType.UNARMED_FIGHTING,
                    name=FightingStyleType.UNARMED_FIGHTING,
                    diceCount=1,
                    diceType=DiceType.D4,
                    resolution=RollResolutionMode.APPLY_DAMAGE,
                    damageType=DamageType.BLUDGEONING,
                ),
                activation=TimeEconomy.SPECIAL,
                description="Roll 1d4 damage for the grapple rider when appropriate.",
            ),
        ),
    ),
}


def selected_fighting_styles(classes: list[CharacterClassLevel]) -> list[FightingStyleType]:
    styles: list[FightingStyleType] = []
    for character_class in classes:
        for fighting_style in character_class.fightingStyles or []:
            if fighting_style not in styles:
                styles.append(fighting_style)
        if character_class.fightingStyle is not None and character_class.fightingStyle not in styles:
            styles.append(character_class.fightingStyle)
    return styles


def fighting_style_features(classes: list[CharacterClassLevel]):
    from dnd_board.character_sheet import SheetFeature

    features: list[SheetFeature] = []
    for style in selected_fighting_styles(classes):
        definition = FIGHTING_STYLE_FEATS.get(style)
        if definition is None:
            continue
        features.append(
            SheetFeature(
                id=enum_key(style),
                name=fighting_style_label(style),
                source=enum_label(FeatCategory.FIGHTING_STYLE),
                activation=TimeEconomy.PASSIVE,
                description=f"{definition.description} Source: {rule_source_label(definition.source)}.",
            )
        )
    return features


def general_feat_options(selected_feats=None, sheet=None):
    from dnd_board.character_sheet import ProgressionChoiceOption

    selected = set(selected_general_feat_keys(selected_feats))
    return [
        ProgressionChoiceOption(value=enum_key(feat_type), label=enum_label(feat_type))
        for feat_type, definition in GENERAL_FEATS.items()
        if general_feat_category(feat_type) == FeatCategory.GENERAL
        if definition.repeatable or enum_key(feat_type) not in selected
        if sheet is None or general_feat_prerequisites_met(feat_type, sheet)
    ]


def general_feat_feature(feat_key: str):
    from dnd_board.character_sheet import SheetFeature

    feat_type = parse_general_feat(feat_key)
    if feat_type is None:
        return None
    definition = GENERAL_FEATS[feat_type]
    prerequisite = feat_prerequisite_description(definition.prerequisites)
    return SheetFeature(
        id=enum_key(feat_type),
        name=enum_label(feat_type),
        source=rule_source_label(definition.source),
        activation=TimeEconomy.PASSIVE,
        description=f"{definition.description}{prerequisite}",
    )


def feat_prerequisite_description(prerequisites: tuple[FeatPrerequisite, ...]) -> str:
    if not prerequisites:
        return ""
    return f" Prerequisite: {', '.join(feat_prerequisite_label(prerequisite) for prerequisite in prerequisites)}."


def feat_prerequisite_label(prerequisite: FeatPrerequisite) -> str:
    if prerequisite.prerequisiteType == FeatPrerequisiteType.CHARACTER_LEVEL:
        return f"Level {prerequisite.minimumLevel}+"
    if prerequisite.prerequisiteType == FeatPrerequisiteType.ABILITY_SCORE:
        abilities = " or ".join(enum_label(ability) for ability in prerequisite.abilities)
        return f"{abilities} {prerequisite.minimumScore}+"
    if prerequisite.prerequisiteType == FeatPrerequisiteType.SPECIES:
        parts = [enum_label(species) for species in prerequisite.species]
        parts.extend(enum_label(size) for size in prerequisite.speciesSizes)
        return " or ".join(parts)
    if prerequisite.prerequisiteType == FeatPrerequisiteType.SPECIES_SIZE:
        return " or ".join(enum_label(size) for size in prerequisite.speciesSizes)
    if prerequisite.prerequisiteType == FeatPrerequisiteType.ARMOR_PROFICIENCY:
        return "Proficiency with " + " or ".join(f"{enum_label(category)} armor" for category in prerequisite.armorCategories)
    if prerequisite.prerequisiteType == FeatPrerequisiteType.WEAPON_PROFICIENCY:
        parts = [enum_label(proficiency) for proficiency in prerequisite.weaponProficiencies]
        parts.extend(enum_label(background) for background in prerequisite.backgrounds)
        return " or ".join(parts)
    if prerequisite.prerequisiteType == FeatPrerequisiteType.CHARACTER_FEATURE:
        return " or ".join(enum_label(feature) for feature in prerequisite.features)
    if prerequisite.prerequisiteType == FeatPrerequisiteType.SPELLCASTING:
        return "Spellcasting or Pact Magic"
    if prerequisite.prerequisiteType == FeatPrerequisiteType.FEAT:
        feat_labels = [enum_label(feat) for feat in prerequisite.feats]
        strike_labels = [enum_label(strike) for strike in prerequisite.giantStrikes]
        return " ".join([*feat_labels, *strike_labels])
    if prerequisite.prerequisiteType == FeatPrerequisiteType.BACKGROUND:
        return " or ".join(enum_label(background) for background in prerequisite.backgrounds)
    return ""


def general_feat_prerequisites_met(feat_type: GeneralFeatType, sheet) -> bool:
    return all(feat_prerequisite_met(prerequisite, sheet) for prerequisite in GENERAL_FEATS[feat_type].prerequisites)


def feat_prerequisite_met(prerequisite: FeatPrerequisite, sheet) -> bool:
    if prerequisite.prerequisiteType == FeatPrerequisiteType.CHARACTER_LEVEL:
        return character_level(sheet) >= prerequisite.minimumLevel
    if prerequisite.prerequisiteType == FeatPrerequisiteType.ABILITY_SCORE:
        return any(ability_score(sheet, ability) >= prerequisite.minimumScore for ability in prerequisite.abilities)
    if prerequisite.prerequisiteType == FeatPrerequisiteType.SPECIES:
        return character_species(sheet) in prerequisite.species or character_size(sheet) in prerequisite.speciesSizes
    if prerequisite.prerequisiteType == FeatPrerequisiteType.SPECIES_SIZE:
        return character_size(sheet) in prerequisite.speciesSizes
    if prerequisite.prerequisiteType == FeatPrerequisiteType.ARMOR_PROFICIENCY:
        return any(has_armor_proficiency(sheet, category) for category in prerequisite.armorCategories)
    if prerequisite.prerequisiteType == FeatPrerequisiteType.WEAPON_PROFICIENCY:
        return any(has_weapon_proficiency(sheet, proficiency) for proficiency in prerequisite.weaponProficiencies) or any(enum_label(background) == sheet_background(sheet) for background in prerequisite.backgrounds)
    if prerequisite.prerequisiteType == FeatPrerequisiteType.CHARACTER_FEATURE:
        return any(has_character_feature(sheet, feature) for feature in prerequisite.features)
    if prerequisite.prerequisiteType == FeatPrerequisiteType.SPELLCASTING:
        return bool(sheet_value(sheet, FeatSheetField.SPELLS, None)) or any(has_character_feature(sheet, feature) for feature in prerequisite.features)
    if prerequisite.prerequisiteType == FeatPrerequisiteType.FEAT:
        return any(has_general_feat(sheet, feat) for feat in prerequisite.feats)
    if prerequisite.prerequisiteType == FeatPrerequisiteType.BACKGROUND:
        return any(enum_label(background) == sheet_background(sheet) for background in prerequisite.backgrounds)
    return False


def character_level(sheet) -> int:
    return sum(character_class.level for character_class in sheet_value(sheet, FeatSheetField.CLASSES, []) or []) or sheet_character_class_level(sheet)


def sheet_character_class_level(sheet) -> int:
    character_class = sheet_value(sheet, FeatSheetField.CHARACTER_CLASS, None)
    return getattr(character_class, FeatCharacterClassField.LEVEL.value, 0)


def character_species(sheet) -> SpeciesType | None:
    race = sheet_value(sheet, FeatSheetField.RACE, "")
    for species in SpeciesType:
        if enum_label(species) == race:
            return species
    return None


SMALL_SPECIES = {SpeciesType.GNOME, SpeciesType.HALFLING, SpeciesType.FAERIE}


def character_size(sheet) -> FeatSpeciesSize | None:
    return FeatSpeciesSize.SMALL if character_species(sheet) in SMALL_SPECIES else None


def has_armor_proficiency(sheet, category: ArmorCategory) -> bool:
    label = f"{enum_label(category)} armor".lower()
    return any(label in proficiency.lower() for proficiency in sheet_proficiencies(sheet))


def has_weapon_proficiency(sheet, proficiency: WeaponProficiencyType) -> bool:
    label = enum_label(proficiency).lower()
    return any(label in sheet_proficiency.lower() for sheet_proficiency in sheet_proficiencies(sheet))


def has_character_feature(sheet, feature: FeatCharacterFeatureType) -> bool:
    label = enum_label(feature).lower()
    feature_lists = [sheet_value(sheet, FeatSheetField.FEATURES, []) or [], sheet_value(sheet, FeatSheetField.ABILITIES, []) or []]
    return any(label in feature_text(item, FeatFeatureField.NAME).lower() or label in feature_text(item, FeatFeatureField.DESCRIPTION).lower() for items in feature_lists for item in items)


def has_general_feat(sheet, feat_type: GeneralFeatType) -> bool:
    key = enum_key(feat_type)
    return any(feature_text(feat, FeatFeatureField.ID) == key for feat in sheet_value(sheet, FeatSheetField.FEATURES, []) or []) or any(feature_text(feat, FeatFeatureField.ID) == key for feat in sheet_value(sheet, FeatSheetField.FEATS, []) or [])


def selected_general_feat_keys(feats) -> list[str]:
    keys: list[str] = []
    for feat in feats or []:
        feat_type = parse_general_feat(feature_text(feat, FeatFeatureField.ID))
        if feat_type is not None:
            key = enum_key(feat_type)
            if key not in keys:
                keys.append(key)
    return keys


def selected_general_feat_types(feats) -> set[GeneralFeatType]:
    selected: set[GeneralFeatType] = set()
    for feat in feats or []:
        feat_type = parse_general_feat(feature_text(feat, FeatFeatureField.ID))
        if feat_type is not None:
            selected.add(feat_type)
    return selected


def ability_score(sheet, ability: AbilityType) -> int:
    ability_scores = sheet_value(sheet, FeatSheetField.ABILITY_SCORES, None)
    if ability_scores is None:
        return 0
    return getattr(ability_scores, enum_key(ability), 0)


def sheet_background(sheet) -> str:
    return sheet_value(sheet, FeatSheetField.BACKGROUND, "")


def sheet_proficiencies(sheet) -> list[str]:
    return sheet_value(sheet, FeatSheetField.PROFICIENCIES, []) or []


def sheet_value(sheet, field: FeatSheetField, default):
    return getattr(sheet, field.value, default)


def feature_text(feature, field: FeatFeatureField) -> str:
    return getattr(feature, field.value, "")


def parse_general_feat(value: str) -> GeneralFeatType | None:
    normalized = normalize_feat_key(value)
    for feat_type in GeneralFeatType:
        if normalized in {normalize_feat_key(feat_type.name), normalize_feat_key(enum_key(feat_type)), normalize_feat_key(enum_label(feat_type))}:
            return feat_type
    return None


def normalize_feat_key(value: str) -> str:
    return value.strip().replace("-", "").replace("_", "").replace(" ", "").lower()


def feat_resources(classes: list[CharacterClassLevel], feats=None, proficiency_bonus: int = 2) -> list[ResourceTracker]:
    selected_feats = selected_general_feat_types(feats)
    resources: list[ResourceTracker] = []
    if GeneralFeatType.LUCKY in selected_feats:
        resources.append(ResourceTracker(
            id=FeatResourceId.LUCK_POINTS.value,
            name=enum_label(GeneralFeatType.LUCKY),
            currentUses=proficiency_bonus,
            maxUses=proficiency_bonus,
            reset=RestType.LONG_REST,
            activation=TimeEconomy.SPECIAL,
            description="Spend Luck Points to gain Advantage on a D20 Test or impose Disadvantage on an attack roll against you.",
        ))
    if GeneralFeatType.BOON_OF_COMBAT_PROWESS in selected_feats:
        resources.append(feat_single_use_resource(FeatResourceId.BOON_OF_COMBAT_PROWESS, GeneralFeatType.BOON_OF_COMBAT_PROWESS, RestType.SHORT_REST, "Turn a missed melee weapon attack into a hit."))
    if GeneralFeatType.BOON_OF_DIMENSIONAL_TRAVEL in selected_feats:
        resources.append(feat_single_use_resource(FeatResourceId.BOON_OF_DIMENSIONAL_TRAVEL, GeneralFeatType.BOON_OF_DIMENSIONAL_TRAVEL, RestType.SHORT_REST, "Cast Misty Step without a spell slot or components."))
    if GeneralFeatType.BOON_OF_FATE in selected_feats:
        resources.append(feat_single_use_resource(FeatResourceId.BOON_OF_FATE, GeneralFeatType.BOON_OF_FATE, RestType.SHORT_REST, "Roll 1d10 and add or subtract it from another creature's d20 Test."))
    if GeneralFeatType.BOON_OF_RECOVERY in selected_feats:
        resources.append(feat_single_use_resource(FeatResourceId.BOON_OF_RECOVERY, GeneralFeatType.BOON_OF_RECOVERY, RestType.LONG_REST, "Regain hit points when reduced to 0 or by using a Bonus Action."))
    return resources


def feat_single_use_resource(resource_id: FeatResourceId, feat_type: GeneralFeatType, reset: RestType, description: str) -> ResourceTracker:
    return ResourceTracker(
        id=resource_id.value,
        name=enum_label(feat_type),
        currentUses=1,
        maxUses=1,
        reset=reset,
        activation=TimeEconomy.SPECIAL,
        description=description,
    )


def feat_abilities(classes: list[CharacterClassLevel], feats=None) -> list[SheetAbility]:
    abilities: list[SheetAbility] = []
    selected_feats = selected_general_feat_types(feats)
    feat_ability_specs = [
        (GeneralFeatType.HEALER, FeatAbilityId.HEALER, TimeEconomy.ACTION, None, "Use a Healer's Kit to restore hit points or stabilize a creature."),
        (GeneralFeatType.LUCKY, FeatAbilityId.LUCKY_ADVANTAGE, TimeEconomy.SPECIAL, FeatResourceId.LUCK_POINTS, "Spend 1 Luck Point to gain Advantage on a D20 Test."),
        (GeneralFeatType.LUCKY, FeatAbilityId.LUCKY_DISADVANTAGE, TimeEconomy.REACTION, FeatResourceId.LUCK_POINTS, "Spend 1 Luck Point to impose Disadvantage on an attack roll against you."),
        (GeneralFeatType.OBSERVANT, FeatAbilityId.OBSERVANT_QUICK_SEARCH, TimeEconomy.BONUS_ACTION, None, "Take the Search action as a Bonus Action."),
        (GeneralFeatType.TELEKINETIC, FeatAbilityId.TELEKINETIC_SHOVE, TimeEconomy.BONUS_ACTION, None, "Telekinetically shove one creature you can see within 30 feet."),
        (GeneralFeatType.BOON_OF_COMBAT_PROWESS, FeatAbilityId.BOON_OF_COMBAT_PROWESS, TimeEconomy.SPECIAL, FeatResourceId.BOON_OF_COMBAT_PROWESS, "Turn a missed melee weapon attack into a hit."),
        (GeneralFeatType.BOON_OF_DIMENSIONAL_TRAVEL, FeatAbilityId.BOON_OF_DIMENSIONAL_TRAVEL, TimeEconomy.ACTION, FeatResourceId.BOON_OF_DIMENSIONAL_TRAVEL, "Cast Misty Step without a spell slot or components."),
        (GeneralFeatType.BOON_OF_FATE, FeatAbilityId.BOON_OF_FATE, TimeEconomy.REACTION, FeatResourceId.BOON_OF_FATE, "Roll 1d10 and add or subtract it from another creature's d20 Test."),
        (GeneralFeatType.BOON_OF_RECOVERY, FeatAbilityId.BOON_OF_RECOVERY, TimeEconomy.BONUS_ACTION, FeatResourceId.BOON_OF_RECOVERY, "Regain hit points."),
    ]
    for feat_type, ability_id, activation, resource_id, description in feat_ability_specs:
        if feat_type not in selected_feats:
            continue
        abilities.append(SheetAbility(
            id=ability_id.value,
            name=enum_label(feat_type),
            source=enum_label(general_feat_category(feat_type)),
            activation=activation,
            description=description,
            resourceId=resource_id.value if resource_id else None,
        ))
    for style in selected_fighting_styles(classes):
        definition = FIGHTING_STYLE_FEATS.get(style)
        if definition is None:
            continue
        for effect in definition.effects:
            if effect.effectType == FeatEffectType.ROLL_ABILITY and effect.rollAction is not None:
                abilities.append(
                    SheetAbility(
                        id=enum_key(style),
                        name=enum_label(style),
                        source=enum_label(FeatCategory.FIGHTING_STYLE),
                        activation=effect.activation,
                        description=effect.description,
                        rollActions=[effect.rollAction],
                    )
                )
            elif effect.effectType == FeatEffectType.SHEET_ABILITY:
                abilities.append(
                    SheetAbility(
                        id=enum_key(style),
                        name=enum_label(style),
                        source=enum_label(FeatCategory.FIGHTING_STYLE),
                        activation=effect.activation,
                        description=effect.description,
                    )
                )
    return abilities


def feat_hit_point_bonus(feats, total_level: int) -> int:
    selected_feats = selected_general_feat_types(feats)
    bonus = 0
    if GeneralFeatType.BOON_OF_FORTITUDE in selected_feats:
        bonus += 40
    return bonus


def feat_speed_bonus(feats) -> int:
    selected_feats = selected_general_feat_types(feats)
    bonus = 0
    if GeneralFeatType.SPEEDY in selected_feats:
        bonus += 10
    if GeneralFeatType.MOBILE in selected_feats:
        bonus += 10
    if GeneralFeatType.BOON_OF_SPEED in selected_feats:
        bonus += 30
    return bonus


def feat_initiative_bonus(feats, proficiency_bonus: int) -> int:
    return proficiency_bonus if GeneralFeatType.ALERT in selected_general_feat_types(feats) else 0


def armor_class_bonus(classes: list[CharacterClassLevel], equipment: list[EquipmentItem]) -> int:
    bonus = 0
    for style in selected_fighting_styles(classes):
        definition = FIGHTING_STYLE_FEATS.get(style)
        if definition is None:
            continue
        bonus += sum(effect.value for effect in definition.effects if effect.effectType == FeatEffectType.ARMOR_CLASS_BONUS and armor_class_bonus_applies(style, equipment))
    return bonus


def attack_roll_modifiers(classes: list[CharacterClassLevel], action: AttackAction) -> list[RollModifierBreakdown]:
    modifiers: list[RollModifierBreakdown] = []
    for definition in selected_fighting_style_definitions(classes):
        for effect in definition.effects:
            if effect.effectType == FeatEffectType.ATTACK_ROLL_BONUS and attack_roll_bonus_applies(effect, action):
                modifiers.append(RollModifierBreakdown(source=enum_label(definition.featType), value=effect.value, description=effect.description))
    return modifiers


def damage_roll_modifiers(classes: list[CharacterClassLevel], equipment: list[EquipmentItem], action: AttackAction, ability_modifier_value: int) -> list[RollModifierBreakdown]:
    modifiers: list[RollModifierBreakdown] = []
    for definition in selected_fighting_style_definitions(classes):
        for effect in definition.effects:
            if effect.effectType == FeatEffectType.DAMAGE_ROLL_BONUS and damage_roll_bonus_applies(effect, equipment, action):
                modifiers.append(RollModifierBreakdown(source=enum_label(definition.featType), value=effect.value, description=effect.description))
            elif effect.effectType == FeatEffectType.DAMAGE_ABILITY_MODIFIER and damage_ability_modifier_applies(effect, action):
                modifiers.append(RollModifierBreakdown(source=enum_label(definition.featType), value=ability_modifier_value, description=effect.description))
    return modifiers


def great_weapon_fighting_applies(classes: list[CharacterClassLevel], action: AttackAction) -> bool:
    return any(
        effect.effectType == FeatEffectType.DAMAGE_DICE_REROLL and damage_dice_reroll_applies(effect, action)
        for definition in selected_fighting_style_definitions(classes)
        for effect in definition.effects
    )


def selected_fighting_style_definitions(classes: list[CharacterClassLevel]) -> list[FeatDefinition]:
    return [definition for style in selected_fighting_styles(classes) if (definition := FIGHTING_STYLE_FEATS.get(style)) is not None]


def attack_roll_bonus_applies(effect: FeatEffect, action: AttackAction) -> bool:
    if effect.attackRollBonusScope == FeatAttackRollBonusScope.RANGED_ATTACK:
        return is_ranged_attack(action)
    if effect.attackRollBonusScope == FeatAttackRollBonusScope.RANGED_WEAPON_ATTACK:
        return is_ranged_weapon_attack(action)
    return False


def damage_roll_bonus_applies(effect: FeatEffect, equipment: list[EquipmentItem], action: AttackAction) -> bool:
    if effect.damageRollBonusScope == FeatDamageRollBonusScope.ONE_HANDED_MELEE_WEAPON_ATTACK:
        return is_one_handed_melee_weapon_attack(action) and is_wielding_exactly_one_one_handed_weapon(equipment)
    if effect.damageRollBonusScope == FeatDamageRollBonusScope.THROWN_RANGED_ATTACK:
        return is_thrown_weapon_attack(action)
    return False


def damage_ability_modifier_applies(effect: FeatEffect, action: AttackAction) -> bool:
    if effect.damageAbilityModifierScope == FeatDamageAbilityModifierScope.TWO_WEAPON_FIGHTING_ATTACK:
        return action.attackKind == AttackKind.TWO_WEAPON_FIGHTING and action.damageAbilityModifier == AttackDamageAbilityModifierMode.EXCLUDED
    return False


def damage_dice_reroll_applies(effect: FeatEffect, action: AttackAction) -> bool:
    if effect.damageDiceRerollScope == FeatDamageDiceRerollScope.TWO_HANDED_OR_VERSATILE_MELEE_WEAPON_ATTACK:
        return is_two_handed_or_versatile_melee_weapon_attack(action)
    return False


def feat_attacks(classes: list[CharacterClassLevel], equipment: list[EquipmentItem], attacks: list[AttackAction]) -> list[AttackAction]:
    styles = selected_fighting_styles(classes)
    next_attacks = list(attacks)
    attack_types = {attack.attackType for attack in next_attacks}
    if FightingStyleType.UNARMED_FIGHTING in styles and AttackActionType.UNARMED_STRIKE not in attack_types:
        next_attacks.append(
            AttackAction(
                id=enum_key(AttackActionType.UNARMED_STRIKE),
                name=enum_label(AttackActionType.UNARMED_STRIKE),
                ability=AbilityType.STRENGTH,
                damageDiceCount=1,
                damageDiceType=DiceType.D8 if has_empty_hands_for_unarmed_fighting(equipment) else DiceType.D6,
                damageType=DamageType.BLUDGEONING,
                attackRange=AttackRangeType.MELEE,
                weaponCategory=WeaponCategory.MELEE,
                attackType=AttackActionType.UNARMED_STRIKE,
                properties=[],
            )
        )
    if FightingStyleType.THROWN_WEAPON_FIGHTING in styles and AttackActionType.THROWN_WEAPON not in attack_types:
        next_attacks.append(
            AttackAction(
                id=enum_key(AttackActionType.THROWN_WEAPON),
                name=enum_label(AttackActionType.THROWN_WEAPON),
                ability=AbilityType.STRENGTH,
                damageDiceCount=1,
                damageDiceType=DiceType.D6,
                damageType=DamageType.SLASHING,
                attackRange=AttackRangeType.RANGED,
                weaponCategory=WeaponCategory.MELEE,
                attackType=AttackActionType.THROWN_WEAPON,
                properties=[WeaponProperty.THROWN],
            )
        )
    return next_attacks


def armor_class_bonus_applies(style: FightingStyleType, equipment: list[EquipmentItem]) -> bool:
    if style == FightingStyleType.DEFENSE:
        return is_wearing_armor(equipment)
    if style == FightingStyleType.MARINER:
        return not is_wearing_heavy_armor(equipment) and not is_wielding_shield(equipment)
    return True


def is_wearing_armor(equipment: list[EquipmentItem]) -> bool:
    return any(item.itemType == EquipmentType.ARMOR and item.slot == EquipmentSlot.ARMOR for item in equipment)


def is_wearing_heavy_armor(equipment: list[EquipmentItem]) -> bool:
    return any(item.itemType == EquipmentType.ARMOR and item.slot == EquipmentSlot.ARMOR and item.armorCategory == ArmorCategory.HEAVY for item in equipment)


def is_wielding_shield(equipment: list[EquipmentItem]) -> bool:
    return any(item.itemType == EquipmentType.SHIELD and item.slot in {EquipmentSlot.MAIN_HAND, EquipmentSlot.OFF_HAND} for item in equipment)


def wielded_weapons(equipment: list[EquipmentItem]) -> list[EquipmentItem]:
    return [item for item in equipment if item.itemType == EquipmentType.WEAPON and item.slot in {EquipmentSlot.MAIN_HAND, EquipmentSlot.OFF_HAND, EquipmentSlot.TWO_HANDS}]


def is_wielding_exactly_one_one_handed_weapon(equipment: list[EquipmentItem]) -> bool:
    weapons = wielded_weapons(equipment)
    return len(weapons) == 1 and weapons[0].slot in {EquipmentSlot.MAIN_HAND, EquipmentSlot.OFF_HAND}


def has_empty_hands_for_unarmed_fighting(equipment: list[EquipmentItem]) -> bool:
    return not wielded_weapons(equipment) and not is_wielding_shield(equipment)


def weapon_properties(action: AttackAction) -> set[WeaponProperty]:
    return set(action.properties or [])


def is_ranged_weapon_attack(action: AttackAction) -> bool:
    return action.weaponCategory == WeaponCategory.RANGED and action.attackRange == AttackRangeType.RANGED


def is_ranged_attack(action: AttackAction) -> bool:
    return action.attackRange == AttackRangeType.RANGED


def is_thrown_weapon_attack(action: AttackAction) -> bool:
    return action.attackRange == AttackRangeType.RANGED and WeaponProperty.THROWN in weapon_properties(action)


def is_melee_weapon_attack(action: AttackAction) -> bool:
    return action.attackRange == AttackRangeType.MELEE and action.damageType in {DamageType.BLUDGEONING, DamageType.PIERCING, DamageType.SLASHING}


def is_one_handed_melee_weapon_attack(action: AttackAction) -> bool:
    return is_melee_weapon_attack(action) and WeaponProperty.TWO_HANDED not in weapon_properties(action)


def is_two_handed_or_versatile_melee_weapon_attack(action: AttackAction) -> bool:
    return is_melee_weapon_attack(action) and bool(weapon_properties(action) & {WeaponProperty.TWO_HANDED, WeaponProperty.VERSATILE})
