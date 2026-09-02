from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from dnd_board.character_sheet import AbilityType, enum_key
from dnd_board.rules.backgrounds import ToolType
from dnd_board.rules.equipment import EquipmentCost, VARIABLE_COST, cost_gp, cost_sp


class ToolCategory(Enum):
    ARTISAN = "Artisan Tools"
    GAMING_SET = "Gaming Set"
    MUSICAL_INSTRUMENT = "Musical Instrument"
    OTHER = "Other Tools"


@dataclass(frozen=True)
class ToolUtilizeAction:
    description: str
    dc: int


@dataclass(frozen=True)
class ToolDefinition:
    toolType: ToolType
    category: ToolCategory
    ability: AbilityType
    weightLb: int | None
    cost: EquipmentCost
    utilizeActions: tuple[ToolUtilizeAction, ...] = ()
    craftOutputs: tuple[str, ...] = ()
    variantParent: ToolType | None = None
    hasVariants: bool = False

    @property
    def costLabel(self) -> str:
        return self.cost.label


def tool_definition(tool_type: ToolType) -> ToolDefinition:
    return TOOL_DEFINITIONS[tool_type]


def tool_definitions() -> dict[ToolType, ToolDefinition]:
    return dict(TOOL_DEFINITIONS)


def serialized_tool_details() -> dict[str, dict]:
    return {
        enum_key(tool_type): {
            "category": definition.category.value,
            "ability": enum_key(definition.ability),
            "weightLb": definition.weightLb,
            "cost": definition.costLabel,
            "utilizeActions": [
                {"description": action.description, "dc": action.dc}
                for action in definition.utilizeActions
            ],
            "craftOutputs": list(definition.craftOutputs),
            "hasVariants": definition.hasVariants,
            "variantParent": enum_key(definition.variantParent) if definition.variantParent else None,
        }
        for tool_type, definition in TOOL_DEFINITIONS.items()
    }


def artisan_tool(tool_type: ToolType, ability: AbilityType, weight: int, cost: EquipmentCost, utilize: tuple[ToolUtilizeAction, ...], craft: tuple[str, ...]) -> ToolDefinition:
    return ToolDefinition(tool_type, ToolCategory.ARTISAN, ability, weight, cost, utilize, craft)


def other_tool(tool_type: ToolType, ability: AbilityType, weight: int | None, cost: EquipmentCost, utilize: tuple[ToolUtilizeAction, ...], craft: tuple[str, ...] = ()) -> ToolDefinition:
    return ToolDefinition(tool_type, ToolCategory.OTHER, ability, weight, cost, utilize, craft)


def gaming_set(tool_type: ToolType, cost: EquipmentCost) -> ToolDefinition:
    return ToolDefinition(tool_type, ToolCategory.GAMING_SET, AbilityType.WISDOM, None, cost, variantParent=ToolType.GAMING_SET)


def musical_instrument(tool_type: ToolType, weight: int, cost: EquipmentCost) -> ToolDefinition:
    return ToolDefinition(tool_type, ToolCategory.MUSICAL_INSTRUMENT, AbilityType.CHARISMA, weight, cost, variantParent=ToolType.MUSICAL_INSTRUMENT)


