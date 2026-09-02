from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import TYPE_CHECKING

from dnd_board.character_sheet import (
    ArmorCategory,
    AttackRangeType,
    CurrencyUnit,
    DamageType,
    DiceType,
    EquipmentItem,
    EquipmentSlot,
    EquipmentType,
    Money,
    WeaponCategory,
    WeaponProperty,
    enum_key,
    enum_label,
    enum_value,
)

if TYPE_CHECKING:
    from dnd_board.rules.backgrounds import ToolType


class EquipmentId(Enum):
    ACID = "Acid"
    ALCHEMISTS_FIRE = "Alchemist's Fire"
    ARCANE_FOCUS = "Arcane Focus"
    ARROWS = "Arrows"
    BACKPACK = "Backpack"
    BALL_BEARINGS = "Ball Bearings"
    BASKET = "Basket"
    BEDROLL = "Bedroll"
    BELL = "Bell"
    BLANKET = "Blanket"
    BLOCK_AND_TACKLE = "Block and Tackle"
    BOLTS = "Bolts"
    BOOK = "Book"
    BULLSEYE_LANTERN = "Bullseye Lantern"
    BUCKET = "Bucket"
    CALTROPS = "Caltrops"
    CANDLES = "Candles"
    CHAIN = "Chain"
    CLIMBERS_KIT = "Climber's Kit"
    CLUB = "Club"
    COSTUME = "Costume"
    CROWBAR = "Crowbar"
    DAGGER = "Dagger"
    FINE_CLOTHES = "Fine Clothes"
    GAMING_SET = "Gaming Set"
    GLASS_BOTTLE = "Glass Bottle"
    GRAPPLING_HOOK = "Grappling Hook"
    GREATCLUB = "Greatclub"
    HEALERS_KIT = "Healer's Kit"
    HOLY_SYMBOL = "Holy Symbol"
    HOLY_WATER = "Holy Water"
    HOODED_LANTERN = "Hooded Lantern"
    HUNTING_TRAP = "Hunting Trap"
    INK = "Ink"
    INK_PEN = "Ink Pen"
    IRON_POT = "Iron Pot"
    IRON_SPIKES = "Iron Spikes"
    JAVELIN = "Javelin"
    LADDER = "Ladder"
    LAMP = "Lamp"
    LIGHT_CROSSBOW = "Light Crossbow"
    LIGHT_HAMMER = "Light Hammer"
    MACE = "Mace"
    MANACLES = "Manacles"
    MAP = "Map"
    MAP_OR_SCROLL_CASE = "Map or Scroll Case"
    MIRROR = "Mirror"
    MUSICAL_INSTRUMENT = "Musical Instrument"
    NET = "Net"
    OIL = "Oil"
    PAPER = "Paper"
    PARCHMENT = "Parchment"
    PERFUME = "Perfume"
    POLE = "Pole"
    PORTABLE_RAM = "Portable Ram"
    POUCH = "Pouch"
    QUARTERSTAFF = "Quarterstaff"
    QUIVER = "Quiver"
    RATIONS = "Rations"
    ROBE = "Robe"
    ROPE = "Rope"
    SHORTBOW = "Shortbow"
    SHOVEL = "Shovel"
    SICKLE = "Sickle"
    SIGNAL_WHISTLE = "Signal Whistle"
    SPEAR = "Spear"
    STRING = "String"
    TENT = "Tent"
    TINDERBOX = "Tinderbox"
    TORCHES = "Torches"
    TRAVELERS_CLOTHES = "Traveler's Clothes"
    VIAL = "Vial"
    WATERSKIN = "Waterskin"


class EquipmentCategory(Enum):
    ADVENTURING_GEAR = "Adventuring Gear"
    AMMUNITION = "Ammunition"
    ARMOR = "Armor"
    CLOTHING = "Clothing"
    FOCUS = "Focus"
    SHIELD = "Shield"
    TOOL = "Tool"
    WEAPON = "Weapon"


class EquipmentCostType(Enum):
    FIXED = "Fixed"
    VARIABLE = "Variable"


@dataclass(frozen=True)
class EquipmentCost:
    type: EquipmentCostType
    money: Money | None = None

    @property
    def label(self) -> str:
        return self.money.label if self.money else "Varies"


def fixed_cost(quantity: int, unit: CurrencyUnit) -> EquipmentCost:
    return EquipmentCost(EquipmentCostType.FIXED, Money(quantity, unit))


