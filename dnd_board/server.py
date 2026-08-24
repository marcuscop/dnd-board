from __future__ import annotations

import json
from io import BytesIO
from dataclasses import asdict, dataclass
from pathlib import Path
from time import time_ns
from typing import Any, Literal

from fastapi import FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, UnidentifiedImageError
from pillow_heif import register_heif_opener

AssetKind = Literal["asset"]
TokenKind = Literal["character", "asset"]

BOARD_WIDTH = 1200
BOARD_HEIGHT = 720
MAX_PLAYERS = 8
DEFAULT_CAMPAIGN_ID = "test-campaign"
CAMPAIGN_DIR = Path("campaigns")
SHARED_DIR = Path("shared")
BOARD_DIR = Path("boards")
PARTY_DIR = Path("party")
SHARED_ASSET_DIR = SHARED_DIR / "assets"
UPLOAD_DIR = Path("data/uploads")
LEGACY_SAVE_DIR = Path("data/saves")
SAVE_DIR = LEGACY_SAVE_DIR
MAX_AVATAR_BYTES = 10 * 1024 * 1024
MAX_AVATAR_PIXELS = 16_000_000
MIN_TOKEN_RADIUS = 8
MAX_TOKEN_RADIUS = 480
DEFAULT_TOKEN_RADIUS = 70
DEFAULT_TOKEN_COLOR = "#111827"
MIN_REVEAL_POINT_DISTANCE = 8
REVEAL_POINT_DISTANCE_RATIO = 0.22

register_heif_opener()
Image.MAX_IMAGE_PIXELS = MAX_AVATAR_PIXELS


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
    kind: AssetKind
    name: str
    avatarUrl: str


@dataclass
class PartyMember:
    id: str
    name: str
    owner: str
    avatarUrl: str | None


@dataclass
class Campaign:
    id: str
    name: str
    path: Path


@dataclass
class Room:
    id: str
    tokens: dict[str, Token]
    players: dict[str, Player]
    fog: FogState
    board_id: str
    next_token_number: int


app = FastAPI()
rooms: dict[str, Room] = {}
next_connection_id = 1


@app.get("/health")
async def health() -> PlainTextResponse:
    return PlainTextResponse("ok")


@app.post("/api/rooms/{room_id}/tokens/{token_id}/avatar")
async def upload_avatar(room_id: str, token_id: str, playerKey: str, file: UploadFile = File(...)) -> dict[str, Any]:
    room = get_or_create_room(sanitize_room_id(room_id))
    token = room.tokens.get(token_id)
    if token is None:
        raise HTTPException(status_code=404, detail="Token not found")

    player = Player(id="http-upload", name="Uploader", player_key=normalize_player_key(playerKey, room.id), websocket=None)
    if not can_control_token(player, token):
        raise HTTPException(status_code=403, detail="Cannot update another player's avatar")

    content = await file.read()
    if len(content) > MAX_AVATAR_BYTES:
        raise HTTPException(status_code=400, detail="Avatar image is too large")

    avatar_png = convert_avatar_to_png(content)

    target_dir = UPLOAD_DIR / room.id / token.id
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / "avatar.png"
    target.write_bytes(avatar_png)

    token.avatarUrl = f"/uploads/{room.id}/{token.id}/avatar.png?v={time_ns()}"
    await broadcast(room, {"type": "token_updated", "token": token_to_dict(token)})
    return {"token": token_to_dict(token)}


@app.post("/api/rooms/{room_id}/tokens/{token_id}/radius")
async def resize_token(room_id: str, token_id: str, playerKey: str, radius: float) -> dict[str, Any]:
    room = get_or_create_room(sanitize_room_id(room_id))
    player = Player(id="http-resize", name="DM", player_key=normalize_player_key(playerKey, room.id), websocket=None, room_id=room.id)
    token = await set_token_radius(room, player, token_id, radius)
    if token is None:
        raise HTTPException(status_code=404 if is_dm(player) else 403, detail="Token resize failed")
    return {"token": token_to_dict(token)}