TOOL_DEFINITIONS: dict[ToolType, ToolDefinition] = {
    ToolType.ARTISANS_TOOLS: ToolDefinition(ToolType.ARTISANS_TOOLS, ToolCategory.ARTISAN, AbilityType.INTELLIGENCE, None, VARIABLE_COST, hasVariants=True),
    ToolType.ALCHEMISTS_SUPPLIES: artisan_tool(ToolType.ALCHEMISTS_SUPPLIES, AbilityType.INTELLIGENCE, 8, cost_gp(50), (ToolUtilizeAction("Identify a substance", 15), ToolUtilizeAction("Start a fire", 15)), ("Acid", "Alchemist's Fire", "Component Pouch", "Oil", "Paper", "Perfume")),
    ToolType.BREWERS_SUPPLIES: artisan_tool(ToolType.BREWERS_SUPPLIES, AbilityType.INTELLIGENCE, 9, cost_gp(20), (ToolUtilizeAction("Detect poisoned drink", 15), ToolUtilizeAction("Identify alcohol", 10)), ("Antitoxin",)),
    ToolType.CALLIGRAPHERS_SUPPLIES: artisan_tool(ToolType.CALLIGRAPHERS_SUPPLIES, AbilityType.DEXTERITY, 5, cost_gp(10), (ToolUtilizeAction("Write text with impressive flourishes that guard against forgery", 15),), ("Ink", "Spell Scroll")),
    ToolType.CARPENTERS_TOOLS: artisan_tool(ToolType.CARPENTERS_TOOLS, AbilityType.STRENGTH, 6, cost_gp(8), (ToolUtilizeAction("Seal or pry open a door or container", 20),), ("Club", "Greatclub", "Quarterstaff", "Barrel", "Chest", "Ladder", "Pole", "Portable Ram", "Torch")),
    ToolType.CARTOGRAPHERS_TOOLS: artisan_tool(ToolType.CARTOGRAPHERS_TOOLS, AbilityType.WISDOM, 6, cost_gp(15), (ToolUtilizeAction("Draft a map of a small area", 15),), ("Map",)),
    ToolType.COBBLERS_TOOLS: artisan_tool(ToolType.COBBLERS_TOOLS, AbilityType.DEXTERITY, 5, cost_gp(5), (ToolUtilizeAction("Modify footwear to grant Advantage on the wearer's next Dexterity (Acrobatics) check", 10),), ("Climber's Kit",)),
    ToolType.COOKS_UTENSILS: artisan_tool(ToolType.COOKS_UTENSILS, AbilityType.WISDOM, 8, cost_gp(1), (ToolUtilizeAction("Improve food's flavor", 10), ToolUtilizeAction("Detect spoiled or poisoned food", 15)), ("Rations",)),
    ToolType.GLASSBLOWERS_TOOLS: artisan_tool(ToolType.GLASSBLOWERS_TOOLS, AbilityType.INTELLIGENCE, 5, cost_gp(30), (ToolUtilizeAction("Discern what a glass object held in the past 24 hours", 15),), ("Glass Bottle", "Magnifying Glass", "Spyglass", "Vial")),
    ToolType.JEWELERS_TOOLS: artisan_tool(ToolType.JEWELERS_TOOLS, AbilityType.INTELLIGENCE, 2, cost_gp(25), (ToolUtilizeAction("Discern a gem's value", 15),), ("Arcane Focus", "Holy Symbol")),
    ToolType.LEATHERWORKERS_TOOLS: artisan_tool(ToolType.LEATHERWORKERS_TOOLS, AbilityType.DEXTERITY, 5, cost_gp(5), (ToolUtilizeAction("Add a design to a leather item", 10),), ("Sling", "Whip", "Hide Armor", "Leather Armor", "Studded Leather Armor", "Backpack", "Crossbow Bolt Case", "Map or Scroll Case", "Parchment", "Pouch", "Quiver", "Waterskin")),
    ToolType.MASONS_TOOLS: artisan_tool(ToolType.MASONS_TOOLS, AbilityType.STRENGTH, 8, cost_gp(10), (ToolUtilizeAction("Chisel a symbol or hole in stone", 10),), ("Block and Tackle",)),
    ToolType.PAINTERS_SUPPLIES: artisan_tool(ToolType.PAINTERS_SUPPLIES, AbilityType.WISDOM, 5, cost_gp(10), (ToolUtilizeAction("Paint a recognizable image of something you've seen", 10),), ("Druidic Focus", "Holy Symbol")),
    ToolType.POTTERS_TOOLS: artisan_tool(ToolType.POTTERS_TOOLS, AbilityType.INTELLIGENCE, 3, cost_gp(10), (ToolUtilizeAction("Discern what a ceramic object held in the past 24 hours", 15),), ("Jug", "Lamp")),
    ToolType.SMITHS_TOOLS: artisan_tool(ToolType.SMITHS_TOOLS, AbilityType.STRENGTH, 8, cost_gp(20), (ToolUtilizeAction("Pry open a door or container", 20),), ("Any Melee weapon except Club, Greatclub, Quarterstaff, and Whip", "Medium armor except Hide", "Heavy armor", "Ball Bearings", "Bucket", "Caltrops", "Chain", "Crowbar", "Firearm Bullets", "Grappling Hook", "Iron Pot", "Iron Spikes", "Sling Bullets")),
    ToolType.TINKERS_TOOLS: artisan_tool(ToolType.TINKERS_TOOLS, AbilityType.DEXTERITY, 10, cost_gp(50), (ToolUtilizeAction("Assemble a Tiny item composed of scrap, which falls apart in 1 minute", 20),), ("Musket", "Pistol", "Bell", "Bullseye Lantern", "Flask", "Hooded Lantern", "Hunting Trap", "Lock", "Manacles", "Mirror", "Shovel", "Signal Whistle", "Tinderbox")),
    ToolType.WEAVERS_TOOLS: artisan_tool(ToolType.WEAVERS_TOOLS, AbilityType.DEXTERITY, 5, cost_gp(1), (ToolUtilizeAction("Mend a tear in clothing", 10), ToolUtilizeAction("Sew a Tiny design", 10)), ("Padded Armor", "Basket", "Bedroll", "Blanket", "Fine Clothes", "Net", "Robe", "Rope", "Sack", "String", "Tent", "Traveler's Clothes")),
    ToolType.WOODCARVERS_TOOLS: artisan_tool(ToolType.WOODCARVERS_TOOLS, AbilityType.DEXTERITY, 5, cost_gp(1), (ToolUtilizeAction("Carve a pattern in wood", 10),), ("Club", "Greatclub", "Quarterstaff", "Ranged weapons except Pistol, Musket, and Sling", "Arcane Focus", "Arrows", "Bolts", "Druidic Focus", "Ink Pen", "Needles")),
    ToolType.DISGUISE_KIT: other_tool(ToolType.DISGUISE_KIT, AbilityType.CHARISMA, 3, cost_gp(25), (ToolUtilizeAction("Apply makeup", 10),), ("Costume",)),
    ToolType.FORGERY_KIT: other_tool(ToolType.FORGERY_KIT, AbilityType.DEXTERITY, 5, cost_gp(15), (ToolUtilizeAction("Mimic 10 or fewer words of someone else's handwriting", 15), ToolUtilizeAction("Duplicate a wax seal", 20))),
    ToolType.GAMING_SET: ToolDefinition(ToolType.GAMING_SET, ToolCategory.GAMING_SET, AbilityType.WISDOM, None, VARIABLE_COST, (ToolUtilizeAction("Discern whether someone is cheating", 10), ToolUtilizeAction("Win the game", 20)), hasVariants=True),
    ToolType.DICE_SET: gaming_set(ToolType.DICE_SET, cost_sp(1)),
    ToolType.DRAGONCHESS_SET: gaming_set(ToolType.DRAGONCHESS_SET, cost_gp(1)),
    ToolType.PLAYING_CARD_SET: gaming_set(ToolType.PLAYING_CARD_SET, cost_sp(5)),
    ToolType.THREE_DRAGON_ANTE_SET: gaming_set(ToolType.THREE_DRAGON_ANTE_SET, cost_gp(1)),
    ToolType.HERBALISM_KIT: other_tool(ToolType.HERBALISM_KIT, AbilityType.INTELLIGENCE, 3, cost_gp(5), (ToolUtilizeAction("Identify a plant", 10),), ("Antitoxin", "Candle", "Healer's Kit", "Potion of Healing")),
    ToolType.MUSICAL_INSTRUMENT: ToolDefinition(ToolType.MUSICAL_INSTRUMENT, ToolCategory.MUSICAL_INSTRUMENT, AbilityType.CHARISMA, None, VARIABLE_COST, (ToolUtilizeAction("Play a known tune", 10), ToolUtilizeAction("Improvise a song", 15)), hasVariants=True),
    ToolType.BAGPIPES: musical_instrument(ToolType.BAGPIPES, 6, cost_gp(30)),
    ToolType.DRUM: musical_instrument(ToolType.DRUM, 3, cost_gp(6)),
    ToolType.DULCIMER: musical_instrument(ToolType.DULCIMER, 10, cost_gp(25)),
    ToolType.FLUTE: musical_instrument(ToolType.FLUTE, 1, cost_gp(2)),
    ToolType.HORN: musical_instrument(ToolType.HORN, 2, cost_gp(3)),
    ToolType.LUTE: musical_instrument(ToolType.LUTE, 2, cost_gp(35)),
    ToolType.LYRE: musical_instrument(ToolType.LYRE, 2, cost_gp(30)),
    ToolType.PAN_FLUTE: musical_instrument(ToolType.PAN_FLUTE, 2, cost_gp(12)),
    ToolType.SHAWM: musical_instrument(ToolType.SHAWM, 1, cost_gp(2)),
    ToolType.VIOL: musical_instrument(ToolType.VIOL, 1, cost_gp(30)),
    ToolType.NAVIGATORS_TOOLS: other_tool(ToolType.NAVIGATORS_TOOLS, AbilityType.WISDOM, 2, cost_gp(25), (ToolUtilizeAction("Plot a course", 10), ToolUtilizeAction("Determine position by stargazing", 15))),
    ToolType.POISONERS_KIT: other_tool(ToolType.POISONERS_KIT, AbilityType.INTELLIGENCE, 2, cost_gp(50), (ToolUtilizeAction("Detect a poisoned object", 10),), ("Basic Poison",)),
    ToolType.THIEVES_TOOLS: other_tool(ToolType.THIEVES_TOOLS, AbilityType.DEXTERITY, 1, cost_gp(25), (ToolUtilizeAction("Pick a lock", 15), ToolUtilizeAction("Disarm a trap", 15))),
}
