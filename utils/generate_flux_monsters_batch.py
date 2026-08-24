from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from utils import generate_flux_monster_test as flux


DEFAULT_NAMES_PATH = Path("shared/dndbeyond_monster_names.json")
DEFAULT_OUTPUT_DIR = Path("shared/assets")
DEFAULT_FAILURES_PATH = Path("shared/assets/generated/flux_failures.json")
DEFAULT_PENDING_PATH = Path("shared/assets/generated/flux_pending.jsonl")
DEFAULT_MODERATED_PATH = Path("shared/assets/request-moderated.json")
DEFAULT_LIMIT = 50
DEFAULT_START = 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate FLUX monster images from a JSON monster-name list.")
    parser.add_argument("--names", type=Path, default=DEFAULT_NAMES_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--failures", type=Path, default=DEFAULT_FAILURES_PATH)
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--start", type=int, default=DEFAULT_START)
    parser.add_argument("--model", default=flux.DEFAULT_MODEL)
    parser.add_argument("--base-url", default=flux.BASE_URL)
    parser.add_argument("--width", type=int, default=1024)
    parser.add_argument("--height", type=int, default=1024)
    parser.add_argument("--timeout", type=float, default=flux.TIMEOUT_SECONDS)
    parser.add_argument("--key-file", type=Path, default=flux.DEFAULT_KEY_FILE)
    parser.add_argument("--pending", type=Path, default=DEFAULT_PENDING_PATH)
    parser.add_argument("--moderated", type=Path, default=DEFAULT_MODERATED_PATH)
    parser.add_argument("--debug-polls", action="store_true", help="Print periodic BFL poll status payloads.")
    parser.add_argument("--debug-every", type=float, default=flux.DEBUG_POLL_SECONDS, help="Seconds between poll debug lines.")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    names = load_names(args.names)
    selected_names = select_names(names, start=args.start, limit=args.limit)
    api_key = flux.load_api_key(args.key_file)
    failures = generate_batch(
        names=selected_names,
        api_key=api_key,
        output_dir=args.output_dir,
        model=args.model,
        base_url=args.base_url,
        width=args.width,
        height=args.height,
        timeout_seconds=args.timeout,
        overwrite=args.overwrite,
        pending_path=args.pending,
        moderated_path=args.moderated,
        debug_polls=args.debug_polls,
        debug_every_seconds=args.debug_every,
    )
    write_failures(args.failures, failures)
    available_count = count_existing_names(selected_names, args.output_dir)
    missing_count = len(selected_names) - available_count
    print(f"Finished: {available_count} available, {len(failures)} failed in this run, {missing_count} still missing")
    if failures:
        print(f"Failures: {args.failures}")


def load_names(path: Path) -> list[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise RuntimeError(f"Monster name file must contain a JSON list: {path}")

    names = [name.strip() for name in data if isinstance(name, str) and name.strip()]
    if not names:
        raise RuntimeError(f"Monster name file did not contain any names: {path}")
    return names


def select_names(names: list[str], *, start: int, limit: int) -> list[str]:
    if start < 0:
        raise ValueError("start must be 0 or greater.")
    if limit < 1:
        raise ValueError("limit must be 1 or greater.")
    return names[start : start + limit]


def generate_batch(
    *,
    names: list[str],
    api_key: str,
    output_dir: Path,
    model: str,
    base_url: str,
    width: int,
    height: int,
    timeout_seconds: float,
    overwrite: bool,
    pending_path: Path | None = None,
    moderated_path: Path | None = None,
    debug_polls: bool = False,
    debug_every_seconds: float = flux.DEBUG_POLL_SECONDS,
) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []

    for index, monster_name in enumerate(names, start=1):
        target = output_dir / f"{flux.slugify(monster_name)}.png"
        if target.exists() and not overwrite:
            print(f"[{index}/{len(names)}] Skipping existing: {target}")
            continue

        print(f"[{index}/{len(names)}] Generating: {monster_name}")
        try:
            prompt = f"{monster_name}{flux.STYLE_SUFFIX}"
            image_url = flux.generate_image(
                api_key=api_key,
                base_url=base_url,
                model=model,
                prompt=prompt,
                width=width,
                height=height,
                timeout_seconds=timeout_seconds,
                debug_polls=debug_polls,
                debug_every_seconds=debug_every_seconds,
            )
            saved_path = flux.download_image(image_url, output_dir, monster_name)
            print(f"[{index}/{len(names)}] Saved: {saved_path}")
        except Exception as error:  # Keep the batch moving and record the failure.
            failures.append({"name": monster_name, "error": str(error)})
            print(f"[{index}/{len(names)}] Failed: {monster_name}: {error}")
            if pending_path is not None and isinstance(error, flux.FluxTimeoutError):
                append_pending_task(
                    pending_path,
                    {
                        "name": monster_name,
                        "model": model,
                        "base_url": base_url,
                        "width": width,
                        "height": height,
                        "timeout_seconds": timeout_seconds,
                        "task_id": error.task_id,
                        "polling_url": error.polling_url,
                        "elapsed_seconds": round(error.elapsed_seconds, 3),
                        "last_status": flux.summarize_status(error.last_status),
                    },
                )
            if moderated_path is not None and isinstance(error, flux.FluxModeratedError):
                append_moderated_request(
                    moderated_path,
                    {
                        "name": monster_name,
                        "model": model,
                        "base_url": base_url,
                        "width": width,
                        "height": height,
                        "task_id": error.task_id,
                        "polling_url": error.polling_url,
                        "status": flux.summarize_status(error.status_data),
                    },
                )
            if is_terminal_billing_error(error):
                print("Stopping batch because BFL reported a billing or credit error.")
                break

    return failures


def append_pending_task(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as pending_file:
        pending_file.write(json.dumps(data, sort_keys=True) + "\n")


def append_moderated_request(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = load_json_list(path)
    name_key = normalized_name_key(data.get("name"))
    if name_key and not any(normalized_name_key(entry.get("name")) == name_key for entry in existing if isinstance(entry, dict)):
        existing.append(data)
    path.write_text(json.dumps(existing, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def normalized_name_key(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().split())


def load_json_list(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    return [entry for entry in data if isinstance(entry, dict)]


def write_failures(path: Path, failures: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(failures, indent=2) + "\n", encoding="utf-8")


def count_existing_names(names: list[str], output_dir: Path) -> int:
    return sum(1 for name in names if (output_dir / f"{flux.slugify(name)}.png").exists())


def is_terminal_billing_error(error: Exception) -> bool:
    message = str(error).lower()
    return any(
        signal in message
        for signal in (
            "402",
            "payment",
            "billing",
            "credit",
            "insufficient",
            "quota",
        )
    )


if __name__ == "__main__":
    main()