@app.post("/api/rooms/{room_id}/save")
async def save_room(room_id: str, playerKey: str) -> dict[str, Any]:
    sanitized_room_id = sanitize_room_id(room_id)
    if normalize_player_key(playerKey, sanitized_room_id) != "dm":
        raise HTTPException(status_code=403, detail="Only the DM can save room state")

    room = get_or_create_room(sanitized_room_id)
    save_room_to_disk(room)
    return {
        "roomId": room.id,
        "saved": True,
        "tokens": [token_to_dict(token) for token in room.tokens.values()],
        "fog": fog_to_dict(room.fog),
        "board": board_to_dict(get_room_board(room)),
    }


@app.get("/api/rooms/{room_id}/state")
async def get_room_state(room_id: str) -> dict[str, Any]:
    room = get_or_create_room(sanitize_room_id(room_id))
    return room_state_message(room)


@app.get("/campaigns/{campaign_id}/{asset_kind}/{filename}")
async def serve_campaign_asset(campaign_id: str, asset_kind: str, filename: str) -> FileResponse:
    campaign = get_campaign(sanitize_asset_id(campaign_id))
    if campaign is None or asset_kind not in {"boards", "party"}:
        raise HTTPException(status_code=404, detail="Asset not found")

    target = campaign.path / asset_kind / Path(filename).name
    if not target.is_file():
        raise HTTPException(status_code=404, detail="Asset not found")
    return FileResponse(target)


