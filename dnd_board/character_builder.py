from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from typing import Any, TypeVar

from dnd_board.character_sheet import (
    AbilityScores,
    AbilityType,
    CharacterClassLevel,
    ClassType,
    FightingStyleType,
    PartyMemberConfig,
    PartyMemberSheet,
    ProficiencyLevel,
    ProgressionChoiceOption,
    ResourceTracker,
    RestType,
    SkillType,
    SpellEntry,
    SpellId,
    SpellSource,
    SpellStatus,
    TimeEconomy,
    enum_key,
    enum_label,
    enum_value,
    serialize_dataclass,
)
from dnd_board.rules.backgrounds import (
    BackgroundEquipmentChoice,
    BackgroundOriginFeatType,
    BackgroundType,
    ToolType,
    background_definition,
    background_equipment,
    background_features_for_tool,
    background_feats,
    background_hit_point_bonus,
    background_label,
    background_purse,
    background_skill_proficiencies,
    background_tool_options,
)
from dnd_board.rules.progression import class_hit_die
from dnd_board.rules.species import SpeciesType, species_definition, species_hit_point_bonus, species_label, species_traits


CHARACTER_BUILDER_STARTING_LEVEL = 1
SUPPORTED_CLASS_TYPES = (ClassType.FIGHTER, ClassType.ROGUE, ClassType.WIZARD)
STANDARD_ARRAY_SCORES = (15, 14, 13, 12, 10, 8)
POINT_BUY_POINTS = 27
POINT_BUY_SCORE_COSTS = {
    8: 0,
    9: 1,
    10: 2,
    11: 3,
    12: 4,
    13: 5,
    14: 7,
    15: 9,
}
RANDOM_SCORE_MINIMUM = 3
RANDOM_SCORE_MAXIMUM = 18
BACKGROUND_ABILITY_INCREASE_TOTAL = 3
BACKGROUND_ABILITY_INCREASE_MAX = 2


class AbilityScoreGenerationMethod(Enum):
    STANDARD_ARRAY = "Standard Array"
    POINT_BUY = "Point Buy"
    RANDOM = "Random"


class CharacterBuilderPayloadField(Enum):
    MEMBER_ID = "memberId"
    NAME = "name"
    OWNER = "owner"
    CLASS_NAME = "className"
    RACE = "race"
    BACKGROUND = "background"
    ABILITY_SCORE_METHOD = "abilityScoreMethod"
    BASE_ABILITY_SCORES = "baseAbilityScores"
    ROLLED_ABILITY_SCORES = "rolledAbilityScores"
    BACKGROUND_ABILITY_INCREASES = "backgroundAbilityIncreases"
    TOOL_PROFICIENCY = "toolProficiency"
    EQUIPMENT_CHOICE = "equipmentChoice"
    MAGIC_INITIATE_SPELLS = "magicInitiateSpells"
    CLASS_SKILL_PROFICIENCIES = "classSkillProficiencies"
    CLASS_EXPERTISE = "classExpertise"
    FIGHTING_STYLE = "fightingStyle"
    WIZARD_CANTRIPS = "wizardCantrips"
    WIZARD_SPELLBOOK_SPELLS = "wizardSpellbookSpells"
    WIZARD_PREPARED_SPELLS = "wizardPreparedSpells"


class CharacterBuilderOptionField(Enum):
    CLASSES = "classes"
    RACES = "races"
    BACKGROUNDS = "backgrounds"
    ABILITY_SCORE_METHODS = "abilityScoreMethods"
    STANDARD_ARRAY = "standardArray"
    POINT_BUY_COSTS = "pointBuyCosts"
    POINT_BUY_POINTS = "pointBuyPoints"
    BACKGROUND_DETAILS = "backgroundDetails"
    CLASS_DETAILS = "classDetails"
    TOOL_DETAILS = "toolDetails"


CharacterBuilderOrigin = TypeVar("CharacterBuilderOrigin", SpeciesType, BackgroundType)


@dataclass(frozen=True)
class CharacterBuilderRequest:
    member_id: str
    name: str
    owner: str
    class_type: ClassType
    race: SpeciesType
    background: BackgroundType
    ability_score_method: AbilityScoreGenerationMethod
    tool_proficiency: ToolType | None
    equipment_choice: BackgroundEquipmentChoice
    magic_initiate_spells: tuple[SpellId, ...]
    class_skill_proficiencies: tuple[SkillType, ...]
    class_expertise: tuple[SkillType, ...]
    fighting_style: FightingStyleType | None
    wizard_cantrips: tuple[SpellId, ...]
    wizard_spellbook_spells: tuple[SpellId, ...]
    wizard_prepared_spells: tuple[SpellId, ...]
    ability_scores: AbilityScores


