from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from dnd_board.character_sheet import (
    CLASS_HIT_DICE,
    AbilityScores,
    AbilityType,
    ArcaneShotType,
    BattleMasterManeuverType,
    CharacterClassLevel,
    ClassOptionKind,
    ClassOptionSelection,
    ClassType,
    FightingStyleType,
    ProficiencyLevel,
    ProgressionChoice,
    ProgressionChoiceOption,
    ProgressionChoiceType,
    RuneType,
    SheetFeature,
    SkillType,
    SpellId,
    SpellSchool,
    SpellSource,
    SpellEntry,
    enum_key,
    enum_label,
    enum_value,
)
from dnd_board.rules.classes.fighter.archetypes import (
    ARCANE_ARCHER_SHOT_PROGRESSION_DEFINITION,
    ELDRITCH_KNIGHT_SPELL_PROGRESSION_DEFINITION,
    RUNE_KNIGHT_RUNE_PROGRESSION_DEFINITION,
)
from dnd_board.rules.classes.fighter.base import FIGHTER_PROGRESSION_DEFINITION, FighterSubclassType, fighter_fighting_style_entitlements, fighter_subclass_label
from dnd_board.rules.classes.fighter.battle_master import BATTLE_MASTER_MANEUVER_PROGRESSION_DEFINITION
from dnd_board.rules.classes.rogue.archetypes import (
    ARCANE_TRICKSTER_SPELL_PROGRESSION_DEFINITION,
)
from dnd_board.rules.classes.rogue.base import ROGUE_PROGRESSION_DEFINITION, RogueSubclassType, rogue_subclass_label
from dnd_board.rules.classes.wizard.base import (
    WIZARD_PROGRESSION_DEFINITION,
    WizardSubclassType,
    wizard_subclass_label,
)
from dnd_board.rules.feats import (
    FIGHTING_STYLE_FEATS,
    GENERAL_FEATS,
    FeatCategory,
    GeneralFeatType,
    general_feat_category,
    general_feat_prerequisites_met,
    fighting_style_label,
    selected_fighting_styles as selected_fighting_style_values,
)
from dnd_board.rules.shared.progression_definitions import (
    ProgressionChoiceId,
    ProgressionChoicePresentation,
    SelectionReplacementPolicy,
    SpellChoiceDefinition,
    SpellCollection,
    SpellConstraint,
    SpellLevelCategory,
    SpellPool,
)


MIN_CHARACTER_LEVEL = 1
MAX_CHARACTER_LEVEL = 20

CLASS_PROGRESSION_DEFINITIONS = {
    definition.characterClass: definition
    for definition in (
        FIGHTER_PROGRESSION_DEFINITION,
        ROGUE_PROGRESSION_DEFINITION,
        WIZARD_PROGRESSION_DEFINITION,
    )
}

SPELL_PROGRESSION_DEFINITIONS = tuple(
    (definition.characterClass, spell_progression)
    for definition in CLASS_PROGRESSION_DEFINITIONS.values()
    for spell_progression in definition.spellChoices
) + (
    (ClassType.FIGHTER, ELDRITCH_KNIGHT_SPELL_PROGRESSION_DEFINITION),
    (ClassType.ROGUE, ARCANE_TRICKSTER_SPELL_PROGRESSION_DEFINITION),
)

CLASS_OPTION_PROGRESSION_DEFINITIONS = (
    BATTLE_MASTER_MANEUVER_PROGRESSION_DEFINITION,
    ARCANE_ARCHER_SHOT_PROGRESSION_DEFINITION,
    RUNE_KNIGHT_RUNE_PROGRESSION_DEFINITION,
)


def configured_progression_choice_ids() -> tuple[ProgressionChoiceId, ...]:
    configured: list[ProgressionChoiceId] = []
    for choices in (
        (
            definition.abilityScoreImprovementChoice
            for definition in CLASS_PROGRESSION_DEFINITIONS.values()
        ),
        (
            definition.epicBoonChoice
            for definition in CLASS_PROGRESSION_DEFINITIONS.values()
        ),
    ):
        configured.extend(
            choice
            for choice in choices
            if choice is not None
        )
    configured.extend(
        choice.choice
        for definition in CLASS_PROGRESSION_DEFINITIONS.values()
        for choice in definition.skillChoices
    )
    configured.extend(
        choice.choice
        for _, choice in SPELL_PROGRESSION_DEFINITIONS
    )
    configured.extend(
        choice
        for definition in CLASS_PROGRESSION_DEFINITIONS.values()
        if (choice := definition.subclassChoice) is not None
    )
    configured.extend(
        choice
        for definition in CLASS_PROGRESSION_DEFINITIONS.values()
        if (choice := definition.fightingStyleChoice) is not None
    )
    configured.extend(
        choice.choice
        for choice in CLASS_OPTION_PROGRESSION_DEFINITIONS
    )
    return tuple(dict.fromkeys(configured))


class HitPointChoiceOption(Enum):
    FIXED = "fixed"
    ROLL = "roll"


class HitPointChoiceOptionLabel(Enum):
    FIXED = "Fixed"
    ROLL = "Roll"


class SpellOptionLabel(Enum):
    CANTRIP = "Cantrip"
    LEVEL = "Level {level}"


class ProgressionSelectionPrefix(Enum):
    FEAT = "feat:"


class SkillSelectionIssue(Enum):
    REQUIREMENT_NOT_MET = "requirementNotMet"
    WRONG_COUNT = "wrongCount"
    INVALID_OPTION = "invalidOption"
    REQUIRES_PROFICIENCY = "requiresProficiency"
    INVALID_FEAT = "invalidFeat"
    INVALID_FEAT_CATEGORY = "invalidFeatCategory"
    FEAT_ALREADY_SELECTED = "featAlreadySelected"
    FEAT_PREREQUISITE_NOT_MET = "featPrerequisiteNotMet"


SubclassType = FighterSubclassType | RogueSubclassType | WizardSubclassType


@dataclass(frozen=True)
class ClassLevelRequirement:
    characterClass: ClassType
    minimumLevel: int
    subclass: FighterSubclassType | RogueSubclassType | WizardSubclassType | None = None


@dataclass(frozen=True)
class SkillProficiencyGrant:
    skill: SkillType
    proficiency: ProficiencyLevel
    minimumClassLevel: int = 1

    def __post_init__(self) -> None:
        if self.minimumClassLevel < 1:
            raise ValueError("Grant minimum class level must be positive")


@dataclass(frozen=True)
class SpellGrant:
    spell: SpellId
    destination: SpellCollection
    source: SpellSource
    category: SpellLevelCategory
    minimumClassLevel: int = 1

    def __post_init__(self) -> None:
        if self.minimumClassLevel < 1:
            raise ValueError("Grant minimum class level must be positive")


@dataclass(frozen=True)
class SpellGrantScope:
    destination: SpellCollection
    source: SpellSource
    category: SpellLevelCategory


@dataclass(frozen=True)
class HitPointGrant:
    characterClass: ClassType
    minimumClassLevel: int
    choice: HitPointChoiceOption
    amount: int
    hitDieResult: int

    def __post_init__(self) -> None:
        if self.minimumClassLevel < 1:
            raise ValueError("Grant minimum class level must be positive")
        if self.amount < 1:
            raise ValueError("Hit point grant amount must be positive")
        if self.hitDieResult < 1:
            raise ValueError("Hit die result must be positive")


@dataclass(frozen=True)
class AbilityScoreGrant:
    characterClass: ClassType
    minimumClassLevel: int
    ability: AbilityType
    amount: int

    def __post_init__(self) -> None:
        if self.minimumClassLevel < 1:
            raise ValueError("Grant minimum class level must be positive")
        if self.amount < 1:
            raise ValueError("Ability score grant amount must be positive")


@dataclass(frozen=True)
class FeatGrant:
    characterClass: ClassType
    minimumClassLevel: int
    feat: GeneralFeatType

    def __post_init__(self) -> None:
        if self.minimumClassLevel < 1:
            raise ValueError("Grant minimum class level must be positive")


@dataclass(frozen=True)
class FightingStyleGrant:
    characterClass: ClassType
    minimumClassLevel: int
    style: FightingStyleType

    def __post_init__(self) -> None:
        if self.minimumClassLevel < 1:
            raise ValueError("Grant minimum class level must be positive")


@dataclass(frozen=True)
class ClassOptionGrant:
    characterClass: ClassType
    minimumClassLevel: int
    kind: ClassOptionKind
    option: BattleMasterManeuverType | ArcaneShotType | RuneType

    def __post_init__(self) -> None:
        if self.minimumClassLevel < 1:
            raise ValueError("Grant minimum class level must be positive")


@dataclass(frozen=True)
class SubclassGrant:
    characterClass: ClassType
    subclass: SubclassType
    minimumClassLevel: int = 3

    def __post_init__(self) -> None:
        if self.minimumClassLevel < 1:
            raise ValueError("Grant minimum class level must be positive")


CharacterGrant = AbilityScoreGrant | ClassOptionGrant | FeatGrant | FightingStyleGrant | HitPointGrant | SkillProficiencyGrant | SpellGrant | SubclassGrant


@dataclass(frozen=True)
class SkillChoiceDefinition:
    candidates: tuple[SkillType, ...]
    count: int
    proficiency: ProficiencyLevel
    requiresExistingProficiency: bool = False
    grantMinimumLevels: tuple[int, ...] = ()