@app.post("/api/rooms/{room_id}/load")
async def load_room(room_id: str, playerKey: str) -> dict[str, Any]:
    sanitized_room_id = sanitize_room_id(room_id)
    if normalize_player_key(playerKey, sanitized_room_id) != "dm":
        raise HTTPException(status_code=403, detail="Only the DM can load room state")

    room = get_or_create_room(sanitized_room_id)
    loaded = await load_room_from_disk(room, Player(id="http-load", name="DM", player_key="dm", websocket=None))
    if not loaded:
        raise HTTPException(status_code=404, detail="No saved room state found")

    return {
        "roomId": room.id,
        "loaded": True,
        "tokens": [token_to_dict(token) for token in room.tokens.values()],
        "fog": fog_to_dict(room.fog),
        "board": board_to_dict(get_room_board(room)),
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    global next_connection_id
    await websocket.accept()
    player = Player(id=f"connection-{next_connection_id}", name="Player", player_key="", websocket=websocket)
    next_connection_id += 1
    await send(player, {"type": "hello", "playerId": player.id})

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                continue

            await handle_message(player, message)
    except WebSocketDisconnect:
        await leave_room(player)


async def handle_message(player: Player, message: dict[str, Any]) -> None:
    message_type = message.get("type")

    if message_type == "join_room":
        await join_room(
            player,
            str(message.get("roomId", "table")),
            str(message.get("playerName", "Player")),
            str(message.get("playerKey", "")),
        )
        return

    room = get_player_room(player)
    if room is None:
        return

    if message_type == "request_token_lock":
        await lock_token(room, player, str(message.get("tokenId", "")), message)
        return

    if message_type == "move_token":
        await move_token(room, player, str(message.get("tokenId", "")), message)
        return

    if message_type == "release_token":
        await release_token(room, player, str(message.get("tokenId", "")))
        return

    if message_type == "set_token_scene":
        await set_token_scene(room, player, str(message.get("tokenId", "")), message)
        return

    if message_type == "set_token_radius":
        await set_token_radius(room, player, str(message.get("tokenId", "")), message.get("radius"))
        return

    if message_type == "set_fog_mode":
        await set_fog_mode(room, player, message)
        return

    if message_type == "reveal_fog":
        await reveal_fog(room, player, message)
        return

    if message_type == "set_board":
        await set_board(room, player, str(message.get("boardId", "")))
        return

    if message_type == "load_asset":
        await load_asset_token(room, player, str(message.get("assetKind", "")), str(message.get("assetId", "")))
        return

    if message_type == "delete_token":
        await delete_token(room, player, str(message.get("tokenId", "")))
        return

    if message_type == "clear_scene":
        await clear_scene(room, player)


async def join_room(player: Player, requested_room_id: str, player_name: str, player_key: str) -> None:
    await leave_room(player)

    room_id = sanitize_room_id(requested_room_id)
    room = get_or_create_room(room_id)

    if len(room.players) >= MAX_PLAYERS:
        if player.websocket is not None:
            await player.websocket.close(code=1008, reason="Room is full")
        return

    player.room_id = room_id
    player.player_key = normalize_player_key(player_key, room_id)
    player.name = player_name.strip()[:24] or "Player"
    room.players[player.id] = player

    await broadcast_room_state(room)


async def leave_room(player: Player) -> None:
    if player.room_id is None:
        return

    room = rooms.get(player.room_id)
    player.room_id = None
    if room is None:
        return

    room.players.pop(player.id, None)
    for token in room.tokens.values():
        if token.lockedBy == player.player_key:
            token.lockedBy = None
            await broadcast(room, {"type": "token_updated", "token": token_to_dict(token)})

    await broadcast(room, {"type": "player_count", "count": len(room.players)})

    if not room.players:
        rooms.pop(room.id, None)


async def lock_token(room: Room, player: Player, token_id: str, message: dict[str, Any] | None = None) -> None:
    token = room.tokens.get(token_id)
    if token is None:
        return

    if not can_control_token(player, token):
        await send(player, {"type": "token_lock_denied", "tokenId": token_id, "reason": "not_owner"})
        return

    if token.lockedBy and token.lockedBy != player.player_key:
        await send(player, {"type": "token_lock_denied", "tokenId": token_id, "lockedBy": token.lockedBy})
        return

    if message is not None:
        apply_token_radius_from_message(room, player, token, message)
    token.lockedBy = player.player_key
    await broadcast(room, {"type": "token_updated", "token": token_to_dict(token)})


async def move_token(room: Room, player: Player, token_id: str, message: dict[str, Any]) -> None:
    token = room.tokens.get(token_id)
    if token is None or token.lockedBy != player.player_key or not can_control_token(player, token):
        return

    board = get_room_board(room)
    apply_token_radius_from_message(room, player, token, message)
    token.x = clamp(to_float(message.get("x")), token.radius, board.width - token.radius)
    token.y = clamp(to_float(message.get("y")), token.radius, board.height - token.radius)
    await broadcast(room, {"type": "token_updated", "token": token_to_dict(token)})


async def release_token(room: Room, player: Player, token_id: str) -> None:
    token = room.tokens.get(token_id)
    if token is None or token.lockedBy != player.player_key or not can_control_token(player, token):
        return

    token.lockedBy = None
    await broadcast(room, {"type": "token_updated", "token": token_to_dict(token)})


async def set_token_scene(room: Room, player: Player, token_id: str, message: dict[str, Any]) -> None:
    token = room.tokens.get(token_id)
    if token is None or token.lockedBy != player.player_key or not can_control_token(player, token):
        return

    token.inScene = bool(message.get("inScene"))
    if token.inScene:
        board = get_room_board(room)
        apply_token_radius_from_message(room, player, token, message)
        token.x = clamp(to_float(message.get("x", token.x)), token.radius, board.width - token.radius)
        token.y = clamp(to_float(message.get("y", token.y)), token.radius, board.height - token.radius)

    await broadcast(room, {"type": "token_updated", "token": token_to_dict(token)})


async def set_token_radius(room: Room, player: Player, token_id: str, radius: Any) -> Token | None:
    if not is_dm(player):
        return None

    token = room.tokens.get(token_id)
    if token is None:
        return None

    board = get_room_board(room)
    token.radius = clamp(to_float(radius), MIN_TOKEN_RADIUS, max_token_radius(board))
    token.x = clamp(token.x, token.radius, board.width - token.radius)
    token.y = clamp(token.y, token.radius, board.height - token.radius)
    await broadcast(room, {"type": "token_updated", "token": token_to_dict(token)})
    await broadcast_room_state(room)
    return token


def apply_token_radius_from_message(room: Room, player: Player, token: Token, message: dict[str, Any]) -> None:
    if not is_dm(player) or "radius" not in message:
        return

    board = get_room_board(room)
    token.radius = clamp(to_float(message.get("radius")), MIN_TOKEN_RADIUS, max_token_radius(board))


async def set_fog_mode(room: Room, player: Player, message: dict[str, Any]) -> None:
    if not is_dm(player):
        return

    hide_mode = bool(message.get("hideMode"))
    room.fog.hideMode = hide_mode
    room.fog.brushSize = clamp(to_float(message.get("brushSize", room.fog.brushSize)), 20, 360)
    if not hide_mode:
        room.fog.revealedAreas = []

    await broadcast(room, {"type": "fog_updated", "fog": fog_to_dict(room.fog)})


async def reveal_fog(room: Room, player: Player, message: dict[str, Any]) -> None:
    if not is_dm(player) or not room.fog.hideMode:
        return

    board = get_room_board(room)
    area = RevealedArea(
        x=clamp(to_float(message.get("x")), 0, board.width),
        y=clamp(to_float(message.get("y")), 0, board.height),
        radius=clamp(to_float(message.get("radius", room.fog.brushSize)), 20, 360),
    )
    if is_redundant_reveal_area(room.fog.revealedAreas, area):
        return

    room.fog.revealedAreas.append(area)
    await broadcast(room, {"type": "fog_updated", "fog": fog_to_dict(room.fog)})


def is_redundant_reveal_area(revealed_areas: list[RevealedArea], area: RevealedArea) -> bool:
    if not revealed_areas:
        return False

    previous = revealed_areas[-1]
    if abs(previous.radius - area.radius) > 0.001:
        return False

    min_distance = max(MIN_REVEAL_POINT_DISTANCE, area.radius * REVEAL_POINT_DISTANCE_RATIO)
    return ((previous.x - area.x) ** 2 + (previous.y - area.y) ** 2) ** 0.5 < min_distance


async def set_board(room: Room, player: Player, board_id: str) -> None:
    if not is_dm(player):
        return

    board = get_board(board_id, room.id)
    if board is None:
        return

    board_changed = room.board_id != board.id
    room.board_id = board.id
    await broadcast(room, {"type": "board_updated", "board": board_to_dict(board)})
    if board_changed and room.fog.hideMode:
        room.fog.revealedAreas = []
        await broadcast(room, {"type": "fog_updated", "fog": fog_to_dict(room.fog)})


async def load_asset_token(room: Room, player: Player, asset_kind: str, asset_id: str) -> None:
    if not is_dm(player):
        return

    asset = get_asset(asset_kind, asset_id)
    if asset is None:
        return

    board = get_room_board(room)
    token = Token(
        id=f"{asset.kind}-{room.next_token_number}",
        kind=asset.kind,
        name=asset.name,
        owner="dm",
        color=DEFAULT_TOKEN_COLOR,
        x=board.width / 2,
        y=board.height / 2,
        radius=default_token_radius(board),
        inScene=True,
        avatarUrl=asset.avatarUrl,
    )
    room.next_token_number += 1
    room.tokens[token.id] = token
    await broadcast(room, {"type": "token_updated", "token": token_to_dict(token)})


async def delete_token(room: Room, player: Player, token_id: str) -> None:
    if not is_dm(player):
        return

    token = room.tokens.get(token_id)
    if token is None or token.kind == "character":
        return

    room.tokens.pop(token_id)
    await broadcast(room, {"type": "token_deleted", "tokenId": token_id})


async def clear_scene(room: Room, player: Player) -> None:
    if not is_dm(player):
        return

    for token in room.tokens.values():
        token.inScene = False
        token.lockedBy = None
    await broadcast_room_state(room)


def get_or_create_room(room_id: str) -> Room:
    room = rooms.get(room_id)
    if room is not None:
        return room

    saved_board_id = load_saved_board_id(room_id)
    saved_tokens = load_saved_tokens(room_id, get_board(saved_board_id, room_id) or fallback_board())
    tokens = merge_saved_tokens_with_party(saved_tokens, room_id) if saved_tokens is not None else seed_tokens(room_id)
    room = Room(
        id=room_id,
        tokens={token.id: token for token in tokens},
        players={},
        fog=load_saved_fog(room_id),
        board_id=saved_board_id,
        next_token_number=next_dynamic_token_number(tokens),
    )
    rooms[room_id] = room
    return room


def seed_tokens(campaign_id: str | None = None) -> list[Token]:
    return [party_member_to_token(member, index) for index, member in enumerate(load_party_members(campaign_id))]


def party_member_to_token(member: PartyMember, index: int) -> Token:
    return Token(
        id=member.id,
        kind="character",
        name=member.name,
        owner=member.owner,
        color=DEFAULT_TOKEN_COLOR,
        x=240 + index * 80,
        y=260 + (index % 2) * 80,
        radius=DEFAULT_TOKEN_RADIUS,
        inScene=False,
        avatarUrl=member.avatarUrl,
    )


def merge_saved_tokens_with_party(saved_tokens: list[Token], campaign_id: str | None = None) -> list[Token]:
    saved_by_id = {token.id: token for token in saved_tokens}
    tokens: list[Token] = []
    for index, member in enumerate(load_party_members(campaign_id)):
        token = party_member_to_token(member, index)
        saved = saved_by_id.get(token.id)
        if saved is not None and saved.kind == "character":
            token.x = saved.x
            token.y = saved.y
            token.radius = saved.radius
            token.inScene = saved.inScene
        tokens.append(token)

    tokens.extend(token for token in saved_tokens if token.kind != "character")
    return tokens


def get_player_room(player: Player) -> Room | None:
    if player.room_id is None:
        return None
    return rooms.get(player.room_id)


def get_room_board(room: Room) -> Board:
    return get_board(room.board_id, room.id) or fallback_board()


def max_token_radius(board: Board) -> float:
    return min(MAX_TOKEN_RADIUS, max(MIN_TOKEN_RADIUS, min(board.width, board.height) / 3))


def default_token_radius(board: Board) -> float:
    return clamp(DEFAULT_TOKEN_RADIUS, MIN_TOKEN_RADIUS, max_token_radius(board))


async def broadcast_room_state(room: Room) -> None:
    await broadcast(room, room_state_message(room))


def room_state_message(room: Room) -> dict[str, Any]:
    return {
        "type": "room_state",
        "roomId": room.id,
        "players": [{"id": player.id, "name": player.name} for player in room.players.values()],
        "tokens": [token_to_dict(token) for token in room.tokens.values()],
        "fog": fog_to_dict(room.fog),
        "board": board_to_dict(get_room_board(room)),
        "boards": [board_to_dict(board) for board in list_boards(room.id)],
        "assets": [asset_to_dict(asset) for asset in list_assets()],
    }


async def broadcast(room: Room, message: dict[str, Any]) -> None:
    disconnected: list[Player] = []
    for player in room.players.values():
        try:
            await send(player, message)
        except (RuntimeError, WebSocketDisconnect):
            disconnected.append(player)

    for player in disconnected:
        await leave_room(player)


async def send(player: Player, message: dict[str, Any]) -> None:
    if player.websocket is None:
        return
    await player.websocket.send_text(json.dumps(message))


def token_to_dict(token: Token) -> dict[str, Any]:
    data = asdict(token)
    if data["lockedBy"] is None:
        data.pop("lockedBy")
    if data["avatarUrl"] is None:
        data.pop("avatarUrl")
    return data


def can_control_token(player: Player, token: Token) -> bool:
    return is_dm(player) or player.player_key == token.owner


def is_dm(player: Player) -> bool:
    return player.player_key == "dm"


def sanitize_room_id(room_id: str) -> str:
    sanitized = "".join(character for character in room_id.strip().lower() if character.isalnum() or character == "-")
    return sanitized[:40] or "table"


def normalize_player_key(player_key: str, campaign_id: str | None = None) -> str:
    normalized = player_key.strip().lower()
    party_members = load_party_members(campaign_id)
    valid_player_keys = {member.owner for member in party_members}
    if normalized in valid_player_keys or normalized == "dm":
        return normalized
    for member in party_members:
        if sanitize_asset_id(member.name) == sanitize_asset_id(normalized):
            return member.owner
    return "player-1"


def save_room_to_disk(room: Room) -> None:
    path = save_path(room.id)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "roomId": room.id,
        "tokens": [token_to_dict(token) for token in room.tokens.values()],
        "fog": fog_to_dict(room.fog),
        "boardId": room.board_id,
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


async def load_room_from_disk(room: Room, player: Player) -> bool:
    if not is_dm(player):
        return False

    saved_board_id = load_saved_board_id(room.id)
    saved_tokens = load_saved_tokens(room.id, get_board(saved_board_id, room.id) or fallback_board())
    if saved_tokens is None:
        return False

    tokens = merge_saved_tokens_with_party(saved_tokens, room.id)
    room.tokens = {token.id: token for token in tokens}
    room.fog = load_saved_fog(room.id)
    room.board_id = saved_board_id
    room.next_token_number = next_dynamic_token_number(tokens)
    await broadcast_room_state(room)
    return True


def load_saved_tokens(room_id: str, board: Board | None = None) -> list[Token] | None:
    path = existing_save_path(room_id)
    if not path.exists():
        return None

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        active_board = board or fallback_board()
        return [token_from_dict(token_data, active_board, room_id) for token_data in data.get("tokens", [])]
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return None


def load_saved_fog(room_id: str) -> FogState:
    path = existing_save_path(room_id)
    if not path.exists():
        return default_fog()

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return fog_from_dict(data.get("fog", {}))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return default_fog()


def load_saved_board_id(room_id: str) -> str:
    path = existing_save_path(room_id)
    if not path.exists():
        return default_board_id(room_id)

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        board_id = str(data.get("boardId", default_board_id(room_id)))
        return board_id if get_board(board_id, room_id) is not None else default_board_id(room_id)
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return default_board_id(room_id)


def token_from_dict(data: dict[str, Any], board: Board | None = None, campaign_id: str | None = None) -> Token:
    kind = str(data.get("kind", "character"))
    if kind not in {"character", "asset"}:
        kind = "character"
    active_board = board or fallback_board()

    return Token(
        id=str(data["id"]),
        kind=kind,
        name=str(data["name"]),
        owner=normalize_owner(str(data["owner"]), campaign_id),
        color=DEFAULT_TOKEN_COLOR,
        x=clamp(to_float(data["x"]), 0, active_board.width),
        y=clamp(to_float(data["y"]), 0, active_board.height),
        radius=clamp(to_float(data["radius"]), MIN_TOKEN_RADIUS, MAX_TOKEN_RADIUS),
        inScene=bool(data["inScene"]),
        avatarUrl=str(data["avatarUrl"]) if data.get("avatarUrl") else None,
        lockedBy=None,
    )


def default_fog() -> FogState:
    return FogState(hideMode=False, brushSize=120, revealedAreas=[])


def fallback_board() -> Board:
    return blank_board()


def blank_board() -> Board:
    return Board(id="-", name="-", url=None, width=BOARD_WIDTH, height=BOARD_HEIGHT)


def default_board_id(campaign_id: str | None = None) -> str:
    boards = list_boards(campaign_id)
    return boards[0].id if boards else blank_board().id


def list_boards(campaign_id: str | None = None) -> list[Board]:
    boards: list[Board] = [blank_board()]
    for path in list_image_files(campaign_asset_dir("boards", campaign_id), BOARD_DIR):
        board_id = sanitize_asset_id(path.stem)
        if not board_id:
            continue
        dimensions = image_dimensions(path)
        if dimensions is None:
            continue
        width, height = dimensions
        boards.append(Board(id=board_id, name=humanize_asset_name(path.stem), url=campaign_file_url("boards", path, campaign_id), width=width, height=height))
    return boards


def load_party_members(campaign_id: str | None = None) -> list[PartyMember]:
    configured = load_party_members_from_manifest(campaign_asset_dir("party", campaign_id) / "party.json", campaign_id)
    if configured:
        return configured[:MAX_PLAYERS]

    members: list[PartyMember] = []
    for index, path in enumerate(list_image_files(campaign_asset_dir("party", campaign_id))[:MAX_PLAYERS], start=1):
        player_id = f"player-{index}"
        members.append(
            PartyMember(
                id=player_id,
                name=humanize_asset_name(path.stem),
                owner=player_id,
                avatarUrl=campaign_file_url("party", path, campaign_id),
            )
        )
    return members or default_party_members()


def load_party_members_from_manifest(path: Path, campaign_id: str | None = None) -> list[PartyMember]:
    if not path.is_file():
        return []

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    raw_members = data.get("members") if isinstance(data, dict) else None
    if not isinstance(raw_members, list):
        return []

    members: list[PartyMember] = []
    seen: set[str] = set()
    for index, raw_member in enumerate(raw_members, start=1):
        if not isinstance(raw_member, dict):
            continue

        fallback_id = f"player-{index}"
        player_id = normalize_party_member_id(str(raw_member.get("id", fallback_id)), fallback_id)
        if player_id in seen:
            continue
        seen.add(player_id)

        image_path = party_image_path(str(raw_member.get("image", "")), campaign_id)
        members.append(
            PartyMember(
                id=player_id,
                name=str(raw_member.get("name", humanize_asset_name(player_id))).strip()[:40] or humanize_asset_name(player_id),
                owner=player_id,
                avatarUrl=campaign_file_url("party", image_path, campaign_id) if image_path is not None else None,
            )
        )
    return members


def normalize_party_member_id(value: str, fallback: str) -> str:
    normalized = sanitize_asset_id(value)
    if normalized.startswith("player-"):
        try:
            number = int(normalized.rsplit("-", 1)[1])
        except (IndexError, ValueError):
            return fallback
        if 1 <= number <= MAX_PLAYERS:
            return f"player-{number}"
    return fallback


def party_image_path(filename: str, campaign_id: str | None = None) -> Path | None:
    if not filename:
        return None
    path = campaign_asset_dir("party", campaign_id) / Path(filename).name
    return path if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".gif"} else None


