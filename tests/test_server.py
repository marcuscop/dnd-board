import asyncio
import json
from dataclasses import replace
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from dnd_board import server
from dnd_board.rules.classes.fighter.archetypes import eldritch_knight_catalog_spell
from dnd_board.rules.classes.fighter.base import FighterSubclassType
from dnd_board.rules.classes.rogue.archetypes import RogueSubclassAbilityType, RogueSubclassAttackType, RogueSubclassRollActionType, arcane_trickster_catalog_spell
from dnd_board.rules.classes.rogue.base import RogueSubclassType
from dnd_board.rules.feats import general_feat_feature
from dnd_board.rules.sources import RuleSource, rule_source_label
from dnd_board.rules.spells import spell_entry, wizard_spell_entry
from dnd_board.character_sheet import (
    AbilityScores,
    AbilityType,
    ArcaneShotType,
    ArmorCategory,
    AttackAction,
    AttackRangeType,
    BattleMasterManeuverType,
    CharacterClassLevel,
    ClassType,
    ConditionApplicationMode,
    ConditionDuration,
    ConditionEffect,
    ConditionType,
    DamageType,
    DiceType,
    EquipmentItem,
    EquipmentSlot,
    EquipmentType,
    FightingStyleType,
    PartyManifest,
    PartyMemberConfig,
    PartyMemberSheet,
    ProficiencyLevel,
    ResourceTracker,
    RollPayload,
    RollAction,
    RollResolutionMode,
    RollSource,
    RestType,
    SheetSectionType,
    SkillType,
    SpellId,
    SpellSource,
    TimeEconomy,
    WeaponCategory,
    WeaponProperty,
    enum_key,
    enum_label,
    typed_json_from_value,
)


def setup_function() -> None:
    server.rooms.clear()


def write_party_campaign(tmp_path, campaign_id: str, *members: PartyMemberConfig) -> None:
    campaign = tmp_path / campaign_id
    party = campaign / "party"
    party.mkdir(parents=True)
    (campaign / "campaign.json").write_text(json.dumps({"id": campaign_id, "name": campaign_id}), encoding="utf-8")
    (party / "party.json").write_text(
        json.dumps(typed_json_from_value(PartyManifest(members=list(members)))),
        encoding="utf-8",
    )


def resolve_rogue_level_choices(client: TestClient, room_id: str) -> dict:
    sheet = client.get(f"/api/rooms/{room_id}/sheet/player-1?playerKey=player-1").json()["sheet"]
    while sheet["pendingChoices"]:
        choice_ids = {choice["id"] for choice in sheet["pendingChoices"]}
        if "hitPointIncrease" in choice_ids:
            response = client.post(f"/api/rooms/{room_id}/sheet/player-1/choices/hitPointIncrease?playerKey=player-1", json={"values": ["fixed"]})
        elif "rogueSubclass" in choice_ids:
            response = client.post(f"/api/rooms/{room_id}/sheet/player-1/choices/rogueSubclass?playerKey=player-1", json={"values": [enum_key(RogueSubclassType.SOULKNIFE)]})
        elif "rogueAbilityScoreImprovement" in choice_ids:
            response = client.post(f"/api/rooms/{room_id}/sheet/player-1/choices/rogueAbilityScoreImprovement?playerKey=player-1", json={"values": ["dexterity", "dexterity"]})
        elif "rogueExpertise" in choice_ids:
            response = client.post(
                f"/api/rooms/{room_id}/sheet/player-1/choices/rogueExpertise?playerKey=player-1",
                json={"values": [enum_key(SkillType.SLEIGHT_OF_HAND), enum_key(SkillType.STEALTH), enum_key(SkillType.PERCEPTION), enum_key(SkillType.INVESTIGATION)]},
            )
        else:
            raise AssertionError(f"Unhandled Rogue level choice: {choice_ids}")
        assert response.status_code == 200
        sheet = response.json()["sheet"]
    return sheet


