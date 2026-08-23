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