@dataclass(frozen=True)
class ClassOptionChoiceDefinition:
    characterClass: ClassType
    kind: ClassOptionKind
    candidates: tuple[BattleMasterManeuverType | ArcaneShotType | RuneType, ...]
    candidateLabels: tuple[tuple[BattleMasterManeuverType | ArcaneShotType | RuneType, str], ...]
    count: int
    grantMinimumLevels: tuple[int, ...]

    def __post_init__(self) -> None:
        if self.count < 0 or len(self.grantMinimumLevels) != self.count:
            raise ValueError("Class option count must match its grant levels")


@dataclass(frozen=True)
class HitPointChoiceDefinition:
    characterClass: ClassType
    classLevel: int
    hitDie: int


@dataclass(frozen=True)
class FeatChoiceDefinition:
    characterClass: ClassType
    classLevel: int
    categories: tuple[FeatCategory, ...]
    candidates: tuple[GeneralFeatType | FightingStyleType, ...]
    count: int = 1


@dataclass(frozen=True)
class AbilityScoreChoiceDefinition:
    characterClass: ClassType
    classLevel: int
    candidates: tuple[AbilityType, ...] = tuple(AbilityType)
    scoreCap: int = 20
    points: int = 2
    featChoice: FeatChoiceDefinition | None = None


@dataclass(frozen=True)
class SubclassChoiceDefinition:
    characterClass: ClassType
    candidates: tuple[SubclassType, ...]
    count: int = 1


CharacterChoiceDefinition = AbilityScoreChoiceDefinition | ClassOptionChoiceDefinition | FeatChoiceDefinition | HitPointChoiceDefinition | SkillChoiceDefinition | SpellChoiceDefinition | SubclassChoiceDefinition


@dataclass(frozen=True)
class ProgressionRule:
    id: ProgressionChoiceId
    presentation: ProgressionChoicePresentation
    requirements: tuple[ClassLevelRequirement, ...]
    choices: tuple[CharacterChoiceDefinition, ...]


@dataclass(frozen=True)
class ProgressionGrantSource:
    rule: ProgressionChoiceId
    characterClass: ClassType
    requiredSubclass: SubclassType | None = None


@dataclass(frozen=True)
class ProgressionGrantRecord:
    source: ProgressionGrantSource
    grants: tuple[CharacterGrant, ...]


@dataclass(frozen=True)
class ProgressionEvaluation:
    source: ProgressionGrantSource
    grants: tuple[CharacterGrant, ...]


class ProgressionRuleViolation(ValueError):
    def __init__(self, issue: SkillSelectionIssue) -> None:
        super().__init__(issue.value)
        self.issue = issue


def level_advance_allowed(pending_choices: list[ProgressionChoice]) -> bool:
    return not pending_choices


def skill_proficiency_selection_valid(
    selected: list[SkillType],
    options: list[SkillType],
    expected_count: int,
) -> bool:
    return len(selected) == expected_count and set(selected).issubset(options)


def skill_proficiency_selection_issue(
    selected: list[SkillType],
    options: list[SkillType],
    expected_count: int,
) -> SkillSelectionIssue | None:
    if len(selected) != expected_count:
        return SkillSelectionIssue.WRONG_COUNT
    if not set(selected).issubset(options):
        return SkillSelectionIssue.INVALID_OPTION
    return None


def rogue_expertise_eligible_skill_keys(
    skills: dict[str, ProficiencyLevel],
) -> set[str]:
    return {
        skill_key
        for skill_key, proficiency in skills.items()
        if proficiency in {ProficiencyLevel.PROFICIENT, ProficiencyLevel.EXPERTISE}
    }


def rogue_expertise_selection_count(
    rogue: CharacterClassLevel,
    skills: dict[str, ProficiencyLevel],
) -> int:
    expertise = next(
        choice
        for choice in ROGUE_PROGRESSION_DEFINITION.skillChoices
        if choice.proficiency == ProficiencyLevel.EXPERTISE
    )
    return min(
        expertise.count_at_level(rogue.level),
        len(rogue_expertise_eligible_skill_keys(skills)),
    )


def rogue_expertise_selection_valid(
    rogue: CharacterClassLevel,
    skills: dict[str, ProficiencyLevel],
    selected: list[SkillType],
) -> bool:
    eligible = rogue_expertise_eligible_skill_keys(skills)
    return (
        len(selected) == rogue_expertise_selection_count(rogue, skills)
        and all(enum_key(skill) in eligible for skill in selected)
    )


def rogue_expertise_selection_issue(
    rogue: CharacterClassLevel,
    skills: dict[str, ProficiencyLevel],
    selected: list[SkillType],
) -> SkillSelectionIssue | None:
    if len(selected) != rogue_expertise_selection_count(rogue, skills):
        return SkillSelectionIssue.WRONG_COUNT
    if any(enum_key(skill) not in rogue_expertise_eligible_skill_keys(skills) for skill in selected):
        return SkillSelectionIssue.REQUIRES_PROFICIENCY
    return None


