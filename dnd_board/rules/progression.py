from __future__ import annotations

from enum import Enum

from dnd_board.character_sheet import (
    ArcaneShotType,
    BattleMasterManeuverType,
    CharacterClassLevel,
    ClassType,
    FightingStyleType,
    ProficiencyLevel,
    ProgressionChoice,
    ProgressionChoiceOption,
    ProgressionChoiceType,
    RuneType,
    SheetFeature,
    SkillType,
    SpellSource,
    SpellEntry,
    enum_key,
    enum_label,
    enum_value,
)
from dnd_board.rules.classes.fighter.archetypes import eldritch_knight_catalog_spell, eldritch_knight_spell_options, eldritch_knight_spellcasting, rune_minimum_level
from dnd_board.rules.classes.fighter.base import FighterSubclassType, fighter_subclass_label
from dnd_board.rules.classes.rogue.archetypes import arcane_trickster_spell_options, arcane_trickster_spellcasting
from dnd_board.rules.classes.rogue.base import RogueSubclassType, rogue_subclass_label
from dnd_board.rules.shared.combat_superiority import combat_superiority_subclass_progression


MIN_CHARACTER_LEVEL = 1
MAX_CHARACTER_LEVEL = 20


class ProgressionChoiceId(Enum):
    HIT_POINT_INCREASE = "hitPointIncrease"
    FIGHTER_ABILITY_SCORE_IMPROVEMENT = "fighterAbilityScoreImprovement"
    ROGUE_ABILITY_SCORE_IMPROVEMENT = "rogueAbilityScoreImprovement"
    FIGHTER_SKILL_PROFICIENCIES = "fighterSkillProficiencies"
    ROGUE_SKILL_PROFICIENCIES = "rogueSkillProficiencies"
    ROGUE_EXPERTISE = "rogueExpertise"
    FIGHTER_SUBCLASS = "fighterSubclass"
    ROGUE_SUBCLASS = "rogueSubclass"
    FIGHTER_FIGHTING_STYLES = "fighterFightingStyles"
    BATTLE_MASTER_MANEUVERS = "battleMasterManeuvers"
    ARCANE_ARCHER_SHOTS = "arcaneArcherShots"
    RUNE_KNIGHT_RUNES = "runeKnightRunes"
    ELDRITCH_KNIGHT_SPELLS = "eldritchKnightSpells"
    ARCANE_TRICKSTER_SPELLS = "arcaneTricksterSpells"


class ProgressionChoiceLabel(Enum):
    HIT_POINTS = "Hit Points"
    ABILITY_SCORE_IMPROVEMENT = "Ability Score Improvement"
    FIGHTER_SKILL_PROFICIENCIES = "Fighter Skill Proficiencies"
    ROGUE_SKILL_PROFICIENCIES = "Rogue Skill Proficiencies"
    ROGUE_EXPERTISE = "Expertise"
    FIGHTER_SUBCLASS = "Martial Archetype"
    ROGUE_SUBCLASS = "Roguish Archetype"
    FIGHTING_STYLE = "Fighting Style"
    BATTLE_MASTER_MANEUVERS = "Battle Master Maneuvers"
    ARCANE_SHOT_OPTIONS = "Arcane Shot Options"
    RUNE_KNIGHT_RUNES = "Rune Knight Runes"
    ELDRITCH_KNIGHT_SPELLS = "Eldritch Knight Spells"
    ARCANE_TRICKSTER_SPELLS = "Arcane Trickster Spells"