def cost_cp(quantity: int) -> EquipmentCost:
    return EquipmentCost(EquipmentCostType.FIXED, Money(quantity, CurrencyUnit.CP))


def cost_sp(quantity: int) -> EquipmentCost:
    return EquipmentCost(EquipmentCostType.FIXED, Money(quantity, CurrencyUnit.SP))


def cost_gp(quantity: int) -> EquipmentCost:
    return EquipmentCost(EquipmentCostType.FIXED, Money(quantity, CurrencyUnit.GP))


VARIABLE_COST = EquipmentCost(EquipmentCostType.VARIABLE)


class WeaponTrainingCategory(Enum):
    SIMPLE = "Simple"
    MARTIAL = "Martial"


class WeaponMastery(Enum):
    CLEAVE = "Cleave"
    GRAZE = "Graze"
    NICK = "Nick"
    PUSH = "Push"
    SAP = "Sap"
    SLOW = "Slow"
    TOPPLE = "Topple"
    VEX = "Vex"


@dataclass(frozen=True)
class EquipmentDefinition:
    equipmentId: EquipmentId
    name: str
    category: EquipmentCategory
    cost: EquipmentCost
    weightLb: float = 0.0
    armorCategory: ArmorCategory | None = None
    armorClass: int = 0
    armorClassBonus: int = 0
    strengthRequirement: int | None = None
    stealthDisadvantage: bool = False
    weaponTraining: WeaponTrainingCategory | None = None
    weaponCategory: WeaponCategory | None = None
    attackRange: AttackRangeType | None = None
    damageDiceCount: int = 0
    damageDiceType: DiceType | None = None
    damageType: DamageType | None = None
    properties: tuple[WeaponProperty, ...] = ()
    normalRangeFeet: int | None = None
    longRangeFeet: int | None = None
    mastery: WeaponMastery | None = None
    toolType: ToolType | None = None
    notes: str = ""

    @property
    def itemType(self) -> EquipmentType:
        return equipment_type_for_category(self.category)

    @property
    def costLabel(self) -> str:
        return self.cost.label


def equipment_type_for_category(category: EquipmentCategory) -> EquipmentType:
    if category == EquipmentCategory.ARMOR:
        return EquipmentType.ARMOR
    if category == EquipmentCategory.SHIELD:
        return EquipmentType.SHIELD
    if category == EquipmentCategory.WEAPON:
        return EquipmentType.WEAPON
    return EquipmentType.GEAR


def equipment_definition(value: str | EquipmentId) -> EquipmentDefinition | None:
    equipment_id = value if isinstance(value, EquipmentId) else enum_value(EquipmentId, value)
    return EQUIPMENT_DEFINITIONS.get(equipment_id)


def equipment_item(value: str | EquipmentId, *, quantity: int = 1, name: str | None = None, notes: str = "") -> EquipmentItem | None:
    definition = equipment_definition(value)
    if definition is None:
        return None
    return EquipmentItem(
        id=equipment_item_id(definition.equipmentId, name),
        name=name or definition.name,
        quantity=quantity,
        weight=definition.weightLb * quantity,
        notes=notes or definition.notes,
        itemType=definition.itemType,
        slot=EquipmentSlot.CARRIED,
        armorCategory=definition.armorCategory,
        armorClass=definition.armorClass,
        armorClassBonus=definition.armorClassBonus,
    )


def equipment_item_id(equipment_id: EquipmentId, name: str | None = None) -> str:
    suffix = re.sub(r"[^a-zA-Z0-9]+", "-", (name or enum_key(equipment_id))).strip("-").lower()
    return suffix or enum_key(equipment_id)


def tool_equipment_item(tool_type: ToolType, *, quantity: int = 1) -> EquipmentItem:
    return EquipmentItem(
        id=enum_key(tool_type),
        name=enum_label(tool_type),
        quantity=quantity,
        itemType=EquipmentType.GEAR,
        slot=EquipmentSlot.CARRIED,
        notes="Tool from background equipment.",
    )