def progression_rule(
    choice_id: ProgressionChoiceId,
    classes: list[CharacterClassLevel],
    skills: dict[str, ProficiencyLevel],
    progression_grants: list[ProgressionGrantRecord] | None = None,
) -> ProgressionRule | None:
    if choice_id == ProgressionChoiceId.HIT_POINT_INCREASE:
        target = next_hit_point_progression_target(classes, progression_grants or [])
        if target is None:
            return None
        character_class, class_level = target
        return ProgressionRule(
            choice_id,
            ProgressionChoicePresentation(
                ProgressionChoiceType.HIT_POINTS,
                "Hit Points",
                f"Choose fixed HP or roll the {hit_die_label(character_class.name)} for this level. Constitution modifier is applied by the server.",
            ),
            (ClassLevelRequirement(character_class.name, class_level),),
            (HitPointChoiceDefinition(
                characterClass=character_class.name,
                classLevel=class_level,
                hitDie=class_hit_die(character_class.name),
            ),),
        )
    ability_score_definition = next(
        (
            definition
            for definition in CLASS_PROGRESSION_DEFINITIONS.values()
            if definition.abilityScoreImprovementChoice == choice_id
        ),
        None,
    )
    if ability_score_definition is not None:
        ability_score_class = ability_score_definition.characterClass
        class_level = next_ability_score_improvement_level(
            choice_id,
            ability_score_class,
            classes,
            progression_grants or [],
        )
        if class_level is None:
            return None
        presentation = ability_score_definition.abilityScoreImprovementPresentation
        if presentation is None:
            raise ValueError("Ability Score Improvement choice requires presentation metadata")
        return ProgressionRule(
            choice_id,
            presentation,
            (ClassLevelRequirement(ability_score_class, class_level),),
            (AbilityScoreChoiceDefinition(
                ability_score_class,
                class_level,
                featChoice=feat_choice_definition(
                    ability_score_class,
                    class_level,
                    tuple(
                        category
                        for category in ability_score_definition.abilityScoreImprovementFeatCategories
                        if isinstance(category, FeatCategory)
                    ),
                ),
            ),),
        )
    epic_boon_definition = next(
        (
            definition
            for definition in CLASS_PROGRESSION_DEFINITIONS.values()
            if definition.epicBoonChoice == choice_id
        ),
        None,
    )
    if epic_boon_definition is not None:
        epic_boon_class = epic_boon_definition.characterClass
        class_entry = next(
            (entry for entry in classes if entry.name == epic_boon_class),
            None,
        )
        already_granted = any(
            record.source.rule == choice_id
            and any(isinstance(grant, FeatGrant) for grant in record.grants)
            for record in progression_grants or []
        )
        epic_boon_level = epic_boon_definition.epicBoonLevel
        if class_entry is None or class_entry.level < epic_boon_level or already_granted:
            return None
        presentation = epic_boon_definition.epicBoonPresentation
        if presentation is None:
            raise ValueError("Epic Boon choice requires presentation metadata")
        return ProgressionRule(
            choice_id,
            presentation,
            (ClassLevelRequirement(epic_boon_class, epic_boon_level),),
            (feat_choice_definition(
                epic_boon_class,
                epic_boon_level,
                tuple(
                    category
                    for category in epic_boon_definition.epicBoonFeatCategories
                    if isinstance(category, FeatCategory)
                ),
            ),),
        )
    fighting_style_definition = next(
        (
            definition
            for definition in CLASS_PROGRESSION_DEFINITIONS.values()
            if definition.fightingStyleChoice == choice_id
        ),
        None,
    )
    if fighting_style_definition is not None:
        fighter = next(
            (entry for entry in classes if entry.name == fighting_style_definition.characterClass),
            None,
        )
        class_level = next_fighting_style_level(
            fighter,
            choice_id,
            progression_grants or [],
        )
        if fighter is None or class_level is None:
            return None
        presentation = fighting_style_definition.fightingStylePresentation
        if presentation is None:
            raise ValueError("Fighting Style choice requires presentation metadata")
        return ProgressionRule(
            choice_id,
            presentation,
            (ClassLevelRequirement(
                fighting_style_definition.characterClass,
                class_level,
                fighting_style_required_subclass(fighter, class_level),
            ),),
            (feat_choice_definition(
                fighting_style_definition.characterClass,
                class_level,
                tuple(
                    category
                    for category in fighting_style_definition.fightingStyleFeatCategories
                    if isinstance(category, FeatCategory)
                ),
            ),),
        )
    class_option_definition = next(
        (
            definition
            for definition in CLASS_OPTION_PROGRESSION_DEFINITIONS
            if definition.choice == choice_id
        ),
        None,
    )
    if class_option_definition is not None:
        fighter = next(
            (entry for entry in classes if entry.name == class_option_definition.characterClass),
            None,
        )
        if fighter is None:
            return None
        grant_levels = list(
            class_option_definition.grant_levels_at_level(fighter.level)
            if class_option_definition.grantSubclass is None
            or fighter.subclass == class_option_definition.grantSubclass
            else ()
        )
        additional_style = class_option_definition.additionalFightingStyle
        if additional_style is not None and has_fighting_style(fighter, additional_style):
            grant_levels.append(next(
                (
                    grant.minimumClassLevel
                    for record in progression_grants or []
                    for grant in record.grants
                    if isinstance(grant, FightingStyleGrant)
                    and grant.style == additional_style
                ),
                1,
            ))
        choice = ClassOptionChoiceDefinition(
            characterClass=class_option_definition.characterClass,
            kind=class_option_definition.kind,
            candidates=class_option_definition.candidates_at_level(fighter.level),
            candidateLabels=class_option_definition.candidateLabels,
            count=len(grant_levels),
            grantMinimumLevels=tuple(sorted(grant_levels)),
        )
        return ProgressionRule(
            choice_id,
            class_option_definition.presentation,
            (ClassLevelRequirement(
                class_option_definition.characterClass,
                class_option_definition.minimumLevel,
                class_option_definition.requiredSubclass,
            ),),
            (choice,),
        )
    subclass_definition = next(
        (
            definition
            for definition in CLASS_PROGRESSION_DEFINITIONS.values()
            if definition.subclassChoice == choice_id
        ),
        None,
    )
    if subclass_definition is not None:
        subclass_class = subclass_definition.characterClass
        presentation = subclass_definition.subclassPresentation
        if presentation is None:
            raise ValueError("Subclass choice requires presentation metadata")
        return ProgressionRule(
            choice_id,
            presentation,
            (ClassLevelRequirement(subclass_class, subclass_definition.subclassLevel),),
            (SubclassChoiceDefinition(subclass_class, subclass_definition.subclasses),),
        )
    configured_skill = next(
        (
            (definition, skill_choice)
            for definition in CLASS_PROGRESSION_DEFINITIONS.values()
            for skill_choice in definition.skillChoices
            if skill_choice.choice == choice_id
        ),
        None,
    )
    if configured_skill is not None:
        definition, skill_choice = configured_skill
        class_type = definition.characterClass
        character_class = next((entry for entry in classes if entry.name == class_type), None)
        class_level = character_class.level if character_class is not None else 0
        candidates = skill_choice.candidates
        if skill_choice.requiresExistingProficiency:
            eligible = rogue_expertise_eligible_skill_keys(skills)
            candidates = tuple(skill for skill in candidates if enum_key(skill) in eligible)
        configured_count = skill_choice.count_at_level(class_level)
        count = min(configured_count, len(candidates)) if class_level >= 1 else 0
        return ProgressionRule(
            choice_id,
            skill_choice.presentation,
            (ClassLevelRequirement(class_type, 1),),
            (SkillChoiceDefinition(
                candidates,
                count,
                skill_choice.proficiency,
                skill_choice.requiresExistingProficiency,
                skill_choice.grantMinimumLevels,
            ),),
        )
    configured_spells = next(
        (
            (character_class, spell_choices)
            for character_class, spell_choices in SPELL_PROGRESSION_DEFINITIONS
            if spell_choices.choice == choice_id
        ),
        None,
    )
    if configured_spells is not None:
        class_type, spell_choices = configured_spells
        character_class = next(
            (entry for entry in classes if entry.name == class_type),
            None,
        )
        class_level = character_class.level if character_class is not None else 0
        return ProgressionRule(
            choice_id,
            spell_choices.presentation,
            (ClassLevelRequirement(
                class_type,
                spell_choices.minimumLevel,
                spell_choices.requiredSubclass,
            ),),
            tuple(choice.at_level(class_level) for choice in spell_choices.choices),
        )
    return None


def next_hit_point_progression_target(
    classes: list[CharacterClassLevel],
    records: list[ProgressionGrantRecord],
) -> tuple[CharacterClassLevel, int] | None:
    granted_levels = {
        (grant.characterClass, grant.minimumClassLevel)
        for record in records
        for grant in record.grants
        if isinstance(grant, HitPointGrant)
    }
    for index, character_class in enumerate(classes):
        first_increase_level = 2 if index == 0 else 1
        for class_level in range(first_increase_level, character_class.level + 1):
            if (character_class.name, class_level) not in granted_levels:
                return character_class, class_level
    return None


def feat_choice_definition(
    character_class: ClassType,
    class_level: int,
    categories: tuple[FeatCategory, ...],
) -> FeatChoiceDefinition:
    general_candidates = tuple(
        feat_type
        for feat_type in GENERAL_FEATS
        if general_feat_category(feat_type) in categories
    )
    fighting_style_candidates = (
        tuple(FIGHTING_STYLE_FEATS)
        if FeatCategory.FIGHTING_STYLE in categories
        else ()
    )
    return FeatChoiceDefinition(
        characterClass=character_class,
        classLevel=class_level,
        categories=categories,
        candidates=(*general_candidates, *fighting_style_candidates),
    )


def progression_grant_source(rule: ProgressionRule) -> ProgressionGrantSource:
    requirement = rule.requirements[0]
    return ProgressionGrantSource(
        rule.id,
        requirement.characterClass,
        requirement.subclass,
    )


def next_ability_score_improvement_level(
    choice_id: ProgressionChoiceId,
    character_class: ClassType,
    classes: list[CharacterClassLevel],
    records: list[ProgressionGrantRecord],
) -> int | None:
    class_entry = next(
        (entry for entry in classes if entry.name == character_class),
        None,
    )
    if class_entry is None:
        return None
    granted_levels = {
        grant.minimumClassLevel
        for record in records
        if record.source.rule == choice_id
        for grant in record.grants
        if isinstance(grant, (AbilityScoreGrant, FeatGrant))
    }
    return next(
        (
            level
            for level in CLASS_PROGRESSION_DEFINITIONS[character_class].abilityScoreImprovementLevels
            if level <= class_entry.level and level not in granted_levels
        ),
        None,
    )


def fighting_style_acquisition_levels(
    fighter: CharacterClassLevel | None,
) -> tuple[int, ...]:
    if fighter is None:
        return ()
    return tuple(
        entitlement.minimumLevel
        for entitlement in fighter_fighting_style_entitlements(fighter)
    )


def fighting_style_required_subclass(
    fighter: CharacterClassLevel,
    class_level: int,
) -> FighterSubclassType | None:
    return next(
        (
            entitlement.requiredSubclass
            for entitlement in fighter_fighting_style_entitlements(fighter)
            if entitlement.minimumLevel == class_level
        ),
        None,
    )


def next_fighting_style_level(
    fighter: CharacterClassLevel | None,
    choice_id: ProgressionChoiceId,
    records: list[ProgressionGrantRecord],
) -> int | None:
    if fighter is None:
        return None
    granted_levels = {
        grant.minimumClassLevel
        for record in records
        if record.source.rule == choice_id
        for grant in record.grants
        if isinstance(grant, FightingStyleGrant)
    }
    acquisition_levels = fighting_style_acquisition_levels(fighter)
    existing_style_count = len(selected_fighting_style_values([fighter]))
    granted_levels.update(acquisition_levels[:existing_style_count])
    return next(
        (
            level
            for level in acquisition_levels
            if level not in granted_levels
        ),
        None,
    )


def progression_requirements_met(
    rule: ProgressionRule,
    classes: list[CharacterClassLevel],
) -> bool:
    return all(
        any(
            character_class.name == requirement.characterClass
            and character_class.level >= requirement.minimumLevel
            and (requirement.subclass is None or character_class.subclass == requirement.subclass)
            for character_class in classes
        )
        for requirement in rule.requirements
    )


