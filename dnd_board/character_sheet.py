from __future__ import annotations

import random
from dataclasses import dataclass, field, fields, is_dataclass, replace
from enum import Enum, auto
from time import time_ns
from types import SimpleNamespace, UnionType
from typing import Any, Union, get_args, get_origin, get_type_hints


class TokenKind(Enum):
    CHARACTER = auto()
    ASSET = auto()


class RollResolutionMode(Enum):
    NONE = auto()
    ATTACK_VS_ARMOR_CLASS = auto()
    APPLY_DAMAGE = auto()
    HEAL_SELF = auto()
    APPLY_TEMPORARY_HIT_POINTS = auto()


class RollLogEntryType(Enum):
    ROLL_CREATED = auto()
    ROLL_RESOLVED = auto()
    ROLL_BLOCKED = auto()


class RollModifierType(Enum):
    NONE = auto()
    CLASS_LEVEL = auto()
    PROFICIENCY_BONUS = auto()
    ABILITY_MODIFIER = auto()


class SheetSectionType(Enum):
    ATTACKS = auto()
    RESOURCES = auto()
    FEATURES = auto()
    ABILITIES = auto()
    ABILITY_SCORES = auto()
    SPELLS = auto()


class ProgressionChoiceType(Enum):
    HIT_POINTS = auto()
    ABILITY_SCORE_IMPROVEMENT = auto()
    SKILL_PROFICIENCIES = auto()
    EXPERTISE = auto()
    SUBCLASS = auto()
    FIGHTING_STYLE = auto()
    BATTLE_MASTER_MANEUVERS = auto()
    ARCANE_SHOTS = auto()
    RUNES = auto()
    SPELLS = auto()


class AbilityRollType(Enum):
    CHECK = auto()
    SAVE = auto()


class UIStringFormatter:
    @staticmethod
    def clean_name(identifier: str) -> str:
        return " ".join(word.capitalize() for word in identifier.replace("_", " ").split())

    @staticmethod
    def lower_camel(identifier: str) -> str:
        words = identifier.lower().split("_")
        return words[0] + "".join(word.capitalize() for word in words[1:])


def api_field(method: Any) -> property:
    method.__api_field__ = True
    return property(method)


def enum_key(member: Enum) -> str:
    return UIStringFormatter.lower_camel(member.name)


def enum_label(member: Enum) -> str:
    if isinstance(member.value, str):
        return member.value
    return UIStringFormatter.clean_name(member.name)


class TypedJsonPrimitiveType(Enum):
    NONE = "None"
    STRING = "str"
    INTEGER = "int"
    FLOAT = "float"
    BOOLEAN = "bool"
    LIST = "list"
    DICTIONARY = "dict"


class AbilityType(Enum):
    STRENGTH = auto()
    DEXTERITY = auto()
    CONSTITUTION = auto()
    INTELLIGENCE = auto()
    WISDOM = auto()
    CHARISMA = auto()


class SkillType(Enum):
    ATHLETICS = auto()
    ACROBATICS = auto()
    SLEIGHT_OF_HAND = auto()
    STEALTH = auto()
    ARCANA = auto()
    HISTORY = auto()
    INVESTIGATION = auto()
    NATURE = auto()
    RELIGION = auto()
    ANIMAL_HANDLING = auto()
    INSIGHT = auto()
    MEDICINE = auto()
    PERCEPTION = auto()
    SURVIVAL = auto()
    DECEPTION = auto()
    INTIMIDATION = auto()
    PERFORMANCE = auto()
    PERSUASION = auto()


class DamageType(Enum):
    ACID = auto()
    BLUDGEONING = auto()
    COLD = auto()
    FIRE = auto()
    FORCE = auto()
    LIGHTNING = auto()
    NECROTIC = auto()
    PIERCING = auto()
    POISON = auto()
    PSYCHIC = auto()
    RADIANT = auto()
    SLASHING = auto()
    THUNDER = auto()


class CreatureType(Enum):
    ABERRATION = auto()
    BEAST = auto()
    CELESTIAL = auto()
    CONSTRUCT = auto()
    DRAGON = auto()
    ELEMENTAL = auto()
    FEY = auto()
    FIEND = auto()
    GIANT = auto()
    HUMANOID = auto()
    MONSTROSITY = auto()
    OOZE = auto()
    PLANT = auto()
    UNDEAD = auto()


class SpellSchool(Enum):
    ABJURATION = auto()
    CONJURATION = auto()
    DIVINATION = auto()
    ENCHANTMENT = auto()
    EVOCATION = auto()
    ILLUSION = auto()
    NECROMANCY = auto()
    TRANSMUTATION = auto()


class SpellComponent(Enum):
    VERBAL = auto()
    SOMATIC = auto()
    MATERIAL = auto()


class SpellId(Enum):
    ABSORB_ELEMENTS = "Absorb Elements"
    ACID_SPLASH = "Acid Splash"
    AID = "Aid"
    ALARM = "Alarm"
    ALTER_SELF = "Alter Self"
    ALUSTRIEL_S_MOONCLOAK = "Alustriel's Mooncloak"
    ANIMAL_FRIENDSHIP = "Animal Friendship"
    ANIMAL_MESSENGER = "Animal Messenger"
    ANIMAL_SHAPES = "Animal Shapes"
    ANIMATE_DEAD = "Animate Dead"
    ANIMATE_OBJECTS = "Animate Objects"
    ANTILIFE_SHELL = "Antilife Shell"
    ANTIMAGIC_FIELD = "Antimagic Field"
    ANTIPATHY_SYMPATHY = "Antipathy/Sympathy"
    ARCANE_EYE = "Arcane Eye"
    ARCANE_GATE = "Arcane Gate"
    ARCANE_LOCK = "Arcane Lock"
    ARCANE_VIGOR = "Arcane Vigor"
    ARMOR_OF_AGATHYS = "Armor of Agathys"
    ARMS_OF_HADAR = "Arms of Hadar"
    ASTRAL_FLOOD = "Astral Flood"
    ASTRAL_PROJECTION = "Astral Projection"
    AUGURY = "Augury"
    AURA_OF_LIFE = "Aura of Life"
    AURA_OF_PURITY = "Aura of Purity"
    AURA_OF_VITALITY = "Aura of Vitality"
    AWAKEN = "Awaken"
    BACKLASH = "Backlash"
    BANE = "Bane"
    BANISHING_SMITE = "Banishing Smite"
    BANISHMENT = "Banishment"
    BARKSKIN = "Barkskin"
    BEACON_OF_HOPE = "Beacon Of Hope"
    BEAST_SENSE = "Beast Sense"
    BEFUDDLEMENT = "Befuddlement"
    BESTOW_CURSE = "Bestow Curse"
    BIGBY_S_HAND = "Bigby's Hand"
    BLADE_BARRIER = "Blade Barrier"
    BLADE_OF_DISASTER = "Blade Of Disaster"
    BLADE_WARD = "Blade Ward"
    BLESS = "Bless"
    BLIGHT = "Blight"
    BLINDING_SMITE = "Blinding Smite"
    BLINDNESS_DEAFNESS = "Blindness/Deafness"
    BLINK = "Blink"
    BLUR = "Blur"
    BOOMING_BLADE = "Booming Blade"
    BURNING_HANDS = "Burning Hands"
    BUZZING_BEE = "Buzzing Bee"
    CACOPHONIC_SHIELD = "Cacophonic Shield"
    CALL_LIGHTNING = "Call Lightning"
    CALM_EMOTIONS = "Calm Emotions"
    CHAIN_LIGHTNING = "Chain Lightning"
    CHARM_MONSTER = "Charm Monster"
    CHARM_PERSON = "Charm Person"
    CHILL_TOUCH = "Chill Touch"
    CHROMATIC_ORB = "Chromatic Orb"
    CIRCLE_OF_DEATH = "Circle Of Death"
    CIRCLE_OF_POWER = "Circle Of Power"
    CLAIRVOYANCE = "Clairvoyance"
    CLONE = "Clone"
    CLOUDKILL = "Cloudkill"
    CLOUD_OF_DAGGERS = "Cloud Of Daggers"
    COLOR_SPRAY = "Color Spray"
    COMMAND = "Command"
    COMMUNE = "Commune"
    COMMUNE_WITH_NATURE = "Commune With Nature"
    COMPELLED_DUEL = "Compelled Duel"
    COMPREHEND_LANGUAGES = "Comprehend Languages"
    COMPULSION = "Compulsion"
    CONE_OF_COLD = "Cone Of Cold"
    CONFUSION = "Confusion"
    CONJURE_ANIMALS = "Conjure Animals"
    CONJURE_BARRAGE = "Conjure Barrage"
    CONJURE_CELESTIAL = "Conjure Celestial"
    CONJURE_CONSTRUCTS = "Conjure Constructs"
    CONJURE_ELEMENTAL = "Conjure Elemental"
    CONJURE_FEY = "Conjure Fey"
    CONJURE_MINOR_ELEMENTALS = "Conjure Minor Elementals"
    CONJURE_VOLLEY = "Conjure Volley"
    CONJURE_WOODLAND_BEINGS = "Conjure Woodland Beings"
    CONTACT_OTHER_PLANE = "Contact Other Plane"
    CONTAGION = "Contagion"
    CONTINGENCY = "Contingency"
    CONTINUAL_FLAME = "Continual Flame"
    CONTROL_WATER = "Control Water"
    CONTROL_WEATHER = "Control Weather"
    CORDON_OF_ARROWS = "Cordon Of Arrows"
    COUNTERSPELL = "Counterspell"
    CREATE_FOOD_AND_WATER = "Create Food And Water"
    CREATE_OR_DESTROY_WATER = "Create or Destroy Water"
    CREATE_UNDEAD = "Create Undead"
    CREATION = "Creation"
    CROWN_OF_MADNESS = "Crown Of Madness"
    CRUSADER_S_MANTLE = "Crusader's Mantle"
    CURE_WOUNDS = "Cure Wounds"
    DANCING_LIGHTS = "Dancing Lights"
    DARKNESS = "Darkness"
    DARKVISION = "Darkvision"
    DAYLIGHT = "Daylight"
    DEATH_ARMOR = "Death Armor"
    DEATH_WARD = "Death Ward"
    DELAYED_BLAST_FIREBALL = "Delayed Blast Fireball"
    DEMIPLANE = "Demiplane"
    DERYAN_S_HELPFUL_HOMUNCULI = "Deryan's Helpful Homunculi"
    DESTRUCTIVE_WAVE = "Destructive Wave"
    DETECT_EVIL_AND_GOOD = "Detect Evil and Good"
    DETECT_MAGIC = "Detect Magic"
    DETECT_POISON_AND_DISEASE = "Detect Poison and Disease"
    DETECT_THOUGHTS = "Detect Thoughts"
    DIMENSION_DOOR = "Dimension Door"
    DIRGE = "Dirge"
    DISGUISE_SELF = "Disguise Self"
    DISINTEGRATE = "Disintegrate"
    DISPEL_EVIL_AND_GOOD = "Dispel Evil and Good"
    DISPEL_MAGIC = "Dispel Magic"
    DISSONANT_WHISPERS = "Dissonant Whispers"
    DIVINATION = "Divination"
    DIVINE_FAVOR = "Divine Favor"
    DIVINE_SMITE = "Divine Smite"
    DIVINE_WORD = "Divine Word"
    DOMINATE_BEAST = "Dominate Beast"
    DOMINATE_MONSTER = "Dominate Monster"
    DOMINATE_PERSON = "Dominate Person"
    DOOMTIDE = "Doomtide"
    DRAGON_S_BREATH = "Dragon's Breath"
    DRAWMIJ_S_INSTANT_SUMMONS = "Drawmij's Instant Summons"
    DREAM = "Dream"
    DRUIDCRAFT = "Druidcraft"
    EARTHQUAKE = "Earthquake"
    ELDRITCH_BLAST = "Eldritch Blast"
    ELEMENTALISM = "Elementalism"
    ELEMENTAL_WEAPON = "Elemental Weapon"
    ELMINSTER_S_EFFULGENT_SPHERES = "Elminster's Effulgent Spheres"
    ELMINSTER_S_ELUSION = "Elminster's Elusion"
    ENHANCE_ABILITY = "Enhance Ability"
    ENLARGE_REDUCE = "Enlarge/Reduce"
    ENSNARING_STRIKE = "Ensnaring Strike"
    ENTANGLE = "Entangle"
    ENTHRALL = "Enthrall"
    ETHEREALNESS = "Etherealness"
    EVARD_S_BLACK_TENTACLES = "Evard's Black Tentacles"
    EXPEDITIOUS_RETREAT = "Expeditious Retreat"
    EYEBITE = "Eyebite"
    FABRICATE = "Fabricate"
    FAERIE_FIRE = "Faerie Fire"
    FALSE_LIFE = "False Life"
    FEAR = "Fear"
    FEATHER_FALL = "Feather Fall"
    FEIGN_DEATH = "Feign Death"
    FIND_FAMILIAR = "Find Familiar"
    FIND_STEED = "Find Steed"
    FIND_THE_PATH = "Find the Path"
    FIND_TRAPS = "Find Traps"
    FINGER_OF_DEATH = "Finger of Death"
    FIREBALL = "Fireball"
    FIRE_BOLT = "Fire Bolt"
    FIRE_SHIELD = "Fire Shield"
    FIRE_STORM = "Fire Storm"
    FLAME_BLADE = "Flame Blade"
    FLAME_STRIKE = "Flame Strike"
    FLAMING_SPHERE = "Flaming Sphere"
    FLESH_TO_STONE = "Flesh to Stone"
    FLY = "Fly"
    FOG_CLOUD = "Fog Cloud"
    FORBIDDANCE = "Forbiddance"
    FORCECAGE = "Forcecage"
    FORESIGHT = "Foresight"
    FOUNT_OF_MOONLIGHT = "Fount of Moonlight"
    FREEDOM_OF_MOVEMENT = "Freedom of Movement"
    FRIENDS = "Friends"
    GASEOUS_FORM = "Gaseous Form"
    GATE = "Gate"
    GEAS = "Geas"
    GENTLE_REPOSE = "Gentle Repose"
    GIANT_INSECT = "Giant Insect"
    GLIBNESS = "Glibness"
    GLOBE_OF_INVULNERABILITY = "Globe of Invulnerability"
    GLYPH_OF_WARDING = "Glyph of Warding"
    GOODBERRY = "Goodberry"
    GRASPING_VINE = "Grasping Vine"
    GREASE = "Grease"
    GREATER_INVISIBILITY = "Greater Invisibility"
    GREATER_RESTORATION = "Greater Restoration"
    GREEN_FLAME_BLADE = "Green-Flame Blade"
    GUARDIAN_OF_FAITH = "Guardian of Faith"
    GUARDS_AND_WARDS = "Guards and Wards"
    GUIDANCE = "Guidance"
    GUIDING_BOLT = "Guiding Bolt"
    GUST_OF_WIND = "Gust of Wind"
    HAIL_OF_THORNS = "Hail of Thorns"
    HALLOW = "Hallow"
    HALLUCINATORY_TERRAIN = "Hallucinatory Terrain"
    HARM = "Harm"
    HASTE = "Haste"
    HEAL = "Heal"
    HEALING_WORD = "Healing Word"
    HEAT_METAL = "Heat Metal"
    HELLISH_REBUKE = "Hellish Rebuke"
    HEROES_FEAST = "Heroes' Feast"
    HEROISM = "Heroism"
    HEX = "Hex"
    HOLD_MONSTER = "Hold Monster"
    HOLD_PERSON = "Hold Person"
    HOLY_AURA = "Holy Aura"
    HOLY_STAR_OF_MYSTRA = "Holy Star of Mystra"
    HOMUNCULUS_SERVANT = "Homunculus Servant"
    HUNGER_OF_HADAR = "Hunger of Hadar"
    HUNTER_S_MARK = "Hunter's Mark"
    HYPNOTIC_PATTERN = "Hypnotic Pattern"
    ICE_KNIFE = "Ice Knife"
    ICE_STORM = "Ice Storm"
    IDENTIFY = "Identify"
    ILLUSORY_SCRIPT = "Illusory Script"
    IMPRISONMENT = "Imprisonment"
    INCENDIARY_CLOUD = "Incendiary Cloud"
    INFLICT_WOUNDS = "Inflict Wounds"
    INSECT_PLAGUE = "Insect Plague"
    INSIDIOUS_RHYTHM = "Insidious Rhythm"
    INVISIBILITY = "Invisibility"
    JALLARZI_S_STORM_OF_RADIANCE = "Jallarzi's Storm of Radiance"
    JUMP = "Jump"
    KNOCK = "Knock"
    LAERAL_S_SILVER_LANCE = "Laeral's Silver Lance"
    LEGEND_LORE = "Legend Lore"
    LEOMUND_S_LAMENTABLE_BELABORMENT = "Leomund's Lamentable Belaborment"
    LEOMUND_S_SECRET_CHEST = "Leomund's Secret Chest"
    LEOMUND_S_TINY_HUT = "Leomund's Tiny Hut"
    LESSER_RESTORATION = "Lesser Restoration"
    LEVITATE = "Levitate"
    LIGHT = "Light"
    LIGHTNING_ARROW = "Lightning Arrow"
    LIGHTNING_BOLT = "Lightning Bolt"
    LOCATE_ANIMALS_OR_PLANTS = "Locate Animals or Plants"
    LOCATE_CREATURE = "Locate Creature"
    LOCATE_OBJECT = "Locate Object"
    LONGSTRIDER = "Longstrider"
    MAGE_ARMOR = "Mage Armor"
    MAGE_HAND = "Mage Hand"
    MAGIC_CIRCLE = "Magic Circle"
    MAGIC_JAR = "Magic Jar"
    MAGIC_MISSILE = "Magic Missile"
    MAGIC_MOUTH = "Magic Mouth"
    MAGIC_WEAPON = "Magic Weapon"
    MAJOR_IMAGE = "Major Image"
    MASS_CURE_WOUNDS = "Mass Cure Wounds"
    MASS_HEAL = "Mass Heal"
    MASS_HEALING_WORD = "Mass Healing Word"
    MASS_SUGGESTION = "Mass Suggestion"
    MAZE = "Maze"
    MELD_INTO_STONE = "Meld into Stone"
    MELF_S_ACID_ARROW = "Melf's Acid Arrow"
    MENDING = "Mending"
    MESSAGE = "Message"
    METEOR_SWARM = "Meteor Swarm"
    MIND_BLANK = "Mind Blank"
    MIND_SLIVER = "Mind Sliver"
    MIND_SPIKE = "Mind Spike"
    MINOR_ILLUSION = "Minor Illusion"
    MIRAGE_ARCANE = "Mirage Arcane"
    MIRROR_IMAGE = "Mirror Image"
    MISLEAD = "Mislead"
    MISTY_STEP = "Misty Step"
    MODIFY_MEMORY = "Modify Memory"
    MOONBEAM = "Moonbeam"
    MORDENKAINEN_S_FAITHFUL_HOUND = "Mordenkainen's Faithful Hound"
    MORDENKAINEN_S_MAGNIFICENT_MANSION = "Mordenkainen's Magnificent Mansion"
    MORDENKAINEN_S_PRIVATE_SANCTUM = "Mordenkainen's Private Sanctum"
    MORDENKAINEN_S_SWORD = "Mordenkainen's Sword"
    MOVE_EARTH = "Move Earth"
    NONDETECTION = "Nondetection"
    NYSTUL_S_MAGIC_AURA = "Nystul's Magic Aura"
    OTILUKE_S_FREEZING_SPHERE = "Otiluke's Freezing Sphere"
    OTILUKE_S_RESILIENT_SPHERE = "Otiluke's Resilient Sphere"
    OTTO_S_IRRESISTIBLE_DANCE = "Otto's Irresistible Dance"
    PASSWALL = "Passwall"
    PASS_WITHOUT_TRACE = "Pass without Trace"
    PHANTASMAL_FORCE = "Phantasmal Force"
    PHANTASMAL_KILLER = "Phantasmal Killer"
    PHANTOM_STEED = "Phantom Steed"
    PLANAR_ALLY = "Planar Ally"
    PLANAR_BINDING = "Planar Binding"
    PLANE_SHIFT = "Plane Shift"
    PLANT_GROWTH = "Plant Growth"
    POISON_SPRAY = "Poison Spray"
    POLYMORPH = "Polymorph"
    POWER_WORD_FORTIFY = "Power Word Fortify"
    POWER_WORD_HEAL = "Power Word Heal"
    POWER_WORD_KILL = "Power Word Kill"
    POWER_WORD_STUN = "Power Word Stun"
    PRAYER_OF_HEALING = "Prayer of Healing"
    PRESTIDIGITATION = "Prestidigitation"
    PRISMATIC_SPRAY = "Prismatic Spray"
    PRISMATIC_WALL = "Prismatic Wall"
    PRODUCE_FLAME = "Produce Flame"
    PROGRAMMED_ILLUSION = "Programmed Illusion"
    PROJECT_IMAGE = "Project Image"
    PROTECTION_FROM_ENERGY = "Protection from Energy"
    PROTECTION_FROM_EVIL_AND_GOOD = "Protection from Evil and Good"
    PROTECTION_FROM_POISON = "Protection from Poison"
    PURIFY_FOOD_AND_DRINK = "Purify Food and Drink"
    RAISE_DEAD = "Raise Dead"
    RARY_S_TELEPATHIC_BOND = "Rary's Telepathic Bond"
    RAY_OF_ENFEEBLEMENT = "Ray of Enfeeblement"
    RAY_OF_FROST = "Ray of Frost"
    RAY_OF_SICKNESS = "Ray of Sickness"
    REGENERATE = "Regenerate"
    REINCARNATE = "Reincarnate"
    REMOVE_CURSE = "Remove Curse"
    RESISTANCE = "Resistance"
    RESURRECTION = "Resurrection"
    REVERSE_GRAVITY = "Reverse Gravity"
    REVIVIFY = "Revivify"
    ROPE_TRICK = "Rope Trick"
    SACRED_FLAME = "Sacred Flame"
    SANCTUARY = "Sanctuary"
    SCORCHING_RAY = "Scorching Ray"
    SCRYING = "Scrying"
    SEARING_ORB = "Searing Orb"
    SEARING_SMITE = "Searing Smite"
    SEEMING = "Seeming"
    SEE_INVISIBILITY = "See Invisibility"
    SENDING = "Sending"
    SEQUESTER = "Sequester"
    SHAPECHANGE = "Shapechange"
    SHATTER = "Shatter"
    SHIELD = "Shield"
    SHIELD_OF_FAITH = "Shield of Faith"
    SHILLELAGH = "Shillelagh"
    SHINING_SMITE = "Shining Smite"
    SHOCKING_GRASP = "Shocking Grasp"
    SILENCE = "Silence"
    SILENT_IMAGE = "Silent Image"
    SIMBUL_S_SYNOSTODWEOMER = "Simbul's Synostodweomer"
    SIMULACRUM = "Simulacrum"
    SLEEP = "Sleep"
    SLEET_STORM = "Sleet Storm"
    SLOW = "Slow"
    SONGAL_S_ELEMENTAL_SUFFUSION = "Songal's Elemental Suffusion"
    SORCEROUS_BURST = "Sorcerous Burst"
    SPARE_THE_DYING = "Spare the Dying"
    SPEAK_WITH_ANIMALS = "Speak with Animals"
    SPEAK_WITH_DEAD = "Speak with Dead"
    SPEAK_WITH_PLANTS = "Speak with Plants"
    SPELLFIRE_FLARE = "Spellfire Flare"
    SPELLFIRE_STORM = "Spellfire Storm"
    SPIDER_CLIMB = "Spider Climb"
    SPIKE_GROWTH = "Spike Growth"
    SPIRITUAL_WEAPON = "Spiritual Weapon"
    SPIRIT_GUARDIANS = "Spirit Guardians"
    STAGGERING_SMITE = "Staggering Smite"
    STARRY_WISP = "Starry Wisp"
    STEEL_WIND_STRIKE = "Steel Wind Strike"
    STICKS_TO_SNAKES = "Sticks to Snakes"
    STINKING_CLOUD = "Stinking Cloud"
    STONESKIN = "Stoneskin"
    STONE_SHAPE = "Stone Shape"
    STORM_OF_VENGEANCE = "Storm of Vengeance"
    SUGGESTION = "Suggestion"
    SUMMON_ABERRATION = "Summon Aberration"
    SUMMON_BEAST = "Summon Beast"
    SUMMON_CELESTIAL = "Summon Celestial"
    SUMMON_CONSTRUCT = "Summon Construct"
    SUMMON_DRAGON = "Summon Dragon"
    SUMMON_ELEMENTAL = "Summon Elemental"
    SUMMON_FEY = "Summon Fey"
    SUMMON_FIEND = "Summon Fiend"
    SUMMON_UNDEAD = "Summon Undead"
    SUNBEAM = "Sunbeam"
    SUNBURST = "Sunburst"
    SWIFT_QUIVER = "Swift Quiver"
    SYLUNE_S_VIPER = "Sylune's Viper"
    SYMBOL = "Symbol"
    SYNAPTIC_STATIC = "Synaptic Static"
    TASHA_S_BUBBLING_CAULDRON = "Tasha's Bubbling Cauldron"
    TASHA_S_HIDEOUS_LAUGHTER = "Tasha's Hideous Laughter"
    TELEKINESIS = "Telekinesis"
    TELEPATHY = "Telepathy"
    TELEPORT = "Teleport"
    TELEPORTATION_CIRCLE = "Teleportation Circle"
    TENSER_S_FLOATING_DISK = "Tenser's Floating Disk"
    THAUMATURGY = "Thaumaturgy"
    THORN_WHIP = "Thorn Whip"
    THUNDERCLAP = "Thunderclap"
    THUNDEROUS_SMITE = "Thunderous Smite"
    THUNDERWAVE = "Thunderwave"
    TIME_STOP = "Time Stop"
    TOLL_THE_DEAD = "Toll the Dead"
    TONGUES = "Tongues"
    TORTOISE_SHELL = "Tortoise Shell"
    TRANSPORT_VIA_PLANTS = "Transport via Plants"
    TREE_STRIDE = "Tree Stride"
    TRUE_POLYMORPH = "True Polymorph"
    TRUE_RESURRECTION = "True Resurrection"
    TRUE_SEEING = "True Seeing"
    TRUE_STRIKE = "True Strike"
    TSUNAMI = "Tsunami"
    UNSEEN_SERVANT = "Unseen Servant"
    VAMPIRIC_TOUCH = "Vampiric Touch"
    VICIOUS_MOCKERY = "Vicious Mockery"
    VITRIOLIC_SPHERE = "Vitriolic Sphere"
    VOID_STAR = "Void Star"
    WALL_OF_FIRE = "Wall of Fire"
    WALL_OF_FORCE = "Wall of Force"
    WALL_OF_ICE = "Wall of Ice"
    WALL_OF_STONE = "Wall of Stone"
    WALL_OF_THORNS = "Wall of Thorns"
    WARDAWAY = "Wardaway"
    WARDING_BOND = "Warding Bond"
    WARDING_WIND = "Warding Wind"
    WATER_BREATHING = "Water Breathing"
    WATER_WALK = "Water Walk"
    WEB = "Web"
    WEIRD = "Weird"
    WIND_WALK = "Wind Walk"
    WIND_WALL = "Wind Wall"
    WISH = "Wish"
    WITCH_BOLT = "Witch Bolt"
    WORD_OF_RADIANCE = "Word of Radiance"
    WORD_OF_RECALL = "Word of Recall"
    WRATHFUL_SMITE = "Wrathful Smite"
    YOLANDE_S_REGAL_PRESENCE = "Yolande's Regal Presence"
    ZONE_OF_TRUTH = "Zone of Truth"