def character_builder_options() -> dict[str, Any]:
    from dnd_board.rules.tools import serialized_tool_details

    return {
        option_key(CharacterBuilderOptionField.CLASSES): serialize_options(enum_options(SUPPORTED_CLASS_TYPES)),
        option_key(CharacterBuilderOptionField.RACES): serialize_options(enum_options(SpeciesType)),
        option_key(CharacterBuilderOptionField.BACKGROUNDS): serialize_options(enum_options(BackgroundType)),
        option_key(CharacterBuilderOptionField.ABILITY_SCORE_METHODS): serialize_options(enum_options(AbilityScoreGenerationMethod)),
        option_key(CharacterBuilderOptionField.STANDARD_ARRAY): list(STANDARD_ARRAY_SCORES),
        option_key(CharacterBuilderOptionField.POINT_BUY_COSTS): POINT_BUY_SCORE_COSTS,
        option_key(CharacterBuilderOptionField.POINT_BUY_POINTS): POINT_BUY_POINTS,
        option_key(CharacterBuilderOptionField.BACKGROUND_DETAILS): background_details(),
        option_key(CharacterBuilderOptionField.CLASS_DETAILS): class_details(),
        option_key(CharacterBuilderOptionField.TOOL_DETAILS): serialized_tool_details(),
    }


def character_builder_request_from_payload(payload: dict[str, Any], *, default_member_id: str, default_owner: str) -> CharacterBuilderRequest:
    class_type = enum_value(ClassType, payload_value(payload, CharacterBuilderPayloadField.CLASS_NAME, enum_key(ClassType.FIGHTER)))
    if class_type not in SUPPORTED_CLASS_TYPES:
        raise ValueError("Choose Fighter, Rogue, or Wizard")

    race = origin_from_payload(SpeciesType, payload_value(payload, CharacterBuilderPayloadField.RACE), SpeciesType.HUMAN)
    background = origin_from_payload(BackgroundType, payload_value(payload, CharacterBuilderPayloadField.BACKGROUND), BackgroundType.WAYFARER)
    ability_score_method = enum_value(AbilityScoreGenerationMethod, payload_value(payload, CharacterBuilderPayloadField.ABILITY_SCORE_METHOD, enum_key(AbilityScoreGenerationMethod.STANDARD_ARRAY))) or AbilityScoreGenerationMethod.STANDARD_ARRAY
    ability_scores = ability_scores_from_payload(
        ability_score_method,
        payload_value(payload, CharacterBuilderPayloadField.BASE_ABILITY_SCORES, {}),
        payload_value(payload, CharacterBuilderPayloadField.ROLLED_ABILITY_SCORES, ()),
        payload_value(payload, CharacterBuilderPayloadField.BACKGROUND_ABILITY_INCREASES, {}),
        background,
    )
    tool_proficiency = selected_tool_from_payload(background, payload_value(payload, CharacterBuilderPayloadField.TOOL_PROFICIENCY))
    equipment_choice = enum_value(BackgroundEquipmentChoice, payload_value(payload, CharacterBuilderPayloadField.EQUIPMENT_CHOICE, enum_key(BackgroundEquipmentChoice.PACKAGE))) or BackgroundEquipmentChoice.PACKAGE
    magic_initiate_spells = magic_initiate_spells_from_payload(background, payload_value(payload, CharacterBuilderPayloadField.MAGIC_INITIATE_SPELLS, ()))
    class_skill_proficiencies = class_skill_proficiencies_from_payload(class_type, payload_value(payload, CharacterBuilderPayloadField.CLASS_SKILL_PROFICIENCIES, ()))
    class_expertise = class_expertise_from_payload(class_type, payload_value(payload, CharacterBuilderPayloadField.CLASS_EXPERTISE, ()), background, class_skill_proficiencies)
    fighting_style = fighting_style_from_payload(class_type, payload_value(payload, CharacterBuilderPayloadField.FIGHTING_STYLE))
    wizard_cantrips = wizard_cantrips_from_payload(class_type, payload_value(payload, CharacterBuilderPayloadField.WIZARD_CANTRIPS, ()))
    wizard_spellbook_spells = wizard_spellbook_spells_from_payload(class_type, payload_value(payload, CharacterBuilderPayloadField.WIZARD_SPELLBOOK_SPELLS, ()))
    wizard_prepared_spells = wizard_prepared_spells_from_payload(class_type, payload_value(payload, CharacterBuilderPayloadField.WIZARD_PREPARED_SPELLS, ()), wizard_spellbook_spells)

    return CharacterBuilderRequest(
        member_id=clean_text(payload_value(payload, CharacterBuilderPayloadField.MEMBER_ID), default_member_id, 40),
        name=clean_text(payload_value(payload, CharacterBuilderPayloadField.NAME), "New Character", 40),
        owner=clean_text(payload_value(payload, CharacterBuilderPayloadField.OWNER), default_owner, 40),
        class_type=class_type,
        race=race,
        background=background,
        ability_score_method=ability_score_method,
        tool_proficiency=tool_proficiency,
        equipment_choice=equipment_choice,
        magic_initiate_spells=magic_initiate_spells,
        class_skill_proficiencies=class_skill_proficiencies,
        class_expertise=class_expertise,
        fighting_style=fighting_style,
        wizard_cantrips=wizard_cantrips,
        wizard_spellbook_spells=wizard_spellbook_spells,
        wizard_prepared_spells=wizard_prepared_spells,
        ability_scores=ability_scores,
    )


