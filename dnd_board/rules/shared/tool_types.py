from enum import Enum


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

SELECTABLE_TOOL_TYPES = tuple(
    tool for tool in ToolType
    if tool not in {ToolType.ARTISANS_TOOLS, ToolType.GAMING_SET, ToolType.MUSICAL_INSTRUMENT}
)