class SpellSource(Enum):
    ARCANE_TRICKSTER = "Arcane Trickster"
    ARTIFICER = "Artificer"
    BARD = "Bard"
    CLERIC = "Cleric"
    DRUID = "Druid"
    ELDRITCH_KNIGHT = "Eldritch Knight"
    MAGIC_INITIATE = "Magic Initiate"
    MONSTER_HUNTER = "Monster Hunter"
    PALADIN = "Paladin"
    PHANTOM = "Phantom"
    PSI_WARRIOR = "Psi Warrior"
    RANGER = "Ranger"
    SCION_OF_THE_THREE = "Scion of the Three"
    SORCERER = "Sorcerer"
    WARLOCK = "Warlock"
    WIZARD = "Wizard"


class SpellRangeType(Enum):
    SELF = auto()
    TOUCH = auto()
    DISTANCE = auto()
    SIGHT = auto()
    UNLIMITED = auto()
    SPECIAL = auto()


class SpellAreaShape(Enum):
    NONE = auto()
    RADIUS = auto()
    CONE = auto()
    CUBE = auto()
    LINE = auto()
    CYLINDER = auto()


class SpellDurationUnit(Enum):
    INSTANTANEOUS = auto()
    ROUND = auto()
    MINUTE = auto()
    HOUR = auto()
    DAY = auto()
    UNTIL_DISPELLED = auto()
    SPECIAL = auto()


class SpellAttackType(Enum):
    NONE = auto()
    MELEE_SPELL_ATTACK = auto()
    RANGED_SPELL_ATTACK = auto()


class SpellEffectKind(Enum):
    DAMAGE = auto()
    HEALING = auto()
    TEMPORARY_HIT_POINTS = auto()
    CONDITION = auto()
    DEFENSE = auto()
    MOVEMENT = auto()
    SUMMONING = auto()
    TRANSFORMATION = auto()
    UTILITY = auto()
    SPECIAL = auto()


class SpellEffectTrigger(Enum):
    ON_CAST = auto()
    ON_HIT = auto()
    ON_FAILED_SAVE = auto()
    ON_SUCCESSFUL_SAVE = auto()
    START_OF_TURN = auto()
    END_OF_TURN = auto()
    ENTERS_AREA = auto()
    REPEAT_SAVE = auto()
    SPECIAL = auto()


class SpellEffectTarget(Enum):
    SELF = auto()
    TARGET = auto()
    AREA = auto()
    CREATURES_CHOSEN = auto()
    OBJECT = auto()
    SPECIAL = auto()


class SpellSaveOutcome(Enum):
    NONE = auto()
    NEGATES = auto()
    HALF_DAMAGE = auto()
    PARTIAL = auto()
    SPECIAL = auto()


class SpellLinkedHealingAmount(Enum):
    HALF_DAMAGE_DEALT = auto()


class SpellScalingType(Enum):
    NONE = auto()
    CANTRIP_LEVEL = auto()
    SPELL_SLOT_LEVEL = auto()
    CASTER_LEVEL = auto()
    SPECIAL = auto()


@dataclass(frozen=True)
class SpellNoArea:
    shape: SpellAreaShape = SpellAreaShape.NONE


@dataclass(frozen=True)
class SpellRadiusArea:
    radiusFeet: int
    shape: SpellAreaShape = SpellAreaShape.RADIUS

    @api_field
    def diameterFeet(self) -> int:
        return self.radiusFeet * 2


@dataclass(frozen=True)
class SpellConeArea:
    lengthFeet: int
    shape: SpellAreaShape = SpellAreaShape.CONE


@dataclass(frozen=True)
class SpellCubeArea:
    sizeFeet: int
    shape: SpellAreaShape = SpellAreaShape.CUBE


@dataclass(frozen=True)
class SpellLineArea:
    lengthFeet: int
    widthFeet: int
    shape: SpellAreaShape = SpellAreaShape.LINE


@dataclass(frozen=True)
class SpellCylinderArea:
    radiusFeet: int
    heightFeet: int
    shape: SpellAreaShape = SpellAreaShape.CYLINDER

    @api_field
    def diameterFeet(self) -> int:
        return self.radiusFeet * 2


SpellArea = SpellNoArea | SpellRadiusArea | SpellConeArea | SpellCubeArea | SpellLineArea | SpellCylinderArea


@dataclass(frozen=True)
class SpellTargeting:
    rangeType: SpellRangeType
    distanceFeet: int = 0
    area: SpellArea = SpellNoArea()

    @api_field
    def summary(self) -> str:
        range_label = spell_target_range_label(self)
        area_label = spell_area_label(self.area)
        return f"{range_label}, {area_label}" if area_label else range_label


@dataclass(frozen=True)
class SpellDuration:
    unit: SpellDurationUnit
    amount: int = 0
    maximum: bool = False

    @api_field
    def summary(self) -> str:
        if self.unit == SpellDurationUnit.INSTANTANEOUS:
            return "Instantaneous"
        if self.unit == SpellDurationUnit.UNTIL_DISPELLED:
            return "Until dispelled"
        if self.unit == SpellDurationUnit.SPECIAL:
            return "Special"
        unit = enum_label(self.unit).lower()
        plural = "s" if self.amount != 1 else ""
        prefix = "Up to " if self.maximum else ""
        return f"{prefix}{self.amount} {unit}{plural}"


