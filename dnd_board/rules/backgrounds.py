from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from dnd_board.character_sheet import AbilityType, EquipmentItem, EquipmentSlot, EquipmentType, ProficiencyLevel, SheetFeature, SkillType, TimeEconomy, enum_key, enum_label
from dnd_board.rules.feats import GeneralFeatType, general_feat_feature


class BackgroundType(Enum):
    ACOLYTE = "Acolyte"
    ARTISAN = "Artisan"
    CHARLATAN = "Charlatan"
    CRIMINAL = "Criminal"
    ENTERTAINER = "Entertainer"
    FARMER = "Farmer"
    GUARD = "Guard"
    GUIDE = "Guide"
    HERMIT = "Hermit"
    MERCHANT = "Merchant"
    NOBLE = "Noble"
    SAGE = "Sage"
    SAILOR = "Sailor"
    SCRIBE = "Scribe"
    SOLDIER = "Soldier"
    WAYFARER = "Wayfarer"
    ABERRANT_HEIR = "Aberrant Heir"
    ARCHAEOLOGIST = "Archaeologist"
    HOUSE_AGENT = "House Agent"
    HOUSE_CANNITH_HEIR = "House Cannith Heir"
    HOUSE_DENEITH_HEIR = "House Deneith Heir"
    HOUSE_GHALLANDA_HEIR = "House Ghallanda Heir"
    HOUSE_JORASCO_HEIR = "House Jorasco Heir"
    HOUSE_KUNDARAK_HEIR = "House Kundarak Heir"
    HOUSE_LYRANDAR_HEIR = "House Lyrandar Heir"
    HOUSE_MEDANI_HEIR = "House Medani Heir"
    HOUSE_ORIEN_HEIR = "House Orien Heir"
    HOUSE_PHIARLAN_HEIR = "House Phiarlan Heir"
    HOUSE_SIVIS_HEIR = "House Sivis Heir"
    HOUSE_THRASHK_HEIR = "House Tharashk Heir"
    HOUSE_THURANNI_HEIR = "House Thuranni Heir"
    HOUSE_VADALIS_HEIR = "House Vadalis Heir"
    INQUISITIVE = "Inquisitive"
    CHONDATHAN_FREEBOOTER = "Chondathan Freebooter"
    DEAD_MAGIC_DWELLER = "Dead Magic Dweller"
    DRAGON_CULTIST = "Dragon Cultist"
    EMERALD_ENCLAVE_CARETAKER = "Emerald Enclave Caretaker"
    FLAMING_FIST_MERCENARY = "Flaming Fist Mercenary"
    GENIE_TOUCHED = "Genie Touched"
    HARPER = "Harper"
    ICE_FISHER = "Ice Fisher"
    KNIGHT_OF_THE_GAUNTLET = "Knight Of The Gauntlet"
    LORDS_ALLIANCE_VASSAL = "Lords' Alliance Vassal"
    MOONWELL_PILGRIM = "Moonwell Pilgrim"
    MULHORANDI_TOMB_RAIDER = "Mulhorandi Tomb Raider"
    MYTHALKEEPER = "Mythalkeeper"
    PURPLE_DRAGON_SQUIRE = "Purple Dragon Squire"
    RASHEMI_WANDERER = "Rashemi Wanderer"
    SHADOWMASTERS_EXILE = "Shadowmasters Exile"
    SPELLFIRE_INITIATE = "Spellfire Initiate"
    ZHENTARIM_MERCENARY = "Zhentarim Mercenary"
    HAUNTED_ONE = "Haunted One"
    INVESTIGATOR = "Investigator"
    MIST_WANDERER = "Mist Wanderer"
    SPIRIT_MEDIUM = "Spirit Medium"
    CAROUSER = "Carouser"
    LORWYN_EXPERT = "Lorwyn Expert"
    PACT_SEEKER = "Pact Seeker"
    SHADOWMOOR_EXPERT = "Shadowmoor Expert"
    VAMPIRE_DEVOTEE = "Vampire Devotee"
    VAMPIRE_SURVIVOR = "Vampire Survivor"


