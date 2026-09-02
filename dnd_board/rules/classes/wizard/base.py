from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from dnd_board.character_sheet import (
    AbilityType,
    CharacterClassLevel,
    ClassType,
    ResourceTracker,
    RestType,
    SheetFeature,
    SpellEntry,
    SpellId,
    SpellSource,
    TimeEconomy,
    enum_key,
    enum_label,
)
from dnd_board.rules.sources import RuleSource, rule_source_label
from dnd_board.rules.spells import SpellListType, spell_entries_for_list, spell_entry_for_list


class WizardFeatureType(Enum):
    SPELLCASTING = auto()
    RITUAL_ADEPT = auto()
    ARCANE_RECOVERY = auto()
    SCHOLAR = auto()
    WIZARD_SUBCLASS = auto()
    ABILITY_SCORE_IMPROVEMENT = auto()
    MEMORIZE_SPELL = auto()
    SUBCLASS_FEATURE = auto()
    SPELL_MASTERY = auto()
    EPIC_BOON = auto()
    SIGNATURE_SPELLS = auto()


class WizardResourceType(Enum):
    ARCANE_RECOVERY = auto()
    FIRST_LEVEL_SPELL_SLOTS = auto()
    SECOND_LEVEL_SPELL_SLOTS = auto()
    THIRD_LEVEL_SPELL_SLOTS = auto()
    FOURTH_LEVEL_SPELL_SLOTS = auto()
    FIFTH_LEVEL_SPELL_SLOTS = auto()
    SIXTH_LEVEL_SPELL_SLOTS = auto()
    SEVENTH_LEVEL_SPELL_SLOTS = auto()
    EIGHTH_LEVEL_SPELL_SLOTS = auto()
    NINTH_LEVEL_SPELL_SLOTS = auto()


class WizardSubclassType(Enum):
    ABJURER = auto()
    DIVINER = auto()
    EVOKER = auto()
    ILLUSIONIST = auto()
    BLADESINGER = auto()
    CHRONURGY = auto()
    CONJURATION = auto()
    ENCHANTMENT = auto()
    GRAVITURGY = auto()
    NECROMANCY = auto()
    ORDER_OF_SCRIBES = auto()
    TRANSMUTATION = auto()
    WAR_MAGIC = auto()
    RUNECRAFTER = auto()
    INVENTION = auto()
    LORE_MASTERY = auto()
    MAGE_OF_LOREHOLD = auto()
    MAGE_OF_PRISMARI = auto()
    MAGE_OF_QUANDRIX = auto()
    MAGE_OF_SILVERQUILL = auto()
    ONOMANCY = auto()
    ORDER_OF_SCRIBES_UA = auto()
    PSIONICS = auto()
    TECHNOMANCY = auto()
    THEURGY = auto()


WIZARD_SUBCLASS_SOURCES: dict[WizardSubclassType, RuleSource] = {
    WizardSubclassType.ABJURER: RuleSource.PLAYERS_HANDBOOK_2024,
    WizardSubclassType.DIVINER: RuleSource.PLAYERS_HANDBOOK_2024,
    WizardSubclassType.EVOKER: RuleSource.PLAYERS_HANDBOOK_2024,
    WizardSubclassType.ILLUSIONIST: RuleSource.PLAYERS_HANDBOOK_2024,
    WizardSubclassType.BLADESINGER: RuleSource.FORGOTTEN_REALMS_HEROES_OF_FAERUN_2024,
    WizardSubclassType.CHRONURGY: RuleSource.LEGACY,
    WizardSubclassType.CONJURATION: RuleSource.LEGACY,
    WizardSubclassType.ENCHANTMENT: RuleSource.LEGACY,
    WizardSubclassType.GRAVITURGY: RuleSource.LEGACY,
    WizardSubclassType.NECROMANCY: RuleSource.LEGACY,
    WizardSubclassType.ORDER_OF_SCRIBES: RuleSource.LEGACY,
    WizardSubclassType.TRANSMUTATION: RuleSource.LEGACY,
    WizardSubclassType.WAR_MAGIC: RuleSource.LEGACY,
    WizardSubclassType.RUNECRAFTER: RuleSource.UNEARTHED_ARCANA,
    WizardSubclassType.INVENTION: RuleSource.UNEARTHED_ARCANA,
    WizardSubclassType.LORE_MASTERY: RuleSource.UNEARTHED_ARCANA,
    WizardSubclassType.MAGE_OF_LOREHOLD: RuleSource.UNEARTHED_ARCANA,
    WizardSubclassType.MAGE_OF_PRISMARI: RuleSource.UNEARTHED_ARCANA,
    WizardSubclassType.MAGE_OF_QUANDRIX: RuleSource.UNEARTHED_ARCANA,
    WizardSubclassType.MAGE_OF_SILVERQUILL: RuleSource.UNEARTHED_ARCANA,
    WizardSubclassType.ONOMANCY: RuleSource.UNEARTHED_ARCANA,
    WizardSubclassType.ORDER_OF_SCRIBES_UA: RuleSource.UNEARTHED_ARCANA,
    WizardSubclassType.PSIONICS: RuleSource.UNEARTHED_ARCANA,
    WizardSubclassType.TECHNOMANCY: RuleSource.UNEARTHED_ARCANA,
    WizardSubclassType.THEURGY: RuleSource.UNEARTHED_ARCANA,
}


