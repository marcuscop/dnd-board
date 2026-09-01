from __future__ import annotations

from enum import Enum, auto


class RuleSource(Enum):
    PLAYERS_HANDBOOK_2024 = auto()
    SYSTEM_REFERENCE_DOCUMENT = auto()
    FIZBANS_TREASURY_OF_DRAGONS = auto()
    GLORY_OF_THE_GIANTS = auto()
    FORGOTTEN_REALMS_HEROES_OF_FAERUN_2024 = auto()
    RAVENLOFT_THE_HORRORS_WITHIN_2024 = auto()
    XANATHARS_GUIDE_TO_EVERYTHING = auto()
    TASHAS_CAULDRON_OF_EVERYTHING = auto()
    UNEARTHED_ARCANA = auto()
    DND_BEYOND_DROPS_2026 = auto()
    LEGACY = auto()


def rule_source_label(source: RuleSource) -> str:
    labels = {
        RuleSource.PLAYERS_HANDBOOK_2024: "Player's Handbook (2024)",
        RuleSource.SYSTEM_REFERENCE_DOCUMENT: "System Reference Document",
        RuleSource.FIZBANS_TREASURY_OF_DRAGONS: "Fizban's Treasury of Dragons",
        RuleSource.GLORY_OF_THE_GIANTS: "Glory of the Giants",
        RuleSource.FORGOTTEN_REALMS_HEROES_OF_FAERUN_2024: "Forgotten Realms: Heroes of Faerun (2024)",
        RuleSource.RAVENLOFT_THE_HORRORS_WITHIN_2024: "Ravenloft: The Horrors Within (2024)",
        RuleSource.XANATHARS_GUIDE_TO_EVERYTHING: "Xanathar's Guide to Everything",
        RuleSource.TASHAS_CAULDRON_OF_EVERYTHING: "Tasha's Cauldron of Everything",
        RuleSource.UNEARTHED_ARCANA: "Unearthed Arcana",
        RuleSource.DND_BEYOND_DROPS_2026: "D&D Beyond Drops (2026)",
        RuleSource.LEGACY: "Legacy",
    }
    return labels[source]


def is_legacy_source(source: RuleSource) -> bool:
    return source == RuleSource.LEGACY