def weapon_definition(
    equipment_id: EquipmentId,
    training: WeaponTrainingCategory,
    category: WeaponCategory,
    damage_dice_count: int,
    damage_dice_type: DiceType,
    damage_type: DamageType,
    properties: tuple[WeaponProperty, ...],
    mastery: WeaponMastery,
    weight: float,
    cost: EquipmentCost,
    normal_range: int | None = None,
    long_range: int | None = None,
) -> EquipmentDefinition:
    return EquipmentDefinition(
        equipmentId=equipment_id,
        name=equipment_id.value,
        category=EquipmentCategory.WEAPON,
        cost=cost,
        weightLb=weight,
        weaponTraining=training,
        weaponCategory=category,
        attackRange=AttackRangeType.RANGED if category == WeaponCategory.RANGED else AttackRangeType.MELEE,
        damageDiceCount=damage_dice_count,
        damageDiceType=damage_dice_type,
        damageType=damage_type,
        properties=properties,
        normalRangeFeet=normal_range,
        longRangeFeet=long_range,
        mastery=mastery,
    )


def gear_definition(equipment_id: EquipmentId, weight: float, cost: EquipmentCost, notes: str = "", category: EquipmentCategory = EquipmentCategory.ADVENTURING_GEAR) -> EquipmentDefinition:
    return EquipmentDefinition(equipment_id, equipment_id.value, category, cost, weight, notes=notes)