class ConditionType(Enum):
    BANE = auto()
    BLINDED = auto()
    BLESSED = auto()
    CHARMED = auto()
    COMMAND_APPROACH = auto()
    COMMAND_DROP = auto()
    COMMAND_FLEE = auto()
    COMMAND_GROVEL = auto()
    COMMAND_HALT = auto()
    DEAFENED = auto()
    EXHAUSTION = auto()
    FAERIE_FIRE = auto()
    FLYING = auto()
    FRIGHTENED = auto()
    GRAPPLED = auto()
    GUIDANCE = auto()
    HASTED = auto()
    INCAPACITATED = auto()
    INVISIBLE = auto()
    LONGSTRIDER = auto()
    MAGE_ARMOR = auto()
    PARALYZED = auto()
    PETRIFIED = auto()
    POISONED = auto()
    PRONE = auto()
    PROTECTION_FROM_POISON = auto()
    RESISTANCE_ACID = auto()
    RESISTANCE_BLUDGEONING = auto()
    RESISTANCE_COLD = auto()
    RESISTANCE_FIRE = auto()
    RESISTANCE_FORCE = auto()
    RESISTANCE_LIGHTNING = auto()
    RESISTANCE_NECROTIC = auto()
    RESISTANCE_PIERCING = auto()
    RESISTANCE_POISON = auto()
    RESISTANCE_PSYCHIC = auto()
    RESISTANCE_RADIANT = auto()
    RESISTANCE_SLASHING = auto()
    RESISTANCE_THUNDER = auto()
    RESTRAINED = auto()
    SHIELDED = auto()
    SHIELD_OF_FAITH = auto()
    SLOWED = auto()
    STUNNED = auto()
    UNCONSCIOUS = auto()


class ConditionApplicationMode(Enum):
    TARGET_SAVE = auto()
    SOURCE_CHECK = auto()
    DIRECT = auto()
    MANUAL = auto()


class ConditionDuration(Enum):
    MANUAL = auto()
    UNTIL_SHORT_REST = auto()
    UNTIL_LONG_REST = auto()


class ConditionRemovalTrigger(Enum):
    AFTER_TAKING_DAMAGE = auto()


class RollModifierEffectOperation(Enum):
    ADD = auto()
    SUBTRACT = auto()


class RollModifierEffectTarget(Enum):
    ABILITY_CHECK = auto()
    ATTACK_ROLL = auto()
    SAVING_THROW = auto()
    ARMOR_CLASS = auto()


class WeaponProperty(Enum):
    AMMUNITION = auto()
    FINESSE = auto()
    HEAVY = auto()
    LIGHT = auto()
    THROWN = auto()
    TWO_HANDED = auto()
    VERSATILE = auto()


class AttackRangeType(Enum):
    MELEE = auto()
    RANGED = auto()


class WeaponCategory(Enum):
    MELEE = auto()
    RANGED = auto()


class CurrencyUnit(Enum):
    CP = "CP"
    SP = "SP"
    GP = "GP"


@dataclass(frozen=True)
class Money:
    quantity: int = 0
    unit: CurrencyUnit = CurrencyUnit.GP

    @property
    def label(self) -> str:
        return f"{self.quantity} {self.unit.value}"


@dataclass
class Purse:
    copper: int = 0
    silver: int = 0
    gold: int = 0


class EquipmentType(Enum):
    ARMOR = auto()
    GEAR = auto()
    SHIELD = auto()
    WEAPON = auto()


class EquipmentSlot(Enum):
    CARRIED = auto()
    MAIN_HAND = auto()
    OFF_HAND = auto()
    TWO_HANDS = auto()
    ARMOR = auto()


class ArmorCategory(Enum):
    LIGHT = auto()
    MEDIUM = auto()
    HEAVY = auto()


class AttackDamageAbilityModifierMode(Enum):
    INCLUDED = auto()
    EXCLUDED = auto()


class AttackKind(Enum):
    STANDARD = auto()
    TWO_WEAPON_FIGHTING = auto()


class AttackActionType(Enum):
    STANDARD = auto()
    UNARMED_STRIKE = auto()
    THROWN_WEAPON = auto()


class DiceType(Enum):
    D4 = 4
    D6 = 6
    D8 = 8
    D10 = 10
    D12 = 12
    D20 = 20


class TimeEconomy(Enum):
    ACTION = auto()
    BONUS_ACTION = auto()
    REACTION = auto()
    MOVEMENT = auto()
    PASSIVE = auto()
    SPECIAL = auto()


class ProficiencyLevel(Enum):
    NONE = auto()
    PROFICIENT = auto()
    EXPERTISE = auto()


class RestType(Enum):
    NONE = auto()
    SHORT_REST = auto()
    LONG_REST = auto()


@dataclass(frozen=True)
class SpellEffectDice:
    diceCount: int
    diceType: DiceType
    staticBonus: int = 0
    bonusAbility: AbilityType | None = None
    bonusSpellcastingAbility: bool = False

    @api_field
    def dice(self) -> str:
        return dice_formula(self.diceCount, self.diceType)


@dataclass(frozen=True)
class SpellDamageEffect:
    dice: SpellEffectDice
    damageType: DamageType


@dataclass(frozen=True)
class SpellHealingEffect:
    dice: SpellEffectDice


@dataclass(frozen=True)
class SpellSourceHealingEffect:
    amount: SpellLinkedHealingAmount


@dataclass(frozen=True)
class SpellConditionEffect:
    condition: ConditionType
    duration: ConditionDuration = ConditionDuration.MANUAL
    saveEnds: bool = False
    removalTrigger: ConditionRemovalTrigger | None = None
    removalAdvantage: bool = False


@dataclass(frozen=True)
class SpellRollModifierEffect:
    condition: ConditionType
    operation: RollModifierEffectOperation
    targets: list[RollModifierEffectTarget]
    dice: SpellEffectDice | None = None
    staticBonus: int = 0
    description: str = ""


@dataclass(frozen=True)
class SpellSavingThrow:
    ability: AbilityType
    outcome: SpellSaveOutcome = SpellSaveOutcome.NEGATES
    repeat: SpellEffectTrigger | None = None
    disadvantageCreatureTypes: list[CreatureType] | None = None


@dataclass(frozen=True)
class SpellScaling:
    scalingType: SpellScalingType
    additionalDice: SpellEffectDice | None = None
    additionalStaticBonus: int = 0
    additionalInstances: int = 0
    interval: int = 1
    description: str = ""


@dataclass(frozen=True)
class SpellEffect:
    kind: SpellEffectKind
    trigger: SpellEffectTrigger = SpellEffectTrigger.ON_CAST
    target: SpellEffectTarget = SpellEffectTarget.TARGET
    attack: SpellAttackType = SpellAttackType.NONE
    targetCreatureTypes: list[CreatureType] | None = None
    savingThrow: SpellSavingThrow | None = None
    damage: SpellDamageEffect | None = None
    healing: SpellHealingEffect | None = None
    sourceHealing: SpellSourceHealingEffect | None = None
    temporaryHitPoints: SpellEffectDice | None = None
    conditions: list[SpellConditionEffect] | None = None
    rollModifier: SpellRollModifierEffect | None = None
    scaling: list[SpellScaling] | None = None
    restType: RestType | None = None
    instances: int = 1
    instanceLabel: str = ""
    actionLabel: str = ""
    description: str = ""


class ClassType(Enum):
    ADVENTURER = auto()
    ARTIFICER = auto()
    BARD = auto()
    CLERIC = auto()
    CREATURE = auto()
    DRUID = auto()
    FIGHTER = auto()
    PALADIN = auto()
    RANGER = auto()
    ROGUE = auto()
    SORCERER = auto()
    WARLOCK = auto()
    WIZARD = auto()


class FightingStyleType(Enum):
    ARCHERY = auto()
    BLIND_FIGHTING = auto()
    CLOSE_QUARTERS_SHOOTER = auto()
    DEFENSE = auto()
    DUELING = auto()
    GREAT_WEAPON_FIGHTING = auto()
    INTERCEPTION = auto()
    MARINER = auto()
    PACK_FIGHTING = auto()
    PRONE_FIGHTING = auto()
    PROTECTION = auto()
    SUPERIOR_TECHNIQUE = auto()
    THROWN_WEAPON_FIGHTING = auto()
    TUNNEL_FIGHTER = auto()
    TWO_WEAPON_FIGHTING = auto()
    UNARMED_FIGHTING = auto()


class BattleMasterManeuverType(Enum):
    AMBUSH = auto()
    BAIT_AND_SWITCH = auto()
    BRACE = auto()
    COMMANDERS_STRIKE = auto()
    COMMANDING_PRESENCE = auto()
    DISARMING_ATTACK = auto()
    DISTRACTING_STRIKE = auto()
    EVASIVE_FOOTWORK = auto()
    FEINTING_ATTACK = auto()
    GOADING_ATTACK = auto()
    GRAPPLING_STRIKE = auto()
    LUNGING_ATTACK = auto()
    MANEUVERING_ATTACK = auto()
    MENACING_ATTACK = auto()
    PARRY = auto()
    PRECISION_ATTACK = auto()
    PUSHING_ATTACK = auto()
    QUICK_TOSS = auto()
    RALLY = auto()
    RIPOSTE = auto()
    SWEEPING_ATTACK = auto()
    TACTICAL_ASSESSMENT = auto()
    TRIP_ATTACK = auto()


class ArcaneShotType(Enum):
    BANISHING_ARROW = auto()
    BEGUILING_ARROW = auto()
    BURSTING_ARROW = auto()
    ENFEEBLING_ARROW = auto()
    GRASPING_ARROW = auto()
    PIERCING_ARROW = auto()
    SEEKING_ARROW = auto()
    SHADOW_ARROW = auto()


class RuneType(Enum):
    CLOUD_RUNE = auto()
    FIRE_RUNE = auto()
    FROST_RUNE = auto()
    STONE_RUNE = auto()
    HILL_RUNE = auto()
    STORM_RUNE = auto()


@dataclass
class AbilityScores:
    strength: int
    dexterity: int
    constitution: int
    intelligence: int
    wisdom: int
    charisma: int


@dataclass
class HitPoints:
    current: int
    max: int
    temporary: int


@dataclass(frozen=True)
class ConditionEffect:
    condition: ConditionType | None
    mode: ConditionApplicationMode
    savingThrow: AbilityType | None = None
    saveDcAbility: AbilityType | None = None
    saveDc: int | None = None
    sourceCheck: AbilityType | None = None
    contestChecks: list[AbilityType] | None = None
    duration: ConditionDuration = ConditionDuration.MANUAL
    removalTrigger: ConditionRemovalTrigger | None = None
    removalSavingThrow: AbilityType | None = None
    removalSaveDc: int | None = None
    removalAdvantage: bool = False
    description: str = ""


@dataclass
class AttackAction:
    id: str
    name: str
    ability: AbilityType
    damageDiceCount: int
    damageDiceType: DiceType
    proficient: bool = True
    damageType: DamageType = DamageType.SLASHING
    toHitBonus: int = 0
    damageBonus: int = 0
    activation: TimeEconomy = TimeEconomy.ACTION
    attackRange: AttackRangeType = AttackRangeType.MELEE
    weaponCategory: WeaponCategory = WeaponCategory.MELEE
    damageAbilityModifier: AttackDamageAbilityModifierMode = AttackDamageAbilityModifierMode.INCLUDED
    attackKind: AttackKind = AttackKind.STANDARD
    attackType: AttackActionType = AttackActionType.STANDARD
    properties: list[WeaponProperty] | None = None

    @api_field
    def damageDie(self) -> str:
        return dice_formula(self.damageDiceCount, self.damageDiceType)


@dataclass
class RollAction:
    id: Enum
    name: Enum
    diceCount: int
    diceType: DiceType
    modifier: RollModifierType = RollModifierType.NONE
    modifierAbility: AbilityType | None = None
    staticModifier: int = 0
    resolution: RollResolutionMode = RollResolutionMode.NONE
    consumesResource: Enum | None = None
    description: str | None = None
    activation: TimeEconomy | None = None
    source: str | None = None
    damageType: DamageType | None = None
    conditionEffects: list[ConditionEffect] | None = None

    @api_field
    def dice(self) -> str:
        return dice_formula(self.diceCount, self.diceType)


@dataclass
class RollModifierBreakdown:
    source: str
    value: int
    description: str = ""


@dataclass
class RollSource:
    section: SheetSectionType
    sourceId: str
    actionId: str


@dataclass
class CharacterClassLevel:
    name: ClassType
    level: int
    subclass: Enum | None = None
    fightingStyle: FightingStyleType | None = None
    fightingStyles: list[FightingStyleType] | None = None
    maneuvers: list[BattleMasterManeuverType] | None = None
    arcaneShots: list[ArcaneShotType] | None = None
    runes: list[RuneType] | None = None


@dataclass
class SkillBonus:
    name: str
    ability: AbilityType
    proficiency: ProficiencyLevel
    modifier: int
    passive: int


@dataclass
class SavingThrowBonus:
    ability: AbilityType
    proficient: bool
    modifier: int


@dataclass
class ProgressionChoiceOption:
    value: str
    label: str


@dataclass
class ProgressionChoice:
    id: str
    choiceType: ProgressionChoiceType
    label: str
    description: str
    minimum: int
    maximum: int
    selected: list[str]
    options: list[ProgressionChoiceOption]


@dataclass
class ResourceTracker:
    id: str
    name: str
    currentUses: int
    maxUses: int
    reset: RestType
    activation: TimeEconomy
    description: str
    rollActions: list[RollAction] | None = None
    source: str | None = None
    spellSlotLevel: int | None = None


@dataclass
class SheetAbility:
    id: str
    name: str
    source: str
    activation: TimeEconomy
    description: str
    resourceId: str | None = None
    rollActions: list[RollAction] | None = None
    conditionEffects: list[ConditionEffect] | None = None


@dataclass
class SheetFeature:
    id: str
    name: str
    source: str
    activation: TimeEconomy
    description: str
    rollActions: list[RollAction] | None = None
    conditionEffects: list[ConditionEffect] | None = None


@dataclass(frozen=True)
class SpellStatus:
    source: SpellSource | None = None
    castingAbility: AbilityType | None = None
    resourceId: str | None = None
    reset: RestType = RestType.NONE


@dataclass
class SpellEntry:
    id: SpellId
    name: SpellId
    level: int
    school: SpellSchool
    castingTime: TimeEconomy
    targeting: SpellTargeting
    duration: SpellDuration
    components: list[SpellComponent]
    description: str
    concentration: bool = False
    ritual: bool = False
    castingDuration: SpellDuration | None = None
    effects: list[SpellEffect] | None = None
    status: SpellStatus = field(default_factory=SpellStatus)

    @api_field
    def castingTimeLabel(self) -> str:
        if self.castingDuration is not None:
            return self.castingDuration.summary
        return enum_label(self.castingTime)

    @api_field
    def source(self) -> SpellSource | None:
        return self.status.source

    @api_field
    def sourceLabel(self) -> str:
        return enum_label(self.status.source) if self.status.source is not None else ""

    @api_field
    def castingAbility(self) -> AbilityType | None:
        return self.status.castingAbility

    @api_field
    def castingAbilityLabel(self) -> str:
        return enum_label(self.status.castingAbility) if self.status.castingAbility is not None else ""

    @api_field
    def resourceId(self) -> str | None:
        return self.status.resourceId

    @api_field
    def reset(self) -> RestType:
        return self.status.reset

    @api_field
    def resetLabel(self) -> str:
        return enum_label(self.status.reset)


@dataclass
class EquipmentItem:
    id: str
    name: str
    equipped: bool = False
    quantity: int = 1
    weight: float = 0.0
    notes: str = ""
    itemType: EquipmentType = EquipmentType.GEAR
    slot: EquipmentSlot = EquipmentSlot.CARRIED
    armorCategory: ArmorCategory | None = None
    armorClass: int = 0
    armorClassBonus: int = 0