class ProgressionChoiceDescription(Enum):
    HIT_POINTS = "Choose fixed HP or roll the {hit_die_label} for this level. Constitution modifier is applied by the server."
    FIGHTER_ABILITY_SCORE_IMPROVEMENT = "Increase one ability score by 2, increase two ability scores by 1, or choose a feat. Optional Martial Versatility changes are not built yet."
    ROGUE_ABILITY_SCORE_IMPROVEMENT = "Increase one ability score by 2, increase two ability scores by 1, or choose a feat."
    FIGHTER_SKILL_PROFICIENCIES = "Choose Fighter skill proficiencies."
    ROGUE_SKILL_PROFICIENCIES = "Choose Rogue skill proficiencies."
    ROGUE_EXPERTISE = "Choose proficient skills to receive Expertise."
    FIGHTER_SUBCLASS = "Choose a Fighter Martial Archetype."
    ROGUE_SUBCLASS = "Choose a Rogue archetype."
    FIGHTING_STYLE = "Choose Fighter Fighting Style feats. These are not repeatable."
    BATTLE_MASTER_MANEUVERS = "Choose maneuvers known for Battle Master or Superior Technique."
    ARCANE_SHOT_OPTIONS = "Choose Arcane Shot options known."
    RUNE_KNIGHT_RUNES = "Choose runes known. Hill and Storm require Fighter level 7."
    ELDRITCH_KNIGHT_SPELLS = "Choose known Eldritch Knight cantrips and wizard spells from the curated starter catalog."
    ARCANE_TRICKSTER_SPELLS = "Choose Arcane Trickster cantrips and wizard spells from the curated starter catalog. Mage Hand is required."


class HitPointChoiceOption(Enum):
    FIXED = "fixed"
    ROLL = "roll"


class HitPointChoiceOptionLabel(Enum):
    FIXED = "Fixed"
    ROLL = "Roll"


class HitDieLabel(Enum):
    FIGHTER = "Fighter d10"
    ROGUE = "Rogue d8"


class HitDieValue(Enum):
    FIGHTER = 10
    ROGUE = 8


class SpellOptionLabel(Enum):
    CANTRIP = "Cantrip"
    LEVEL = "Level {level}"


