import asyncio
import json
from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from dnd_board import server


def setup_function() -> None:
    server.rooms.clear()


def test_room_starts_with_four_owned_player_characters() -> None:
    client = TestClient(server.app)

    with client.websocket_connect("/ws") as websocket:
        hello = websocket.receive_json()
        assert hello["type"] == "hello"

        websocket.send_json({"type": "join_room", "roomId": "unit-test", "playerKey": "player-1"})
        state = websocket.receive_json()

    assert state["type"] == "room_state"
    assert [token["id"] for token in state["tokens"]] == ["player-1", "player-2", "player-3", "player-4"]
    assert [token["owner"] for token in state["tokens"]] == ["player-1", "player-2", "player-3", "player-4"]
    assert all(token["kind"] == "character" for token in state["tokens"])
    assert all(token["inScene"] is False for token in state["tokens"])
    assert state["fog"] == {"hideMode": False, "brushSize": 120, "revealedAreas": []}
    assert state["board"]["id"] == "green"
    assert state["board"]["width"] == 1200
    assert state["board"]["height"] == 720
    assert any(board["id"] == "phandalin" and board["width"] == 4000 and board["height"] == 2788 for board in state["boards"])
    assert any(asset["kind"] == "npc" and asset["id"] == "npc1" for asset in state["assets"])
    assert any(asset["kind"] == "monster" and asset["id"] == "goblin" for asset in state["assets"])
    assert any(asset["kind"] == "beast" and asset["id"] == "wolf" for asset in state["assets"])


def test_player_can_lock_and_move_only_their_own_character() -> None:
    client = TestClient(server.app)

    with client.websocket_connect("/ws") as player_one:
        player_one.receive_json()
        player_one.send_json({"type": "join_room", "roomId": "permission-test", "playerKey": "player-1"})
        player_one.receive_json()

        player_one.send_json({"type": "request_token_lock", "tokenId": "player-2"})
        denied = player_one.receive_json()
        assert denied["type"] == "token_lock_denied"
        assert denied["tokenId"] == "player-2"
        assert denied["reason"] == "not_owner"

        player_one.send_json({"type": "request_token_lock", "tokenId": "player-1"})
        locked = player_one.receive_json()
        assert locked["type"] == "token_updated"
        assert locked["token"]["id"] == "player-1"
        assert locked["token"]["lockedBy"] == "player-1"

        player_one.send_json({"type": "set_token_scene", "tokenId": "player-1", "inScene": True, "x": 300, "y": 320})
        placed = player_one.receive_json()
        assert placed["type"] == "token_updated"
        assert placed["token"]["inScene"] is True
        assert placed["token"]["x"] == 300
        assert placed["token"]["y"] == 320

        player_one.send_json({"type": "move_token", "tokenId": "player-1", "x": 450, "y": 480})
        moved = player_one.receive_json()
        assert moved["type"] == "token_updated"
        assert moved["token"]["x"] == 450
        assert moved["token"]["y"] == 480


def test_other_players_see_owned_character_lock_but_cannot_take_it() -> None:
    room = server.get_or_create_room("lock-test")
    player_one_socket = FakeSocket()
    player_two_socket = FakeSocket()
    player_one = server.Player(id="connection-1", name="Player 1", player_key="player-1", websocket=player_one_socket, room_id=room.id)
    player_two = server.Player(id="connection-2", name="Player 2", player_key="player-2", websocket=player_two_socket, room_id=room.id)
    room.players[player_one.id] = player_one
    room.players[player_two.id] = player_two

    asyncio.run(server.lock_token(room, player_one, "player-1"))
    assert player_two_socket.messages[-1]["type"] == "token_updated"
    assert player_two_socket.messages[-1]["token"]["lockedBy"] == "player-1"

    asyncio.run(server.lock_token(room, player_two, "player-1"))
    denied = player_two_socket.messages[-1]
    assert denied["type"] == "token_lock_denied"
    assert denied["tokenId"] == "player-1"
    assert denied["reason"] == "not_owner"


