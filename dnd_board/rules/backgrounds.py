from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from collections.abc import Iterable

from dnd_board.character_sheet import AbilityType, CurrencyUnit, EquipmentItem, Money, ProficiencyLevel, Purse, SheetFeature, SkillType, TimeEconomy, enum_key, enum_label
from dnd_board.rules.equipment import EquipmentId, equipment_item, tool_equipment_item
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
    DISGUISE_KIT = "Disguise Kit"
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
    POISONERS_KIT = "Poisoner's Kit"
    THIEVES_TOOLS = "Thieves' Tools"


class BackgroundEquipmentChoice(Enum):
    PACKAGE = "Background Equipment"
    GOLD = "50 GP"


class BackgroundFeatureType(Enum):
    TOOL_PROFICIENCY = "Tool Proficiency"


class BackgroundOriginFeatType(Enum):
    ABERRANT_DRAGONMARK = "Aberrant Dragonmark"
    ALERT = "Alert"
    CHILD_OF_THE_SUN = "Child of the Sun"
    CULT_OF_THE_DRAGON_INITIATE = "Cult of the Dragon Initiate"
    CRAFTER = "Crafter"
    EMERALD_ENCLAVE_FLEDGLING = "Emerald Enclave Fledgling"
    FEY_PACT = "Fey Pact"
    GATHERED_WHISPERS = "Gathered Whispers"
    HARPER_AGENT = "Harper Agent"
    HEALER = "Healer"
    LUCKY = "Lucky"
    LORDS_ALLIANCE_AGENT = "Lords' Alliance Agent"
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
    MAGIC_INITIATE_CLERIC = "Magic Initiate (Cleric)"
    MAGIC_INITIATE_DRUID = "Magic Initiate (Druid)"
    MAGIC_INITIATE_WIZARD = "Magic Initiate (Wizard)"
    MIST_WALKER = "Mist Walker"
    MUSICIAN = "Musician"
    PURPLE_DRAGON_ROOK = "Purple Dragon Rook"
    SAVAGE_ATTACKER = "Savage Attacker"
    SHADOWMOOR_HEXER = "Shadowmoor Hexer"
    SHARP_EYE = "Sharp Eye"
    SKILLED = "Skilled"
    SPELLFIRE_SPARK = "Spellfire Spark"
    SURVIVOR = "Survivor"
    TAVERN_BRAWLER = "Tavern Brawler"
    TIRELESS_REVELER = "Tireless Reveler"
    TOUGH = "Tough"
    TYRO_OF_THE_GAUNTLET = "Tyro of the Gauntlet"
    VAMPIRE_HUNTER = "Vampire Hunter"
    VAMPIRE_S_PLAYTHING = "Vampire's Plaything"
    ZHENTARIM_RUFFIAN = "Zhentarim Ruffian"