def progression_choices(
    classes: list[CharacterClassLevel],
    spells: list[SpellEntry],
    hit_point_increases: list[int],
    ability_score_improvements: list[str],
    skill_proficiencies: dict[str, ProficiencyLevel],
    feats: list[SheetFeature] | None = None,
    feat_eligibility_sheet=None,
) -> list[ProgressionChoice]:
    fighter = fighter_class(classes)
    rogue = rogue_class(classes)

    choices: list[ProgressionChoice] = []
    expected_hit_point_increases = max(0, total_character_level(classes) - 1)
    if len(hit_point_increases) < expected_hit_point_increases:
        primary_class = classes[0].name if classes else ClassType.FIGHTER
        choices.append(single_choice(
            choice_id=ProgressionChoiceId.HIT_POINT_INCREASE,
            choice_type=ProgressionChoiceType.HIT_POINTS,
            label=progression_choice_label(ProgressionChoiceLabel.HIT_POINTS),
            description=hit_point_choice_description(primary_class),
            selected=[],
            options=hit_point_choice_options(),
        ))

    fighter_asi_count = fighter_asi_levels_up_to(fighter.level) if fighter is not None else 0
    rogue_asi_count = rogue_asi_levels_up_to(rogue.level) if rogue is not None else 0
    asi_count = fighter_asi_count + rogue_asi_count
    if fighter is not None and len(ability_score_improvements) < fighter_asi_count:
        from dnd_board.rules.feats import general_feat_options, selected_general_feat_keys

        choices.append(ProgressionChoice(
            id=choice_id_value(ProgressionChoiceId.FIGHTER_ABILITY_SCORE_IMPROVEMENT),
            choiceType=ProgressionChoiceType.ABILITY_SCORE_IMPROVEMENT,
            label=progression_choice_label(ProgressionChoiceLabel.ABILITY_SCORE_IMPROVEMENT),
            description=progression_choice_description(ProgressionChoiceDescription.FIGHTER_ABILITY_SCORE_IMPROVEMENT),
            minimum=asi_count,
            maximum=asi_count,
            selected=[*ability_score_improvements, *selected_general_feat_keys(feats)],
            options=general_feat_options(feats, feat_eligibility_sheet),
        ))

    if rogue is not None and len(ability_score_improvements) < asi_count and len(ability_score_improvements) >= fighter_asi_count:
        from dnd_board.rules.feats import general_feat_options, selected_general_feat_keys

        choices.append(ProgressionChoice(
            id=choice_id_value(ProgressionChoiceId.ROGUE_ABILITY_SCORE_IMPROVEMENT),
            choiceType=ProgressionChoiceType.ABILITY_SCORE_IMPROVEMENT,
            label=progression_choice_label(ProgressionChoiceLabel.ABILITY_SCORE_IMPROVEMENT),
            description=progression_choice_description(ProgressionChoiceDescription.ROGUE_ABILITY_SCORE_IMPROVEMENT),
            minimum=asi_count,
            maximum=asi_count,
            selected=[*ability_score_improvements, *selected_general_feat_keys(feats)],
            options=general_feat_options(feats, feat_eligibility_sheet),
        ))

    if rogue is not None:
        choices.extend(rogue_skill_progression_choices(rogue, skill_proficiencies))

    if fighter is not None:
        choices.extend(fighter_skill_progression_choices(fighter, skill_proficiencies))

    if fighter is not None and fighter.level >= 3 and fighter.subclass is None:
        choices.append(single_choice(
            choice_id=ProgressionChoiceId.FIGHTER_SUBCLASS,
            choice_type=ProgressionChoiceType.SUBCLASS,
            label=progression_choice_label(ProgressionChoiceLabel.FIGHTER_SUBCLASS),
            description=progression_choice_description(ProgressionChoiceDescription.FIGHTER_SUBCLASS),
            selected=[],
            options=fighter_subclass_options(),
        ))

    if rogue is not None and rogue.level >= 3 and rogue.subclass is None:
        choices.append(single_choice(
            choice_id=ProgressionChoiceId.ROGUE_SUBCLASS,
            choice_type=ProgressionChoiceType.SUBCLASS,
            label=progression_choice_label(ProgressionChoiceLabel.ROGUE_SUBCLASS),
            description=progression_choice_description(ProgressionChoiceDescription.ROGUE_SUBCLASS),
            selected=[],
            options=rogue_subclass_options(),
        ))

    if fighter is None:
        return [
            *choices,
            *arcane_trickster_progression_choices(rogue, spells),
        ]

    fighting_style_count = fighter_fighting_style_count(fighter)
    selected_styles = selected_enum_keys(fighter.fightingStyles or ([fighter.fightingStyle] if fighter.fightingStyle else []))
    if len(selected_styles) < fighting_style_count:
        choices.append(multi_choice(
            choice_id=ProgressionChoiceId.FIGHTER_FIGHTING_STYLES,
            choice_type=ProgressionChoiceType.FIGHTING_STYLE,
            label=progression_choice_label(ProgressionChoiceLabel.FIGHTING_STYLE),
            description=progression_choice_description(ProgressionChoiceDescription.FIGHTING_STYLE),
            minimum=fighting_style_count,
            maximum=fighting_style_count,
            selected=selected_styles,
            options=fighting_style_options(),
        ))

    maneuver_count = fighter_maneuver_count(fighter)
    selected_maneuvers = selected_enum_keys(fighter.maneuvers or [])
    if len(selected_maneuvers) < maneuver_count:
        choices.append(multi_choice(
            choice_id=ProgressionChoiceId.BATTLE_MASTER_MANEUVERS,
            choice_type=ProgressionChoiceType.BATTLE_MASTER_MANEUVERS,
            label=progression_choice_label(ProgressionChoiceLabel.BATTLE_MASTER_MANEUVERS),
            description=progression_choice_description(ProgressionChoiceDescription.BATTLE_MASTER_MANEUVERS),
            minimum=maneuver_count,
            maximum=maneuver_count,
            selected=selected_maneuvers,
            options=battle_master_maneuver_options(),
        ))

    arcane_shot_count = fighter_arcane_shot_count(fighter)
    selected_shots = selected_enum_keys(fighter.arcaneShots or [])
    if len(selected_shots) < arcane_shot_count:
        choices.append(multi_choice(
            choice_id=ProgressionChoiceId.ARCANE_ARCHER_SHOTS,
            choice_type=ProgressionChoiceType.ARCANE_SHOTS,
            label=progression_choice_label(ProgressionChoiceLabel.ARCANE_SHOT_OPTIONS),
            description=progression_choice_description(ProgressionChoiceDescription.ARCANE_SHOT_OPTIONS),
            minimum=arcane_shot_count,
            maximum=arcane_shot_count,
            selected=selected_shots,
            options=enum_options(ArcaneShotType),
        ))

    rune_count = fighter_rune_count(fighter)
    selected_runes = selected_enum_keys(fighter.runes or [])
    if len(selected_runes) < rune_count:
        choices.append(multi_choice(
            choice_id=ProgressionChoiceId.RUNE_KNIGHT_RUNES,
            choice_type=ProgressionChoiceType.RUNES,
            label=progression_choice_label(ProgressionChoiceLabel.RUNE_KNIGHT_RUNES),
            description=progression_choice_description(ProgressionChoiceDescription.RUNE_KNIGHT_RUNES),
            minimum=rune_count,
            maximum=rune_count,
            selected=selected_runes,
            options=[
                ProgressionChoiceOption(value=enum_key(rune), label=enum_label(rune))
                for rune in RuneType
                if rune_minimum_level(rune) <= fighter.level
            ],
        ))

    spell_count = fighter_configured_spell_count(fighter)
    fighter_spell_count = len([spell for spell in spells if eldritch_knight_catalog_spell(spell.id) is not None])
    if fighter_spell_count < spell_count:
        choices.append(ProgressionChoice(
            id=choice_id_value(ProgressionChoiceId.ELDRITCH_KNIGHT_SPELLS),
            choiceType=ProgressionChoiceType.SPELLS,
            label=progression_choice_label(ProgressionChoiceLabel.ELDRITCH_KNIGHT_SPELLS),
            description=progression_choice_description(ProgressionChoiceDescription.ELDRITCH_KNIGHT_SPELLS),
            minimum=spell_count,
            maximum=spell_count,
            selected=[enum_key(spell.id) for spell in spells],
            options=[
                ProgressionChoiceOption(value=enum_key(spell.id), label=spell_option_label(spell))
                for spell in eldritch_knight_spell_options(fighter.level, [enum_key(spell.id) for spell in spells])
            ],
        ))

    return [
        *choices,
        *arcane_trickster_progression_choices(rogue, spells),
    ]


