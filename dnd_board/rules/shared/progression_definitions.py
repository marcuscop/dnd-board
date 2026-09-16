from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from dnd_board.character_sheet import (
    AbilityType,
    ArcaneShotType,
    BattleMasterManeuverType,
    ClassOptionKind,
    ClassType,
    FightingStyleType,
    ProficiencyLevel,
    ProgressionChoiceType,
    RuneType,
    SkillType,
    SpellId,
    SpellEntry,
    SpellSchool,
    SpellSource,
)
from dnd_board.rules.shared.effects import Modifier


class ProgressionChoiceId(Enum):
    HIT_POINT_INCREASE = "hitPointIncrease"
    FEAT_ABILITY_SCORE_INCREASE = "featAbilityScoreIncrease"
    FIGHTER_ABILITY_SCORE_IMPROVEMENT = "fighterAbilityScoreImprovement"
    ROGUE_ABILITY_SCORE_IMPROVEMENT = "rogueAbilityScoreImprovement"
    WIZARD_ABILITY_SCORE_IMPROVEMENT = "wizardAbilityScoreImprovement"
    FIGHTER_EPIC_BOON = "fighterEpicBoon"
    ROGUE_EPIC_BOON = "rogueEpicBoon"
    WIZARD_EPIC_BOON = "wizardEpicBoon"
    FIGHTER_SKILL_PROFICIENCIES = "fighterSkillProficiencies"
    ROGUE_SKILL_PROFICIENCIES = "rogueSkillProficiencies"
    WIZARD_SKILL_PROFICIENCIES = "wizardSkillProficiencies"
    ROGUE_EXPERTISE = "rogueExpertise"
    FIGHTER_SUBCLASS = "fighterSubclass"
    ROGUE_SUBCLASS = "rogueSubclass"
    WIZARD_SUBCLASS = "wizardSubclass"
    FIGHTER_FIGHTING_STYLES = "fighterFightingStyles"
    BATTLE_MASTER_MANEUVERS = "battleMasterManeuvers"
    ARCANE_ARCHER_SHOTS = "arcaneArcherShots"
    RUNE_KNIGHT_RUNES = "runeKnightRunes"
    ELDRITCH_KNIGHT_SPELLS = "eldritchKnightSpells"
    ARCANE_TRICKSTER_SPELLS = "arcaneTricksterSpells"
    WIZARD_CANTRIPS = "wizardCantrips"
    WIZARD_SPELLBOOK_SPELLS = "wizardSpellbookSpells"
    WIZARD_PREPARED_SPELLS = "wizardPreparedSpells"


@dataclass(frozen=True)
class ProgressionChoicePresentation:
    choiceType: ProgressionChoiceType
    label: str
    description: str


class SelectionReplacementPolicy(Enum):
    SAME_SOURCE = "sameSource"


@dataclass(frozen=True)
class SkillProgressionDefinition:
    choice: ProgressionChoiceId
    presentation: ProgressionChoicePresentation
    candidates: tuple[SkillType, ...]
    count: int
    proficiency: ProficiencyLevel = ProficiencyLevel.PROFICIENT
    requiresExistingProficiency: bool = False
    countsByClassLevel: tuple[int, ...] = ()
    grantMinimumLevels: tuple[int, ...] = ()
    replacement: SelectionReplacementPolicy = SelectionReplacementPolicy.SAME_SOURCE

    def count_at_level(self, class_level: int) -> int:
        if class_level < 1:
            return 0
        if not self.countsByClassLevel:
            return self.count
        return self.countsByClassLevel[
            min(class_level, len(self.countsByClassLevel)) - 1
        ]


class SpellCollection(Enum):
    KNOWN = "known"
    PREPARED = "prepared"
    SPELLBOOK = "spellbook"


class SpellPool(Enum):
    CLASS_SPELL_LIST = "classSpellList"
    CHARACTER_COLLECTION = "characterCollection"


class SpellConstraint(Enum):
    CANTRIP = "cantrip"
    NON_CANTRIP = "nonCantrip"
    WITHIN_AVAILABLE_SPELL_LEVEL = "withinAvailableSpellLevel"


class SpellLevelCategory(Enum):
    CANTRIP = "cantrip"
    LEVELED = "leveled"


ClassOption = BattleMasterManeuverType | ArcaneShotType | RuneType


@dataclass(frozen=True)
class ClassOptionProgressionDefinition:
    choice: ProgressionChoiceId
    presentation: ProgressionChoicePresentation
    characterClass: ClassType
    kind: ClassOptionKind
    candidates: tuple[ClassOption, ...]
    candidateLabels: tuple[tuple[ClassOption, str], ...]
    minimumLevel: int
    grantLevelsByClassLevel: tuple[tuple[int, ...], ...]
    requiredSubclass: Enum | None = None
    candidateMinimumLevels: tuple[tuple[ClassOption, int], ...] = ()
    additionalFightingStyle: FightingStyleType | None = None
    grantSubclass: Enum | None = None
    replacement: SelectionReplacementPolicy = SelectionReplacementPolicy.SAME_SOURCE

    def candidates_at_level(self, class_level: int) -> tuple[ClassOption, ...]:
        minimum_levels = dict(self.candidateMinimumLevels)
        return tuple(
            candidate
            for candidate in self.candidates
            if class_level >= minimum_levels.get(candidate, self.minimumLevel)
        )

    def grant_levels_at_level(self, class_level: int) -> tuple[int, ...]:
        if class_level < 1:
            return ()
        return self.grantLevelsByClassLevel[
            min(class_level, len(self.grantLevelsByClassLevel)) - 1
        ]