def default_party_members() -> list[PartyMember]:
    return [
        PartyMember(id=f"player-{index + 1}", name=f"Player {index + 1}", owner=f"player-{index + 1}", avatarUrl=None)
        for index in range(4)
    ]


def get_board(board_id: str, campaign_id: str | None = None) -> Board | None:
    normalized = sanitize_asset_id(board_id)
    for board in list_boards(campaign_id):
        if board.id == normalized:
            return board
    return None


def board_to_dict(board: Board) -> dict[str, Any]:
    data = asdict(board)
    if data["url"] is None:
        data.pop("url")
    return data


def image_dimensions(path: Path) -> tuple[int, int] | None:
    try:
        with Image.open(path) as image:
            return image.size
    except (OSError, UnidentifiedImageError, Image.DecompressionBombError):
        return None


def sanitize_asset_id(asset_id: str) -> str:
    return "".join(character for character in asset_id.strip().lower() if character.isalnum() or character == "-")[:60]


def humanize_asset_name(asset_name: str) -> str:
    return asset_name.replace("-", " ").replace("_", " ").title()


def list_assets() -> list[Asset]:
    return list_assets_from_dir("asset", SHARED_ASSET_DIR)


def list_assets_from_dir(kind: AssetKind, directory: Path) -> list[Asset]:
    assets: list[Asset] = []
    for path in list_image_files(directory):
        asset_id = sanitize_asset_id(path.stem)
        if not asset_id:
            continue
        assets.append(Asset(id=asset_id, kind=kind, name=humanize_asset_name(path.stem), avatarUrl=asset_file_url(path)))
    return assets