def evaluate_progression_rule(
    rule: ProgressionRule,
    classes: list[CharacterClassLevel],
    skills: dict[str, ProficiencyLevel],
    values: list[str],
    *,
    spellbook: list[SpellEntry] | None = None,
    constitution_modifier: int = 0,
    hit_point_bonus: int = 0,
    hit_die_result: int | None = None,
    ability_scores: AbilityScores | None = None,
    selected_feats: tuple[GeneralFeatType, ...] = (),
    selected_fighting_styles: tuple[FightingStyleType, ...] = (),
    feat_eligibility_sheet=None,
) -> ProgressionEvaluation:
    if not progression_requirements_met(rule, classes):
        raise ProgressionRuleViolation(SkillSelectionIssue.REQUIREMENT_NOT_MET)
    if rule.choices and all(isinstance(choice, SpellChoiceDefinition) for choice in rule.choices):
        return evaluate_spell_progression_choices(
            rule,
            tuple(choice for choice in rule.choices if isinstance(choice, SpellChoiceDefinition)),
            classes,
            values,
            spellbook or [],
        )
    if len(rule.choices) == 1 and isinstance(rule.choices[0], AbilityScoreChoiceDefinition):
        return evaluate_ability_score_progression_choice(
            rule,
            rule.choices[0],
            values,
            ability_scores or AbilityScores(10, 10, 10, 10, 10, 10),
            selected_feats=selected_feats,
            selected_fighting_styles=selected_fighting_styles,
            feat_eligibility_sheet=feat_eligibility_sheet,
        )
    if len(rule.choices) == 1 and isinstance(rule.choices[0], FeatChoiceDefinition):
        return evaluate_feat_progression_choice(
            rule,
            rule.choices[0],
            values,
            selected_feats=selected_feats,
            selected_fighting_styles=selected_fighting_styles,
            feat_eligibility_sheet=feat_eligibility_sheet,
        )
    if len(rule.choices) == 1 and isinstance(rule.choices[0], ClassOptionChoiceDefinition):
        return evaluate_class_option_progression_choice(
            rule,
            rule.choices[0],
            values,
        )
    if len(rule.choices) == 1 and isinstance(rule.choices[0], HitPointChoiceDefinition):
        return evaluate_hit_point_progression_choice(
            rule,
            rule.choices[0],
            values,
            constitution_modifier=constitution_modifier,
            hit_point_bonus=hit_point_bonus,
            hit_die_result=hit_die_result,
        )
    if len(rule.choices) == 1 and isinstance(rule.choices[0], SubclassChoiceDefinition):
        return evaluate_subclass_progression_choice(rule, rule.choices[0], values)
    if len(rule.choices) != 1:
        raise ValueError("Progression rules require exactly one homogeneous choice family")
    choice = rule.choices[0]
    selected = [
        skill
        for value in dict.fromkeys(value.strip() for value in values if value.strip())
        if (skill := enum_value(SkillType, value)) is not None
    ]
    if len(selected) != choice.count or len(selected) != len(set(selected)):
        raise ProgressionRuleViolation(SkillSelectionIssue.WRONG_COUNT)
    if any(skill not in choice.candidates for skill in selected):
        issue = (
            SkillSelectionIssue.REQUIRES_PROFICIENCY
            if choice.requiresExistingProficiency
            else SkillSelectionIssue.INVALID_OPTION
        )
        raise ProgressionRuleViolation(issue)
    return ProgressionEvaluation(
        source=progression_grant_source(rule),
        grants=tuple(
            SkillProficiencyGrant(
                skill,
                choice.proficiency,
                (
                    choice.grantMinimumLevels[index]
                    if index < len(choice.grantMinimumLevels)
                    else 1
                ),
            )
            for index, skill in enumerate(selected)
        ),
    )


def evaluate_ability_score_progression_choice(
    rule: ProgressionRule,
    choice: AbilityScoreChoiceDefinition,
    values: list[str],
    ability_scores: AbilityScores,
    *,
    selected_feats: tuple[GeneralFeatType, ...] = (),
    selected_fighting_styles: tuple[FightingStyleType, ...] = (),
    feat_eligibility_sheet=None,
) -> ProgressionEvaluation:
    clean_values = [value.strip() for value in values if value.strip()]
    if (
        choice.featChoice is not None
        and len(clean_values) == 1
        and clean_values[0].lower().startswith(ProgressionSelectionPrefix.FEAT.value)
    ):
        return evaluate_feat_progression_choice(
            rule,
            choice.featChoice,
            [clean_values[0][len(ProgressionSelectionPrefix.FEAT.value):]],
            selected_feats=selected_feats,
            selected_fighting_styles=selected_fighting_styles,
            feat_eligibility_sheet=feat_eligibility_sheet,
        )
    if len(clean_values) == 1:
        clean_values.append(clean_values[0])
    if len(clean_values) != choice.points:
        raise ProgressionRuleViolation(SkillSelectionIssue.WRONG_COUNT)
    selected = [enum_value(AbilityType, value) for value in clean_values]
    if any(ability is None or ability not in choice.candidates for ability in selected):
        raise ProgressionRuleViolation(SkillSelectionIssue.INVALID_OPTION)
    grants: list[AbilityScoreGrant] = []
    for ability in choice.candidates:
        requested = selected.count(ability)
        if requested <= 0:
            continue
        current = getattr(ability_scores, enum_key(ability))
        amount = min(requested, max(0, choice.scoreCap - current))
        if amount > 0:
            grants.append(AbilityScoreGrant(
                choice.characterClass,
                choice.classLevel,
                ability,
                amount,
            ))
    if not grants:
        raise ProgressionRuleViolation(SkillSelectionIssue.INVALID_OPTION)
    return ProgressionEvaluation(
        source=progression_grant_source(rule),
        grants=tuple(grants),
    )


def evaluate_feat_progression_choice(
    rule: ProgressionRule,
    choice: FeatChoiceDefinition,
    values: list[str],
    *,
    selected_feats: tuple[GeneralFeatType, ...] = (),
    selected_fighting_styles: tuple[FightingStyleType, ...] = (),
    feat_eligibility_sheet=None,
) -> ProgressionEvaluation:
    clean_values = list(dict.fromkeys(value.strip() for value in values if value.strip()))
    if len(clean_values) != choice.count:
        raise ProgressionRuleViolation(SkillSelectionIssue.WRONG_COUNT)
    grants: list[FeatGrant | FightingStyleGrant] = []
    for value in clean_values:
        general_feat = enum_value(GeneralFeatType, value)
        fighting_style = enum_value(FightingStyleType, value)
        if general_feat is not None:
            if general_feat not in choice.candidates:
                raise ProgressionRuleViolation(SkillSelectionIssue.INVALID_FEAT_CATEGORY)
            definition = GENERAL_FEATS[general_feat]
            if general_feat_category(general_feat) not in choice.categories:
                raise ProgressionRuleViolation(SkillSelectionIssue.INVALID_FEAT_CATEGORY)
            if not definition.repeatable and general_feat in selected_feats:
                raise ProgressionRuleViolation(SkillSelectionIssue.FEAT_ALREADY_SELECTED)
            if (
                feat_eligibility_sheet is not None
                and not general_feat_prerequisites_met(general_feat, feat_eligibility_sheet)
            ):
                raise ProgressionRuleViolation(SkillSelectionIssue.FEAT_PREREQUISITE_NOT_MET)
            grants.append(FeatGrant(choice.characterClass, choice.classLevel, general_feat))
            continue
        if fighting_style is not None:
            if fighting_style not in choice.candidates:
                raise ProgressionRuleViolation(SkillSelectionIssue.INVALID_FEAT_CATEGORY)
            definition = FIGHTING_STYLE_FEATS[fighting_style]
            if FeatCategory.FIGHTING_STYLE not in choice.categories:
                raise ProgressionRuleViolation(SkillSelectionIssue.INVALID_FEAT_CATEGORY)
            if not definition.repeatable and fighting_style in selected_fighting_styles:
                raise ProgressionRuleViolation(SkillSelectionIssue.FEAT_ALREADY_SELECTED)
            grants.append(FightingStyleGrant(
                choice.characterClass,
                choice.classLevel,
                fighting_style,
            ))
            continue
        raise ProgressionRuleViolation(SkillSelectionIssue.INVALID_FEAT)
    return ProgressionEvaluation(
        source=progression_grant_source(rule),
        grants=tuple(grants),
    )


def evaluate_class_option_progression_choice(
    rule: ProgressionRule,
    choice: ClassOptionChoiceDefinition,
    values: list[str],
) -> ProgressionEvaluation:
    clean_values = list(dict.fromkeys(value.strip() for value in values if value.strip()))
    if len(clean_values) != choice.count:
        raise ProgressionRuleViolation(SkillSelectionIssue.WRONG_COUNT)
    candidates_by_key = {enum_key(option): option for option in choice.candidates}
    selected = [candidates_by_key.get(value) for value in clean_values]
    if any(option is None or option not in choice.candidates for option in selected):
        raise ProgressionRuleViolation(SkillSelectionIssue.INVALID_OPTION)
    return ProgressionEvaluation(
        source=progression_grant_source(rule),
        grants=tuple(
            ClassOptionGrant(
                characterClass=choice.characterClass,
                minimumClassLevel=choice.grantMinimumLevels[index],
                kind=choice.kind,
                option=option,
            )
            for index, option in enumerate(selected)
            if option is not None
        ),
    )


def evaluate_hit_point_progression_choice(
    rule: ProgressionRule,
    choice: HitPointChoiceDefinition,
    values: list[str],
    *,
    constitution_modifier: int,
    hit_point_bonus: int,
    hit_die_result: int | None,
) -> ProgressionEvaluation:
    clean_values = list(dict.fromkeys(value.strip() for value in values if value.strip()))
    if len(clean_values) != 1:
        raise ProgressionRuleViolation(SkillSelectionIssue.WRONG_COUNT)
    selected = enum_value(HitPointChoiceOption, clean_values[0])
    if selected is None:
        raise ProgressionRuleViolation(SkillSelectionIssue.INVALID_OPTION)
    if selected == HitPointChoiceOption.ROLL:
        if hit_die_result is None or not 1 <= hit_die_result <= choice.hitDie:
            raise ProgressionRuleViolation(SkillSelectionIssue.INVALID_OPTION)
        die_result = hit_die_result
    else:
        die_result = choice.hitDie // 2 + 1
    amount = max(1, die_result + constitution_modifier + hit_point_bonus)
    return ProgressionEvaluation(
        source=progression_grant_source(rule),
        grants=(HitPointGrant(
            characterClass=choice.characterClass,
            minimumClassLevel=choice.classLevel,
            choice=selected,
            amount=amount,
            hitDieResult=die_result,
        ),),
    )