def build_party_member_config(request: CharacterBuilderRequest) -> PartyMemberConfig:
    species = species_definition(request.race)
    character_class = CharacterClassLevel(
        name=request.class_type,
        level=CHARACTER_BUILDER_STARTING_LEVEL,
        fightingStyles=[request.fighting_style] if request.fighting_style else None,
    )
    skills = builder_skill_proficiencies(request.background, request.class_skill_proficiencies, request.class_expertise)
    return PartyMemberConfig(
        id=request.member_id,
        name=request.name,
        maxHp=fixed_max_hp(request.class_type, CHARACTER_BUILDER_STARTING_LEVEL, request.ability_scores, request.race, request.background),
        abilityScores=request.ability_scores,
        sheet=PartyMemberSheet(
            race=species_label(request.race),
            background=background_label(request.background),
            classes=[character_class],
            speed=species.speed,
            skills=skills or None,
            proficiencies=background_proficiencies(request.tool_proficiency) or None,
            feats=background_feats(request.background) or None,
            traits=species_traits(request.race) or None,
            features=background_features_for_tool(request.background, request.tool_proficiency) or None,
            resources=background_spell_resources(request.background, request.magic_initiate_spells) or None,
            spells=builder_spell_entries(request) or None,
            spellbook=wizard_spellbook_entries(request) or None,
            equipment=background_equipment(request.background, request.equipment_choice, request.tool_proficiency) or None,
            purse=background_purse(request.background, request.equipment_choice),
            damageResistances=list(species.damageResistances) or None,
        ),
    )


def payload_key(field: CharacterBuilderPayloadField) -> str:
    return field.value


def option_key(field: CharacterBuilderOptionField) -> str:
    return field.value


def enum_options(options: type[Enum] | tuple[Enum, ...]) -> list[ProgressionChoiceOption]:
    return [ProgressionChoiceOption(value=enum_key(option), label=enum_label(option)) for option in options]


def serialize_options(options: list[ProgressionChoiceOption]) -> list[dict[str, Any]]:
    return serialize_dataclass(options)


def payload_value(payload: dict[str, Any], field: CharacterBuilderPayloadField, default: Any = None) -> Any:
    return payload.get(payload_key(field), default)


def origin_from_payload(enum_type: type[CharacterBuilderOrigin], value: Any, fallback: CharacterBuilderOrigin) -> CharacterBuilderOrigin:
    return enum_value(enum_type, value) or fallback


def background_details() -> dict[str, dict[str, Any]]:
    return {
        enum_key(background_type): {
            "abilityScores": serialize_options(enum_options(background_ability_options(background_type))),
            "skillProficiencies": serialize_options(enum_options(tuple(background_skill_proficiency_types(background_type)))),
            "toolOptions": serialize_options(enum_options(background_tool_options(background_type))),
            "equipmentChoices": serialize_options(enum_options(BackgroundEquipmentChoice)),
            "magicInitiateSpellChoices": magic_initiate_spell_choices(background_type),
        }
        for background_type in BackgroundType
    }