@dataclass
class PartyMemberSheet:
    race: str | None = None
    background: str | None = None
    alignment: str | None = None
    classes: list[CharacterClassLevel] | None = None
    armorClass: int | None = None
    speed: int | None = None
    proficiencyBonus: int | None = None
    skills: dict[str, ProficiencyLevel] | None = None
    savingThrowProficiencies: list[AbilityType] | None = None
    proficiencies: list[str] | None = None
    feats: list[SheetFeature] | None = None
    traits: list[SheetFeature] | None = None
    features: list[SheetFeature] | None = None
    resources: list[ResourceTracker] | None = None
    spells: list[SpellEntry] | None = None
    spellbook: list[SpellEntry] | None = None
    hitPointIncreases: list[int] | None = None
    abilityScoreImprovements: list[str] | None = None
    conditions: list[ConditionType] | None = None
    creatureTypes: list[CreatureType] | None = None
    damageResistances: list[DamageType] | None = None
    damageVulnerabilities: list[DamageType] | None = None
    damageImmunities: list[DamageType] | None = None
    attacks: list[AttackAction] | None = None
    equipment: list[EquipmentItem] | None = None
    purse: Purse | None = None


@dataclass
class PartyMemberConfig:
    id: str
    name: str
    image: str | None = None
    maxHp: int | None = None
    abilityScores: AbilityScores | None = None
    sheet: PartyMemberSheet | None = None


@dataclass
class PartyManifest:
    members: list[PartyMemberConfig]


@dataclass
class CharacterClass:
    name: ClassType
    level: int


@dataclass
class CharacterSheet:
    id: str
    tokenId: str
    kind: TokenKind
    name: str
    owner: str
    avatarUrl: str | None
    characterClass: CharacterClass
    classes: list[CharacterClassLevel]
    race: str
    background: str
    alignment: str
    proficiencyBonus: int
    hp: HitPoints
    abilityScores: AbilityScores
    abilityModifiers: dict[str, int]
    armorClass: int
    initiativeBonus: int
    speed: int
    savingThrows: list[SavingThrowBonus]
    skills: list[SkillBonus]
    passiveChecks: dict[str, int]
    pendingChoices: list[ProgressionChoice]
    resources: list[ResourceTracker]
    abilities: list[SheetAbility]
    features: list[SheetFeature]
    spells: list[SpellEntry]
    spellbook: list[SpellEntry]
    proficiencies: list[str]
    conditions: list[ConditionType]
    creatureTypes: list[CreatureType]
    damageResistances: list[DamageType]
    damageVulnerabilities: list[DamageType]
    damageImmunities: list[DamageType]
    attacks: list[AttackAction]
    equipment: list[EquipmentItem]
    purse: Purse = field(default_factory=Purse)


@dataclass
class RollPayload:
    id: str
    sheetId: str
    tokenId: str
    roller: str
    source: RollSource
    sourceLabel: str
    resolution: RollResolutionMode
    label: str
    iconUrl: str | None
    dice: list[int]
    diceType: DiceType
    die: str
    modifier: int
    modifierBreakdown: list[RollModifierBreakdown]
    total: int
    createdAt: int
    advantageConditions: list[ConditionType] | None = None
    disadvantageConditions: list[ConditionType] | None = None
    damageType: DamageType | None = None
    damageSavingThrow: AbilityType | None = None
    damageSaveDc: int | None = None
    damageSaveOutcome: SpellSaveOutcome | None = None
    damageSaveDisadvantageCreatureTypes: list[CreatureType] | None = None
    targetCreatureTypes: list[CreatureType] | None = None
    sourceHealing: SpellSourceHealingEffect | None = None
    conditionEffects: list[ConditionEffect] | None = None
    restType: RestType | None = None
    resourceSpent: RollResourceSpend | None = None


@dataclass
class RollResourceSpend:
    resourceId: str
    resourceName: str
    remainingUses: int
    maxUses: int


@dataclass
class RollResolution:
    id: str
    roll: RollPayload
    targetSheetId: str
    targetTokenId: str
    targetName: str
    targetArmorClass: int
    targetHp: HitPoints
    targetConditions: list[ConditionType]
    outcome: str
    createdAt: int
    responseRolls: list[RollPayload] | None = None


@dataclass
class RollLogEntry:
    id: str
    entryType: RollLogEntryType
    createdAt: int
    roll: RollPayload
    resolution: RollResolution | None = None


@dataclass
class PartyMember:
    id: str
    name: str
    owner: str
    avatarUrl: str | None
    abilityScores: AbilityScores | None = None
    maxHp: int | None = None
    sheet: PartyMemberSheet | None = None


ABILITY_NAMES = [
    AbilityType.STRENGTH,
    AbilityType.DEXTERITY,
    AbilityType.CONSTITUTION,
    AbilityType.INTELLIGENCE,
    AbilityType.WISDOM,
    AbilityType.CHARISMA,
]
SKILL_ABILITIES = {
    enum_key(SkillType.ATHLETICS): AbilityType.STRENGTH,
    enum_key(SkillType.ACROBATICS): AbilityType.DEXTERITY,
    enum_key(SkillType.SLEIGHT_OF_HAND): AbilityType.DEXTERITY,
    enum_key(SkillType.STEALTH): AbilityType.DEXTERITY,
    enum_key(SkillType.ARCANA): AbilityType.INTELLIGENCE,
    enum_key(SkillType.HISTORY): AbilityType.INTELLIGENCE,
    enum_key(SkillType.INVESTIGATION): AbilityType.INTELLIGENCE,
    enum_key(SkillType.NATURE): AbilityType.INTELLIGENCE,
    enum_key(SkillType.RELIGION): AbilityType.INTELLIGENCE,
    enum_key(SkillType.ANIMAL_HANDLING): AbilityType.WISDOM,
    enum_key(SkillType.INSIGHT): AbilityType.WISDOM,
    enum_key(SkillType.MEDICINE): AbilityType.WISDOM,
    enum_key(SkillType.PERCEPTION): AbilityType.WISDOM,
    enum_key(SkillType.SURVIVAL): AbilityType.WISDOM,
    enum_key(SkillType.DECEPTION): AbilityType.CHARISMA,
    enum_key(SkillType.INTIMIDATION): AbilityType.CHARISMA,
    enum_key(SkillType.PERFORMANCE): AbilityType.CHARISMA,
    enum_key(SkillType.PERSUASION): AbilityType.CHARISMA,
}

TYPE_KEY = "$type"
FIELDS_KEY = "fields"
ITEMS_KEY = "items"
VALUE_KEY = "value"


def build_character_sheet(
    *,
    token_id: str,
    kind: TokenKind,
    name: str,
    owner: str,
    avatar_url: str | None,
    party_member: PartyMember | None,
    current_hp: int | None,
    resource_overrides: dict[str, int],
    equipment_slot_overrides: dict[str, EquipmentSlot] | None = None,
) -> CharacterSheet:
    ability_scores = party_member.abilityScores if party_member and party_member.abilityScores else generated_ability_scores(token_id)
    max_hp = party_member.maxHp if party_member and party_member.maxHp is not None else generated_max_hp(token_id, ability_scores)
    dexterity_modifier = ability_modifier(ability_scores.dexterity)
    sheet_config = party_member.sheet if party_member else None
    classes = sheet_config.classes if sheet_config and sheet_config.classes else [CharacterClassLevel(name=ClassType.ADVENTURER if kind == TokenKind.CHARACTER else ClassType.CREATURE, level=1)]
    total_level = sum(character_class.level for character_class in classes) or 1
    primary_class = classes[0]
    proficiency_bonus = sheet_config.proficiencyBonus if sheet_config and sheet_config.proficiencyBonus is not None else proficiency_bonus_for_level(total_level)
    ability_modifiers = ability_modifier_map(ability_scores)
    skill_proficiencies = sheet_config.skills if sheet_config and sheet_config.skills else {}
    save_proficiencies = set(sheet_config.savingThrowProficiencies if sheet_config and sheet_config.savingThrowProficiencies else default_save_proficiencies(classes))
    configured_spells = hydrated_spell_entries(sheet_config.spells if sheet_config and sheet_config.spells else [])
    configured_spellbook = hydrated_spell_entries(sheet_config.spellbook if sheet_config and sheet_config.spellbook else [])
    configured_feats = sheet_config.feats if sheet_config and sheet_config.feats else []
    resources = apply_resource_overrides(sheet_config.resources if sheet_config and sheet_config.resources else default_resources(classes, ability_scores, configured_feats, proficiency_bonus), resource_overrides)
    feat_abilities = default_feat_abilities(classes, configured_feats)
    subclass_abilities = default_subclass_abilities(classes)
    abilities = [*resource_roll_abilities(resources), *feat_abilities, *subclass_abilities]
    features = default_features(classes)
    hit_point_increases = sheet_config.hitPointIncreases if sheet_config and sheet_config.hitPointIncreases else []
    ability_score_improvements = sheet_config.abilityScoreImprovements if sheet_config and sheet_config.abilityScoreImprovements else []
    feat_eligibility_sheet = SimpleNamespace(
        race=sheet_config.race if sheet_config and sheet_config.race else "",
        background=sheet_config.background if sheet_config and sheet_config.background else "",
        abilityScores=ability_scores,
        classes=classes,
        proficiencies=sheet_config.proficiencies if sheet_config and sheet_config.proficiencies else [],
        feats=configured_feats,
        features=[*features, *(sheet_config.features if sheet_config and sheet_config.features else [])],
        abilities=abilities,
        spells=configured_spells,
    )
    pending_choices = default_progression_choices(classes, configured_spells, hit_point_increases, ability_score_improvements, skill_proficiencies, configured_feats, feat_eligibility_sheet, spellbook=configured_spellbook)
    spells = [*default_spells(classes), *default_spellcasting_spells(classes, configured_spells)]
    if sheet_config:
        features = [*(sheet_config.traits or []), *features, *(sheet_config.features or []), *(sheet_config.feats or [])]
    equipment = apply_equipment_slot_overrides(sheet_config.equipment if sheet_config and sheet_config.equipment else [], equipment_slot_overrides or {})
    purse = sheet_config.purse if sheet_config and sheet_config.purse else Purse()
    armor_class = base_armor_class(sheet_config, equipment, dexterity_modifier)
    armor_class += default_armor_class_bonus(classes, equipment)
    attacks = sheet_config.attacks if sheet_config and sheet_config.attacks else default_attacks(kind)
    attacks = default_feat_attacks(classes, equipment, attacks)
    max_hp += default_feat_hit_point_bonus(configured_feats, total_level)
    speed = (sheet_config.speed if sheet_config and sheet_config.speed is not None else 30) + default_feat_speed_bonus(configured_feats)

    return CharacterSheet(
        id=token_id,
        tokenId=token_id,
        kind=kind,
        name=name,
        owner=owner,
        avatarUrl=avatar_url,
        characterClass=CharacterClass(name=primary_class.name, level=primary_class.level),
        classes=classes,
        race=sheet_config.race if sheet_config and sheet_config.race else "",
        background=sheet_config.background if sheet_config and sheet_config.background else "",
        alignment=sheet_config.alignment if sheet_config and sheet_config.alignment else "",
        proficiencyBonus=proficiency_bonus,
        hp=HitPoints(current=clamp_int(current_hp, 0, max_hp) if current_hp is not None else max_hp, max=max_hp, temporary=0),
        abilityScores=ability_scores,
        abilityModifiers=ability_modifiers,
        armorClass=armor_class,
        initiativeBonus=dexterity_modifier + default_feat_initiative_bonus(configured_feats, proficiency_bonus),
        speed=speed,
        savingThrows=build_saving_throws(ability_modifiers, save_proficiencies, proficiency_bonus),
        skills=build_skills(ability_modifiers, skill_proficiencies, proficiency_bonus),
        passiveChecks=build_passive_checks(ability_modifiers, skill_proficiencies, proficiency_bonus),
        pendingChoices=pending_choices,
        resources=resources,
        abilities=abilities,
        features=features,
        spells=spells,
        spellbook=configured_spellbook,
        proficiencies=sheet_config.proficiencies if sheet_config and sheet_config.proficiencies else [],
        conditions=sheet_config.conditions if sheet_config and sheet_config.conditions else [],
        creatureTypes=sheet_config.creatureTypes if sheet_config and sheet_config.creatureTypes else [CreatureType.HUMANOID] if kind == TokenKind.CHARACTER else [],
        damageResistances=sheet_config.damageResistances if sheet_config and sheet_config.damageResistances else [],
        damageVulnerabilities=sheet_config.damageVulnerabilities if sheet_config and sheet_config.damageVulnerabilities else [],
        damageImmunities=sheet_config.damageImmunities if sheet_config and sheet_config.damageImmunities else [],
        attacks=attacks,
        equipment=equipment,
        purse=purse,
    )


def build_attack_roll_payload(sheet: CharacterSheet, roller: str, action: AttackAction) -> RollPayload:
    ability_score = getattr(sheet.abilityScores, enum_key(action.ability))
    modifier_breakdown = [
        RollModifierBreakdown(source=enum_label(action.ability), value=ability_modifier(ability_score)),
        *attack_roll_modifier_breakdown(sheet.classes, action),
    ]
    if action.toHitBonus:
        modifier_breakdown.append(RollModifierBreakdown(source=f"{action.name} Attack Bonus", value=action.toHitBonus))
    created_at = time_ns()
    if action.proficient:
        modifier_breakdown.append(RollModifierBreakdown(source="Proficiency", value=sheet.proficiencyBonus))
    modifier_breakdown.extend(active_roll_modifier_breakdown(sheet, RollModifierEffectTarget.ATTACK_ROLL))
    modifier = sum(part.value for part in modifier_breakdown)

    dice = [random.randint(1, 20)]
    return RollPayload(
        id=f"roll-{created_at}",
        sheetId=sheet.id,
        tokenId=sheet.tokenId,
        roller=roller,
        source=RollSource(section=SheetSectionType.ATTACKS, sourceId=action.id, actionId=enum_key(RollResolutionMode.ATTACK_VS_ARMOR_CLASS)),
        sourceLabel=action.name,
        resolution=RollResolutionMode.ATTACK_VS_ARMOR_CLASS,
        label="Attack Roll",
        iconUrl=None,
        dice=dice,
        diceType=DiceType.D20,
        die=enum_key(DiceType.D20),
        modifier=modifier,
        modifierBreakdown=modifier_breakdown,
        total=sum(dice) + modifier,
        createdAt=created_at,
        damageType=action.damageType,
    )


def build_damage_roll_payload(sheet: CharacterSheet, roller: str, action: AttackAction) -> RollPayload:
    ability_score = getattr(sheet.abilityScores, enum_key(action.ability))
    modifier_breakdown = []
    if action.damageAbilityModifier == AttackDamageAbilityModifierMode.INCLUDED:
        modifier_breakdown.append(RollModifierBreakdown(source=enum_label(action.ability), value=ability_modifier(ability_score)))
    modifier_breakdown.extend(damage_roll_modifier_breakdown(sheet.classes, sheet.equipment, action, ability_modifier(ability_score)))
    if action.toHitBonus:
        modifier_breakdown.append(RollModifierBreakdown(source=f"{action.name} Attack Bonus", value=action.toHitBonus))
    if action.damageBonus:
        modifier_breakdown.append(RollModifierBreakdown(source=f"{action.name} Damage Bonus", value=action.damageBonus))
    modifier = sum(part.value for part in modifier_breakdown)
    count = action.damageDiceCount
    sides = action.damageDiceType.value
    dice = [random.randint(1, sides) for _ in range(count)]
    if uses_great_weapon_fighting(sheet.classes, action):
        dice = [max(3, roll) for roll in dice]
        modifier_breakdown.append(RollModifierBreakdown(source="Great Weapon Fighting", value=0, description="Treated weapon damage dice of 1 or 2 as 3."))
    created_at = time_ns()
    return RollPayload(
        id=f"roll-{created_at}",
        sheetId=sheet.id,
        tokenId=sheet.tokenId,
        roller=roller,
        source=RollSource(section=SheetSectionType.ATTACKS, sourceId=action.id, actionId=enum_key(RollResolutionMode.APPLY_DAMAGE)),
        sourceLabel=action.name,
        resolution=RollResolutionMode.APPLY_DAMAGE,
        label="Damage Roll",
        iconUrl=None,
        dice=dice,
        diceType=action.damageDiceType,
        die=damage_die_formula(action),
        modifier=modifier,
        modifierBreakdown=modifier_breakdown,
        total=sum(dice) + modifier,
        createdAt=created_at,
        damageType=action.damageType,
    )


