from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from dnd_board.application.character_state_service import (
    CharacterStatePersistence,
    clear_active_concentration,
)
from dnd_board.application.persistence import fog_to_dict, token_to_dict
from dnd_board.application.room_state import Asset, Board, Player, RevealedArea, Room, Token
from dnd_board.character_sheet import TokenKind, enum_key


@dataclass(frozen=True)
class BoardOperations:
    broadcast: Callable[[Room, dict[str, Any]], Awaitable[None]]
    broadcast_room: Callable[[Room], Awaitable[None]]
    send: Callable[[Player, dict[str, Any]], Awaitable[None]]
    get_board: Callable[[str, str | None], Board | None]
    get_asset: Callable[[str, str], Asset | None]
    get_room_board: Callable[[Room], Board]
    board_to_dict: Callable[[Board], dict[str, Any]]
    remove_pending_rolls: Callable[[Room, str], None]
    state_persistence: CharacterStatePersistence
    default_token_color: str
    minimum_token_radius: float
    maximum_token_radius: float
    default_token_radius: float
    minimum_reveal_distance: float
    reveal_distance_ratio: float


async def lock_token(room: Room, player: Player, token_id: str, message: dict[str, Any] | None, operations: BoardOperations) -> None:
    token = room.tokens.get(token_id)
    if token is None:
        return
    if not can_control_token(player, token):
        await operations.send(player, {"type": "token_lock_denied", "tokenId": token_id, "reason": "not_owner"})
        return
    if token.lockedBy and token.lockedBy != player.player_key:
        await operations.send(player, {"type": "token_lock_denied", "tokenId": token_id, "lockedBy": token.lockedBy})
        return
    if message is not None:
        apply_token_radius_from_message(room, player, token, message, operations)
    token.lockedBy = player.player_key
    await _broadcast_token(room, token, operations)


async def move_token(room: Room, player: Player, token_id: str, message: dict[str, Any], operations: BoardOperations) -> None:
    token = room.tokens.get(token_id)
    if token is None or token.lockedBy != player.player_key or not can_control_token(player, token):
        return
    board = operations.get_room_board(room)
    apply_token_radius_from_message(room, player, token, message, operations)
    token.x = clamp(to_float(message.get("x")), token.radius, board.width - token.radius)
    token.y = clamp(to_float(message.get("y")), token.radius, board.height - token.radius)
    await _broadcast_token(room, token, operations)


async def release_token(room: Room, player: Player, token_id: str, operations: BoardOperations) -> None:
    token = room.tokens.get(token_id)
    if token is None or token.lockedBy != player.player_key or not can_control_token(player, token):
        return
    token.lockedBy = None
    await _broadcast_token(room, token, operations)


async def set_token_scene(room: Room, player: Player, token_id: str, message: dict[str, Any], operations: BoardOperations) -> None:
    token = room.tokens.get(token_id)
    if token is None or token.lockedBy != player.player_key or not can_control_token(player, token):
        return
    token.inScene = bool(message.get("inScene"))
    if token.inScene:
        board = operations.get_room_board(room)
        apply_token_radius_from_message(room, player, token, message, operations)
        token.x = clamp(to_float(message.get("x", token.x)), token.radius, board.width - token.radius)
        token.y = clamp(to_float(message.get("y", token.y)), token.radius, board.height - token.radius)
    await _broadcast_token(room, token, operations)


async def set_token_radius(room: Room, player: Player, token_id: str, radius: Any, operations: BoardOperations) -> Token | None:
    if not is_dm(player):
        return None
    token = room.tokens.get(token_id)
    if token is None:
        return None
    board = operations.get_room_board(room)
    token.radius = clamp(to_float(radius), operations.minimum_token_radius, max_token_radius(board, operations))
    token.x = clamp(token.x, token.radius, board.width - token.radius)
    token.y = clamp(token.y, token.radius, board.height - token.radius)
    await _broadcast_token(room, token, operations)
    await operations.broadcast_room(room)
    return token


def apply_token_radius_from_message(room: Room, player: Player, token: Token, message: dict[str, Any], operations: BoardOperations) -> None:
    if not is_dm(player) or "radius" not in message:
        return
    board = operations.get_room_board(room)
    token.radius = clamp(to_float(message.get("radius")), operations.minimum_token_radius, max_token_radius(board, operations))


async def set_fog_mode(room: Room, player: Player, message: dict[str, Any], operations: BoardOperations) -> None:
    if not is_dm(player):
        return
    room.fog.hideMode = bool(message.get("hideMode"))
    room.fog.brushSize = clamp(to_float(message.get("brushSize", room.fog.brushSize)), 20, 360)
    if not room.fog.hideMode:
        room.fog.revealedAreas = []
    await operations.broadcast(room, {"type": "fog_updated", "fog": fog_to_dict(room.fog)})