def class_details() -> dict[str, dict[str, Any]]:
    from dnd_board.rules.classes.wizard.base import (
        wizard_cantrip_count,
        wizard_cantrip_options,
        wizard_prepared_spell_count,
        wizard_prepared_spell_options,
        wizard_spellbook_spell_count,
        wizard_spellbook_spell_options,
    )
    from dnd_board.rules.progression import (
        fighter_fighting_style_count,
        fighter_skill_option_types,
        rogue_expertise_count,
        rogue_skill_option_types,
        wizard_skill_option_types,
    )

    details: dict[str, dict[str, Any]] = {}
    for class_type in SUPPORTED_CLASS_TYPES:
        character_class = CharacterClassLevel(name=class_type, level=CHARACTER_BUILDER_STARTING_LEVEL)
        skill_options = {
            ClassType.FIGHTER: fighter_skill_option_types,
            ClassType.ROGUE: rogue_skill_option_types,
            ClassType.WIZARD: wizard_skill_option_types,
        }[class_type]()
        details[enum_key(class_type)] = {
            "skillProficiencies": {
                "minimum": class_skill_proficiency_count(class_type),
                "maximum": class_skill_proficiency_count(class_type),
                "options": serialize_options(enum_options(tuple(skill_options))),
            },
            "expertise": {
                "minimum": rogue_expertise_count(character_class) if class_type == ClassType.ROGUE else 0,
                "maximum": rogue_expertise_count(character_class) if class_type == ClassType.ROGUE else 0,
            },
            "fightingStyles": {
                "minimum": fighter_fighting_style_count(character_class) if class_type == ClassType.FIGHTER else 0,
                "maximum": fighter_fighting_style_count(character_class) if class_type == ClassType.FIGHTER else 0,
                "options": serialize_options(enum_options(FightingStyleType)),
            },
            "wizardSpells": {
                "cantripsKnown": wizard_cantrip_count(character_class) if class_type == ClassType.WIZARD else 0,
                "spellbookSpellsKnown": wizard_spellbook_spell_count(character_class) if class_type == ClassType.WIZARD else 0,
                "preparedSpellsKnown": wizard_prepared_spell_count(character_class) if class_type == ClassType.WIZARD else 0,
                "cantrips": serialize_spell_options(wizard_cantrip_options(CHARACTER_BUILDER_STARTING_LEVEL)) if class_type == ClassType.WIZARD else [],
                "spellbookSpells": serialize_spell_options(wizard_spellbook_spell_options(CHARACTER_BUILDER_STARTING_LEVEL)) if class_type == ClassType.WIZARD else [],
                "preparedSpells": serialize_spell_options(wizard_prepared_spell_options(CHARACTER_BUILDER_STARTING_LEVEL)) if class_type == ClassType.WIZARD else [],
            },
        }
    return details


def ability_scores_from_payload(method: AbilityScoreGenerationMethod, base_value: Any, rolled_value: Any, increase_value: Any, background: BackgroundType) -> AbilityScores:
    base_scores = base_ability_scores_from_payload(method, base_value, rolled_value)
    increases = background_ability_increases_from_payload(increase_value, background)
    return AbilityScores(**{
        enum_key(ability): base_scores[ability] + increases[ability]
        for ability in AbilityType
    })


def base_ability_scores_from_payload(method: AbilityScoreGenerationMethod, value: Any, rolled_value: Any = ()) -> dict[AbilityType, int]:
    if not isinstance(value, dict):
        raise ValueError("Assign base scores to all abilities")
    scores: dict[AbilityType, int] = {}
    for ability in AbilityType:
        raw_score = value.get(enum_key(ability))
        try:
            score = int(raw_score)
        except (TypeError, ValueError):
            raise ValueError("Assign base scores to all abilities") from None
        scores[ability] = score
    validate_base_ability_scores(method, scores, rolled_value)
    return scores


def validate_base_ability_scores(method: AbilityScoreGenerationMethod, scores: dict[AbilityType, int], rolled_value: Any) -> None:
    if method == AbilityScoreGenerationMethod.STANDARD_ARRAY:
        validate_standard_array_scores(scores)
        return
    if method == AbilityScoreGenerationMethod.POINT_BUY:
        validate_point_buy_scores(scores)
        return
    validate_random_scores(scores, rolled_value)