def test_health_endpoint_returns_ok() -> None:
    client = TestClient(server.app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.text == "ok"


def test_room_starts_with_four_owned_player_characters() -> None:
    client = TestClient(server.app)

    with client.websocket_connect("/ws") as websocket:
        hello = websocket.receive_json()
        assert hello["type"] == "hello"

        websocket.send_json({"type": "join_room", "roomId": "unit-test", "playerKey": "player-1"})
        state = websocket.receive_json()

    assert state["type"] == "room_state"
    assert [token["id"] for token in state["tokens"][:4]] == ["player-1", "player-2", "player-3", "player-4"]
    assert [token["owner"] for token in state["tokens"][:4]] == ["player-1", "player-2", "player-3", "player-4"]
    assert all(token["kind"] == "character" for token in state["tokens"])
    assert [token["avatarUrl"] for token in state["tokens"][:4]] == [
        "/campaigns/test-campaign/party/ex1.png",
        "/campaigns/test-campaign/party/ex2.png",
        "/campaigns/test-campaign/party/ex3.png",
        "/campaigns/test-campaign/party/ex4.png",
    ]
    assert all(token["inScene"] is False for token in state["tokens"])
    assert state["fog"] == {"hideMode": False, "brushSize": 120, "revealedAreas": []}
    assert state["board"]["id"] == "-"
    assert state["board"]["width"] == 1200
    assert state["board"]["height"] == 720
    assert state["boards"][0]["id"] == "-"
    assert any(board["id"] == "store-basement" and board["width"] == 1000 and board["height"] == 700 for board in state["boards"])
    assert all(board["id"] != "green" for board in state["boards"])
    assert any(asset["kind"] == "asset" and asset["id"] == "npc1" for asset in state["assets"])
    assert any(asset["kind"] == "asset" and asset["id"] == "aboleth" for asset in state["assets"])
    assert any(asset["kind"] == "asset" and asset["id"] == "black-greatwyrm" for asset in state["assets"])


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


def test_player_can_join_with_configured_character_name() -> None:
    client = TestClient(server.app)

    with client.websocket_connect("/ws") as marina:
        marina.receive_json()
        marina.send_json({"type": "join_room", "roomId": "name-identity-test", "playerKey": "Marina"})
        marina.receive_json()

        marina.send_json({"type": "request_token_lock", "tokenId": "player-1"})
        locked = marina.receive_json()

    assert locked["type"] == "token_updated"
    assert locked["token"]["id"] == "player-1"
    assert locked["token"]["lockedBy"] == "player-1"


def test_room_uses_campaign_specific_boards_and_party() -> None:
    client = TestClient(server.app)

    with client.websocket_connect("/ws") as websocket:
        websocket.receive_json()
        websocket.send_json({"type": "join_room", "roomId": "test-campaign-2", "playerKey": "dm"})
        state = websocket.receive_json()

    assert state["type"] == "room_state"
    party_tokens = [token for token in state["tokens"] if token["kind"] == "character"]
    assert [token["id"] for token in party_tokens] == ["player-1", "player-2"]
    assert [token["name"] for token in party_tokens] == ["Marina", "Edward"]
    assert [token["avatarUrl"] for token in party_tokens] == [
        "/campaigns/test-campaign-2/party/ex1.png",
        "/campaigns/test-campaign-2/party/ex2.png",
    ]
    assert any(board["id"] == "village" and board["url"] == "/campaigns/test-campaign-2/boards/village.png" for board in state["boards"])
    assert all(board["id"] not in {"store-basement", "windmill"} for board in state["boards"])


def test_campaign_specific_player_name_resolution() -> None:
    client = TestClient(server.app)

    with client.websocket_connect("/ws") as marina:
        marina.receive_json()
        marina.send_json({"type": "join_room", "roomId": "test-campaign-2", "playerKey": "Marina"})
        marina.receive_json()

        marina.send_json({"type": "request_token_lock", "tokenId": "player-1"})
        locked = marina.receive_json()

    assert locked["type"] == "token_updated"
    assert locked["token"]["id"] == "player-1"
    assert locked["token"]["lockedBy"] == "player-1"


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


def test_avatar_upload_rejects_missing_token_and_oversized_file(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(server, "UPLOAD_DIR", tmp_path)
    monkeypatch.setattr(server, "MAX_AVATAR_BYTES", 3)
    client = TestClient(server.app)

    missing = client.post(
        "/api/rooms/avatar-error-test/tokens/not-a-token/avatar?playerKey=dm",
        files={"file": ("hero.png", make_image("PNG"), "image/png")},
    )
    oversized = client.post(
        "/api/rooms/avatar-error-test/tokens/player-1/avatar?playerKey=player-1",
        files={"file": ("hero.png", b"1234", "image/png")},
    )

    assert missing.status_code == 404
    assert missing.json()["detail"] == "Token not found"
    assert oversized.status_code == 400
    assert oversized.json()["detail"] == "Avatar image is too large"


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


def test_campaign_save_path_uses_matching_campaign_folder() -> None:
    assert server.save_path("test-campaign-2") == server.CAMPAIGN_DIR / "test-campaign-2" / "saves" / "test-campaign-2.json"


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
    assert player_one_token["avatarUrl"] == "/campaigns/test-campaign/party/ex1.png"


def test_saved_character_metadata_is_replaced_by_static_party_manifest(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(server, "SAVE_DIR", tmp_path)
    saved_data = {
        "roomId": "static-party-test",
        "boardId": "green",
        "fog": {"hideMode": False, "brushSize": 120, "revealedAreas": []},
        "tokens": [
            {
                "id": "player-1",
                "kind": "character",
                "name": "Old Saved Name",
                "owner": "player-1",
                "color": "#000000",
                "x": 333,
                "y": 444,
                "radius": 88,
                "inScene": True,
                "avatarUrl": "/uploads/static-party-test/player-1/avatar.png",
            }
        ],
    }
    (tmp_path / "static-party-test.json").write_text(json.dumps(saved_data), encoding="utf-8")

    room = server.get_or_create_room("static-party-test")

    token = room.tokens["player-1"]
    manifest_member = server.load_party_members()[0]
    assert token.name == manifest_member.name
    assert token.avatarUrl == manifest_member.avatarUrl
    assert token.color == server.DEFAULT_TOKEN_COLOR
    assert token.x == 333
    assert token.y == 444
    assert token.radius == 88
    assert token.inScene is True


def test_room_state_uses_blank_board_when_no_campaign_boards(monkeypatch) -> None:
    monkeypatch.setattr(server, "list_boards", lambda campaign_id=None: [])

    room = server.get_or_create_room("no-board-test")
    state = server.room_state_message(room)

    assert room.board_id == "-"
    assert state["board"] == {"id": "-", "name": "-", "width": 1200, "height": 720}
    assert state["boards"] == []


def test_dm_can_load_saved_room_state_without_restart(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(server, "SAVE_DIR", tmp_path)
    room = server.get_or_create_room("manual-load-test")
    dm_socket = FakeSocket()
    dm = server.Player(id="connection-1", name="DM", player_key="dm", websocket=dm_socket, room_id=room.id)
    room.players[dm.id] = dm

    room.tokens["player-1"].inScene = True
    room.tokens["player-1"].x = 111
    room.tokens["player-1"].y = 222
    room.board_id = "windmill"
    room.fog.hideMode = True
    room.fog.revealedAreas.append(server.RevealedArea(x=200, y=300, radius=80))
    server.save_room_to_disk(room)

    room.tokens["player-1"].x = 900
    room.tokens["player-1"].y = 600
    room.board_id = ""
    room.fog.hideMode = False
    room.fog.revealedAreas = []

    asyncio.run(server.load_room_from_disk(room, dm))

    assert room.tokens["player-1"].x == 111
    assert room.tokens["player-1"].y == 222
    assert room.board_id == "windmill"
    assert room.fog.hideMode is True
    assert room.fog.revealedAreas == [server.RevealedArea(x=200, y=300, radius=80)]
    assert dm_socket.messages[-1]["type"] == "room_state"
    assert dm_socket.messages[-1]["board"]["id"] == "windmill"


def test_saved_large_board_token_positions_load_without_green_board_clamp(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(server, "SAVE_DIR", tmp_path)
    room = server.get_or_create_room("large-board-position-load-test")
    room.board_id = "windmill"
    room.tokens["player-1"].inScene = True
    room.tokens["player-1"].x = 2500
    room.tokens["player-1"].y = 1200
    server.save_room_to_disk(room)

    server.rooms.clear()
    loaded = server.get_or_create_room("large-board-position-load-test")

    assert loaded.board_id == "windmill"
    assert loaded.tokens["player-1"].x == 2500
    assert loaded.tokens["player-1"].y == 1200


def test_saved_large_board_fog_positions_load_without_default_board_clamp(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(server, "SAVE_DIR", tmp_path)
    room = server.get_or_create_room("large-board-fog-load-test")
    room.board_id = "windmill"
    room.fog.hideMode = True
    room.fog.brushSize = 120
    room.fog.revealedAreas = [server.RevealedArea(x=2200, y=1400, radius=120)]
    server.save_room_to_disk(room)

    server.rooms.clear()
    loaded = server.get_or_create_room("large-board-fog-load-test")

    assert loaded.board_id == "windmill"
    assert loaded.fog.hideMode is True
    assert loaded.fog.revealedAreas == [server.RevealedArea(x=2200, y=1400, radius=120)]


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


def test_reveal_fog_skips_redundant_nearby_points() -> None:
    room = server.get_or_create_room("fog-dedupe-test")
    dm_socket = FakeSocket()
    dm = server.Player(id="connection-1", name="DM", player_key="dm", websocket=dm_socket, room_id=room.id)
    room.players[dm.id] = dm
    room.fog.hideMode = True

    asyncio.run(server.reveal_fog(room, dm, {"x": 100, "y": 100, "radius": 80}))
    asyncio.run(server.reveal_fog(room, dm, {"x": 104, "y": 104, "radius": 80}))
    asyncio.run(server.reveal_fog(room, dm, {"x": 140, "y": 100, "radius": 80}))

    assert room.fog.revealedAreas == [
        server.RevealedArea(x=100, y=100, radius=80),
        server.RevealedArea(x=140, y=100, radius=80),
    ]
    assert [message["type"] for message in dm_socket.messages] == ["fog_updated", "fog_updated"]


def test_only_dm_can_switch_boards() -> None:
    client = TestClient(server.app)

    with client.websocket_connect("/ws") as player_one:
        player_one.receive_json()
        player_one.send_json({"type": "join_room", "roomId": "board-permission-test", "playerKey": "player-1"})
        player_one.receive_json()

        player_one.send_json({"type": "set_board", "boardId": "windmill"})

        room = server.rooms["board-permission-test"]
        assert room.board_id == "-"


def test_dm_can_switch_board_and_broadcast_update() -> None:
    room = server.get_or_create_room("board-switch-test")
    dm_socket = FakeSocket()
    player_socket = FakeSocket()
    dm = server.Player(id="connection-1", name="DM", player_key="dm", websocket=dm_socket, room_id=room.id)
    player_one = server.Player(id="connection-2", name="Player 1", player_key="player-1", websocket=player_socket, room_id=room.id)
    room.players[dm.id] = dm
    room.players[player_one.id] = player_one

    asyncio.run(server.set_board(room, dm, "windmill"))
    dm_update = dm_socket.messages[-1]
    player_update = player_socket.messages[-1]

    assert dm_update["type"] == "board_updated"
    assert dm_update["board"]["id"] == "windmill"
    assert dm_update["board"]["width"] == 2500
    assert dm_update["board"]["height"] == 1618
    assert player_update["type"] == "board_updated"
    assert player_update["board"]["id"] == "windmill"


def test_dm_can_switch_to_blank_board() -> None:
    room = server.get_or_create_room("blank-board-switch-test")
    room.board_id = "windmill"
    dm_socket = FakeSocket()
    dm = server.Player(id="connection-1", name="DM", player_key="dm", websocket=dm_socket, room_id=room.id)
    room.players[dm.id] = dm

    asyncio.run(server.set_board(room, dm, "-"))

    assert room.board_id == "-"
    assert dm_socket.messages[-1]["type"] == "board_updated"
    assert dm_socket.messages[-1]["board"] == {"id": "-", "name": "-", "width": 1200, "height": 720}


def test_dm_switches_board_within_room_campaign() -> None:
    room = server.get_or_create_room("test-campaign-2")
    dm_socket = FakeSocket()
    dm = server.Player(id="connection-1", name="DM", player_key="dm", websocket=dm_socket, room_id=room.id)
    room.players[dm.id] = dm

    asyncio.run(server.set_board(room, dm, "village"))

    assert room.board_id == "village"
    assert dm_socket.messages[-1]["type"] == "board_updated"
    assert dm_socket.messages[-1]["board"]["url"] == "/campaigns/test-campaign-2/boards/village.png"


def test_switching_boards_while_hidden_resets_fog_reveals() -> None:
    room = server.get_or_create_room("board-fog-reset-test")
    dm_socket = FakeSocket()
    player_socket = FakeSocket()
    dm = server.Player(id="connection-1", name="DM", player_key="dm", websocket=dm_socket, room_id=room.id)
    player = server.Player(id="connection-2", name="Player 1", player_key="player-1", websocket=player_socket, room_id=room.id)
    room.players[dm.id] = dm
    room.players[player.id] = player
    room.fog.hideMode = True
    room.fog.revealedAreas.append(server.RevealedArea(x=100, y=120, radius=80))

    asyncio.run(server.set_board(room, dm, "windmill"))

    assert room.board_id == "windmill"
    assert room.fog.hideMode is True
    assert room.fog.revealedAreas == []
    assert [message["type"] for message in dm_socket.messages] == ["board_updated", "fog_updated"]
    assert dm_socket.messages[-1]["fog"] == {"hideMode": True, "brushSize": 120, "revealedAreas": []}
    assert [message["type"] for message in player_socket.messages] == ["board_updated", "fog_updated"]


def test_switching_boards_while_unhidden_does_not_reset_fog() -> None:
    room = server.get_or_create_room("board-fog-unhidden-test")
    dm_socket = FakeSocket()
    dm = server.Player(id="connection-1", name="DM", player_key="dm", websocket=dm_socket, room_id=room.id)
    room.players[dm.id] = dm
    room.fog.hideMode = False
    room.fog.revealedAreas.append(server.RevealedArea(x=100, y=120, radius=80))

    asyncio.run(server.set_board(room, dm, "windmill"))

    assert room.board_id == "windmill"
    assert room.fog.revealedAreas == [server.RevealedArea(x=100, y=120, radius=80)]
    assert [message["type"] for message in dm_socket.messages] == ["board_updated"]


def test_saved_room_state_loads_selected_board(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(server, "SAVE_DIR", tmp_path)
    client = TestClient(server.app)

    with client.websocket_connect("/ws") as dm:
        dm.receive_json()
        dm.send_json({"type": "join_room", "roomId": "board-save-test", "playerKey": "dm"})
        dm.receive_json()
        dm.send_json({"type": "set_board", "boardId": "windmill"})
        dm.receive_json()

        saved = client.post("/api/rooms/board-save-test/save?playerKey=dm")
        assert saved.status_code == 200

    server.rooms.clear()

    with client.websocket_connect("/ws") as dm:
        dm.receive_json()
        dm.send_json({"type": "join_room", "roomId": "board-save-test", "playerKey": "dm"})
        state = dm.receive_json()

    assert state["board"]["id"] == "windmill"


def test_only_dm_can_load_registry_asset() -> None:
    room = server.get_or_create_room("asset-permission-test")
    player_socket = FakeSocket()
    player = server.Player(id="connection-1", name="Player 1", player_key="player-1", websocket=player_socket, room_id=room.id)
    room.players[player.id] = player

    asyncio.run(server.load_asset_token(room, player, "asset", "aboleth"))

    assert all(token.kind != server.TokenKind.ASSET for token in room.tokens.values())
    assert player_socket.messages == []


def test_dm_can_load_shared_asset_tokens() -> None:
    room = server.get_or_create_room("asset-load-test")
    dm_socket = FakeSocket()
    dm = server.Player(id="connection-1", name="DM", player_key="dm", websocket=dm_socket, room_id=room.id)
    room.players[dm.id] = dm

    asyncio.run(server.load_asset_token(room, dm, "asset", "npc1"))
    asyncio.run(server.load_asset_token(room, dm, "asset", "aboleth"))
    asyncio.run(server.load_asset_token(room, dm, "asset", "black-greatwyrm"))

    npc = room.tokens["asset-1"]
    monster = room.tokens["asset-2"]
    second_monster = room.tokens["asset-3"]
    assert npc.kind == server.TokenKind.ASSET
    assert npc.owner == "dm"
    assert npc.avatarUrl == "/shared/assets/npc1.png"
    assert monster.kind == server.TokenKind.ASSET
    assert monster.owner == "dm"
    assert monster.avatarUrl.startswith("/shared/assets/aboleth.")
    assert second_monster.kind == server.TokenKind.ASSET
    assert second_monster.owner == "dm"
    assert second_monster.avatarUrl == "/shared/assets/black-greatwyrm.png"
    assert [message["type"] for message in dm_socket.messages[-3:]] == ["token_updated", "token_updated", "token_updated"]


def test_shared_files_are_available_as_global_assets() -> None:
    assets = server.list_assets()

    aboleth = next(asset for asset in assets if asset.kind == server.TokenKind.ASSET and asset.id == "aboleth")
    assert aboleth.avatarUrl == "/shared/assets/aboleth.png"


def test_dm_loaded_asset_uses_active_board_center() -> None:
    room = server.get_or_create_room("asset-board-size-test")
    room.board_id = "windmill"
    dm_socket = FakeSocket()
    dm = server.Player(id="connection-1", name="DM", player_key="dm", websocket=dm_socket, room_id=room.id)
    room.players[dm.id] = dm

    asyncio.run(server.load_asset_token(room, dm, "asset", "aboleth"))

    monster = room.tokens["asset-1"]
    assert monster.x == 1250
    assert monster.y == 809
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
    room.board_id = "windmill"
    room.fog.hideMode = True
    room.fog.revealedAreas.append(server.RevealedArea(x=20, y=30, radius=40))
    room.tokens["player-1"].inScene = True
    room.tokens["player-1"].lockedBy = "player-1"

    asyncio.run(server.clear_scene(room, dm))

    assert all(token.inScene is False for token in room.tokens.values())
    assert all(token.lockedBy is None for token in room.tokens.values())
    assert room.board_id == "windmill"
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


def test_http_resize_rejects_missing_token() -> None:
    client = TestClient(server.app)

    response = client.post("/api/rooms/resize-missing-test/tokens/not-a-token/radius?playerKey=dm&radius=72")

    assert response.status_code == 404
    assert response.json()["detail"] == "Token resize failed"


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
    room.board_id = "windmill"
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


def test_dm_can_delete_loaded_asset() -> None:
    room = server.get_or_create_room("delete-asset-test")
    dm_socket = FakeSocket()
    player_socket = FakeSocket()
    dm = server.Player(id="connection-1", name="DM", player_key="dm", websocket=dm_socket, room_id=room.id)
    player = server.Player(id="connection-2", name="Player 1", player_key="player-1", websocket=player_socket, room_id=room.id)
    room.players[dm.id] = dm
    room.players[player.id] = player

    asyncio.run(server.load_asset_token(room, dm, "asset", "aboleth"))
    asyncio.run(server.delete_token(room, dm, "asset-1"))

    assert "asset-1" not in room.tokens
    assert dm_socket.messages[-1] == {"type": "token_deleted", "tokenId": "asset-1"}
    assert player_socket.messages[-1] == {"type": "token_deleted", "tokenId": "asset-1"}


def test_sheet_endpoint_returns_party_sheets_for_player(tmp_path, monkeypatch) -> None:
    write_party_campaign(
        tmp_path,
        "sheet-player-test",
        PartyMemberConfig(
            id="player-1",
            name="Marina",
            maxHp=31,
            abilityScores=AbilityScores(strength=16, dexterity=14, constitution=15, intelligence=10, wisdom=12, charisma=8),
            sheet=PartyMemberSheet(
                race="Human",
                classes=[CharacterClassLevel(name=ClassType.FIGHTER, level=7)],
                attacks=[
                    AttackAction(
                        id="longsword",
                        name="Longsword",
                        ability=AbilityType.STRENGTH,
                        damageDiceCount=1,
                        damageDiceType=DiceType.D8,
                    )
                ],
            ),
        ),
        PartyMemberConfig(id="player-2", name="Edward"),
        PartyMemberConfig(id="player-3", name="Hal"),
        PartyMemberConfig(id="player-4", name="Valarie"),
    )
    monkeypatch.setattr(server, "CAMPAIGN_DIR", tmp_path)
    client = TestClient(server.app)

    response = client.get("/api/rooms/sheet-player-test/sheet?playerKey=Marina")

    assert response.status_code == 200
    body = response.json()
    assert body["type"] == "sheet_state"
    assert body["playerKey"] == "player-1"
    assert [sheet["id"] for sheet in body["sheets"]] == ["player-1", "player-2", "player-3", "player-4"]
    marina = body["sheets"][0]
    assert marina["name"] == "Marina"
    assert marina["hp"]["current"] == marina["hp"]["max"]
    assert marina["characterClass"] == {"name": "fighter", "nameLabel": "Fighter", "level": 7}
    assert marina["race"] == "Human"
    assert marina["resources"][0]["id"] == "secondWind"
    assert any(resource["id"] == "actionSurge" for resource in marina["resources"])
    assert set(marina["abilityScores"]) == {"strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"}
    assert marina["attacks"][0]["id"] == "longsword"
    assert marina["attacks"][0]["damageDie"] == "1d8"
    assert body["pendingRolls"] == []
    assert body["rollHistory"] == []


def test_dm_sheet_endpoint_includes_loaded_asset_sheets() -> None:
    client = TestClient(server.app)
    room = server.get_or_create_room("sheet-dm-test")
    dm = server.Player(id="connection-1", name="DM", player_key="dm", websocket=FakeSocket(), room_id=room.id)
    asyncio.run(server.load_asset_token(room, dm, "asset", "aboleth"))

    dm_response = client.get("/api/rooms/sheet-dm-test/sheet?playerKey=dm")
    player_response = client.get("/api/rooms/sheet-dm-test/sheet?playerKey=player-1")

    assert dm_response.status_code == 200
    assert any(sheet["id"] == "asset-1" and sheet["name"] == "Aboleth" for sheet in dm_response.json()["sheets"])
    assert all(sheet["kind"] == "character" for sheet in player_response.json()["sheets"])


def test_sheet_roll_permissions_and_payload(monkeypatch) -> None:
    client = TestClient(server.app)
    monkeypatch.setattr(server.random, "randint", lambda minimum, maximum: 12)
    room = server.get_or_create_room("sheet-roll-test")
    dm_socket = FakeSocket()
    player_socket = FakeSocket()
    room.players["connection-1"] = server.Player(id="connection-1", name="DM", player_key="dm", websocket=dm_socket, room_id=room.id)
    room.players["connection-2"] = server.Player(id="connection-2", name="Player 1", player_key="player-1", websocket=player_socket, room_id=room.id)

    own_roll = client.post("/api/rooms/sheet-roll-test/sheet/player-1/rolls/attack?playerKey=player-1")
    forbidden = client.post("/api/rooms/sheet-roll-test/sheet/player-2/rolls/attack?playerKey=player-1")
    dm_roll = client.post("/api/rooms/sheet-roll-test/sheet/player-2/rolls/attack?playerKey=dm")

    assert own_roll.status_code == 200
    own_roll_body = own_roll.json()["roll"]
    assert own_roll_body["sheetId"] == "player-1"
    assert own_roll_body["resolution"] == "attackVsArmorClass"
    assert own_roll_body["source"] == {
        "section": "attacks",
        "sectionLabel": "Attacks",
        "sourceId": "longsword",
        "actionId": "attackVsArmorClass",
    }
    assert own_roll_body["sourceLabel"] == "Longsword"
    assert own_roll_body["label"] == "Attack Roll"
    assert "iconUrl" not in own_roll_body
    assert own_roll_body["dice"] == [12]
    assert own_roll_body["die"] == "d20"
    assert own_roll_body["total"] == 12 + own_roll_body["modifier"]
    assert forbidden.status_code == 403
    assert dm_roll.status_code == 200
    assert dm_roll.json()["roll"]["roller"] == "dm"
    assert dm_socket.messages[0]["type"] == "roll_created"
    assert dm_socket.messages[0]["roll"] == own_roll_body
    assert dm_socket.messages[0]["logEntry"]["roll"] == own_roll_body
    assert player_socket.messages[0] == dm_socket.messages[0]


def test_player_can_roll_fire_bolt_spell_attack_and_scaled_damage(tmp_path, monkeypatch) -> None:
    fire_bolt = spell_entry(SpellId.FIRE_BOLT)
    burning_hands = wizard_spell_entry(SpellId.BURNING_HANDS)
    assert fire_bolt is not None
    assert burning_hands is not None
    write_party_campaign(
        tmp_path,
        "spell-roll-test",
        PartyMemberConfig(
            id="player-1",
            name="Evoker",
            maxHp=44,
            abilityScores=AbilityScores(strength=8, dexterity=14, constitution=14, intelligence=18, wisdom=10, charisma=10),
            sheet=PartyMemberSheet(classes=[CharacterClassLevel(name=ClassType.WIZARD, level=5)], spells=[fire_bolt, burning_hands]),
        ),
        PartyMemberConfig(
            id="player-2",
            name="Dodger",
            maxHp=30,
            abilityScores=AbilityScores(strength=10, dexterity=16, constitution=12, intelligence=10, wisdom=10, charisma=10),
            sheet=PartyMemberSheet(classes=[CharacterClassLevel(name=ClassType.ROGUE, level=5)], savingThrowProficiencies=[AbilityType.DEXTERITY]),
        ),
    )
    monkeypatch.setattr(server, "CAMPAIGN_DIR", tmp_path)
    monkeypatch.setattr("dnd_board.character_sheet.random.randint", lambda minimum, maximum: 4 if maximum in (6, 10) else 12)
    client = TestClient(server.app)

    attack = client.post("/api/rooms/spell-roll-test/sheet/player-1/spells/fireBolt/rolls/attack?playerKey=player-1")
    damage = client.post("/api/rooms/spell-roll-test/sheet/player-1/spells/fireBolt/rolls/damage?playerKey=player-1")
    burning_hands_damage = client.post("/api/rooms/spell-roll-test/sheet/player-1/spells/burningHands/rolls/damage?playerKey=player-1&spellSlotLevel=3")
    unavailable_slot = client.post("/api/rooms/spell-roll-test/sheet/player-1/spells/burningHands/rolls/damage?playerKey=player-1&spellSlotLevel=4")
    too_low_slot = client.post("/api/rooms/spell-roll-test/sheet/player-1/spells/burningHands/rolls/damage?playerKey=player-1&spellSlotLevel=0")
    missing_spell = client.post("/api/rooms/spell-roll-test/sheet/player-1/spells/missing/rolls/damage?playerKey=player-1")

    assert attack.status_code == 200
    assert damage.status_code == 200
    assert burning_hands_damage.status_code == 200
    assert unavailable_slot.status_code == 400
    assert too_low_slot.status_code == 400
    assert missing_spell.status_code == 404
    attack_roll = attack.json()["roll"]
    damage_roll = damage.json()["roll"]
    assert attack_roll["source"] == {
        "section": "spells",
        "sectionLabel": "Spells",
        "sourceId": "fireBolt",
        "actionId": "attackVsArmorClass",
    }
    assert attack_roll["label"] == "Spell Attack"
    assert attack_roll["modifier"] == 7
    assert attack_roll["total"] == 19
    assert attack_roll["damageType"] == "fire"
    assert damage_roll["source"] == {
        "section": "spells",
        "sectionLabel": "Spells",
        "sourceId": "fireBolt",
        "actionId": "damage-0",
    }
    assert damage_roll["label"] == "Spell Damage"
    assert damage_roll["die"] == "2d10"
    assert damage_roll["total"] == 8
    assert damage_roll["damageType"] == "fire"
    burning_hands_roll = burning_hands_damage.json()["roll"]
    assert burning_hands_roll["source"]["sourceId"] == "burningHands"
    assert burning_hands_roll["source"]["actionId"] == "damage-0-slot-3"
    assert burning_hands_roll["die"] == "5d6"
    assert burning_hands_roll["total"] == 20
    assert burning_hands_roll["damageType"] == "fire"
    assert burning_hands_roll["damageSavingThrow"] == "dexterity"
    assert burning_hands_roll["damageSaveDc"] == 15
    assert burning_hands_roll["damageSaveOutcome"] == "halfDamage"

    resolution = client.post(f"/api/rooms/spell-roll-test/rolls/{burning_hands_roll['id']}/resolve?playerKey=dm&targetSheetId=player-2")
    dodger = client.get("/api/rooms/spell-roll-test/sheet/player-2?playerKey=player-2").json()["sheet"]
    resolution_body = resolution.json()["resolution"]

    assert resolution.status_code == 200
    assert dodger["hp"] == {"current": 20, "max": 30, "temporary": 0}
    assert "passes DC 15 Dexterity save for half damage" in resolution_body["outcome"]
    assert resolution_body["responseRolls"][0]["label"] == "Dexterity Save"
    assert resolution_body["responseRolls"][0]["total"] == 18


def test_player_can_roll_tashas_hideous_laughter_effect_and_dm_can_preserve_roll(tmp_path, monkeypatch) -> None:
    tasha = wizard_spell_entry(SpellId.TASHA_S_HIDEOUS_LAUGHTER)
    assert tasha is not None
    assert tasha.effects is not None
    stale_tasha = replace(
        tasha,
        effects=[
            replace(
                tasha.effects[0],
                conditions=[
                    replace(condition, removalTrigger=None, removalAdvantage=False)
                    for condition in tasha.effects[0].conditions or []
                ],
            )
        ],
    )
    write_party_campaign(
        tmp_path,
        "tasha-effect-test",
        PartyMemberConfig(
            id="player-1",
            name="Enchanter",
            maxHp=30,
            abilityScores=AbilityScores(strength=8, dexterity=14, constitution=14, intelligence=18, wisdom=10, charisma=10),
            sheet=PartyMemberSheet(
                classes=[CharacterClassLevel(name=ClassType.WIZARD, level=5)],
                spells=[stale_tasha],
                attacks=[
                    AttackAction(
                        "staff",
                        "Quarterstaff",
                        AbilityType.STRENGTH,
                        1,
                        DiceType.D6,
                        damageType=DamageType.BLUDGEONING,
                    )
                ],
            ),
        ),
        PartyMemberConfig(
            id="player-2",
            name="Target",
            maxHp=30,
            abilityScores=AbilityScores(strength=10, dexterity=10, constitution=12, intelligence=10, wisdom=8, charisma=10),
            sheet=PartyMemberSheet(classes=[CharacterClassLevel(name=ClassType.FIGHTER, level=5)]),
        ),
    )
    monkeypatch.setattr(server, "CAMPAIGN_DIR", tmp_path)
    server_rolls = iter([1, 2, 20])
    monkeypatch.setattr(server.random, "randint", lambda minimum, maximum: next(server_rolls) if maximum == 20 else 4)
    client = TestClient(server.app)

    effect_response = client.post("/api/rooms/tasha-effect-test/sheet/player-1/spells/tashaSHideousLaughter/rolls/effect?playerKey=player-1")

    assert effect_response.status_code == 200
    effect_roll = effect_response.json()["roll"]
    assert effect_roll["source"]["sourceId"] == "tashaSHideousLaughter"
    assert effect_roll["source"]["actionId"] == "condition-0"
    assert effect_roll["label"] == "Spell Effect"
    assert [effect["condition"] for effect in effect_roll["conditionEffects"]] == ["prone", "incapacitated"]
    assert {effect["savingThrow"] for effect in effect_roll["conditionEffects"]} == {"wisdom"}
    assert {effect["saveDc"] for effect in effect_roll["conditionEffects"]} == {15}

    resolution = client.post(
        f"/api/rooms/tasha-effect-test/rolls/{effect_roll['id']}/resolve?playerKey=dm&targetSheetId=player-2&preserveRoll=true"
    )
    target = client.get("/api/rooms/tasha-effect-test/sheet/player-2?playerKey=player-2").json()["sheet"]
    pending = client.get("/api/rooms/tasha-effect-test/sheet?playerKey=dm").json()["pendingRolls"]
    resolution_body = resolution.json()["resolution"]

    assert resolution.status_code == 200
    assert set(target["conditions"]) >= {"prone", "incapacitated"}
    assert "fails DC 15 Wisdom save and gains Prone, and Incapacitated" in resolution_body["outcome"]
    assert len(resolution_body["responseRolls"]) == 1
    assert resolution_body["responseRolls"][0]["label"] == "Wisdom Save"
    assert resolution_body["responseRolls"][0]["total"] == 0
    assert effect_roll["id"] in {roll["id"] for roll in pending}
    assert any(roll["label"] == "Wisdom Save" for roll in pending)

    damage_response = client.post("/api/rooms/tasha-effect-test/sheet/player-1/rolls/damage?playerKey=player-1&attackId=staff")
    damage_roll = damage_response.json()["roll"]
    damage_resolution = client.post(f"/api/rooms/tasha-effect-test/rolls/{damage_roll['id']}/resolve?playerKey=dm&targetSheetId=player-2")
    cleared_target = client.get("/api/rooms/tasha-effect-test/sheet/player-2?playerKey=player-2").json()["sheet"]
    damage_resolution_body = damage_resolution.json()["resolution"]

    assert damage_response.status_code == 200
    assert damage_resolution.status_code == 200
    assert set(cleared_target["conditions"]).isdisjoint({"prone", "incapacitated"})
    assert "passes DC 15 Wisdom save with Advantage after taking damage and ends Prone, and Incapacitated" in damage_resolution_body["outcome"]
    assert damage_resolution_body["responseRolls"][0]["dice"] == [2, 20]
    assert damage_resolution_body["responseRolls"][0]["die"] == "2d20kh1"
    assert damage_resolution_body["responseRolls"][0]["total"] == 19


def test_player_can_roll_ability_check_and_saving_throw(tmp_path, monkeypatch) -> None:
    write_party_campaign(
        tmp_path,
        "ability-roll-test",
        PartyMemberConfig(
            id="player-1",
            name="Roll Fighter",
            maxHp=31,
            abilityScores=AbilityScores(strength=16, dexterity=14, constitution=15, intelligence=10, wisdom=12, charisma=8),
            sheet=PartyMemberSheet(
                classes=[CharacterClassLevel(name=ClassType.FIGHTER, level=7)],
                savingThrowProficiencies=[AbilityType.STRENGTH, AbilityType.CONSTITUTION],
            ),
        ),
    )
    monkeypatch.setattr(server, "CAMPAIGN_DIR", tmp_path)
    client = TestClient(server.app)
    monkeypatch.setattr(server.random, "randint", lambda minimum, maximum: 11)

    check = client.post("/api/rooms/ability-roll-test/sheet/player-1/rolls/ability-check?playerKey=player-1&ability=strength")
    save = client.post("/api/rooms/ability-roll-test/sheet/player-1/rolls/saving-throw?playerKey=player-1&ability=strength")

    assert check.status_code == 200
    check_roll = check.json()["roll"]
    assert check_roll["label"] == "Strength Check"
    assert check_roll["sourceLabel"] == "Strength"
    assert check_roll["source"] == {
        "section": "abilityScores",
        "sectionLabel": "Ability Scores",
        "sourceId": "strength",
        "actionId": "check",
    }
    assert check_roll["modifierBreakdown"] == [{"source": "Strength", "value": 3, "description": ""}]
    assert check_roll["total"] == 14

    assert save.status_code == 200
    save_roll = save.json()["roll"]
    assert save_roll["label"] == "Strength Save"
    assert save_roll["sourceLabel"] == "Strength"
    assert save_roll["source"]["actionId"] == "save"
    assert save_roll["modifierBreakdown"] == [{"source": "Strength", "value": 3, "description": ""}, {"source": "Proficiency", "value": 3, "description": ""}]
    assert save_roll["total"] == 17


def test_ability_roll_rejects_unknown_ability() -> None:
    client = TestClient(server.app)

    response = client.post("/api/rooms/unknown-ability-test/sheet/player-1/rolls/ability-check?playerKey=player-1&ability=luck")

    assert response.status_code == 404
    assert response.json()["detail"] == "Ability not found"


def test_player_can_update_owned_sheet_resource(tmp_path, monkeypatch) -> None:
    write_party_campaign(
        tmp_path,
        "resource-test",
        PartyMemberConfig(
            id="player-1",
            name="Resource Fighter",
            maxHp=36,
            abilityScores=AbilityScores(strength=16, dexterity=14, constitution=15, intelligence=10, wisdom=12, charisma=8),
            sheet=PartyMemberSheet(
                classes=[CharacterClassLevel(name=ClassType.FIGHTER, level=4, fightingStyles=[FightingStyleType.DEFENSE])],
                hitPointIncreases=[8, 8, 8],
                abilityScoreImprovements=["strength:2"],
            ),
        ),
    )
    monkeypatch.setattr(server, "CAMPAIGN_DIR", tmp_path)
    client = TestClient(server.app)

    response = client.post("/api/rooms/resource-test/sheet/player-1/resources/actionSurge?playerKey=player-1&currentUses=0")
    sheet = client.get("/api/rooms/resource-test/sheet/player-1?playerKey=player-1").json()["sheet"]
    action_surge = next(resource for resource in sheet["resources"] if resource["id"] == "actionSurge")

    assert response.status_code == 200
    assert action_surge["currentUses"] == 0


def test_sheet_resource_update_rejects_missing_resource(tmp_path, monkeypatch) -> None:
    write_party_campaign(
        tmp_path,
        "missing-resource-test",
        PartyMemberConfig(
            id="player-1",
            name="Resource Fighter",
            maxHp=12,
            abilityScores=AbilityScores(strength=16, dexterity=14, constitution=15, intelligence=10, wisdom=12, charisma=8),
            sheet=PartyMemberSheet(classes=[CharacterClassLevel(name=ClassType.FIGHTER, level=1, fightingStyles=[FightingStyleType.DEFENSE])]),
        ),
    )
    monkeypatch.setattr(server, "CAMPAIGN_DIR", tmp_path)
    client = TestClient(server.app)

    response = client.post("/api/rooms/missing-resource-test/sheet/player-1/resources/notAResource?playerKey=player-1&currentUses=0")

    assert response.status_code == 404
    assert response.json()["detail"] == "Resource not found"


def test_sheet_endpoint_rejects_missing_visible_sheet() -> None:
    client = TestClient(server.app)

    response = client.get("/api/rooms/missing-sheet-test/sheet/not-a-sheet?playerKey=player-1")

    assert response.status_code == 404
    assert response.json()["detail"] == "Sheet not found"


def test_player_can_update_owned_sheet_conditions(tmp_path, monkeypatch) -> None:
    write_party_campaign(
        tmp_path,
        "condition-test",
        PartyMemberConfig(
            id="player-1",
            name="Condition Fighter",
            maxHp=12,
            abilityScores=AbilityScores(strength=16, dexterity=14, constitution=15, intelligence=10, wisdom=12, charisma=8),
            sheet=PartyMemberSheet(classes=[CharacterClassLevel(name=ClassType.FIGHTER, level=1)]),
        ),
        PartyMemberConfig(
            id="player-2",
            name="Other Fighter",
            maxHp=12,
            abilityScores=AbilityScores(strength=16, dexterity=14, constitution=15, intelligence=10, wisdom=12, charisma=8),
            sheet=PartyMemberSheet(classes=[CharacterClassLevel(name=ClassType.FIGHTER, level=1)]),
        ),
    )
    monkeypatch.setattr(server, "CAMPAIGN_DIR", tmp_path)
    client = TestClient(server.app)

    denied = client.post("/api/rooms/condition-test/sheet/player-1/conditions/prone?playerKey=player-2&active=true")
    applied = client.post("/api/rooms/condition-test/sheet/player-1/conditions/prone?playerKey=player-1&active=true")
    cleared = client.post("/api/rooms/condition-test/sheet/player-1/conditions/prone?playerKey=player-1&active=false")

    assert denied.status_code == 403
    assert applied.status_code == 200
    assert applied.json()["sheet"]["conditions"] == ["prone"]
    assert cleared.status_code == 200
    assert cleared.json()["sheet"]["conditions"] == []


def test_player_can_update_generated_sheet_conditions_without_manifest(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(server, "CAMPAIGN_DIR", tmp_path)
    client = TestClient(server.app)

    applied = client.post("/api/rooms/generated-condition-test/sheet/player-1/conditions/prone?playerKey=player-1&active=true")
    sheet = client.get("/api/rooms/generated-condition-test/sheet/player-1?playerKey=player-1").json()["sheet"]

    assert applied.status_code == 200
    assert applied.json()["sheet"]["conditions"] == ["prone"]
    assert sheet["conditions"] == ["prone"]


def test_sheet_conditions_are_loaded_from_party_manifest(tmp_path, monkeypatch) -> None:
    write_party_campaign(
        tmp_path,
        "condition-load-test",
        PartyMemberConfig(
            id="player-1",
            name="Condition Fighter",
            maxHp=12,
            abilityScores=AbilityScores(strength=16, dexterity=14, constitution=15, intelligence=10, wisdom=12, charisma=8),
            sheet=PartyMemberSheet(
                classes=[CharacterClassLevel(name=ClassType.FIGHTER, level=1)],
                conditions=[ConditionType.FRIGHTENED, ConditionType.PRONE],
            ),
        ),
    )
    monkeypatch.setattr(server, "CAMPAIGN_DIR", tmp_path)
    client = TestClient(server.app)

    sheet = client.get("/api/rooms/condition-load-test/sheet/player-1?playerKey=player-1").json()["sheet"]

    assert sheet["conditions"] == ["frightened", "prone"]


def test_only_dm_can_level_sheet(tmp_path, monkeypatch) -> None:
    write_party_campaign(
        tmp_path,
        "level-permission-test",
        PartyMemberConfig(
            id="player-1",
            name="Level Fighter",
            maxHp=12,
            abilityScores=AbilityScores(strength=16, dexterity=14, constitution=15, intelligence=10, wisdom=12, charisma=8),
            sheet=PartyMemberSheet(classes=[CharacterClassLevel(name=ClassType.FIGHTER, level=1)]),
        ),
    )
    monkeypatch.setattr(server, "CAMPAIGN_DIR", tmp_path)
    client = TestClient(server.app)

    response = client.post("/api/rooms/level-permission-test/sheet/player-1/level?playerKey=player-1&delta=1")

    assert response.status_code == 403


def test_level_sheet_rejects_invalid_class(tmp_path, monkeypatch) -> None:
    write_party_campaign(
        tmp_path,
        "level-invalid-class-test",
        PartyMemberConfig(
            id="player-1",
            name="Level Rogue",
            maxHp=10,
            abilityScores=AbilityScores(strength=10, dexterity=16, constitution=14, intelligence=10, wisdom=12, charisma=8),
            sheet=PartyMemberSheet(classes=[CharacterClassLevel(name=ClassType.ROGUE, level=1)]),
        ),
    )
    monkeypatch.setattr(server, "CAMPAIGN_DIR", tmp_path)
    client = TestClient(server.app)

    response = client.post("/api/rooms/level-invalid-class-test/sheet/player-1/level?playerKey=dm&delta=1&className=bard")

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid class"


def test_dm_cannot_level_up_with_unresolved_level_choices(tmp_path, monkeypatch) -> None:
    write_party_campaign(
        tmp_path,
        "level-gate-test",
        PartyMemberConfig(
            id="player-1",
            name="Level Fighter",
            maxHp=36,
            abilityScores=AbilityScores(strength=16, dexterity=14, constitution=15, intelligence=10, wisdom=12, charisma=8),
            sheet=PartyMemberSheet(classes=[CharacterClassLevel(name=ClassType.FIGHTER, level=4)]),
        ),
    )
    monkeypatch.setattr(server, "CAMPAIGN_DIR", tmp_path)
    client = TestClient(server.app)

    response = client.post("/api/rooms/level-gate-test/sheet/player-1/level?playerKey=dm&delta=1")

    assert response.status_code == 400
    assert response.json()["detail"] == "Resolve pending level choices before leveling up: Hit Points, Ability Score Improvement, Fighter Skill Proficiencies, Martial Archetype, Fighting Style"


def test_level_one_fighter_must_choose_starting_fighting_style_before_level_up(tmp_path, monkeypatch) -> None:
    write_party_campaign(
        tmp_path,
        "level-one-style-gate-test",
        PartyMemberConfig(
            id="player-1",
            name="Level Fighter",
            maxHp=12,
            abilityScores=AbilityScores(strength=16, dexterity=14, constitution=15, intelligence=10, wisdom=12, charisma=8),
            sheet=PartyMemberSheet(classes=[CharacterClassLevel(name=ClassType.FIGHTER, level=1)]),
        ),
    )
    monkeypatch.setattr(server, "CAMPAIGN_DIR", tmp_path)
    client = TestClient(server.app)

    response = client.post("/api/rooms/level-one-style-gate-test/sheet/player-1/level?playerKey=dm&delta=1")

    assert response.status_code == 400
    assert response.json()["detail"] == "Resolve pending level choices before leveling up: Fighter Skill Proficiencies, Fighting Style"


def test_player_can_apply_own_level_choice_but_not_other_sheets(tmp_path, monkeypatch) -> None:
    write_party_campaign(
        tmp_path,
        "player-choice-test",
        PartyMemberConfig(
            id="player-1",
            name="Choice Fighter",
            maxHp=12,
            abilityScores=AbilityScores(strength=16, dexterity=14, constitution=15, intelligence=10, wisdom=12, charisma=8),
            sheet=PartyMemberSheet(classes=[CharacterClassLevel(name=ClassType.FIGHTER, level=1)]),
        ),
        PartyMemberConfig(
            id="player-2",
            name="Other Fighter",
            maxHp=12,
            abilityScores=AbilityScores(strength=16, dexterity=14, constitution=15, intelligence=10, wisdom=12, charisma=8),
            sheet=PartyMemberSheet(classes=[CharacterClassLevel(name=ClassType.FIGHTER, level=1)]),
        ),
    )
    monkeypatch.setattr(server, "CAMPAIGN_DIR", tmp_path)
    client = TestClient(server.app)

    other_player = client.post('/api/rooms/player-choice-test/sheet/player-1/choices/fighterFightingStyles?playerKey=player-2', json={"values": ["defense"]})
    owner = client.post('/api/rooms/player-choice-test/sheet/player-1/choices/fighterFightingStyles?playerKey=player-1', json={"values": ["defense"]})

    assert other_player.status_code == 403
    assert owner.status_code == 200
    assert owner.json()["sheet"]["classes"][0]["fightingStyles"] == ["defense"]


def test_progression_choice_rejects_non_list_values(tmp_path, monkeypatch) -> None:
    write_party_campaign(
        tmp_path,
        "choice-values-test",
        PartyMemberConfig(
            id="player-1",
            name="Choice Fighter",
            maxHp=12,
            abilityScores=AbilityScores(strength=16, dexterity=14, constitution=15, intelligence=10, wisdom=12, charisma=8),
            sheet=PartyMemberSheet(classes=[CharacterClassLevel(name=ClassType.FIGHTER, level=1)]),
        ),
    )
    monkeypatch.setattr(server, "CAMPAIGN_DIR", tmp_path)
    client = TestClient(server.app)

    response = client.post('/api/rooms/choice-values-test/sheet/player-1/choices/fighterFightingStyles?playerKey=player-1', json={"values": "defense"})

    assert response.status_code == 400
    assert response.json()["detail"] == "Choice values must be a list"


def test_progression_choice_rejects_invalid_choice_id(tmp_path, monkeypatch) -> None:
    write_party_campaign(
        tmp_path,
        "invalid-choice-test",
        PartyMemberConfig(
            id="player-1",
            name="Choice Fighter",
            maxHp=12,
            abilityScores=AbilityScores(strength=16, dexterity=14, constitution=15, intelligence=10, wisdom=12, charisma=8),
            sheet=PartyMemberSheet(classes=[CharacterClassLevel(name=ClassType.FIGHTER, level=1)]),
        ),
    )
    monkeypatch.setattr(server, "CAMPAIGN_DIR", tmp_path)
    client = TestClient(server.app)

    response = client.post('/api/rooms/invalid-choice-test/sheet/player-1/choices/notAChoice?playerKey=player-1', json={"values": []})

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid progression choice"


def test_player_can_apply_fighter_ability_score_improvement(tmp_path, monkeypatch) -> None:
    write_party_campaign(
        tmp_path,
        "asi-choice-test",
        PartyMemberConfig(
            id="player-1",
            name="ASI Fighter",
            maxHp=36,
            abilityScores=AbilityScores(strength=16, dexterity=14, constitution=15, intelligence=10, wisdom=12, charisma=8),
            sheet=PartyMemberSheet(classes=[CharacterClassLevel(name=ClassType.FIGHTER, level=4)]),
        ),
    )
    monkeypatch.setattr(server, "CAMPAIGN_DIR", tmp_path)
    client = TestClient(server.app)

    response = client.post('/api/rooms/asi-choice-test/sheet/player-1/choices/fighterAbilityScoreImprovement?playerKey=player-1', json={"values": ["strength", "dexterity"]})
    sheet = response.json()["sheet"]

    assert response.status_code == 200
    assert sheet["abilityScores"]["strength"] == 17
    assert sheet["abilityScores"]["dexterity"] == 15
    assert "fighterAbilityScoreImprovement" not in {choice["id"] for choice in sheet["pendingChoices"]}


def test_fighter_ability_score_improvement_can_apply_plus_two_and_caps_at_twenty(tmp_path, monkeypatch) -> None:
    write_party_campaign(
        tmp_path,
        "asi-cap-test",
        PartyMemberConfig(
            id="player-1",
            name="ASI Fighter",
            maxHp=36,
            abilityScores=AbilityScores(strength=19, dexterity=14, constitution=15, intelligence=10, wisdom=12, charisma=8),
            sheet=PartyMemberSheet(classes=[CharacterClassLevel(name=ClassType.FIGHTER, level=4)]),
        ),
    )
    monkeypatch.setattr(server, "CAMPAIGN_DIR", tmp_path)
    client = TestClient(server.app)

    response = client.post('/api/rooms/asi-cap-test/sheet/player-1/choices/fighterAbilityScoreImprovement?playerKey=player-1', json={"values": ["strength", "strength"]})
    sheet = response.json()["sheet"]

    assert response.status_code == 200
    assert sheet["abilityScores"]["strength"] == 20


def test_fighter_ability_score_improvement_updates_hp_when_constitution_modifier_changes(tmp_path, monkeypatch) -> None:
    write_party_campaign(
        tmp_path,
        "asi-constitution-test",
        PartyMemberConfig(
            id="player-1",
            name="ASI Fighter",
            maxHp=36,
            abilityScores=AbilityScores(strength=16, dexterity=14, constitution=15, intelligence=10, wisdom=12, charisma=8),
            sheet=PartyMemberSheet(classes=[CharacterClassLevel(name=ClassType.FIGHTER, level=4)]),
        ),
    )
    monkeypatch.setattr(server, "CAMPAIGN_DIR", tmp_path)
    client = TestClient(server.app)

    response = client.post('/api/rooms/asi-constitution-test/sheet/player-1/choices/fighterAbilityScoreImprovement?playerKey=player-1', json={"values": ["constitution", "constitution"]})
    sheet = response.json()["sheet"]

    assert response.status_code == 200
    assert sheet["abilityScores"]["constitution"] == 17
    assert sheet["hp"]["max"] == 40


def test_player_can_choose_feat_for_fighter_ability_score_improvement(tmp_path, monkeypatch) -> None:
    write_party_campaign(
        tmp_path,
        "asi-feat-test",
        PartyMemberConfig(
            id="player-1",
            name="Feat Fighter",
            maxHp=36,
            abilityScores=AbilityScores(strength=16, dexterity=14, constitution=15, intelligence=10, wisdom=12, charisma=8),
            sheet=PartyMemberSheet(classes=[CharacterClassLevel(name=ClassType.FIGHTER, level=4)]),
        ),
    )
    monkeypatch.setattr(server, "CAMPAIGN_DIR", tmp_path)
    client = TestClient(server.app)

    response = client.post('/api/rooms/asi-feat-test/sheet/player-1/choices/fighterAbilityScoreImprovement?playerKey=player-1', json={"values": ["feat:actor"]})
    sheet = response.json()["sheet"]
    feats = {feature["id"]: feature for feature in sheet["features"]}

    assert response.status_code == 200
    assert feats["actor"]["name"] == "Actor"
    assert feats["actor"]["source"] == rule_source_label(RuleSource.PLAYERS_HANDBOOK_2024)
    assert "fighterAbilityScoreImprovement" not in {choice["id"] for choice in sheet["pendingChoices"]}


def test_ability_score_improvement_rejects_non_general_feat(tmp_path, monkeypatch) -> None:
    write_party_campaign(
        tmp_path,
        "asi-origin-feat-test",
        PartyMemberConfig(
            id="player-1",
            name="Feat Fighter",
            maxHp=36,
            abilityScores=AbilityScores(strength=16, dexterity=14, constitution=15, intelligence=10, wisdom=12, charisma=8),
            sheet=PartyMemberSheet(classes=[CharacterClassLevel(name=ClassType.FIGHTER, level=4)]),
        ),
    )
    monkeypatch.setattr(server, "CAMPAIGN_DIR", tmp_path)
    client = TestClient(server.app)

    response = client.post('/api/rooms/asi-origin-feat-test/sheet/player-1/choices/fighterAbilityScoreImprovement?playerKey=player-1', json={"values": ["feat:alert"]})

    assert response.status_code == 400
    assert response.json()["detail"] == "That feat is not available from this progression choice"


def test_fighter_ability_score_improvement_rejects_duplicate_feat(tmp_path, monkeypatch) -> None:
    write_party_campaign(
        tmp_path,
        "asi-duplicate-feat-test",
        PartyMemberConfig(
            id="player-1",
            name="Feat Fighter",
            maxHp=36,
            abilityScores=AbilityScores(strength=16, dexterity=14, constitution=15, intelligence=10, wisdom=12, charisma=8),
            sheet=PartyMemberSheet(
                classes=[CharacterClassLevel(name=ClassType.FIGHTER, level=6)],
                abilityScoreImprovements=["feat:actor"],
                feats=[
                    general_feat_feature("actor")
                ],
            ),
        ),
    )
    monkeypatch.setattr(server, "CAMPAIGN_DIR", tmp_path)
    client = TestClient(server.app)

    response = client.post('/api/rooms/asi-duplicate-feat-test/sheet/player-1/choices/fighterAbilityScoreImprovement?playerKey=player-1', json={"values": ["feat:actor"]})

    assert response.status_code == 400


def test_tough_origin_feat_adds_hit_points_on_level_up(tmp_path, monkeypatch) -> None:
    write_party_campaign(
        tmp_path,
        "tough-level-up-test",
        PartyMemberConfig(
            id="player-1",
            name="Tough Fighter",
            maxHp=14,
            abilityScores=AbilityScores(strength=16, dexterity=14, constitution=15, intelligence=10, wisdom=12, charisma=8),
            sheet=PartyMemberSheet(
                classes=[CharacterClassLevel(name=ClassType.FIGHTER, level=1, fightingStyles=[FightingStyleType.DEFENSE])],
                skills={
                    enum_key(SkillType.ATHLETICS): ProficiencyLevel.PROFICIENT,
                    enum_key(SkillType.PERCEPTION): ProficiencyLevel.PROFICIENT,
                },
                feats=[general_feat_feature("tough")],
            ),
        ),
    )
    monkeypatch.setattr(server, "CAMPAIGN_DIR", tmp_path)
    client = TestClient(server.app)

    level_response = client.post("/api/rooms/tough-level-up-test/sheet/player-1/level?playerKey=dm&delta=1&className=fighter")
    hp_response = client.post("/api/rooms/tough-level-up-test/sheet/player-1/choices/hitPointIncrease?playerKey=dm", json={"values": ["fixed"]})

    assert level_response.status_code == 200
    assert hp_response.status_code == 200
    assert hp_response.json()["sheet"]["hp"]["max"] == 24


def test_dm_level_up_exposes_pending_fighter_choices_and_applies_them(tmp_path, monkeypatch) -> None:
    write_party_campaign(
        tmp_path,
        "level-choice-test",
        PartyMemberConfig(
            id="player-1",
            name="Level Fighter",
            maxHp=12,
            abilityScores=AbilityScores(strength=16, dexterity=14, constitution=15, intelligence=10, wisdom=12, charisma=8),
            sheet=PartyMemberSheet(
                classes=[CharacterClassLevel(name=ClassType.FIGHTER, level=2, fightingStyles=[FightingStyleType.DEFENSE])],
                skills={
                    enum_key(SkillType.ATHLETICS): ProficiencyLevel.PROFICIENT,
                    enum_key(SkillType.PERCEPTION): ProficiencyLevel.PROFICIENT,
                },
                hitPointIncreases=[8],
            ),
        ),
    )
    monkeypatch.setattr(server, "CAMPAIGN_DIR", tmp_path)
    client = TestClient(server.app)

    leveled = client.post("/api/rooms/level-choice-test/sheet/player-1/level?playerKey=dm&delta=1")
    sheet = leveled.json()["sheet"]
    choices = {choice["id"]: choice for choice in sheet["pendingChoices"]}

    assert leveled.status_code == 200
    assert sheet["characterClass"]["level"] == 3
    assert {"hitPointIncrease", "fighterSubclass"} <= choices.keys()

    hp = client.post('/api/rooms/level-choice-test/sheet/player-1/choices/hitPointIncrease?playerKey=dm', json={"values": ["fixed"]})
    archetype = client.post('/api/rooms/level-choice-test/sheet/player-1/choices/fighterSubclass?playerKey=dm', json={"values": ["champion"]})
    final_sheet = archetype.json()["sheet"]

    assert hp.json()["sheet"]["hp"]["max"] == 20
    assert archetype.json()["sheet"]["classes"][0]["subclass"] == "champion"
    assert "fighterSubclass" not in {choice["id"] for choice in final_sheet["pendingChoices"]}


def test_level_down_prunes_unavailable_fighter_choices_and_hp(tmp_path, monkeypatch) -> None:
    write_party_campaign(
        tmp_path,
        "level-down-test",
        PartyMemberConfig(
            id="player-1",
            name="Level Fighter",
            maxHp=29,
            abilityScores=AbilityScores(strength=16, dexterity=14, constitution=15, intelligence=10, wisdom=12, charisma=8),
            sheet=PartyMemberSheet(
                classes=[
                    CharacterClassLevel(
                        name=ClassType.FIGHTER,
                        level=3,
                        subclass=FighterSubclassType.CHAMPION,
                        fightingStyles=[FightingStyleType.DEFENSE],
                    )
                ],
                hitPointIncreases=[8, 9],
            ),
        ),
    )
    monkeypatch.setattr(server, "CAMPAIGN_DIR", tmp_path)
    client = TestClient(server.app)

    response = client.post("/api/rooms/level-down-test/sheet/player-1/level?playerKey=dm&delta=-1")
    sheet = response.json()["sheet"]

    assert response.status_code == 200
    assert sheet["characterClass"]["level"] == 2
    assert "subclass" not in sheet["classes"][0]
    assert sheet["hp"]["max"] == 20


def test_level_down_prunes_fighter_ability_score_improvements(tmp_path, monkeypatch) -> None:
    write_party_campaign(
        tmp_path,
        "asi-level-down-test",
        PartyMemberConfig(
            id="player-1",
            name="Level Fighter",
            maxHp=36,
            abilityScores=AbilityScores(strength=18, dexterity=14, constitution=15, intelligence=10, wisdom=12, charisma=8),
            sheet=PartyMemberSheet(
                classes=[CharacterClassLevel(name=ClassType.FIGHTER, level=4)],
                abilityScoreImprovements=["strength:2"],
            ),
        ),
    )
    monkeypatch.setattr(server, "CAMPAIGN_DIR", tmp_path)
    client = TestClient(server.app)

    response = client.post("/api/rooms/asi-level-down-test/sheet/player-1/level?playerKey=dm&delta=-1")
    sheet = response.json()["sheet"]

    assert response.status_code == 200
    assert sheet["characterClass"]["level"] == 3
    assert sheet["abilityScores"]["strength"] == 16


def test_level_down_prunes_fighter_feat_improvements(tmp_path, monkeypatch) -> None:
    write_party_campaign(
        tmp_path,
        "feat-level-down-test",
        PartyMemberConfig(
            id="player-1",
            name="Level Fighter",
            maxHp=36,
            abilityScores=AbilityScores(strength=16, dexterity=14, constitution=15, intelligence=10, wisdom=12, charisma=8),
            sheet=PartyMemberSheet(
                classes=[CharacterClassLevel(name=ClassType.FIGHTER, level=4)],
                abilityScoreImprovements=["feat:actor"],
                feats=[general_feat_feature("actor")],
            ),
        ),
    )
    monkeypatch.setattr(server, "CAMPAIGN_DIR", tmp_path)
    client = TestClient(server.app)

    response = client.post("/api/rooms/feat-level-down-test/sheet/player-1/level?playerKey=dm&delta=-1")
    sheet = response.json()["sheet"]

    assert response.status_code == 200
    assert sheet["characterClass"]["level"] == 3
    assert "actor" not in {feature["id"] for feature in sheet["features"]}


def test_player_can_choose_eldritch_knight_spells(tmp_path, monkeypatch) -> None:
    write_party_campaign(
        tmp_path,
        "eldritch-spell-choice-test",
        PartyMemberConfig(
            id="player-1",
            name="Spell Fighter",
            maxHp=28,
            abilityScores=AbilityScores(strength=16, dexterity=14, constitution=15, intelligence=14, wisdom=12, charisma=8),
            sheet=PartyMemberSheet(
                classes=[CharacterClassLevel(name=ClassType.FIGHTER, level=3, subclass=FighterSubclassType.ELDRITCH_KNIGHT, fightingStyles=[FightingStyleType.DEFENSE])],
                hitPointIncreases=[8, 8],
            ),
        ),
    )
    monkeypatch.setattr(server, "CAMPAIGN_DIR", tmp_path)
    client = TestClient(server.app)

    response = client.post(
        '/api/rooms/eldritch-spell-choice-test/sheet/player-1/choices/eldritchKnightSpells?playerKey=player-1',
        json={"values": ["fireBolt", "mageHand", "shield", "magicMissile", "findFamiliar"]},
    )
    sheet = response.json()["sheet"]
    spells = {spell["id"]: spell for spell in sheet["spells"]}

    assert response.status_code == 200
    assert spells["fireBolt"]["level"] == 0
    assert spells["shield"]["castingAbility"] == "intelligence"
    assert spells["findFamiliar"]["school"] == "conjuration"
    assert "eldritchKnightSpells" not in {choice["id"] for choice in sheet["pendingChoices"]}


def test_player_can_choose_arcane_trickster_spells(tmp_path, monkeypatch) -> None:
    write_party_campaign(
        tmp_path,
        "arcane-trickster-spell-choice-test",
        PartyMemberConfig(
            id="player-1",
            name="Spell Rogue",
            maxHp=24,
            abilityScores=AbilityScores(strength=10, dexterity=16, constitution=14, intelligence=14, wisdom=12, charisma=8),
            sheet=PartyMemberSheet(
                classes=[CharacterClassLevel(name=ClassType.ROGUE, level=3, subclass=RogueSubclassType.ARCANE_TRICKSTER)],
                hitPointIncreases=[7, 7],
            ),
        ),
    )
    monkeypatch.setattr(server, "CAMPAIGN_DIR", tmp_path)
    client = TestClient(server.app)

    response = client.post(
        '/api/rooms/arcane-trickster-spell-choice-test/sheet/player-1/choices/arcaneTricksterSpells?playerKey=player-1',
        json={"values": ["fireBolt", "mageHand", "mindSliver", "shield", "magicMissile", "charmPerson"]},
    )
    sheet = response.json()["sheet"]
    spells = {spell["id"]: spell for spell in sheet["spells"]}

    assert response.status_code == 200
    assert spells["mageHand"]["level"] == 0
    assert spells["shield"]["castingAbility"] == "intelligence"
    assert spells["charmPerson"]["source"] == "arcaneTrickster"
    assert "arcaneTricksterSpells" not in {choice["id"] for choice in sheet["pendingChoices"]}


def test_rogue_levels_into_soulknife_and_uses_homing_strikes(tmp_path, monkeypatch) -> None:
    write_party_campaign(
        tmp_path,
        "soulknife-journey-test",
        PartyMemberConfig(
            id="player-1",
            name="Journey Rogue",
            maxHp=10,
            abilityScores=AbilityScores(strength=10, dexterity=16, constitution=14, intelligence=12, wisdom=12, charisma=10),
            sheet=PartyMemberSheet(
                classes=[CharacterClassLevel(name=ClassType.ROGUE, level=1)],
                skills={
                    enum_key(SkillType.SLEIGHT_OF_HAND): ProficiencyLevel.EXPERTISE,
                    enum_key(SkillType.STEALTH): ProficiencyLevel.EXPERTISE,
                    enum_key(SkillType.PERCEPTION): ProficiencyLevel.PROFICIENT,
                    enum_key(SkillType.INVESTIGATION): ProficiencyLevel.PROFICIENT,
                },
            ),
        ),
    )
    monkeypatch.setattr(server, "CAMPAIGN_DIR", tmp_path)
    monkeypatch.setattr(server.random, "randint", lambda minimum, maximum: 4)
    client = TestClient(server.app)

    sheet = None
    for _ in range(8):
        leveled = client.post("/api/rooms/soulknife-journey-test/sheet/player-1/level?playerKey=dm&delta=1&className=rogue")
        assert leveled.status_code == 200
        sheet = resolve_rogue_level_choices(client, "soulknife-journey-test")

    assert sheet is not None
    assert sheet["characterClass"]["name"] == "rogue"
    assert sheet["characterClass"]["level"] == 9
    assert sheet["abilityScores"]["dexterity"] == 20
    assert "rogueAbilityScoreImprovement" not in {choice["id"] for choice in sheet["pendingChoices"]}
    resources = {resource["id"]: resource for resource in sheet["resources"]}
    abilities = {ability["id"]: ability for ability in sheet["abilities"]}
    attacks = {attack["id"]: attack for attack in sheet["attacks"]}
    assert resources["psionicEnergyDice"]["maxUses"] == 8
    assert abilities[enum_key(RogueSubclassAbilityType.HOMING_STRIKES)]["resourceId"] == "psionicEnergyDice"
    assert attacks[enum_key(RogueSubclassAttackType.PSYCHIC_BLADE)]["id"] == enum_key(RogueSubclassAttackType.PSYCHIC_BLADE)
    assert attacks[enum_key(RogueSubclassAttackType.PSYCHIC_BLADE)]["damageType"] == "psychic"

    roll = client.post(
        f"/api/rooms/soulknife-journey-test/sheet/player-1/abilities/{enum_key(RogueSubclassAbilityType.HOMING_STRIKES)}/rolls/{enum_key(RogueSubclassRollActionType.HOMING_STRIKES)}?playerKey=player-1"
    )
    updated_sheet = client.get("/api/rooms/soulknife-journey-test/sheet/player-1?playerKey=player-1").json()["sheet"]
    psionic_energy = next(resource for resource in updated_sheet["resources"] if resource["id"] == "psionicEnergyDice")

    assert roll.status_code == 200
    assert roll.json()["roll"]["label"] == "Homing Strikes"
    assert roll.json()["roll"]["die"] == "1d8"
    assert roll.json()["roll"]["dice"] == [4]
    assert roll.json()["roll"]["resourceSpent"] == {
        "resourceId": "psionicEnergyDice",
        "resourceName": "Psionic Energy Dice",
        "remainingUses": 7,
        "maxUses": 8,
    }
    assert psionic_energy["currentUses"] == 7


def test_eldritch_knight_spell_choice_rejects_wrong_counts(tmp_path, monkeypatch) -> None:
    write_party_campaign(
        tmp_path,
        "eldritch-spell-count-test",
        PartyMemberConfig(
            id="player-1",
            name="Spell Fighter",
            maxHp=28,
            abilityScores=AbilityScores(strength=16, dexterity=14, constitution=15, intelligence=14, wisdom=12, charisma=8),
            sheet=PartyMemberSheet(
                classes=[CharacterClassLevel(name=ClassType.FIGHTER, level=3, subclass=FighterSubclassType.ELDRITCH_KNIGHT, fightingStyles=[FightingStyleType.DEFENSE])],
                hitPointIncreases=[8, 8],
            ),
        ),
    )
    monkeypatch.setattr(server, "CAMPAIGN_DIR", tmp_path)
    client = TestClient(server.app)

    response = client.post(
        '/api/rooms/eldritch-spell-count-test/sheet/player-1/choices/eldritchKnightSpells?playerKey=player-1',
        json={"values": ["fireBolt", "mageHand", "minorIllusion", "shield", "magicMissile"]},
    )

    assert response.status_code == 400


def test_eldritch_knight_spell_choice_rejects_too_many_flexible_spells(tmp_path, monkeypatch) -> None:
    write_party_campaign(
        tmp_path,
        "eldritch-spell-school-test",
        PartyMemberConfig(
            id="player-1",
            name="Spell Fighter",
            maxHp=28,
            abilityScores=AbilityScores(strength=16, dexterity=14, constitution=15, intelligence=14, wisdom=12, charisma=8),
            sheet=PartyMemberSheet(
                classes=[CharacterClassLevel(name=ClassType.FIGHTER, level=3, subclass=FighterSubclassType.ELDRITCH_KNIGHT, fightingStyles=[FightingStyleType.DEFENSE])],
                hitPointIncreases=[8, 8],
            ),
        ),
    )
    monkeypatch.setattr(server, "CAMPAIGN_DIR", tmp_path)
    client = TestClient(server.app)

    response = client.post(
        '/api/rooms/eldritch-spell-school-test/sheet/player-1/choices/eldritchKnightSpells?playerKey=player-1',
        json={"values": ["fireBolt", "mageHand", "shield", "findFamiliar", "sleep"]},
    )

    assert response.status_code == 400


def test_level_down_prunes_eldritch_knight_spells(tmp_path, monkeypatch) -> None:
    from dnd_board.rules.classes.fighter.archetypes import eldritch_knight_catalog_spell

    write_party_campaign(
        tmp_path,
        "eldritch-spell-level-down-test",
        PartyMemberConfig(
            id="player-1",
            name="Spell Fighter",
            maxHp=58,
            abilityScores=AbilityScores(strength=16, dexterity=14, constitution=15, intelligence=14, wisdom=12, charisma=8),
            sheet=PartyMemberSheet(
                classes=[CharacterClassLevel(name=ClassType.FIGHTER, level=7, subclass=FighterSubclassType.ELDRITCH_KNIGHT, fightingStyles=[FightingStyleType.DEFENSE])],
                hitPointIncreases=[8, 8, 8, 8, 8, 8],
                abilityScoreImprovements=["strength:2"],
                spells=[
                    eldritch_knight_catalog_spell("fireBolt"),
                    eldritch_knight_catalog_spell("mageHand"),
                    eldritch_knight_catalog_spell("shield"),
                    eldritch_knight_catalog_spell("magicMissile"),
                    eldritch_knight_catalog_spell("thunderwave"),
                    eldritch_knight_catalog_spell("absorbElements"),
                    eldritch_knight_catalog_spell("shatter"),
                ],
            ),
        ),
    )
    monkeypatch.setattr(server, "CAMPAIGN_DIR", tmp_path)
    client = TestClient(server.app)

    response = client.post("/api/rooms/eldritch-spell-level-down-test/sheet/player-1/level?playerKey=dm&delta=-1")
    sheet = response.json()["sheet"]
    spell_ids = {spell["id"] for spell in sheet["spells"]}

    assert response.status_code == 200
    assert sheet["characterClass"]["level"] == 6
    assert len(sheet["spells"]) == 6
    assert "shatter" not in spell_ids


def test_only_dm_can_rest_sheet_resources() -> None:
    client = TestClient(server.app)

    response = client.post("/api/rooms/rest-permission-test/sheet/rest?playerKey=player-1&rest=short")

    assert response.status_code == 403


def test_rest_sheet_resources_rejects_invalid_rest_type() -> None:
    client = TestClient(server.app)

    response = client.post("/api/rooms/rest-invalid-test/sheet/rest?playerKey=dm&rest=nap")

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid rest type"


def test_short_rest_resets_only_short_rest_resources(tmp_path, monkeypatch) -> None:
    campaign = tmp_path / "short-rest-test"
    party = campaign / "party"
    party.mkdir(parents=True)
    (campaign / "campaign.json").write_text('{"id":"short-rest-test","name":"Short Rest Test"}', encoding="utf-8")
    (party / "party.json").write_text(
        json.dumps(
            typed_json_from_value(
                PartyManifest(
                    members=[
                        PartyMemberConfig(
                            id="player-1",
                            name="Rest Fighter",
                            maxHp=31,
                            sheet=PartyMemberSheet(classes=[CharacterClassLevel(name=ClassType.FIGHTER, level=9)]),
                        ),
                        PartyMemberConfig(
                            id="player-2",
                            name="Second Rest Fighter",
                            maxHp=31,
                            sheet=PartyMemberSheet(classes=[CharacterClassLevel(name=ClassType.FIGHTER, level=9)]),
                        ),
                    ]
                )
            )
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(server, "CAMPAIGN_DIR", tmp_path)
    client = TestClient(server.app)
    room = server.get_or_create_room("short-rest-test")
    for token_id in ("player-1", "player-2"):
        sheet = server.token_to_sheet(room.tokens[token_id], room.id)
        room.resource_uses[sheet.tokenId] = {resource.id: 0 for resource in sheet.resources}
        room.temporary_hit_points[sheet.tokenId] = 7

    response = client.post("/api/rooms/short-rest-test/sheet/rest?playerKey=dm&rest=short")
    sheets = {sheet["id"]: sheet for sheet in response.json()["sheets"]}
    resources = {resource["id"]: resource for resource in sheets["player-1"]["resources"]}
    second_resources = {resource["id"]: resource for resource in sheets["player-2"]["resources"]}

    assert response.status_code == 200
    assert resources["secondWind"]["currentUses"] == resources["secondWind"]["maxUses"]
    assert resources["actionSurge"]["currentUses"] == resources["actionSurge"]["maxUses"]
    assert resources["indomitable"]["currentUses"] == 0
    assert sheets["player-1"]["hp"]["temporary"] == 7
    assert second_resources["secondWind"]["currentUses"] == second_resources["secondWind"]["maxUses"]
    assert second_resources["actionSurge"]["currentUses"] == second_resources["actionSurge"]["maxUses"]
    assert second_resources["indomitable"]["currentUses"] == 0
    assert sheets["player-2"]["hp"]["temporary"] == 7


def test_long_rest_resets_short_and_long_rest_resources(tmp_path, monkeypatch) -> None:
    campaign = tmp_path / "long-rest-test"
    party = campaign / "party"
    party.mkdir(parents=True)
    (campaign / "campaign.json").write_text('{"id":"long-rest-test","name":"Long Rest Test"}', encoding="utf-8")
    (party / "party.json").write_text(
        json.dumps(
            typed_json_from_value(
                PartyManifest(
                    members=[
                        PartyMemberConfig(
                            id="player-1",
                            name="Rest Fighter",
                            maxHp=31,
                            sheet=PartyMemberSheet(classes=[CharacterClassLevel(name=ClassType.FIGHTER, level=9)]),
                        )
                    ]
                )
            )
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(server, "CAMPAIGN_DIR", tmp_path)
    client = TestClient(server.app)
    room = server.get_or_create_room("long-rest-test")
    sheet = server.token_to_sheet(room.tokens["player-1"], room.id)
    room.resource_uses[sheet.tokenId] = {resource.id: 0 for resource in sheet.resources}
    room.temporary_hit_points[sheet.tokenId] = 9

    response = client.post("/api/rooms/long-rest-test/sheet/rest?playerKey=dm&rest=long")
    rested_sheet = response.json()["sheets"][0]
    resources = {resource["id"]: resource for resource in rested_sheet["resources"]}

    assert response.status_code == 200
    assert all(resource["currentUses"] == resource["maxUses"] for resource in resources.values())
    assert rested_sheet["hp"]["temporary"] == 0


def test_rest_clears_only_conditions_with_matching_durations(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(server, "CAMPAIGN_DIR", tmp_path)
    client = TestClient(server.app)
    room = server.get_or_create_room("condition-rest-test")
    room.condition_overrides["player-1"] = [ConditionType.BLINDED, ConditionType.FRIGHTENED, ConditionType.PRONE]
    room.condition_durations["player-1"] = {
        ConditionType.BLINDED: ConditionDuration.UNTIL_SHORT_REST,
        ConditionType.FRIGHTENED: ConditionDuration.UNTIL_LONG_REST,
        ConditionType.PRONE: ConditionDuration.MANUAL,
    }

    short_rest = client.post("/api/rooms/condition-rest-test/sheet/rest?playerKey=dm&rest=short")
    after_short = client.get("/api/rooms/condition-rest-test/sheet/player-1?playerKey=player-1").json()["sheet"]
    long_rest = client.post("/api/rooms/condition-rest-test/sheet/rest?playerKey=dm&rest=long")
    after_long = client.get("/api/rooms/condition-rest-test/sheet/player-1?playerKey=player-1").json()["sheet"]

    assert short_rest.status_code == 200
    assert after_short["conditions"] == ["frightened", "prone"]
    assert long_rest.status_code == 200
    assert after_long["conditions"] == ["prone"]


def test_sheet_roll_queue_keeps_one_pending_roll_per_source_and_resolves(monkeypatch) -> None:
    client = TestClient(server.app)
    monkeypatch.setattr(server.random, "randint", lambda minimum, maximum: 10)
    room = server.get_or_create_room("sheet-roll-queue-test")
    dm_socket = FakeSocket()
    room.players["connection-1"] = server.Player(id="connection-1", name="DM", player_key="dm", websocket=dm_socket, room_id=room.id)

    attack = client.post("/api/rooms/sheet-roll-queue-test/sheet/player-1/rolls/attack?playerKey=player-1")
    damage = client.post("/api/rooms/sheet-roll-queue-test/sheet/player-1/rolls/damage?playerKey=player-1")
    pending = client.get("/api/rooms/sheet-roll-queue-test/sheet?playerKey=dm").json()["pendingRolls"]
    resolution = client.post(
        f"/api/rooms/sheet-roll-queue-test/rolls/{damage.json()['roll']['id']}/resolve?playerKey=dm&targetSheetId=player-2"
    )

    assert attack.status_code == 200
    assert damage.status_code == 200
    assert damage.json()["roll"]["resolution"] == "applyDamage"
    assert damage.json()["roll"]["label"] == "Damage Roll"
    assert "iconUrl" not in damage.json()["roll"]
    assert {roll["id"] for roll in pending} == {attack.json()["roll"]["id"], damage.json()["roll"]["id"]}
    assert resolution.status_code == 200
    assert resolution.json()["resolution"]["roll"]["id"] == damage.json()["roll"]["id"]
    assert [roll["id"] for roll in client.get("/api/rooms/sheet-roll-queue-test/sheet?playerKey=dm").json()["pendingRolls"]] == [attack.json()["roll"]["id"]]
    assert dm_socket.messages[-1]["type"] == "roll_resolved"


def test_player_can_clear_owned_sheet_pending_rolls(monkeypatch) -> None:
    client = TestClient(server.app)
    monkeypatch.setattr(server.random, "randint", lambda minimum, maximum: 10)

    player_roll = client.post("/api/rooms/sheet-clear-rolls-test/sheet/player-1/rolls/ability-check?playerKey=player-1&ability=strength")
    other_roll = client.post("/api/rooms/sheet-clear-rolls-test/sheet/player-2/rolls/ability-check?playerKey=player-2&ability=dexterity")
    denied = client.post("/api/rooms/sheet-clear-rolls-test/sheet/player-2/rolls/clear?playerKey=player-1")
    cleared = client.post("/api/rooms/sheet-clear-rolls-test/sheet/player-1/rolls/clear?playerKey=player-1")
    pending = client.get("/api/rooms/sheet-clear-rolls-test/sheet?playerKey=dm").json()["pendingRolls"]

    assert player_roll.status_code == 200
    assert other_roll.status_code == 200
    assert denied.status_code == 403
    assert cleared.status_code == 200
    assert [roll["tokenId"] for roll in pending] == ["player-2"]


def test_sheet_roll_history_keeps_duplicate_rolls_and_caps_at_ten(monkeypatch) -> None:
    client = TestClient(server.app)
    monkeypatch.setattr(server.random, "randint", lambda minimum, maximum: 10)

    first_roll_ids = []
    for _ in range(11):
        response = client.post("/api/rooms/sheet-roll-history-test/sheet/player-1/rolls/attack?playerKey=player-1")
        assert response.status_code == 200
        first_roll_ids.append(response.json()["roll"]["id"])

    sheet_state = client.get("/api/rooms/sheet-roll-history-test/sheet?playerKey=dm").json()
    pending = sheet_state["pendingRolls"]
    history = sheet_state["rollHistory"]

    assert len(pending) == 1
    assert pending[0]["id"] == first_roll_ids[-1]
    assert len(history) == 10
    assert [entry["roll"]["id"] for entry in history] == first_roll_ids[1:]
    assert all(entry["entryType"] == "rollCreated" for entry in history)


def test_sheet_roll_history_logs_resolution_after_roll_creation(monkeypatch) -> None:
    client = TestClient(server.app)
    monkeypatch.setattr(server.random, "randint", lambda minimum, maximum: 10)

    damage = client.post("/api/rooms/sheet-roll-resolution-history-test/sheet/player-1/rolls/damage?playerKey=player-1")
    resolution = client.post(
        f"/api/rooms/sheet-roll-resolution-history-test/rolls/{damage.json()['roll']['id']}/resolve?playerKey=dm&targetSheetId=player-2"
    )
    history = client.get("/api/rooms/sheet-roll-resolution-history-test/sheet?playerKey=dm").json()["rollHistory"]

    assert resolution.status_code == 200
    assert [entry["entryType"] for entry in history] == ["rollCreated", "rollResolved"]
    assert history[-1]["resolution"]["id"] == resolution.json()["resolution"]["id"]


def test_tactical_mind_roll_consumes_second_wind_and_has_own_pending_slot(tmp_path, monkeypatch) -> None:
    write_party_campaign(
        tmp_path,
        "tactical-mind-roll-test",
        PartyMemberConfig(
            id="player-1",
            name="Tactical Fighter",
            maxHp=36,
            abilityScores=AbilityScores(strength=16, dexterity=14, constitution=15, intelligence=10, wisdom=12, charisma=8),
            sheet=PartyMemberSheet(classes=[CharacterClassLevel(name=ClassType.FIGHTER, level=4)]),
        ),
    )
    monkeypatch.setattr(server, "CAMPAIGN_DIR", tmp_path)
    client = TestClient(server.app)
    monkeypatch.setattr(server.random, "randint", lambda minimum, maximum: 7)

    attack = client.post("/api/rooms/tactical-mind-roll-test/sheet/player-1/rolls/attack?playerKey=player-1")
    tactical_mind = client.post("/api/rooms/tactical-mind-roll-test/sheet/player-1/abilities/tacticalMind/rolls/tacticalMind?playerKey=player-1")
    sheet = client.get("/api/rooms/tactical-mind-roll-test/sheet/player-1?playerKey=player-1").json()["sheet"]
    pending = client.get("/api/rooms/tactical-mind-roll-test/sheet?playerKey=dm").json()["pendingRolls"]
    second_wind = next(resource for resource in sheet["resources"] if resource["id"] == "secondWind")

    assert attack.status_code == 200
    assert tactical_mind.status_code == 200
    roll = tactical_mind.json()["roll"]
    assert roll["label"] == "Tactical Mind"
    assert roll["sourceLabel"] == "Fighter"
    assert roll["resolution"] == "none"
    assert roll["die"] == "1d10"
    assert roll["diceType"] == "d10"
    assert roll["dice"] == [7]
    assert roll["resourceSpent"] == {
        "resourceId": "secondWind",
        "resourceName": "Second Wind",
        "remainingUses": 2,
        "maxUses": 3,
    }
    assert second_wind["currentUses"] == 2
    assert {pending_roll["id"] for pending_roll in pending} == {attack.json()["roll"]["id"], roll["id"]}


def test_fighter_sheet_exposes_tactical_mind_roll_action(tmp_path, monkeypatch) -> None:
    write_party_campaign(
        tmp_path,
        "tactical-mind-action-test",
        PartyMemberConfig(
            id="player-1",
            name="Tactical Fighter",
            maxHp=28,
            abilityScores=AbilityScores(strength=16, dexterity=14, constitution=15, intelligence=10, wisdom=12, charisma=8),
            sheet=PartyMemberSheet(
                classes=[CharacterClassLevel(name=ClassType.FIGHTER, level=2, fightingStyles=[FightingStyleType.DEFENSE])],
                hitPointIncreases=[8],
            ),
        ),
    )
    monkeypatch.setattr(server, "CAMPAIGN_DIR", tmp_path)
    client = TestClient(server.app)

    sheet = client.get("/api/rooms/tactical-mind-action-test/sheet/player-1?playerKey=player-1").json()["sheet"]
    tactical_mind = next(ability for ability in sheet["abilities"] if ability["id"] == "tacticalMind")

    assert tactical_mind["resourceId"] == "secondWind"
    assert any(action["id"] == "tacticalMind" and action["nameLabel"] == "Tactical Mind" for action in tactical_mind["rollActions"])


def test_superior_technique_roll_consumes_superiority_die(tmp_path, monkeypatch) -> None:
    campaign = tmp_path / "superior-technique-roll-test"
    party = campaign / "party"
    party.mkdir(parents=True)
    (campaign / "campaign.json").write_text('{"id":"superior-technique-roll-test","name":"Superior Technique Test"}', encoding="utf-8")
    (party / "party.json").write_text(
        json.dumps(
            typed_json_from_value(
                PartyManifest(
                    members=[
                        PartyMemberConfig(
                            id="player-1",
                            name="Superior Technique Fighter",
                            maxHp=31,
                            abilityScores=AbilityScores(strength=16, dexterity=14, constitution=15, intelligence=10, wisdom=12, charisma=8),
                            sheet=PartyMemberSheet(
                                classes=[
                                    CharacterClassLevel(
                                        name=ClassType.FIGHTER,
                                        level=7,
                                        fightingStyle=FightingStyleType.SUPERIOR_TECHNIQUE,
                                    )
                                ]
                            ),
                        )
                    ]
                )
            )
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(server, "CAMPAIGN_DIR", tmp_path)
    client = TestClient(server.app)
    monkeypatch.setattr(server.random, "randint", lambda minimum, maximum: 5)

    response = client.post("/api/rooms/superior-technique-roll-test/sheet/player-1/abilities/ambush/rolls/ambush?playerKey=player-1")
    sheet = client.get("/api/rooms/superior-technique-roll-test/sheet/player-1?playerKey=player-1").json()["sheet"]
    superiority_die = next(resource for resource in sheet["resources"] if resource["id"] == "superiorityDice")

    assert response.status_code == 200
    roll = response.json()["roll"]
    assert roll["label"] == "Ambush"
    assert roll["sourceLabel"] == "Battle Master"
    assert roll["die"] == "1d6"
    assert roll["diceType"] == "d6"
    assert roll["dice"] == [5]
    assert roll["resourceSpent"] == {
        "resourceId": "superiorityDice",
        "resourceName": "Superiority Dice",
        "remainingUses": 0,
        "maxUses": 1,
    }
    assert superiority_die["currentUses"] == 0


def test_cavalier_warding_maneuver_roll_consumes_resource(tmp_path, monkeypatch) -> None:
    campaign = tmp_path / "cavalier-campaign"
    party = campaign / "party"
    party.mkdir(parents=True)
    (campaign / "campaign.json").write_text('{"id":"cavalier-campaign","name":"Cavalier Campaign"}', encoding="utf-8")
    (party / "party.json").write_text(
        json.dumps(
            typed_json_from_value(
                PartyManifest(
                    members=[
                        PartyMemberConfig(
                            id="player-1",
                            name="Cavalier",
                            maxHp=31,
                            abilityScores=AbilityScores(strength=16, dexterity=12, constitution=14, intelligence=10, wisdom=10, charisma=10),
                            sheet=PartyMemberSheet(classes=[CharacterClassLevel(name=ClassType.FIGHTER, level=7, subclass=FighterSubclassType.CAVALIER)]),
                        )
                    ]
                )
            )
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(server, "CAMPAIGN_DIR", tmp_path)
    monkeypatch.setattr(server.random, "randint", lambda minimum, maximum: 6)
    client = TestClient(server.app)

    response = client.post("/api/rooms/cavalier-campaign/sheet/player-1/abilities/wardingManeuver/rolls/wardingManeuver?playerKey=player-1")
    sheet = client.get("/api/rooms/cavalier-campaign/sheet/player-1?playerKey=player-1").json()["sheet"]
    warding_maneuver = next(resource for resource in sheet["resources"] if resource["id"] == "wardingManeuver")

    assert response.status_code == 200
    roll = response.json()["roll"]
    assert roll["label"] == "Warding Maneuver"
    assert roll["sourceLabel"] == "Cavalier"
    assert roll["die"] == "1d8"
    assert roll["dice"] == [6]
    assert roll["resourceSpent"]["remainingUses"] == 1
    assert warding_maneuver["currentUses"] == 1


def test_damage_roll_resolution_reduces_target_hp(monkeypatch) -> None:
    client = TestClient(server.app)
    monkeypatch.setattr(server.random, "randint", lambda minimum, maximum: 8)
    room = server.get_or_create_room("sheet-damage-hp-test")
    target_starting_hp = server.token_to_sheet(room.tokens["player-2"], room.id).hp.max

    damage = client.post("/api/rooms/sheet-damage-hp-test/sheet/player-1/rolls/damage?playerKey=player-1").json()["roll"]
    resolution = client.post(f"/api/rooms/sheet-damage-hp-test/rolls/{damage['id']}/resolve?playerKey=dm&targetSheetId=player-2")
    target_sheet = client.get("/api/rooms/sheet-damage-hp-test/sheet/player-2?playerKey=player-1").json()["sheet"]

    assert resolution.status_code == 200
    assert resolution.json()["resolution"]["targetHp"]["current"] == max(0, target_starting_hp - damage["total"])
    assert target_sheet["hp"]["current"] == max(0, target_starting_hp - damage["total"])


def test_damage_roll_resolution_consumes_temporary_hp_first(monkeypatch) -> None:
    client = TestClient(server.app)
    monkeypatch.setattr(server.random, "randint", lambda minimum, maximum: 6)
    room = server.get_or_create_room("sheet-temp-damage-test")
    room.temporary_hit_points["player-2"] = 4
    target_starting_hp = server.token_to_sheet(room.tokens["player-2"], room.id).hp.max

    damage = client.post("/api/rooms/sheet-temp-damage-test/sheet/player-1/rolls/damage?playerKey=player-1").json()["roll"]
    resolution = client.post(f"/api/rooms/sheet-temp-damage-test/rolls/{damage['id']}/resolve?playerKey=dm&targetSheetId=player-2")
    target_sheet = client.get("/api/rooms/sheet-temp-damage-test/sheet/player-2?playerKey=player-1").json()["sheet"]

    assert resolution.status_code == 200
    expected_current = target_starting_hp - max(0, damage["total"] - 4)
    assert resolution.json()["resolution"]["targetHp"] == {"current": expected_current, "max": target_starting_hp, "temporary": 0}
    assert target_sheet["hp"] == {"current": expected_current, "max": target_starting_hp, "temporary": 0}


def test_damage_roll_resolution_applies_resistance_vulnerability_and_immunity(tmp_path, monkeypatch) -> None:
    write_party_campaign(
        tmp_path,
        "damage-defense-test",
        PartyMemberConfig(
            id="player-1",
            name="Attacker",
            maxHp=20,
            abilityScores=AbilityScores(strength=10, dexterity=10, constitution=10, intelligence=10, wisdom=10, charisma=10),
            sheet=PartyMemberSheet(
                attacks=[
                    AttackAction(
                        id="acid",
                        name="Acid",
                        ability=AbilityType.STRENGTH,
                        damageDiceCount=1,
                        damageDiceType=DiceType.D10,
                        damageType=DamageType.ACID,
                    ),
                    AttackAction(
                        id="cold",
                        name="Cold",
                        ability=AbilityType.STRENGTH,
                        damageDiceCount=1,
                        damageDiceType=DiceType.D10,
                        damageType=DamageType.COLD,
                    ),
                    AttackAction(
                        id="fire",
                        name="Fire",
                        ability=AbilityType.STRENGTH,
                        damageDiceCount=1,
                        damageDiceType=DiceType.D10,
                        damageType=DamageType.FIRE,
                    ),
                ],
            ),
        ),
        PartyMemberConfig(
            id="player-2",
            name="Defender",
            maxHp=40,
            abilityScores=AbilityScores(strength=10, dexterity=10, constitution=10, intelligence=10, wisdom=10, charisma=10),
            sheet=PartyMemberSheet(
                damageResistances=[DamageType.ACID],
                damageVulnerabilities=[DamageType.COLD],
                damageImmunities=[DamageType.FIRE],
            ),
        ),
    )
    monkeypatch.setattr(server, "CAMPAIGN_DIR", tmp_path)
    monkeypatch.setattr(server.random, "randint", lambda minimum, maximum: 9)
    client = TestClient(server.app)

    acid_roll = client.post("/api/rooms/damage-defense-test/sheet/player-1/rolls/damage?playerKey=player-1&attackId=acid").json()["roll"]
    acid_resolution = client.post(f"/api/rooms/damage-defense-test/rolls/{acid_roll['id']}/resolve?playerKey=dm&targetSheetId=player-2")
    cold_roll = client.post("/api/rooms/damage-defense-test/sheet/player-1/rolls/damage?playerKey=player-1&attackId=cold").json()["roll"]
    cold_resolution = client.post(f"/api/rooms/damage-defense-test/rolls/{cold_roll['id']}/resolve?playerKey=dm&targetSheetId=player-2")
    fire_roll = client.post("/api/rooms/damage-defense-test/sheet/player-1/rolls/damage?playerKey=player-1&attackId=fire").json()["roll"]
    fire_resolution = client.post(f"/api/rooms/damage-defense-test/rolls/{fire_roll['id']}/resolve?playerKey=dm&targetSheetId=player-2")
    defender = client.get("/api/rooms/damage-defense-test/sheet/player-2?playerKey=player-2").json()["sheet"]

    assert acid_resolution.status_code == 200
    assert acid_resolution.json()["resolution"]["targetHp"]["current"] == 36
    assert "Acid resistance" in acid_resolution.json()["resolution"]["outcome"]
    assert cold_resolution.status_code == 200
    assert cold_resolution.json()["resolution"]["targetHp"]["current"] == 18
    assert "Cold vulnerability" in cold_resolution.json()["resolution"]["outcome"]
    assert fire_resolution.status_code == 200
    assert fire_resolution.json()["resolution"]["targetHp"]["current"] == 18
    assert "Fire immunity" in fire_resolution.json()["resolution"]["outcome"]
    assert defender["hp"]["current"] == 18
    assert defender["damageResistances"] == ["acid"]
    assert defender["damageVulnerabilities"] == ["cold"]
    assert defender["damageImmunities"] == ["fire"]


def test_damage_resistance_reduces_temporary_hp_loss(tmp_path, monkeypatch) -> None:
    write_party_campaign(
        tmp_path,
        "damage-defense-temp-test",
        PartyMemberConfig(
            id="player-1",
            name="Attacker",
            maxHp=20,
            abilityScores=AbilityScores(strength=10, dexterity=10, constitution=10, intelligence=10, wisdom=10, charisma=10),
            sheet=PartyMemberSheet(
                attacks=[
                    AttackAction(
                        id="acid",
                        name="Acid",
                        ability=AbilityType.STRENGTH,
                        damageDiceCount=1,
                        damageDiceType=DiceType.D10,
                        damageType=DamageType.ACID,
                    )
                ],
            ),
        ),
        PartyMemberConfig(
            id="player-2",
            name="Defender",
            maxHp=40,
            abilityScores=AbilityScores(strength=10, dexterity=10, constitution=10, intelligence=10, wisdom=10, charisma=10),
            sheet=PartyMemberSheet(damageResistances=[DamageType.ACID]),
        ),
    )
    monkeypatch.setattr(server, "CAMPAIGN_DIR", tmp_path)
    monkeypatch.setattr(server.random, "randint", lambda minimum, maximum: 9)
    client = TestClient(server.app)
    room = server.get_or_create_room("damage-defense-temp-test")
    room.temporary_hit_points["player-2"] = 6

    roll = client.post("/api/rooms/damage-defense-temp-test/sheet/player-1/rolls/damage?playerKey=player-1&attackId=acid").json()["roll"]
    response = client.post(f"/api/rooms/damage-defense-temp-test/rolls/{roll['id']}/resolve?playerKey=dm&targetSheetId=player-2")

    assert response.status_code == 200
    assert response.json()["resolution"]["targetHp"] == {"current": 40, "max": 40, "temporary": 2}


def test_second_wind_roll_immediately_heals_source(monkeypatch) -> None:
    client = TestClient(server.app)
    monkeypatch.setattr(server.random, "randint", lambda minimum, maximum: 5)
    room = server.get_or_create_room("sheet-healing-test")
    room.hit_points["player-1"] = 10
    starting_sheet = server.token_to_sheet(room.tokens["player-1"], room.id)

    response = client.post("/api/rooms/sheet-healing-test/sheet/player-1/resources/secondWind/rolls/secondWindHeal?playerKey=player-1")
    healed_sheet = client.get("/api/rooms/sheet-healing-test/sheet/player-1?playerKey=player-1").json()["sheet"]
    pending = client.get("/api/rooms/sheet-healing-test/sheet?playerKey=dm").json()["pendingRolls"]

    assert response.status_code == 200
    roll = response.json()["roll"]
    assert roll["resolution"] == "healSelf"
    assert response.json()["resolution"]["targetSheetId"] == "player-1"
    assert response.json()["logEntry"]["entryType"] == "rollResolved"
    assert healed_sheet["hp"]["current"] == min(starting_sheet.hp.max, 10 + roll["total"])
    assert pending == []


def test_reclaim_potential_roll_resolution_adds_temporary_hp(tmp_path, monkeypatch) -> None:
    client = TestClient(server.app)
    monkeypatch.setattr(server, "CAMPAIGN_DIR", tmp_path)
    monkeypatch.setattr(server.random, "randint", lambda minimum, maximum: 4)
    write_party_campaign(
        tmp_path,
        "sheet-temporary-healing-test",
        PartyMemberConfig(
            id="player-1",
            name="Echo",
            maxHp=40,
            abilityScores=AbilityScores(strength=14, dexterity=14, constitution=16, intelligence=10, wisdom=10, charisma=10),
            sheet=PartyMemberSheet(
                classes=[CharacterClassLevel(name=ClassType.FIGHTER, level=15, subclass=FighterSubclassType.ECHO_KNIGHT)]
            ),
        ),
    )

    roll = client.post("/api/rooms/sheet-temporary-healing-test/sheet/player-1/resources/reclaimPotential/rolls/reclaimPotential?playerKey=player-1").json()["roll"]
    resolution = client.post(f"/api/rooms/sheet-temporary-healing-test/rolls/{roll['id']}/resolve?playerKey=dm&targetSheetId=player-1")
    sheet = client.get("/api/rooms/sheet-temporary-healing-test/sheet/player-1?playerKey=player-1").json()["sheet"]

    assert resolution.status_code == 200
    assert roll["resolution"] == "applyTemporaryHitPoints"
    assert sheet["hp"] == {"current": 40, "max": 40, "temporary": 11}


def test_battle_master_rally_roll_resolution_adds_temporary_hp_to_ally(tmp_path, monkeypatch) -> None:
    client = TestClient(server.app)
    monkeypatch.setattr(server, "CAMPAIGN_DIR", tmp_path)
    monkeypatch.setattr(server.random, "randint", lambda minimum, maximum: 5)
    write_party_campaign(
        tmp_path,
        "sheet-rally-drop-test",
        PartyMemberConfig(
            id="player-1",
            name="Commander",
            maxHp=40,
            abilityScores=AbilityScores(strength=14, dexterity=10, constitution=12, intelligence=10, wisdom=10, charisma=16),
            sheet=PartyMemberSheet(
                classes=[
                    CharacterClassLevel(
                        name=ClassType.FIGHTER,
                        level=3,
                        subclass=FighterSubclassType.BATTLE_MASTER,
                        maneuvers=[BattleMasterManeuverType.RALLY],
                    )
                ],
            ),
        ),
        PartyMemberConfig(id="player-2", name="Ally", maxHp=22, abilityScores=AbilityScores(10, 10, 10, 10, 10, 10), sheet=PartyMemberSheet()),
    )

    roll = client.post("/api/rooms/sheet-rally-drop-test/sheet/player-1/resources/superiorityDice/rolls/rally?playerKey=player-1").json()["roll"]
    resolution = client.post(f"/api/rooms/sheet-rally-drop-test/rolls/{roll['id']}/resolve?playerKey=dm&targetSheetId=player-2")
    ally = client.get("/api/rooms/sheet-rally-drop-test/sheet/player-2?playerKey=player-2").json()["sheet"]

    assert resolution.status_code == 200
    assert roll["resolution"] == "applyTemporaryHitPoints"
    assert roll["total"] == 6
    assert roll["modifierBreakdown"] == [{"source": "Modifier", "value": 1, "description": ""}]
    assert ally["hp"] == {"current": 22, "max": 22, "temporary": 6}


def test_condition_roll_resolution_applies_condition_on_failed_save(tmp_path, monkeypatch) -> None:
    client = TestClient(server.app)
    monkeypatch.setattr(server, "CAMPAIGN_DIR", tmp_path)
    rolls = iter([4, 4, 1])
    monkeypatch.setattr(server.random, "randint", lambda minimum, maximum: next(rolls))
    write_party_campaign(
        tmp_path,
        "sheet-condition-drop-test",
        PartyMemberConfig(
            id="player-1",
            name="Archer",
            maxHp=40,
            abilityScores=AbilityScores(strength=10, dexterity=14, constitution=12, intelligence=18, wisdom=10, charisma=10),
            sheet=PartyMemberSheet(
                classes=[
                    CharacterClassLevel(
                        name=ClassType.FIGHTER,
                        level=3,
                        subclass=FighterSubclassType.ARCANE_ARCHER,
                        arcaneShots=[ArcaneShotType.SHADOW_ARROW],
                    )
                ]
            ),
        ),
        PartyMemberConfig(id="player-2", name="Target", maxHp=30, abilityScores=AbilityScores(10, 10, 10, 10, 8, 10), sheet=PartyMemberSheet()),
    )

    roll = client.post("/api/rooms/sheet-condition-drop-test/sheet/player-1/abilities/shadowArrow/rolls/shadowArrow?playerKey=player-1").json()["roll"]
    resolution = client.post(f"/api/rooms/sheet-condition-drop-test/rolls/{roll['id']}/resolve?playerKey=dm&targetSheetId=player-2")
    sheet = client.get("/api/rooms/sheet-condition-drop-test/sheet/player-2?playerKey=player-2").json()["sheet"]

    assert resolution.status_code == 200
    assert roll["conditionEffects"][0]["saveDc"] == 14
    assert resolution.json()["resolution"]["responseRolls"][0]["label"] == "Wisdom Save"
    assert resolution.json()["resolution"]["responseRolls"][0]["sourceLabel"] == "Shadow Arrow"
    assert resolution.json()["resolution"]["targetConditions"] == ["blinded"]
    assert sheet["conditions"] == ["blinded"]
    pending = client.get("/api/rooms/sheet-condition-drop-test/sheet?playerKey=dm").json()["pendingRolls"]
    assert any(response_roll["tokenId"] == "player-2" and response_roll["label"] == "Wisdom Save" for response_roll in pending)


def test_condition_roll_resolution_survives_sheet_poll_without_manifest(tmp_path, monkeypatch) -> None:
    client = TestClient(server.app)
    monkeypatch.setattr(server, "CAMPAIGN_DIR", tmp_path)
    monkeypatch.setattr(server.random, "randint", lambda minimum, maximum: 1)
    room = server.get_or_create_room("generated-condition-drop-test")
    roll = RollPayload(
        id="test-prone-roll",
        sheetId="player-1",
        tokenId="player-1",
        roller="player-1",
        source=RollSource(section=SheetSectionType.ABILITIES, sourceId="test-trip", actionId="test-trip"),
        sourceLabel="Test Trip",
        resolution=RollResolutionMode.NONE,
        label="Test Trip",
        iconUrl=None,
        dice=[1],
        diceType=DiceType.D6,
        die="1d6",
        modifier=0,
        modifierBreakdown=[],
        total=1,
        createdAt=1,
        conditionEffects=[
            ConditionEffect(
                condition=ConditionType.PRONE,
                mode=ConditionApplicationMode.TARGET_SAVE,
                savingThrow=AbilityType.STRENGTH,
                saveDc=30,
            )
        ],
    )
    room.pending_rolls[server.roll_queue_key(roll)] = roll

    resolution = client.post("/api/rooms/generated-condition-drop-test/rolls/test-prone-roll/resolve?playerKey=dm&targetSheetId=player-2")
    sheet = client.get("/api/rooms/generated-condition-drop-test/sheet/player-2?playerKey=player-2").json()["sheet"]

    assert resolution.status_code == 200
    assert resolution.json()["resolution"]["targetConditions"] == ["prone"]
    assert sheet["conditions"] == ["prone"]


def test_pushing_attack_triggers_visible_strength_save_without_condition(tmp_path, monkeypatch) -> None:
    client = TestClient(server.app)
    monkeypatch.setattr(server, "CAMPAIGN_DIR", tmp_path)
    rolls = iter([4, 1])
    monkeypatch.setattr(server.random, "randint", lambda minimum, maximum: next(rolls))
    write_party_campaign(
        tmp_path,
        "sheet-pushing-drop-test",
        PartyMemberConfig(
            id="player-1",
            name="Pusher",
            maxHp=40,
            abilityScores=AbilityScores(strength=18, dexterity=10, constitution=12, intelligence=10, wisdom=10, charisma=10),
            sheet=PartyMemberSheet(
                classes=[
                    CharacterClassLevel(
                        name=ClassType.FIGHTER,
                        level=3,
                        subclass=FighterSubclassType.BATTLE_MASTER,
                        maneuvers=[BattleMasterManeuverType.PUSHING_ATTACK],
                    )
                ],
            ),
        ),
        PartyMemberConfig(id="player-2", name="Target", maxHp=30, abilityScores=AbilityScores(8, 10, 10, 10, 10, 10), sheet=PartyMemberSheet()),
    )

    roll = client.post("/api/rooms/sheet-pushing-drop-test/sheet/player-1/resources/superiorityDice/rolls/pushingAttack?playerKey=player-1").json()["roll"]
    resolution = client.post(f"/api/rooms/sheet-pushing-drop-test/rolls/{roll['id']}/resolve?playerKey=dm&targetSheetId=player-2")
    pending = client.get("/api/rooms/sheet-pushing-drop-test/sheet?playerKey=dm").json()["pendingRolls"]

    assert resolution.status_code == 200
    assert roll["conditionEffects"][0]["savingThrow"] == "strength"
    assert "Target fails DC 14 Strength save" in resolution.json()["resolution"]["outcome"]
    assert resolution.json()["resolution"]["targetConditions"] == []
    assert resolution.json()["resolution"]["responseRolls"][0]["label"] == "Strength Save"
    assert resolution.json()["resolution"]["responseRolls"][0]["sourceLabel"] == "Pushing Attack"
    assert any(response_roll["tokenId"] == "player-2" and response_roll["label"] == "Strength Save" for response_roll in pending)


def test_grappling_strike_resolves_contested_check_and_applies_grappled(tmp_path, monkeypatch) -> None:
    client = TestClient(server.app)
    monkeypatch.setattr(server, "CAMPAIGN_DIR", tmp_path)
    rolls = iter([3, 10, 4])
    monkeypatch.setattr(server.random, "randint", lambda minimum, maximum: next(rolls))
    write_party_campaign(
        tmp_path,
        "sheet-grapple-drop-test",
        PartyMemberConfig(
            id="player-1",
            name="Grappler",
            maxHp=40,
            abilityScores=AbilityScores(strength=18, dexterity=10, constitution=12, intelligence=10, wisdom=10, charisma=10),
            sheet=PartyMemberSheet(
                skills={enum_key(SkillType.ATHLETICS): ProficiencyLevel.PROFICIENT},
                classes=[
                    CharacterClassLevel(
                        name=ClassType.FIGHTER,
                        level=3,
                        subclass=FighterSubclassType.BATTLE_MASTER,
                        maneuvers=[BattleMasterManeuverType.GRAPPLING_STRIKE],
                    )
                ],
            ),
        ),
        PartyMemberConfig(
            id="player-2",
            name="Escaper",
            maxHp=30,
            abilityScores=AbilityScores(strength=10, dexterity=16, constitution=10, intelligence=10, wisdom=10, charisma=10),
            sheet=PartyMemberSheet(skills={enum_key(SkillType.ACROBATICS): ProficiencyLevel.PROFICIENT}),
        ),
    )

    roll = client.post("/api/rooms/sheet-grapple-drop-test/sheet/player-1/resources/superiorityDice/rolls/grapplingStrike?playerKey=player-1").json()["roll"]
    resolution = client.post(f"/api/rooms/sheet-grapple-drop-test/rolls/{roll['id']}/resolve?playerKey=dm&targetSheetId=player-2")
    sheet = client.get("/api/rooms/sheet-grapple-drop-test/sheet/player-2?playerKey=player-2").json()["sheet"]

    assert resolution.status_code == 200
    assert roll["conditionEffects"][0]["mode"] == "sourceCheck"
    strength_athletics = f"{enum_label(AbilityType.STRENGTH)} ({enum_label(SkillType.ATHLETICS)})"
    dexterity_acrobatics = f"{enum_label(AbilityType.DEXTERITY)} ({enum_label(SkillType.ACROBATICS)})"
    assert {response_roll["label"] for response_roll in resolution.json()["resolution"]["responseRolls"]} == {
        strength_athletics,
        dexterity_acrobatics,
    }
    assert f"Grappler wins {strength_athletics}" in resolution.json()["resolution"]["outcome"]
    assert f"Escaper {dexterity_acrobatics}" in resolution.json()["resolution"]["outcome"]
    assert resolution.json()["resolution"]["targetConditions"] == ["grappled"]
    assert sheet["conditions"] == ["grappled"]


def test_grappling_strike_does_not_apply_grappled_when_target_wins_contest(tmp_path, monkeypatch) -> None:
    client = TestClient(server.app)
    monkeypatch.setattr(server, "CAMPAIGN_DIR", tmp_path)
    rolls = iter([1, 2, 18])
    monkeypatch.setattr(server.random, "randint", lambda minimum, maximum: next(rolls))
    write_party_campaign(
        tmp_path,
        "sheet-grapple-fail-drop-test",
        PartyMemberConfig(
            id="player-1",
            name="Grappler",
            maxHp=40,
            abilityScores=AbilityScores(strength=14, dexterity=10, constitution=12, intelligence=10, wisdom=10, charisma=10),
            sheet=PartyMemberSheet(
                classes=[
                    CharacterClassLevel(
                        name=ClassType.FIGHTER,
                        level=3,
                        subclass=FighterSubclassType.BATTLE_MASTER,
                        maneuvers=[BattleMasterManeuverType.GRAPPLING_STRIKE],
                    )
                ],
            ),
        ),
        PartyMemberConfig(
            id="player-2",
            name="Escaper",
            maxHp=30,
            abilityScores=AbilityScores(strength=10, dexterity=18, constitution=10, intelligence=10, wisdom=10, charisma=10),
            sheet=PartyMemberSheet(skills={enum_key(SkillType.ACROBATICS): ProficiencyLevel.PROFICIENT}),
        ),
    )

    roll = client.post("/api/rooms/sheet-grapple-fail-drop-test/sheet/player-1/resources/superiorityDice/rolls/grapplingStrike?playerKey=player-1").json()["roll"]
    resolution = client.post(f"/api/rooms/sheet-grapple-fail-drop-test/rolls/{roll['id']}/resolve?playerKey=dm&targetSheetId=player-2")
    sheet = client.get("/api/rooms/sheet-grapple-fail-drop-test/sheet/player-2?playerKey=player-2").json()["sheet"]

    assert resolution.status_code == 200
    assert "no Grappled" in resolution.json()["resolution"]["outcome"]
    assert resolution.json()["resolution"]["targetConditions"] == []
    assert sheet["conditions"] == []


def test_sheet_endpoint_uses_party_manifest_stats(tmp_path, monkeypatch) -> None:
    campaign = tmp_path / "stat-campaign"
    party = campaign / "party"
    party.mkdir(parents=True)
    (campaign / "campaign.json").write_text('{"id":"stat-campaign","name":"Stat Campaign"}', encoding="utf-8")
    (party / "party.json").write_text(
        json.dumps(
            typed_json_from_value(
                PartyManifest(
                    members=[
                        PartyMemberConfig(
                            id="player-1",
                            name="Configured Hero",
                            maxHp=31,
                            abilityScores=AbilityScores(strength=16, dexterity=14, constitution=13, intelligence=12, wisdom=10, charisma=8),
                        )
                    ]
                )
            )
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(server, "CAMPAIGN_DIR", tmp_path)

    response = TestClient(server.app).get("/api/rooms/stat-campaign/sheet?playerKey=player-1")

    assert response.status_code == 200
    sheet = response.json()["sheets"][0]
    assert sheet["name"] == "Configured Hero"
    assert sheet["hp"] == {"current": 31, "max": 31, "temporary": 0}
    assert sheet["abilityScores"]["strength"] == 16
    assert sheet["attacks"][0]["damageDie"] == "1d8"


def test_close_quarters_shooter_bonus_is_exposed_in_sheet_roll_payload(tmp_path, monkeypatch) -> None:
    campaign = tmp_path / "close-quarters-campaign"
    party = campaign / "party"
    party.mkdir(parents=True)
    (campaign / "campaign.json").write_text('{"id":"close-quarters-campaign","name":"Close Quarters Campaign"}', encoding="utf-8")
    (party / "party.json").write_text(
        json.dumps(
            typed_json_from_value(
                PartyManifest(
                    members=[
                        PartyMemberConfig(
                            id="player-1",
                            name="Configured Fighter",
                            maxHp=31,
                            abilityScores=AbilityScores(strength=16, dexterity=14, constitution=13, intelligence=12, wisdom=10, charisma=8),
                            sheet=PartyMemberSheet(
                                classes=[
                                    CharacterClassLevel(
                                        name=ClassType.FIGHTER,
                                        level=1,
                                        fightingStyle=FightingStyleType.CLOSE_QUARTERS_SHOOTER,
                                    )
                                ],
                                attacks=[
                                    AttackAction(
                                        id="longbow",
                                        name="Longbow",
                                        ability=AbilityType.DEXTERITY,
                                        damageDiceCount=1,
                                        damageDiceType=DiceType.D8,
                                        damageType=DamageType.PIERCING,
                                        attackRange=AttackRangeType.RANGED,
                                        weaponCategory=WeaponCategory.RANGED,
                                        properties=[WeaponProperty.AMMUNITION, WeaponProperty.TWO_HANDED],
                                    )
                                ],
                            ),
                        )
                    ]
                )
            )
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(server, "CAMPAIGN_DIR", tmp_path)
    monkeypatch.setattr(server.random, "randint", lambda minimum, maximum: 4)

    response = TestClient(server.app).post("/api/rooms/close-quarters-campaign/sheet/player-1/rolls/attack?playerKey=player-1&attackId=longbow")
    roll = response.json()["roll"]

    assert response.status_code == 200
    assert roll["modifier"] == 5
    assert [(part["source"], part["value"]) for part in roll["modifierBreakdown"]] == [("Dexterity", 2), ("Close Quarters Shooter", 1), ("Proficiency", 2)]


def test_equipment_slot_update_recalculates_fighting_style_armor_class(tmp_path, monkeypatch) -> None:
    campaign = tmp_path / "equipment-slot-campaign"
    party = campaign / "party"
    party.mkdir(parents=True)
    (campaign / "campaign.json").write_text('{"id":"equipment-slot-campaign","name":"Equipment Slot Campaign"}', encoding="utf-8")
    (party / "party.json").write_text(
        json.dumps(
            typed_json_from_value(
                PartyManifest(
                    members=[
                        PartyMemberConfig(
                            id="player-1",
                            name="Configured Fighter",
                            maxHp=31,
                            abilityScores=AbilityScores(strength=16, dexterity=14, constitution=13, intelligence=12, wisdom=10, charisma=8),
                            sheet=PartyMemberSheet(
                                classes=[CharacterClassLevel(name=ClassType.FIGHTER, level=1, fightingStyle=FightingStyleType.DEFENSE)],
                                equipment=[
                                    EquipmentItem(
                                        id="chain-mail",
                                        name="Chain Mail",
                                        itemType=EquipmentType.ARMOR,
                                        slot=EquipmentSlot.ARMOR,
                                        armorCategory=ArmorCategory.HEAVY,
                                        armorClass=16,
                                    ),
                                    EquipmentItem(
                                        id="shield",
                                        name="Shield",
                                        itemType=EquipmentType.SHIELD,
                                        slot=EquipmentSlot.OFF_HAND,
                                        armorClassBonus=2,
                                    ),
                                ],
                            ),
                        )
                    ]
                )
            )
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(server, "CAMPAIGN_DIR", tmp_path)
    client = TestClient(server.app)

    starting_sheet = client.get("/api/rooms/equipment-slot-campaign/sheet/player-1?playerKey=player-1").json()["sheet"]
    unwield_shield = client.post("/api/rooms/equipment-slot-campaign/sheet/player-1/equipment/shield/slot?playerKey=player-1&slot=carried")
    unworn_armor = client.post("/api/rooms/equipment-slot-campaign/sheet/player-1/equipment/chain-mail/slot?playerKey=player-1&slot=carried")

    assert starting_sheet["armorClass"] == 19
    assert unwield_shield.json()["sheet"]["armorClass"] == 17
    assert unworn_armor.json()["sheet"]["armorClass"] == 14


def test_equipment_slot_update_rejects_missing_item_and_invalid_slots(tmp_path, monkeypatch) -> None:
    write_party_campaign(
        tmp_path,
        "equipment-slot-errors",
        PartyMemberConfig(
            id="player-1",
            name="Equipment Fighter",
            maxHp=12,
            abilityScores=AbilityScores(strength=16, dexterity=14, constitution=13, intelligence=12, wisdom=10, charisma=8),
            sheet=PartyMemberSheet(
                classes=[CharacterClassLevel(name=ClassType.FIGHTER, level=1, fightingStyle=FightingStyleType.DEFENSE)],
                equipment=[
                    EquipmentItem(
                        id="chain-mail",
                        name="Chain Mail",
                        itemType=EquipmentType.ARMOR,
                        slot=EquipmentSlot.CARRIED,
                        armorCategory=ArmorCategory.HEAVY,
                        armorClass=16,
                    )
                ],
            ),
        ),
    )
    monkeypatch.setattr(server, "CAMPAIGN_DIR", tmp_path)
    client = TestClient(server.app)

    missing = client.post("/api/rooms/equipment-slot-errors/sheet/player-1/equipment/missing/slot?playerKey=player-1&slot=armor")
    invalid_slot = client.post("/api/rooms/equipment-slot-errors/sheet/player-1/equipment/chain-mail/slot?playerKey=player-1&slot=leftPocket")
    invalid_for_item = client.post("/api/rooms/equipment-slot-errors/sheet/player-1/equipment/chain-mail/slot?playerKey=player-1&slot=mainHand")

    assert missing.status_code == 404
    assert missing.json()["detail"] == "Equipment item not found"
    assert invalid_slot.status_code == 400
    assert invalid_slot.json()["detail"] == "Invalid equipment slot"
    assert invalid_for_item.status_code == 400
    assert invalid_for_item.json()["detail"] == "Invalid slot for equipment item"


def test_unarmed_fighting_damage_die_updates_after_equipment_slot_changes(tmp_path, monkeypatch) -> None:
    campaign = tmp_path / "unarmed-slot-campaign"
    party = campaign / "party"
    party.mkdir(parents=True)
    (campaign / "campaign.json").write_text('{"id":"unarmed-slot-campaign","name":"Unarmed Slot Campaign"}', encoding="utf-8")
    (party / "party.json").write_text(
        json.dumps(
            typed_json_from_value(
                PartyManifest(
                    members=[
                        PartyMemberConfig(
                            id="player-1",
                            name="Configured Fighter",
                            maxHp=31,
                            abilityScores=AbilityScores(strength=16, dexterity=14, constitution=13, intelligence=12, wisdom=10, charisma=8),
                            sheet=PartyMemberSheet(
                                classes=[CharacterClassLevel(name=ClassType.FIGHTER, level=1, fightingStyle=FightingStyleType.UNARMED_FIGHTING)],
                                equipment=[
                                    EquipmentItem(id="longsword", name="Longsword", itemType=EquipmentType.WEAPON, slot=EquipmentSlot.MAIN_HAND),
                                    EquipmentItem(id="shield", name="Shield", itemType=EquipmentType.SHIELD, slot=EquipmentSlot.OFF_HAND, armorClassBonus=2),
                                ],
                            ),
                        )
                    ]
                )
            )
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(server, "CAMPAIGN_DIR", tmp_path)
    monkeypatch.setattr(server.random, "randint", lambda minimum, maximum: 5)
    client = TestClient(server.app)

    starting_sheet = client.get("/api/rooms/unarmed-slot-campaign/sheet/player-1?playerKey=player-1").json()["sheet"]
    client.post("/api/rooms/unarmed-slot-campaign/sheet/player-1/equipment/shield/slot?playerKey=player-1&slot=carried")
    empty_hands = client.post("/api/rooms/unarmed-slot-campaign/sheet/player-1/equipment/longsword/slot?playerKey=player-1&slot=carried").json()["sheet"]
    damage_roll = client.post("/api/rooms/unarmed-slot-campaign/sheet/player-1/rolls/damage?playerKey=player-1&attackId=unarmedStrike").json()["roll"]

    assert next(attack for attack in starting_sheet["attacks"] if attack["attackType"] == "unarmedStrike")["damageDiceType"] == "d6"
    assert next(attack for attack in empty_hands["attacks"] if attack["attackType"] == "unarmedStrike")["damageDiceType"] == "d8"
    assert damage_roll["diceType"] == "d8"
    assert damage_roll["die"] == "1d8"


def test_unarmed_fighting_grapple_rider_roll_resolves_as_damage(tmp_path, monkeypatch) -> None:
    campaign = tmp_path / "unarmed-rider-campaign"
    party = campaign / "party"
    party.mkdir(parents=True)
    (campaign / "campaign.json").write_text('{"id":"unarmed-rider-campaign","name":"Unarmed Rider Campaign"}', encoding="utf-8")
    (party / "party.json").write_text(
        json.dumps(
            typed_json_from_value(
                PartyManifest(
                    members=[
                        PartyMemberConfig(
                            id="player-1",
                            name="Grappler",
                            maxHp=31,
                            abilityScores=AbilityScores(strength=16, dexterity=14, constitution=13, intelligence=12, wisdom=10, charisma=8),
                            sheet=PartyMemberSheet(classes=[CharacterClassLevel(name=ClassType.FIGHTER, level=1, fightingStyle=FightingStyleType.UNARMED_FIGHTING)]),
                        ),
                        PartyMemberConfig(id="player-2", name="Target", maxHp=20, abilityScores=AbilityScores(10, 10, 10, 10, 10, 10), sheet=PartyMemberSheet()),
                    ]
                )
            )
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(server, "CAMPAIGN_DIR", tmp_path)
    monkeypatch.setattr(server.random, "randint", lambda minimum, maximum: 3)
    client = TestClient(server.app)

    roll = client.post("/api/rooms/unarmed-rider-campaign/sheet/player-1/abilities/unarmedFighting/rolls/unarmedFighting?playerKey=player-1").json()["roll"]
    resolution = client.post(f"/api/rooms/unarmed-rider-campaign/rolls/{roll['id']}/resolve?playerKey=dm&targetSheetId=player-2")
    target = client.get("/api/rooms/unarmed-rider-campaign/sheet/player-2?playerKey=player-2").json()["sheet"]

    assert resolution.status_code == 200
    assert roll["resolution"] == "applyDamage"
    assert roll["damageType"] == "bludgeoning"
    assert target["hp"]["current"] == 17


def test_server_endpoint_guard_paths_for_sheet_mutations(tmp_path, monkeypatch) -> None:
    write_party_campaign(
        tmp_path,
        "guard-path-test",
        PartyMemberConfig(
            id="player-1",
            name="Guard Fighter",
            maxHp=12,
            abilityScores=AbilityScores(16, 14, 13, 12, 10, 8),
            sheet=PartyMemberSheet(
                classes=[CharacterClassLevel(name=ClassType.FIGHTER, level=3)],
                equipment=[EquipmentItem(id="rope", name="Rope", itemType=EquipmentType.GEAR, slot=EquipmentSlot.CARRIED)],
            ),
        ),
        PartyMemberConfig(id="player-2", name="Other"),
    )
    monkeypatch.setattr(server, "CAMPAIGN_DIR", tmp_path)
    client = TestClient(server.app)

    assert client.post("/api/rooms/guard-path-test/sheet/not-a-sheet/rolls/clear?playerKey=player-1").status_code == 404
    assert client.post("/api/rooms/guard-path-test/sheet/player-1/rolls/clear?playerKey=player-2").status_code == 403
    assert client.post("/api/rooms/guard-path-test/sheet/not-a-sheet/resources/actionSurge?playerKey=player-1&currentUses=0").status_code == 404
    assert client.post("/api/rooms/guard-path-test/sheet/player-1/resources/secondWind?playerKey=player-2&currentUses=0").status_code == 403
    assert client.post("/api/rooms/guard-path-test/sheet/not-a-sheet/level?playerKey=dm&delta=1").status_code == 404
    assert client.post("/api/rooms/guard-path-test/sheet/not-a-sheet/choices/fighterSubclass?playerKey=player-1", json={"values": ["champion"]}).status_code == 404
    assert client.post("/api/rooms/guard-path-test/sheet/player-1/choices/fighterSubclass?playerKey=player-2", json={"values": ["champion"]}).status_code == 403
    assert client.post("/api/rooms/guard-path-test/sheet/player-1/choices/fighterSubclass?playerKey=player-1", json={"values": "champion"}).status_code == 400
    assert client.post("/api/rooms/guard-path-test/sheet/player-1/choices/not-a-choice?playerKey=player-1", json={"values": ["champion"]}).status_code == 400
    assert client.post("/api/rooms/guard-path-test/sheet/player-1/equipment/rope/slot?playerKey=player-1&slot=armor").status_code == 400
    assert client.post("/api/rooms/guard-path-test/sheet/player-1/equipment/rope/slot?playerKey=player-1&slot=bad-slot").status_code == 400
    assert client.post("/api/rooms/guard-path-test/sheet/player-1/conditions/not-a-condition?playerKey=player-1&active=true").status_code == 400


def test_handle_message_dispatches_websocket_routes(monkeypatch) -> None:
    room = server.get_or_create_room("dispatch-test")
    socket = FakeSocket()
    player = server.Player(id="connection-1", name="Player", player_key="player-1", websocket=socket, room_id=room.id)
    room.players[player.id] = player
    calls: list[tuple[str, tuple]] = []

    async def record(name):
        async def inner(*args):
            calls.append((name, args))
        return inner

    async def join(*args):
        calls.append(("join_room", args))

    monkeypatch.setattr(server, "join_room", join)
    for name in [
        "lock_token",
        "move_token",
        "release_token",
        "set_token_scene",
        "set_token_radius",
        "set_fog_mode",
        "reveal_fog",
        "set_board",
        "load_asset_token",
        "delete_token",
        "clear_scene",
    ]:
        monkeypatch.setattr(server, name, asyncio.run(record(name)))

    asyncio.run(server.handle_message(player, {"type": "join_room", "roomId": "next", "playerName": "Ana", "playerKey": "dm"}))
    asyncio.run(server.handle_message(player, {"type": "request_token_lock", "tokenId": "player-1"}))
    asyncio.run(server.handle_message(player, {"type": "move_token", "tokenId": "player-1"}))
    asyncio.run(server.handle_message(player, {"type": "release_token", "tokenId": "player-1"}))
    asyncio.run(server.handle_message(player, {"type": "set_token_scene", "tokenId": "player-1"}))
    asyncio.run(server.handle_message(player, {"type": "set_token_radius", "tokenId": "player-1", "radius": 88}))
    asyncio.run(server.handle_message(player, {"type": "set_fog_mode"}))
    asyncio.run(server.handle_message(player, {"type": "reveal_fog"}))
    asyncio.run(server.handle_message(player, {"type": "set_board", "boardId": "windmill"}))
    asyncio.run(server.handle_message(player, {"type": "load_asset", "assetKind": "asset", "assetId": "aboleth"}))
    asyncio.run(server.handle_message(player, {"type": "delete_token", "tokenId": "asset-1"}))
    asyncio.run(server.handle_message(player, {"type": "clear_scene"}))
    player.room_id = None
    asyncio.run(server.handle_message(player, {"type": "move_token", "tokenId": "player-1"}))

    assert [name for name, _args in calls] == [
        "join_room",
        "lock_token",
        "move_token",
        "release_token",
        "set_token_scene",
        "set_token_radius",
        "set_fog_mode",
        "reveal_fog",
        "set_board",
        "load_asset_token",
        "delete_token",
        "clear_scene",
    ]


def test_server_state_helpers_cover_rest_equipment_and_room_edges(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(server, "CAMPAIGN_DIR", tmp_path)
    room = server.get_or_create_room("helper-path-test")
    dm_socket = FakeSocket()
    player = server.Player(id="connection-1", name="DM", player_key="dm", websocket=dm_socket, room_id=room.id)
    room.players[player.id] = player
    sheet = server.token_to_sheet(room.tokens["player-1"], room.id, current_hp=5)
    short_resource = ResourceTracker("short", "Short", 0, 2, RestType.SHORT_REST, TimeEconomy.SPECIAL, "short")
    long_resource = ResourceTracker("long", "Long", 0, 1, RestType.LONG_REST, TimeEconomy.SPECIAL, "long")
    none_resource = ResourceTracker("none", "None", 0, 1, RestType.NONE, TimeEconomy.SPECIAL, "none")
    sheet.resources = [short_resource, long_resource, none_resource]
    sheet.conditions = [ConditionType.PRONE, ConditionType.FRIGHTENED, ConditionType.CHARMED]
    room.condition_durations[sheet.tokenId] = {
        ConditionType.PRONE: ConditionDuration.UNTIL_SHORT_REST,
        ConditionType.FRIGHTENED: ConditionDuration.UNTIL_LONG_REST,
        ConditionType.CHARMED: ConditionDuration.MANUAL,
    }
    room.temporary_hit_points[sheet.tokenId] = 7

    server.reset_sheet_resources(room, sheet, RestType.SHORT_REST)
    server.reset_sheet_conditions(room, sheet, RestType.SHORT_REST)
    server.reset_sheet_temporary_hit_points(room, sheet, RestType.SHORT_REST)
    assert room.resource_uses[sheet.tokenId] == {"short": 2}
    assert room.condition_overrides[sheet.tokenId] == [ConditionType.FRIGHTENED, ConditionType.CHARMED]
    assert room.temporary_hit_points[sheet.tokenId] == 7

    server.reset_sheet_resources(room, sheet, RestType.LONG_REST)
    server.reset_sheet_conditions(room, sheet, RestType.LONG_REST)
    server.reset_sheet_temporary_hit_points(room, sheet, RestType.LONG_REST)
    assert room.resource_uses[sheet.tokenId] == {"short": 2, "long": 1}
    assert sheet.tokenId not in room.temporary_hit_points
    assert server.parse_rest_type("short-rest") == RestType.SHORT_REST
    assert server.parse_rest_type("long") == RestType.LONG_REST
    assert server.resource_resets_on_rest(RestType.NONE, RestType.LONG_REST) is False

    armor = EquipmentItem(id="chain", name="Chain Mail", itemType=EquipmentType.ARMOR, slot=EquipmentSlot.ARMOR, armorCategory=ArmorCategory.HEAVY, armorClass=16)
    sword = EquipmentItem(id="sword", name="Sword", itemType=EquipmentType.WEAPON, slot=EquipmentSlot.MAIN_HAND)
    shield_item = EquipmentItem(id="shield", name="Shield", itemType=EquipmentType.SHIELD, slot=EquipmentSlot.OFF_HAND)
    sheet.equipment = [armor, sword, shield_item]
    server.set_equipment_slot(room, sheet, "new-armor", EquipmentSlot.ARMOR)
    server.set_equipment_slot(room, sheet, "greatsword", EquipmentSlot.TWO_HANDS)
    server.set_equipment_slot(room, sheet, "dagger", EquipmentSlot.MAIN_HAND)
    assert room.equipment_slots[sheet.tokenId]["chain"] == EquipmentSlot.CARRIED
    assert room.equipment_slots[sheet.tokenId]["sword"] == EquipmentSlot.CARRIED
    assert server.valid_equipment_slots(EquipmentItem(id="gear", name="Gear", itemType=EquipmentType.GEAR, slot=EquipmentSlot.CARRIED)) == {EquipmentSlot.CARRIED}

    history_roll = RollPayload("roll", "sheet", "token", "player", RollSource(SheetSectionType.ATTACKS, "a", "b"), "A", RollResolutionMode.NONE, "Roll", None, [], DiceType.D20, "d20", 0, [], 0, 1)
    room.roll_history = [server.RollLogEntry(str(index), server.RollLogEntryType.ROLL_CREATED, index, history_roll) for index in range(server.ROLL_HISTORY_LIMIT + 3)]
    server.append_roll_log_entry(room, server.RollLogEntry("last", server.RollLogEntryType.ROLL_CREATED, 999, history_roll))
    assert len(room.roll_history) == server.ROLL_HISTORY_LIMIT
    assert room.roll_history[-1].id == "last"

    player.room_id = "missing-room"
    asyncio.run(server.leave_room(player))
    assert player.room_id is None


def test_server_roll_resolution_helper_edges(monkeypatch) -> None:
    rolls = iter([1, 20, 20, 1])
    monkeypatch.setattr(server.random, "randint", lambda minimum, maximum: next(rolls))
    room = server.get_or_create_room("resolution-helper-test")
    source = server.token_to_sheet(room.tokens["player-1"], room.id)
    target = server.token_to_sheet(room.tokens["player-2"], room.id)
    target.conditions = []
    target.savingThrows = []
    target.abilityScores.dexterity = 10
    room.tokens.pop("player-1")

    missing_source_roll = RollPayload(
        "roll-missing-source",
        source.id,
        source.tokenId,
        "player-1",
        RollSource(SheetSectionType.ABILITIES, "ability", "action"),
        "Effect",
        RollResolutionMode.NONE,
        "Effect",
        None,
        [1],
        DiceType.D20,
        "d20",
        0,
        [],
        1,
        1,
        conditionEffects=[ConditionEffect(ConditionType.GRAPPLED, ConditionApplicationMode.SOURCE_CHECK, sourceCheck=AbilityType.STRENGTH, contestChecks=[AbilityType.STRENGTH, AbilityType.DEXTERITY])],
    )
    assert server.resolve_source_check_condition_effects(missing_source_roll, None, target) == []

    save_fail_roll = RollPayload(
        "roll-save-fail",
        source.id,
        source.tokenId,
        "player-1",
        RollSource(SheetSectionType.ABILITIES, "ability", "action"),
        "Poison",
        RollResolutionMode.NONE,
        "Poison",
        None,
        [1],
        DiceType.D20,
        "d20",
        0,
        [],
        1,
        1,
        conditionEffects=[ConditionEffect(ConditionType.POISONED, ConditionApplicationMode.TARGET_SAVE, savingThrow=AbilityType.DEXTERITY, saveDc=15)],
    )
    fail_outcomes = server.resolve_target_save_effects(save_fail_roll, target)
    pass_outcomes = server.resolve_target_save_effects(save_fail_roll, target)
    assert "fails DC 15 Dexterity save and gains Poisoned" in fail_outcomes[0][0]
    assert "passes DC 15 Dexterity save against Poisoned" in pass_outcomes[0][0]

    room.tokens["player-1"] = server.Token("player-1", server.TokenKind.CHARACTER, "Source", "player-1", server.DEFAULT_TOKEN_COLOR, 0, 0, 70, True)
    grapple_roll = RollPayload(
        "roll-grapple",
        source.id,
        source.tokenId,
        "player-1",
        RollSource(SheetSectionType.ABILITIES, "ability", "action"),
        "Grapple",
        RollResolutionMode.NONE,
        "Grapple",
        None,
        [1],
        DiceType.D20,
        "d20",
        0,
        [],
        1,
        1,
        conditionEffects=[ConditionEffect(ConditionType.GRAPPLED, ConditionApplicationMode.SOURCE_CHECK, sourceCheck=AbilityType.STRENGTH, contestChecks=[AbilityType.STRENGTH, AbilityType.DEXTERITY])],
    )
    outcomes = server.resolve_source_check_condition_effects(grapple_roll, source, target)
    assert outcomes[0][1] == ConditionType.GRAPPLED
    assert len(outcomes[0][2]) == 2


def test_member_progression_helper_error_and_pruning_paths(monkeypatch) -> None:
    monkeypatch.setattr(server.random, "randint", lambda minimum, maximum: 1)
    no_asi_member = PartyMemberConfig(id="player-1", name="No ASI", sheet=PartyMemberSheet(classes=[CharacterClassLevel(name=ClassType.FIGHTER, level=3)]))
    server.apply_member_ability_score_improvement(no_asi_member, ["strength"])
    assert no_asi_member.sheet.abilityScoreImprovements is None

    member = PartyMemberConfig(
        id="player-1",
        name="ASI Fighter",
        maxHp=20,
        abilityScores=AbilityScores(19, 10, 13, 10, 10, 10),
        sheet=PartyMemberSheet(classes=[CharacterClassLevel(name=ClassType.FIGHTER, level=4)]),
    )
    server.apply_member_ability_score_improvement(member, ["strength"])
    assert member.abilityScores.strength == 20
    assert member.sheet.abilityScoreImprovements == ["strength:1"]

    for values, detail in [
        (["strength", "dexterity", "constitution"], "Choose one ability twice or two abilities once"),
        (["luck"], "Invalid ability score"),
        ([], "Choose one ability twice or two abilities once"),
    ]:
        with pytest.raises(Exception) as error:
            server.apply_member_ability_score_improvement(
                PartyMemberConfig(id="player-1", name="Bad ASI", sheet=PartyMemberSheet(classes=[CharacterClassLevel(name=ClassType.FIGHTER, level=4)])),
                values,
            )
        assert error.value.status_code == 400
        assert error.value.detail == detail

    maxed = PartyMemberConfig(id="player-1", name="Maxed", abilityScores=AbilityScores(20, 20, 20, 20, 20, 20), sheet=PartyMemberSheet(classes=[CharacterClassLevel(name=ClassType.FIGHTER, level=4)]))
    with pytest.raises(Exception) as max_error:
        server.apply_member_ability_score_improvement(maxed, ["strength"])
    assert max_error.value.detail == "Ability scores cannot be increased above 20"

    feat_member = PartyMemberConfig(id="player-1", name="Feat", sheet=PartyMemberSheet(classes=[CharacterClassLevel(name=ClassType.FIGHTER, level=4)]))
    with pytest.raises(Exception) as invalid_feat:
        server.apply_member_ability_score_improvement(feat_member, ["feat:not-real"])
    assert invalid_feat.value.detail == "Invalid feat"
    server.apply_member_ability_score_improvement(feat_member, ["feat:actor"])
    with pytest.raises(Exception) as duplicate_feat:
        server.apply_member_ability_score_improvement(PartyMemberConfig(id="player-1", name="Feat", sheet=PartyMemberSheet(classes=[CharacterClassLevel(name=ClassType.FIGHTER, level=8)], feats=feat_member.sheet.feats)), ["feat:actor"])
    assert duplicate_feat.value.detail == "Feat is already selected"

    member.sheet.abilityScoreImprovements = ["strength:1", "feat:actor", "constitution:2"]
    member.sheet.feats = [general_feat_feature("actor")]
    member.abilityScores.constitution = 15
    server.prune_member_ability_score_improvements(member)
    assert member.sheet.abilityScoreImprovements == ["strength:1"]
    assert member.sheet.feats is None


def test_member_spell_pruning_paths() -> None:
    shield = eldritch_knight_catalog_spell("shield")
    mage_hand = arcane_trickster_catalog_spell("mageHand")
    assert shield is not None
    assert mage_hand is not None
    arcane_trickster_mage_hand = replace(mage_hand, source=SpellSource.ARCANE_TRICKSTER)

    fighter_member = PartyMemberConfig(
        id="player-1",
        name="Not EK",
        sheet=PartyMemberSheet(classes=[CharacterClassLevel(name=ClassType.FIGHTER, level=3, subclass=FighterSubclassType.CHAMPION)], spells=[shield]),
    )
    rogue_member = PartyMemberConfig(
        id="player-1",
        name="Not AT",
        sheet=PartyMemberSheet(classes=[CharacterClassLevel(name=ClassType.ROGUE, level=3, subclass=RogueSubclassType.THIEF)], spells=[arcane_trickster_mage_hand]),
    )

    server.prune_member_eldritch_knight_spells(PartyMemberConfig(id="player-1", name="No Sheet"))
    server.prune_member_arcane_trickster_spells(PartyMemberConfig(id="player-1", name="No Spells", sheet=PartyMemberSheet()))
    server.prune_member_eldritch_knight_spells(fighter_member)
    server.prune_member_arcane_trickster_spells(rogue_member)
    assert fighter_member.sheet.spells is None
    assert rogue_member.sheet.spells is None


def test_saved_state_and_asset_parsing_fallbacks(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(server, "SAVE_DIR", tmp_path / "saves")
    monkeypatch.setattr(server, "CAMPAIGN_DIR", tmp_path / "campaigns")
    save_dir = tmp_path / "saves"
    save_dir.mkdir()
    bad_path = save_dir / "bad.json"
    bad_path.write_text("{bad", encoding="utf-8")

    assert server.load_saved_tokens("missing") is None
    assert server.load_saved_tokens("bad") is None
    assert server.load_saved_fog("bad") == server.default_fog()
    assert server.load_saved_board_id("bad") == "-"
    assert server.load_saved_resource_uses("bad") == {}

    resources_path = save_dir / "resources.json"
    resources_path.write_text(json.dumps({"resources": {" Player 1! ": {"Second Wind": "2", "bad": "x"}, "bad": []}}), encoding="utf-8")
    assert server.load_saved_resource_uses("resources") == {"player1": {"secondwind": 2}}

    party_dir = tmp_path / "campaigns" / "party-fallback" / "party"
    party_dir.mkdir(parents=True)
    assert server.load_party_members_from_manifest(party_dir / "missing.json") == []
    (party_dir / "bad.json").write_text("{bad", encoding="utf-8")
    assert server.load_party_members_from_manifest(party_dir / "bad.json") == []

    duplicate_manifest = PartyManifest(
        members=[
            PartyMemberConfig(id="player-1", name="First"),
            PartyMemberConfig(id="player-1", name="Duplicate"),
            PartyMemberConfig(id="not-player", name="Fallback"),
        ]
    )
    (party_dir / "party.json").write_text(json.dumps(typed_json_from_value(duplicate_manifest)), encoding="utf-8")
    members = server.load_party_members_from_manifest(party_dir / "party.json", "party-fallback")
    assert [member.id for member in members] == ["player-1", "player-3"]

    images = tmp_path / "images"
    images.mkdir()
    (images / "not-image.png").write_text("bad", encoding="utf-8")
    (images / "notes.txt").write_text("skip", encoding="utf-8")
    assert server.image_dimensions(images / "not-image.png") is None
    assert server.list_assets_from_dir(server.TokenKind.ASSET, images) == [server.Asset(id="not-image", kind=server.TokenKind.ASSET, name="Not Image", avatarUrl="/shared/assets/not-image.png")]
    assert server.get_asset("asset", "missing") is None
    assert server.board_to_dict(server.Board("-", "-", None, 1, 1)) == {"id": "-", "name": "-", "width": 1, "height": 1}
    assert server.fog_from_dict({"hideMode": True, "brushSize": "bad", "revealedAreas": [{"x": 9999, "y": -1, "radius": "bad"}, "skip"]}, server.Board("-", "-", None, 100, 50)).revealedAreas == [
        server.RevealedArea(x=100, y=0, radius=20)
    ]
    assert server.next_dynamic_token_number(
        [
            server.Token("player-1", server.TokenKind.CHARACTER, "Character", "player-1", server.DEFAULT_TOKEN_COLOR, 0, 0, 70, False),
            server.Token("asset-bad", server.TokenKind.ASSET, "Bad", "dm", server.DEFAULT_TOKEN_COLOR, 0, 0, 70, False),
            server.Token("asset-7", server.TokenKind.ASSET, "Seven", "dm", server.DEFAULT_TOKEN_COLOR, 0, 0, 70, False),
        ]
    ) == 8


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