@dataclass(frozen=True)
class WizardProgression:
    level: int
    proficiency_bonus: int
    features: tuple[WizardFeatureType, ...]
    cantrips_known: int
    prepared_spells: int
    spell_slots: tuple[int, int, int, int, int, int, int, int, int]


WIZARD_LEVELS: dict[int, WizardProgression] = {
    1: WizardProgression(1, 2, (WizardFeatureType.SPELLCASTING, WizardFeatureType.RITUAL_ADEPT, WizardFeatureType.ARCANE_RECOVERY), 3, 4, (2, 0, 0, 0, 0, 0, 0, 0, 0)),
    2: WizardProgression(2, 2, (WizardFeatureType.SCHOLAR,), 3, 5, (3, 0, 0, 0, 0, 0, 0, 0, 0)),
    3: WizardProgression(3, 2, (WizardFeatureType.WIZARD_SUBCLASS,), 3, 6, (4, 2, 0, 0, 0, 0, 0, 0, 0)),
    4: WizardProgression(4, 2, (WizardFeatureType.ABILITY_SCORE_IMPROVEMENT,), 4, 7, (4, 3, 0, 0, 0, 0, 0, 0, 0)),
    5: WizardProgression(5, 3, (WizardFeatureType.MEMORIZE_SPELL,), 4, 9, (4, 3, 2, 0, 0, 0, 0, 0, 0)),
    6: WizardProgression(6, 3, (WizardFeatureType.SUBCLASS_FEATURE,), 4, 10, (4, 3, 3, 0, 0, 0, 0, 0, 0)),
    7: WizardProgression(7, 3, (), 4, 11, (4, 3, 3, 1, 0, 0, 0, 0, 0)),
    8: WizardProgression(8, 3, (WizardFeatureType.ABILITY_SCORE_IMPROVEMENT,), 4, 12, (4, 3, 3, 2, 0, 0, 0, 0, 0)),
    9: WizardProgression(9, 4, (), 4, 14, (4, 3, 3, 3, 1, 0, 0, 0, 0)),
    10: WizardProgression(10, 4, (WizardFeatureType.SUBCLASS_FEATURE,), 5, 15, (4, 3, 3, 3, 2, 0, 0, 0, 0)),
    11: WizardProgression(11, 4, (), 5, 16, (4, 3, 3, 3, 2, 1, 0, 0, 0)),
    12: WizardProgression(12, 4, (WizardFeatureType.ABILITY_SCORE_IMPROVEMENT,), 5, 16, (4, 3, 3, 3, 2, 1, 0, 0, 0)),
    13: WizardProgression(13, 5, (), 5, 17, (4, 3, 3, 3, 2, 1, 1, 0, 0)),
    14: WizardProgression(14, 5, (WizardFeatureType.SUBCLASS_FEATURE,), 5, 18, (4, 3, 3, 3, 2, 1, 1, 0, 0)),
    15: WizardProgression(15, 5, (), 5, 19, (4, 3, 3, 3, 2, 1, 1, 1, 0)),
    16: WizardProgression(16, 5, (WizardFeatureType.ABILITY_SCORE_IMPROVEMENT,), 5, 21, (4, 3, 3, 3, 2, 1, 1, 1, 0)),
    17: WizardProgression(17, 6, (), 5, 22, (4, 3, 3, 3, 2, 1, 1, 1, 1)),
    18: WizardProgression(18, 6, (WizardFeatureType.SPELL_MASTERY,), 5, 23, (4, 3, 3, 3, 3, 1, 1, 1, 1)),
    19: WizardProgression(19, 6, (WizardFeatureType.EPIC_BOON,), 5, 24, (4, 3, 3, 3, 3, 2, 1, 1, 1)),
    20: WizardProgression(20, 6, (WizardFeatureType.SIGNATURE_SPELLS,), 5, 25, (4, 3, 3, 3, 3, 2, 2, 1, 1)),
}