@dataclass(frozen=True)
class SpellChoiceDefinition:
    pool: SpellPool
    count: int
    constraints: tuple[SpellConstraint, ...]
    destination: SpellCollection
    source: SpellSource
    replacement: SelectionReplacementPolicy
    minimumPoolSize: int = 0
    grantMinimumLevels: tuple[int, ...] = ()
    requiredSpells: tuple[SpellId, ...] = ()
    preferredSchools: tuple[SpellSchool, ...] = ()
    unrestrictedCount: int | None = None
    poolClass: ClassType | None = None
    poolCollection: SpellCollection | None = None
    maximumSpellLevel: int | None = None
    castingAbility: AbilityType = AbilityType.INTELLIGENCE
    supplementalSpells: tuple[SpellId, ...] = ()
    supplementalSpellEntries: tuple[SpellEntry, ...] = ()


@dataclass(frozen=True)
class SpellChoiceProgressionDefinition:
    pool: SpellPool
    countsByClassLevel: tuple[int, ...]
    constraints: tuple[SpellConstraint, ...]
    destination: SpellCollection
    source: SpellSource
    grantMinimumLevels: tuple[int, ...] = ()
    minimumPoolSizesByClassLevel: tuple[int, ...] = ()
    requiredSpells: tuple[SpellId, ...] = ()
    preferredSchools: tuple[SpellSchool, ...] = ()
    unrestrictedCountsByClassLevel: tuple[int, ...] = ()
    poolClass: ClassType | None = None
    poolCollection: SpellCollection | None = None
    maximumSpellLevelsByClassLevel: tuple[int, ...] = ()
    castingAbility: AbilityType = AbilityType.INTELLIGENCE
    supplementalSpells: tuple[SpellId, ...] = ()
    supplementalSpellEntries: tuple[SpellEntry, ...] = ()

    def at_level(self, class_level: int) -> SpellChoiceDefinition:
        level_index = max(0, min(class_level, len(self.countsByClassLevel)) - 1)
        return SpellChoiceDefinition(
            pool=self.pool,
            count=self.countsByClassLevel[level_index],
            constraints=self.constraints,
            destination=self.destination,
            source=self.source,
            replacement=SelectionReplacementPolicy.SAME_SOURCE,
            minimumPoolSize=(
                self.minimumPoolSizesByClassLevel[level_index]
                if self.minimumPoolSizesByClassLevel
                else 0
            ),
            grantMinimumLevels=self.grantMinimumLevels,
            requiredSpells=self.requiredSpells,
            preferredSchools=self.preferredSchools,
            unrestrictedCount=(
                self.unrestrictedCountsByClassLevel[level_index]
                if self.unrestrictedCountsByClassLevel
                else None
            ),
            poolClass=self.poolClass,
            poolCollection=self.poolCollection,
            maximumSpellLevel=(
                self.maximumSpellLevelsByClassLevel[level_index]
                if self.maximumSpellLevelsByClassLevel
                else None
            ),
            castingAbility=self.castingAbility,
            supplementalSpells=self.supplementalSpells,
            supplementalSpellEntries=self.supplementalSpellEntries,
        )


@dataclass(frozen=True)
class SpellProgressionDefinition:
    choice: ProgressionChoiceId
    presentation: ProgressionChoicePresentation
    minimumLevel: int
    choices: tuple[SpellChoiceProgressionDefinition, ...]
    requiredSubclass: Enum | None = None


def grant_minimum_levels(
    counts_by_class_level: tuple[int, ...],
    minimum_level: int,
) -> tuple[int, ...]:
    maximum_count = max(counts_by_class_level, default=0)
    return tuple(
        next(
            level
            for level, count in enumerate(counts_by_class_level, start=1)
            if level >= minimum_level and count >= slot
        )
        for slot in range(1, maximum_count + 1)
    )


@dataclass(frozen=True)
class ClassProgressionDefinition:
    characterClass: ClassType
    abilityScoreImprovementLevels: tuple[int, ...]
    epicBoonLevel: int
    subclasses: tuple[Enum, ...]
    subclassLevel: int = 3
    abilityScoreImprovementChoice: ProgressionChoiceId | None = None
    abilityScoreImprovementPresentation: ProgressionChoicePresentation | None = None
    abilityScoreImprovementFeatCategories: tuple[Enum, ...] = ()
    epicBoonChoice: ProgressionChoiceId | None = None
    epicBoonPresentation: ProgressionChoicePresentation | None = None
    epicBoonFeatCategories: tuple[Enum, ...] = ()
    subclassChoice: ProgressionChoiceId | None = None
    subclassPresentation: ProgressionChoicePresentation | None = None
    skillChoices: tuple[SkillProgressionDefinition, ...] = ()
    spellChoices: tuple[SpellProgressionDefinition, ...] = ()
    fightingStyleChoice: ProgressionChoiceId | None = None
    fightingStylePresentation: ProgressionChoicePresentation | None = None
    fightingStyleFeatCategories: tuple[Enum, ...] = ()
    classOptionChoices: tuple[ClassOptionProgressionDefinition, ...] = ()
    allocationModifiersByLevel: tuple[tuple[Modifier, ...], ...] = ()