BACKGROUND_ORIGIN_FEATS: dict[BackgroundOriginFeatType, GeneralFeatType] = {
    BackgroundOriginFeatType.ABERRANT_DRAGONMARK: GeneralFeatType.ABERRANT_DRAGONMARK,
    BackgroundOriginFeatType.ALERT: GeneralFeatType.ALERT,
    BackgroundOriginFeatType.CHILD_OF_THE_SUN: GeneralFeatType.CHILD_OF_THE_SUN,
    BackgroundOriginFeatType.CULT_OF_THE_DRAGON_INITIATE: GeneralFeatType.CULT_OF_THE_DRAGON_INITIATE,
    BackgroundOriginFeatType.CRAFTER: GeneralFeatType.CRAFTER,
    BackgroundOriginFeatType.EMERALD_ENCLAVE_FLEDGLING: GeneralFeatType.EMERALD_ENCLAVE_FLEDGLING,
    BackgroundOriginFeatType.FEY_PACT: GeneralFeatType.FEY_PACT,
    BackgroundOriginFeatType.GATHERED_WHISPERS: GeneralFeatType.GATHERED_WHISPERS,
    BackgroundOriginFeatType.HARPER_AGENT: GeneralFeatType.HARPER_AGENT,
    BackgroundOriginFeatType.HEALER: GeneralFeatType.HEALER,
    BackgroundOriginFeatType.LUCKY: GeneralFeatType.LUCKY,
    BackgroundOriginFeatType.LORDS_ALLIANCE_AGENT: GeneralFeatType.LORDS_ALLIANCE_AGENT,
    BackgroundOriginFeatType.MARK_OF_DETECTION: GeneralFeatType.MARK_OF_DETECTION,
    BackgroundOriginFeatType.MARK_OF_FINDING: GeneralFeatType.MARK_OF_FINDING,
    BackgroundOriginFeatType.MARK_OF_HANDLING: GeneralFeatType.MARK_OF_HANDLING,
    BackgroundOriginFeatType.MARK_OF_HEALING: GeneralFeatType.MARK_OF_HEALING,
    BackgroundOriginFeatType.MARK_OF_HOSPITALITY: GeneralFeatType.MARK_OF_HOSPITALITY,
    BackgroundOriginFeatType.MARK_OF_MAKING: GeneralFeatType.MARK_OF_MAKING,
    BackgroundOriginFeatType.MARK_OF_PASSAGE: GeneralFeatType.MARK_OF_PASSAGE,
    BackgroundOriginFeatType.MARK_OF_SCRIBING: GeneralFeatType.MARK_OF_SCRIBING,
    BackgroundOriginFeatType.MARK_OF_SENTINEL: GeneralFeatType.MARK_OF_SENTINEL,
    BackgroundOriginFeatType.MARK_OF_SHADOW: GeneralFeatType.MARK_OF_SHADOW,
    BackgroundOriginFeatType.MARK_OF_STORM: GeneralFeatType.MARK_OF_STORM,
    BackgroundOriginFeatType.MARK_OF_WARDING: GeneralFeatType.MARK_OF_WARDING,
    BackgroundOriginFeatType.MAGIC_INITIATE_CLERIC: GeneralFeatType.MAGIC_INITIATE,
    BackgroundOriginFeatType.MAGIC_INITIATE_DRUID: GeneralFeatType.MAGIC_INITIATE,
    BackgroundOriginFeatType.MAGIC_INITIATE_WIZARD: GeneralFeatType.MAGIC_INITIATE,
    BackgroundOriginFeatType.MIST_WALKER: GeneralFeatType.MIST_WALKER,
    BackgroundOriginFeatType.MUSICIAN: GeneralFeatType.MUSICIAN,
    BackgroundOriginFeatType.PURPLE_DRAGON_ROOK: GeneralFeatType.PURPLE_DRAGON_ROOK,
    BackgroundOriginFeatType.SAVAGE_ATTACKER: GeneralFeatType.SAVAGE_ATTACKER,
    BackgroundOriginFeatType.SHADOWMOOR_HEXER: GeneralFeatType.SHADOWMOOR_HEXER,
    BackgroundOriginFeatType.SHARP_EYE: GeneralFeatType.SHARP_EYE,
    BackgroundOriginFeatType.SKILLED: GeneralFeatType.SKILLED,
    BackgroundOriginFeatType.SPELLFIRE_SPARK: GeneralFeatType.SPELLFIRE_SPARK,
    BackgroundOriginFeatType.SURVIVOR: GeneralFeatType.SURVIVOR,
    BackgroundOriginFeatType.TAVERN_BRAWLER: GeneralFeatType.TAVERN_BRAWLER,
    BackgroundOriginFeatType.TIRELESS_REVELER: GeneralFeatType.TIRELESS_REVELER,
    BackgroundOriginFeatType.TOUGH: GeneralFeatType.TOUGH,
    BackgroundOriginFeatType.TYRO_OF_THE_GAUNTLET: GeneralFeatType.TYRO_OF_THE_GAUNTLET,
    BackgroundOriginFeatType.VAMPIRE_HUNTER: GeneralFeatType.VAMPIRE_HUNTER,
    BackgroundOriginFeatType.VAMPIRE_S_PLAYTHING: GeneralFeatType.VAMPIRE_S_PLAYTHING,
    BackgroundOriginFeatType.ZHENTARIM_RUFFIAN: GeneralFeatType.ZHENTARIM_RUFFIAN,
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
class BackgroundEquipmentGrant:
    equipmentId: EquipmentId | None = None
    toolType: ToolType | None = None
    quantity: int = 1
    selectedTool: bool = False
    money: Money | None = None
    name: str | None = None


def eq(equipment_id: EquipmentId, quantity: int = 1, name: str | None = None) -> BackgroundEquipmentGrant:
    return BackgroundEquipmentGrant(equipmentId=equipment_id, quantity=quantity, name=name)


def tool(tool_type: ToolType, quantity: int = 1) -> BackgroundEquipmentGrant:
    return BackgroundEquipmentGrant(toolType=tool_type, quantity=quantity)


def selected_tool(quantity: int = 1) -> BackgroundEquipmentGrant:
    return BackgroundEquipmentGrant(quantity=quantity, selectedTool=True)


def coins(quantity: int, unit: CurrencyUnit = CurrencyUnit.GP) -> BackgroundEquipmentGrant:
    return BackgroundEquipmentGrant(money=Money(quantity, unit))


@dataclass(frozen=True)
class BackgroundDefinition:
    backgroundType: BackgroundType
    source: BackgroundSource
    abilityScores: tuple[AbilityType, ...] = ()
    feat: BackgroundOriginFeatType | None = None
    skillProficiencies: tuple[SkillType, ...] = ()
    toolProficiency: ToolType | None = None
    equipmentPackage: tuple[BackgroundEquipmentGrant, ...] = ()


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


def background_equipment(background_type: BackgroundType, choice: BackgroundEquipmentChoice, selected_tool: ToolType | None = None) -> list[EquipmentItem]:
    if choice == BackgroundEquipmentChoice.GOLD:
        return []
    return [
        item
        for item in (background_equipment_grant_item(grant, selected_tool) for grant in background_definition(background_type).equipmentPackage)
        if item is not None
    ]


def background_equipment_grant_item(grant: BackgroundEquipmentGrant, selected_tool_type: ToolType | None = None) -> EquipmentItem | None:
    if grant.money:
        return None
    if grant.selectedTool:
        return tool_equipment_item(selected_tool_type, quantity=grant.quantity) if selected_tool_type else None
    if grant.toolType:
        return tool_equipment_item(grant.toolType, quantity=grant.quantity)
    if grant.equipmentId:
        return equipment_item(grant.equipmentId, quantity=grant.quantity, name=grant.name)
    return None


def background_purse(background_type: BackgroundType, choice: BackgroundEquipmentChoice) -> Purse:
    if choice == BackgroundEquipmentChoice.GOLD:
        return purse_from_money((Money(50, CurrencyUnit.GP),))
    return purse_from_money(grant.money for grant in background_definition(background_type).equipmentPackage if grant.money)


def purse_from_money(money_entries: Iterable[Money]) -> Purse:
    purse = Purse()
    for money in money_entries:
        if money.unit == CurrencyUnit.CP:
            purse.copper += money.quantity
        elif money.unit == CurrencyUnit.SP:
            purse.silver += money.quantity
        elif money.unit == CurrencyUnit.GP:
            purse.gold += money.quantity
    return purse


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
    BackgroundType.ACOLYTE: BackgroundDefinition(BackgroundType.ACOLYTE, BackgroundSource.COMMON, (AbilityType.INTELLIGENCE, AbilityType.WISDOM, AbilityType.CHARISMA), BackgroundOriginFeatType.MAGIC_INITIATE_CLERIC, (SkillType.INSIGHT, SkillType.RELIGION), ToolType.CALLIGRAPHERS_SUPPLIES, (tool(ToolType.CALLIGRAPHERS_SUPPLIES), eq(EquipmentId.BOOK, name='Book (prayers)'), eq(EquipmentId.HOLY_SYMBOL), eq(EquipmentId.PARCHMENT, 10), eq(EquipmentId.ROBE), coins(8),)),
    BackgroundType.ARTISAN: BackgroundDefinition(BackgroundType.ARTISAN, BackgroundSource.COMMON, (AbilityType.STRENGTH, AbilityType.DEXTERITY, AbilityType.INTELLIGENCE), BackgroundOriginFeatType.CRAFTER, (SkillType.INVESTIGATION, SkillType.PERSUASION), ToolType.ARTISANS_TOOLS, (selected_tool(), eq(EquipmentId.POUCH, 2), eq(EquipmentId.TRAVELERS_CLOTHES), coins(32),)),
    BackgroundType.CHARLATAN: BackgroundDefinition(BackgroundType.CHARLATAN, BackgroundSource.COMMON, (AbilityType.DEXTERITY, AbilityType.CONSTITUTION, AbilityType.CHARISMA), BackgroundOriginFeatType.SKILLED, (SkillType.DECEPTION, SkillType.SLEIGHT_OF_HAND), ToolType.FORGERY_KIT, (tool(ToolType.FORGERY_KIT), eq(EquipmentId.COSTUME), eq(EquipmentId.FINE_CLOTHES), coins(15),)),
    BackgroundType.CRIMINAL: BackgroundDefinition(BackgroundType.CRIMINAL, BackgroundSource.COMMON, (AbilityType.DEXTERITY, AbilityType.CONSTITUTION, AbilityType.INTELLIGENCE), BackgroundOriginFeatType.ALERT, (SkillType.SLEIGHT_OF_HAND, SkillType.STEALTH), ToolType.THIEVES_TOOLS, (eq(EquipmentId.DAGGER, 2), tool(ToolType.THIEVES_TOOLS), eq(EquipmentId.CROWBAR), eq(EquipmentId.POUCH, 2), eq(EquipmentId.TRAVELERS_CLOTHES), coins(16),)),
    BackgroundType.ENTERTAINER: BackgroundDefinition(BackgroundType.ENTERTAINER, BackgroundSource.COMMON, (AbilityType.STRENGTH, AbilityType.DEXTERITY, AbilityType.CHARISMA), BackgroundOriginFeatType.MUSICIAN, (SkillType.ACROBATICS, SkillType.PERFORMANCE), ToolType.MUSICAL_INSTRUMENT, (selected_tool(), eq(EquipmentId.COSTUME, 2), eq(EquipmentId.MIRROR), eq(EquipmentId.PERFUME), eq(EquipmentId.TRAVELERS_CLOTHES), coins(11),)),
    BackgroundType.FARMER: BackgroundDefinition(BackgroundType.FARMER, BackgroundSource.COMMON, (AbilityType.STRENGTH, AbilityType.CONSTITUTION, AbilityType.WISDOM), BackgroundOriginFeatType.TOUGH, (SkillType.ANIMAL_HANDLING, SkillType.NATURE), ToolType.CARPENTERS_TOOLS, (eq(EquipmentId.SICKLE), tool(ToolType.CARPENTERS_TOOLS), eq(EquipmentId.HEALERS_KIT), eq(EquipmentId.IRON_POT), eq(EquipmentId.SHOVEL), eq(EquipmentId.TRAVELERS_CLOTHES), coins(30),)),
    BackgroundType.GUARD: BackgroundDefinition(BackgroundType.GUARD, BackgroundSource.COMMON, (AbilityType.STRENGTH, AbilityType.INTELLIGENCE, AbilityType.WISDOM), BackgroundOriginFeatType.ALERT, (SkillType.ATHLETICS, SkillType.PERCEPTION), ToolType.GAMING_SET, (eq(EquipmentId.SPEAR), eq(EquipmentId.LIGHT_CROSSBOW), eq(EquipmentId.BOLTS, 20), selected_tool(), eq(EquipmentId.HOODED_LANTERN), eq(EquipmentId.MANACLES), eq(EquipmentId.QUIVER), eq(EquipmentId.TRAVELERS_CLOTHES), coins(12),)),
    BackgroundType.GUIDE: BackgroundDefinition(BackgroundType.GUIDE, BackgroundSource.COMMON, (AbilityType.DEXTERITY, AbilityType.CONSTITUTION, AbilityType.WISDOM), BackgroundOriginFeatType.MAGIC_INITIATE_DRUID, (SkillType.STEALTH, SkillType.SURVIVAL), ToolType.CARTOGRAPHERS_TOOLS, (eq(EquipmentId.SHORTBOW), eq(EquipmentId.ARROWS, 20), tool(ToolType.CARTOGRAPHERS_TOOLS), eq(EquipmentId.BEDROLL), eq(EquipmentId.QUIVER), eq(EquipmentId.TENT), eq(EquipmentId.TRAVELERS_CLOTHES), coins(3),)),
    BackgroundType.HERMIT: BackgroundDefinition(BackgroundType.HERMIT, BackgroundSource.COMMON, (AbilityType.CONSTITUTION, AbilityType.WISDOM, AbilityType.CHARISMA), BackgroundOriginFeatType.HEALER, (SkillType.MEDICINE, SkillType.RELIGION), ToolType.HERBALISM_KIT, (eq(EquipmentId.QUARTERSTAFF), tool(ToolType.HERBALISM_KIT), eq(EquipmentId.BEDROLL), eq(EquipmentId.BOOK, name='Book (philosophy)'), eq(EquipmentId.LAMP), eq(EquipmentId.OIL, 3), eq(EquipmentId.TRAVELERS_CLOTHES), coins(16),)),
    BackgroundType.MERCHANT: BackgroundDefinition(BackgroundType.MERCHANT, BackgroundSource.COMMON, (AbilityType.CONSTITUTION, AbilityType.INTELLIGENCE, AbilityType.CHARISMA), BackgroundOriginFeatType.LUCKY, (SkillType.ANIMAL_HANDLING, SkillType.PERSUASION), ToolType.NAVIGATORS_TOOLS, (tool(ToolType.NAVIGATORS_TOOLS), eq(EquipmentId.POUCH, 2), eq(EquipmentId.TRAVELERS_CLOTHES), coins(22),)),
    BackgroundType.NOBLE: BackgroundDefinition(BackgroundType.NOBLE, BackgroundSource.COMMON, (AbilityType.STRENGTH, AbilityType.INTELLIGENCE, AbilityType.CHARISMA), BackgroundOriginFeatType.SKILLED, (SkillType.HISTORY, SkillType.PERSUASION), ToolType.GAMING_SET, (selected_tool(), eq(EquipmentId.FINE_CLOTHES), eq(EquipmentId.PERFUME), coins(29),)),
    BackgroundType.SAGE: BackgroundDefinition(BackgroundType.SAGE, BackgroundSource.COMMON, (AbilityType.CONSTITUTION, AbilityType.INTELLIGENCE, AbilityType.WISDOM), BackgroundOriginFeatType.MAGIC_INITIATE_WIZARD, (SkillType.ARCANA, SkillType.HISTORY), ToolType.CALLIGRAPHERS_SUPPLIES, (eq(EquipmentId.QUARTERSTAFF), tool(ToolType.CALLIGRAPHERS_SUPPLIES), eq(EquipmentId.BOOK, name='Book (history)'), eq(EquipmentId.PARCHMENT, 8), eq(EquipmentId.ROBE), coins(8),)),
    BackgroundType.SAILOR: BackgroundDefinition(BackgroundType.SAILOR, BackgroundSource.COMMON, (AbilityType.STRENGTH, AbilityType.DEXTERITY, AbilityType.WISDOM), BackgroundOriginFeatType.TAVERN_BRAWLER, (SkillType.ACROBATICS, SkillType.PERCEPTION), ToolType.NAVIGATORS_TOOLS, (eq(EquipmentId.DAGGER), tool(ToolType.NAVIGATORS_TOOLS), eq(EquipmentId.ROPE), eq(EquipmentId.TRAVELERS_CLOTHES), coins(20),)),
    BackgroundType.SCRIBE: BackgroundDefinition(BackgroundType.SCRIBE, BackgroundSource.COMMON, (AbilityType.DEXTERITY, AbilityType.INTELLIGENCE, AbilityType.WISDOM), BackgroundOriginFeatType.SKILLED, (SkillType.INVESTIGATION, SkillType.PERCEPTION), ToolType.CALLIGRAPHERS_SUPPLIES, (tool(ToolType.CALLIGRAPHERS_SUPPLIES), eq(EquipmentId.FINE_CLOTHES), eq(EquipmentId.LAMP), eq(EquipmentId.OIL, 3), eq(EquipmentId.PARCHMENT, 12), coins(23),)),
    BackgroundType.SOLDIER: BackgroundDefinition(BackgroundType.SOLDIER, BackgroundSource.COMMON, (AbilityType.STRENGTH, AbilityType.DEXTERITY, AbilityType.CONSTITUTION), BackgroundOriginFeatType.SAVAGE_ATTACKER, (SkillType.ATHLETICS, SkillType.INTIMIDATION), ToolType.GAMING_SET, (eq(EquipmentId.SPEAR), eq(EquipmentId.SHORTBOW), eq(EquipmentId.ARROWS, 20), selected_tool(), eq(EquipmentId.HEALERS_KIT), eq(EquipmentId.QUIVER), eq(EquipmentId.TRAVELERS_CLOTHES), coins(14),)),
    BackgroundType.WAYFARER: BackgroundDefinition(BackgroundType.WAYFARER, BackgroundSource.COMMON, (AbilityType.DEXTERITY, AbilityType.WISDOM, AbilityType.CHARISMA), BackgroundOriginFeatType.LUCKY, (SkillType.INSIGHT, SkillType.STEALTH), ToolType.THIEVES_TOOLS, (eq(EquipmentId.DAGGER, 2), tool(ToolType.THIEVES_TOOLS), eq(EquipmentId.GAMING_SET), eq(EquipmentId.BEDROLL), eq(EquipmentId.POUCH, 2), eq(EquipmentId.TRAVELERS_CLOTHES), coins(16),)),
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
    BackgroundType.ABERRANT_HEIR: BackgroundDefinition(BackgroundType.ABERRANT_HEIR, BackgroundSource.EBERRON, (AbilityType.STRENGTH, AbilityType.CONSTITUTION, AbilityType.CHARISMA), BackgroundOriginFeatType.ABERRANT_DRAGONMARK, (SkillType.HISTORY, SkillType.INTIMIDATION), ToolType.DISGUISE_KIT, (eq(EquipmentId.DAGGER), tool(ToolType.DISGUISE_KIT), eq(EquipmentId.COSTUME), eq(EquipmentId.TRAVELERS_CLOTHES), coins(16),)),
    BackgroundType.ARCHAEOLOGIST: BackgroundDefinition(BackgroundType.ARCHAEOLOGIST, BackgroundSource.EBERRON, (AbilityType.DEXTERITY, AbilityType.INTELLIGENCE, AbilityType.WISDOM), BackgroundOriginFeatType.SKILLED, (SkillType.HISTORY, SkillType.SURVIVAL), ToolType.CARTOGRAPHERS_TOOLS, (tool(ToolType.CARTOGRAPHERS_TOOLS), eq(EquipmentId.BULLSEYE_LANTERN), eq(EquipmentId.MAP), eq(EquipmentId.MAP_OR_SCROLL_CASE), eq(EquipmentId.SHOVEL), eq(EquipmentId.TENT), eq(EquipmentId.TRAVELERS_CLOTHES), coins(17),)),
    BackgroundType.HOUSE_AGENT: BackgroundDefinition(BackgroundType.HOUSE_AGENT, BackgroundSource.EBERRON, (AbilityType.STRENGTH, AbilityType.INTELLIGENCE, AbilityType.CHARISMA), BackgroundOriginFeatType.LUCKY, (SkillType.INVESTIGATION, SkillType.PERSUASION), ToolType.ARTISANS_TOOLS, (selected_tool(), eq(EquipmentId.FINE_CLOTHES), coins(20),)),
    BackgroundType.HOUSE_CANNITH_HEIR: BackgroundDefinition(BackgroundType.HOUSE_CANNITH_HEIR, BackgroundSource.EBERRON, (AbilityType.STRENGTH, AbilityType.DEXTERITY, AbilityType.INTELLIGENCE), BackgroundOriginFeatType.MARK_OF_MAKING, (SkillType.INVESTIGATION, SkillType.SLEIGHT_OF_HAND), ToolType.ARTISANS_TOOLS, (selected_tool(), eq(EquipmentId.CROWBAR), eq(EquipmentId.FINE_CLOTHES), eq(EquipmentId.POUCH, 2), coins(17),)),
    BackgroundType.HOUSE_DENEITH_HEIR: BackgroundDefinition(BackgroundType.HOUSE_DENEITH_HEIR, BackgroundSource.EBERRON, (AbilityType.STRENGTH, AbilityType.CONSTITUTION, AbilityType.WISDOM), BackgroundOriginFeatType.MARK_OF_SENTINEL, (SkillType.INSIGHT, SkillType.PERCEPTION), ToolType.GAMING_SET, (eq(EquipmentId.SPEAR), eq(EquipmentId.SHORTBOW), eq(EquipmentId.ARROWS, 20), selected_tool(), eq(EquipmentId.FINE_CLOTHES), eq(EquipmentId.HEALERS_KIT), eq(EquipmentId.QUIVER), coins(1),)),
    BackgroundType.HOUSE_GHALLANDA_HEIR: BackgroundDefinition(BackgroundType.HOUSE_GHALLANDA_HEIR, BackgroundSource.EBERRON, (AbilityType.DEXTERITY, AbilityType.WISDOM, AbilityType.CHARISMA), BackgroundOriginFeatType.MARK_OF_HOSPITALITY, (SkillType.INSIGHT, SkillType.PERSUASION), ToolType.COOKS_UTENSILS, (tool(ToolType.COOKS_UTENSILS), eq(EquipmentId.FINE_CLOTHES), eq(EquipmentId.IRON_POT), eq(EquipmentId.LAMP), eq(EquipmentId.OIL, 5), eq(EquipmentId.PERFUME), coins(26),)),
    BackgroundType.HOUSE_JORASCO_HEIR: BackgroundDefinition(BackgroundType.HOUSE_JORASCO_HEIR, BackgroundSource.EBERRON, (AbilityType.DEXTERITY, AbilityType.CONSTITUTION, AbilityType.WISDOM), BackgroundOriginFeatType.MARK_OF_HEALING, (SkillType.MEDICINE, SkillType.STEALTH), ToolType.HERBALISM_KIT, (tool(ToolType.HERBALISM_KIT), eq(EquipmentId.FINE_CLOTHES), eq(EquipmentId.HEALERS_KIT), coins(25),)),
    BackgroundType.HOUSE_KUNDARAK_HEIR: BackgroundDefinition(BackgroundType.HOUSE_KUNDARAK_HEIR, BackgroundSource.EBERRON, (AbilityType.STRENGTH, AbilityType.CONSTITUTION, AbilityType.INTELLIGENCE), BackgroundOriginFeatType.MARK_OF_WARDING, (SkillType.ARCANA, SkillType.INVESTIGATION), ToolType.THIEVES_TOOLS, (tool(ToolType.THIEVES_TOOLS), eq(EquipmentId.FINE_CLOTHES), coins(10),)),
    BackgroundType.HOUSE_LYRANDAR_HEIR: BackgroundDefinition(BackgroundType.HOUSE_LYRANDAR_HEIR, BackgroundSource.EBERRON, (AbilityType.STRENGTH, AbilityType.DEXTERITY, AbilityType.CHARISMA), BackgroundOriginFeatType.MARK_OF_STORM, (SkillType.ACROBATICS, SkillType.NATURE), ToolType.NAVIGATORS_TOOLS, (tool(ToolType.NAVIGATORS_TOOLS), eq(EquipmentId.FINE_CLOTHES), coins(10),)),
    BackgroundType.HOUSE_MEDANI_HEIR: BackgroundDefinition(BackgroundType.HOUSE_MEDANI_HEIR, BackgroundSource.EBERRON, (AbilityType.DEXTERITY, AbilityType.INTELLIGENCE, AbilityType.WISDOM), BackgroundOriginFeatType.MARK_OF_DETECTION, (SkillType.INSIGHT, SkillType.INVESTIGATION), ToolType.DISGUISE_KIT, (tool(ToolType.DISGUISE_KIT), eq(EquipmentId.FINE_CLOTHES), coins(10),)),
    BackgroundType.HOUSE_ORIEN_HEIR: BackgroundDefinition(BackgroundType.HOUSE_ORIEN_HEIR, BackgroundSource.EBERRON, (AbilityType.DEXTERITY, AbilityType.CONSTITUTION, AbilityType.INTELLIGENCE), BackgroundOriginFeatType.MARK_OF_PASSAGE, (SkillType.ACROBATICS, SkillType.ATHLETICS), ToolType.CARTOGRAPHERS_TOOLS, (tool(ToolType.CARTOGRAPHERS_TOOLS), eq(EquipmentId.FINE_CLOTHES), eq(EquipmentId.MAP), eq(EquipmentId.MAP_OR_SCROLL_CASE), coins(18),)),
    BackgroundType.HOUSE_PHIARLAN_HEIR: BackgroundDefinition(BackgroundType.HOUSE_PHIARLAN_HEIR, BackgroundSource.EBERRON, (AbilityType.DEXTERITY, AbilityType.WISDOM, AbilityType.CHARISMA), BackgroundOriginFeatType.MARK_OF_SHADOW, (SkillType.DECEPTION, SkillType.STEALTH), ToolType.DISGUISE_KIT, (tool(ToolType.DISGUISE_KIT), eq(EquipmentId.FINE_CLOTHES), coins(10),)),
    BackgroundType.HOUSE_SIVIS_HEIR: BackgroundDefinition(BackgroundType.HOUSE_SIVIS_HEIR, BackgroundSource.EBERRON, (AbilityType.INTELLIGENCE, AbilityType.WISDOM, AbilityType.CHARISMA), BackgroundOriginFeatType.MARK_OF_SCRIBING, (SkillType.HISTORY, SkillType.PERCEPTION), ToolType.CALLIGRAPHERS_SUPPLIES, (tool(ToolType.CALLIGRAPHERS_SUPPLIES), eq(EquipmentId.FINE_CLOTHES), eq(EquipmentId.INK), eq(EquipmentId.INK_PEN, 5), eq(EquipmentId.PAPER, 30), eq(EquipmentId.PARCHMENT, 9), coins(8),)),
    BackgroundType.HOUSE_THRASHK_HEIR: BackgroundDefinition(BackgroundType.HOUSE_THRASHK_HEIR, BackgroundSource.EBERRON, (AbilityType.CONSTITUTION, AbilityType.INTELLIGENCE, AbilityType.WISDOM), BackgroundOriginFeatType.MARK_OF_FINDING, (SkillType.PERCEPTION, SkillType.SURVIVAL), ToolType.GAMING_SET, (selected_tool(), eq(EquipmentId.CLIMBERS_KIT), eq(EquipmentId.FINE_CLOTHES), eq(EquipmentId.HUNTING_TRAP), eq(EquipmentId.MANACLES), coins(2),)),
    BackgroundType.HOUSE_THURANNI_HEIR: BackgroundDefinition(BackgroundType.HOUSE_THURANNI_HEIR, BackgroundSource.EBERRON, (AbilityType.DEXTERITY, AbilityType.INTELLIGENCE, AbilityType.CHARISMA), BackgroundOriginFeatType.MARK_OF_SHADOW, (SkillType.PERFORMANCE, SkillType.STEALTH), ToolType.MUSICAL_INSTRUMENT, (selected_tool(), eq(EquipmentId.COSTUME), eq(EquipmentId.FINE_CLOTHES), coins(13),)),
    BackgroundType.HOUSE_VADALIS_HEIR: BackgroundDefinition(BackgroundType.HOUSE_VADALIS_HEIR, BackgroundSource.EBERRON, (AbilityType.CONSTITUTION, AbilityType.WISDOM, AbilityType.CHARISMA), BackgroundOriginFeatType.MARK_OF_HANDLING, (SkillType.ANIMAL_HANDLING, SkillType.NATURE), ToolType.HERBALISM_KIT, (tool(ToolType.HERBALISM_KIT), eq(EquipmentId.FINE_CLOTHES), eq(EquipmentId.NET), coins(29),)),
    BackgroundType.INQUISITIVE: BackgroundDefinition(BackgroundType.INQUISITIVE, BackgroundSource.EBERRON, (AbilityType.CONSTITUTION, AbilityType.INTELLIGENCE, AbilityType.CHARISMA), BackgroundOriginFeatType.ALERT, (SkillType.INSIGHT, SkillType.INVESTIGATION), ToolType.THIEVES_TOOLS, (tool(ToolType.THIEVES_TOOLS), eq(EquipmentId.BULLSEYE_LANTERN), eq(EquipmentId.CROWBAR), eq(EquipmentId.OIL, 10), eq(EquipmentId.TRAVELERS_CLOTHES), coins(10),)),
    BackgroundType.CHONDATHAN_FREEBOOTER: BackgroundDefinition(BackgroundType.CHONDATHAN_FREEBOOTER, BackgroundSource.FAERUN, (AbilityType.STRENGTH, AbilityType.DEXTERITY, AbilityType.WISDOM), BackgroundOriginFeatType.SKILLED, (SkillType.ATHLETICS, SkillType.SLEIGHT_OF_HAND), ToolType.WEAVERS_TOOLS, (eq(EquipmentId.DAGGER), tool(ToolType.WEAVERS_TOOLS), eq(EquipmentId.BACKPACK), eq(EquipmentId.BALL_BEARINGS), eq(EquipmentId.BASKET), eq(EquipmentId.BEDROLL), eq(EquipmentId.BUCKET), eq(EquipmentId.RATIONS, 3), eq(EquipmentId.ROPE), eq(EquipmentId.SIGNAL_WHISTLE), eq(EquipmentId.TRAVELERS_CLOTHES), coins(38),)),
    BackgroundType.DEAD_MAGIC_DWELLER: BackgroundDefinition(BackgroundType.DEAD_MAGIC_DWELLER, BackgroundSource.FAERUN, (AbilityType.STRENGTH, AbilityType.CONSTITUTION, AbilityType.WISDOM), BackgroundOriginFeatType.HEALER, (SkillType.MEDICINE, SkillType.SURVIVAL), ToolType.LEATHERWORKERS_TOOLS, (eq(EquipmentId.GREATCLUB), tool(ToolType.LEATHERWORKERS_TOOLS), eq(EquipmentId.BEDROLL), eq(EquipmentId.BLANKET), eq(EquipmentId.HEALERS_KIT), eq(EquipmentId.POLE), eq(EquipmentId.RATIONS, 3), eq(EquipmentId.TENT), eq(EquipmentId.TINDERBOX), eq(EquipmentId.TORCHES, 5), eq(EquipmentId.TRAVELERS_CLOTHES), eq(EquipmentId.WATERSKIN), coins(32),)),
    BackgroundType.DRAGON_CULTIST: BackgroundDefinition(BackgroundType.DRAGON_CULTIST, BackgroundSource.FAERUN, (AbilityType.DEXTERITY, AbilityType.CONSTITUTION, AbilityType.INTELLIGENCE), BackgroundOriginFeatType.CULT_OF_THE_DRAGON_INITIATE, (SkillType.DECEPTION, SkillType.STEALTH), ToolType.CALLIGRAPHERS_SUPPLIES, (tool(ToolType.CALLIGRAPHERS_SUPPLIES), eq(EquipmentId.DAGGER), eq(EquipmentId.GLASS_BOTTLE), eq(EquipmentId.LAMP), eq(EquipmentId.MANACLES), eq(EquipmentId.OIL, 5), eq(EquipmentId.POUCH, 2), eq(EquipmentId.ROBE), eq(EquipmentId.ROPE), coins(30),)),
    BackgroundType.EMERALD_ENCLAVE_CARETAKER: BackgroundDefinition(BackgroundType.EMERALD_ENCLAVE_CARETAKER, BackgroundSource.FAERUN, (AbilityType.CONSTITUTION, AbilityType.INTELLIGENCE, AbilityType.WISDOM), BackgroundOriginFeatType.EMERALD_ENCLAVE_FLEDGLING, (SkillType.NATURE, SkillType.SURVIVAL), ToolType.HERBALISM_KIT, (eq(EquipmentId.SHORTBOW), eq(EquipmentId.ARROWS, 20), tool(ToolType.HERBALISM_KIT), eq(EquipmentId.BEDROLL), eq(EquipmentId.BLANKET), eq(EquipmentId.POUCH), eq(EquipmentId.TENT), eq(EquipmentId.TRAVELERS_CLOTHES), coins(13),)),
    BackgroundType.FLAMING_FIST_MERCENARY: BackgroundDefinition(BackgroundType.FLAMING_FIST_MERCENARY, BackgroundSource.FAERUN, (AbilityType.STRENGTH, AbilityType.CONSTITUTION, AbilityType.CHARISMA), BackgroundOriginFeatType.TOUGH, (SkillType.INTIMIDATION, SkillType.PERCEPTION), ToolType.SMITHS_TOOLS, (eq(EquipmentId.MACE), tool(ToolType.SMITHS_TOOLS), eq(EquipmentId.FINE_CLOTHES), eq(EquipmentId.MANACLES), eq(EquipmentId.PORTABLE_RAM), coins(4),)),
    BackgroundType.GENIE_TOUCHED: BackgroundDefinition(BackgroundType.GENIE_TOUCHED, BackgroundSource.FAERUN, (AbilityType.DEXTERITY, AbilityType.WISDOM, AbilityType.CHARISMA), BackgroundOriginFeatType.MAGIC_INITIATE_WIZARD, (SkillType.PERCEPTION, SkillType.PERSUASION), ToolType.GLASSBLOWERS_TOOLS, (eq(EquipmentId.LIGHT_HAMMER), tool(ToolType.GLASSBLOWERS_TOOLS), eq(EquipmentId.FINE_CLOTHES), eq(EquipmentId.LAMP), eq(EquipmentId.OIL, 3), eq(EquipmentId.WATERSKIN), coins(2),)),
    BackgroundType.HARPER: BackgroundDefinition(BackgroundType.HARPER, BackgroundSource.FAERUN, (AbilityType.DEXTERITY, AbilityType.INTELLIGENCE, AbilityType.CHARISMA), BackgroundOriginFeatType.HARPER_AGENT, (SkillType.PERFORMANCE, SkillType.SLEIGHT_OF_HAND), ToolType.DISGUISE_KIT, (tool(ToolType.DISGUISE_KIT), eq(EquipmentId.BEDROLL), eq(EquipmentId.COSTUME), eq(EquipmentId.GRAPPLING_HOOK), eq(EquipmentId.ROPE), eq(EquipmentId.TRAVELERS_CLOTHES), coins(14),)),
    BackgroundType.ICE_FISHER: BackgroundDefinition(BackgroundType.ICE_FISHER, BackgroundSource.FAERUN, (AbilityType.STRENGTH, AbilityType.DEXTERITY, AbilityType.CONSTITUTION), BackgroundOriginFeatType.ALERT, (SkillType.ANIMAL_HANDLING, SkillType.ATHLETICS), ToolType.WOODCARVERS_TOOLS, (tool(ToolType.WOODCARVERS_TOOLS), eq(EquipmentId.BASKET), eq(EquipmentId.BLOCK_AND_TACKLE), eq(EquipmentId.BUCKET), eq(EquipmentId.CHAIN), eq(EquipmentId.HUNTING_TRAP), eq(EquipmentId.NET), eq(EquipmentId.POLE), eq(EquipmentId.RATIONS, 3), eq(EquipmentId.ROPE), eq(EquipmentId.TRAVELERS_CLOTHES), coins(32),)),
    BackgroundType.KNIGHT_OF_THE_GAUNTLET: BackgroundDefinition(BackgroundType.KNIGHT_OF_THE_GAUNTLET, BackgroundSource.FAERUN, (AbilityType.STRENGTH, AbilityType.INTELLIGENCE, AbilityType.WISDOM), BackgroundOriginFeatType.TYRO_OF_THE_GAUNTLET, (SkillType.ATHLETICS, SkillType.MEDICINE), ToolType.SMITHS_TOOLS, (eq(EquipmentId.SPEAR), tool(ToolType.SMITHS_TOOLS), eq(EquipmentId.BULLSEYE_LANTERN), eq(EquipmentId.HOLY_SYMBOL), eq(EquipmentId.MANACLES), eq(EquipmentId.OIL, 5), eq(EquipmentId.TINDERBOX), eq(EquipmentId.TRAVELERS_CLOTHES), coins(9),)),
    BackgroundType.LORDS_ALLIANCE_VASSAL: BackgroundDefinition(BackgroundType.LORDS_ALLIANCE_VASSAL, BackgroundSource.FAERUN, (AbilityType.STRENGTH, AbilityType.INTELLIGENCE, AbilityType.CHARISMA), BackgroundOriginFeatType.LORDS_ALLIANCE_AGENT, (SkillType.INSIGHT, SkillType.PERSUASION), ToolType.CALLIGRAPHERS_SUPPLIES, (eq(EquipmentId.JAVELIN, 2), tool(ToolType.CALLIGRAPHERS_SUPPLIES), eq(EquipmentId.FINE_CLOTHES), eq(EquipmentId.INK), eq(EquipmentId.INK_PEN, 5), eq(EquipmentId.PARCHMENT, 9), coins(13),)),
    BackgroundType.MOONWELL_PILGRIM: BackgroundDefinition(BackgroundType.MOONWELL_PILGRIM, BackgroundSource.FAERUN, (AbilityType.CONSTITUTION, AbilityType.WISDOM, AbilityType.CHARISMA), BackgroundOriginFeatType.MAGIC_INITIATE_DRUID, (SkillType.NATURE, SkillType.PERFORMANCE), ToolType.PAINTERS_SUPPLIES, (eq(EquipmentId.QUARTERSTAFF), tool(ToolType.PAINTERS_SUPPLIES), eq(EquipmentId.BEDROLL), eq(EquipmentId.BELL), eq(EquipmentId.POUCH), eq(EquipmentId.ROBE), eq(EquipmentId.STRING), eq(EquipmentId.TRAVELERS_CLOTHES), eq(EquipmentId.WATERSKIN), coins(34),)),
    BackgroundType.MULHORANDI_TOMB_RAIDER: BackgroundDefinition(BackgroundType.MULHORANDI_TOMB_RAIDER, BackgroundSource.FAERUN, (AbilityType.DEXTERITY, AbilityType.CONSTITUTION, AbilityType.INTELLIGENCE), BackgroundOriginFeatType.LUCKY, (SkillType.INVESTIGATION, SkillType.RELIGION), ToolType.MASONS_TOOLS, (eq(EquipmentId.DAGGER), eq(EquipmentId.LIGHT_HAMMER), tool(ToolType.MASONS_TOOLS), eq(EquipmentId.BACKPACK), eq(EquipmentId.BEDROLL), eq(EquipmentId.CROWBAR), eq(EquipmentId.LADDER), eq(EquipmentId.POLE), eq(EquipmentId.POUCH, 2), eq(EquipmentId.ROPE), eq(EquipmentId.STRING), eq(EquipmentId.TINDERBOX), eq(EquipmentId.TORCHES, 5), eq(EquipmentId.TRAVELERS_CLOTHES), eq(EquipmentId.WATERSKIN), coins(26),)),
    BackgroundType.MYTHALKEEPER: BackgroundDefinition(BackgroundType.MYTHALKEEPER, BackgroundSource.FAERUN, (AbilityType.INTELLIGENCE, AbilityType.WISDOM, AbilityType.CHARISMA), BackgroundOriginFeatType.CRAFTER, (SkillType.ARCANA, SkillType.HISTORY), ToolType.JEWELERS_TOOLS, (eq(EquipmentId.QUARTERSTAFF), tool(ToolType.JEWELERS_TOOLS), eq(EquipmentId.PERFUME), eq(EquipmentId.POUCH), eq(EquipmentId.ROBE), eq(EquipmentId.SHOVEL), eq(EquipmentId.STRING), eq(EquipmentId.WATERSKIN), coins(16),)),
    BackgroundType.PURPLE_DRAGON_SQUIRE: BackgroundDefinition(BackgroundType.PURPLE_DRAGON_SQUIRE, BackgroundSource.FAERUN, (AbilityType.STRENGTH, AbilityType.WISDOM, AbilityType.CHARISMA), BackgroundOriginFeatType.PURPLE_DRAGON_ROOK, (SkillType.ANIMAL_HANDLING, SkillType.INSIGHT), ToolType.NAVIGATORS_TOOLS, (eq(EquipmentId.SPEAR), tool(ToolType.NAVIGATORS_TOOLS), eq(EquipmentId.FINE_CLOTHES), coins(9),)),
    BackgroundType.RASHEMI_WANDERER: BackgroundDefinition(BackgroundType.RASHEMI_WANDERER, BackgroundSource.FAERUN, (AbilityType.STRENGTH, AbilityType.CONSTITUTION, AbilityType.CHARISMA), BackgroundOriginFeatType.TOUGH, (SkillType.INTIMIDATION, SkillType.PERCEPTION), ToolType.CARTOGRAPHERS_TOOLS, (tool(ToolType.CARTOGRAPHERS_TOOLS), eq(EquipmentId.BACKPACK), eq(EquipmentId.BEDROLL), eq(EquipmentId.HOODED_LANTERN), eq(EquipmentId.OIL, 3), eq(EquipmentId.ROPE), eq(EquipmentId.TINDERBOX), eq(EquipmentId.TRAVELERS_CLOTHES), eq(EquipmentId.WATERSKIN), coins(23),)),
    BackgroundType.SHADOWMASTERS_EXILE: BackgroundDefinition(BackgroundType.SHADOWMASTERS_EXILE, BackgroundSource.FAERUN, (AbilityType.DEXTERITY, AbilityType.INTELLIGENCE, AbilityType.CHARISMA), BackgroundOriginFeatType.SAVAGE_ATTACKER, (SkillType.ACROBATICS, SkillType.STEALTH), ToolType.THIEVES_TOOLS, (eq(EquipmentId.DAGGER, 2), tool(ToolType.THIEVES_TOOLS), eq(EquipmentId.CALTROPS), eq(EquipmentId.COSTUME), eq(EquipmentId.GRAPPLING_HOOK), eq(EquipmentId.IRON_SPIKES), eq(EquipmentId.MIRROR), eq(EquipmentId.POUCH, 2), eq(EquipmentId.ROPE), eq(EquipmentId.TRAVELERS_CLOTHES), coins(3),)),
    BackgroundType.SPELLFIRE_INITIATE: BackgroundDefinition(BackgroundType.SPELLFIRE_INITIATE, BackgroundSource.FAERUN, (AbilityType.CONSTITUTION, AbilityType.INTELLIGENCE, AbilityType.CHARISMA), BackgroundOriginFeatType.SPELLFIRE_SPARK, (SkillType.ARCANA, SkillType.PERCEPTION), ToolType.GAMING_SET, (selected_tool(), eq(EquipmentId.ARCANE_FOCUS, name='Arcane Focus (Crystal or Wand)'), eq(EquipmentId.POUCH, 2), eq(EquipmentId.TRAVELERS_CLOTHES), coins(36),)),
    BackgroundType.ZHENTARIM_MERCENARY: BackgroundDefinition(BackgroundType.ZHENTARIM_MERCENARY, BackgroundSource.FAERUN, (AbilityType.STRENGTH, AbilityType.DEXTERITY, AbilityType.CHARISMA), BackgroundOriginFeatType.ZHENTARIM_RUFFIAN, (SkillType.INTIMIDATION, SkillType.PERCEPTION), ToolType.FORGERY_KIT, (eq(EquipmentId.CLUB), eq(EquipmentId.DAGGER), tool(ToolType.FORGERY_KIT), eq(EquipmentId.FINE_CLOTHES), eq(EquipmentId.HOODED_LANTERN), eq(EquipmentId.OIL, 3), eq(EquipmentId.POUCH, 2), eq(EquipmentId.STRING), eq(EquipmentId.TINDERBOX), coins(11),)),
    BackgroundType.HAUNTED_ONE: BackgroundDefinition(BackgroundType.HAUNTED_ONE, BackgroundSource.RAVENLOFT, (AbilityType.CONSTITUTION, AbilityType.WISDOM, AbilityType.CHARISMA), BackgroundOriginFeatType.SURVIVOR, (SkillType.ARCANA, SkillType.SURVIVAL), ToolType.GAMING_SET, (selected_tool(), eq(EquipmentId.CROWBAR), eq(EquipmentId.HOLY_WATER), eq(EquipmentId.MIRROR), eq(EquipmentId.OIL, 2), eq(EquipmentId.SIGNAL_WHISTLE), eq(EquipmentId.TINDERBOX), eq(EquipmentId.TRAVELERS_CLOTHES), eq(EquipmentId.TORCHES, 5), eq(EquipmentId.WATERSKIN), coins(14),)),
    BackgroundType.INVESTIGATOR: BackgroundDefinition(BackgroundType.INVESTIGATOR, BackgroundSource.RAVENLOFT, (AbilityType.INTELLIGENCE, AbilityType.WISDOM, AbilityType.CHARISMA), BackgroundOriginFeatType.SHARP_EYE, (SkillType.INSIGHT, SkillType.INVESTIGATION), ToolType.DISGUISE_KIT, (tool(ToolType.DISGUISE_KIT), eq(EquipmentId.MANACLES), eq(EquipmentId.SHOVEL), eq(EquipmentId.TRAVELERS_CLOTHES), eq(EquipmentId.VIAL, 3), coins(16),)),
    BackgroundType.MIST_WANDERER: BackgroundDefinition(BackgroundType.MIST_WANDERER, BackgroundSource.RAVENLOFT, (AbilityType.DEXTERITY, AbilityType.CONSTITUTION, AbilityType.WISDOM), BackgroundOriginFeatType.MIST_WALKER, (SkillType.SURVIVAL, SkillType.STEALTH), ToolType.ARTISANS_TOOLS, (selected_tool(), eq(EquipmentId.LAMP), eq(EquipmentId.OIL, 5), eq(EquipmentId.POUCH), eq(EquipmentId.ROPE), eq(EquipmentId.TINDERBOX), eq(EquipmentId.TRAVELERS_CLOTHES), coins(30),)),
    BackgroundType.SPIRIT_MEDIUM: BackgroundDefinition(BackgroundType.SPIRIT_MEDIUM, BackgroundSource.RAVENLOFT, (AbilityType.CONSTITUTION, AbilityType.INTELLIGENCE, AbilityType.WISDOM), BackgroundOriginFeatType.GATHERED_WHISPERS, (SkillType.INSIGHT, SkillType.RELIGION), ToolType.GAMING_SET, (eq(EquipmentId.DAGGER), selected_tool(), eq(EquipmentId.BASKET), eq(EquipmentId.BELL), eq(EquipmentId.CANDLES, 8), eq(EquipmentId.INK), eq(EquipmentId.INK_PEN), eq(EquipmentId.PAPER, 5), eq(EquipmentId.TINDERBOX), eq(EquipmentId.TRAVELERS_CLOTHES), coins(32),)),
    BackgroundType.CAROUSER: BackgroundDefinition(BackgroundType.CAROUSER, BackgroundSource.EXOTIC, (AbilityType.DEXTERITY, AbilityType.INTELLIGENCE, AbilityType.CHARISMA), BackgroundOriginFeatType.TIRELESS_REVELER, (SkillType.DECEPTION, SkillType.PERSUASION), ToolType.GAMING_SET, (eq(EquipmentId.DAGGER), selected_tool(), eq(EquipmentId.FINE_CLOTHES), eq(EquipmentId.GLASS_BOTTLE), eq(EquipmentId.MIRROR), eq(EquipmentId.PERFUME), eq(EquipmentId.POUCH), eq(EquipmentId.TINDERBOX), coins(19),)),
    BackgroundType.LORWYN_EXPERT: BackgroundDefinition(BackgroundType.LORWYN_EXPERT, BackgroundSource.EXOTIC, (AbilityType.STRENGTH, AbilityType.CONSTITUTION, AbilityType.WISDOM), BackgroundOriginFeatType.CHILD_OF_THE_SUN, (SkillType.ATHLETICS, SkillType.NATURE), ToolType.CARTOGRAPHERS_TOOLS, (eq(EquipmentId.QUARTERSTAFF), tool(ToolType.CARTOGRAPHERS_TOOLS), eq(EquipmentId.BACKPACK), eq(EquipmentId.BASKET), eq(EquipmentId.PARCHMENT, 4), eq(EquipmentId.ROPE), eq(EquipmentId.TRAVELERS_CLOTHES), coins(29),)),
    BackgroundType.PACT_SEEKER: BackgroundDefinition(BackgroundType.PACT_SEEKER, BackgroundSource.EXOTIC, (AbilityType.CONSTITUTION, AbilityType.INTELLIGENCE, AbilityType.CHARISMA), BackgroundOriginFeatType.FEY_PACT, (SkillType.ARCANA, SkillType.PERSUASION), ToolType.CALLIGRAPHERS_SUPPLIES, (eq(EquipmentId.BOOK), tool(ToolType.CALLIGRAPHERS_SUPPLIES), eq(EquipmentId.INK), eq(EquipmentId.INK_PEN), eq(EquipmentId.PARCHMENT, 10), eq(EquipmentId.TRAVELERS_CLOTHES), coins(2),)),
    BackgroundType.SHADOWMOOR_EXPERT: BackgroundDefinition(BackgroundType.SHADOWMOOR_EXPERT, BackgroundSource.EXOTIC, (AbilityType.DEXTERITY, AbilityType.INTELLIGENCE, AbilityType.CHARISMA), BackgroundOriginFeatType.SHADOWMOOR_HEXER, (SkillType.ACROBATICS, SkillType.DECEPTION), ToolType.GLASSBLOWERS_TOOLS, (eq(EquipmentId.DAGGER), tool(ToolType.GLASSBLOWERS_TOOLS), eq(EquipmentId.BACKPACK), eq(EquipmentId.HUNTING_TRAP), eq(EquipmentId.LAMP), eq(EquipmentId.OIL, 3), eq(EquipmentId.TRAVELERS_CLOTHES), eq(EquipmentId.WATERSKIN), coins(8),)),
    BackgroundType.VAMPIRE_DEVOTEE: BackgroundDefinition(BackgroundType.VAMPIRE_DEVOTEE, BackgroundSource.EXOTIC, (AbilityType.STRENGTH, AbilityType.CONSTITUTION, AbilityType.CHARISMA), BackgroundOriginFeatType.VAMPIRE_S_PLAYTHING, (SkillType.PERSUASION, SkillType.STEALTH), ToolType.COOKS_UTENSILS, (tool(ToolType.COOKS_UTENSILS), eq(EquipmentId.FINE_CLOTHES), eq(EquipmentId.GLASS_BOTTLE, 2), eq(EquipmentId.HEALERS_KIT), eq(EquipmentId.PERFUME), eq(EquipmentId.LAMP), eq(EquipmentId.OIL, 3), eq(EquipmentId.WATERSKIN), coins(19),)),
    BackgroundType.VAMPIRE_SURVIVOR: BackgroundDefinition(BackgroundType.VAMPIRE_SURVIVOR, BackgroundSource.EXOTIC, (AbilityType.DEXTERITY, AbilityType.CONSTITUTION, AbilityType.WISDOM), BackgroundOriginFeatType.VAMPIRE_HUNTER, (SkillType.INSIGHT, SkillType.RELIGION), ToolType.WOODCARVERS_TOOLS, (tool(ToolType.WOODCARVERS_TOOLS), eq(EquipmentId.CROWBAR), eq(EquipmentId.HOODED_LANTERN), eq(EquipmentId.HOLY_SYMBOL, name='Holy Symbol (reliquary)'), eq(EquipmentId.HOLY_WATER), eq(EquipmentId.MIRROR), eq(EquipmentId.OIL, 3), eq(EquipmentId.TINDERBOX), eq(EquipmentId.TRAVELERS_CLOTHES), eq(EquipmentId.WATERSKIN), coins(4),)),
}