def build_spell_attack_roll_payload(sheet: CharacterSheet, roller: str, spell: SpellEntry) -> RollPayload:
    casting_ability = spell_casting_ability(sheet, spell)
    ability_score = getattr(sheet.abilityScores, enum_key(casting_ability))
    modifier_breakdown = [
        RollModifierBreakdown(source=enum_label(casting_ability), value=ability_modifier(ability_score)),
        RollModifierBreakdown(source="Proficiency", value=sheet.proficiencyBonus),
    ]
    modifier_breakdown.extend(active_roll_modifier_breakdown(sheet, RollModifierEffectTarget.ATTACK_ROLL))
    modifier = sum(part.value for part in modifier_breakdown)
    dice = [random.randint(1, 20)]
    created_at = time_ns()
    return RollPayload(
        id=f"roll-{created_at}",
        sheetId=sheet.id,
        tokenId=sheet.tokenId,
        roller=roller,
        source=RollSource(section=SheetSectionType.SPELLS, sourceId=enum_key(spell.id), actionId=enum_key(RollResolutionMode.ATTACK_VS_ARMOR_CLASS)),
        sourceLabel=enum_label(spell.name),
        resolution=RollResolutionMode.ATTACK_VS_ARMOR_CLASS,
        label="Spell Attack",
        iconUrl=None,
        dice=dice,
        diceType=DiceType.D20,
        die=enum_key(DiceType.D20),
        modifier=modifier,
        modifierBreakdown=modifier_breakdown,
        total=sum(dice) + modifier,
        createdAt=created_at,
        damageType=first_spell_damage_type(spell),
    )


def build_spell_damage_roll_payload(
    sheet: CharacterSheet,
    roller: str,
    spell: SpellEntry,
    effect_index: int = 0,
    spell_slot_level: int | None = None,
    instance_index: int | None = None,
) -> RollPayload:
    effect = spell_damage_effect_at(spell, effect_index)
    if effect is None or effect.damage is None:
        raise ValueError("Spell damage effect not found")

    instance_count = scaled_spell_effect_instance_count(effect, sheet, spell.level, spell_slot_level)
    if instance_index is not None and (instance_index < 0 or instance_index >= instance_count):
        raise ValueError("Spell damage instance not found")
    active_instance_index = instance_index if instance_index is not None else 0
    dice_count = scaled_spell_effect_dice_count(effect.damage.dice.diceCount, effect.scaling, sheet, spell.level, spell_slot_level)
    dice_type = effect.damage.dice.diceType
    dice = [random.randint(1, dice_type.value) for _ in range(dice_count)]
    modifier_breakdown = []
    static_bonus = effect.damage.dice.staticBonus
    if static_bonus:
        modifier_breakdown.append(RollModifierBreakdown(source="Spell", value=static_bonus))
    if effect.damage.dice.bonusAbility is not None:
        ability_score = getattr(sheet.abilityScores, enum_key(effect.damage.dice.bonusAbility))
        modifier_breakdown.append(RollModifierBreakdown(source=enum_label(effect.damage.dice.bonusAbility), value=ability_modifier(ability_score)))
    if effect.damage.dice.bonusSpellcastingAbility:
        casting_ability = spell_casting_ability(sheet, spell)
        ability_score = getattr(sheet.abilityScores, enum_key(casting_ability))
        modifier_breakdown.append(RollModifierBreakdown(source=enum_label(casting_ability), value=ability_modifier(ability_score)))
    scaled_static_bonus = scaled_spell_effect_static_bonus(effect.damage.dice.staticBonus, effect.scaling, spell.level, spell_slot_level)
    if scaled_static_bonus != effect.damage.dice.staticBonus:
        modifier_breakdown.append(RollModifierBreakdown(source="Spell Slot", value=scaled_static_bonus - effect.damage.dice.staticBonus))
    modifier = sum(part.value for part in modifier_breakdown)
    created_at = time_ns()
    return RollPayload(
        id=f"roll-{created_at}",
        sheetId=sheet.id,
        tokenId=sheet.tokenId,
        roller=roller,
        source=RollSource(section=SheetSectionType.SPELLS, sourceId=enum_key(spell.id), actionId=spell_damage_action_id(effect_index, spell_slot_level, active_instance_index if instance_count > 1 else None)),
        sourceLabel=enum_label(spell.name),
        resolution=RollResolutionMode.APPLY_DAMAGE,
        label=spell_damage_roll_label(effect, active_instance_index, instance_count),
        iconUrl=None,
        dice=dice,
        diceType=dice_type,
        die=dice_formula(dice_count, dice_type),
        modifier=modifier,
        modifierBreakdown=modifier_breakdown,
        total=sum(dice) + modifier,
        createdAt=created_at,
        damageType=effect.damage.damageType,
        damageSavingThrow=effect.savingThrow.ability if effect.savingThrow is not None else None,
        damageSaveDc=spell_save_dc(sheet, spell) if effect.savingThrow is not None else None,
        damageSaveOutcome=effect.savingThrow.outcome if effect.savingThrow is not None else None,
        damageSaveDisadvantageCreatureTypes=effect.savingThrow.disadvantageCreatureTypes if effect.savingThrow is not None else None,
        targetCreatureTypes=effect.targetCreatureTypes,
        sourceHealing=effect.sourceHealing,
        conditionEffects=spell_damage_condition_effects(effect),
        restType=effect.restType,
    )


def build_spell_healing_roll_payload(
    sheet: CharacterSheet,
    roller: str,
    spell: SpellEntry,
    effect_index: int = 0,
    spell_slot_level: int | None = None,
) -> RollPayload:
    effect = spell_healing_effect_at(spell, effect_index)
    if effect is None or effect.healing is None:
        raise ValueError("Spell healing effect not found")

    dice_count = scaled_spell_effect_dice_count(effect.healing.dice.diceCount, effect.scaling, sheet, spell.level, spell_slot_level)
    dice_type = effect.healing.dice.diceType
    dice = [random.randint(1, dice_type.value) for _ in range(dice_count)]
    modifier_breakdown = []
    static_bonus = effect.healing.dice.staticBonus
    if static_bonus:
        modifier_breakdown.append(RollModifierBreakdown(source="Spell", value=static_bonus))
    if effect.healing.dice.bonusAbility is not None:
        ability_score = getattr(sheet.abilityScores, enum_key(effect.healing.dice.bonusAbility))
        modifier_breakdown.append(RollModifierBreakdown(source=enum_label(effect.healing.dice.bonusAbility), value=ability_modifier(ability_score)))
    if effect.healing.dice.bonusSpellcastingAbility:
        casting_ability = spell_casting_ability(sheet, spell)
        ability_score = getattr(sheet.abilityScores, enum_key(casting_ability))
        modifier_breakdown.append(RollModifierBreakdown(source=enum_label(casting_ability), value=ability_modifier(ability_score)))
    scaled_static_bonus = scaled_spell_effect_static_bonus(effect.healing.dice.staticBonus, effect.scaling, spell.level, spell_slot_level)
    if scaled_static_bonus != effect.healing.dice.staticBonus:
        modifier_breakdown.append(RollModifierBreakdown(source="Spell Slot", value=scaled_static_bonus - effect.healing.dice.staticBonus))
    modifier = sum(part.value for part in modifier_breakdown)
    created_at = time_ns()
    return RollPayload(
        id=f"roll-{created_at}",
        sheetId=sheet.id,
        tokenId=sheet.tokenId,
        roller=roller,
        source=RollSource(section=SheetSectionType.SPELLS, sourceId=enum_key(spell.id), actionId=spell_healing_action_id(effect_index, spell_slot_level)),
        sourceLabel=enum_label(spell.name),
        resolution=RollResolutionMode.HEAL_SELF,
        label=spell_healing_roll_label(effect),
        iconUrl=None,
        dice=dice,
        diceType=dice_type,
        die=dice_formula(dice_count, dice_type),
        modifier=modifier,
        modifierBreakdown=modifier_breakdown,
        total=sum(dice) + modifier,
        createdAt=created_at,
        restType=effect.restType,
    )


def build_spell_condition_roll_payload(sheet: CharacterSheet, roller: str, spell: SpellEntry, effect_index: int = 0) -> RollPayload:
    effect = spell_condition_effect_at(spell, effect_index)
    if effect is None or not effect.conditions:
        raise ValueError("Spell condition effect not found")
    casting_ability = spell_casting_ability(sheet, spell) if effect.savingThrow is not None else None
    save_dc = spell_save_dc(sheet, spell) if effect.savingThrow is not None else None
    condition_effects = [
        ConditionEffect(
            condition=condition.condition,
            mode=ConditionApplicationMode.TARGET_SAVE if effect.savingThrow is not None else ConditionApplicationMode.DIRECT,
            savingThrow=effect.savingThrow.ability if effect.savingThrow is not None else None,
            saveDcAbility=casting_ability,
            saveDc=save_dc,
            duration=condition.duration,
            removalTrigger=condition.removalTrigger,
            removalSavingThrow=effect.savingThrow.ability if condition.removalTrigger is not None and effect.savingThrow is not None else None,
            removalSaveDc=save_dc if condition.removalTrigger is not None else None,
            removalAdvantage=condition.removalAdvantage,
            description=effect.description,
        )
        for condition in effect.conditions
    ]
    created_at = time_ns()
    return RollPayload(
        id=f"roll-{created_at}",
        sheetId=sheet.id,
        tokenId=sheet.tokenId,
        roller=roller,
        source=RollSource(section=SheetSectionType.SPELLS, sourceId=enum_key(spell.id), actionId=spell_condition_action_id(effect_index)),
        sourceLabel=enum_label(spell.name),
        resolution=RollResolutionMode.NONE,
        label=f"{effect.actionLabel} Effect" if effect.actionLabel else "Spell Effect",
        iconUrl=None,
        dice=[],
        diceType=DiceType.D20,
        die="",
        modifier=0,
        modifierBreakdown=[],
        total=0,
        createdAt=created_at,
        conditionEffects=condition_effects,
    )


def spell_damage_effect_at(spell: SpellEntry, effect_index: int) -> SpellEffect | None:
    if effect_index < 0 or spell.effects is None:
        return None
    damage_effects = [effect for effect in spell.effects if effect.kind == SpellEffectKind.DAMAGE and effect.damage is not None]
    if effect_index >= len(damage_effects):
        return None
    return damage_effects[effect_index]


def spell_healing_effect_at(spell: SpellEntry, effect_index: int) -> SpellEffect | None:
    if effect_index < 0 or spell.effects is None:
        return None
    healing_effects = [effect for effect in spell.effects if effect.kind == SpellEffectKind.HEALING and effect.healing is not None]
    if effect_index >= len(healing_effects):
        return None
    return healing_effects[effect_index]


def spell_condition_effect_at(spell: SpellEntry, effect_index: int) -> SpellEffect | None:
    if effect_index < 0 or spell.effects is None:
        return None
    condition_effects = [effect for effect in spell.effects if effect.kind == SpellEffectKind.CONDITION and effect.conditions]
    if effect_index >= len(condition_effects):
        return None
    return condition_effects[effect_index]


def spell_damage_action_id(effect_index: int, spell_slot_level: int | None = None, instance_index: int | None = None) -> str:
    slot_suffix = f"-slot-{spell_slot_level}" if spell_slot_level is not None else ""
    instance_suffix = f"-instance-{instance_index}" if instance_index is not None else ""
    return f"damage-{effect_index}{slot_suffix}{instance_suffix}"


def spell_healing_action_id(effect_index: int, spell_slot_level: int | None = None) -> str:
    slot_suffix = f"-slot-{spell_slot_level}" if spell_slot_level is not None else ""
    return f"healing-{effect_index}{slot_suffix}"


def spell_damage_roll_label(effect: SpellEffect, instance_index: int, instance_count: int) -> str:
    prefix = effect.actionLabel or "Spell"
    if instance_count <= 1:
        return f"{prefix} Damage"
    return f"{effect.instanceLabel or 'Instance'} {instance_index + 1} Damage"


def spell_healing_roll_label(effect: SpellEffect) -> str:
    return f"{effect.actionLabel} Healing" if effect.actionLabel else "Healing"


def spell_condition_action_id(effect_index: int) -> str:
    return f"condition-{effect_index}"


def spell_damage_condition_effects(effect: SpellEffect) -> list[ConditionEffect] | None:
    if not effect.conditions:
        return None
    return [
        ConditionEffect(
            condition=condition.condition,
            mode=ConditionApplicationMode.DIRECT,
            duration=condition.duration,
            removalTrigger=condition.removalTrigger,
            removalAdvantage=condition.removalAdvantage,
            description=effect.description,
        )
        for condition in effect.conditions
    ]


def first_spell_damage_type(spell: SpellEntry) -> DamageType | None:
    effect = spell_damage_effect_at(spell, 0)
    return effect.damage.damageType if effect is not None and effect.damage is not None else None


def spell_save_dc(sheet: CharacterSheet, spell: SpellEntry) -> int:
    ability_score = getattr(sheet.abilityScores, enum_key(spell_casting_ability(sheet, spell)))
    return 8 + sheet.proficiencyBonus + ability_modifier(ability_score)


CLASS_SPELLCASTING_ABILITIES: dict[ClassType, AbilityType] = {
    ClassType.ARTIFICER: AbilityType.INTELLIGENCE,
    ClassType.BARD: AbilityType.CHARISMA,
    ClassType.CLERIC: AbilityType.WISDOM,
    ClassType.DRUID: AbilityType.WISDOM,
    ClassType.PALADIN: AbilityType.CHARISMA,
    ClassType.RANGER: AbilityType.WISDOM,
    ClassType.SORCERER: AbilityType.CHARISMA,
    ClassType.WARLOCK: AbilityType.CHARISMA,
    ClassType.WIZARD: AbilityType.INTELLIGENCE,
}


def spell_casting_ability(sheet: CharacterSheet, spell: SpellEntry) -> AbilityType:
    if spell.castingAbility is not None:
        return spell.castingAbility
    matching_spell = next((entry for entry in sheet.spells if entry.id == spell.id and entry.castingAbility is not None), None)
    if matching_spell is not None and matching_spell.castingAbility is not None:
        return matching_spell.castingAbility
    matching_spellbook_spell = next((entry for entry in sheet.spellbook if entry.id == spell.id and entry.castingAbility is not None), None)
    if matching_spellbook_spell is not None and matching_spellbook_spell.castingAbility is not None:
        return matching_spellbook_spell.castingAbility
    for character_class in sheet.classes:
        ability = CLASS_SPELLCASTING_ABILITIES.get(character_class.name)
        if ability is not None:
            return ability
    raise ValueError("Spell casting ability not found")


def scaled_spell_effect_dice_count(
    base_count: int,
    scaling: list[SpellScaling] | None,
    sheet: CharacterSheet,
    spell_level: int = 0,
    spell_slot_level: int | None = None,
) -> int:
    if not scaling:
        return base_count
    total = base_count
    total_level = sum(character_class.level for character_class in sheet.classes) or 1
    for rule in scaling:
        if rule.scalingType == SpellScalingType.CANTRIP_LEVEL and rule.additionalDice is not None:
            total += sum(1 for level in (5, 11, 17) if total_level >= level) * rule.additionalDice.diceCount
        if rule.scalingType == SpellScalingType.SPELL_SLOT_LEVEL and rule.additionalDice is not None and spell_slot_level is not None:
            total += max(0, spell_slot_level - spell_level) // rule.interval * rule.additionalDice.diceCount
    return total


def scaled_spell_effect_static_bonus(
    base_bonus: int,
    scaling: list[SpellScaling] | None,
    spell_level: int = 0,
    spell_slot_level: int | None = None,
) -> int:
    if not scaling:
        return base_bonus
    total = base_bonus
    for rule in scaling:
        if rule.scalingType == SpellScalingType.SPELL_SLOT_LEVEL and spell_slot_level is not None:
            total += max(0, spell_slot_level - spell_level) // rule.interval * rule.additionalStaticBonus
    return total


def scaled_spell_effect_instance_count(
    effect: SpellEffect,
    sheet: CharacterSheet | None = None,
    spell_level: int = 0,
    spell_slot_level: int | None = None,
) -> int:
    total = max(1, effect.instances)
    total_level = sum(character_class.level for character_class in sheet.classes) if sheet is not None else 1
    total_level = total_level or 1
    for rule in effect.scaling or []:
        if rule.scalingType == SpellScalingType.CANTRIP_LEVEL:
            total += sum(1 for level in (5, 11, 17) if total_level >= level) * rule.additionalInstances
        if rule.scalingType == SpellScalingType.SPELL_SLOT_LEVEL and spell_slot_level is not None:
            total += max(0, spell_slot_level - spell_level) // rule.interval * rule.additionalInstances
    return total


