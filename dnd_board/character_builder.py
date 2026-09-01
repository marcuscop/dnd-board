from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, TypeVar

from dnd_board.character_sheet import (
    AbilityScores,
    AbilityType,
    CharacterClassLevel,
    ClassType,
    PartyMemberConfig,
    PartyMemberSheet,
    ProgressionChoiceOption,
    enum_key,
    enum_label,
    enum_value,
    serialize_dataclass,
)
from dnd_board.rules.backgrounds import (
    BackgroundEquipmentChoice,
    BackgroundType,
    ToolType,
    background_definition,
    background_equipment,
    background_features_for_tool,
    background_feats,
    background_hit_point_bonus,
    background_label,
    background_skill_proficiencies,
    background_tool_options,
)
from dnd_board.rules.progression import class_hit_die
from dnd_board.rules.species import SpeciesType, species_definition, species_hit_point_bonus, species_label, species_traits


CHARACTER_BUILDER_STARTING_LEVEL = 1
SUPPORTED_CLASS_TYPES = (ClassType.FIGHTER, ClassType.ROGUE)
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


class CharacterBuilderOptionField(Enum):
    CLASSES = "classes"
    RACES = "races"
    BACKGROUNDS = "backgrounds"
    ABILITY_SCORE_METHODS = "abilityScoreMethods"
    STANDARD_ARRAY = "standardArray"
    POINT_BUY_COSTS = "pointBuyCosts"
    POINT_BUY_POINTS = "pointBuyPoints"
    BACKGROUND_DETAILS = "backgroundDetails"


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
    ability_scores: AbilityScores


def character_builder_options() -> dict[str, Any]:
    return {
        option_key(CharacterBuilderOptionField.CLASSES): serialize_options(enum_options(SUPPORTED_CLASS_TYPES)),
        option_key(CharacterBuilderOptionField.RACES): serialize_options(enum_options(SpeciesType)),
        option_key(CharacterBuilderOptionField.BACKGROUNDS): serialize_options(enum_options(BackgroundType)),
        option_key(CharacterBuilderOptionField.ABILITY_SCORE_METHODS): serialize_options(enum_options(AbilityScoreGenerationMethod)),
        option_key(CharacterBuilderOptionField.STANDARD_ARRAY): list(STANDARD_ARRAY_SCORES),
        option_key(CharacterBuilderOptionField.POINT_BUY_COSTS): POINT_BUY_SCORE_COSTS,
        option_key(CharacterBuilderOptionField.POINT_BUY_POINTS): POINT_BUY_POINTS,
        option_key(CharacterBuilderOptionField.BACKGROUND_DETAILS): background_details(),
    }


def character_builder_request_from_payload(payload: dict[str, Any], *, default_member_id: str, default_owner: str) -> CharacterBuilderRequest:
    class_type = enum_value(ClassType, payload_value(payload, CharacterBuilderPayloadField.CLASS_NAME, enum_key(ClassType.FIGHTER)))
    if class_type not in SUPPORTED_CLASS_TYPES:
        raise ValueError("Choose Fighter or Rogue")

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
        ability_scores=ability_scores,
    )


def build_party_member_config(request: CharacterBuilderRequest) -> PartyMemberConfig:
    species = species_definition(request.race)
    return PartyMemberConfig(
        id=request.member_id,
        name=request.name,
        maxHp=fixed_max_hp(request.class_type, CHARACTER_BUILDER_STARTING_LEVEL, request.ability_scores, request.race, request.background),
        abilityScores=request.ability_scores,
        sheet=PartyMemberSheet(
            race=species_label(request.race),
            background=background_label(request.background),
            classes=[
                CharacterClassLevel(
                    name=request.class_type,
                    level=CHARACTER_BUILDER_STARTING_LEVEL,
                )
            ],
            speed=species.speed,
            skills=background_skill_proficiencies(request.background) or None,
            proficiencies=background_proficiencies(request.tool_proficiency) or None,
            feats=background_feats(request.background) or None,
            traits=species_traits(request.race) or None,
            features=background_features_for_tool(request.background, request.tool_proficiency) or None,
            equipment=background_equipment(request.background, request.equipment_choice) or None,
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
            "toolOptions": serialize_options(enum_options(background_tool_options(background_type))),
            "equipmentChoices": serialize_options(enum_options(BackgroundEquipmentChoice)),
        }
        for background_type in BackgroundType
    }


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
