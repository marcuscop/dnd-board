from __future__ import annotations

from enum import Enum

from dnd_board.character_sheet import (
    ArcaneShotType,
    BattleMasterManeuverType,
    CharacterClassLevel,
    ClassType,
    FightingStyleType,
    ProgressionChoice,
    ProgressionChoiceOption,
    ProgressionChoiceType,
    RuneType,
    SheetFeature,
    SpellEntry,
    enum_key,
    enum_label,
    enum_value,
)
from dnd_board.rules.classes.fighter.archetypes import eldritch_knight_spell_options, eldritch_knight_spellcasting, rune_minimum_level
from dnd_board.rules.classes.fighter.base import FighterSubclassType
from dnd_board.rules.shared.combat_superiority import combat_superiority_subclass_progression


MIN_CHARACTER_LEVEL = 1
MAX_CHARACTER_LEVEL = 20


def progression_choices(
    classes: list[CharacterClassLevel],
    spells: list[SpellEntry],
    hit_point_increases: list[int],
    ability_score_improvements: list[str],
    feats: list[SheetFeature] | None = None,
) -> list[ProgressionChoice]:
    fighter = fighter_class(classes)
    if fighter is None:
        return []

    choices: list[ProgressionChoice] = []
    expected_hit_point_increases = max(0, total_character_level(classes) - 1)
    if len(hit_point_increases) < expected_hit_point_increases:
        choices.append(single_choice(
            choice_id="hitPointIncrease",
            choice_type=ProgressionChoiceType.HIT_POINTS,
            label="Hit Points",
            description="Choose fixed HP or roll the Fighter d10 for this level. Constitution modifier is applied by the server.",
            selected=[],
            options=[
                ProgressionChoiceOption(value="fixed", label="Fixed"),
                ProgressionChoiceOption(value="roll", label="Roll"),
            ],
        ))

    asi_count = fighter_asi_levels_up_to(fighter.level)
    if len(ability_score_improvements) < asi_count:
        from dnd_board.rules.feats import general_feat_options, selected_general_feat_keys

        choices.append(ProgressionChoice(
            id="fighterAbilityScoreImprovement",
            choiceType=ProgressionChoiceType.ABILITY_SCORE_IMPROVEMENT,
            label="Ability Score Improvement",
            description="Increase one ability score by 2, increase two ability scores by 1, or choose a feat. Optional Martial Versatility changes are not built yet.",
            minimum=asi_count,
            maximum=asi_count,
            selected=[*ability_score_improvements, *selected_general_feat_keys(feats)],
            options=general_feat_options(feats),
        ))

    if fighter.level >= 3 and fighter.subclass is None:
        choices.append(single_choice(
            choice_id="fighterSubclass",
            choice_type=ProgressionChoiceType.SUBCLASS,
            label="Martial Archetype",
            description="Choose a Fighter Martial Archetype.",
            selected=[],
            options=enum_options(FighterSubclassType),
        ))

    fighting_style_count = fighter_fighting_style_count(fighter)
    selected_styles = selected_enum_keys(fighter.fightingStyles or ([fighter.fightingStyle] if fighter.fightingStyle else []))
    if len(selected_styles) < fighting_style_count:
        choices.append(multi_choice(
            choice_id="fighterFightingStyles",
            choice_type=ProgressionChoiceType.FIGHTING_STYLE,
            label="Fighting Style",
            description="Choose Fighter Fighting Style feats. These are not repeatable.",
            minimum=fighting_style_count,
            maximum=fighting_style_count,
            selected=selected_styles,
            options=enum_options(FightingStyleType),
        ))

    maneuver_count = fighter_maneuver_count(fighter)
    selected_maneuvers = selected_enum_keys(fighter.maneuvers or [])
    if len(selected_maneuvers) < maneuver_count:
        choices.append(multi_choice(
            choice_id="battleMasterManeuvers",
            choice_type=ProgressionChoiceType.BATTLE_MASTER_MANEUVERS,
            label="Battle Master Maneuvers",
            description="Choose maneuvers known for Battle Master or Superior Technique.",
            minimum=maneuver_count,
            maximum=maneuver_count,
            selected=selected_maneuvers,
            options=enum_options(BattleMasterManeuverType),
        ))

    arcane_shot_count = fighter_arcane_shot_count(fighter)
    selected_shots = selected_enum_keys(fighter.arcaneShots or [])
    if len(selected_shots) < arcane_shot_count:
        choices.append(multi_choice(
            choice_id="arcaneArcherShots",
            choice_type=ProgressionChoiceType.ARCANE_SHOTS,
            label="Arcane Shot Options",
            description="Choose Arcane Shot options known.",
            minimum=arcane_shot_count,
            maximum=arcane_shot_count,
            selected=selected_shots,
            options=enum_options(ArcaneShotType),
        ))

    rune_count = fighter_rune_count(fighter)
    selected_runes = selected_enum_keys(fighter.runes or [])
    if len(selected_runes) < rune_count:
        choices.append(multi_choice(
            choice_id="runeKnightRunes",
            choice_type=ProgressionChoiceType.RUNES,
            label="Rune Knight Runes",
            description="Choose runes known. Hill and Storm require Fighter level 7.",
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
    if len(spells) < spell_count:
        choices.append(ProgressionChoice(
            id="eldritchKnightSpells",
            choiceType=ProgressionChoiceType.SPELLS,
            label="Eldritch Knight Spells",
            description="Choose known Eldritch Knight cantrips and wizard spells from the curated starter catalog.",
            minimum=spell_count,
            maximum=spell_count,
            selected=[spell.id for spell in spells],
            options=[
                ProgressionChoiceOption(value=spell.id, label=spell_option_label(spell))
                for spell in eldritch_knight_spell_options(fighter.level, [spell.id for spell in spells])
            ],
        ))

    return choices


def apply_progression_choice(classes: list[CharacterClassLevel], choice_id: str, values: list[str]) -> list[CharacterClassLevel]:
    next_classes = [copy_character_class(character_class) for character_class in classes]
    fighter = fighter_class(next_classes)
    if fighter is None:
        return next_classes

    normalized_choice_id = choice_id.strip().replace("-", "").replace("_", "").lower()
    clean_values = unique_values(values)
    if normalized_choice_id == "fightersubclass" and fighter.level >= 3:
        fighter.subclass = enum_value(FighterSubclassType, clean_values[0]) if clean_values else None
    elif normalized_choice_id == "fighterfightingstyles":
        styles = parse_enum_values(FightingStyleType, clean_values)[: fighter_fighting_style_count(fighter)]
        fighter.fightingStyle = None
        fighter.fightingStyles = styles
    elif normalized_choice_id == "battlemastermaneuvers":
        fighter.maneuvers = parse_enum_values(BattleMasterManeuverType, clean_values)[: fighter_maneuver_count(fighter)]
    elif normalized_choice_id == "arcanearchershots":
        fighter.arcaneShots = parse_enum_values(ArcaneShotType, clean_values)[: fighter_arcane_shot_count(fighter)]
    elif normalized_choice_id == "runeknightrunes":
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
        if character_class.name != ClassType.FIGHTER:
            continue
        character_class.level = max(MIN_CHARACTER_LEVEL, min(MAX_CHARACTER_LEVEL, character_class.level))
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


def total_character_level(classes: list[CharacterClassLevel]) -> int:
    return sum(character_class.level for character_class in classes)


def fighter_asi_levels_up_to(fighter_level: int) -> int:
    return sum(1 for level in [4, 6, 8, 12, 14, 16, 19] if fighter_level >= level)


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


def spell_option_label(spell: SpellEntry) -> str:
    level_label = "Cantrip" if spell.level == 0 else f"Level {spell.level}"
    return f"{level_label}: {spell.name}"


def has_fighting_style(fighter: CharacterClassLevel, style: FightingStyleType) -> bool:
    return style == fighter.fightingStyle or style in (fighter.fightingStyles or [])


def single_choice(choice_id: str, choice_type: ProgressionChoiceType, label: str, description: str, selected: list[str], options: list[ProgressionChoiceOption]) -> ProgressionChoice:
    return ProgressionChoice(choice_id, choice_type, label, description, 1, 1, selected, options)


def multi_choice(
    choice_id: str,
    choice_type: ProgressionChoiceType,
    label: str,
    description: str,
    minimum: int,
    maximum: int,
    selected: list[str],
    options: list[ProgressionChoiceOption],
) -> ProgressionChoice:
    return ProgressionChoice(choice_id, choice_type, label, description, minimum, maximum, selected, options)


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
        maneuvers=list(character_class.maneuvers) if character_class.maneuvers else None,
        arcaneShots=list(character_class.arcaneShots) if character_class.arcaneShots else None,
        runes=list(character_class.runes) if character_class.runes else None,
    )
