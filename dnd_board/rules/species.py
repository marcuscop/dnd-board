from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from dnd_board.character_sheet import DamageType, SheetFeature, TimeEconomy, enum_key, enum_label


class SpeciesType(Enum):
    AASIMAR = "Aasimar"
    DRAGONBORN = "Dragonborn"
    DWARF = "Dwarf"
    ELF = "Elf"
    GNOME = "Gnome"
    GOLIATH = "Goliath"
    HALFLING = "Halfling"
    HUMAN = "Human"
    ORC = "Orc"
    TIEFLING = "Tiefling"
    CHANGELING = "Changeling"
    KALASHTAR = "Kalashtar"
    KHORAVAR = "Khoravar"
    SHIFTER = "Shifter"
    WARFORGED = "Warforged"
    BOGGART = "Boggart"
    FAERIE = "Faerie"
    FLAMEKIN = "Flamekin"
    LORWYN_CHANGELING = "Lorwyn Changeling"
    RIMEKIN = "Rimekin"
    DHAMPIR = "Dhampir"
    HEXBLOOD = "Hexblood"
    LUPIN = "Lupin"
    REBORN = "Reborn"


class SpeciesSource(Enum):
    COMMON = "Common"
    EBERRON = "Eberron"
    LORWYN = "Lorwyn"
    RAVENLOFT = "Ravenloft"
    EXOTIC = "Exotic"


class SpeciesTraitType(Enum):
    ADRENALINE_RUSH = "Adrenaline Rush"
    BRAVE = "Brave"
    BREATH_WEAPON = "Breath Weapon"
    CELESTIAL_RESISTANCE = "Celestial Resistance"
    CELESTIAL_REVELATION = "Celestial Revelation"
    DAMAGE_RESISTANCE = "Damage Resistance"
    DARKVISION = "Darkvision"
    DRACONIC_ANCESTRY = "Draconic Ancestry"
    DRACONIC_FLIGHT = "Draconic Flight"
    DWARVEN_RESILIENCE = "Dwarven Resilience"
    DWARVEN_TOUGHNESS = "Dwarven Toughness"
    ELVEN_LINEAGE = "Elven Lineage"
    FEY_ANCESTRY = "Fey Ancestry"
    FIENDISH_LEGACY = "Fiendish Legacy"
    GIANT_ANCESTRY = "Giant Ancestry"
    GNOMISH_CUNNING = "Gnomish Cunning"
    GNOMISH_LINEAGE = "Gnomish Lineage"
    HALFLING_NIMBLENESS = "Halfling Nimbleness"
    HEALING_HANDS = "Healing Hands"
    LARGE_FORM = "Large Form"
    LIGHT_BEARER = "Light Bearer"
    LUCK = "Luck"
    NATURALLY_STEALTHY = "Naturally Stealthy"
    OTHERWORLDLY_PRESENCE = "Otherworldly Presence"
    POWERFUL_BUILD = "Powerful Build"
    RELENTLESS_ENDURANCE = "Relentless Endurance"
    RESOURCEFUL = "Resourceful"
    SKILLFUL = "Skillful"
    SPECIES_TRAITS = "Species Traits"
    STONECUNNING = "Stonecunning"
    TRANCE = "Trance"
    VERSATILE = "Versatile"


@dataclass(frozen=True)
class SpeciesTraitDefinition:
    traitType: SpeciesTraitType
    description: str
    activation: TimeEconomy = TimeEconomy.PASSIVE


@dataclass(frozen=True)
class SpeciesDefinition:
    speciesType: SpeciesType
    source: SpeciesSource
    speed: int = 30
    damageResistances: tuple[DamageType, ...] = ()
    traits: tuple[SpeciesTraitDefinition, ...] = ()
    hitPointBonusPerLevel: int = 0


def species_definition(species_type: SpeciesType) -> SpeciesDefinition:
    return SPECIES_DEFINITIONS[species_type]


def species_label(species_type: SpeciesType) -> str:
    return enum_label(species_type)


def species_traits(species_type: SpeciesType) -> list[SheetFeature]:
    definition = species_definition(species_type)
    return [
        SheetFeature(
            id=f"{enum_key(species_type)}{enum_key(trait.traitType)}",
            name=enum_label(trait.traitType),
            source=enum_label(species_type),
            activation=trait.activation,
            description=trait.description,
        )
        for trait in definition.traits
    ]


def species_hit_point_bonus(species_type: SpeciesType, level: int) -> int:
    return species_definition(species_type).hitPointBonusPerLevel * level