def apply_progression_choice(classes: list[CharacterClassLevel], choice_id: ProgressionChoiceId, values: list[str]) -> list[CharacterClassLevel]:
    next_classes = [copy_character_class(character_class) for character_class in classes]
    fighter = fighter_class(next_classes)
    rogue = rogue_class(next_classes)

    clean_values = unique_values(values)
    if fighter is not None and choice_id == ProgressionChoiceId.FIGHTER_SUBCLASS and fighter.level >= 3:
        fighter.subclass = enum_value(FighterSubclassType, clean_values[0]) if clean_values else None
    elif rogue is not None and choice_id == ProgressionChoiceId.ROGUE_SUBCLASS and rogue.level >= 3:
        rogue.subclass = enum_value(RogueSubclassType, clean_values[0]) if clean_values else None
    elif fighter is not None and choice_id == ProgressionChoiceId.FIGHTER_FIGHTING_STYLES:
        styles = parse_enum_values(FightingStyleType, clean_values)[: fighter_fighting_style_count(fighter)]
        fighter.fightingStyle = None
        fighter.fightingStyles = styles
    elif fighter is not None and choice_id == ProgressionChoiceId.BATTLE_MASTER_MANEUVERS:
        fighter.maneuvers = parse_enum_values(BattleMasterManeuverType, clean_values)[: fighter_maneuver_count(fighter)]
    elif fighter is not None and choice_id == ProgressionChoiceId.ARCANE_ARCHER_SHOTS:
        fighter.arcaneShots = parse_enum_values(ArcaneShotType, clean_values)[: fighter_arcane_shot_count(fighter)]
    elif fighter is not None and choice_id == ProgressionChoiceId.RUNE_KNIGHT_RUNES:
        options = {rune for rune in RuneType if rune_minimum_level(rune) <= fighter.level}
        fighter.runes = [rune for rune in parse_enum_values(RuneType, clean_values) if rune in options][: fighter_rune_count(fighter)]

    return prune_progression_choices(next_classes)


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
        if character_class.name == ClassType.ROGUE and character_class.level < 3:
            character_class.subclass = None
        if character_class.name != ClassType.FIGHTER:
            continue
        if character_class.level < 3:
            character_class.subclass = None
            character_class.arcaneShots = None
            character_class.runes = None
        if character_class.subclass != FighterSubclassType.ARCANE_ARCHER:
            character_class.arcaneShots = None
        if character_class.subclass != FighterSubclassType.RUNE_KNIGHT:
            character_class.runes = None
        style_count = fighter_fighting_style_count(character_class)
        styles = parse_enum_values(FightingStyleType, selected_enum_keys(character_class.fightingStyles or ([character_class.fightingStyle] if character_class.fightingStyle else [])))
        character_class.fightingStyle = None
        character_class.fightingStyles = styles[:style_count] or None
        maneuver_count = fighter_maneuver_count(character_class)
        character_class.maneuvers = (character_class.maneuvers or [])[:maneuver_count] or None
        shot_count = fighter_arcane_shot_count(character_class)
        character_class.arcaneShots = (character_class.arcaneShots or [])[:shot_count] or None
        rune_count = fighter_rune_count(character_class)
        eligible_runes = [rune for rune in character_class.runes or [] if rune_minimum_level(rune) <= character_class.level]
        character_class.runes = eligible_runes[:rune_count] or None
    return classes