def get_asset(asset_kind: str, asset_id: str) -> Asset | None:
    normalized_kind = asset_kind.strip().lower()
    normalized_id = sanitize_asset_id(asset_id)
    for asset in list_assets():
        if asset.kind == normalized_kind and asset.id == normalized_id:
            return asset
    return None


def asset_to_dict(asset: Asset) -> dict[str, Any]:
    return asdict(asset)


def normalize_owner(owner: str, campaign_id: str | None = None) -> str:
    normalized = owner.strip().lower()
    if normalized == "dm":
        return normalized
    return normalize_player_key(normalized, campaign_id)


def next_dynamic_token_number(tokens: list[Token]) -> int:
    highest = 0
    for token in tokens:
        if token.kind == "character":
            continue
        try:
            highest = max(highest, int(token.id.rsplit("-", 1)[1]))
        except (IndexError, ValueError):
            continue
    return highest + 1


def active_campaign(campaign_id: str | None = None) -> Campaign:
    requested_id = sanitize_asset_id(campaign_id or DEFAULT_CAMPAIGN_ID)
    campaign = get_campaign(requested_id)
    if campaign is not None:
        return campaign
    default_campaign = get_campaign(DEFAULT_CAMPAIGN_ID)
    return default_campaign or Campaign(id=DEFAULT_CAMPAIGN_ID, name=humanize_asset_name(DEFAULT_CAMPAIGN_ID), path=CAMPAIGN_DIR / DEFAULT_CAMPAIGN_ID)