def wizard_level(classes: list[CharacterClassLevel]) -> int:
    return sum(character_class.level for character_class in classes if character_class.name == ClassType.WIZARD)


def wizard_class(classes: list[CharacterClassLevel]) -> CharacterClassLevel | None:
    return next((character_class for character_class in classes if character_class.name == ClassType.WIZARD), None)


def wizard_progression(classes: list[CharacterClassLevel]) -> WizardProgression | None:
    level = wizard_level(classes)
    if level <= 0:
        return None
    return WIZARD_LEVELS[min(level, max(WIZARD_LEVELS))]


def wizard_subclass_source(subclass: WizardSubclassType) -> RuleSource:
    return WIZARD_SUBCLASS_SOURCES.get(subclass, RuleSource.LEGACY)


def wizard_subclass_label(subclass: WizardSubclassType) -> str:
    label = enum_label(subclass)
    source = wizard_subclass_source(subclass)
    current_sources = {
        RuleSource.PLAYERS_HANDBOOK_2024,
        RuleSource.FORGOTTEN_REALMS_HEROES_OF_FAERUN_2024,
    }
    return label if source in current_sources else f"{label} (Legacy)"


def wizard_resources(classes: list[CharacterClassLevel]) -> list[ResourceTracker]:
    progression = wizard_progression(classes)
    if progression is None:
        return []
    resources = [
        ResourceTracker(
            id=enum_key(WizardResourceType.ARCANE_RECOVERY),
            name=enum_label(WizardResourceType.ARCANE_RECOVERY),
            currentUses=1,
            maxUses=1,
            reset=RestType.LONG_REST,
            activation=TimeEconomy.SPECIAL,
            description="Once per Long Rest when you finish a Short Rest, recover expended spell slots with combined levels up to half your Wizard level rounded up.",
            source=enum_label(ClassType.WIZARD),
        )
    ]
    resource_types = (
        WizardResourceType.FIRST_LEVEL_SPELL_SLOTS,
        WizardResourceType.SECOND_LEVEL_SPELL_SLOTS,
        WizardResourceType.THIRD_LEVEL_SPELL_SLOTS,
        WizardResourceType.FOURTH_LEVEL_SPELL_SLOTS,
        WizardResourceType.FIFTH_LEVEL_SPELL_SLOTS,
        WizardResourceType.SIXTH_LEVEL_SPELL_SLOTS,
        WizardResourceType.SEVENTH_LEVEL_SPELL_SLOTS,
        WizardResourceType.EIGHTH_LEVEL_SPELL_SLOTS,
        WizardResourceType.NINTH_LEVEL_SPELL_SLOTS,
    )
    for slot_level, (resource_type, max_uses) in enumerate(zip(resource_types, progression.spell_slots), start=1):
        if max_uses <= 0:
            continue
        resources.append(ResourceTracker(
            id=enum_key(resource_type),
            name=enum_label(resource_type),
            currentUses=max_uses,
            maxUses=max_uses,
            reset=RestType.LONG_REST,
            activation=TimeEconomy.SPECIAL,
            description=f"Level {slot_level} Wizard spell slots.",
            source=enum_label(ClassType.WIZARD),
        ))
    return resources


def wizard_features(classes: list[CharacterClassLevel]) -> list[SheetFeature]:
    progression = wizard_progression(classes)
    character_class = wizard_class(classes)
    if progression is None or character_class is None:
        return []
    features: list[SheetFeature] = []
    for level in range(1, progression.level + 1):
        level_progression = WIZARD_LEVELS[level]
        features.extend(feature_for_type(feature_type, level_progression, character_class) for feature_type in level_progression.features)
    from dnd_board.rules.classes.wizard.archetypes import wizard_subclass_features

    features.extend(wizard_subclass_features(character_class.subclass, progression.level))
    return dedupe_features(features)


