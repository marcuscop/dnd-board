from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from dnd_board.character_sheet import CharacterClassLevel, ClassType, ResourceTracker, RestType, SheetAbility, SheetFeature, TimeEconomy, enum_key, enum_label
from dnd_board.rules.classes.wizard.base import WizardSubclassType, wizard_class, wizard_subclass_label


class WizardSubclassFeatureType(Enum):
    SAVANT = auto()
    ARCANE_WARD = auto()
    PROJECTED_WARD = auto()
    SPELL_BREAKER = auto()
    SPELL_RESISTANCE = auto()
    PORTENT = auto()
    EXPERT_DIVINATION = auto()
    THE_THIRD_EYE = auto()
    GREATER_PORTENT = auto()
    EVOCATION_SAVANT = auto()
    POTENT_CANTRIP = auto()
    SCULPT_SPELLS = auto()
    EMPOWERED_EVOCATION = auto()
    OVERCHANNEL = auto()
    ILLUSION_SAVANT = auto()
    IMPROVED_ILLUSIONS = auto()
    PHANTASMAL_CREATURES = auto()
    ILLUSORY_SELF = auto()
    ILLUSORY_REALITY = auto()
    BLADESONG = auto()
    EXTRA_ATTACK = auto()
    SONG_OF_DEFENSE = auto()
    SONG_OF_VICTORY = auto()
    LEGACY_SUBCLASS_FEATURE = auto()


class WizardSubclassResourceType(Enum):
    ARCANE_WARD = auto()
    PORTENT = auto()
    GREATER_PORTENT = auto()
    BLADESONG = auto()
    ILLUSORY_SELF = auto()


@dataclass(frozen=True)
class WizardSubclassFeatureProgression:
    subclass: WizardSubclassType
    feature: WizardSubclassFeatureType
    level: int
    activation: TimeEconomy
    description: str