def evaluate_subclass_progression_choice(
    rule: ProgressionRule,
    choice: SubclassChoiceDefinition,
    values: list[str],
) -> ProgressionEvaluation:
    clean_values = list(dict.fromkeys(value.strip() for value in values if value.strip()))
    if len(clean_values) != choice.count:
        raise ProgressionRuleViolation(SkillSelectionIssue.WRONG_COUNT)
    selected = [
        next(
            (option for option in choice.candidates if enum_value(type(option), value) == option),
            None,
        )
        for value in clean_values
    ]
    if any(candidate is None for candidate in selected):
        raise ProgressionRuleViolation(SkillSelectionIssue.INVALID_OPTION)
    selected_subclass = selected[0]
    if selected_subclass is None:
        raise ProgressionRuleViolation(SkillSelectionIssue.INVALID_OPTION)
    return ProgressionEvaluation(
        source=progression_grant_source(rule),
        grants=(SubclassGrant(choice.characterClass, selected_subclass),),
    )


def evaluate_spell_progression_choices(
    rule: ProgressionRule,
    choices: tuple[SpellChoiceDefinition, ...],
    classes: list[CharacterClassLevel],
    values: list[str],
    spellbook: list[SpellEntry],
) -> ProgressionEvaluation:
    selected = [
        spell_id
        for value in dict.fromkeys(value.strip() for value in values if value.strip())
        if (spell_id := enum_value(SpellId, value)) is not None
    ]
    if len(selected) != sum(choice.count for choice in choices) or len(selected) != len(set(selected)):
        raise ProgressionRuleViolation(SkillSelectionIssue.WRONG_COUNT)
    grants: list[SpellGrant] = []
    assigned: set[SpellId] = set()
    for choice in choices:
        if len(spellbook) < choice.minimumPoolSize:
            raise ProgressionRuleViolation(SkillSelectionIssue.REQUIREMENT_NOT_MET)
        candidates = spell_choice_candidates(choice, classes, spellbook)
        candidates_by_id = {spell.id: spell for spell in candidates}
        segment = [spell_id for spell_id in selected if spell_id in candidates_by_id]
        if len(segment) != choice.count:
            raise ProgressionRuleViolation(SkillSelectionIssue.INVALID_OPTION)
        if any(required not in segment for required in choice.requiredSpells):
            raise ProgressionRuleViolation(SkillSelectionIssue.INVALID_OPTION)
        if choice.unrestrictedCount is not None and choice.preferredSchools:
            unrestricted = sum(
                1
                for spell_id in segment
                if candidates_by_id[spell_id].school not in choice.preferredSchools
            )
            if unrestricted > choice.unrestrictedCount:
                raise ProgressionRuleViolation(SkillSelectionIssue.INVALID_OPTION)
        assigned.update(segment)
        grants.extend(
            SpellGrant(
                spell=spell_id,
                destination=choice.destination,
                source=choice.source,
                category=spell_choice_level_category(choice),
                minimumClassLevel=(
                    choice.grantMinimumLevels[index]
                    if index < len(choice.grantMinimumLevels)
                    else 1
                ),
            )
            for index, spell_id in enumerate(segment)
        )
    if assigned != set(selected):
        raise ProgressionRuleViolation(SkillSelectionIssue.INVALID_OPTION)
    return ProgressionEvaluation(
        source=progression_grant_source(rule),
        grants=tuple(grants),
    )


def spell_choice_candidates(
    choice: SpellChoiceDefinition,
    classes: list[CharacterClassLevel],
    spellbook: list[SpellEntry],
) -> list[SpellEntry]:
    if (
        choice.pool == SpellPool.CHARACTER_COLLECTION
        and choice.poolCollection == SpellCollection.SPELLBOOK
    ):
        candidates = list(spellbook)
    elif choice.pool == SpellPool.CLASS_SPELL_LIST and choice.poolClass is not None:
        from dnd_board.rules.spells import class_spell_entries, normalized_spell_entry, spell_entry

        catalog = {
            spell.id: spell
            for spell in class_spell_entries(
            choice.poolClass,
            source=choice.source,
            casting_ability=choice.castingAbility,
            maximum_level=choice.maximumSpellLevel,
            )
        }
        for spell_id in choice.supplementalSpells:
            supplemental = spell_entry(spell_id)
            if supplemental is None:
                continue
            if choice.maximumSpellLevel is not None and supplemental.level > choice.maximumSpellLevel:
                continue
            catalog[spell_id] = normalized_spell_entry(
                supplemental,
                source=choice.source,
                casting_ability=choice.castingAbility,
            )
        for supplemental in choice.supplementalSpellEntries:
            if choice.maximumSpellLevel is not None and supplemental.level > choice.maximumSpellLevel:
                continue
            catalog[supplemental.id] = normalized_spell_entry(
                supplemental,
                source=choice.source,
                casting_ability=choice.castingAbility,
            )
        candidates = list(catalog.values())
    else:
        return []
    if SpellConstraint.CANTRIP in choice.constraints:
        candidates = [spell for spell in candidates if spell.level == 0]
    if SpellConstraint.NON_CANTRIP in choice.constraints:
        candidates = [spell for spell in candidates if spell.level > 0]
    if SpellConstraint.WITHIN_AVAILABLE_SPELL_LEVEL in choice.constraints:
        maximum_level = choice.maximumSpellLevel or 0
        candidates = [spell for spell in candidates if spell.level <= maximum_level]
    return candidates


def spell_choice_level_category(
    choice: SpellChoiceDefinition,
) -> SpellLevelCategory:
    if SpellConstraint.CANTRIP in choice.constraints:
        return SpellLevelCategory.CANTRIP
    return SpellLevelCategory.LEVELED


def spell_grant_scopes(
    records: list[ProgressionGrantRecord],
) -> set[SpellGrantScope]:
    return {
        SpellGrantScope(grant.destination, grant.source, grant.category)
        for record in records
        for grant in record.grants
        if isinstance(grant, SpellGrant)
    }


def active_spell_progression_entries(
    records: list[ProgressionGrantRecord],
    classes: list[CharacterClassLevel],
    skills: dict[str, ProficiencyLevel],
    spellbook: list[SpellEntry],
    *,
    destination: SpellCollection,
) -> list[tuple[SpellGrant, SpellEntry]]:
    active: list[tuple[SpellGrant, SpellEntry]] = []
    for record in records:
        rule = progression_rule(record.source.rule, classes, skills)
        if rule is None or not progression_requirements_met(rule, classes):
            continue
        for choice in rule.choices:
            if not isinstance(choice, SpellChoiceDefinition) or choice.destination != destination:
                continue
            candidates = spell_choice_candidates(choice, classes, spellbook)
            candidates_by_id = {spell.id: spell for spell in candidates}
            matching = [
                grant
                for grant in record.grants
                if isinstance(grant, SpellGrant)
                and grant.destination == choice.destination
                and grant.source == choice.source
                and grant.category == spell_choice_level_category(choice)
                and grant.spell in candidates_by_id
                and spell_grant_matches_choice(grant, choice, candidates_by_id)
            ]
            active.extend(
                (grant, candidates_by_id[grant.spell])
                for grant in matching[:choice.count]
            )
    return active


def spell_grant_matches_choice(
    grant: SpellGrant,
    choice: SpellChoiceDefinition,
    candidates_by_id: dict[SpellId, SpellEntry],
) -> bool:
    spell = candidates_by_id[grant.spell]
    if SpellConstraint.CANTRIP in choice.constraints:
        return spell.level == 0
    if SpellConstraint.NON_CANTRIP in choice.constraints:
        return spell.level > 0
    return True


def apply_progression_grants(
    base_skills: dict[str, ProficiencyLevel],
    records: list[ProgressionGrantRecord],
) -> dict[str, ProficiencyLevel]:
    skills = dict(base_skills)
    proficiency_rank = {
        ProficiencyLevel.NONE: 0,
        ProficiencyLevel.PROFICIENT: 1,
        ProficiencyLevel.EXPERTISE: 2,
    }
    for record in records:
        for grant in record.grants:
            if not isinstance(grant, SkillProficiencyGrant):
                continue
            current = skills.get(enum_key(grant.skill), ProficiencyLevel.NONE)
            if proficiency_rank[grant.proficiency] > proficiency_rank[current]:
                skills[enum_key(grant.skill)] = grant.proficiency
    return skills


def subclass_grant_classes(
    records: list[ProgressionGrantRecord],
) -> set[ClassType]:
    return {
        grant.characterClass
        for record in records
        for grant in record.grants
        if isinstance(grant, SubclassGrant)
    }


def hit_point_grant_total(records: list[ProgressionGrantRecord]) -> int:
    return sum(
        grant.amount
        for record in records
        for grant in record.grants
        if isinstance(grant, HitPointGrant)
    )