COMMON_SPECIES_DEFINITIONS: dict[SpeciesType, SpeciesDefinition] = {
    SpeciesType.AASIMAR: SpeciesDefinition(
        SpeciesType.AASIMAR,
        SpeciesSource.COMMON,
        damageResistances=(DamageType.NECROTIC, DamageType.RADIANT),
        traits=(
            SpeciesTraitDefinition(SpeciesTraitType.CELESTIAL_RESISTANCE, "You have resistance to Necrotic damage and Radiant damage."),
            SpeciesTraitDefinition(SpeciesTraitType.DARKVISION, "You have Darkvision with a range of 60 feet."),
            SpeciesTraitDefinition(SpeciesTraitType.HEALING_HANDS, "As a Magic action, heal a creature for d4s equal to your Proficiency Bonus once per Long Rest.", TimeEconomy.ACTION),
            SpeciesTraitDefinition(SpeciesTraitType.LIGHT_BEARER, "You know the Light cantrip. Charisma is your spellcasting ability for it."),
            SpeciesTraitDefinition(SpeciesTraitType.CELESTIAL_REVELATION, "At character level 3, transform as a Bonus Action once per Long Rest. Choose Heavenly Wings, Inner Radiance, or Necrotic Shroud each time.", TimeEconomy.BONUS_ACTION),
        ),
    ),
    SpeciesType.DRAGONBORN: SpeciesDefinition(
        SpeciesType.DRAGONBORN,
        SpeciesSource.COMMON,
        traits=(
            SpeciesTraitDefinition(SpeciesTraitType.DRACONIC_ANCESTRY, "Choose a draconic damage type for your Breath Weapon and resistance."),
            SpeciesTraitDefinition(SpeciesTraitType.BREATH_WEAPON, "Use an action to exhale destructive energy. Uses and damage scale by character level.", TimeEconomy.ACTION),
            SpeciesTraitDefinition(SpeciesTraitType.DAMAGE_RESISTANCE, "Gain resistance to the damage type chosen for Draconic Ancestry."),
            SpeciesTraitDefinition(SpeciesTraitType.DARKVISION, "You have Darkvision with a range of 60 feet."),
            SpeciesTraitDefinition(SpeciesTraitType.DRACONIC_FLIGHT, "At character level 5, sprout spectral wings and gain a Fly Speed for 10 minutes once per Long Rest.", TimeEconomy.BONUS_ACTION),
        ),
    ),
    SpeciesType.DWARF: SpeciesDefinition(
        SpeciesType.DWARF,
        SpeciesSource.COMMON,
        damageResistances=(DamageType.POISON,),
        traits=(
            SpeciesTraitDefinition(SpeciesTraitType.DARKVISION, "You have Darkvision with a range of 120 feet."),
            SpeciesTraitDefinition(SpeciesTraitType.DWARVEN_RESILIENCE, "You have resistance to Poison damage and advantage on saving throws to avoid or end the Poisoned condition."),
            SpeciesTraitDefinition(SpeciesTraitType.DWARVEN_TOUGHNESS, "Your Hit Point maximum increases by 1, and it increases by 1 again whenever you gain a level."),
            SpeciesTraitDefinition(SpeciesTraitType.STONECUNNING, "As a Bonus Action, gain Tremorsense with a range of 60 feet for 10 minutes. You can use this a number of times equal to your Proficiency Bonus per Long Rest.", TimeEconomy.BONUS_ACTION),
        ),
        hitPointBonusPerLevel=1,
    ),
    SpeciesType.ELF: SpeciesDefinition(
        SpeciesType.ELF,
        SpeciesSource.COMMON,
        traits=(
            SpeciesTraitDefinition(SpeciesTraitType.DARKVISION, "You have Darkvision with a range of 60 feet."),
            SpeciesTraitDefinition(SpeciesTraitType.ELVEN_LINEAGE, "Choose Drow, High Elf, or Wood Elf for lineage spells and traits."),
            SpeciesTraitDefinition(SpeciesTraitType.FEY_ANCESTRY, "You have advantage on saving throws you make to avoid or end the Charmed condition."),
            SpeciesTraitDefinition(SpeciesTraitType.TRANCE, "You do not need to sleep and can finish a Long Rest in 4 hours if you spend them in a trance."),
        ),
    ),
    SpeciesType.GNOME: SpeciesDefinition(
        SpeciesType.GNOME,
        SpeciesSource.COMMON,
        traits=(
            SpeciesTraitDefinition(SpeciesTraitType.DARKVISION, "You have Darkvision with a range of 60 feet."),
            SpeciesTraitDefinition(SpeciesTraitType.GNOMISH_CUNNING, "You have advantage on Intelligence, Wisdom, and Charisma saving throws."),
            SpeciesTraitDefinition(SpeciesTraitType.GNOMISH_LINEAGE, "Choose Forest Gnome or Rock Gnome for additional magical traits."),
        ),
    ),
    SpeciesType.GOLIATH: SpeciesDefinition(
        SpeciesType.GOLIATH,
        SpeciesSource.COMMON,
        speed=35,
        traits=(
            SpeciesTraitDefinition(SpeciesTraitType.GIANT_ANCESTRY, "Choose a giant ancestry benefit when you select this species."),
            SpeciesTraitDefinition(SpeciesTraitType.LARGE_FORM, "As a Bonus Action, become Large for 10 minutes once per Long Rest.", TimeEconomy.BONUS_ACTION),
            SpeciesTraitDefinition(SpeciesTraitType.POWERFUL_BUILD, "You have advantage on ability checks to end the Grappled condition, and your carrying capacity increases."),
        ),
    ),
    SpeciesType.HALFLING: SpeciesDefinition(
        SpeciesType.HALFLING,
        SpeciesSource.COMMON,
        traits=(
            SpeciesTraitDefinition(SpeciesTraitType.BRAVE, "You have advantage on saving throws you make to avoid or end the Frightened condition."),
            SpeciesTraitDefinition(SpeciesTraitType.HALFLING_NIMBLENESS, "You can move through the space of any creature that is a size larger than you."),
            SpeciesTraitDefinition(SpeciesTraitType.LUCK, "When you roll a 1 on the d20 of a D20 Test, you can reroll the die and must use the new roll."),
            SpeciesTraitDefinition(SpeciesTraitType.NATURALLY_STEALTHY, "You can take the Hide action even when obscured only by a creature at least one size larger than you."),
        ),
    ),
    SpeciesType.HUMAN: SpeciesDefinition(
        SpeciesType.HUMAN,
        SpeciesSource.COMMON,
        traits=(
            SpeciesTraitDefinition(SpeciesTraitType.RESOURCEFUL, "You gain Heroic Inspiration whenever you finish a Long Rest."),
            SpeciesTraitDefinition(SpeciesTraitType.SKILLFUL, "You gain proficiency in one skill of your choice."),
            SpeciesTraitDefinition(SpeciesTraitType.VERSATILE, "You gain an Origin feat of your choice."),
        ),
    ),
    SpeciesType.ORC: SpeciesDefinition(
        SpeciesType.ORC,
        SpeciesSource.COMMON,
        traits=(
            SpeciesTraitDefinition(SpeciesTraitType.ADRENALINE_RUSH, "As a Bonus Action, Dash and gain Temporary Hit Points. Uses refresh on a Short or Long Rest.", TimeEconomy.BONUS_ACTION),
            SpeciesTraitDefinition(SpeciesTraitType.DARKVISION, "You have Darkvision with a range of 120 feet."),
            SpeciesTraitDefinition(SpeciesTraitType.RELENTLESS_ENDURANCE, "When reduced to 0 Hit Points but not killed outright, drop to 1 Hit Point instead once per Long Rest."),
        ),
    ),
    SpeciesType.TIEFLING: SpeciesDefinition(
        SpeciesType.TIEFLING,
        SpeciesSource.COMMON,
        traits=(
            SpeciesTraitDefinition(SpeciesTraitType.DARKVISION, "You have Darkvision with a range of 60 feet."),
            SpeciesTraitDefinition(SpeciesTraitType.FIENDISH_LEGACY, "Choose Abyssal, Chthonic, or Infernal for resistance and spells."),
            SpeciesTraitDefinition(SpeciesTraitType.OTHERWORLDLY_PRESENCE, "You know the Thaumaturgy cantrip. Charisma is your spellcasting ability for it."),
        ),
    ),
}