def test_dm_lock_can_preserve_current_radius() -> None:
    room = server.get_or_create_room("lock-radius-test")
    dm_socket = FakeSocket()
    dm = server.Player(id="connection-1", name="DM", player_key="dm", websocket=dm_socket, room_id=room.id)
    room.players[dm.id] = dm

    asyncio.run(server.lock_token(room, dm, "player-1", {"radius": 96}))

    assert room.tokens["player-1"].radius == 96
    assert dm_socket.messages[-1]["token"]["radius"] == 96
    assert dm_socket.messages[-1]["token"]["lockedBy"] == "dm"


def test_dm_resize_then_grab_and_move_preserves_radius_through_websocket() -> None:
    client = TestClient(server.app)

    with client.websocket_connect("/ws") as dm:
        dm.receive_json()
        dm.send_json({"type": "join_room", "roomId": "resize-grab-test", "playerKey": "dm"})
        dm.receive_json()

        dm.send_json({"type": "set_token_radius", "tokenId": "player-1", "radius": 96})
        resized = dm.receive_json()
        resized_state = dm.receive_json()
        assert resized["type"] == "token_updated"
        assert resized["token"]["radius"] == 96
        assert resized_state["type"] == "room_state"
        assert token_by_id(resized_state, "player-1")["radius"] == 96

        dm.send_json({"type": "request_token_lock", "tokenId": "player-1", "radius": 96})
        locked = dm.receive_json()
        assert locked["type"] == "token_updated"
        assert locked["token"]["radius"] == 96
        assert locked["token"]["lockedBy"] == "dm"

        dm.send_json({"type": "move_token", "tokenId": "player-1", "x": 500, "y": 400, "radius": 96})
        moved = dm.receive_json()

    assert moved["type"] == "token_updated"
    assert moved["token"]["radius"] == 96
    assert moved["token"]["x"] == 500
    assert moved["token"]["y"] == 400