def apply_ability_score_progression_grants(
    base_scores: AbilityScores,
    records: list[ProgressionGrantRecord],
    score_cap: int = 20,
) -> AbilityScores:
    scores = AbilityScores(
        strength=base_scores.strength,
        dexterity=base_scores.dexterity,
        constitution=base_scores.constitution,
        intelligence=base_scores.intelligence,
        wisdom=base_scores.wisdom,
        charisma=base_scores.charisma,
    )
    for record in records:
        for grant in record.grants:
            if not isinstance(grant, AbilityScoreGrant):
                continue
            ability_key = enum_key(grant.ability)
            setattr(
                scores,
                ability_key,
                min(score_cap, getattr(scores, ability_key) + grant.amount),
            )
    return scores


def progression_feat_grants(
    records: list[ProgressionGrantRecord],
) -> list[FeatGrant]:
    return [
        grant
        for record in records
        for grant in record.grants
        if isinstance(grant, FeatGrant)
    ]


def progression_fighting_style_grants(
    records: list[ProgressionGrantRecord],
) -> list[FightingStyleGrant]:
    return [
        grant
        for record in records
        for grant in record.grants
        if isinstance(grant, FightingStyleGrant)
    ]


def progression_class_option_grants(
    records: list[ProgressionGrantRecord],
    kind: ClassOptionKind,
) -> list[ClassOptionGrant]:
    return [
        grant
        for record in records
        for grant in record.grants
        if isinstance(grant, ClassOptionGrant) and grant.kind == kind
    ]


def progression_grants_share_entitlement(
    first: CharacterGrant,
    second: CharacterGrant,
) -> bool:
    if isinstance(first, (AbilityScoreGrant, FeatGrant)) and isinstance(second, (AbilityScoreGrant, FeatGrant)):
        return (
            first.characterClass == second.characterClass
            and first.minimumClassLevel == second.minimumClassLevel
        )
    if isinstance(first, HitPointGrant) and isinstance(second, HitPointGrant):
        return (
            first.characterClass == second.characterClass
            and first.minimumClassLevel == second.minimumClassLevel
        )
    if isinstance(first, FightingStyleGrant) and isinstance(second, FightingStyleGrant):
        return (
            first.characterClass == second.characterClass
            and first.minimumClassLevel == second.minimumClassLevel
        )
    if isinstance(first, ClassOptionGrant) and isinstance(second, ClassOptionGrant):
        return (
            first.characterClass == second.characterClass
            and first.kind == second.kind
            and first.minimumClassLevel == second.minimumClassLevel
        )
    return False


def replace_progression_grant_record(
    records: list[ProgressionGrantRecord],
    evaluation: ProgressionEvaluation,
) -> tuple[list[ProgressionGrantRecord], ProgressionGrantRecord | None]:
    previous = next(
        (record for record in records if record.source == evaluation.source),
        None,
    )
    grants = evaluation.grants
    if grants and isinstance(
        grants[0],
        (AbilityScoreGrant, ClassOptionGrant, FeatGrant, FightingStyleGrant, HitPointGrant),
    ):
        retained = tuple(
            grant
            for grant in (previous.grants if previous is not None else ())
            if not any(
                progression_grants_share_entitlement(grant, candidate)
                for candidate in grants
            )
        )
        grants = (*retained, *grants)
    replaced = [record for record in records if record.source != evaluation.source]
    replaced.append(ProgressionGrantRecord(evaluation.source, grants))
    return replaced, previous


def apply_fighting_style_progression_grants(
    classes: list[CharacterClassLevel],
    previous_records: list[ProgressionGrantRecord],
    records: list[ProgressionGrantRecord],
) -> list[CharacterClassLevel]:
    next_classes = [copy_character_class(character_class) for character_class in classes]
    for character_class in next_classes:
        previous_styles = {
            grant.style
            for grant in progression_fighting_style_grants(previous_records)
            if grant.characterClass == character_class.name
        }
        granted_styles = [
            grant.style
            for grant in progression_fighting_style_grants(records)
            if grant.characterClass == character_class.name
        ]
        if not previous_styles and not granted_styles:
            continue
        current = list(character_class.fightingStyles or ())
        if character_class.fightingStyle is not None:
            current.append(character_class.fightingStyle)
        retained = [style for style in current if style not in previous_styles]
        character_class.fightingStyle = None
        character_class.fightingStyles = list(dict.fromkeys([
            *retained,
            *granted_styles,
        ])) or None
    return next_classes


def apply_class_option_progression_grants(
    classes: list[CharacterClassLevel],
    previous_records: list[ProgressionGrantRecord],
    records: list[ProgressionGrantRecord],
) -> list[CharacterClassLevel]:
    next_classes = [copy_character_class(character_class) for character_class in classes]
    for character_class in next_classes:
        previous_options = {
            (grant.kind, grant.option)
            for record in previous_records
            for grant in record.grants
            if isinstance(grant, ClassOptionGrant)
            and grant.characterClass == character_class.name
        }
        granted_options = [
            ClassOptionSelection(grant.kind, grant.option)
            for record in records
            for grant in record.grants
            if isinstance(grant, ClassOptionGrant)
            and grant.characterClass == character_class.name
        ]
        if not previous_options and not granted_options:
            continue
        retained = [
            selection
            for selection in character_class.classOptions or []
            if (selection.kind, selection.option) not in previous_options
        ]
        character_class.classOptions = list(dict.fromkeys([
            *retained,
            *granted_options,
        ])) or None
    return next_classes


def apply_subclass_progression_grants(
    classes: list[CharacterClassLevel],
    records: list[ProgressionGrantRecord],
    managed_classes: set[ClassType],
) -> list[CharacterClassLevel]:
    next_classes = [copy_character_class(character_class) for character_class in classes]
    for character_class in next_classes:
        if character_class.name in managed_classes:
            character_class.subclass = None
    for record in records:
        for grant in record.grants:
            if not isinstance(grant, SubclassGrant):
                continue
            character_class = next(
                (entry for entry in next_classes if entry.name == grant.characterClass),
                None,
            )
            if (
                character_class is not None
                and character_class.level >= grant.minimumClassLevel
                and subclass_matches_class(grant.subclass, grant.characterClass)
            ):
                character_class.subclass = grant.subclass
    return prune_progression_choices(next_classes)


def subclass_matches_class(subclass: SubclassType, character_class: ClassType) -> bool:
    definition = CLASS_PROGRESSION_DEFINITIONS.get(character_class)
    return definition is not None and subclass in definition.subclasses


def reconcile_progression_grant_records(
    base_skills: dict[str, ProficiencyLevel],
    records: list[ProgressionGrantRecord],
    classes: list[CharacterClassLevel],
) -> list[ProgressionGrantRecord]:
    available_classes = {
        character_class.name: character_class.level
        for character_class in classes
    }
    active = []
    for record in records:
        rule = progression_rule(record.source.rule, classes, base_skills)
        if rule is not None and not progression_requirements_met(rule, classes):
            continue
        class_level = available_classes.get(record.source.characterClass, 0)
        required_subclass = (
            record.source.requiredSubclass
            or (rule.requirements[0].subclass if rule is not None else None)
        )
        subclass_requirement_met = required_subclass is None or any(
            character_class.name == record.source.characterClass
            and character_class.subclass == required_subclass
            for character_class in classes
        )
        grants: tuple[CharacterGrant, ...] = tuple(
            grant
            for grant in record.grants
            if class_level >= grant.minimumClassLevel
            and subclass_requirement_met
        )
        if (
            rule is not None
            and len(rule.choices) == 1
            and isinstance(rule.choices[0], ClassOptionChoiceDefinition)
        ):
            choice = rule.choices[0]
            class_option_grants = tuple(
                grant
                for grant in grants
                if isinstance(grant, ClassOptionGrant)
                and grant.kind == choice.kind
                and grant.option in choice.candidates
            )[:choice.count]
            grants = tuple(
                grant for grant in grants if not isinstance(grant, ClassOptionGrant)
            ) + class_option_grants
        if grants:
            active.append(ProgressionGrantRecord(record.source, grants))
    independent = [
        record
        for record in active
        if not (
            (rule := progression_rule(record.source.rule, classes, base_skills))
            and isinstance(rule.choices[0], SkillChoiceDefinition)
            and rule.choices[0].requiresExistingProficiency
        )
    ]
    prerequisite_skills = apply_progression_grants(base_skills, independent)
    dependent = [
        record
        for record in active
        if record not in independent
        and all(
            isinstance(grant, SkillProficiencyGrant)
            and
            prerequisite_skills.get(enum_key(grant.skill))
            in {ProficiencyLevel.PROFICIENT, ProficiencyLevel.EXPERTISE}
            for grant in record.grants
        )
    ]
    return [record for record in active if record in independent or record in dependent]


def progression_model_types() -> list[type[object]]:
    return [
        AbilityScoreChoiceDefinition,
        AbilityScoreGrant,
        ClassOptionChoiceDefinition,
        ClassOptionGrant,
        ClassOptionKind,
        ClassLevelRequirement,
        FeatCategory,
        FeatChoiceDefinition,
        FeatGrant,
        FightingStyleGrant,
        FightingStyleType,
        GeneralFeatType,
        HitPointChoiceOption,
        HitPointChoiceDefinition,
        HitPointGrant,
        ProgressionChoiceId,
        ProgressionChoicePresentation,
        ProgressionEvaluation,
        ProgressionGrantRecord,
        ProgressionGrantSource,
        ProgressionRule,
        ProgressionSelectionPrefix,
        SelectionReplacementPolicy,
        SkillChoiceDefinition,
        SkillProficiencyGrant,
        SpellChoiceDefinition,
        SpellCollection,
        SpellConstraint,
        SpellGrant,
        SpellGrantScope,
        SpellLevelCategory,
        SpellPool,
        SubclassChoiceDefinition,
        SubclassGrant,
    ]