def feature_for_type(feature_type: WizardFeatureType, progression: WizardProgression, character_class: CharacterClassLevel) -> SheetFeature:
    descriptions = {
        WizardFeatureType.SPELLCASTING: f"Use Intelligence for Wizard spells. Prepare {progression.prepared_spells} spells and know {progression.cantrips_known} cantrips at this Wizard level.",
        WizardFeatureType.RITUAL_ADEPT: "You can cast Wizard ritual spells in your spellbook as rituals even if they are not prepared.",
        WizardFeatureType.ARCANE_RECOVERY: "Tracked as a resource. Recover expended spell slots after a Short Rest once per Long Rest.",
        WizardFeatureType.SCHOLAR: "Gain Expertise in one trained Intelligence skill: Arcana, History, Investigation, Nature, or Religion.",
        WizardFeatureType.WIZARD_SUBCLASS: subclass_description(character_class),
        WizardFeatureType.ABILITY_SCORE_IMPROVEMENT: "Gain Ability Score Improvement or another feat for which you qualify.",
        WizardFeatureType.MEMORIZE_SPELL: "After a Short Rest, replace one prepared Wizard spell with another spell from your spellbook.",
        WizardFeatureType.SUBCLASS_FEATURE: subclass_description(character_class),
        WizardFeatureType.SPELL_MASTERY: "Choose a level 1 and level 2 Wizard spell in your spellbook that have a casting time of Action; cast them at their lowest level without expending a spell slot.",
        WizardFeatureType.EPIC_BOON: "Gain an Epic Boon feat or another feat for which you qualify.",
        WizardFeatureType.SIGNATURE_SPELLS: "Choose two level 3 Wizard spells in your spellbook as Signature Spells; each can be cast once without a spell slot per Short or Long Rest.",
    }
    return SheetFeature(
        id=enum_key(feature_type),
        name=enum_label(feature_type),
        source=enum_label(ClassType.WIZARD),
        activation=feature_activation(feature_type),
        description=descriptions[feature_type],
    )


def feature_activation(feature_type: WizardFeatureType) -> TimeEconomy:
    if feature_type == WizardFeatureType.MEMORIZE_SPELL:
        return TimeEconomy.SPECIAL
    return TimeEconomy.PASSIVE


def subclass_description(character_class: CharacterClassLevel) -> str:
    if character_class.subclass is None:
        return "Choose a Wizard subclass."
    if isinstance(character_class.subclass, WizardSubclassType):
        source = rule_source_label(wizard_subclass_source(character_class.subclass))
        return f"{wizard_subclass_label(character_class.subclass)} subclass features ({source}) are included up to your Wizard level."
    return f"{enum_label(character_class.subclass)} subclass features are included up to your Wizard level."


def wizard_cantrip_count(wizard: CharacterClassLevel) -> int:
    if wizard.level < 1:
        return 0
    return WIZARD_LEVELS[min(wizard.level, max(WIZARD_LEVELS))].cantrips_known


def wizard_prepared_spell_count(wizard: CharacterClassLevel) -> int:
    if wizard.level < 1:
        return 0
    return WIZARD_LEVELS[min(wizard.level, max(WIZARD_LEVELS))].prepared_spells


def wizard_spellbook_spell_count(wizard: CharacterClassLevel) -> int:
    if wizard.level < 1:
        return 0
    return 6 + ((min(wizard.level, max(WIZARD_LEVELS)) - 1) * 2)


def wizard_configured_spell_count(wizard: CharacterClassLevel) -> int:
    if wizard.level < 1:
        return 0
    progression = WIZARD_LEVELS[min(wizard.level, max(WIZARD_LEVELS))]
    return progression.cantrips_known + progression.prepared_spells


def wizard_cantrip_options(wizard_level_value: int) -> list[SpellEntry]:
    return spell_entries_for_list(
        SpellListType.WIZARD,
        exact_level=0,
        source=SpellSource.WIZARD,
        casting_ability=AbilityType.INTELLIGENCE,
    )


def wizard_prepared_spell_options(wizard_level_value: int) -> list[SpellEntry]:
    progression = WIZARD_LEVELS[min(max(1, wizard_level_value), max(WIZARD_LEVELS))]
    return [
        spell
        for spell in spell_entries_for_list(
            SpellListType.WIZARD,
            maximum_level=max_prepared_spell_level(progression),
            source=SpellSource.WIZARD,
            casting_ability=AbilityType.INTELLIGENCE,
        )
        if spell.level > 0
    ]


def wizard_spellbook_spell_options(wizard_level_value: int) -> list[SpellEntry]:
    return wizard_prepared_spell_options(wizard_level_value)


