from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from fastapi import WebSocket

from dnd_board.character_sheet import (
    AbilityType,
    CharacterSheet,
    ConditionDuration,
    ConditionType,
    DamageType,
    EquipmentSlot,
    HitPoints,
    RollLogEntry,
    RollPayload,
    RollSource,
    ResolutionInterceptorPrompt,
    RestType,
    SpellId,
    TokenKind,
)
from dnd_board.rules.shared.character_effects import CharacterEffectExecution
from dnd_board.rules.encounter import EncounterState
from dnd_board.rules.shared.effects import (
    ActiveOngoingEffect,
    ActiveScheduledEffect,
    EffectNodeId,
    ResolutionEventType,
)


@dataclass
class Token:
    id: str
    kind: TokenKind
    name: str
    owner: str
    color: str
    x: float
    y: float
    radius: float
    inScene: bool
    avatarUrl: str | None = None
    lockedBy: str | None = None


@dataclass
class Player:
    id: str
    name: str
    player_key: str
    websocket: WebSocket | None
    room_id: str | None = None


@dataclass
class RevealedArea:
    x: float
    y: float
    radius: float


@dataclass
class FogState:
    hideMode: bool
    brushSize: float
    revealedAreas: list[RevealedArea]


@dataclass
class Board:
    id: str
    name: str
    url: str | None
    width: int
    height: int


@dataclass
class Asset:
    id: str
    kind: TokenKind
    name: str
    avatarUrl: str


@dataclass
class Campaign:
    id: str
    name: str
    path: Path


@dataclass
class ConditionRemovalSave:
    savingThrow: AbilityType
    saveDc: int
    advantage: bool = False


@dataclass
class ActiveConditionSource:
    targetSheetId: str
    condition: ConditionType
    spellId: SpellId
    casterSheetId: str
    wasAlreadyActive: bool = False


@dataclass
class ActiveConcentration:
    casterSheetId: str
    spellId: SpellId
    spellName: str
    conditionSources: list[ActiveConditionSource]


@dataclass
class ActiveMaxHitPointReduction:
    amount: int
    source: RollSource
    sourceName: str
    reset: RestType


@dataclass
class ActiveMaxHitPointIncrease:
    amount: int
    source: RollSource
    sourceName: str


class DamageDefenseType(Enum):
    RESISTANCE = "resistance"
    VULNERABILITY = "vulnerability"
    IMMUNITY = "immunity"


@dataclass(frozen=True)
class CharacterRuntimeSnapshot:
    hitPoints: HitPoints
    conditions: tuple[ConditionType, ...]
    suppressedConditions: tuple[ConditionType, ...]
    damageResistances: tuple[DamageType, ...]
    damageVulnerabilities: tuple[DamageType, ...]
    damageImmunities: tuple[DamageType, ...]
    ongoingEffects: tuple[ActiveOngoingEffect, ...]


@dataclass(frozen=True)
class InteractionEventKey:
    eventType: ResolutionEventType
    effectNodeId: EffectNodeId | None


@dataclass
class PendingCharacterResolution:
    active: CharacterEffectExecution
    roll: RollPayload
    targetSheetId: str
    responseRolls: list[RollPayload]
    outcomePrefixes: list[str]
    ignoredInterceptors: list[str]
    participantSnapshots: dict[str, CharacterRuntimeSnapshot]
    interactionEvent: InteractionEventKey | None = None
    dispatchedEvents: set[InteractionEventKey] = field(default_factory=set)
    scheduledEffectStates: dict[str, list[ActiveScheduledEffect]] = field(default_factory=dict)
    touchedScheduledTargets: set[str] = field(default_factory=set)


@dataclass
class Room:
    id: str
    tokens: dict[str, Token]
    players: dict[str, Player]
    fog: FogState
    board_id: str
    next_token_number: int
    pending_rolls: dict[tuple[str, str, str, str], RollPayload]
    pending_resolution_prompts: dict[str, ResolutionInterceptorPrompt]
    roll_history: list[RollLogEntry]
    hit_points: dict[str, int]
    temporary_hit_points: dict[str, int]
    max_hit_point_increases: dict[str, list[ActiveMaxHitPointIncrease]]
    max_hit_point_reductions: dict[str, list[ActiveMaxHitPointReduction]]
    exhaustion_levels: dict[str, int]
    condition_overrides: dict[str, list[ConditionType]]
    suppressed_conditions: dict[str, list[ConditionType]]
    condition_durations: dict[str, dict[ConditionType, ConditionDuration]]
    condition_removals: dict[str, dict[ConditionType, ConditionRemovalSave]]
    active_concentrations: dict[str, ActiveConcentration]
    damage_resistances: dict[str, list[DamageType]]
    damage_vulnerabilities: dict[str, list[DamageType]]
    damage_immunities: dict[str, list[DamageType]]
    resource_uses: dict[str, dict[str, int]]
    equipment_slots: dict[str, dict[str, EquipmentSlot]]
    ongoing_effects: dict[str, list[ActiveOngoingEffect]]
    scheduled_effects: dict[str, list[ActiveScheduledEffect]]
    pending_effect_executions: dict[int, PendingCharacterResolution]
    encounter: EncounterState | None = None