class BackgroundSource(Enum):
    COMMON = "Common"
    EBERRON = "Eberron"
    FAERUN = "Faerun"
    RAVENLOFT = "Ravenloft"
    EXOTIC = "Exotic"


class ToolType(Enum):
    ARTISANS_TOOLS = "one kind of Artisan's Tools"
    ALCHEMISTS_SUPPLIES = "Alchemist's Supplies"
    BREWERS_SUPPLIES = "Brewer's Supplies"
    CALLIGRAPHERS_SUPPLIES = "Calligrapher's Supplies"
    CARPENTERS_TOOLS = "Carpenter's Tools"
    CARTOGRAPHERS_TOOLS = "Cartographer's Tools"
    COBBLERS_TOOLS = "Cobbler's Tools"
    COOKS_UTENSILS = "Cook's Utensils"
    GLASSBLOWERS_TOOLS = "Glassblower's Tools"
    JEWELERS_TOOLS = "Jeweler's Tools"
    LEATHERWORKERS_TOOLS = "Leatherworker's Tools"
    MASONS_TOOLS = "Mason's Tools"
    PAINTERS_SUPPLIES = "Painter's Supplies"
    POTTERS_TOOLS = "Potter's Tools"
    SMITHS_TOOLS = "Smith's Tools"
    TINKERS_TOOLS = "Tinker's Tools"
    WEAVERS_TOOLS = "Weaver's Tools"
    WOODCARVERS_TOOLS = "Woodcarver's Tools"
    FORGERY_KIT = "Forgery Kit"
    GAMING_SET = "one Gaming Set"
    DICE_SET = "Dice Set"
    DRAGONCHESS_SET = "Dragonchess Set"
    PLAYING_CARD_SET = "Playing Card Set"
    THREE_DRAGON_ANTE_SET = "Three-Dragon Ante Set"
    HERBALISM_KIT = "Herbalism Kit"
    MUSICAL_INSTRUMENT = "one Musical Instrument"
    BAGPIPES = "Bagpipes"
    DRUM = "Drum"
    DULCIMER = "Dulcimer"
    FLUTE = "Flute"
    LUTE = "Lute"
    LYRE = "Lyre"
    HORN = "Horn"
    PAN_FLUTE = "Pan Flute"
    SHAWM = "Shawm"
    VIOL = "Viol"
    NAVIGATORS_TOOLS = "Navigator's Tools"
    THIEVES_TOOLS = "Thieves' Tools"


class BackgroundEquipmentChoice(Enum):
    PACKAGE = "Background Equipment"
    GOLD = "50 GP"


class BackgroundFeatureType(Enum):
    TOOL_PROFICIENCY = "Tool Proficiency"


class BackgroundOriginFeatType(Enum):
    ALERT = "Alert"
    CRAFTER = "Crafter"
    HEALER = "Healer"
    LUCKY = "Lucky"
    MAGIC_INITIATE_CLERIC = "Magic Initiate (Cleric)"
    MAGIC_INITIATE_DRUID = "Magic Initiate (Druid)"
    MAGIC_INITIATE_WIZARD = "Magic Initiate (Wizard)"
    MUSICIAN = "Musician"
    SAVAGE_ATTACKER = "Savage Attacker"
    SKILLED = "Skilled"
    TAVERN_BRAWLER = "Tavern Brawler"
    TOUGH = "Tough"