def build_ability_check_roll_payload(sheet: CharacterSheet, roller: str, ability: AbilityType) -> RollPayload:
    ability_score = getattr(sheet.abilityScores, enum_key(ability))
    modifier_breakdown = [RollModifierBreakdown(source=enum_label(ability), value=ability_modifier(ability_score))]
    modifier_breakdown.extend(active_roll_modifier_breakdown(sheet, RollModifierEffectTarget.ABILITY_CHECK))
    return build_d20_roll_payload(
        sheet=sheet,
        roller=roller,
        source=RollSource(section=SheetSectionType.ABILITY_SCORES, sourceId=enum_key(ability), actionId=enum_key(AbilityRollType.CHECK)),
        source_label=enum_label(ability),
        label=f"{enum_label(ability)} Check",
        modifier_breakdown=modifier_breakdown,
    )


def build_saving_throw_roll_payload(sheet: CharacterSheet, roller: str, ability: AbilityType) -> RollPayload:
    save = next((saving_throw for saving_throw in sheet.savingThrows if saving_throw.ability == ability), None)
    ability_score = getattr(sheet.abilityScores, enum_key(ability))
    ability_modifier_value = ability_modifier(ability_score)
    if save is None:
        modifier_breakdown = [RollModifierBreakdown(source=enum_label(ability), value=ability_modifier_value)]
    else:
        modifier_breakdown = [RollModifierBreakdown(source=enum_label(ability), value=ability_modifier_value)]
        if save.proficient:
            modifier_breakdown.append(RollModifierBreakdown(source="Proficiency", value=sheet.proficiencyBonus))
    if ability == AbilityType.DEXTERITY and ConditionType.SLOWED in sheet.conditions:
        modifier_breakdown.append(RollModifierBreakdown(source=enum_label(ConditionType.SLOWED), value=-2, description="Subtract 2 from Dexterity saving throws."))
    modifier_breakdown.extend(active_roll_modifier_breakdown(sheet, RollModifierEffectTarget.SAVING_THROW))
    advantage_conditions = condition_saving_throw_advantage_conditions(sheet, ability)
    disadvantage_conditions = condition_saving_throw_disadvantage_conditions(sheet, ability)
    return build_d20_roll_payload(
        sheet=sheet,
        roller=roller,
        source=RollSource(section=SheetSectionType.ABILITY_SCORES, sourceId=enum_key(ability), actionId=enum_key(AbilityRollType.SAVE)),
        source_label=enum_label(ability),
        label=f"{enum_label(ability)} Save",
        modifier_breakdown=modifier_breakdown,
        advantage_conditions=advantage_conditions,
        disadvantage_conditions=disadvantage_conditions,
    )


ACTIVE_CONDITION_ROLL_MODIFIERS: dict[ConditionType, SpellRollModifierEffect] = {
    ConditionType.BANE: SpellRollModifierEffect(
        condition=ConditionType.BANE,
        operation=RollModifierEffectOperation.SUBTRACT,
        targets=[RollModifierEffectTarget.ATTACK_ROLL, RollModifierEffectTarget.SAVING_THROW],
        dice=SpellEffectDice(1, DiceType.D4),
        description="Subtract 1d4 from attack rolls and saving throws.",
    ),
    ConditionType.BLESSED: SpellRollModifierEffect(
        condition=ConditionType.BLESSED,
        operation=RollModifierEffectOperation.ADD,
        targets=[RollModifierEffectTarget.ATTACK_ROLL, RollModifierEffectTarget.SAVING_THROW],
        dice=SpellEffectDice(1, DiceType.D4),
        description="Add 1d4 to attack rolls and saving throws.",
    ),
    ConditionType.GUIDANCE: SpellRollModifierEffect(
        condition=ConditionType.GUIDANCE,
        operation=RollModifierEffectOperation.ADD,
        targets=[RollModifierEffectTarget.ABILITY_CHECK],
        dice=SpellEffectDice(1, DiceType.D4),
        description="Add 1d4 to an ability check.",
    ),
}


DAMAGE_RESISTANCE_CONDITIONS: dict[ConditionType, DamageType] = {
    ConditionType.RESISTANCE_ACID: DamageType.ACID,
    ConditionType.RESISTANCE_BLUDGEONING: DamageType.BLUDGEONING,
    ConditionType.RESISTANCE_COLD: DamageType.COLD,
    ConditionType.RESISTANCE_FIRE: DamageType.FIRE,
    ConditionType.RESISTANCE_FORCE: DamageType.FORCE,
    ConditionType.RESISTANCE_LIGHTNING: DamageType.LIGHTNING,
    ConditionType.RESISTANCE_NECROTIC: DamageType.NECROTIC,
    ConditionType.RESISTANCE_PIERCING: DamageType.PIERCING,
    ConditionType.RESISTANCE_POISON: DamageType.POISON,
    ConditionType.RESISTANCE_PSYCHIC: DamageType.PSYCHIC,
    ConditionType.RESISTANCE_RADIANT: DamageType.RADIANT,
    ConditionType.RESISTANCE_SLASHING: DamageType.SLASHING,
    ConditionType.RESISTANCE_THUNDER: DamageType.THUNDER,
}


def active_roll_modifier_breakdown(sheet: CharacterSheet, target: RollModifierEffectTarget) -> list[RollModifierBreakdown]:
    modifiers: list[RollModifierBreakdown] = []
    for condition in sheet.conditions:
        effect = ACTIVE_CONDITION_ROLL_MODIFIERS.get(condition)
        if effect is None or target not in effect.targets:
            continue
        value = effect.staticBonus
        if effect.dice is not None:
            value += sum(random.randint(1, effect.dice.diceType.value) for _ in range(effect.dice.diceCount))
        if effect.operation == RollModifierEffectOperation.SUBTRACT:
            value = -value
        modifiers.append(RollModifierBreakdown(source=enum_label(condition), value=value, description=effect.description))
    return modifiers


CONDITION_SAVING_THROW_ADVANTAGES: dict[ConditionType, set[AbilityType] | None] = {
    ConditionType.HASTED: {AbilityType.DEXTERITY},
}

CONDITION_SAVING_THROW_DISADVANTAGES: dict[ConditionType, set[AbilityType] | None] = {}


def condition_saving_throw_advantage_conditions(sheet: CharacterSheet, ability: AbilityType) -> list[ConditionType]:
    return condition_saving_throw_roll_conditions(sheet.conditions, ability, CONDITION_SAVING_THROW_ADVANTAGES)


def condition_saving_throw_disadvantage_conditions(sheet: CharacterSheet, ability: AbilityType) -> list[ConditionType]:
    return condition_saving_throw_roll_conditions(sheet.conditions, ability, CONDITION_SAVING_THROW_DISADVANTAGES)


def condition_saving_throw_roll_conditions(
    conditions: list[ConditionType],
    ability: AbilityType,
    rule_map: dict[ConditionType, set[AbilityType] | None],
) -> list[ConditionType]:
    matching: list[ConditionType] = []
    for condition in conditions:
        abilities = rule_map.get(condition)
        if abilities is None and condition in rule_map:
            matching.append(condition)
        elif abilities is not None and ability in abilities:
            matching.append(condition)
    return matching


CONDITION_ARMOR_CLASS_BONUSES: dict[ConditionType, int] = {
    ConditionType.HASTED: 2,
    ConditionType.SHIELDED: 5,
    ConditionType.SHIELD_OF_FAITH: 2,
    ConditionType.SLOWED: -2,
}


def condition_armor_class_bonus(conditions: list[ConditionType]) -> int:
    return sum(CONDITION_ARMOR_CLASS_BONUSES.get(condition, 0) for condition in conditions)


def condition_adjusted_armor_class(sheet: CharacterSheet) -> int:
    bonus = condition_armor_class_bonus(sheet.conditions)
    armor_class = sheet.armorClass + bonus
    if ConditionType.MAGE_ARMOR in sheet.conditions and not worn_armor(sheet.equipment):
        mage_armor_class = 13 + ability_modifier(sheet.abilityScores.dexterity) + equipped_shield_bonus(sheet.equipment) + bonus
        armor_class = max(armor_class, mage_armor_class)
    return armor_class