def is_wizard_cantrip_selection_valid(wizard_level_value: int, spells: list[SpellEntry]) -> bool:
    progression = WIZARD_LEVELS[min(max(1, wizard_level_value), max(WIZARD_LEVELS))]
    return (
        len(spells) == progression.cantrips_known
        and len({spell.id for spell in spells}) == len(spells)
        and all(spell.source == SpellSource.WIZARD and spell.level == 0 for spell in spells)
    )


def is_wizard_prepared_spell_selection_valid(wizard_level_value: int, spells: list[SpellEntry]) -> bool:
    progression = WIZARD_LEVELS[min(max(1, wizard_level_value), max(WIZARD_LEVELS))]
    max_spell_level = max_prepared_spell_level(progression)
    return (
        len(spells) == progression.prepared_spells
        and len({spell.id for spell in spells}) == len(spells)
        and all(spell.source == SpellSource.WIZARD and 0 < spell.level <= max_spell_level for spell in spells)
    )


def is_wizard_spellbook_selection_valid(wizard_level_value: int, spells: list[SpellEntry]) -> bool:
    progression = WIZARD_LEVELS[min(max(1, wizard_level_value), max(WIZARD_LEVELS))]
    max_spell_level = max_prepared_spell_level(progression)
    return (
        len(spells) == 6 + ((progression.level - 1) * 2)
        and len({spell.id for spell in spells}) == len(spells)
        and all(spell.source == SpellSource.WIZARD and 0 < spell.level <= max_spell_level for spell in spells)
    )


def wizard_spellbook_spells(spells: list[SpellEntry]) -> list[SpellEntry]:
    return [spell for spell in spells if spell.source == SpellSource.WIZARD and spell.level > 0]


def wizard_cantrips(spells: list[SpellEntry]) -> list[SpellEntry]:
    return [spell for spell in spells if spell.source == SpellSource.WIZARD and spell.level == 0]


def wizard_prepared_spells(spells: list[SpellEntry]) -> list[SpellEntry]:
    return [spell for spell in spells if spell.source == SpellSource.WIZARD and spell.level > 0]


def wizard_catalog_spell(value: str | SpellId) -> SpellEntry | None:
    return spell_entry_for_list(value, SpellListType.WIZARD, source=SpellSource.WIZARD, casting_ability=AbilityType.INTELLIGENCE)


def pruned_wizard_spells(wizard_level_value: int, spells: list[SpellEntry]) -> list[SpellEntry]:
    progression = WIZARD_LEVELS[min(max(1, wizard_level_value), max(WIZARD_LEVELS))]
    max_spell_level = max_prepared_spell_level(progression)
    cantrips = [spell for spell in spells if spell.source == SpellSource.WIZARD and spell.level == 0][: progression.cantrips_known]
    prepared = [spell for spell in spells if spell.source == SpellSource.WIZARD and 0 < spell.level <= max_spell_level][: progression.prepared_spells]
    return [*cantrips, *prepared]


def pruned_wizard_spellbook(wizard_level_value: int, spellbook: list[SpellEntry]) -> list[SpellEntry]:
    progression = WIZARD_LEVELS[min(max(1, wizard_level_value), max(WIZARD_LEVELS))]
    max_spell_level = max_prepared_spell_level(progression)
    spell_count = 6 + ((progression.level - 1) * 2)
    return [spell for spell in spellbook if spell.source == SpellSource.WIZARD and 0 < spell.level <= max_spell_level][:spell_count]


def max_prepared_spell_level(progression: WizardProgression) -> int:
    for index in range(len(progression.spell_slots) - 1, -1, -1):
        if progression.spell_slots[index] > 0:
            return index + 1
    return 1


def wizard_skill_proficiency_count(wizard: CharacterClassLevel) -> int:
    return 2 if wizard.level >= 1 else 0


def wizard_skill_option_types() -> list[SkillType]:
    from dnd_board.character_sheet import SkillType

    return [
        SkillType.ARCANA,
        SkillType.HISTORY,
        SkillType.INSIGHT,
        SkillType.INVESTIGATION,
        SkillType.MEDICINE,
        SkillType.RELIGION,
    ]


def wizard_asi_levels_up_to(wizard_level: int) -> int:
    return sum(1 for level in [4, 8, 12, 16, 19] if wizard_level >= level)


def dedupe_features(features: list[SheetFeature]) -> list[SheetFeature]:
    deduped: dict[str, SheetFeature] = {}
    for feature in features:
        deduped[feature.id] = feature
    return list(deduped.values())