BACKGROUND_ORIGIN_FEATS: dict[BackgroundOriginFeatType, GeneralFeatType] = {
    BackgroundOriginFeatType.ALERT: GeneralFeatType.ALERT,
    BackgroundOriginFeatType.CRAFTER: GeneralFeatType.CRAFTER,
    BackgroundOriginFeatType.HEALER: GeneralFeatType.HEALER,
    BackgroundOriginFeatType.LUCKY: GeneralFeatType.LUCKY,
    BackgroundOriginFeatType.MAGIC_INITIATE_CLERIC: GeneralFeatType.MAGIC_INITIATE,
    BackgroundOriginFeatType.MAGIC_INITIATE_DRUID: GeneralFeatType.MAGIC_INITIATE,
    BackgroundOriginFeatType.MAGIC_INITIATE_WIZARD: GeneralFeatType.MAGIC_INITIATE,
    BackgroundOriginFeatType.MUSICIAN: GeneralFeatType.MUSICIAN,
    BackgroundOriginFeatType.SAVAGE_ATTACKER: GeneralFeatType.SAVAGE_ATTACKER,
    BackgroundOriginFeatType.SKILLED: GeneralFeatType.SKILLED,
    BackgroundOriginFeatType.TAVERN_BRAWLER: GeneralFeatType.TAVERN_BRAWLER,
    BackgroundOriginFeatType.TOUGH: GeneralFeatType.TOUGH,
}

ARTISANS_TOOLS_OPTIONS = (
    ToolType.ALCHEMISTS_SUPPLIES,
    ToolType.BREWERS_SUPPLIES,
    ToolType.CALLIGRAPHERS_SUPPLIES,
    ToolType.CARPENTERS_TOOLS,
    ToolType.CARTOGRAPHERS_TOOLS,
    ToolType.COBBLERS_TOOLS,
    ToolType.COOKS_UTENSILS,
    ToolType.GLASSBLOWERS_TOOLS,
    ToolType.JEWELERS_TOOLS,
    ToolType.LEATHERWORKERS_TOOLS,
    ToolType.MASONS_TOOLS,
    ToolType.PAINTERS_SUPPLIES,
    ToolType.POTTERS_TOOLS,
    ToolType.SMITHS_TOOLS,
    ToolType.TINKERS_TOOLS,
    ToolType.WEAVERS_TOOLS,
    ToolType.WOODCARVERS_TOOLS,
)

GAMING_SET_OPTIONS = (
    ToolType.DICE_SET,
    ToolType.DRAGONCHESS_SET,
    ToolType.PLAYING_CARD_SET,
    ToolType.THREE_DRAGON_ANTE_SET,
)

MUSICAL_INSTRUMENT_OPTIONS = (
    ToolType.BAGPIPES,
    ToolType.DRUM,
    ToolType.DULCIMER,
    ToolType.FLUTE,
    ToolType.LUTE,
    ToolType.LYRE,
    ToolType.HORN,
    ToolType.PAN_FLUTE,
    ToolType.SHAWM,
    ToolType.VIOL,
)


@dataclass(frozen=True)
class BackgroundDefinition:
    backgroundType: BackgroundType
    source: BackgroundSource
    abilityScores: tuple[AbilityType, ...] = ()
    feat: BackgroundOriginFeatType | None = None
    skillProficiencies: tuple[SkillType, ...] = ()
    toolProficiency: ToolType | None = None


def background_definition(background_type: BackgroundType) -> BackgroundDefinition:
    return BACKGROUND_DEFINITIONS[background_type]


def background_label(background_type: BackgroundType) -> str:
    return enum_label(background_type)


def background_skill_proficiencies(background_type: BackgroundType) -> dict[str, ProficiencyLevel]:
    return {enum_key(skill): ProficiencyLevel.PROFICIENT for skill in background_definition(background_type).skillProficiencies}


def background_features(background_type: BackgroundType) -> list[SheetFeature]:
    definition = background_definition(background_type)
    tool = background_default_tool(background_type)
    return background_features_for_tool(background_type, tool) if tool else []


def background_features_for_tool(background_type: BackgroundType, tool: ToolType | None) -> list[SheetFeature]:
    definition = background_definition(background_type)
    features: list[SheetFeature] = []
    if definition.toolProficiency and tool:
        features.append(SheetFeature(
            id=f"{enum_key(background_type)}{enum_key(BackgroundFeatureType.TOOL_PROFICIENCY)}",
            name=enum_label(BackgroundFeatureType.TOOL_PROFICIENCY),
            source=enum_label(background_type),
            activation=TimeEconomy.PASSIVE,
            description=f"Gain proficiency with {enum_label(tool)}.",
        ))
    return features