WIZARD_SUBCLASS_FEATURES: tuple[WizardSubclassFeatureProgression, ...] = (
    WizardSubclassFeatureProgression(WizardSubclassType.ABJURER, WizardSubclassFeatureType.SAVANT, 3, TimeEconomy.PASSIVE, "Choose two Wizard Abjuration spells of level 2 or lower to add to your spellbook for free; future Abjuration spell copying is faster and cheaper."),
    WizardSubclassFeatureProgression(WizardSubclassType.ABJURER, WizardSubclassFeatureType.ARCANE_WARD, 3, TimeEconomy.SPECIAL, "When you cast an Abjuration spell with a spell slot, create or restore an Arcane Ward that absorbs damage."),
    WizardSubclassFeatureProgression(WizardSubclassType.ABJURER, WizardSubclassFeatureType.PROJECTED_WARD, 6, TimeEconomy.REACTION, "When a creature you can see within 30 feet takes damage, your Arcane Ward can absorb that damage."),
    WizardSubclassFeatureProgression(WizardSubclassType.ABJURER, WizardSubclassFeatureType.SPELL_BREAKER, 10, TimeEconomy.PASSIVE, "Counterspell and Dispel Magic are always prepared; add them to your spellbook if needed."),
    WizardSubclassFeatureProgression(WizardSubclassType.ABJURER, WizardSubclassFeatureType.SPELL_RESISTANCE, 14, TimeEconomy.PASSIVE, "You have Advantage on saving throws against spells and Resistance to spell damage."),
    WizardSubclassFeatureProgression(WizardSubclassType.DIVINER, WizardSubclassFeatureType.SAVANT, 3, TimeEconomy.PASSIVE, "Choose two Wizard Divination spells of level 2 or lower to add to your spellbook for free; future Divination spell copying is faster and cheaper."),
    WizardSubclassFeatureProgression(WizardSubclassType.DIVINER, WizardSubclassFeatureType.PORTENT, 3, TimeEconomy.SPECIAL, "After finishing a Long Rest, roll two d20s and replace attack rolls, saving throws, or ability checks you can see with those rolls."),
    WizardSubclassFeatureProgression(WizardSubclassType.DIVINER, WizardSubclassFeatureType.EXPERT_DIVINATION, 6, TimeEconomy.SPECIAL, "When you cast a Divination spell with a spell slot, regain one expended lower-level spell slot."),
    WizardSubclassFeatureProgression(WizardSubclassType.DIVINER, WizardSubclassFeatureType.THE_THIRD_EYE, 10, TimeEconomy.BONUS_ACTION, "Gain one special sense until a Short or Long Rest: Darkvision, See Invisibility, or another divinatory perception option."),
    WizardSubclassFeatureProgression(WizardSubclassType.DIVINER, WizardSubclassFeatureType.GREATER_PORTENT, 14, TimeEconomy.SPECIAL, "Roll three Portent dice after a Long Rest instead of two."),
    WizardSubclassFeatureProgression(WizardSubclassType.EVOKER, WizardSubclassFeatureType.EVOCATION_SAVANT, 3, TimeEconomy.PASSIVE, "Choose two Wizard Evocation spells of level 2 or lower to add to your spellbook for free; future Evocation spell copying is faster and cheaper."),
    WizardSubclassFeatureProgression(WizardSubclassType.EVOKER, WizardSubclassFeatureType.POTENT_CANTRIP, 3, TimeEconomy.PASSIVE, "Your damaging cantrips affect creatures even when the creature avoids the brunt of the effect."),
    WizardSubclassFeatureProgression(WizardSubclassType.EVOKER, WizardSubclassFeatureType.SCULPT_SPELLS, 6, TimeEconomy.SPECIAL, "Protect chosen creatures from your Evocation spells' areas of effect."),
    WizardSubclassFeatureProgression(WizardSubclassType.EVOKER, WizardSubclassFeatureType.EMPOWERED_EVOCATION, 10, TimeEconomy.PASSIVE, "Add your Intelligence modifier to one damage roll of Wizard Evocation spells you cast."),
    WizardSubclassFeatureProgression(WizardSubclassType.EVOKER, WizardSubclassFeatureType.OVERCHANNEL, 14, TimeEconomy.SPECIAL, "Maximize damage for a Wizard spell of level 1-5 that deals damage, with harm to yourself on repeated uses before a Long Rest."),
    WizardSubclassFeatureProgression(WizardSubclassType.ILLUSIONIST, WizardSubclassFeatureType.ILLUSION_SAVANT, 3, TimeEconomy.PASSIVE, "Choose two Wizard Illusion spells of level 2 or lower to add to your spellbook for free; future Illusion spell copying is faster and cheaper."),
    WizardSubclassFeatureProgression(WizardSubclassType.ILLUSIONIST, WizardSubclassFeatureType.IMPROVED_ILLUSIONS, 3, TimeEconomy.PASSIVE, "Gain improved Minor Illusion and enhanced Illusion spell use."),
    WizardSubclassFeatureProgression(WizardSubclassType.ILLUSIONIST, WizardSubclassFeatureType.PHANTASMAL_CREATURES, 6, TimeEconomy.SPECIAL, "Summon Beast and Summon Fey are always prepared and can appear illusionary."),
    WizardSubclassFeatureProgression(WizardSubclassType.ILLUSIONIST, WizardSubclassFeatureType.ILLUSORY_SELF, 10, TimeEconomy.REACTION, "When hit by an attack, interpose an illusory duplicate that can turn the attack into a miss."),
    WizardSubclassFeatureProgression(WizardSubclassType.ILLUSIONIST, WizardSubclassFeatureType.ILLUSORY_REALITY, 14, TimeEconomy.BONUS_ACTION, "Make part of an Illusion spell real for a limited time."),
    WizardSubclassFeatureProgression(WizardSubclassType.BLADESINGER, WizardSubclassFeatureType.BLADESONG, 3, TimeEconomy.BONUS_ACTION, "Start a Bladesong to gain combat benefits while not wearing medium/heavy armor or using a shield."),
    WizardSubclassFeatureProgression(WizardSubclassType.BLADESINGER, WizardSubclassFeatureType.EXTRA_ATTACK, 6, TimeEconomy.PASSIVE, "Attack twice instead of once when you take the Attack action, and replace one attack with a cantrip."),
    WizardSubclassFeatureProgression(WizardSubclassType.BLADESINGER, WizardSubclassFeatureType.SONG_OF_DEFENSE, 10, TimeEconomy.REACTION, "Expend a spell slot to reduce damage while Bladesong is active."),
    WizardSubclassFeatureProgression(WizardSubclassType.BLADESINGER, WizardSubclassFeatureType.SONG_OF_VICTORY, 14, TimeEconomy.PASSIVE, "Add your Intelligence modifier to melee weapon damage while Bladesong is active."),
)


