"""Seed the dev-only sandbox campaign used by scripts/dev-sandbox.sh.

Populates campaigns/test-campaign-sandbox/ with three level-1 party members
(a Fighter, a Rogue, and a Wizard) built entirely through the existing
character builder and campaign repository code -- no hand-written
party.json content. A fourth slot (player-4) is deliberately left empty so
its /sheet URL shows the in-app character builder panel.

Board and party portrait images are copied read-only from the real
campaigns/test-campaign/ folder, since nothing else can source them. That
folder is never deleted and never written to by this script.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SANDBOX_CAMPAIGN_ID = "test-campaign-sandbox"
SANDBOX_DIR = REPO_ROOT / "campaigns" / SANDBOX_CAMPAIGN_ID
SOURCE_CAMPAIGN_DIR = REPO_ROOT / "campaigns" / "test-campaign"

sys.path.insert(0, str(REPO_ROOT))

from dnd_board.application.campaign_repository import CampaignPaths, save_party_member  # noqa: E402
from dnd_board.character_builder import (  # noqa: E402
    CharacterBuilderPayloadField,
    build_party_member_config,
    character_builder_request_from_payload,
    payload_key,
)
from dnd_board.character_sheet import AbilityType, ClassType, enum_key  # noqa: E402
from dnd_board.rules.backgrounds import BackgroundType, background_definition  # noqa: E402

MAX_PLAYERS = 8
DEFAULT_BACKGROUND = BackgroundType.WAYFARER


def assert_sandbox_path(path: Path) -> None:
    """Defense in depth: refuse to write anywhere but the sandbox folder."""
    if path.parent.name != "campaigns" or path.name != SANDBOX_CAMPAIGN_ID:
        raise RuntimeError(f"Refusing to write outside the sandbox folder: {path}")


def campaign_paths() -> CampaignPaths:
    return CampaignPaths(
        campaign_dir=REPO_ROOT / "campaigns",
        legacy_save_dir=SANDBOX_DIR / "saves",
        save_dir=SANDBOX_DIR / "saves",
        default_campaign_id=SANDBOX_CAMPAIGN_ID,
        max_players=MAX_PLAYERS,
    )


def ability_scores_payload(order: list[AbilityType]) -> dict[str, int]:
    standard_array = (15, 14, 13, 12, 10, 8)
    return {enum_key(ability): score for ability, score in zip(order, standard_array)}


def background_ability_increases_payload() -> dict[str, int]:
    """+1/+1/+1 across whichever abilities the default background allows."""
    options = background_definition(DEFAULT_BACKGROUND).abilityScores or tuple(AbilityType)
    return {enum_key(ability): 1 for ability in options[:3]}


def seed_payload(member_id: str, name: str, class_type: ClassType, ability_order: list[AbilityType]) -> dict:
    return {
        payload_key(CharacterBuilderPayloadField.MEMBER_ID): member_id,
        payload_key(CharacterBuilderPayloadField.NAME): name,
        payload_key(CharacterBuilderPayloadField.OWNER): member_id,
        payload_key(CharacterBuilderPayloadField.CLASS_NAME): enum_key(class_type),
        payload_key(CharacterBuilderPayloadField.BASE_ABILITY_SCORES): ability_scores_payload(ability_order),
        payload_key(CharacterBuilderPayloadField.BACKGROUND_ABILITY_INCREASES): background_ability_increases_payload(),
    }


SEED_CHARACTERS = [
    seed_payload(
        "player-1",
        "Test Fighter",
        ClassType.FIGHTER,
        [AbilityType.STRENGTH, AbilityType.CONSTITUTION, AbilityType.DEXTERITY, AbilityType.WISDOM, AbilityType.CHARISMA, AbilityType.INTELLIGENCE],
    ),
    seed_payload(
        "player-2",
        "Test Rogue",
        ClassType.ROGUE,
        [AbilityType.DEXTERITY, AbilityType.CONSTITUTION, AbilityType.WISDOM, AbilityType.INTELLIGENCE, AbilityType.CHARISMA, AbilityType.STRENGTH],
    ),
    seed_payload(
        "player-3",
        "Test Wizard",
        ClassType.WIZARD,
        [AbilityType.INTELLIGENCE, AbilityType.CONSTITUTION, AbilityType.DEXTERITY, AbilityType.WISDOM, AbilityType.CHARISMA, AbilityType.STRENGTH],
    ),
]
# player-4 is intentionally left unseeded -- an empty slot, so its /sheet
# URL shows the character builder panel instead of a character sheet.


def copy_images(source_dir: Path, dest_dir: Path) -> None:
    if not source_dir.is_dir():
        return
    dest_dir.mkdir(parents=True, exist_ok=True)
    image_suffixes = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
    for source_file in source_dir.iterdir():
        if source_file.is_file() and source_file.suffix.lower() in image_suffixes:
            shutil.copy2(source_file, dest_dir / source_file.name)


def main() -> None:
    assert_sandbox_path(SANDBOX_DIR)

    copy_images(SOURCE_CAMPAIGN_DIR / "boards", SANDBOX_DIR / "boards")
    copy_images(SOURCE_CAMPAIGN_DIR / "party", SANDBOX_DIR / "party")

    paths = campaign_paths()
    seeded = []
    for payload in SEED_CHARACTERS:
        member_id = payload[payload_key(CharacterBuilderPayloadField.MEMBER_ID)]
        request = character_builder_request_from_payload(payload, default_member_id=member_id, default_owner=member_id)
        member = build_party_member_config(request)
        assert_sandbox_path(SANDBOX_DIR)
        save_party_member(paths, SANDBOX_CAMPAIGN_ID, member)
        level = member.sheet.classes[0].level if member.sheet and member.sheet.classes else 1
        seeded.append(f"{member.name} ({member.id}) - {enum_key(member.sheet.classes[0].name)} level {level}")

    print(f"Seeded sandbox campaign '{SANDBOX_CAMPAIGN_ID}' at {SANDBOX_DIR}")
    for line in seeded:
        print(f"  - {line}")
    print("  - player-4 left empty (no sheet) so its /sheet URL shows the character builder")


if __name__ == "__main__":
    main()