def background_tool_options(background_type: BackgroundType) -> tuple[ToolType, ...]:
    tool = background_definition(background_type).toolProficiency
    if tool == ToolType.ARTISANS_TOOLS:
        return ARTISANS_TOOLS_OPTIONS
    if tool == ToolType.GAMING_SET:
        return GAMING_SET_OPTIONS
    if tool == ToolType.MUSICAL_INSTRUMENT:
        return MUSICAL_INSTRUMENT_OPTIONS
    return (tool,) if tool else ()


def background_default_tool(background_type: BackgroundType) -> ToolType | None:
    options = background_tool_options(background_type)
    return options[0] if options else None


def background_equipment(background_type: BackgroundType, choice: BackgroundEquipmentChoice) -> list[EquipmentItem]:
    if choice == BackgroundEquipmentChoice.GOLD:
        return [
            EquipmentItem(
                id=f"{enum_key(background_type)}StartingGold",
                name=enum_label(BackgroundEquipmentChoice.GOLD),
                quantity=50,
                notes="Starting gold from background.",
                itemType=EquipmentType.GEAR,
                slot=EquipmentSlot.CARRIED,
            )
        ]
    return [
        EquipmentItem(
            id=f"{enum_key(background_type)}EquipmentPackage",
            name=f"{enum_label(background_type)} Equipment Package",
            notes="Starting equipment package from background.",
            itemType=EquipmentType.GEAR,
            slot=EquipmentSlot.CARRIED,
        )
    ]


def background_feats(background_type: BackgroundType) -> list[SheetFeature]:
    feat = background_feat_feature(background_definition(background_type))
    return [feat] if feat else []


def background_feat_feature(definition: BackgroundDefinition) -> SheetFeature | None:
    if definition.feat is None:
        return None
    feature = general_feat_feature(enum_key(BACKGROUND_ORIGIN_FEATS[definition.feat]))
    if feature is not None:
        feature.name = enum_label(definition.feat)
        return feature
    return None


def background_hit_point_bonus(background_type: BackgroundType, level: int) -> int:
    return 2 * level if background_definition(background_type).feat == BackgroundOriginFeatType.TOUGH else 0