LEGACY_SUBCLASS_DESCRIPTIONS: dict[WizardSubclassType, str] = {
    WizardSubclassType.CHRONURGY: "Legacy Chronurgy magic features are included as descriptive features; deeper time manipulation mechanics will be modeled in a later pass.",
    WizardSubclassType.CONJURATION: "Legacy Conjuration features are included as descriptive features; object creation and teleport details remain manual.",
    WizardSubclassType.ENCHANTMENT: "Legacy Enchantment features are included as descriptive features; charm and memory-alteration mechanics remain manual.",
    WizardSubclassType.GRAVITURGY: "Legacy Graviturgy features are included as descriptive features; gravity manipulation effects remain manual.",
    WizardSubclassType.NECROMANCY: "Legacy Necromancy features are included as descriptive features; undead-control details remain manual.",
    WizardSubclassType.ORDER_OF_SCRIBES: "Legacy Order of Scribes features are included as descriptive features; awakened spellbook mechanics remain manual.",
    WizardSubclassType.TRANSMUTATION: "Legacy Transmutation features are included as descriptive features; transmuter's stone choices remain manual.",
    WizardSubclassType.WAR_MAGIC: "Legacy War Magic features are included as descriptive features; tactical reaction and power surge details remain manual.",
    WizardSubclassType.RUNECRAFTER: "UA Runecrafter features are included as descriptive features.",
    WizardSubclassType.INVENTION: "UA Invention features are included as descriptive features.",
    WizardSubclassType.LORE_MASTERY: "UA Lore Mastery features are included as descriptive features.",
    WizardSubclassType.MAGE_OF_LOREHOLD: "UA Mage of Lorehold features are included as descriptive features.",
    WizardSubclassType.MAGE_OF_PRISMARI: "UA Mage of Prismari features are included as descriptive features.",
    WizardSubclassType.MAGE_OF_QUANDRIX: "UA Mage of Quandrix features are included as descriptive features.",
    WizardSubclassType.MAGE_OF_SILVERQUILL: "UA Mage of Silverquill features are included as descriptive features.",
    WizardSubclassType.ONOMANCY: "UA Onomancy features are included as descriptive features.",
    WizardSubclassType.ORDER_OF_SCRIBES_UA: "UA Order of Scribes features are included as descriptive features.",
    WizardSubclassType.PSIONICS: "UA Psionics features are included as descriptive features.",
    WizardSubclassType.TECHNOMANCY: "UA Technomancy features are included as descriptive features.",
    WizardSubclassType.THEURGY: "UA Theurgy features are included as descriptive features.",
}


def wizard_subclass_features(subclass: Enum | None, wizard_level: int) -> list[SheetFeature]:
    if not isinstance(subclass, WizardSubclassType):
        return []
    progressions = [
        progression
        for progression in WIZARD_SUBCLASS_FEATURES
        if progression.subclass == subclass and wizard_level >= progression.level
    ]
    features = [
        SheetFeature(
            id=f"{enum_key(progression.subclass)}{enum_label(progression.feature).replace(' ', '')}",
            name=enum_label(progression.feature),
            source=wizard_subclass_label(progression.subclass),
            activation=progression.activation,
            description=progression.description,
        )
        for progression in progressions
    ]
    if not features and subclass in LEGACY_SUBCLASS_DESCRIPTIONS and wizard_level >= 3:
        features.append(SheetFeature(
            id=f"{enum_key(subclass)}LegacySubclassFeature",
            name=wizard_subclass_label(subclass),
            source=wizard_subclass_label(subclass),
            activation=TimeEconomy.PASSIVE,
            description=LEGACY_SUBCLASS_DESCRIPTIONS[subclass],
        ))
    return features


def wizard_subclass_resources(classes: list[CharacterClassLevel]) -> list[ResourceTracker]:
    character_class = wizard_class(classes)
    if character_class is None or not isinstance(character_class.subclass, WizardSubclassType):
        return []
    subclass = character_class.subclass
    level = character_class.level
    resources: list[ResourceTracker] = []
    if subclass == WizardSubclassType.DIVINER and level >= 3:
        resource_type = WizardSubclassResourceType.GREATER_PORTENT if level >= 14 else WizardSubclassResourceType.PORTENT
        uses = 3 if level >= 14 else 2
        resources.append(ResourceTracker(enum_key(resource_type), enum_label(resource_type), uses, uses, RestType.LONG_REST, TimeEconomy.SPECIAL, "Rolled Portent dice available after a Long Rest.", source=wizard_subclass_label(subclass)))
    if subclass == WizardSubclassType.BLADESINGER and level >= 3:
        resources.append(ResourceTracker(enum_key(WizardSubclassResourceType.BLADESONG), enum_label(WizardSubclassResourceType.BLADESONG), 2, 2, RestType.LONG_REST, TimeEconomy.BONUS_ACTION, "Start Bladesong.", source=wizard_subclass_label(subclass)))
    if subclass == WizardSubclassType.ILLUSIONIST and level >= 10:
        resources.append(ResourceTracker(enum_key(WizardSubclassResourceType.ILLUSORY_SELF), enum_label(WizardSubclassResourceType.ILLUSORY_SELF), 1, 1, RestType.SHORT_REST, TimeEconomy.REACTION, "Use Illusory Self to avoid an attack.", source=wizard_subclass_label(subclass)))
    return resources


def wizard_subclass_abilities(classes: list[CharacterClassLevel]) -> list[SheetAbility]:
    return []