def test_player_can_upload_image_avatar_for_their_character(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(server, "UPLOAD_DIR", tmp_path)
    client = TestClient(server.app)
    image = make_image("JPEG")

    response = client.post(
        "/api/rooms/avatar-test/tokens/player-1/avatar?playerKey=player-1",
        files={"file": ("hero.jpg", image, "image/jpeg")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token"]["id"] == "player-1"
    assert body["token"]["avatarUrl"].startswith("/uploads/avatar-test/player-1/")
    assert "?v=" in body["token"]["avatarUrl"]
    avatar_path = tmp_path / "avatar-test" / "player-1" / "avatar.png"
    assert avatar_path.exists()
    with Image.open(avatar_path) as converted:
        assert converted.format == "PNG"


def test_replacing_avatar_changes_avatar_url_version(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(server, "UPLOAD_DIR", tmp_path)
    client = TestClient(server.app)

    first = client.post(
        "/api/rooms/avatar-version-test/tokens/player-1/avatar?playerKey=player-1",
        files={"file": ("hero.png", make_image("PNG"), "image/png")},
    )
    second = client.post(
        "/api/rooms/avatar-version-test/tokens/player-1/avatar?playerKey=player-1",
        files={"file": ("hero.png", make_image("PNG"), "image/png")},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["token"]["avatarUrl"] != second.json()["token"]["avatarUrl"]


def test_player_cannot_upload_avatar_for_another_character(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(server, "UPLOAD_DIR", tmp_path)
    client = TestClient(server.app)
    image = make_image("PNG")

    response = client.post(
        "/api/rooms/avatar-test/tokens/player-2/avatar?playerKey=player-1",
        files={"file": ("hero.png", image, "image/png")},
    )

    assert response.status_code == 403


def test_avatar_upload_rejects_non_image_file(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(server, "UPLOAD_DIR", tmp_path)
    client = TestClient(server.app)

    response = client.post(
        "/api/rooms/avatar-test/tokens/player-1/avatar?playerKey=player-1",
        files={"file": ("hero.txt", b"not-png", "text/plain")},
    )

    assert response.status_code == 400


def test_only_dm_can_save_room_state(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(server, "SAVE_DIR", tmp_path)
    client = TestClient(server.app)

    forbidden = client.post("/api/rooms/save-test/save?playerKey=player-1")
    assert forbidden.status_code == 403

    saved = client.post("/api/rooms/save-test/save?playerKey=dm")
    assert saved.status_code == 200
    assert (tmp_path / "save-test.json").exists()


def test_default_save_path_is_campaign_scoped() -> None:
    assert server.save_path("save-test") == server.CAMPAIGN_DIR / server.DEFAULT_CAMPAIGN_ID / "saves" / "save-test.json"


def test_saved_room_state_loads_when_room_is_recreated(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(server, "SAVE_DIR", tmp_path)
    client = TestClient(server.app)

    with client.websocket_connect("/ws") as player_one:
        player_one.receive_json()
        player_one.send_json({"type": "join_room", "roomId": "reload-test", "playerKey": "player-1"})
        player_one.receive_json()
        player_one.send_json({"type": "request_token_lock", "tokenId": "player-1"})
        player_one.receive_json()
        player_one.send_json({"type": "set_token_scene", "tokenId": "player-1", "inScene": True, "x": 333, "y": 444})
        player_one.receive_json()
        room = server.rooms["reload-test"]
        dm = server.Player(id="http-dm", name="DM", player_key="dm", websocket=None, room_id=room.id)
        asyncio.run(server.set_token_radius(room, dm, "player-1", 88))

        saved = client.post("/api/rooms/reload-test/save?playerKey=dm")
        assert saved.status_code == 200
        saved_data = json.loads((tmp_path / "reload-test.json").read_text(encoding="utf-8"))
        saved_player_one = next(token for token in saved_data["tokens"] if token["id"] == "player-1")
        assert saved_player_one["radius"] == 88

    server.rooms.clear()

    with client.websocket_connect("/ws") as player_one:
        player_one.receive_json()
        player_one.send_json({"type": "join_room", "roomId": "reload-test", "playerKey": "player-1"})
        state = player_one.receive_json()

    player_one_token = next(token for token in state["tokens"] if token["id"] == "player-1")
    assert player_one_token["inScene"] is True
    assert player_one_token["x"] == 333
    assert player_one_token["y"] == 444
    assert player_one_token["radius"] == 88


def test_dm_can_load_saved_room_state_without_restart(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(server, "SAVE_DIR", tmp_path)
    room = server.get_or_create_room("manual-load-test")
    dm_socket = FakeSocket()
    dm = server.Player(id="connection-1", name="DM", player_key="dm", websocket=dm_socket, room_id=room.id)
    room.players[dm.id] = dm

    room.tokens["player-1"].inScene = True
    room.tokens["player-1"].x = 111
    room.tokens["player-1"].y = 222
    room.board_id = "phandalin"
    room.fog.hideMode = True
    room.fog.revealedAreas.append(server.RevealedArea(x=200, y=300, radius=80))
    server.save_room_to_disk(room)

    room.tokens["player-1"].x = 900
    room.tokens["player-1"].y = 600
    room.board_id = "green"
    room.fog.hideMode = False
    room.fog.revealedAreas = []

    asyncio.run(server.load_room_from_disk(room, dm))

    assert room.tokens["player-1"].x == 111
    assert room.tokens["player-1"].y == 222
    assert room.board_id == "phandalin"
    assert room.fog.hideMode is True
    assert room.fog.revealedAreas == [server.RevealedArea(x=200, y=300, radius=80)]
    assert dm_socket.messages[-1]["type"] == "room_state"
    assert dm_socket.messages[-1]["board"]["id"] == "phandalin"


def test_saved_large_board_token_positions_load_without_green_board_clamp(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(server, "SAVE_DIR", tmp_path)
    room = server.get_or_create_room("large-board-position-load-test")
    room.board_id = "phandalin"
    room.tokens["player-1"].inScene = True
    room.tokens["player-1"].x = 2500
    room.tokens["player-1"].y = 1200
    server.save_room_to_disk(room)

    server.rooms.clear()
    loaded = server.get_or_create_room("large-board-position-load-test")

    assert loaded.board_id == "phandalin"
    assert loaded.tokens["player-1"].x == 2500
    assert loaded.tokens["player-1"].y == 1200


def test_non_dm_cannot_load_saved_room_state(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(server, "SAVE_DIR", tmp_path)
    client = TestClient(server.app)

    response = client.post("/api/rooms/manual-load-test/load?playerKey=player-1")

    assert response.status_code == 403


def test_only_dm_can_update_fog_state() -> None:
    client = TestClient(server.app)

    with client.websocket_connect("/ws") as player_one:
        player_one.receive_json()
        player_one.send_json({"type": "join_room", "roomId": "fog-permission-test", "playerKey": "player-1"})
        player_one.receive_json()

        player_one.send_json({"type": "set_fog_mode", "hideMode": True})
        player_one.send_json({"type": "reveal_fog", "x": 100, "y": 120, "radius": 80})

        room = server.rooms["fog-permission-test"]
        assert room.fog.hideMode is False
        assert room.fog.revealedAreas == []


def test_dm_can_update_and_save_fog_state(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(server, "SAVE_DIR", tmp_path)
    client = TestClient(server.app)

    with client.websocket_connect("/ws") as dm:
        dm.receive_json()
        dm.send_json({"type": "join_room", "roomId": "fog-save-test", "playerKey": "dm"})
        dm.receive_json()

        dm.send_json({"type": "set_fog_mode", "hideMode": True, "brushSize": 90})
        fog_mode = dm.receive_json()
        assert fog_mode["type"] == "fog_updated"
        assert fog_mode["fog"]["hideMode"] is True
        assert fog_mode["fog"]["brushSize"] == 90

        dm.send_json({"type": "reveal_fog", "x": 222, "y": 333, "radius": 90})
        revealed = dm.receive_json()
        assert revealed["type"] == "fog_updated"
        assert revealed["fog"]["revealedAreas"] == [{"x": 222, "y": 333, "radius": 90}]

        saved = client.post("/api/rooms/fog-save-test/save?playerKey=dm")
        assert saved.status_code == 200

    server.rooms.clear()

    with client.websocket_connect("/ws") as dm:
        dm.receive_json()
        dm.send_json({"type": "join_room", "roomId": "fog-save-test", "playerKey": "dm"})
        state = dm.receive_json()

    assert state["fog"]["hideMode"] is True
    assert state["fog"]["brushSize"] == 90
    assert state["fog"]["revealedAreas"] == [{"x": 222, "y": 333, "radius": 90}]


def test_only_dm_can_switch_boards() -> None:
    client = TestClient(server.app)

    with client.websocket_connect("/ws") as player_one:
        player_one.receive_json()
        player_one.send_json({"type": "join_room", "roomId": "board-permission-test", "playerKey": "player-1"})
        player_one.receive_json()

        player_one.send_json({"type": "set_board", "boardId": "phandalin"})

        room = server.rooms["board-permission-test"]
        assert room.board_id == "green"


def test_dm_can_switch_board_and_broadcast_update() -> None:
    room = server.get_or_create_room("board-switch-test")
    dm_socket = FakeSocket()
    player_socket = FakeSocket()
    dm = server.Player(id="connection-1", name="DM", player_key="dm", websocket=dm_socket, room_id=room.id)
    player_one = server.Player(id="connection-2", name="Player 1", player_key="player-1", websocket=player_socket, room_id=room.id)
    room.players[dm.id] = dm
    room.players[player_one.id] = player_one

    asyncio.run(server.set_board(room, dm, "phandalin"))
    dm_update = dm_socket.messages[-1]
    player_update = player_socket.messages[-1]

    assert dm_update["type"] == "board_updated"
    assert dm_update["board"]["id"] == "phandalin"
    assert dm_update["board"]["width"] == 4000
    assert dm_update["board"]["height"] == 2788
    assert player_update["type"] == "board_updated"
    assert player_update["board"]["id"] == "phandalin"


def test_saved_room_state_loads_selected_board(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(server, "SAVE_DIR", tmp_path)
    client = TestClient(server.app)

    with client.websocket_connect("/ws") as dm:
        dm.receive_json()
        dm.send_json({"type": "join_room", "roomId": "board-save-test", "playerKey": "dm"})
        dm.receive_json()
        dm.send_json({"type": "set_board", "boardId": "phandalin"})
        dm.receive_json()

        saved = client.post("/api/rooms/board-save-test/save?playerKey=dm")
        assert saved.status_code == 200

    server.rooms.clear()

    with client.websocket_connect("/ws") as dm:
        dm.receive_json()
        dm.send_json({"type": "join_room", "roomId": "board-save-test", "playerKey": "dm"})
        state = dm.receive_json()

    assert state["board"]["id"] == "phandalin"


def test_only_dm_can_load_registry_asset() -> None:
    room = server.get_or_create_room("asset-permission-test")
    player_socket = FakeSocket()
    player = server.Player(id="connection-1", name="Player 1", player_key="player-1", websocket=player_socket, room_id=room.id)
    room.players[player.id] = player

    asyncio.run(server.load_asset_token(room, player, "monster", "goblin"))

    assert all(token.kind != "monster" for token in room.tokens.values())
    assert player_socket.messages == []


def test_dm_can_load_npc_monster_and_beast_tokens() -> None:
    room = server.get_or_create_room("asset-load-test")
    dm_socket = FakeSocket()
    dm = server.Player(id="connection-1", name="DM", player_key="dm", websocket=dm_socket, room_id=room.id)
    room.players[dm.id] = dm

    asyncio.run(server.load_asset_token(room, dm, "npc", "npc1"))
    asyncio.run(server.load_asset_token(room, dm, "monster", "goblin"))
    asyncio.run(server.load_asset_token(room, dm, "beast", "wolf"))

    npc = room.tokens["npc-1"]
    monster = room.tokens["monster-2"]
    beast = room.tokens["beast-3"]
    assert npc.kind == "npc"
    assert npc.owner == "dm"
    assert npc.avatarUrl == "/campaigns/test-campaign/npcs/npc1.png"
    assert monster.kind == "monster"
    assert monster.owner == "dm"
    assert monster.avatarUrl == "/campaigns/test-campaign/monsters/goblin.jpg"
    assert beast.kind == "beast"
    assert beast.owner == "dm"
    assert beast.avatarUrl == "/campaigns/test-campaign/beasts/wolf.jpeg"
    assert [message["type"] for message in dm_socket.messages[-3:]] == ["token_updated", "token_updated", "token_updated"]


def test_dm_loaded_asset_uses_active_board_center() -> None:
    room = server.get_or_create_room("asset-board-size-test")
    room.board_id = "phandalin"
    dm_socket = FakeSocket()
    dm = server.Player(id="connection-1", name="DM", player_key="dm", websocket=dm_socket, room_id=room.id)
    room.players[dm.id] = dm

    asyncio.run(server.load_asset_token(room, dm, "monster", "goblin"))

    monster = room.tokens["monster-1"]
    assert monster.x == 2000
    assert monster.y == 1394
    assert monster.radius == 70


def test_dm_can_move_any_token() -> None:
    room = server.get_or_create_room("dm-move-test")
    dm_socket = FakeSocket()
    dm = server.Player(id="connection-1", name="DM", player_key="dm", websocket=dm_socket, room_id=room.id)
    room.players[dm.id] = dm

    asyncio.run(server.lock_token(room, dm, "player-1"))
    asyncio.run(server.move_token(room, dm, "player-1", {"x": 600, "y": 500}))

    assert room.tokens["player-1"].x == 600
    assert room.tokens["player-1"].y == 500


def test_dm_move_can_preserve_current_radius() -> None:
    room = server.get_or_create_room("dm-move-radius-test")
    dm_socket = FakeSocket()
    dm = server.Player(id="connection-1", name="DM", player_key="dm", websocket=dm_socket, room_id=room.id)
    room.players[dm.id] = dm
    token = room.tokens["player-1"]
    token.lockedBy = "dm"

    asyncio.run(server.move_token(room, dm, "player-1", {"x": 600, "y": 500, "radius": 88}))

    assert token.radius == 88
    assert token.x == 600
    assert token.y == 500
    assert dm_socket.messages[-1]["token"]["radius"] == 88


def test_only_dm_can_clear_scene() -> None:
    room = server.get_or_create_room("clear-permission-test")
    room.tokens["player-1"].inScene = True
    player_socket = FakeSocket()
    player = server.Player(id="connection-1", name="Player 1", player_key="player-1", websocket=player_socket, room_id=room.id)
    room.players[player.id] = player

    asyncio.run(server.clear_scene(room, player))

    assert room.tokens["player-1"].inScene is True
    assert player_socket.messages == []


def test_dm_can_clear_scene_without_resetting_fog_or_board() -> None:
    room = server.get_or_create_room("clear-scene-test")
    dm_socket = FakeSocket()
    dm = server.Player(id="connection-1", name="DM", player_key="dm", websocket=dm_socket, room_id=room.id)
    room.players[dm.id] = dm
    room.board_id = "phandalin"
    room.fog.hideMode = True
    room.fog.revealedAreas.append(server.RevealedArea(x=20, y=30, radius=40))
    room.tokens["player-1"].inScene = True
    room.tokens["player-1"].lockedBy = "player-1"

    asyncio.run(server.clear_scene(room, dm))

    assert all(token.inScene is False for token in room.tokens.values())
    assert all(token.lockedBy is None for token in room.tokens.values())
    assert room.board_id == "phandalin"
    assert room.fog.hideMode is True
    assert room.fog.revealedAreas == [server.RevealedArea(x=20, y=30, radius=40)]
    assert dm_socket.messages[-1]["type"] == "room_state"
    assert all(token["inScene"] is False for token in dm_socket.messages[-1]["tokens"])


def test_dm_can_clear_scene_through_websocket() -> None:
    client = TestClient(server.app)

    with client.websocket_connect("/ws") as dm:
        dm.receive_json()
        dm.send_json({"type": "join_room", "roomId": "clear-scene-ws-test", "playerKey": "dm"})
        dm.receive_json()
        dm.send_json({"type": "request_token_lock", "tokenId": "player-1"})
        dm.receive_json()
        dm.send_json({"type": "set_token_scene", "tokenId": "player-1", "inScene": True, "x": 300, "y": 320})
        dm.receive_json()

        dm.send_json({"type": "clear_scene"})
        state = dm.receive_json()

    assert state["type"] == "room_state"
    assert all(token["inScene"] is False for token in state["tokens"])
    assert all("lockedBy" not in token for token in state["tokens"])


def test_dm_can_resize_token() -> None:
    room = server.get_or_create_room("resize-token-test")
    dm_socket = FakeSocket()
    dm = server.Player(id="connection-1", name="DM", player_key="dm", websocket=dm_socket, room_id=room.id)
    room.players[dm.id] = dm

    asyncio.run(server.set_token_radius(room, dm, "player-1", 72))

    assert room.tokens["player-1"].radius == 72
    assert dm_socket.messages[-1]["type"] == "room_state"
    assert token_by_id(dm_socket.messages[-1], "player-1")["radius"] == 72


def test_dm_resize_broadcasts_radius_to_player() -> None:
    room = server.get_or_create_room("resize-broadcast-test")
    dm_socket = FakeSocket()
    player_socket = FakeSocket()
    dm = server.Player(id="connection-1", name="DM", player_key="dm", websocket=dm_socket, room_id=room.id)
    player = server.Player(id="connection-2", name="Player 1", player_key="player-1", websocket=player_socket, room_id=room.id)
    room.players[dm.id] = dm
    room.players[player.id] = player

    asyncio.run(server.set_token_radius(room, dm, "player-1", 72))

    assert dm_socket.messages[-2]["type"] == "token_updated"
    assert dm_socket.messages[-2]["token"]["radius"] == 72
    assert player_socket.messages[-2]["type"] == "token_updated"
    assert player_socket.messages[-2]["token"]["radius"] == 72
    assert token_by_id(dm_socket.messages[-1], "player-1")["radius"] == 72
    assert token_by_id(player_socket.messages[-1], "player-1")["radius"] == 72


def test_dm_resize_visible_to_player_through_websocket() -> None:
    client = TestClient(server.app)

    with client.websocket_connect("/ws") as dm, client.websocket_connect("/ws") as player:
        dm.receive_json()
        player.receive_json()
        dm.send_json({"type": "join_room", "roomId": "resize-visible-test", "playerKey": "dm"})
        dm.receive_json()
        player.send_json({"type": "join_room", "roomId": "resize-visible-test", "playerKey": "player-1"})
        player.receive_json()
        dm.receive_json()

        dm.send_json({"type": "request_token_lock", "tokenId": "player-1"})
        dm.receive_json()
        player.receive_json()
        dm.send_json({"type": "set_token_scene", "tokenId": "player-1", "inScene": True, "x": 300, "y": 320})
        dm.receive_json()
        player.receive_json()

        dm.send_json({"type": "set_token_radius", "tokenId": "player-1", "radius": 96})
        dm_resized = dm.receive_json()
        player_resized = player.receive_json()

    assert dm_resized["type"] == "token_updated"
    assert dm_resized["token"]["radius"] == 96
    assert player_resized["type"] == "token_updated"
    assert player_resized["token"]["radius"] == 96


def test_dm_http_resize_visible_to_player_websocket() -> None:
    client = TestClient(server.app)

    with client.websocket_connect("/ws") as player:
        player.receive_json()
        player.send_json({"type": "join_room", "roomId": "http-resize-visible-test", "playerKey": "player-1"})
        player.receive_json()

        response = client.post("/api/rooms/http-resize-visible-test/tokens/player-1/radius?playerKey=dm&radius=104")
        player_resized = player.receive_json()

    assert response.status_code == 200
    assert response.json()["token"]["radius"] == 104
    assert player_resized["type"] == "token_updated"
    assert player_resized["token"]["radius"] == 104


def test_dm_http_resize_is_saved(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(server, "SAVE_DIR", tmp_path)
    client = TestClient(server.app)

    response = client.post("/api/rooms/http-resize-save-test/tokens/player-1/radius?playerKey=dm&radius=104")
    saved = client.post("/api/rooms/http-resize-save-test/save?playerKey=dm")

    saved_data = json.loads((tmp_path / "http-resize-save-test.json").read_text(encoding="utf-8"))
    saved_player_one = next(token for token in saved_data["tokens"] if token["id"] == "player-1")
    assert response.status_code == 200
    assert saved.status_code == 200
    assert saved_player_one["radius"] == 104


def test_room_state_endpoint_includes_resized_radius() -> None:
    client = TestClient(server.app)

    resized = client.post("/api/rooms/state-radius-test/tokens/player-1/radius?playerKey=dm&radius=104")
    state = client.get("/api/rooms/state-radius-test/state")

    assert resized.status_code == 200
    assert state.status_code == 200
    assert token_by_id(state.json(), "player-1")["radius"] == 104


def test_non_dm_cannot_resize_token() -> None:
    room = server.get_or_create_room("resize-permission-test")
    player_socket = FakeSocket()
    player = server.Player(id="connection-1", name="Player 1", player_key="player-1", websocket=player_socket, room_id=room.id)
    room.players[player.id] = player

    asyncio.run(server.set_token_radius(room, player, "player-1", 72))

    assert room.tokens["player-1"].radius == 70
    assert player_socket.messages == []


def test_resize_token_clamps_position_to_active_board() -> None:
    room = server.get_or_create_room("resize-clamp-test")
    dm_socket = FakeSocket()
    dm = server.Player(id="connection-1", name="DM", player_key="dm", websocket=dm_socket, room_id=room.id)
    room.players[dm.id] = dm
    token = room.tokens["player-1"]
    token.x = 1195
    token.y = 715

    asyncio.run(server.set_token_radius(room, dm, "player-1", 80))

    assert token.radius == 80
    assert token.x == 1120
    assert token.y == 640


def test_dm_can_resize_token_above_old_fixed_limit_on_large_board() -> None:
    room = server.get_or_create_room("resize-large-board-test")
    room.board_id = "phandalin"
    dm_socket = FakeSocket()
    dm = server.Player(id="connection-1", name="DM", player_key="dm", websocket=dm_socket, room_id=room.id)
    room.players[dm.id] = dm

    asyncio.run(server.set_token_radius(room, dm, "player-1", 320))

    assert room.tokens["player-1"].radius == 320
    assert token_by_id(dm_socket.messages[-1], "player-1")["radius"] == 320


def test_non_dm_cannot_delete_tokens() -> None:
    room = server.get_or_create_room("delete-permission-test")
    player_socket = FakeSocket()
    player = server.Player(id="connection-1", name="Player 1", player_key="player-1", websocket=player_socket, room_id=room.id)
    room.players[player.id] = player

    asyncio.run(server.delete_token(room, player, "player-1"))

    assert "player-1" in room.tokens
    assert player_socket.messages == []


def test_dm_cannot_delete_party_characters() -> None:
    room = server.get_or_create_room("delete-character-test")
    dm_socket = FakeSocket()
    dm = server.Player(id="connection-1", name="DM", player_key="dm", websocket=dm_socket, room_id=room.id)
    room.players[dm.id] = dm

    asyncio.run(server.delete_token(room, dm, "player-1"))

    assert "player-1" in room.tokens
    assert dm_socket.messages == []


def test_dm_can_delete_loaded_npc_or_monster() -> None:
    room = server.get_or_create_room("delete-asset-test")
    dm_socket = FakeSocket()
    player_socket = FakeSocket()
    dm = server.Player(id="connection-1", name="DM", player_key="dm", websocket=dm_socket, room_id=room.id)
    player = server.Player(id="connection-2", name="Player 1", player_key="player-1", websocket=player_socket, room_id=room.id)
    room.players[dm.id] = dm
    room.players[player.id] = player

    asyncio.run(server.load_asset_token(room, dm, "monster", "goblin"))
    asyncio.run(server.delete_token(room, dm, "monster-1"))

    assert "monster-1" not in room.tokens
    assert dm_socket.messages[-1] == {"type": "token_deleted", "tokenId": "monster-1"}
    assert player_socket.messages[-1] == {"type": "token_deleted", "tokenId": "monster-1"}


def make_image(image_format: str) -> bytes:
    image = Image.new("RGBA", (8, 8), (255, 0, 0, 255))
    output = BytesIO()
    if image_format == "JPEG":
        image = image.convert("RGB")
    image.save(output, format=image_format)
    return output.getvalue()


def token_by_id(message: dict, token_id: str) -> dict:
    return next(token for token in message["tokens"] if token["id"] == token_id)


class FakeSocket:
    def __init__(self) -> None:
        self.messages = []

    async def send_text(self, text: str) -> None:
        self.messages.append(json.loads(text))
