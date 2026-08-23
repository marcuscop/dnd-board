from __future__ import annotations

import json

import pytest

from utils import build_dndbeyond_monster_names as monster_names


def test_parse_monster_names_from_dndbeyond_listing_html():
    html = """
    <div class="row monster-name">
      <span class="name">
        <a class="link" href="/monsters/175311-sire-of-insanity">Sire of Insanity</a>
      </span>
      <span class="source">Guildmasters' Guide to Ravnica</span>
    </div>
    <div class="row monster-name">
      <span class="name">
        <a class="link" href="/monsters/17036-ancient-red-dragon">Ancient Red Dragon</a>
      </span>
    </div>
    """

    assert monster_names.parse_monster_names(html) == ["Sire of Insanity", "Ancient Red Dragon"]


def test_parse_monster_names_ignores_pagination_and_dedupes_names():
    html = """
    <a href="/monsters?page=2">Next</a>
    <a href="/monsters/17036-ancient-red-dragon">Ancient Red Dragon</a>
    <a href="/monsters/17036-ancient-red-dragon">Ancient Red Dragon</a>
    <a href="/classes/fighter">Fighter</a>
    """

    assert monster_names.parse_monster_names(html) == ["Ancient Red Dragon"]


def test_fetch_monster_names_rejects_invalid_range():
    with pytest.raises(ValueError, match="last_page"):
        monster_names.fetch_monster_names(base_url="https://example.test/monsters", first_page=5, last_page=4, delay_seconds=0)


def test_build_page_url():
    assert monster_names.build_page_url("https://www.dndbeyond.com/monsters", 140) == "https://www.dndbeyond.com/monsters?page=140"


def test_write_names_creates_parent_directory(tmp_path):
    target = tmp_path / "shared" / "dndbeyond_monster_names.json"

    monster_names.write_names(target, ["Sire of Insanity", "Ancient Red Dragon"])

    assert json.loads(target.read_text(encoding="utf-8")) == ["Sire of Insanity", "Ancient Red Dragon"]