def get_campaign(campaign_id: str) -> Campaign | None:
    campaign_path = CAMPAIGN_DIR / sanitize_asset_id(campaign_id)
    if not campaign_path.exists() or not campaign_path.is_dir():
        return None
    return Campaign(id=campaign_path.name, name=humanize_asset_name(campaign_path.name), path=campaign_path)


def campaign_asset_dir(directory_name: str, campaign_id: str | None = None) -> Path:
    return active_campaign(campaign_id).path / directory_name


def campaign_save_dir(campaign_id: str | None = None) -> Path:
    return active_campaign(campaign_id).path / "saves"


def save_path(room_id: str) -> Path:
    if SAVE_DIR != LEGACY_SAVE_DIR:
        return SAVE_DIR / f"{room_id}.json"
    return campaign_save_dir(room_id) / f"{room_id}.json"


def existing_save_path(room_id: str) -> Path:
    campaign_path = save_path(room_id)
    if campaign_path.exists():
        return campaign_path
    return LEGACY_SAVE_DIR / f"{room_id}.json"


def list_image_files(*directories: Path) -> list[Path]:
    seen: set[str] = set()
    paths: list[Path] = []
    for directory in directories:
        if not directory.exists():
            continue
        for path in sorted(directory.iterdir()):
            if path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp", ".gif"}:
                continue
            asset_id = sanitize_asset_id(path.stem)
            if not asset_id or asset_id in seen:
                continue
            seen.add(asset_id)
            paths.append(path)
    return paths


