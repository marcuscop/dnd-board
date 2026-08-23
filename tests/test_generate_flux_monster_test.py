from utils import generate_flux_monster_test


def test_slugify_monster_prompt() -> None:
    assert generate_flux_monster_test.slugify("grimlock - dungeons and dragons monster") == "grimlock-dungeons-and-dragons-monster"


def test_load_api_key_from_local_flux_api_file(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("BFL_API_KEY", raising=False)
    key_file = tmp_path / "flux-api"
    key_file.write_text("BFL_API_KEY='test-key'\n", encoding="utf-8")

    assert generate_flux_monster_test.load_api_key(key_file) == "test-key"


def test_poll_result_prefers_polling_url(monkeypatch) -> None:
    calls = []

    def fake_request_json(url, *, api_key, method="GET", payload=None):
        calls.append((url, api_key, method, payload))
        return {"status": "Ready"}

    monkeypatch.setattr(generate_flux_monster_test, "request_json", fake_request_json)

    result = generate_flux_monster_test.poll_result(
        api_key="test-key",
        base_url="https://api.bfl.ai/v1",
        polling_url="https://api.bfl.ai/v1/get_result?id=task-1",
        task_id="ignored",
    )

    assert result == {"status": "Ready"}
    assert calls == [("https://api.bfl.ai/v1/get_result?id=task-1", "test-key", "GET", None)]


def test_poll_result_falls_back_to_task_id(monkeypatch) -> None:
    calls = []

    def fake_request_json(url, *, api_key, method="GET", payload=None):
        calls.append((url, api_key, method, payload))
        return {"status": "Ready"}

    monkeypatch.setattr(generate_flux_monster_test, "request_json", fake_request_json)

    generate_flux_monster_test.poll_result(
        api_key="test-key",
        base_url="https://api.bfl.ai/v1",
        polling_url=None,
        task_id="task-1",
    )

    assert calls == [("https://api.bfl.ai/v1/get_result?id=task-1", "test-key", "GET", None)]
