from __future__ import annotations

from enum import Enum, auto


class RuleSource(Enum):
    PLAYERS_HANDBOOK_2024 = auto()
    FORGOTTEN_REALMS_HEROES_OF_FAERUN_2024 = auto()
    DND_BEYOND_DROPS_2026 = auto()
    LEGACY = auto()


def rule_source_label(source: RuleSource) -> str:
    labels = {
        RuleSource.PLAYERS_HANDBOOK_2024: "Player's Handbook (2024)",
        RuleSource.FORGOTTEN_REALMS_HEROES_OF_FAERUN_2024: "Forgotten Realms: Heroes of Faerun (2024)",
        RuleSource.DND_BEYOND_DROPS_2026: "D&D Beyond Drops (2026)",
        RuleSource.LEGACY: "Legacy",
    }
    return labels[source]


def is_legacy_source(source: RuleSource) -> bool:
    return source == RuleSource.LEGACY
