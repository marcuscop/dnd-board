from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from dnd_board.application.room_state import Campaign
from dnd_board.character_sheet import (
    PartyManifest,
    PartyMemberConfig,
    party_manifest_from_dict,
    sanitize_identifier,
    typed_json_from_value,
)


@dataclass(frozen=True)
class CampaignPaths:
    campaign_dir: Path
    legacy_save_dir: Path
    save_dir: Path
    default_campaign_id: str
    max_players: int


MemberUpdate = Callable[[PartyMemberConfig], None]


def active_campaign(paths: CampaignPaths, campaign_id: str | None = None) -> Campaign:
    requested_id = sanitize_identifier(campaign_id or paths.default_campaign_id)
    campaign = get_campaign(paths, requested_id)
    if campaign is not None:
        return campaign
    default_campaign = get_campaign(paths, paths.default_campaign_id)
    return default_campaign or Campaign(
        id=paths.default_campaign_id,
        name=humanize_name(paths.default_campaign_id),
        path=paths.campaign_dir / paths.default_campaign_id,
    )


def get_campaign(paths: CampaignPaths, campaign_id: str) -> Campaign | None:
    campaign_path = paths.campaign_dir / sanitize_identifier(campaign_id)
    if not campaign_path.exists() or not campaign_path.is_dir():
        return None
    return Campaign(
        id=campaign_path.name,
        name=humanize_name(campaign_path.name),
        path=campaign_path,
    )


def campaign_asset_dir(
    paths: CampaignPaths,
    directory_name: str,
    campaign_id: str | None = None,
) -> Path:
    return active_campaign(paths, campaign_id).path / directory_name


def campaign_save_dir(paths: CampaignPaths, campaign_id: str | None = None) -> Path:
    return active_campaign(paths, campaign_id).path / "saves"


def save_path(paths: CampaignPaths, room_id: str) -> Path:
    if paths.save_dir != paths.legacy_save_dir:
        return paths.save_dir / f"{room_id}.json"
    return campaign_save_dir(paths, room_id) / f"{room_id}.json"


def existing_save_path(paths: CampaignPaths, room_id: str) -> Path:
    campaign_path = save_path(paths, room_id)
    if campaign_path.exists():
        return campaign_path
    return paths.legacy_save_dir / f"{room_id}.json"


def humanize_name(value: str) -> str:
    return value.replace("-", " ").replace("_", " ").title()


def load_party_manifest(path: Path) -> PartyManifest | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return party_manifest_from_dict(data)


def update_party_member(
    paths: CampaignPaths,
    campaign_id: str,
    member_id: str,
    update: MemberUpdate,
) -> PartyMemberConfig | None:
    path = campaign_asset_dir(paths, "party", campaign_id) / "party.json"
    manifest = load_party_manifest(path)
    if manifest is None:
        return None
    target = next(
        (
            member
            for member in manifest.members
            if normalize_party_member_id(paths, member.id, "") == member_id
        ),
        None,
    )
    if target is None:
        return None
    update(target)
    _write_manifest(path, manifest)
    return target


def save_party_member(
    paths: CampaignPaths,
    campaign_id: str,
    member: PartyMemberConfig,
) -> PartyMemberConfig:
    path = writable_party_manifest_path(paths, campaign_id)
    manifest = load_party_manifest(path) or PartyManifest(members=[])
    target = next(
        (
            candidate
            for candidate in manifest.members
            if normalize_party_member_id(paths, candidate.id, "") == member.id
        ),
        None,
    )
    if target is None:
        manifest.members.append(member)
    else:
        manifest.members[manifest.members.index(target)] = member
    _write_manifest(path, manifest)
    return member


def writable_party_manifest_path(paths: CampaignPaths, campaign_id: str) -> Path:
    campaign_path = paths.campaign_dir / sanitize_identifier(campaign_id)
    party_path = campaign_path / "party"
    party_path.mkdir(parents=True, exist_ok=True)
    campaign_config = campaign_path / "campaign.json"
    if not campaign_config.exists():
        campaign_config.write_text(
            json.dumps(
                {"id": campaign_path.name, "name": humanize_name(campaign_path.name)},
                indent=2,
            ),
            encoding="utf-8",
        )
    return party_path / "party.json"


def normalize_party_member_id(
    paths: CampaignPaths,
    value: str,
    fallback: str,
) -> str:
    normalized = sanitize_identifier(value)
    if normalized.startswith("player-"):
        try:
            number = int(normalized.rsplit("-", 1)[1])
        except (IndexError, ValueError):
            return fallback
        if 1 <= number <= paths.max_players:
            return f"player-{number}"
    return fallback


def _write_manifest(path: Path, manifest: PartyManifest) -> None:
    path.write_text(
        json.dumps(typed_json_from_value(manifest), indent=2, sort_keys=False),
        encoding="utf-8",
    )