def fighter_class(classes: list[CharacterClassLevel]) -> CharacterClassLevel | None:
    return next((character_class for character_class in classes if character_class.name == ClassType.FIGHTER), None)


def rogue_class(classes: list[CharacterClassLevel]) -> CharacterClassLevel | None:
    return next((character_class for character_class in classes if character_class.name == ClassType.ROGUE), None)


def total_character_level(classes: list[CharacterClassLevel]) -> int:
    return sum(character_class.level for character_class in classes)


def fighter_asi_levels_up_to(fighter_level: int) -> int:
    return sum(1 for level in [4, 6, 8, 12, 14, 16, 19] if fighter_level >= level)


def rogue_asi_levels_up_to(rogue_level: int) -> int:
    return sum(1 for level in [4, 8, 10, 12, 16] if rogue_level >= level)


def fighter_skill_progression_choices(fighter: CharacterClassLevel, skill_proficiencies: dict[str, ProficiencyLevel]) -> list[ProgressionChoice]:
    selected_fighter_skills = [
        skill_key
        for skill_key in fighter_skill_option_keys()
        if skill_proficiencies.get(skill_key) in {ProficiencyLevel.PROFICIENT, ProficiencyLevel.EXPERTISE}
    ]
    if fighter.level < 1 or len(selected_fighter_skills) >= fighter_skill_proficiency_count(fighter):
        return []
    return [
        multi_choice(
            choice_id=ProgressionChoiceId.FIGHTER_SKILL_PROFICIENCIES,
            choice_type=ProgressionChoiceType.SKILL_PROFICIENCIES,
            label=progression_choice_label(ProgressionChoiceLabel.FIGHTER_SKILL_PROFICIENCIES),
            description=progression_choice_description(ProgressionChoiceDescription.FIGHTER_SKILL_PROFICIENCIES),
            minimum=fighter_skill_proficiency_count(fighter),
            maximum=fighter_skill_proficiency_count(fighter),
            selected=selected_fighter_skills,
            options=fighter_skill_options(),
        )
    ]


def fighter_skill_proficiency_count(fighter: CharacterClassLevel) -> int:
    return 2 if fighter.level >= 1 else 0


def fighter_skill_option_keys() -> list[str]:
    return [enum_key(skill) for skill in fighter_skill_option_types()]


def fighter_skill_options() -> list[ProgressionChoiceOption]:
    return [ProgressionChoiceOption(value=enum_key(skill), label=enum_label(skill)) for skill in fighter_skill_option_types()]


def fighter_skill_option_types() -> list[SkillType]:
    return [
        SkillType.ACROBATICS,
        SkillType.ANIMAL_HANDLING,
        SkillType.ATHLETICS,
        SkillType.HISTORY,
        SkillType.INSIGHT,
        SkillType.INTIMIDATION,
        SkillType.PERCEPTION,
        SkillType.PERSUASION,
        SkillType.SURVIVAL,
    ]