COMMON_BACKGROUND_DEFINITIONS: dict[BackgroundType, BackgroundDefinition] = {
    BackgroundType.ACOLYTE: BackgroundDefinition(BackgroundType.ACOLYTE, BackgroundSource.COMMON, (AbilityType.INTELLIGENCE, AbilityType.WISDOM, AbilityType.CHARISMA), BackgroundOriginFeatType.MAGIC_INITIATE_CLERIC, (SkillType.INSIGHT, SkillType.RELIGION), ToolType.CALLIGRAPHERS_SUPPLIES),
    BackgroundType.ARTISAN: BackgroundDefinition(BackgroundType.ARTISAN, BackgroundSource.COMMON, (AbilityType.STRENGTH, AbilityType.DEXTERITY, AbilityType.INTELLIGENCE), BackgroundOriginFeatType.CRAFTER, (SkillType.INVESTIGATION, SkillType.PERSUASION), ToolType.ARTISANS_TOOLS),
    BackgroundType.CHARLATAN: BackgroundDefinition(BackgroundType.CHARLATAN, BackgroundSource.COMMON, (AbilityType.DEXTERITY, AbilityType.CONSTITUTION, AbilityType.CHARISMA), BackgroundOriginFeatType.SKILLED, (SkillType.DECEPTION, SkillType.SLEIGHT_OF_HAND), ToolType.FORGERY_KIT),
    BackgroundType.CRIMINAL: BackgroundDefinition(BackgroundType.CRIMINAL, BackgroundSource.COMMON, (AbilityType.DEXTERITY, AbilityType.CONSTITUTION, AbilityType.INTELLIGENCE), BackgroundOriginFeatType.ALERT, (SkillType.SLEIGHT_OF_HAND, SkillType.STEALTH), ToolType.THIEVES_TOOLS),
    BackgroundType.ENTERTAINER: BackgroundDefinition(BackgroundType.ENTERTAINER, BackgroundSource.COMMON, (AbilityType.STRENGTH, AbilityType.DEXTERITY, AbilityType.CHARISMA), BackgroundOriginFeatType.MUSICIAN, (SkillType.ACROBATICS, SkillType.PERFORMANCE), ToolType.MUSICAL_INSTRUMENT),
    BackgroundType.FARMER: BackgroundDefinition(BackgroundType.FARMER, BackgroundSource.COMMON, (AbilityType.STRENGTH, AbilityType.CONSTITUTION, AbilityType.WISDOM), BackgroundOriginFeatType.TOUGH, (SkillType.ANIMAL_HANDLING, SkillType.NATURE), ToolType.CARPENTERS_TOOLS),
    BackgroundType.GUARD: BackgroundDefinition(BackgroundType.GUARD, BackgroundSource.COMMON, (AbilityType.STRENGTH, AbilityType.INTELLIGENCE, AbilityType.WISDOM), BackgroundOriginFeatType.ALERT, (SkillType.ATHLETICS, SkillType.PERCEPTION), ToolType.GAMING_SET),
    BackgroundType.GUIDE: BackgroundDefinition(BackgroundType.GUIDE, BackgroundSource.COMMON, (AbilityType.DEXTERITY, AbilityType.CONSTITUTION, AbilityType.WISDOM), BackgroundOriginFeatType.MAGIC_INITIATE_DRUID, (SkillType.STEALTH, SkillType.SURVIVAL), ToolType.CARTOGRAPHERS_TOOLS),
    BackgroundType.HERMIT: BackgroundDefinition(BackgroundType.HERMIT, BackgroundSource.COMMON, (AbilityType.CONSTITUTION, AbilityType.WISDOM, AbilityType.CHARISMA), BackgroundOriginFeatType.HEALER, (SkillType.MEDICINE, SkillType.RELIGION), ToolType.HERBALISM_KIT),
    BackgroundType.MERCHANT: BackgroundDefinition(BackgroundType.MERCHANT, BackgroundSource.COMMON, (AbilityType.CONSTITUTION, AbilityType.INTELLIGENCE, AbilityType.CHARISMA), BackgroundOriginFeatType.LUCKY, (SkillType.ANIMAL_HANDLING, SkillType.PERSUASION), ToolType.NAVIGATORS_TOOLS),
    BackgroundType.NOBLE: BackgroundDefinition(BackgroundType.NOBLE, BackgroundSource.COMMON, (AbilityType.STRENGTH, AbilityType.INTELLIGENCE, AbilityType.CHARISMA), BackgroundOriginFeatType.SKILLED, (SkillType.HISTORY, SkillType.PERSUASION), ToolType.GAMING_SET),
    BackgroundType.SAGE: BackgroundDefinition(BackgroundType.SAGE, BackgroundSource.COMMON, (AbilityType.CONSTITUTION, AbilityType.INTELLIGENCE, AbilityType.WISDOM), BackgroundOriginFeatType.MAGIC_INITIATE_WIZARD, (SkillType.ARCANA, SkillType.HISTORY), ToolType.CALLIGRAPHERS_SUPPLIES),
    BackgroundType.SAILOR: BackgroundDefinition(BackgroundType.SAILOR, BackgroundSource.COMMON, (AbilityType.STRENGTH, AbilityType.DEXTERITY, AbilityType.WISDOM), BackgroundOriginFeatType.TAVERN_BRAWLER, (SkillType.ACROBATICS, SkillType.PERCEPTION), ToolType.NAVIGATORS_TOOLS),
    BackgroundType.SCRIBE: BackgroundDefinition(BackgroundType.SCRIBE, BackgroundSource.COMMON, (AbilityType.DEXTERITY, AbilityType.INTELLIGENCE, AbilityType.WISDOM), BackgroundOriginFeatType.SKILLED, (SkillType.INVESTIGATION, SkillType.PERCEPTION), ToolType.CALLIGRAPHERS_SUPPLIES),
    BackgroundType.SOLDIER: BackgroundDefinition(BackgroundType.SOLDIER, BackgroundSource.COMMON, (AbilityType.STRENGTH, AbilityType.DEXTERITY, AbilityType.CONSTITUTION), BackgroundOriginFeatType.SAVAGE_ATTACKER, (SkillType.ATHLETICS, SkillType.INTIMIDATION), ToolType.GAMING_SET),
    BackgroundType.WAYFARER: BackgroundDefinition(BackgroundType.WAYFARER, BackgroundSource.COMMON, (AbilityType.DEXTERITY, AbilityType.WISDOM, AbilityType.CHARISMA), BackgroundOriginFeatType.LUCKY, (SkillType.INSIGHT, SkillType.STEALTH), ToolType.THIEVES_TOOLS),
}