def validate_standard_array_scores(scores: dict[AbilityType, int]) -> None:
    if sorted(scores.values(), reverse=True) != list(STANDARD_ARRAY_SCORES):
        raise ValueError("Use each standard array score exactly once")


def validate_point_buy_scores(scores: dict[AbilityType, int]) -> None:
    cost = 0
    for score in scores.values():
        if score not in POINT_BUY_SCORE_COSTS:
            raise ValueError("Point buy scores must be between 8 and 15")
        cost += POINT_BUY_SCORE_COSTS[score]
    if cost > POINT_BUY_POINTS:
        raise ValueError("Point buy scores cannot cost more than 27 points")


def validate_random_scores(scores: dict[AbilityType, int], rolled_value: Any) -> None:
    if not isinstance(rolled_value, list):
        raise ValueError("Random scores must include the rolled score pool")
    try:
        rolled_scores = [int(score) for score in rolled_value]
    except (TypeError, ValueError):
        raise ValueError("Random scores must include valid rolled values") from None
    if len(rolled_scores) != len(tuple(AbilityType)) or any(score < RANDOM_SCORE_MINIMUM or score > RANDOM_SCORE_MAXIMUM for score in rolled_scores):
        raise ValueError("Random scores must include six scores from 3 to 18")
    if sorted(scores.values(), reverse=True) != sorted(rolled_scores, reverse=True):
        raise ValueError("Assign each rolled score exactly once")


def background_ability_increases_from_payload(value: Any, background: BackgroundType) -> dict[AbilityType, int]:
    if not isinstance(value, dict):
        raise ValueError("Choose background ability score increases")
    allowed = set(background_ability_options(background))
    increases: dict[AbilityType, int] = {}
    for ability in AbilityType:
        raw_increase = value.get(enum_key(ability), 0)
        try:
            increase = int(raw_increase)
        except (TypeError, ValueError):
            raise ValueError("Choose valid background ability score increases") from None
        if increase < 0 or increase > BACKGROUND_ABILITY_INCREASE_MAX:
            raise ValueError("Background ability increases must be 0, 1, or 2")
        if increase and ability not in allowed:
            raise ValueError("Background ability increases must use the selected background abilities")
        increases[ability] = increase
    non_zero = sorted(increase for increase in increases.values() if increase)
    if sum(increases.values()) != BACKGROUND_ABILITY_INCREASE_TOTAL or non_zero not in ([1, 1, 1], [1, 2]):
        raise ValueError("Background ability increases must be +2/+1 or +1/+1/+1")
    return increases


def background_ability_options(background: BackgroundType) -> tuple[AbilityType, ...]:
    options = background_definition(background).abilityScores
    return options or tuple(AbilityType)


def background_skill_proficiency_types(background: BackgroundType) -> list[SkillType]:
    skills: list[SkillType] = []
    for skill_key, proficiency in background_skill_proficiencies(background).items():
        skill = enum_value(SkillType, skill_key)
        if proficiency == ProficiencyLevel.PROFICIENT and skill is not None:
            skills.append(skill)
    return skills


def magic_initiate_spell_choices(background: BackgroundType) -> dict[str, Any] | None:
    from dnd_board.rules.spells import spell_entries_for_list

    spell_list = magic_initiate_spell_list(background)
    if spell_list is None:
        return None
    casting_ability = magic_initiate_casting_ability(background)
    cantrips = spell_entries_for_list(spell_list, exact_level=0, source=SpellSource.MAGIC_INITIATE, casting_ability=casting_ability)
    first_level_spells = spell_entries_for_list(spell_list, exact_level=1, source=SpellSource.MAGIC_INITIATE, casting_ability=casting_ability)
    return {
        "spellList": spell_list.value,
        "cantripsKnown": 2,
        "firstLevelSpellsKnown": 1,
        "cantrips": serialize_spell_options(cantrips),
        "firstLevelSpells": serialize_spell_options(first_level_spells),
    }


