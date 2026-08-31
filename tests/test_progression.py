from dnd_board.character_sheet import ArcaneShotType, BattleMasterManeuverType, CharacterClassLevel, ClassType, FightingStyleType, RuneType
from dnd_board.rules.classes.fighter.base import FighterSubclassType
from dnd_board.rules.classes.rogue.base import RogueSubclassType
from dnd_board.rules.progression import (
    ProgressionChoiceId,
    apply_progression_choice,
    fighter_arcane_shot_count,
    fighter_rune_count,
    parse_enum_values,
    parse_progression_choice_id,
    prune_progression_choices,
    selected_enum_keys,
    unique_values,
    update_class_level,
)


def test_apply_fighter_progression_choices_for_subclass_options() -> None:
    classes = [
        CharacterClassLevel(
            name=ClassType.FIGHTER,
            level=10,
            subclass=FighterSubclassType.BATTLE_MASTER,
        )
    ]

    styled = apply_progression_choice(classes, ProgressionChoiceId.FIGHTER_FIGHTING_STYLES, ["defense", "dueling"])
    maneuvered = apply_progression_choice(classes, ProgressionChoiceId.BATTLE_MASTER_MANEUVERS, ["ambush", "commandersStrike", "tripAttack"])
    arcane_archer = apply_progression_choice(
        [CharacterClassLevel(name=ClassType.FIGHTER, level=7, subclass=FighterSubclassType.ARCANE_ARCHER)],
        ProgressionChoiceId.ARCANE_ARCHER_SHOTS,
        ["banishingArrow", "graspingArrow", "seekingArrow"],
    )
    rune_knight = apply_progression_choice(
        [CharacterClassLevel(name=ClassType.FIGHTER, level=7, subclass=FighterSubclassType.RUNE_KNIGHT)],
        ProgressionChoiceId.RUNE_KNIGHT_RUNES,
        ["cloudRune", "fireRune", "hillRune", "stormRune"],
    )

    assert styled[0].fightingStyles == [FightingStyleType.DEFENSE]
    assert maneuvered[0].maneuvers == [BattleMasterManeuverType.AMBUSH, BattleMasterManeuverType.COMMANDERS_STRIKE, BattleMasterManeuverType.TRIP_ATTACK]
    assert arcane_archer[0].arcaneShots == [ArcaneShotType.BANISHING_ARROW, ArcaneShotType.GRASPING_ARROW, ArcaneShotType.SEEKING_ARROW]
    assert rune_knight[0].runes == [RuneType.CLOUD_RUNE, RuneType.FIRE_RUNE, RuneType.HILL_RUNE]


def test_fighter_subclass_option_counts_cover_level_gates() -> None:
    assert fighter_arcane_shot_count(CharacterClassLevel(name=ClassType.FIGHTER, level=2, subclass=FighterSubclassType.ARCANE_ARCHER)) == 0
    assert fighter_arcane_shot_count(CharacterClassLevel(name=ClassType.FIGHTER, level=3, subclass=FighterSubclassType.ARCANE_ARCHER)) == 2
    assert fighter_arcane_shot_count(CharacterClassLevel(name=ClassType.FIGHTER, level=7, subclass=FighterSubclassType.ARCANE_ARCHER)) == 3
    assert fighter_arcane_shot_count(CharacterClassLevel(name=ClassType.FIGHTER, level=15, subclass=FighterSubclassType.ARCANE_ARCHER)) == 4

    assert fighter_rune_count(CharacterClassLevel(name=ClassType.FIGHTER, level=2, subclass=FighterSubclassType.RUNE_KNIGHT)) == 0
    assert fighter_rune_count(CharacterClassLevel(name=ClassType.FIGHTER, level=3, subclass=FighterSubclassType.RUNE_KNIGHT)) == 2
    assert fighter_rune_count(CharacterClassLevel(name=ClassType.FIGHTER, level=7, subclass=FighterSubclassType.RUNE_KNIGHT)) == 3
    assert fighter_rune_count(CharacterClassLevel(name=ClassType.FIGHTER, level=10, subclass=FighterSubclassType.RUNE_KNIGHT)) == 4
    assert fighter_rune_count(CharacterClassLevel(name=ClassType.FIGHTER, level=15, subclass=FighterSubclassType.RUNE_KNIGHT)) == 5


def test_progression_parser_and_level_update_reject_unknown_values() -> None:
    classes = [CharacterClassLevel(name=ClassType.ROGUE, level=4)]

    assert parse_progression_choice_id("not-a-choice") is None
    assert parse_progression_choice_id("fighter-subclass") == ProgressionChoiceId.FIGHTER_SUBCLASS
    assert update_class_level(classes, ClassType.FIGHTER, 1) == classes


def test_apply_and_prune_progression_edge_paths() -> None:
    fighter = CharacterClassLevel(
        name=ClassType.FIGHTER,
        level=3,
        subclass=FighterSubclassType.ARCANE_ARCHER,
        arcaneShots=[ArcaneShotType.BANISHING_ARROW],
        runes=[RuneType.CLOUD_RUNE],
    )
    rogue = CharacterClassLevel(name=ClassType.ROGUE, level=3)

    assert apply_progression_choice([fighter], ProgressionChoiceId.FIGHTER_SUBCLASS, ["champion"])[0].subclass == FighterSubclassType.CHAMPION
    assert apply_progression_choice([rogue], ProgressionChoiceId.ROGUE_SUBCLASS, ["soulknife"])[0].subclass == RogueSubclassType.SOULKNIFE
    assert apply_progression_choice([fighter], ProgressionChoiceId.FIGHTER_SUBCLASS, [])[0].subclass is None
    assert apply_progression_choice([rogue], ProgressionChoiceId.ROGUE_SUBCLASS, [])[0].subclass is None

    low_level_fighter = prune_progression_choices([CharacterClassLevel(name=ClassType.FIGHTER, level=2, subclass=FighterSubclassType.ARCANE_ARCHER, arcaneShots=[ArcaneShotType.BANISHING_ARROW], runes=[RuneType.CLOUD_RUNE])])[0]
    low_level_rogue = prune_progression_choices([CharacterClassLevel(name=ClassType.ROGUE, level=2, subclass=RogueSubclassType.SOULKNIFE)])[0]

    assert low_level_fighter.subclass is None
    assert low_level_fighter.arcaneShots is None
    assert low_level_fighter.runes is None
    assert low_level_rogue.subclass is None
    assert apply_progression_choice([fighter], ProgressionChoiceId.ROGUE_SUBCLASS, ["soulknife"])[0].subclass == FighterSubclassType.ARCANE_ARCHER
    assert update_class_level([CharacterClassLevel(name=ClassType.FIGHTER, level=20)], ClassType.FIGHTER, 1)[0].level == 20
    assert update_class_level([CharacterClassLevel(name=ClassType.FIGHTER, level=1)], ClassType.FIGHTER, -1)[0].level == 1


def test_progression_value_helpers_filter_duplicates_and_invalid_values() -> None:
    assert selected_enum_keys([FightingStyleType.DEFENSE, FightingStyleType.DEFENSE, FightingStyleType.DUELING]) == ["defense", "dueling"]
    assert parse_enum_values(FightingStyleType, ["defense", "defense", "not-real"]) == [FightingStyleType.DEFENSE]
    assert unique_values(["a", "a", "b"]) == ["a", "b"]