def rogue_skill_progression_choices(rogue: CharacterClassLevel, skill_proficiencies: dict[str, ProficiencyLevel]) -> list[ProgressionChoice]:
    choices: list[ProgressionChoice] = []
    selected_rogue_skills = [
        skill_key
        for skill_key in rogue_skill_option_keys()
        if skill_proficiencies.get(skill_key) in {ProficiencyLevel.PROFICIENT, ProficiencyLevel.EXPERTISE}
    ]
    if rogue.level >= 1 and len(selected_rogue_skills) < rogue_skill_proficiency_count(rogue):
        choices.append(multi_choice(
            choice_id=ProgressionChoiceId.ROGUE_SKILL_PROFICIENCIES,
            choice_type=ProgressionChoiceType.SKILL_PROFICIENCIES,
            label=progression_choice_label(ProgressionChoiceLabel.ROGUE_SKILL_PROFICIENCIES),
            description=progression_choice_description(ProgressionChoiceDescription.ROGUE_SKILL_PROFICIENCIES),
            minimum=rogue_skill_proficiency_count(rogue),
            maximum=rogue_skill_proficiency_count(rogue),
            selected=selected_rogue_skills,
            options=rogue_skill_options(),
        ))
        return choices

    expected_expertise = rogue_expertise_count(rogue)
    selected_expertise = [
        skill_key
        for skill_key, proficiency in skill_proficiencies.items()
        if proficiency == ProficiencyLevel.EXPERTISE
    ]
    expertise_options = [
        ProgressionChoiceOption(value=enum_key(skill), label=enum_label(skill))
        for skill in SkillType
        if skill_proficiencies.get(enum_key(skill)) in {ProficiencyLevel.PROFICIENT, ProficiencyLevel.EXPERTISE}
    ]
    required_expertise = min(expected_expertise, len(expertise_options))
    if expected_expertise > 0 and len(selected_expertise) < required_expertise:
        choices.append(multi_choice(
            choice_id=ProgressionChoiceId.ROGUE_EXPERTISE,
            choice_type=ProgressionChoiceType.EXPERTISE,
            label=progression_choice_label(ProgressionChoiceLabel.ROGUE_EXPERTISE),
            description=progression_choice_description(ProgressionChoiceDescription.ROGUE_EXPERTISE),
            minimum=required_expertise,
            maximum=required_expertise,
            selected=selected_expertise,
            options=expertise_options,
        ))
    return choices


def rogue_skill_proficiency_count(rogue: CharacterClassLevel) -> int:
    return 4 if rogue.level >= 1 else 0


def rogue_expertise_count(rogue: CharacterClassLevel) -> int:
    if rogue.level >= 6:
        return 4
    return 2 if rogue.level >= 1 else 0


def rogue_skill_option_keys() -> list[str]:
    return [enum_key(skill) for skill in rogue_skill_option_types()]


def rogue_skill_options() -> list[ProgressionChoiceOption]:
    return [ProgressionChoiceOption(value=enum_key(skill), label=enum_label(skill)) for skill in rogue_skill_option_types()]


def rogue_skill_option_types() -> list[SkillType]:
    return [
        SkillType.ACROBATICS,
        SkillType.ATHLETICS,
        SkillType.DECEPTION,
        SkillType.INSIGHT,
        SkillType.INTIMIDATION,
        SkillType.INVESTIGATION,
        SkillType.PERCEPTION,
        SkillType.PERSUASION,
        SkillType.SLEIGHT_OF_HAND,
        SkillType.STEALTH,
    ]


def fighter_fighting_style_count(fighter: CharacterClassLevel) -> int:
    count = 1 if fighter.level >= 1 else 0
    if fighter.subclass == FighterSubclassType.CHAMPION and fighter.level >= 7:
        count += 1
    if fighter.subclass == FighterSubclassType.BRUTE and fighter.level >= 10:
        count += 1
    return count


def fighter_maneuver_count(fighter: CharacterClassLevel) -> int:
    count = 0
    if fighter.subclass == FighterSubclassType.BATTLE_MASTER and fighter.level >= 3:
        progression = combat_superiority_subclass_progression(fighter.level)
        count = {
            3: 3,
            7: 5,
            10: 7,
            15: 9,
            18: 9,
        }.get(progression.minimum_level if progression else 0, 0)
    if has_fighting_style(fighter, FightingStyleType.SUPERIOR_TECHNIQUE):
        count += 1
    return count


def fighter_arcane_shot_count(fighter: CharacterClassLevel) -> int:
    if fighter.subclass != FighterSubclassType.ARCANE_ARCHER or fighter.level < 3:
        return 0
    if fighter.level >= 15:
        return 4
    if fighter.level >= 7:
        return 3
    return 2


def fighter_rune_count(fighter: CharacterClassLevel) -> int:
    if fighter.subclass != FighterSubclassType.RUNE_KNIGHT or fighter.level < 3:
        return 0
    if fighter.level >= 15:
        return 5
    if fighter.level >= 10:
        return 4
    if fighter.level >= 7:
        return 3
    return 2