def magic_initiate_spells_from_payload(background: BackgroundType, value: Any) -> tuple[SpellId, ...]:
    spell_list = magic_initiate_spell_list(background)
    if spell_list is None:
        return ()
    if not isinstance(value, list):
        raise ValueError("Choose Magic Initiate spells")
    selected: list[SpellId] = []
    for item in value:
        spell_id = enum_value(SpellId, item)
        if spell_id is None:
            raise ValueError("Choose valid Magic Initiate spells")
        selected.append(spell_id)
    if len(set(selected)) != len(selected):
        raise ValueError("Choose each Magic Initiate spell once")
    cantrip_options = {option["value"] for option in magic_initiate_spell_choices(background)["cantrips"]}
    first_level_options = {option["value"] for option in magic_initiate_spell_choices(background)["firstLevelSpells"]}
    cantrips = [spell_id for spell_id in selected if enum_key(spell_id) in cantrip_options]
    first_level_spells = [spell_id for spell_id in selected if enum_key(spell_id) in first_level_options]
    if len(cantrips) != 2 or len(first_level_spells) != 1 or len(selected) != 3:
        raise ValueError("Choose two cantrips and one 1st-level spell for Magic Initiate")
    return tuple(selected)


def class_skill_proficiencies_from_payload(class_type: ClassType, value: Any) -> tuple[SkillType, ...]:
    expected_count = class_skill_proficiency_count(class_type)
    allowed = class_skill_options(class_type)
    if value in (None, ()) or value == []:
        return tuple(allowed[:expected_count])
    if not isinstance(value, list):
        raise ValueError("Choose class skill proficiencies")
    selected = skill_choices_from_payload(value)
    if len(selected) != expected_count:
        raise ValueError(f"Choose {expected_count} class skill proficiencies")
    if any(skill not in set(allowed) for skill in selected):
        raise ValueError("Choose valid class skill proficiencies")
    return tuple(selected)


def class_skill_proficiency_count(class_type: ClassType) -> int:
    return {
        ClassType.FIGHTER: 2,
        ClassType.ROGUE: 4,
        ClassType.WIZARD: 2,
    }[class_type]


def class_skill_options(class_type: ClassType) -> tuple[SkillType, ...]:
    from dnd_board.rules.progression import fighter_skill_option_types, rogue_skill_option_types, wizard_skill_option_types

    return tuple({
        ClassType.FIGHTER: fighter_skill_option_types,
        ClassType.ROGUE: rogue_skill_option_types,
        ClassType.WIZARD: wizard_skill_option_types,
    }[class_type]())


def class_expertise_from_payload(class_type: ClassType, value: Any, background: BackgroundType, class_skills: tuple[SkillType, ...]) -> tuple[SkillType, ...]:
    if class_type != ClassType.ROGUE:
        return ()
    expected_count = 2
    eligible: list[SkillType] = list(class_skills)
    for skill_key, proficiency in background_skill_proficiencies(background).items():
        skill = enum_value(SkillType, skill_key)
        if proficiency == ProficiencyLevel.PROFICIENT and skill is not None and skill not in eligible:
            eligible.append(skill)
    if value in (None, ()) or value == []:
        return tuple(eligible[:expected_count])
    if not isinstance(value, list):
        raise ValueError("Choose Rogue Expertise skills")
    selected = skill_choices_from_payload(value)
    if len(selected) != expected_count:
        raise ValueError(f"Choose {expected_count} Rogue Expertise skills")
    if any(skill not in set(eligible) for skill in selected):
        raise ValueError("Rogue Expertise requires a skill proficiency")
    return tuple(selected)


def fighting_style_from_payload(class_type: ClassType, value: Any) -> FightingStyleType | None:
    if class_type != ClassType.FIGHTER:
        return None
    if value in (None, ""):
        return next(iter(FightingStyleType))
    style = enum_value(FightingStyleType, value)
    if style is None:
        raise ValueError("Choose a Fighter Fighting Style")
    return style


def wizard_cantrips_from_payload(class_type: ClassType, value: Any) -> tuple[SpellId, ...]:
    if class_type != ClassType.WIZARD:
        return ()
    from dnd_board.rules.classes.wizard.base import is_wizard_cantrip_selection_valid
    from dnd_board.rules.classes.wizard.base import wizard_cantrip_options

    if value in (None, ()) or value == []:
        return tuple(spell.id for spell in wizard_cantrip_options(CHARACTER_BUILDER_STARTING_LEVEL)[:3])
    spells = wizard_spell_entries_from_payload(value)
    if not is_wizard_cantrip_selection_valid(CHARACTER_BUILDER_STARTING_LEVEL, spells):
        raise ValueError("Choose legal Wizard cantrips")
    return tuple(spell.id for spell in spells)


