from __future__ import annotations

from enum import Enum, auto

from dnd_board.character_sheet import CharacterClassLevel, SheetFeature, TimeEconomy, enum_key, enum_label
from dnd_board.rules.classes.fighter.base import FighterSubclassType


class ChampionFeatureType(Enum):
    IMPROVED_CRITICAL = auto()
    REMARKABLE_ATHLETE = auto()
    ADDITIONAL_FIGHTING_STYLE = auto()
    HEROIC_WARRIOR = auto()
    SUPERIOR_CRITICAL = auto()
    SURVIVOR = auto()


def champion_features(character_class: CharacterClassLevel, fighter_level_value: int) -> list[SheetFeature]:
    if character_class.subclass != FighterSubclassType.CHAMPION:
        return []

    features = [
        champion_feature(
            ChampionFeatureType.IMPROVED_CRITICAL,
            "Weapon and Unarmed Strike attacks score a Critical Hit on a d20 roll of 19 or 20.",
            3,
        ),
        champion_feature(
            ChampionFeatureType.REMARKABLE_ATHLETE,
            "Advantage on Initiative rolls and Strength (Athletics) checks; after scoring a Critical Hit, move up to half Speed without provoking Opportunity Attacks.",
            3,
        ),
        champion_feature(
            ChampionFeatureType.ADDITIONAL_FIGHTING_STYLE,
            "Gain another Fighting Style feat.",
            7,
        ),
        champion_feature(
            ChampionFeatureType.HEROIC_WARRIOR,
            "During combat, gain Heroic Inspiration when starting your turn without it.",
            10,
        ),
        champion_feature(
            ChampionFeatureType.SUPERIOR_CRITICAL,
            "Weapon and Unarmed Strike attacks score a Critical Hit on a d20 roll of 18-20.",
            15,
        ),
        champion_feature(
            ChampionFeatureType.SURVIVOR,
            "Gain death save resilience and regain hit points at the start of your turn while Bloodied and above 0 HP.",
            18,
        ),
    ]
    return [feature for minimum_level, feature in features if fighter_level_value >= minimum_level]


def champion_feature(feature_type: ChampionFeatureType, description: str, minimum_level: int) -> tuple[int, SheetFeature]:
    return (
        minimum_level,
        SheetFeature(
            id=enum_key(feature_type),
            name=enum_label(feature_type),
            source=enum_label(FighterSubclassType.CHAMPION),
            activation=TimeEconomy.PASSIVE,
            description=description,
        ),
    )
