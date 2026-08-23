from __future__ import annotations

import argparse
import json
import os
import re
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


BASE_URL = "https://api.bfl.ai/v1"
DEFAULT_MODEL = "flux-2-pro"
DEFAULT_MONSTER = "boggle"
DEFAULT_OUTPUT_DIR = Path("shared/monsters/")
DEFAULT_KEY_FILE = Path("flux-api")
POLL_INTERVAL_SECONDS = 1.5
TIMEOUT_SECONDS = 25
STYLE_SUFFIX = (
    ", dark fantasy with no symbols, substantial design, dungeons and dragons monster manual, "
    " isolated on white background, detailed watercolor vignette, "
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate one test monster image with the Black Forest Labs FLUX API.")
    parser.add_argument("--monster", default=DEFAULT_MONSTER)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--base-url", default=BASE_URL)
    parser.add_argument("--width", type=int, default=1024)
    parser.add_argument("--height", type=int, default=1024)
    parser.add_argument("--timeout", type=float, default=TIMEOUT_SECONDS)
    parser.add_argument("--key-file", type=Path, default=DEFAULT_KEY_FILE)
    args = parser.parse_args()

    api_key = load_api_key(args.key_file)
    prompt = f"{args.monster}{STYLE_SUFFIX}"
    image_url = generate_image(
        api_key=api_key,
        base_url=args.base_url,
        model=args.model,
        prompt=prompt,
        width=args.width,
        height=args.height,
        timeout_seconds=args.timeout,
    )
    target = download_image(image_url, args.output_dir, args.monster)
    print(f"Saved: {target}")


def load_api_key(key_file: Path) -> str:
    api_key = os.getenv("BFL_API_KEY", "").strip()
    if api_key:
        return api_key

    if key_file.exists():
        raw = key_file.read_text(encoding="utf-8").strip()
        if raw.startswith("BFL_API_KEY="):
            return raw.split("=", 1)[1].strip().strip('"').strip("'")
        return raw

    raise ValueError("Set BFL_API_KEY or create a local flux-api file containing the key.")


def generate_image(*, api_key: str, base_url: str, model: str, prompt: str, width: int, height: int, timeout_seconds: float = TIMEOUT_SECONDS) -> str:
    print(f"[1/3] Submitting generation to {model}...")
    submit_url = f"{base_url.rstrip('/')}/{model}"
    payload = {
        "prompt": prompt,
        "width": width,
        "height": height,
        "prompt_upsampling": False,
        "output_format": "png",
    }
    submit_data = request_json(
        submit_url,
        api_key=api_key,
        method="POST",
        payload=payload,
    )
    polling_url = submit_data.get("polling_url")
    task_id = submit_data.get("id")
    if not polling_url and not task_id:
        raise RuntimeError(f"BFL response did not include polling_url or task id: {submit_data}")

    print(f"[2/3] Waiting for task {task_id or polling_url}...")
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        status_data = poll_result(api_key=api_key, base_url=base_url, polling_url=str(polling_url) if polling_url else None, task_id=str(task_id) if task_id else None)
        status = status_data.get("status")

        if status == "Ready":
            image_url = status_data.get("result", {}).get("sample")
            if not image_url:
                raise RuntimeError(f"BFL result was ready but had no sample URL: {status_data}")
            print(f"Ready: {image_url}")
            return str(image_url)

        if status in {"Failed", "Error"}:
            raise RuntimeError(f"BFL task failed: {status_data}")

        time.sleep(POLL_INTERVAL_SECONDS)

    raise TimeoutError(f"BFL task did not finish within {timeout_seconds:g} seconds")


def poll_result(*, api_key: str, base_url: str, polling_url: str | None, task_id: str | None) -> dict[str, Any]:
    if polling_url:
        return request_json(polling_url, api_key=api_key)
    if not task_id:
        raise RuntimeError("Cannot poll BFL result without polling_url or task_id")
    return request_json(f"{base_url.rstrip('/')}/get_result?id={task_id}", api_key=api_key)


def download_image(image_url: str, output_dir: Path, monster_name: str) -> Path:
    print("[3/3] Downloading image...")
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / f"{slugify(monster_name)}.png"

    request = Request(image_url, headers={"User-Agent": "dnd-board-flux-test/0.1"})
    try:
        with urlopen(request, timeout=30) as response:
            target.write_bytes(response.read())
    except (HTTPError, URLError) as error:
        raise RuntimeError(f"Failed to download generated image: {error}") from error

    return target


def request_json(url: str, *, api_key: str, method: str = "GET", payload: dict[str, Any] | None = None) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(
        url,
        data=body,
        method=method,
        headers={
            "X-Key": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "dnd-board-flux-test/0.1",
        },
    )
    try:
        with urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"BFL request failed with {error.code}: {details}") from error
    except (URLError, json.JSONDecodeError) as error:
        raise RuntimeError(f"BFL request failed: {error}") from error

    if not isinstance(data, dict):
        raise RuntimeError(f"BFL response was not a JSON object: {data}")
    return data


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
    return slug.strip("-") or "monster"


if __name__ == "__main__":
    main()