def wizard_spellbook_spells_from_payload(class_type: ClassType, value: Any) -> tuple[SpellId, ...]:
    if class_type != ClassType.WIZARD:
        return ()
    from dnd_board.rules.classes.wizard.base import is_wizard_spellbook_selection_valid
    from dnd_board.rules.classes.wizard.base import wizard_spellbook_spell_count, wizard_spellbook_spell_options

    if value in (None, ()) or value == []:
        count = wizard_spellbook_spell_count(CharacterClassLevel(name=ClassType.WIZARD, level=CHARACTER_BUILDER_STARTING_LEVEL))
        return tuple(spell.id for spell in wizard_spellbook_spell_options(CHARACTER_BUILDER_STARTING_LEVEL)[:count])
    spells = wizard_spell_entries_from_payload(value)
    if not is_wizard_spellbook_selection_valid(CHARACTER_BUILDER_STARTING_LEVEL, spells):
        raise ValueError("Choose legal Wizard spellbook spells")
    return tuple(spell.id for spell in spells)


def wizard_prepared_spells_from_payload(class_type: ClassType, value: Any, spellbook_spells: tuple[SpellId, ...]) -> tuple[SpellId, ...]:
    if class_type != ClassType.WIZARD:
        return ()
    from dnd_board.rules.classes.wizard.base import is_wizard_prepared_spell_selection_valid

    if value in (None, ()) or value == []:
        return tuple(spellbook_spells[:4])
    spells = wizard_spell_entries_from_payload(value)
    if not is_wizard_prepared_spell_selection_valid(CHARACTER_BUILDER_STARTING_LEVEL, spells):
        raise ValueError("Choose legal prepared Wizard spells")
    spellbook_ids = set(spellbook_spells)
    if any(spell.id not in spellbook_ids for spell in spells):
        raise ValueError("Prepared Wizard spells must be in your spellbook")
    return tuple(spell.id for spell in spells)


def wizard_spell_entries_from_payload(value: Any) -> list[SpellEntry]:
    from dnd_board.rules.classes.wizard.base import wizard_catalog_spell

    if not isinstance(value, list):
        raise ValueError("Choose Wizard spells")
    spells: list[SpellEntry] = []
    for item in value:
        spell_id = enum_value(SpellId, item)
        if spell_id is None:
            raise ValueError("Choose valid Wizard spells")
        spell = wizard_catalog_spell(spell_id)
        if spell is None:
            raise ValueError("Choose valid Wizard spells")
        spells.append(spell)
    if len({spell.id for spell in spells}) != len(spells):
        raise ValueError("Choose each Wizard spell once")
    return spells


def skill_choices_from_payload(value: list[Any]) -> list[SkillType]:
    selected: list[SkillType] = []
    for item in value:
        skill = enum_value(SkillType, item)
        if skill is None:
            raise ValueError("Choose valid skills")
        if skill not in selected:
            selected.append(skill)
    return selected


def background_spell_entries(background: BackgroundType, selected_spells: tuple[SpellId, ...]) -> list[SpellEntry]:
    from dnd_board.rules.spells import spell_entry_for_list

    spell_list = magic_initiate_spell_list(background)
    if spell_list is None:
        return []
    casting_ability = magic_initiate_casting_ability(background)
    spells = []
    for spell_id in selected_spells:
        spell = spell_entry_for_list(spell_id, spell_list, source=SpellSource.MAGIC_INITIATE, casting_ability=casting_ability)
        if spell is not None and spell.level == 1:
            spell = replace(
                spell,
                status=SpellStatus(
                    source=spell.source,
                    castingAbility=spell.castingAbility,
                    resourceId=magic_initiate_resource_id(spell.id),
                    reset=RestType.LONG_REST,
                ),
            )
        spells.append(spell)
    return [spell for spell in spells if spell is not None]


def builder_spell_entries(request: CharacterBuilderRequest) -> list[SpellEntry]:
    return [
        *background_spell_entries(request.background, request.magic_initiate_spells),
        *wizard_spell_entries(request.wizard_cantrips),
        *wizard_spell_entries(request.wizard_prepared_spells),
    ]


def wizard_spellbook_entries(request: CharacterBuilderRequest) -> list[SpellEntry]:
    return wizard_spell_entries(request.wizard_spellbook_spells)


def wizard_spell_entries(spell_ids: tuple[SpellId, ...]) -> list[SpellEntry]:
    from dnd_board.rules.classes.wizard.base import wizard_catalog_spell

    return [spell for spell_id in spell_ids if (spell := wizard_catalog_spell(spell_id)) is not None]