async def reveal_fog(room: Room, player: Player, message: dict[str, Any], operations: BoardOperations) -> None:
    if not is_dm(player) or not room.fog.hideMode:
        return
    board = operations.get_room_board(room)
    area = RevealedArea(
        x=clamp(to_float(message.get("x")), 0, board.width),
        y=clamp(to_float(message.get("y")), 0, board.height),
        radius=clamp(to_float(message.get("radius", room.fog.brushSize)), 20, 360),
    )
    if is_redundant_reveal_area(room.fog.revealedAreas, area, operations):
        return
    room.fog.revealedAreas.append(area)
    await operations.broadcast(room, {"type": "fog_updated", "fog": fog_to_dict(room.fog)})


def is_redundant_reveal_area(revealed_areas: list[RevealedArea], area: RevealedArea, operations: BoardOperations) -> bool:
    if not revealed_areas:
        return False
    previous = revealed_areas[-1]
    if abs(previous.radius - area.radius) > 0.001:
        return False
    minimum = max(operations.minimum_reveal_distance, area.radius * operations.reveal_distance_ratio)
    return ((previous.x - area.x) ** 2 + (previous.y - area.y) ** 2) ** 0.5 < minimum


async def set_board(room: Room, player: Player, board_id: str, operations: BoardOperations) -> None:
    if not is_dm(player):
        return
    board = operations.get_board(board_id, room.id)
    if board is None:
        return
    changed = room.board_id != board.id
    room.board_id = board.id
    await operations.broadcast(room, {"type": "board_updated", "board": operations.board_to_dict(board)})
    if changed and room.fog.hideMode:
        room.fog.revealedAreas = []
        await operations.broadcast(room, {"type": "fog_updated", "fog": fog_to_dict(room.fog)})


async def load_asset_token(room: Room, player: Player, asset_kind: str, asset_id: str, operations: BoardOperations) -> None:
    if not is_dm(player):
        return
    asset = operations.get_asset(asset_kind, asset_id)
    if asset is None:
        return
    board = operations.get_room_board(room)
    token = Token(
        id=f"{enum_key(asset.kind)}-{room.next_token_number}",
        kind=TokenKind.ASSET,
        name=asset.name,
        owner="dm",
        color=operations.default_token_color,
        x=board.width / 2,
        y=board.height / 2,
        radius=default_token_radius(board, operations),
        inScene=True,
        avatarUrl=asset.avatarUrl,
    )
    room.next_token_number += 1
    room.tokens[token.id] = token
    await _broadcast_token(room, token, operations)


async def delete_token(room: Room, player: Player, token_id: str, operations: BoardOperations) -> None:
    if not is_dm(player):
        return
    token = room.tokens.get(token_id)
    if token is None or token.kind == TokenKind.CHARACTER:
        return
    room.tokens.pop(token_id)
    operations.remove_pending_rolls(room, token_id)
    for state in (
        room.hit_points, room.temporary_hit_points, room.max_hit_point_increases,
        room.max_hit_point_reductions, room.exhaustion_levels, room.condition_overrides,
        room.suppressed_conditions, room.condition_durations, room.condition_removals,
        room.damage_resistances, room.damage_vulnerabilities, room.damage_immunities,
        room.ongoing_effects, room.scheduled_effects,
    ):
        state.pop(token_id, None)
    clear_active_concentration(room, token_id, operations.state_persistence)
    await operations.broadcast(room, {"type": "token_deleted", "tokenId": token_id})


async def clear_scene(room: Room, player: Player, operations: BoardOperations) -> None:
    if not is_dm(player):
        return
    for token in room.tokens.values():
        token.inScene = False
        token.lockedBy = None
    await operations.broadcast_room(room)


def can_control_token(player: Player, token: Token) -> bool:
    return is_dm(player) or player.player_key == token.owner


def is_dm(player: Player) -> bool:
    return player.player_key == "dm"


def max_token_radius(board: Board, operations: BoardOperations) -> float:
    return min(operations.maximum_token_radius, max(operations.minimum_token_radius, min(board.width, board.height) / 3))


def default_token_radius(board: Board, operations: BoardOperations) -> float:
    return clamp(operations.default_token_radius, operations.minimum_token_radius, max_token_radius(board, operations))


def to_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0


def clamp(value: float, minimum: float, maximum: float) -> float:
    return min(maximum, max(minimum, value))


async def _broadcast_token(room: Room, token: Token, operations: BoardOperations) -> None:
    await operations.broadcast(room, {"type": "token_updated", "token": token_to_dict(token)})