def progression_choices(
    classes: list[CharacterClassLevel],
    spells: list[SpellEntry],
    skill_proficiencies: dict[str, ProficiencyLevel],
    feats: list[SheetFeature] | None = None,
    feat_eligibility_sheet=None,
    *,
    spellbook: list[SpellEntry] | None = None,
    progression_grants: list[ProgressionGrantRecord] | None = None,
) -> list[ProgressionChoice]:
    choices: list[ProgressionChoice] = []
    hit_point_rule = progression_rule(
        ProgressionChoiceId.HIT_POINT_INCREASE,
        classes,
        skill_proficiencies,
        progression_grants,
    )
    if hit_point_rule is not None:
        hit_point_choice = progression_choice_for_rule(
            hit_point_rule,
            skill_proficiencies,
            progression_grants,
            classes=classes,
        )
        if hit_point_choice is not None:
            choices.append(hit_point_choice)
    for choice_id in configured_progression_choice_ids():
        rule = progression_rule(
            choice_id,
            classes,
            skill_proficiencies,
            progression_grants,
        )
        if rule is not None:
            choice = progression_choice_for_rule(
                rule,
                skill_proficiencies,
                progression_grants,
                classes=classes,
                spells=spells,
                spellbook=spellbook,
                feats=feats,
                feat_eligibility_sheet=feat_eligibility_sheet,
            )
            if choice is not None:
                choices.append(choice)

    return choices


def update_class_level(classes: list[CharacterClassLevel], class_name: ClassType, delta: int) -> list[CharacterClassLevel]:
    next_classes = [copy_character_class(character_class) for character_class in classes]
    target = next((character_class for character_class in next_classes if character_class.name == class_name), None)
    if target is None:
        return next_classes
    target.level = max(MIN_CHARACTER_LEVEL, min(MAX_CHARACTER_LEVEL, target.level + delta))
    return prune_progression_choices(next_classes)


def prune_progression_choices(classes: list[CharacterClassLevel]) -> list[CharacterClassLevel]:
    for character_class in classes:
        character_class.level = max(MIN_CHARACTER_LEVEL, min(MAX_CHARACTER_LEVEL, character_class.level))
        definition = CLASS_PROGRESSION_DEFINITIONS.get(character_class.name)
        if definition is not None and character_class.level < definition.subclassLevel:
            character_class.subclass = None
    return classes


def total_character_level(classes: list[CharacterClassLevel]) -> int:
    return sum(character_class.level for character_class in classes)


def progression_choice_for_rule(
    rule: ProgressionRule,
    skills: dict[str, ProficiencyLevel],
    records: list[ProgressionGrantRecord] | None,
    *,
    classes: list[CharacterClassLevel] | None = None,
    spells: list[SpellEntry] | None = None,
    spellbook: list[SpellEntry] | None = None,
    feats: list[SheetFeature] | None = None,
    feat_eligibility_sheet=None,
) -> ProgressionChoice | None:
    if not progression_requirements_met(rule, classes or []):
        return None
    if len(rule.choices) == 1 and isinstance(rule.choices[0], HitPointChoiceDefinition):
        return hit_point_progression_choice(rule, rule.choices[0])
    if len(rule.choices) == 1 and isinstance(rule.choices[0], AbilityScoreChoiceDefinition):
        return ability_score_progression_choice(
            rule,
            rule.choices[0],
            feats,
            feat_eligibility_sheet,
        )
    if len(rule.choices) == 1 and isinstance(rule.choices[0], FeatChoiceDefinition):
        return feat_progression_choice(
            rule,
            rule.choices[0],
            feats,
            feat_eligibility_sheet,
            classes or [],
        )
    if len(rule.choices) == 1 and isinstance(rule.choices[0], ClassOptionChoiceDefinition):
        return class_option_progression_choice(
            rule,
            rule.choices[0],
            classes or [],
            records,
        )
    if rule.choices and all(isinstance(choice, SpellChoiceDefinition) for choice in rule.choices):
        return spell_progression_choice(
            rule,
            tuple(choice for choice in rule.choices if isinstance(choice, SpellChoiceDefinition)),
            classes or [],
            spells or [],
            spellbook or [],
            records,
        )
    if len(rule.choices) == 1 and isinstance(rule.choices[0], SubclassChoiceDefinition):
        return subclass_progression_choice(
            rule,
            rule.choices[0],
            classes or [],
            records,
        )
    if len(rule.choices) != 1:
        raise ValueError("Progression rules require exactly one homogeneous choice family")
    choice = rule.choices[0]
    if choice.count <= 0:
        return None
    record = next(
        (record for record in records or [] if record.source.rule == rule.id),
        None,
    )
    if records is not None and record is not None and len(record.grants) >= choice.count:
        return None
    if record is not None:
        selected = [enum_key(grant.skill) for grant in record.grants]
    else:
        selected = [
            enum_key(skill)
            for skill in choice.candidates
            if skills.get(enum_key(skill)) == choice.proficiency
            or (
                choice.proficiency == ProficiencyLevel.PROFICIENT
                and skills.get(enum_key(skill)) == ProficiencyLevel.EXPERTISE
            )
        ]
        if len(selected) >= choice.count:
            return None
    return multi_choice(
        choice_id=rule.id,
        choice_type=rule.presentation.choiceType,
        label=rule.presentation.label,
        description=rule.presentation.description,
        minimum=choice.count,
        maximum=choice.count,
        selected=selected,
        options=[
            ProgressionChoiceOption(value=enum_key(skill), label=enum_label(skill))
            for skill in choice.candidates
        ],
    )


def hit_point_progression_choice(
    rule: ProgressionRule,
    choice: HitPointChoiceDefinition,
) -> ProgressionChoice:
    return single_choice(
        choice_id=rule.id,
        choice_type=rule.presentation.choiceType,
        label=rule.presentation.label,
        description=rule.presentation.description,
        selected=[],
        options=hit_point_choice_options(),
    )


def ability_score_progression_choice(
    rule: ProgressionRule,
    choice: AbilityScoreChoiceDefinition,
    feats: list[SheetFeature] | None,
    feat_eligibility_sheet,
) -> ProgressionChoice:
    return single_choice(
        choice_id=rule.id,
        choice_type=rule.presentation.choiceType,
        label=rule.presentation.label,
        description=rule.presentation.description,
        selected=[],
        options=feat_choice_options(
            choice.featChoice,
            feats,
            feat_eligibility_sheet,
            [],
        ) if choice.featChoice is not None else [],
    )


def feat_progression_choice(
    rule: ProgressionRule,
    choice: FeatChoiceDefinition,
    feats: list[SheetFeature] | None,
    feat_eligibility_sheet,
    classes: list[CharacterClassLevel],
) -> ProgressionChoice:
    return single_choice(
        choice_id=rule.id,
        choice_type=rule.presentation.choiceType,
        label=rule.presentation.label,
        description=rule.presentation.description,
        selected=[],
        options=feat_choice_options(
            choice,
            feats,
            feat_eligibility_sheet,
            selected_fighting_style_values(classes),
        ),
    )


def class_option_progression_choice(
    rule: ProgressionRule,
    choice: ClassOptionChoiceDefinition,
    classes: list[CharacterClassLevel],
    records: list[ProgressionGrantRecord] | None,
) -> ProgressionChoice | None:
    if choice.count <= 0:
        return None
    character_class = next(
        (entry for entry in classes if entry.name == choice.characterClass),
        None,
    )
    if character_class is None:
        return None
    current_options = character_class.selected_options(choice.kind)
    record = next(
        (record for record in records or [] if record.source.rule == rule.id),
        None,
    )
    if record is not None:
        selected = [
            enum_key(grant.option)
            for grant in record.grants
            if isinstance(grant, ClassOptionGrant) and grant.kind == choice.kind
        ]
        if len(selected) >= choice.count:
            return None
    else:
        selected = selected_enum_keys(current_options)
        if len(selected) >= choice.count:
            return None
    return multi_choice(
        choice_id=rule.id,
        choice_type=rule.presentation.choiceType,
        label=rule.presentation.label,
        description=rule.presentation.description,
        minimum=choice.count,
        maximum=choice.count,
        selected=selected,
        options=[
            ProgressionChoiceOption(
                value=enum_key(option),
                label=dict(choice.candidateLabels).get(option, enum_label(option)),
            )
            for option in choice.candidates
        ],
    )


