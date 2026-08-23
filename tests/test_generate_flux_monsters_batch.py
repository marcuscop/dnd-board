from __future__ import annotations

import json

from utils import generate_flux_monsters_batch as batch


def test_load_names_keeps_only_nonempty_strings(tmp_path):
    path = tmp_path / "names.json"
    path.write_text(json.dumps(["Aboleth", "", 3, " Goblin "]), encoding="utf-8")

    assert batch.load_names(path) == ["Aboleth", "Goblin"]


def test_select_names_uses_start_and_limit():
    assert batch.select_names(["A", "B", "C", "D"], start=1, limit=2) == ["B", "C"]


def test_generate_batch_skips_existing_without_overwrite(tmp_path, monkeypatch):
    existing = tmp_path / "aboleth.png"
    existing.write_bytes(b"existing")
    calls = []

    def fake_generate_image(**kwargs):
        calls.append(kwargs)
        return "https://example.test/goblin.png"

    def fake_download_image(image_url, output_dir, monster_name):
        target = output_dir / f"{monster_name.lower()}.png"
        target.write_bytes(b"generated")
        return target

    monkeypatch.setattr(batch.flux, "generate_image", fake_generate_image)
    monkeypatch.setattr(batch.flux, "download_image", fake_download_image)

    failures = batch.generate_batch(
        names=["Aboleth", "Goblin"],
        api_key="key",
        output_dir=tmp_path,
        model="flux-test",
        base_url="https://api.example.test",
        width=1024,
        height=1024,
        timeout_seconds=25,
        overwrite=False,
    )

    assert failures == []
    assert len(calls) == 1
    assert calls[0]["prompt"].startswith("Goblin")


def test_generate_batch_records_failure_and_continues(tmp_path, monkeypatch):
    def fake_generate_image(**kwargs):
        if kwargs["prompt"].startswith("Aboleth"):
            raise RuntimeError("boom")
        return "https://example.test/goblin.png"

    def fake_download_image(image_url, output_dir, monster_name):
        target = output_dir / f"{monster_name.lower()}.png"
        target.write_bytes(b"generated")
        return target

    monkeypatch.setattr(batch.flux, "generate_image", fake_generate_image)
    monkeypatch.setattr(batch.flux, "download_image", fake_download_image)

    failures = batch.generate_batch(
        names=["Aboleth", "Goblin"],
        api_key="key",
        output_dir=tmp_path,
        model="flux-test",
        base_url="https://api.example.test",
        width=1024,
        height=1024,
        timeout_seconds=25,
        overwrite=False,
    )

    assert failures == [{"name": "Aboleth", "error": "boom"}]
    assert (tmp_path / "goblin.png").exists()


def test_generate_batch_logs_pending_timeout_tasks(tmp_path, monkeypatch):
    pending_path = tmp_path / "pending.jsonl"

    def fake_generate_image(**kwargs):
        raise batch.flux.FluxTimeoutError(
            task_id="task-1",
            polling_url="https://api.example.test/poll/task-1",
            elapsed_seconds=25.125,
            timeout_seconds=25,
            last_status={"status": "Pending"},
        )

    monkeypatch.setattr(batch.flux, "generate_image", fake_generate_image)

    failures = batch.generate_batch(
        names=["Aboleth"],
        api_key="key",
        output_dir=tmp_path,
        model="flux-test",
        base_url="https://api.example.test",
        width=1024,
        height=1024,
        timeout_seconds=25,
        overwrite=False,
        pending_path=pending_path,
    )

    pending = json.loads(pending_path.read_text(encoding="utf-8"))
    assert failures[0]["name"] == "Aboleth"
    assert pending["name"] == "Aboleth"
    assert pending["task_id"] == "task-1"
    assert pending["last_status"] == {"status": "Pending"}


def test_generate_batch_logs_moderated_requests(tmp_path, monkeypatch):
    moderated_path = tmp_path / "request-moderated.json"

    def fake_generate_image(**kwargs):
        raise batch.flux.FluxModeratedError(
            task_id="task-1",
            polling_url="https://api.example.test/poll/task-1",
            status_data={"status": "Request Moderated", "progress": None},
        )

    monkeypatch.setattr(batch.flux, "generate_image", fake_generate_image)

    failures = batch.generate_batch(
        names=["Aerisi Kalinoth"],
        api_key="key",
        output_dir=tmp_path,
        model="flux-test",
        base_url="https://api.example.test",
        width=1024,
        height=1024,
        timeout_seconds=25,
        overwrite=False,
        moderated_path=moderated_path,
    )

    moderated = json.loads(moderated_path.read_text(encoding="utf-8"))
    assert failures[0]["name"] == "Aerisi Kalinoth"
    assert moderated == [
        {
            "base_url": "https://api.example.test",
            "height": 1024,
            "model": "flux-test",
            "name": "Aerisi Kalinoth",
            "polling_url": "https://api.example.test/poll/task-1",
            "status": {"progress": None, "status": "Request Moderated"},
            "task_id": "task-1",
            "width": 1024,
        }
    ]


def test_moderated_requests_are_deduped_by_monster_name(tmp_path):
    moderated_path = tmp_path / "request-moderated.json"
    batch.append_moderated_request(moderated_path, {"name": "Aerisi Kalinoth", "task_id": "task-1"})
    batch.append_moderated_request(moderated_path, {"name": " aerisi   kalinoth ", "task_id": "task-2"})

    moderated = json.loads(moderated_path.read_text(encoding="utf-8"))
    assert moderated == [{"name": "Aerisi Kalinoth", "task_id": "task-1"}]


def test_generate_batch_stops_on_billing_error(tmp_path, monkeypatch):
    calls = []

    def fake_generate_image(**kwargs):
        calls.append(kwargs["prompt"])
        raise RuntimeError("BFL request failed with 402: Insufficient credits")

    monkeypatch.setattr(batch.flux, "generate_image", fake_generate_image)

    failures = batch.generate_batch(
        names=["Aboleth", "Goblin"],
        api_key="key",
        output_dir=tmp_path,
        model="flux-test",
        base_url="https://api.example.test",
        width=1024,
        height=1024,
        timeout_seconds=25,
        overwrite=False,
    )

    assert len(calls) == 1
    assert failures == [{"name": "Aboleth", "error": "BFL request failed with 402: Insufficient credits"}]


def test_count_existing_names_uses_slugged_png_files(tmp_path):
    (tmp_path / "adult-red-dragon.png").write_bytes(b"existing")

    assert batch.count_existing_names(["Adult Red Dragon", "Adult Blue Dragon"], tmp_path) == 1