BACKGROUND_SOURCES: dict[BackgroundSource, tuple[BackgroundType, ...]] = {
    BackgroundSource.EBERRON: (
        BackgroundType.ABERRANT_HEIR, BackgroundType.ARCHAEOLOGIST, BackgroundType.HOUSE_AGENT, BackgroundType.HOUSE_CANNITH_HEIR,
        BackgroundType.HOUSE_DENEITH_HEIR, BackgroundType.HOUSE_GHALLANDA_HEIR, BackgroundType.HOUSE_JORASCO_HEIR,
        BackgroundType.HOUSE_KUNDARAK_HEIR, BackgroundType.HOUSE_LYRANDAR_HEIR, BackgroundType.HOUSE_MEDANI_HEIR,
        BackgroundType.HOUSE_ORIEN_HEIR, BackgroundType.HOUSE_PHIARLAN_HEIR, BackgroundType.HOUSE_SIVIS_HEIR,
        BackgroundType.HOUSE_THRASHK_HEIR, BackgroundType.HOUSE_THURANNI_HEIR, BackgroundType.HOUSE_VADALIS_HEIR,
        BackgroundType.INQUISITIVE,
    ),
    BackgroundSource.FAERUN: (
        BackgroundType.CHONDATHAN_FREEBOOTER, BackgroundType.DEAD_MAGIC_DWELLER, BackgroundType.DRAGON_CULTIST,
        BackgroundType.EMERALD_ENCLAVE_CARETAKER, BackgroundType.FLAMING_FIST_MERCENARY, BackgroundType.GENIE_TOUCHED,
        BackgroundType.HARPER, BackgroundType.ICE_FISHER, BackgroundType.KNIGHT_OF_THE_GAUNTLET,
        BackgroundType.LORDS_ALLIANCE_VASSAL, BackgroundType.MOONWELL_PILGRIM, BackgroundType.MULHORANDI_TOMB_RAIDER,
        BackgroundType.MYTHALKEEPER, BackgroundType.PURPLE_DRAGON_SQUIRE, BackgroundType.RASHEMI_WANDERER,
        BackgroundType.SHADOWMASTERS_EXILE, BackgroundType.SPELLFIRE_INITIATE, BackgroundType.ZHENTARIM_MERCENARY,
    ),
    BackgroundSource.RAVENLOFT: (BackgroundType.HAUNTED_ONE, BackgroundType.INVESTIGATOR, BackgroundType.MIST_WANDERER, BackgroundType.SPIRIT_MEDIUM),
    BackgroundSource.EXOTIC: (BackgroundType.CAROUSER, BackgroundType.LORWYN_EXPERT, BackgroundType.PACT_SEEKER, BackgroundType.SHADOWMOOR_EXPERT, BackgroundType.VAMPIRE_DEVOTEE, BackgroundType.VAMPIRE_SURVIVOR),
}

BACKGROUND_DEFINITIONS: dict[BackgroundType, BackgroundDefinition] = {
    **COMMON_BACKGROUND_DEFINITIONS,
    **{
        background_type: BackgroundDefinition(background_type, source)
        for source, backgrounds in BACKGROUND_SOURCES.items()
        for background_type in backgrounds
    },
}