def feat_choice_options(
    choice: FeatChoiceDefinition,
    feats: list[SheetFeature] | None,
    feat_eligibility_sheet,
    selected_styles: list[FightingStyleType],
) -> list[ProgressionChoiceOption]:
    from dnd_board.rules.feats import selected_general_feat_types

    selected_feats = selected_general_feat_types(feats)
    options: list[ProgressionChoiceOption] = []
    for candidate in choice.candidates:
        if isinstance(candidate, GeneralFeatType):
            definition = GENERAL_FEATS[candidate]
            if not definition.repeatable and candidate in selected_feats:
                continue
            if feat_eligibility_sheet is not None and not general_feat_prerequisites_met(candidate, feat_eligibility_sheet):
                continue
            options.append(ProgressionChoiceOption(
                value=enum_key(candidate),
                label=enum_label(candidate),
            ))
        elif isinstance(candidate, FightingStyleType):
            definition = FIGHTING_STYLE_FEATS[candidate]
            if not definition.repeatable and candidate in selected_styles:
                continue
            options.append(ProgressionChoiceOption(
                value=enum_key(candidate),
                label=fighting_style_label(candidate),
            ))
    return options


def subclass_progression_choice(
    rule: ProgressionRule,
    choice: SubclassChoiceDefinition,
    classes: list[CharacterClassLevel],
    records: list[ProgressionGrantRecord] | None,
) -> ProgressionChoice | None:
    character_class = next(
        (entry for entry in classes if entry.name == choice.characterClass),
        None,
    )
    if character_class is None or character_class.subclass is not None:
        return None
    record = next(
        (entry for entry in records or [] if entry.source.rule == rule.id),
        None,
    )
    selected = [
        enum_key(grant.subclass)
        for grant in record.grants if isinstance(grant, SubclassGrant)
    ] if record is not None else []
    return single_choice(
        choice_id=rule.id,
        choice_type=rule.presentation.choiceType,
        label=rule.presentation.label,
        description=rule.presentation.description,
        selected=selected,
        options=[
            ProgressionChoiceOption(
                value=enum_key(subclass),
                label=(
                    fighter_subclass_label(subclass)
                    if isinstance(subclass, FighterSubclassType)
                    else (
                        rogue_subclass_label(subclass)
                        if isinstance(subclass, RogueSubclassType)
                        else wizard_subclass_label(subclass)
                    )
                ),
            )
            for subclass in choice.candidates
        ],
    )


def spell_progression_choice(
    rule: ProgressionRule,
    choices: tuple[SpellChoiceDefinition, ...],
    classes: list[CharacterClassLevel],
    spells: list[SpellEntry],
    spellbook: list[SpellEntry],
    records: list[ProgressionGrantRecord] | None,
) -> ProgressionChoice | None:
    total_count = sum(choice.count for choice in choices)
    if total_count <= 0 or any(len(spellbook) < choice.minimumPoolSize for choice in choices):
        return None
    record = next(
        (record for record in records or [] if record.source.rule == rule.id),
        None,
    )
    if record is not None:
        selected_ids = [
            grant.spell
            for grant in record.grants
            if isinstance(grant, SpellGrant)
            and any(
                grant.destination == choice.destination
                and grant.source == choice.source
                and grant.category == spell_choice_level_category(choice)
                for choice in choices
            )
        ]
    else:
        selected_ids = []
        for choice in choices:
            candidate_ids = {
                spell.id for spell in spell_choice_candidates(choice, classes, spellbook)
            }
            selected_ids.extend(
                spell.id
                for spell in spell_entries_for_collection(choice.destination, spells, spellbook)
                if spell.source == choice.source
                and spell.id in candidate_ids
            )
    try:
        evaluate_spell_progression_choices(
            rule,
            choices,
            classes,
            [enum_key(spell_id) for spell_id in selected_ids],
            spellbook,
        )
    except ProgressionRuleViolation:
        pass
    else:
        return None
    option_entries: list[SpellEntry] = []
    seen_options: set[SpellId] = set()
    for choice in choices:
        for spell in spell_choice_option_candidates(choice, classes, spellbook, selected_ids):
            if spell.id not in seen_options:
                option_entries.append(spell)
                seen_options.add(spell.id)
    return multi_choice(
        choice_id=rule.id,
        choice_type=rule.presentation.choiceType,
        label=rule.presentation.label,
        description=rule.presentation.description,
        minimum=total_count,
        maximum=total_count,
        selected=[enum_key(spell_id) for spell_id in selected_ids],
        options=[
            ProgressionChoiceOption(value=enum_key(spell.id), label=spell_option_label(spell))
            for spell in option_entries
        ],
    )


def spell_choice_option_candidates(
    choice: SpellChoiceDefinition,
    classes: list[CharacterClassLevel],
    spellbook: list[SpellEntry],
    selected_ids: list[SpellId],
) -> list[SpellEntry]:
    candidates = spell_choice_candidates(choice, classes, spellbook)
    if choice.unrestrictedCount is None or not choice.preferredSchools:
        return candidates
    candidates_by_id = {spell.id: spell for spell in candidates}
    unrestricted_used = sum(
        1
        for spell_id in selected_ids
        if spell_id in candidates_by_id
        and candidates_by_id[spell_id].school not in choice.preferredSchools
    )
    if unrestricted_used < choice.unrestrictedCount:
        return candidates
    return [
        spell
        for spell in candidates
        if spell.id in selected_ids or spell.school in choice.preferredSchools
    ]


def spell_entries_for_collection(
    collection: SpellCollection,
    spells: list[SpellEntry],
    spellbook: list[SpellEntry],
) -> list[SpellEntry]:
    if collection == SpellCollection.KNOWN:
        return list(spells)
    if collection == SpellCollection.PREPARED:
        return [spell for spell in spells if spell.level > 0]
    if collection == SpellCollection.SPELLBOOK:
        return list(spellbook)
    return []


def spell_option_label(spell: SpellEntry) -> str:
    level_label = progression_spell_option_label(SpellOptionLabel.CANTRIP) if spell.level == 0 else progression_spell_option_label(SpellOptionLabel.LEVEL, level=spell.level)
    return f"{level_label}: {enum_label(spell.name)}"


def hit_die_label(class_name: ClassType) -> str:
    return f"{enum_label(class_name)} d{class_hit_die(class_name)}"


def class_hit_die(class_name: ClassType) -> int:
    return CLASS_HIT_DICE[class_name]


def hit_point_choice_options() -> list[ProgressionChoiceOption]:
    return [
        ProgressionChoiceOption(value=hit_point_choice_option_value(HitPointChoiceOption.FIXED), label=hit_point_choice_option_label(HitPointChoiceOptionLabel.FIXED)),
        ProgressionChoiceOption(value=hit_point_choice_option_value(HitPointChoiceOption.ROLL), label=hit_point_choice_option_label(HitPointChoiceOptionLabel.ROLL)),
    ]


def hit_point_choice_option_value(option: HitPointChoiceOption) -> str:
    return option.value


def hit_point_choice_option_label(label: HitPointChoiceOptionLabel) -> str:
    return label.value


def progression_spell_option_label(label: SpellOptionLabel, **format_values: object) -> str:
    return label.value.format(**format_values)


def has_fighting_style(fighter: CharacterClassLevel, style: FightingStyleType) -> bool:
    return style == fighter.fightingStyle or style in (fighter.fightingStyles or [])


def single_choice(choice_id: ProgressionChoiceId, choice_type: ProgressionChoiceType, label: str, description: str, selected: list[str], options: list[ProgressionChoiceOption]) -> ProgressionChoice:
    return ProgressionChoice(choice_id_value(choice_id), choice_type, label, description, 1, 1, selected, options)


def multi_choice(
    choice_id: ProgressionChoiceId,
    choice_type: ProgressionChoiceType,
    label: str,
    description: str,
    minimum: int,
    maximum: int,
    selected: list[str],
    options: list[ProgressionChoiceOption],
) -> ProgressionChoice:
    return ProgressionChoice(choice_id_value(choice_id), choice_type, label, description, minimum, maximum, selected, options)


def parse_progression_choice_id(value: str) -> ProgressionChoiceId | None:
    normalized = value.strip().replace("-", "").replace("_", "").lower()
    for choice_id in ProgressionChoiceId:
        if normalized in {choice_id.value.lower(), choice_id.name.replace("_", "").lower()}:
            return choice_id
    return None


def choice_id_value(choice_id: ProgressionChoiceId) -> str:
    return choice_id.value


def enum_options(enum_type: type[Enum]) -> list[ProgressionChoiceOption]:
    return [ProgressionChoiceOption(value=enum_key(option), label=enum_label(option)) for option in enum_type]


def selected_enum_keys(values: list[Enum]) -> list[str]:
    selected: list[str] = []
    for value in values:
        key = enum_key(value)
        if key not in selected:
            selected.append(key)
    return selected


def parse_enum_values(enum_type: type[Enum], values: list[str]):
    parsed = []
    for value in values:
        enum_member = enum_value(enum_type, value)
        if enum_member is not None and enum_member not in parsed:
            parsed.append(enum_member)
    return parsed


def unique_values(values: list[str]) -> list[str]:
    unique: list[str] = []
    for value in values:
        if value not in unique:
            unique.append(value)
    return unique


def copy_character_class(character_class: CharacterClassLevel) -> CharacterClassLevel:
    return CharacterClassLevel(
        name=character_class.name,
        level=character_class.level,
        subclass=character_class.subclass,
        fightingStyle=character_class.fightingStyle,
        fightingStyles=list(character_class.fightingStyles) if character_class.fightingStyles else None,
        classOptions=list(character_class.classOptions) if character_class.classOptions else None,
    )
