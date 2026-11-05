from collections import Counter

from dnd_board.character_sheet import FightingStyleType
from dnd_board.rules.feats import (
    FIGHTING_STYLE_FEATS,
    GENERAL_FEATS,
    FeatCategory,
    GeneralFeatType,
    fighting_style_label,
    fighting_style_source,
    general_feat_category,
)
from dnd_board.rules.sources import RuleSource, is_legacy_source, rule_source_label


def test_2024_feat_index_categories_and_sources() -> None:
    assert set(GENERAL_FEATS) == set(GeneralFeatType)
    assert set(FIGHTING_STYLE_FEATS) == set(FightingStyleType)
    assert Counter(definition.category for definition in GENERAL_FEATS.values()) == {
        FeatCategory.ORIGIN: 35,
        FeatCategory.GENERAL: 118,  # Includes retained feats absent from the 2024 index.
        FeatCategory.EPIC_BOON: 32,
        FeatCategory.DRAGONMARK: 13,
        FeatCategory.GREATER_DRAGONMARK: 14,
        FeatCategory.PLANAR_PACT: 2,
        FeatCategory.GREATER_PLANAR_PACT: 4,
        FeatCategory.DARK_GIFT: 9,
    }
    assert all(general_feat_category(feat) == definition.category for feat, definition in GENERAL_FEATS.items())

    arcana_general = {
        feat for feat, definition in GENERAL_FEATS.items()
        if definition.source is RuleSource.ARCANA_UNLEASHED
    }
    assert len(arcana_general) == 28
    assert all(not GENERAL_FEATS[feat].mechanics.interactions for feat in arcana_general)
    assert fighting_style_source(FightingStyleType.ARCANE_WARRIOR) is RuleSource.ARCANA_UNLEASHED
    assert fighting_style_label(FightingStyleType.ARCANE_WARRIOR) == "Arcane Warrior"
    assert GENERAL_FEATS[GeneralFeatType.SHARP_EYE].source is RuleSource.RAVENLOFT_THE_HORRORS_WITHIN_2024
    assert GENERAL_FEATS[GeneralFeatType.SURVIVOR].source is RuleSource.RAVENLOFT_THE_HORRORS_WITHIN_2024
    assert GENERAL_FEATS[GeneralFeatType.SHIFTING_COMBATANT].source is RuleSource.DND_BEYOND_DROPS_2026
    assert GENERAL_FEATS[GeneralFeatType.TACTICAL_COMBATANT].source is RuleSource.DND_BEYOND_DROPS_2026


def test_2014_phb_feats_remain_available_as_legacy() -> None:
    for feat in (
        GeneralFeatType.DUNGEON_DELVER,
        GeneralFeatType.LINGUIST,
        GeneralFeatType.MARTIAL_ADEPT,
        GeneralFeatType.MOBILE,
    ):
        assert GENERAL_FEATS[feat].source is RuleSource.PLAYERS_HANDBOOK_2014
        assert general_feat_category(feat) is FeatCategory.GENERAL
    assert is_legacy_source(RuleSource.PLAYERS_HANDBOOK_2014)
    assert rule_source_label(RuleSource.PLAYERS_HANDBOOK_2014) == "Player's Handbook (2014)"