def fighter_configured_spell_count(fighter: CharacterClassLevel) -> int:
    if fighter.subclass != FighterSubclassType.ELDRITCH_KNIGHT or fighter.level < 3:
        return 0
    progression = eldritch_knight_spellcasting(fighter.level)
    return progression.cantrips_known + progression.spells_known


def rogue_configured_spell_count(rogue: CharacterClassLevel) -> int:
    if rogue.subclass != RogueSubclassType.ARCANE_TRICKSTER or rogue.level < 3:
        return 0
    progression = arcane_trickster_spellcasting(rogue.level)
    return progression.cantrips_known + progression.spells_known


def arcane_trickster_progression_choices(rogue: CharacterClassLevel | None, spells: list[SpellEntry]) -> list[ProgressionChoice]:
    if rogue is None:
        return []
    spell_count = rogue_configured_spell_count(rogue)
    arcane_trickster_spells = [spell for spell in spells if spell.source == SpellSource.ARCANE_TRICKSTER]
    if len(arcane_trickster_spells) >= spell_count:
        return []
    return [
        ProgressionChoice(
            id=choice_id_value(ProgressionChoiceId.ARCANE_TRICKSTER_SPELLS),
            choiceType=ProgressionChoiceType.SPELLS,
            label=progression_choice_label(ProgressionChoiceLabel.ARCANE_TRICKSTER_SPELLS),
            description=progression_choice_description(ProgressionChoiceDescription.ARCANE_TRICKSTER_SPELLS),
            minimum=spell_count,
            maximum=spell_count,
            selected=[enum_key(spell.id) for spell in arcane_trickster_spells],
            options=[
                ProgressionChoiceOption(value=enum_key(spell.id), label=spell_option_label(spell))
                for spell in arcane_trickster_spell_options(rogue.level, [enum_key(spell.id) for spell in arcane_trickster_spells])
            ],
        )
    ]


def spell_option_label(spell: SpellEntry) -> str:
    level_label = progression_spell_option_label(SpellOptionLabel.CANTRIP) if spell.level == 0 else progression_spell_option_label(SpellOptionLabel.LEVEL, level=spell.level)
    return f"{level_label}: {enum_label(spell.name)}"


def progression_choice_label(label: ProgressionChoiceLabel) -> str:
    return label.value


def progression_choice_description(description: ProgressionChoiceDescription, **format_values: object) -> str:
    return description.value.format(**format_values)


def hit_point_choice_description(class_name: ClassType) -> str:
    return progression_choice_description(
        ProgressionChoiceDescription.HIT_POINTS,
        hit_die_label=hit_die_label(class_name),
    )


def hit_die_label(class_name: ClassType) -> str:
    if class_name == ClassType.ROGUE:
        return HitDieLabel.ROGUE.value
    return HitDieLabel.FIGHTER.value


def class_hit_die(class_name: ClassType) -> int:
    if class_name == ClassType.ROGUE:
        return HitDieValue.ROGUE.value
    return HitDieValue.FIGHTER.value


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


def fighter_subclass_options() -> list[ProgressionChoiceOption]:
    return [ProgressionChoiceOption(value=enum_key(option), label=fighter_subclass_label(option)) for option in FighterSubclassType]


def rogue_subclass_options() -> list[ProgressionChoiceOption]:
    return [ProgressionChoiceOption(value=enum_key(option), label=rogue_subclass_label(option)) for option in RogueSubclassType]


def fighting_style_options() -> list[ProgressionChoiceOption]:
    from dnd_board.rules.feats import fighting_style_label

    return [ProgressionChoiceOption(value=enum_key(option), label=fighting_style_label(option)) for option in FightingStyleType]


def battle_master_maneuver_options() -> list[ProgressionChoiceOption]:
    from dnd_board.rules.classes.fighter.battle_master import battle_master_maneuver_label

    return [ProgressionChoiceOption(value=enum_key(option), label=battle_master_maneuver_label(option)) for option in BattleMasterManeuverType]


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
        maneuvers=list(character_class.maneuvers) if character_class.maneuvers else None,
        arcaneShots=list(character_class.arcaneShots) if character_class.arcaneShots else None,
        runes=list(character_class.runes) if character_class.runes else None,
    )