def condition_adjusted_speed(speed: int, conditions: list[ConditionType]) -> int:
    adjusted = speed
    if ConditionType.HASTED in conditions:
        adjusted *= 2
    if ConditionType.SLOWED in conditions:
        adjusted = max(0, adjusted // 2)
    if ConditionType.LONGSTRIDER in conditions:
        adjusted += 10
    return adjusted


def worn_armor(equipment: list[EquipmentItem]) -> EquipmentItem | None:
    return next((item for item in equipment if item.itemType == EquipmentType.ARMOR and item.slot == EquipmentSlot.ARMOR), None)


def equipped_shield_bonus(equipment: list[EquipmentItem]) -> int:
    return sum(item.armorClassBonus for item in equipment if item.itemType == EquipmentType.SHIELD and item.slot in {EquipmentSlot.MAIN_HAND, EquipmentSlot.OFF_HAND})


def build_d20_roll_payload(
    *,
    sheet: CharacterSheet,
    roller: str,
    source: RollSource,
    source_label: str,
    label: str,
    modifier_breakdown: list[RollModifierBreakdown],
    advantage_conditions: list[ConditionType] | None = None,
    disadvantage_conditions: list[ConditionType] | None = None,
) -> RollPayload:
    modifier = sum(part.value for part in modifier_breakdown)
    dice = [random.randint(1, 20)]
    has_advantage = bool(advantage_conditions) and not disadvantage_conditions
    has_disadvantage = bool(disadvantage_conditions) and not advantage_conditions
    if has_advantage or has_disadvantage:
        dice.append(random.randint(1, 20))
    die_roll = min(dice) if has_disadvantage else max(dice)
    created_at = time_ns()
    return RollPayload(
        id=f"roll-{created_at}",
        sheetId=sheet.id,
        tokenId=sheet.tokenId,
        roller=roller,
        source=source,
        sourceLabel=source_label,
        resolution=RollResolutionMode.NONE,
        label=label,
        iconUrl=None,
        dice=dice,
        diceType=DiceType.D20,
        die="2d20kl1" if has_disadvantage else "2d20kh1" if has_advantage else enum_key(DiceType.D20),
        modifier=modifier,
        modifierBreakdown=modifier_breakdown,
        advantageConditions=advantage_conditions or None,
        disadvantageConditions=disadvantage_conditions or None,
        total=die_roll + modifier,
        createdAt=created_at,
    )


def build_roll_action_payload(sheet: CharacterSheet, roller: str, source: RollSource, action: RollAction, source_label: str | None = None) -> RollPayload:
    dice = [random.randint(1, action.diceType.value) for _ in range(action.diceCount)]
    modifier = roll_action_modifier(sheet, action)
    modifier_breakdown = []
    if modifier:
        modifier_breakdown.append(RollModifierBreakdown(source=roll_action_modifier_label(action), value=modifier))
    created_at = time_ns()
    return RollPayload(
        id=f"roll-{created_at}",
        sheetId=sheet.id,
        tokenId=sheet.tokenId,
        roller=roller,
        source=source,
        sourceLabel=source_label or enum_label(action.name),
        resolution=action.resolution,
        label=enum_label(action.name),
        iconUrl=None,
        dice=dice,
        diceType=action.diceType,
        die=dice_formula(action.diceCount, action.diceType),
        modifier=modifier,
        modifierBreakdown=modifier_breakdown,
        total=sum(dice) + modifier,
        createdAt=created_at,
        damageType=action.damageType,
        conditionEffects=roll_condition_effects(sheet, action),
    )


def roll_condition_effects(sheet: CharacterSheet, action: RollAction) -> list[ConditionEffect] | None:
    if not action.conditionEffects:
        return None
    return [
        ConditionEffect(
            condition=effect.condition,
            mode=effect.mode,
            savingThrow=effect.savingThrow,
            saveDcAbility=effect.saveDcAbility,
            saveDc=condition_effect_save_dc(sheet, effect),
            sourceCheck=effect.sourceCheck,
            contestChecks=effect.contestChecks,
            duration=effect.duration,
            description=effect.description,
        )
        for effect in action.conditionEffects
    ]


def condition_effect_save_dc(sheet: CharacterSheet, effect: ConditionEffect) -> int | None:
    if effect.mode != ConditionApplicationMode.TARGET_SAVE:
        return None
    dc_ability = effect.saveDcAbility or strongest_save_dc_ability(sheet)
    ability_score = getattr(sheet.abilityScores, enum_key(dc_ability))
    return 8 + sheet.proficiencyBonus + ability_modifier(ability_score)


def strongest_save_dc_ability(sheet: CharacterSheet) -> AbilityType:
    return max(
        (AbilityType.STRENGTH, AbilityType.DEXTERITY),
        key=lambda ability: ability_modifier(getattr(sheet.abilityScores, enum_key(ability))),
    )


def roll_action_modifier(sheet: CharacterSheet, action: RollAction) -> int:
    if action.modifier == RollModifierType.CLASS_LEVEL:
        return sheet.characterClass.level + action.staticModifier
    if action.modifier == RollModifierType.PROFICIENCY_BONUS:
        return sheet.proficiencyBonus + action.staticModifier
    if action.modifier == RollModifierType.ABILITY_MODIFIER and action.modifierAbility is not None:
        return ability_modifier(getattr(sheet.abilityScores, enum_key(action.modifierAbility))) + action.staticModifier
    return action.staticModifier


def roll_action_modifier_label(action: RollAction) -> str:
    if action.modifier == RollModifierType.CLASS_LEVEL:
        return "Class Level"
    if action.modifier == RollModifierType.PROFICIENCY_BONUS:
        return "Proficiency"
    if action.modifier == RollModifierType.ABILITY_MODIFIER and action.modifierAbility is not None:
        return enum_label(action.modifierAbility)
    return "Modifier"


def resolve_roll_against_target(roll: RollPayload, target: CharacterSheet) -> RollResolution:
    target_conditions = list(target.conditions)
    damage_blocked_by_creature_type = False
    if roll.resolution == RollResolutionMode.ATTACK_VS_ARMOR_CLASS:
        outcome = "hits" if roll.total >= target.armorClass else "misses"
        target_hp = target.hp
    elif roll.resolution == RollResolutionMode.APPLY_DAMAGE:
        if not target_creature_type_matches(roll, target):
            damage_blocked_by_creature_type = True
            target_hp = target.hp
            outcome = f"has no effect; target is not {creature_type_list_label(roll.targetCreatureTypes or [])}"
        else:
            damage_reduction = active_damage_reduction_roll(roll.damageType, target)
            adjusted_damage = damage_after_defenses(max(0, roll.total), roll.damageType, target, damage_reduction)
            remaining_damage = adjusted_damage
            next_temporary = max(0, target.hp.temporary - remaining_damage)
            remaining_damage = max(0, remaining_damage - target.hp.temporary)
            next_hp = max(0, target.hp.current - remaining_damage)
            target_hp = HitPoints(current=next_hp, max=target.hp.max, temporary=next_temporary)
            outcome = damage_outcome(roll.total, adjusted_damage, roll.damageType, target, damage_reduction)
    elif roll.resolution == RollResolutionMode.HEAL_SELF:
        next_hp = min(target.hp.max, target.hp.current + max(0, roll.total))
        target_hp = HitPoints(current=next_hp, max=target.hp.max, temporary=target.hp.temporary)
        outcome = f"heals {roll.total} hit points"
    elif roll.resolution == RollResolutionMode.APPLY_TEMPORARY_HIT_POINTS:
        rolled_temporary = max(0, roll.total)
        next_temporary = max(target.hp.temporary, rolled_temporary)
        target_hp = HitPoints(current=target.hp.current, max=target.hp.max, temporary=next_temporary)
        outcome = (
            f"gains {rolled_temporary} temporary hit points"
            if rolled_temporary >= target.hp.temporary
            else f"keeps {target.hp.temporary} temporary hit points"
        )
    else:
        target_hp = target.hp
        outcome = f"rolls {roll.total}"

    condition_outcomes = [] if damage_blocked_by_creature_type else resolve_condition_effects(roll, target)
    if condition_outcomes:
        target_conditions = apply_condition_outcomes(target_conditions, condition_outcomes)
        outcome = f"{outcome}; {'; '.join(condition_outcomes)}"

    return RollResolution(
        id=f"resolution-{time_ns()}",
        roll=roll,
        targetSheetId=target.id,
        targetTokenId=target.tokenId,
        targetName=target.name,
        targetArmorClass=target.armorClass,
        targetHp=target_hp,
        targetConditions=target_conditions,
        outcome=outcome,
        createdAt=time_ns(),
    )


def target_creature_type_matches(roll: RollPayload, target: CharacterSheet) -> bool:
    return not roll.targetCreatureTypes or bool(set(roll.targetCreatureTypes).intersection(target.creatureTypes))


def creature_type_list_label(creature_types: list[CreatureType]) -> str:
    labels = [enum_label(creature_type) for creature_type in creature_types]
    if not labels:
        return "a valid creature type"
    if len(labels) == 1:
        return labels[0]
    if len(labels) == 2:
        return f"{labels[0]} or {labels[1]}"
    return f"{', '.join(labels[:-1])}, or {labels[-1]}"


def resolve_condition_effects(roll: RollPayload, target: CharacterSheet) -> list[str]:
    outcomes: list[str] = []
    for effect in roll.conditionEffects or []:
        if effect.mode == ConditionApplicationMode.DIRECT and effect.condition is not None:
            if effect.condition == ConditionType.POISONED and ConditionType.PROTECTION_FROM_POISON in target.conditions:
                outcomes.append(f"{target.name} resists {enum_label(effect.condition)} due to {enum_label(ConditionType.PROTECTION_FROM_POISON)}")
                continue
            outcomes.append(f"{target.name} gains {enum_label(effect.condition)}")
        elif effect.mode == ConditionApplicationMode.MANUAL and effect.condition is not None:
            outcomes.append(f"{enum_label(effect.condition)} requires manual resolution")
    return outcomes


def damage_after_defenses(damage: int, damage_type: DamageType | None, target: CharacterSheet, damage_reduction: int = 0) -> int:
    if damage_type is None:
        return damage
    if damage_type in target.damageImmunities:
        return 0
    adjusted = max(0, damage - damage_reduction)
    if damage_type in effective_damage_resistances(target):
        adjusted //= 2
    if damage_type in target.damageVulnerabilities:
        adjusted *= 2
    return adjusted


def effective_damage_resistances(target: CharacterSheet) -> set[DamageType]:
    return set(effective_damage_resistance_list(target))


def effective_damage_resistance_list(target: CharacterSheet) -> list[DamageType]:
    resistances = set(target.damageResistances)
    ordered_resistances = list(target.damageResistances)
    if ConditionType.PROTECTION_FROM_POISON in target.conditions:
        resistances.add(DamageType.POISON)
        if DamageType.POISON not in ordered_resistances:
            ordered_resistances.append(DamageType.POISON)
    return [damage_type for damage_type in ordered_resistances if damage_type in resistances]


def active_damage_reduction_roll(damage_type: DamageType | None, target: CharacterSheet) -> int:
    if damage_type is None or damage_type not in active_damage_reduction_types(target):
        return 0
    return random.randint(1, 4)


def active_damage_reduction_types(target: CharacterSheet) -> set[DamageType]:
    return {DAMAGE_RESISTANCE_CONDITIONS[condition] for condition in target.conditions if condition in DAMAGE_RESISTANCE_CONDITIONS}


def damage_outcome(raw_damage: int, adjusted_damage: int, damage_type: DamageType | None, target: CharacterSheet, damage_reduction: int = 0) -> str:
    if adjusted_damage == raw_damage or damage_type is None:
        return f"deals {adjusted_damage} damage"
    damage_label = enum_label(damage_type)
    if damage_type in target.damageImmunities:
        return f"deals 0 damage after {damage_label} immunity"
    adjustments = []
    if damage_reduction:
        adjustments.append(f"Resistance {damage_label} reduces damage by {damage_reduction}")
    if damage_type in effective_damage_resistances(target):
        adjustments.append(f"{damage_label} resistance")
    if damage_type in target.damageVulnerabilities:
        adjustments.append(f"{damage_label} vulnerability")
    return f"deals {adjusted_damage} damage after {', '.join(adjustments)}"


def saving_throw_total(target: CharacterSheet, ability: AbilityType) -> int:
    saving_throw = next((save for save in target.savingThrows if save.ability == ability), None)
    ability_score = getattr(target.abilityScores, enum_key(ability))
    total = random.randint(1, 20) + ability_modifier(ability_score)
    if saving_throw is not None and saving_throw.proficient:
        total += target.proficiencyBonus
    return total


def apply_condition_outcomes(current_conditions: list[ConditionType], outcomes: list[str]) -> list[ConditionType]:
    next_conditions = list(current_conditions)
    for condition in ConditionType:
        if any(f"gains {enum_label(condition)}" in outcome for outcome in outcomes) and condition not in next_conditions:
            next_conditions.append(condition)
    if ConditionType.PROTECTION_FROM_POISON in next_conditions and ConditionType.POISONED in next_conditions:
        next_conditions.remove(ConditionType.POISONED)
    return next_conditions


def generated_ability_scores(seed: str) -> AbilityScores:
    rng = random.Random(seed)
    return AbilityScores(
        strength=rng.randint(8, 15),
        dexterity=rng.randint(8, 15),
        constitution=rng.randint(8, 15),
        intelligence=rng.randint(8, 15),
        wisdom=rng.randint(8, 15),
        charisma=rng.randint(8, 15),
    )


def generated_max_hp(seed: str, ability_scores: AbilityScores) -> int:
    rng = random.Random(f"{seed}:hp")
    return max(1, rng.randint(8, 24) + ability_modifier(ability_scores.constitution))


def ability_modifier(score: int) -> int:
    return (score - 10) // 2


def proficiency_bonus_for_level(level: int) -> int:
    return 2 + max(0, min(19, level - 1)) // 4


def base_armor_class(sheet_config: PartyMemberSheet | None, equipment: list[EquipmentItem], dexterity_modifier: int) -> int:
    if sheet_config and sheet_config.armorClass is not None:
        return sheet_config.armorClass

    worn_armor = next((item for item in equipment if item.itemType == EquipmentType.ARMOR and item.slot == EquipmentSlot.ARMOR), None)
    wielded_shields = [item for item in equipment if item.itemType == EquipmentType.SHIELD and item.slot in {EquipmentSlot.MAIN_HAND, EquipmentSlot.OFF_HAND}]
    if worn_armor is not None and worn_armor.armorClass > 0:
        armor_class = armor_item_class(worn_armor, dexterity_modifier)
        return armor_class + sum(shield.armorClassBonus for shield in wielded_shields)
    return 12 + min(3, dexterity_modifier) + sum(shield.armorClassBonus for shield in wielded_shields)


def armor_item_class(item: EquipmentItem, dexterity_modifier: int) -> int:
    if item.armorCategory == ArmorCategory.HEAVY:
        return item.armorClass
    if item.armorCategory == ArmorCategory.MEDIUM:
        return item.armorClass + min(2, dexterity_modifier)
    return item.armorClass + dexterity_modifier


def ability_modifier_map(ability_scores: AbilityScores) -> dict[str, int]:
    return {enum_key(ability): ability_modifier(getattr(ability_scores, enum_key(ability))) for ability in ABILITY_NAMES}


def build_saving_throws(ability_modifiers: dict[str, int], proficient_abilities: set[AbilityType], proficiency_bonus: int) -> list[SavingThrowBonus]:
    return [
        SavingThrowBonus(
            ability=ability,
            proficient=ability in proficient_abilities,
            modifier=ability_modifiers[enum_key(ability)] + (proficiency_bonus if ability in proficient_abilities else 0),
        )
        for ability in ABILITY_NAMES
    ]


def build_skills(ability_modifiers: dict[str, int], skill_proficiencies: dict[str, ProficiencyLevel], proficiency_bonus: int) -> list[SkillBonus]:
    return [
        SkillBonus(
            name=skill,
            ability=ability,
            proficiency=skill_proficiencies.get(skill, ProficiencyLevel.NONE),
            modifier=ability_modifiers[enum_key(ability)] + proficiency_multiplier(skill_proficiencies.get(skill, ProficiencyLevel.NONE)) * proficiency_bonus,
            passive=10 + ability_modifiers[enum_key(ability)] + proficiency_multiplier(skill_proficiencies.get(skill, ProficiencyLevel.NONE)) * proficiency_bonus,
        )
        for skill, ability in SKILL_ABILITIES.items()
    ]


def build_passive_checks(ability_modifiers: dict[str, int], skill_proficiencies: dict[str, ProficiencyLevel], proficiency_bonus: int) -> dict[str, int]:
    skills = build_skills(ability_modifiers, skill_proficiencies, proficiency_bonus)
    passive_skill_keys = {enum_key(SkillType.PERCEPTION), enum_key(SkillType.INVESTIGATION), enum_key(SkillType.INSIGHT)}
    return {skill.name: skill.passive for skill in skills if skill.name in passive_skill_keys}


def proficiency_multiplier(level: ProficiencyLevel | None) -> int:
    if level == ProficiencyLevel.EXPERTISE:
        return 2
    return 1 if level == ProficiencyLevel.PROFICIENT else 0


def default_save_proficiencies(classes: list[CharacterClassLevel]) -> list[AbilityType]:
    primary = classes[0].name if classes else None
    proficiencies: list[AbilityType] = []
    if primary == ClassType.FIGHTER:
        proficiencies.extend([AbilityType.STRENGTH, AbilityType.CONSTITUTION])
    if primary == ClassType.ROGUE:
        proficiencies.extend([AbilityType.DEXTERITY, AbilityType.INTELLIGENCE])
    if primary == ClassType.WIZARD:
        proficiencies.extend([AbilityType.INTELLIGENCE, AbilityType.WISDOM])
    if any(character_class.name == ClassType.ROGUE and character_class.level >= 15 for character_class in classes):
        proficiencies.extend([AbilityType.WISDOM, AbilityType.CHARISMA])
    return list(dict.fromkeys(proficiencies))


def default_attacks(kind: TokenKind) -> list[AttackAction]:
    return [
        AttackAction(
            id="main-hand",
            name="Main Hand" if kind == TokenKind.CHARACTER else "Strike",
            ability=AbilityType.STRENGTH,
            damageDiceCount=1,
            damageDiceType=DiceType.D8,
            properties=[],
        )
    ]


def default_resources(classes: list[CharacterClassLevel], ability_scores: AbilityScores | None = None, feats: list[SheetFeature] | None = None, proficiency_bonus: int = 2) -> list[ResourceTracker]:
    from dnd_board.rules.classes.fighter.archetypes import fighter_subclass_resources
    from dnd_board.rules.classes.fighter.base import fighter_resources
    from dnd_board.rules.classes.rogue.archetypes import rogue_subclass_resources
    from dnd_board.rules.classes.rogue.base import rogue_resources
    from dnd_board.rules.classes.wizard.archetypes import wizard_subclass_resources
    from dnd_board.rules.classes.wizard.base import wizard_resources
    from dnd_board.rules.feats import feat_resources
    from dnd_board.rules.shared.combat_superiority import combat_superiority_resource

    resources = [
        *fighter_resources(classes),
        *fighter_subclass_resources(classes, ability_scores),
        *rogue_resources(classes),
        *rogue_subclass_resources(classes, ability_scores),
        *wizard_resources(classes),
        *wizard_subclass_resources(classes),
        *feat_resources(classes, feats, proficiency_bonus),
    ]
    superiority_dice = combat_superiority_resource(classes)
    if superiority_dice is not None:
        resources.append(superiority_dice)
    return resources


def resource_roll_abilities(resources: list[ResourceTracker]) -> list[SheetAbility]:
    abilities: list[SheetAbility] = []
    for resource in resources:
        for action in resource.rollActions or []:
            abilities.append(
                SheetAbility(
                    id=enum_key(action.id),
                    name=enum_label(action.name),
                    source=action.source or resource.source or resource.name,
                    activation=action.activation or resource.activation,
                    description=action.description or dice_formula(action.diceCount, action.diceType),
                    resourceId=resource.id,
                    rollActions=[action],
                )
            )
    return abilities


def apply_resource_overrides(resources: list[ResourceTracker], overrides: dict[str, int]) -> list[ResourceTracker]:
    return [
        ResourceTracker(
            id=resource.id,
            name=resource.name,
            currentUses=clamp_int(overrides.get(resource.id, resource.currentUses), 0, resource.maxUses),
            maxUses=resource.maxUses,
            reset=resource.reset,
            activation=resource.activation,
            description=resource.description,
            rollActions=resource.rollActions,
            source=resource.source,
            spellSlotLevel=resource.spellSlotLevel,
        )
        for resource in resources
    ]


def apply_equipment_slot_overrides(equipment: list[EquipmentItem], overrides: dict[str, EquipmentSlot]) -> list[EquipmentItem]:
    return [
        EquipmentItem(
            id=item.id,
            name=item.name,
            equipped=overrides.get(item.id, item.slot) != EquipmentSlot.CARRIED,
            quantity=item.quantity,
            weight=item.weight,
            notes=item.notes,
            itemType=item.itemType,
            slot=overrides.get(item.id, item.slot),
            armorCategory=item.armorCategory,
            armorClass=item.armorClass,
            armorClassBonus=item.armorClassBonus,
        )
        for item in equipment
    ]


def default_features(classes: list[CharacterClassLevel]) -> list[SheetFeature]:
    from dnd_board.rules.classes.fighter.base import fighter_features
    from dnd_board.rules.classes.rogue.base import rogue_features
    from dnd_board.rules.classes.wizard.base import wizard_features

    return [*fighter_features(classes), *rogue_features(classes), *wizard_features(classes)]


def default_feat_abilities(classes: list[CharacterClassLevel], feats: list[SheetFeature] | None = None) -> list[SheetAbility]:
    from dnd_board.rules.feats import feat_abilities

    return feat_abilities(classes, feats)


def default_feat_hit_point_bonus(feats: list[SheetFeature], total_level: int) -> int:
    from dnd_board.rules.feats import feat_hit_point_bonus

    return feat_hit_point_bonus(feats, total_level)


def default_feat_speed_bonus(feats: list[SheetFeature]) -> int:
    from dnd_board.rules.feats import feat_speed_bonus

    return feat_speed_bonus(feats)


def default_feat_initiative_bonus(feats: list[SheetFeature], proficiency_bonus: int) -> int:
    from dnd_board.rules.feats import feat_initiative_bonus

    return feat_initiative_bonus(feats, proficiency_bonus)


def default_subclass_abilities(classes: list[CharacterClassLevel]) -> list[SheetAbility]:
    from dnd_board.rules.classes.fighter.archetypes import fighter_subclass_abilities
    from dnd_board.rules.classes.rogue.archetypes import rogue_subclass_abilities
    from dnd_board.rules.classes.rogue.base import rogue_abilities
    from dnd_board.rules.classes.wizard.archetypes import wizard_subclass_abilities

    return [*fighter_subclass_abilities(classes), *rogue_abilities(classes), *rogue_subclass_abilities(classes), *wizard_subclass_abilities(classes)]


def default_spells(classes: list[CharacterClassLevel]) -> list[SpellEntry]:
    from dnd_board.rules.classes.fighter.archetypes import fighter_subclass_spells
    from dnd_board.rules.classes.rogue.archetypes import rogue_subclass_spells

    return [*fighter_subclass_spells(classes), *rogue_subclass_spells(classes)]


def default_spellcasting_spells(classes: list[CharacterClassLevel], spells: list[SpellEntry]) -> list[SpellEntry]:
    from dnd_board.rules.classes.fighter.archetypes import normalized_spellcasting_spells
    from dnd_board.rules.classes.rogue.archetypes import normalized_arcane_trickster_spells

    return normalized_arcane_trickster_spells(classes, normalized_spellcasting_spells(classes, spells))


def hydrated_spell_entries(spells: list[SpellEntry]) -> list[SpellEntry]:
    from dnd_board.rules.spells import spell_entry

    hydrated: list[SpellEntry] = []
    for spell in spells:
        current = spell_entry(spell.id)
        if current is None:
            hydrated.append(spell)
            continue
        hydrated.append(
            replace(
                current,
                status=SpellStatus(
                    source=spell.source,
                    castingAbility=spell.castingAbility,
                    resourceId=spell.resourceId,
                    reset=spell.reset,
                ),
            )
        )
    return hydrated


def default_progression_choices(
    classes: list[CharacterClassLevel],
    spells: list[SpellEntry],
    hit_point_increases: list[int],
    ability_score_improvements: list[str],
    skill_proficiencies: dict[str, ProficiencyLevel] | None = None,
    feats: list[SheetFeature] | None = None,
    feat_eligibility_sheet=None,
    *,
    spellbook: list[SpellEntry] | None = None,
) -> list[ProgressionChoice]:
    from dnd_board.rules.progression import progression_choices

    return progression_choices(classes, spells, hit_point_increases, ability_score_improvements, skill_proficiencies or {}, feats, feat_eligibility_sheet, spellbook=spellbook)


def default_armor_class_bonus(classes: list[CharacterClassLevel], equipment: list[EquipmentItem]) -> int:
    from dnd_board.rules.feats import armor_class_bonus

    return armor_class_bonus(classes, equipment)


def default_feat_attacks(classes: list[CharacterClassLevel], equipment: list[EquipmentItem], attacks: list[AttackAction]) -> list[AttackAction]:
    from dnd_board.rules.classes.rogue.archetypes import rogue_subclass_attacks
    from dnd_board.rules.feats import feat_attacks

    return rogue_subclass_attacks(classes, feat_attacks(classes, equipment, attacks))


def attack_roll_modifier_breakdown(classes: list[CharacterClassLevel], action: AttackAction) -> list[RollModifierBreakdown]:
    from dnd_board.rules.feats import attack_roll_modifiers

    return attack_roll_modifiers(classes, action)


def damage_roll_modifier_breakdown(classes: list[CharacterClassLevel], equipment: list[EquipmentItem], action: AttackAction, ability_modifier_value: int) -> list[RollModifierBreakdown]:
    from dnd_board.rules.feats import damage_roll_modifiers

    return damage_roll_modifiers(classes, equipment, action, ability_modifier_value)


def uses_great_weapon_fighting(classes: list[CharacterClassLevel], action: AttackAction) -> bool:
    from dnd_board.rules.feats import great_weapon_fighting_applies

    return great_weapon_fighting_applies(classes, action)


def party_manifest_from_dict(value: Any) -> PartyManifest | None:
    loaded = typed_json_to_value(value, PartyManifest)
    return loaded if isinstance(loaded, PartyManifest) else None


def typed_json_to_value(node: Any, expected_type: Any = Any) -> Any:
    if not isinstance(node, dict) or TYPE_KEY not in node:
        return None

    expected_type = non_null_type(expected_type)
    type_name = str(node.get(TYPE_KEY))
    if type_name == typed_json_primitive_type_key(TypedJsonPrimitiveType.NONE):
        return None
    if type_name == typed_json_primitive_type_key(TypedJsonPrimitiveType.LIST):
        expected_item_type = Any
        if get_origin(expected_type) is list:
            expected_args = get_args(expected_type)
            expected_item_type = expected_args[0] if expected_args else Any
        items = node.get(ITEMS_KEY)
        if not isinstance(items, list):
            return None
        converted_items = [typed_json_to_value(item, expected_item_type) for item in items]
        if type_allows_none(expected_item_type):
            return converted_items
        return [item for item in converted_items if item is not None]
    if type_name.startswith(typed_json_primitive_type_key(TypedJsonPrimitiveType.DICTIONARY)):
        expected_value_type = Any
        if get_origin(expected_type) is dict:
            expected_args = get_args(expected_type)
            expected_value_type = expected_args[1] if len(expected_args) > 1 else Any
        raw_items = node.get(VALUE_KEY)
        if not isinstance(raw_items, dict):
            return None
        return {str(key): typed_json_to_value(item, expected_value_type) for key, item in raw_items.items()}
    if type_name in typed_json_scalar_type_keys():
        value = typed_primitive_value(type_name, node.get(VALUE_KEY))
        if isinstance(expected_type, type) and issubclass(expected_type, Enum):
            return enum_value(expected_type, value)
        return value if value_matches_type(value, expected_type) else None

    registry = typed_json_registry()
    model_type = registry.get(type_name)
    if model_type is None:
        return None
    if isinstance(model_type, type) and issubclass(model_type, Enum):
        value = enum_value(model_type, node.get(VALUE_KEY))
        return value if value_matches_type(value, expected_type) else None
    if isinstance(model_type, type) and is_dataclass(model_type):
        value = typed_dataclass_from_json(model_type, node)
        return value if value_matches_type(value, expected_type) else None
    return None


def non_null_type(expected_type: Any) -> Any:
    origin = get_origin(expected_type)
    if origin not in {Union, UnionType}:
        return expected_type
    options = [option for option in get_args(expected_type) if option is not type(None)]
    return options[0] if len(options) == 1 else expected_type


def type_allows_none(expected_type: Any) -> bool:
    if expected_type is Any or expected_type is type(None):
        return True
    origin = get_origin(expected_type)
    return origin in {Union, UnionType} and type(None) in get_args(expected_type)


def value_matches_type(value: Any, expected_type: Any) -> bool:
    if value is None:
        return False
    if expected_type is Any:
        return True

    origin = get_origin(expected_type)
    if origin in {Union, UnionType}:
        return any(value_matches_type(value, option) for option in get_args(expected_type) if option is not type(None))
    if origin is list:
        return isinstance(value, list)
    if origin is dict:
        return isinstance(value, dict)
    if not isinstance(expected_type, type):
        return True
    if expected_type is bool:
        return isinstance(value, bool)
    if expected_type is int:
        return isinstance(value, int) and not isinstance(value, bool)
    if expected_type is float:
        return isinstance(value, float)
    return isinstance(value, expected_type)


def typed_dataclass_from_json(model_type: type[Any], node: dict[str, Any]) -> Any | None:
    raw_fields = node.get(FIELDS_KEY)
    if not isinstance(raw_fields, dict):
        return None

    type_hints = get_type_hints(model_type)
    kwargs: dict[str, Any] = {}
    for field in fields(model_type):
        if field.name not in raw_fields:
            continue
        raw_value = raw_fields[field.name]
        converted = typed_json_to_value(raw_value, type_hints.get(field.name, field.type))
        if converted is not None:
            kwargs[field.name] = converted

    try:
        return model_type(**kwargs)
    except (TypeError, ValueError):
        return None


def typed_json_primitive_type_key(primitive_type: TypedJsonPrimitiveType) -> str:
    return primitive_type.value


def typed_json_scalar_type_keys() -> set[str]:
    return {
        typed_json_primitive_type_key(TypedJsonPrimitiveType.STRING),
        typed_json_primitive_type_key(TypedJsonPrimitiveType.INTEGER),
        typed_json_primitive_type_key(TypedJsonPrimitiveType.FLOAT),
        typed_json_primitive_type_key(TypedJsonPrimitiveType.BOOLEAN),
    }


def typed_primitive_value(type_name: str, value: Any) -> Any:
    if type_name == typed_json_primitive_type_key(TypedJsonPrimitiveType.STRING) and isinstance(value, str):
        return value
    if type_name == typed_json_primitive_type_key(TypedJsonPrimitiveType.INTEGER) and isinstance(value, int) and not isinstance(value, bool):
        return value
    if type_name == typed_json_primitive_type_key(TypedJsonPrimitiveType.FLOAT) and isinstance(value, float):
        return value
    if type_name == typed_json_primitive_type_key(TypedJsonPrimitiveType.BOOLEAN) and isinstance(value, bool):
        return value
    return None


def typed_json_registry() -> dict[str, type[Any]]:
    from dnd_board.rules.classes.fighter.archetypes import FighterSubclassResourceType, FighterSubclassRollActionType
    from dnd_board.rules.classes.fighter.base import FighterSubclassType
    from dnd_board.rules.classes.rogue.archetypes import RogueSubclassAbilityType, RogueSubclassAttackType, RogueSubclassResourceType, RogueSubclassRollActionType
    from dnd_board.rules.classes.rogue.base import RogueAbilityType, RogueFeatureType, RogueResourceType, RogueSubclassType
    from dnd_board.rules.classes.wizard.archetypes import WizardSubclassFeatureType, WizardSubclassResourceType
    from dnd_board.rules.classes.wizard.base import WizardFeatureType, WizardResourceType, WizardSubclassType
    from dnd_board.rules.shared.combat_superiority import BattleMasterResourceType, MonsterHunterSuperiorityActionType, ScoutSuperiorityActionType

    return {
        type_.__name__: type_
        for type_ in [
            AbilityScores,
            AbilityRollType,
            AbilityType,
            ArcaneShotType,
            ArmorCategory,
            AttackAction,
            AttackActionType,
            AttackDamageAbilityModifierMode,
            AttackKind,
            AttackRangeType,
            BattleMasterManeuverType,
            BattleMasterResourceType,
            MonsterHunterSuperiorityActionType,
            FighterSubclassResourceType,
            FighterSubclassRollActionType,
            CharacterClassLevel,
            ClassType,
            CurrencyUnit,
            CreatureType,
            DamageType,
            DiceType,
            ConditionType,
            ConditionApplicationMode,
            ConditionDuration,
            ConditionRemovalTrigger,
            ConditionEffect,
            EquipmentSlot,
            EquipmentType,
            EquipmentItem,
            FightingStyleType,
            FighterSubclassType,
            RogueAbilityType,
            RogueFeatureType,
            RogueResourceType,
            RogueSubclassAbilityType,
            RogueSubclassAttackType,
            RogueSubclassResourceType,
            RogueSubclassRollActionType,
            RogueSubclassType,
            PartyManifest,
            PartyMemberConfig,
            PartyMemberSheet,
            Money,
            ProgressionChoice,
            ProgressionChoiceOption,
            ProgressionChoiceType,
            ProficiencyLevel,
            Purse,
            RestType,
            RollAction,
            RollLogEntry,
            RollLogEntryType,
            RollModifierBreakdown,
            RollModifierEffectOperation,
            RollModifierEffectTarget,
            RollModifierType,
            RollResolutionMode,
            ResourceTracker,
            RuneType,
            SkillType,
            SpellAreaShape,
            SpellAttackType,
            SpellComponent,
            SpellConeArea,
            SpellCubeArea,
            SpellCylinderArea,
            SpellConditionEffect,
            SpellDamageEffect,
            SpellDuration,
            SpellDurationUnit,
            SpellEffect,
            SpellEffectDice,
            SpellEffectKind,
            SpellEffectTarget,
            SpellEffectTrigger,
            SpellHealingEffect,
            SpellEntry,
            SpellId,
            SpellLineArea,
            SpellLinkedHealingAmount,
            SpellNoArea,
            SpellRadiusArea,
            SpellRangeType,
            SpellRollModifierEffect,
            SpellSavingThrow,
            SpellSaveOutcome,
            SpellSourceHealingEffect,
            SpellScaling,
            SpellScalingType,
            SpellSchool,
            SpellSource,
            SpellStatus,
            SpellTargeting,
            SheetFeature,
            SheetAbility,
            ScoutSuperiorityActionType,
            TimeEconomy,
            WeaponProperty,
            WeaponCategory,
            WizardFeatureType,
            WizardResourceType,
            WizardSubclassFeatureType,
            WizardSubclassResourceType,
            WizardSubclassType,
        ]
    }


def typed_json_from_value(value: Any) -> dict[str, Any]:
    if value is None:
        return {TYPE_KEY: typed_json_primitive_type_key(TypedJsonPrimitiveType.NONE), VALUE_KEY: None}
    if isinstance(value, Enum):
        return {TYPE_KEY: value.__class__.__name__, VALUE_KEY: value.name}
    if isinstance(value, list):
        return {TYPE_KEY: typed_json_primitive_type_key(TypedJsonPrimitiveType.LIST), ITEMS_KEY: [typed_json_from_value(item) for item in value]}
    if isinstance(value, dict):
        return {
            TYPE_KEY: typed_json_primitive_type_key(TypedJsonPrimitiveType.DICTIONARY),
            VALUE_KEY: {str(key): typed_json_from_value(item) for key, item in value.items()},
        }
    if isinstance(value, str):
        return {TYPE_KEY: typed_json_primitive_type_key(TypedJsonPrimitiveType.STRING), VALUE_KEY: value}
    if isinstance(value, bool):
        return {TYPE_KEY: typed_json_primitive_type_key(TypedJsonPrimitiveType.BOOLEAN), VALUE_KEY: value}
    if isinstance(value, int):
        return {TYPE_KEY: typed_json_primitive_type_key(TypedJsonPrimitiveType.INTEGER), VALUE_KEY: value}
    if isinstance(value, float):
        return {TYPE_KEY: typed_json_primitive_type_key(TypedJsonPrimitiveType.FLOAT), VALUE_KEY: value}
    if is_dataclass(value):
        return {
            TYPE_KEY: value.__class__.__name__,
            FIELDS_KEY: {
                field.name: typed_json_from_value(getattr(value, field.name))
                for field in fields(value)
                if getattr(value, field.name) is not None
            },
        }
    raise TypeError(f"Unsupported typed JSON value: {value.__class__.__name__}")


def sheet_to_dict(sheet: CharacterSheet) -> dict[str, Any]:
    return serialize_dataclass(sheet)


def roll_payload_to_dict(payload: RollPayload) -> dict[str, Any]:
    return serialize_dataclass(payload)


def roll_resolution_to_dict(resolution: RollResolution) -> dict[str, Any]:
    return serialize_dataclass(resolution)


def roll_log_entry_to_dict(entry: RollLogEntry) -> dict[str, Any]:
    return serialize_dataclass(entry)


def serialize_dataclass(value: Any) -> Any:
    return serialize_value(value)


def serialize_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return enum_key(value)
    if isinstance(value, list):
        return [serialize_value(item) for item in value]
    if isinstance(value, dict):
        return {key: serialize_value(item) for key, item in value.items()}
    if hasattr(value, "__dataclass_fields__"):
        data: dict[str, Any] = {}
        for field in fields(value):
            field_value = getattr(value, field.name)
            if field_value is None:
                continue
            data[field.name] = serialize_value(field_value)
            field_label = serialize_label_value(field_value)
            if field_label is not None:
                data[f"{field.name}Label"] = field_label
        for key, computed_value in computed_api_values(value).items():
            data[key] = serialize_value(computed_value)
        return data
    return value


def serialize_label_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return enum_label(value)
    if isinstance(value, list) and value and all(isinstance(item, Enum) for item in value):
        return [enum_label(item) for item in value]
    return None


def computed_api_values(value: Any) -> dict[str, Any]:
    return {
        name: getattr(value, name)
        for name, attribute in vars(value.__class__).items()
        if isinstance(attribute, property) and attribute.fget is not None and getattr(attribute.fget, "__api_field__", False)
    }


def spell_target_range_label(targeting: SpellTargeting) -> str:
    if targeting.rangeType == SpellRangeType.SELF:
        return "Self"
    if targeting.rangeType == SpellRangeType.TOUCH:
        return "Touch"
    if targeting.rangeType == SpellRangeType.SIGHT:
        return "Sight"
    if targeting.rangeType == SpellRangeType.UNLIMITED:
        return "Unlimited"
    if targeting.rangeType == SpellRangeType.SPECIAL:
        return "Special"
    return f"{targeting.distanceFeet} ft"


def spell_area_label(area: SpellArea) -> str:
    if isinstance(area, SpellNoArea):
        return ""
    if isinstance(area, SpellRadiusArea):
        return f"{area.radiusFeet} ft radius"
    if isinstance(area, SpellConeArea):
        return f"{area.lengthFeet} ft cone"
    if isinstance(area, SpellCubeArea):
        return f"{area.sizeFeet} ft cube"
    if isinstance(area, SpellLineArea):
        return f"{area.lengthFeet} ft line x {area.widthFeet} ft"
    if isinstance(area, SpellCylinderArea):
        return f"{area.radiusFeet} ft radius x {area.heightFeet} ft cylinder"
    return ""


def enum_value(enum_type: type[Enum], value: Any) -> Any:
    if value is None:
        return None
    normalized = str(value).strip().replace("-", "_").replace(" ", "_").upper()
    for member in enum_type:
        member_value = member.value if isinstance(member.value, str) else None
        normalized_member_value = member_value.replace("-", "_").replace(" ", "_").upper() if member_value is not None else None
        if normalized in {member.name, enum_key(member).upper(), enum_label(member).replace(" ", "_").upper(), normalized_member_value}:
            return member
    return None


def damage_die_formula(attack: AttackAction) -> str:
    return dice_formula(attack.damageDiceCount, attack.damageDiceType)


def dice_formula(count: int, dice_type: DiceType) -> str:
    return f"{count}d{dice_type.value}"


def clamped_ability_score(value: Any) -> int:
    score = int(value)
    if score < 1 or score > 30:
        raise ValueError("Ability scores must be between 1 and 30")
    return score


def positive_int(value: Any) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def optional_text(value: Any, limit: int) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text[:limit] if text else None


def text_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [text for item in value if (text := optional_text(item, 80)) is not None]


def sanitize_identifier(value: str) -> str:
    return "".join(character for character in value.strip().lower() if character.isalnum() or character == "-")[:60]


def to_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0


def clamp_int(value: int, minimum: int, maximum: int) -> int:
    return min(maximum, max(minimum, value))