EQUIPMENT_DEFINITIONS: dict[EquipmentId, EquipmentDefinition] = {
    EquipmentId.DAGGER: weapon_definition(EquipmentId.DAGGER, WeaponTrainingCategory.SIMPLE, WeaponCategory.MELEE, 1, DiceType.D4, DamageType.PIERCING, (WeaponProperty.FINESSE, WeaponProperty.LIGHT, WeaponProperty.THROWN), WeaponMastery.NICK, 1, cost_gp(2), 20, 60),
    EquipmentId.CLUB: weapon_definition(EquipmentId.CLUB, WeaponTrainingCategory.SIMPLE, WeaponCategory.MELEE, 1, DiceType.D4, DamageType.BLUDGEONING, (WeaponProperty.LIGHT,), WeaponMastery.SLOW, 2, cost_sp(1)),
    EquipmentId.GREATCLUB: weapon_definition(EquipmentId.GREATCLUB, WeaponTrainingCategory.SIMPLE, WeaponCategory.MELEE, 1, DiceType.D8, DamageType.BLUDGEONING, (WeaponProperty.TWO_HANDED,), WeaponMastery.PUSH, 10, cost_sp(2)),
    EquipmentId.JAVELIN: weapon_definition(EquipmentId.JAVELIN, WeaponTrainingCategory.SIMPLE, WeaponCategory.MELEE, 1, DiceType.D6, DamageType.PIERCING, (WeaponProperty.THROWN,), WeaponMastery.SLOW, 2, cost_sp(5), 30, 120),
    EquipmentId.LIGHT_CROSSBOW: weapon_definition(EquipmentId.LIGHT_CROSSBOW, WeaponTrainingCategory.SIMPLE, WeaponCategory.RANGED, 1, DiceType.D8, DamageType.PIERCING, (WeaponProperty.AMMUNITION, WeaponProperty.TWO_HANDED), WeaponMastery.SLOW, 5, cost_gp(25), 80, 320),
    EquipmentId.LIGHT_HAMMER: weapon_definition(EquipmentId.LIGHT_HAMMER, WeaponTrainingCategory.SIMPLE, WeaponCategory.MELEE, 1, DiceType.D4, DamageType.BLUDGEONING, (WeaponProperty.LIGHT, WeaponProperty.THROWN), WeaponMastery.NICK, 2, cost_gp(2), 20, 60),
    EquipmentId.MACE: weapon_definition(EquipmentId.MACE, WeaponTrainingCategory.SIMPLE, WeaponCategory.MELEE, 1, DiceType.D6, DamageType.BLUDGEONING, (), WeaponMastery.SAP, 4, cost_gp(5)),
    EquipmentId.QUARTERSTAFF: weapon_definition(EquipmentId.QUARTERSTAFF, WeaponTrainingCategory.SIMPLE, WeaponCategory.MELEE, 1, DiceType.D6, DamageType.BLUDGEONING, (WeaponProperty.VERSATILE,), WeaponMastery.TOPPLE, 4, cost_sp(2)),
    EquipmentId.SHORTBOW: weapon_definition(EquipmentId.SHORTBOW, WeaponTrainingCategory.SIMPLE, WeaponCategory.RANGED, 1, DiceType.D6, DamageType.PIERCING, (WeaponProperty.AMMUNITION, WeaponProperty.TWO_HANDED), WeaponMastery.VEX, 2, cost_gp(25), 80, 320),
    EquipmentId.SICKLE: weapon_definition(EquipmentId.SICKLE, WeaponTrainingCategory.SIMPLE, WeaponCategory.MELEE, 1, DiceType.D4, DamageType.SLASHING, (WeaponProperty.LIGHT,), WeaponMastery.NICK, 2, cost_gp(1)),
    EquipmentId.SPEAR: weapon_definition(EquipmentId.SPEAR, WeaponTrainingCategory.SIMPLE, WeaponCategory.MELEE, 1, DiceType.D6, DamageType.PIERCING, (WeaponProperty.THROWN, WeaponProperty.VERSATILE), WeaponMastery.SAP, 3, cost_gp(1), 20, 60),
    EquipmentId.ARCANE_FOCUS: gear_definition(EquipmentId.ARCANE_FOCUS, 0, VARIABLE_COST, category=EquipmentCategory.FOCUS),
    EquipmentId.ARROWS: gear_definition(EquipmentId.ARROWS, 1, cost_gp(1), "Ammunition for bows.", EquipmentCategory.AMMUNITION),
    EquipmentId.BOLTS: gear_definition(EquipmentId.BOLTS, 1.5, cost_gp(1), "Ammunition for crossbows.", EquipmentCategory.AMMUNITION),
    EquipmentId.BOOK: gear_definition(EquipmentId.BOOK, 5, cost_gp(25)),
    EquipmentId.BACKPACK: gear_definition(EquipmentId.BACKPACK, 5, cost_gp(2)),
    EquipmentId.BALL_BEARINGS: gear_definition(EquipmentId.BALL_BEARINGS, 2, cost_gp(1)),
    EquipmentId.BASKET: gear_definition(EquipmentId.BASKET, 2, cost_sp(4)),
    EquipmentId.BEDROLL: gear_definition(EquipmentId.BEDROLL, 7, cost_gp(1)),
    EquipmentId.BELL: gear_definition(EquipmentId.BELL, 0, cost_gp(1)),
    EquipmentId.BLANKET: gear_definition(EquipmentId.BLANKET, 3, cost_sp(5)),
    EquipmentId.BLOCK_AND_TACKLE: gear_definition(EquipmentId.BLOCK_AND_TACKLE, 5, cost_gp(1)),
    EquipmentId.BULLSEYE_LANTERN: gear_definition(EquipmentId.BULLSEYE_LANTERN, 2, cost_gp(10)),
    EquipmentId.BUCKET: gear_definition(EquipmentId.BUCKET, 2, cost_cp(5)),
    EquipmentId.CALTROPS: gear_definition(EquipmentId.CALTROPS, 2, cost_gp(1)),
    EquipmentId.CANDLES: gear_definition(EquipmentId.CANDLES, 0, cost_cp(1)),
    EquipmentId.CHAIN: gear_definition(EquipmentId.CHAIN, 10, cost_gp(5)),
    EquipmentId.CLIMBERS_KIT: gear_definition(EquipmentId.CLIMBERS_KIT, 12, cost_gp(25)),
    EquipmentId.COSTUME: gear_definition(EquipmentId.COSTUME, 4, cost_gp(5), category=EquipmentCategory.CLOTHING),
    EquipmentId.CROWBAR: gear_definition(EquipmentId.CROWBAR, 5, cost_gp(2)),
    EquipmentId.FINE_CLOTHES: gear_definition(EquipmentId.FINE_CLOTHES, 6, cost_gp(15), category=EquipmentCategory.CLOTHING),
    EquipmentId.GAMING_SET: gear_definition(EquipmentId.GAMING_SET, 0, VARIABLE_COST, category=EquipmentCategory.TOOL),
    EquipmentId.GLASS_BOTTLE: gear_definition(EquipmentId.GLASS_BOTTLE, 2, cost_gp(2)),
    EquipmentId.GRAPPLING_HOOK: gear_definition(EquipmentId.GRAPPLING_HOOK, 4, cost_gp(2)),
    EquipmentId.HEALERS_KIT: gear_definition(EquipmentId.HEALERS_KIT, 3, cost_gp(5)),
    EquipmentId.HOLY_SYMBOL: gear_definition(EquipmentId.HOLY_SYMBOL, 0, cost_gp(5), category=EquipmentCategory.FOCUS),
    EquipmentId.HOLY_WATER: gear_definition(EquipmentId.HOLY_WATER, 1, cost_gp(25)),
    EquipmentId.HOODED_LANTERN: gear_definition(EquipmentId.HOODED_LANTERN, 2, cost_gp(5)),
    EquipmentId.HUNTING_TRAP: gear_definition(EquipmentId.HUNTING_TRAP, 25, cost_gp(5)),
    EquipmentId.INK: gear_definition(EquipmentId.INK, 0, cost_gp(10)),
    EquipmentId.INK_PEN: gear_definition(EquipmentId.INK_PEN, 0, cost_cp(2)),
    EquipmentId.IRON_POT: gear_definition(EquipmentId.IRON_POT, 10, cost_gp(2)),
    EquipmentId.IRON_SPIKES: gear_definition(EquipmentId.IRON_SPIKES, 5, cost_gp(1)),
    EquipmentId.LADDER: gear_definition(EquipmentId.LADDER, 25, cost_sp(1)),
    EquipmentId.LAMP: gear_definition(EquipmentId.LAMP, 1, cost_sp(5)),
    EquipmentId.MANACLES: gear_definition(EquipmentId.MANACLES, 6, cost_gp(2)),
    EquipmentId.MAP: gear_definition(EquipmentId.MAP, 0, cost_gp(1)),
    EquipmentId.MAP_OR_SCROLL_CASE: gear_definition(EquipmentId.MAP_OR_SCROLL_CASE, 1, cost_gp(1)),
    EquipmentId.MIRROR: gear_definition(EquipmentId.MIRROR, 0.5, cost_gp(5)),
    EquipmentId.MUSICAL_INSTRUMENT: gear_definition(EquipmentId.MUSICAL_INSTRUMENT, 0, VARIABLE_COST, category=EquipmentCategory.TOOL),
    EquipmentId.NET: gear_definition(EquipmentId.NET, 3, cost_gp(1)),
    EquipmentId.OIL: gear_definition(EquipmentId.OIL, 1, cost_sp(1)),
    EquipmentId.PAPER: gear_definition(EquipmentId.PAPER, 0, cost_sp(2)),
    EquipmentId.PARCHMENT: gear_definition(EquipmentId.PARCHMENT, 0, cost_sp(1)),
    EquipmentId.PERFUME: gear_definition(EquipmentId.PERFUME, 0, cost_gp(5)),
    EquipmentId.POLE: gear_definition(EquipmentId.POLE, 7, cost_cp(5)),
    EquipmentId.PORTABLE_RAM: gear_definition(EquipmentId.PORTABLE_RAM, 35, cost_gp(4)),
    EquipmentId.POUCH: gear_definition(EquipmentId.POUCH, 1, cost_sp(5)),
    EquipmentId.QUIVER: gear_definition(EquipmentId.QUIVER, 1, cost_gp(1)),
    EquipmentId.RATIONS: gear_definition(EquipmentId.RATIONS, 2, cost_sp(5)),
    EquipmentId.ROBE: gear_definition(EquipmentId.ROBE, 4, cost_gp(1), category=EquipmentCategory.CLOTHING),
    EquipmentId.ROPE: gear_definition(EquipmentId.ROPE, 5, cost_gp(1)),
    EquipmentId.SHOVEL: gear_definition(EquipmentId.SHOVEL, 5, cost_gp(2)),
    EquipmentId.SIGNAL_WHISTLE: gear_definition(EquipmentId.SIGNAL_WHISTLE, 0, cost_cp(5)),
    EquipmentId.STRING: gear_definition(EquipmentId.STRING, 0, cost_sp(1)),
    EquipmentId.TENT: gear_definition(EquipmentId.TENT, 20, cost_gp(2)),
    EquipmentId.TINDERBOX: gear_definition(EquipmentId.TINDERBOX, 1, cost_sp(5)),
    EquipmentId.TORCHES: gear_definition(EquipmentId.TORCHES, 1, cost_cp(1)),
    EquipmentId.TRAVELERS_CLOTHES: gear_definition(EquipmentId.TRAVELERS_CLOTHES, 4, cost_gp(2), category=EquipmentCategory.CLOTHING),
    EquipmentId.VIAL: gear_definition(EquipmentId.VIAL, 0, cost_gp(1)),
    EquipmentId.WATERSKIN: gear_definition(EquipmentId.WATERSKIN, 5, cost_sp(2)),
}