SPECIES_SOURCES: dict[SpeciesSource, tuple[SpeciesType, ...]] = {
    SpeciesSource.EBERRON: (SpeciesType.CHANGELING, SpeciesType.KALASHTAR, SpeciesType.KHORAVAR, SpeciesType.SHIFTER, SpeciesType.WARFORGED),
    SpeciesSource.LORWYN: (SpeciesType.BOGGART, SpeciesType.FAERIE, SpeciesType.FLAMEKIN, SpeciesType.LORWYN_CHANGELING, SpeciesType.RIMEKIN),
    SpeciesSource.RAVENLOFT: (SpeciesType.DHAMPIR, SpeciesType.HEXBLOOD, SpeciesType.LUPIN, SpeciesType.REBORN),
}

SPECIES_DEFINITIONS: dict[SpeciesType, SpeciesDefinition] = {
    **COMMON_SPECIES_DEFINITIONS,
    **{
        species_type: SpeciesDefinition(
            species_type,
            source,
            traits=(SpeciesTraitDefinition(SpeciesTraitType.SPECIES_TRAITS, "Detailed species mechanics are not implemented yet."),),
        )
        for source, species_types in SPECIES_SOURCES.items()
        for species_type in species_types
        if species_type not in COMMON_SPECIES_DEFINITIONS
    },
}