def builder_skill_proficiencies(background: BackgroundType, class_skills: tuple[SkillType, ...], expertise: tuple[SkillType, ...]) -> dict[str, ProficiencyLevel]:
    skills = dict(background_skill_proficiencies(background))
    for skill in class_skills:
        skills[enum_key(skill)] = ProficiencyLevel.PROFICIENT
    for skill in expertise:
        skills[enum_key(skill)] = ProficiencyLevel.EXPERTISE
    return skills


def background_spell_resources(background: BackgroundType, selected_spells: tuple[SpellId, ...]) -> list[ResourceTracker]:
    spells = background_spell_entries(background, selected_spells)
    return [
        ResourceTracker(
            id=magic_initiate_resource_id(spell.id),
            name=f"{enum_label(spell.id)} Free Cast",
            currentUses=1,
            maxUses=1,
            reset=RestType.LONG_REST,
            activation=TimeEconomy.ACTION,
            description=f"Cast {enum_label(spell.id)} once without expending a spell slot. Resets on a Long Rest.",
            source=enum_label(SpellSource.MAGIC_INITIATE),
        )
        for spell in spells
        if spell.level == 1
    ]


def magic_initiate_resource_id(spell_id: SpellId) -> str:
    return f"magicInitiate{enum_key(spell_id)[0].upper()}{enum_key(spell_id)[1:]}FreeCast"


def magic_initiate_spell_list(background: BackgroundType):
    from dnd_board.rules.spells import SpellListType

    feat = background_definition(background).feat
    return {
        BackgroundOriginFeatType.MAGIC_INITIATE_CLERIC: SpellListType.CLERIC,
        BackgroundOriginFeatType.MAGIC_INITIATE_DRUID: SpellListType.DRUID,
        BackgroundOriginFeatType.MAGIC_INITIATE_WIZARD: SpellListType.WIZARD,
    }.get(feat)


def magic_initiate_casting_ability(background: BackgroundType) -> AbilityType:
    feat = background_definition(background).feat
    if feat == BackgroundOriginFeatType.MAGIC_INITIATE_WIZARD:
        return AbilityType.INTELLIGENCE
    return AbilityType.WISDOM


def serialize_spell_options(spells: list[SpellEntry]) -> list[dict[str, Any]]:
    return [
        {
            "value": enum_key(spell.id),
            "label": enum_label(spell.id),
            "school": enum_key(spell.school),
            "level": spell.level,
            "castingTime": enum_key(spell.castingTime),
            "castingTimeLabel": spell.castingTimeLabel,
            "range": spell.targeting.summary,
            "duration": spell.duration.summary,
            "components": [enum_label(component) for component in spell.components],
        }
        for spell in spells
    ]


def selected_tool_from_payload(background: BackgroundType, value: Any) -> ToolType | None:
    options = background_tool_options(background)
    if not options:
        return None
    if value in {None, ""}:
        return options[0]
    selected = enum_value(ToolType, value)
    if selected not in options:
        raise ValueError("Choose a valid tool proficiency for the selected background")
    return selected


def background_proficiencies(tool: ToolType | None) -> list[str]:
    return [enum_label(tool)] if tool else []


def fixed_max_hp(class_type: ClassType, level: int, ability_scores: AbilityScores, race: SpeciesType = SpeciesType.HUMAN, background: BackgroundType = BackgroundType.WAYFARER) -> int:
    hit_die = class_hit_die(class_type)
    constitution = ability_modifier(ability_scores.constitution)
    origin_bonus = species_hit_point_bonus(race, level) + background_hit_point_bonus(background, level)
    return max(1, hit_die + constitution + sum(fixed_hit_point_increases(class_type, level, ability_scores)) + origin_bonus)


def fixed_hit_point_increases(class_type: ClassType, level: int, ability_scores: AbilityScores) -> list[int]:
    if level <= 1:
        return []
    hit_die = class_hit_die(class_type)
    constitution = ability_modifier(ability_scores.constitution)
    bump = max(1, (hit_die // 2 + 1) + constitution)
    return [bump for _level in range(2, level + 1)]


def ability_modifier(score: int) -> int:
    return (score - 10) // 2


def clean_text(value: Any, fallback: str, limit: int) -> str:
    text = str(value or "").strip()
    return text[:limit] if text else fallback
