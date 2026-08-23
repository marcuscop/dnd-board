from __future__ import annotations

import argparse
import json
import re
import time
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen


BASE_URL = "https://www.dndbeyond.com/monsters"
DEFAULT_OUTPUT_PATH = Path("shared/dndbeyond_monster_names.json")
DEFAULT_FIRST_PAGE = 1
DEFAULT_LAST_PAGE = 179
DEFAULT_DELAY_SECONDS = 0.2
USER_AGENT = "Mozilla/5.0 dnd-board-monster-names/0.1"
MONSTER_DETAIL_HREF_RE = re.compile(r"^/monsters/\d+-[a-z0-9-]+$")


class DndBeyondMonsterNameParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.names: list[str] = []
        self._current_href: str | None = None
        self._current_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return

        href = dict(attrs).get("href")
        if not href or not is_monster_detail_href(href):
            return

        self._current_href = href
        self._current_text = []

    def handle_data(self, data: str) -> None:
        if self._current_href:
            self._current_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag != "a" or not self._current_href:
            return

        name = " ".join("".join(self._current_text).split())
        if name:
            self.names.append(name)

        self._current_href = None
        self._current_text = []


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a JSON file containing D&D Beyond monster names.")
    parser.add_argument("--base-url", default=BASE_URL)
    parser.add_argument("--first-page", type=int, default=DEFAULT_FIRST_PAGE)
    parser.add_argument("--last-page", type=int, default=DEFAULT_LAST_PAGE)
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY_SECONDS)
    parser.add_argument("--source-file", type=Path, help="Parse one local HTML file instead of fetching pages.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    args = parser.parse_args()

    if args.source_file:
        names = parse_monster_names(args.source_file.read_text(encoding="utf-8"))
    else:
        names = fetch_monster_names(
            base_url=args.base_url,
            first_page=args.first_page,
            last_page=args.last_page,
            delay_seconds=args.delay,
        )

    write_names(args.output, names)
    print(f"Saved {len(names)} monster names: {args.output}")


def fetch_monster_names(*, base_url: str, first_page: int, last_page: int, delay_seconds: float) -> list[str]:
    if first_page < 1:
        raise ValueError("first_page must be 1 or greater.")
    if last_page < first_page:
        raise ValueError("last_page must be greater than or equal to first_page.")

    names: list[str] = []
    seen: set[str] = set()

    for page in range(first_page, last_page + 1):
        url = build_page_url(base_url, page)
        html = fetch_html(url)
        page_names = parse_monster_names(html)
        if not page_names:
            raise RuntimeError(f"No monster names found on page {page}: {url}")

        for name in page_names:
            if name in seen:
                continue
            seen.add(name)
            names.append(name)

        print(f"Page {page}: {len(page_names)} names, {len(names)} total")
        if delay_seconds > 0 and page < last_page:
            time.sleep(delay_seconds)

    return names


def build_page_url(base_url: str, page: int) -> str:
    return f"{base_url}?page={page}"


def fetch_html(url: str) -> str:
    request = Request(urljoin(BASE_URL, url), headers={"Accept": "text/html", "User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=30) as response:
            return response.read().decode("utf-8", errors="replace")
    except HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Failed to fetch {url} with {error.code}: {details[:300]}") from error
    except URLError as error:
        raise RuntimeError(f"Failed to fetch {url}: {error}") from error


def parse_monster_names(html: str) -> list[str]:
    parser = DndBeyondMonsterNameParser()
    parser.feed(html)
    return dedupe_names(parser.names)


def dedupe_names(names: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for name in names:
        clean_name = " ".join(name.split())
        if not clean_name or clean_name in seen:
            continue
        seen.add(clean_name)
        deduped.append(clean_name)
    return deduped


def is_monster_detail_href(href: str) -> bool:
    return bool(MONSTER_DETAIL_HREF_RE.match(href))


def write_names(path: Path, names: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(names, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