def asset_file_url(path: Path) -> str:
    if path.parent == SHARED_ASSET_DIR:
        return f"/shared/assets/{path.name}"
    return f"/shared/assets/{path.name}"


def campaign_file_url(directory_name: str, path: Path, campaign_id: str | None = None) -> str:
    campaign = active_campaign(campaign_id)
    campaign_directory = campaign_asset_dir(directory_name, campaign.id)
    if path.parent == campaign_directory:
        return f"/campaigns/{campaign.id}/{directory_name}/{path.name}"
    if path.parent == BOARD_DIR:
        return f"/boards/{path.name}"
    return f"/campaigns/{campaign.id}/{directory_name}/{path.name}"


def fog_to_dict(fog: FogState) -> dict[str, Any]:
    return {
        "hideMode": fog.hideMode,
        "brushSize": fog.brushSize,
        "revealedAreas": [asdict(area) for area in fog.revealedAreas],
    }


def fog_from_dict(data: dict[str, Any]) -> FogState:
    return FogState(
        hideMode=bool(data.get("hideMode", False)),
        brushSize=clamp(to_float(data.get("brushSize", 120)), 20, 360),
        revealedAreas=[
            RevealedArea(
                x=clamp(to_float(area.get("x")), 0, BOARD_WIDTH),
                y=clamp(to_float(area.get("y")), 0, BOARD_HEIGHT),
                radius=clamp(to_float(area.get("radius", 120)), 20, 360),
            )
            for area in data.get("revealedAreas", [])
            if isinstance(area, dict)
        ],
    )


def convert_avatar_to_png(content: bytes) -> bytes:
    try:
        with Image.open(BytesIO(content)) as image:
            image.load()
            image.thumbnail((512, 512))
            converted = image.convert("RGBA")
    except (OSError, UnidentifiedImageError, Image.DecompressionBombError) as error:
        raise HTTPException(status_code=400, detail="Avatar must be a valid image file") from error

    output = BytesIO()
    converted.save(output, format="PNG", optimize=True)
    return output.getvalue()


def to_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0


def clamp(value: float, minimum: float, maximum: float) -> float:
    return min(maximum, max(minimum, value))


dist_dir = Path(__file__).resolve().parent.parent / "dist"
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR, check_dir=False), name="uploads")
app.mount("/shared", StaticFiles(directory=SHARED_DIR, check_dir=False), name="shared")
app.mount("/boards", StaticFiles(directory=BOARD_DIR, check_dir=False), name="boards")
if dist_dir.exists():
    app.mount("/assets", StaticFiles(directory=dist_dir / "assets", check_dir=False), name="assets")

    @app.get("/{path:path}")
    async def serve_client(path: str) -> FileResponse:
        target = dist_dir / path
        if path and target.is_file():
            return FileResponse(target)
        return FileResponse(dist_dir / "index.html")
