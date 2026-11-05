from __future__ import annotations

from uuid import uuid4

from dnd_board.application.room_state import PendingRest, RestGrantPrompt, RestGrantTarget, Room
from dnd_board.character_sheet import CharacterSheet, RestType, TokenKind, enum_key, enum_label
from dnd_board.rules.feats import GENERAL_FEATS, selected_general_feat_types
from dnd_board.rules.rest import HitDieSpend
from dnd_board.rules.shared.resources import ResourceId, ResourceRecoveryTrigger, RestGrantCount, RestGrantRecipient, rest_grant_requirements_met


def prepare_rest(
    sheets: list[CharacterSheet],
    rest_type: RestType,
    initiator_player_key: str,
    hit_dice_by_sheet: dict[str, list[HitDieSpend]],
) -> PendingRest:
    trigger = (
        ResourceRecoveryTrigger.SHORT_REST
        if rest_type == RestType.SHORT_REST
        else ResourceRecoveryTrigger.LONG_REST
    )
    prompts: dict[str, RestGrantPrompt] = {}
    for source in sheets:
        if source.kind != TokenKind.CHARACTER or source.hp.current < 1:
            continue
        for feat in sorted(selected_general_feat_types(source.features), key=enum_key):
            for grant in GENERAL_FEATS[feat].restGrants:
                if trigger not in grant.triggers or not rest_grant_requirements_met(grant, source.proficiencies):
                    continue
                if grant.recipient != RestGrantRecipient.ALLY:
                    raise ValueError("Unsupported rest grant recipient")
                if grant.maximumTargets != RestGrantCount.PROFICIENCY_BONUS:
                    raise ValueError("Unsupported rest grant target count")
                targets = tuple(
                    RestGrantTarget(sheet.id, sheet.name)
                    for sheet in sheets
                    if sheet.id != source.id
                    and sheet.kind == TokenKind.CHARACTER
                    and resource_available(sheet, grant.resource)
                )
                if not targets:
                    continue
                prompt = RestGrantPrompt(
                    id=uuid4().hex,
                    sourceSheetId=source.id,
                    sourceName=source.name,
                    ownerPlayerKey=source.owner,
                    label=f"{enum_label(feat)}: {grant.resource.value}",
                    resource=grant.resource,
                    maximumTargets=min(source.proficiencyBonus, len(targets)),
                    targets=targets,
                )
                prompts[prompt.id] = prompt
    return PendingRest(
        id=uuid4().hex,
        restType=rest_type,
        initiatorPlayerKey=initiator_player_key,
        hitDiceBySheet=hit_dice_by_sheet,
        prompts=prompts,
        choices={prompt_id: None for prompt_id in prompts},
    )


def resource_available(sheet: CharacterSheet, resource_id: ResourceId) -> bool:
    resource = next((item for item in sheet.resources if item.resource == resource_id), None)
    return resource is not None and resource.currentUses < resource.maxUses


def visible_rest_prompts(rest: PendingRest | None, player_key: str, is_dm: bool) -> list[RestGrantPrompt]:
    if rest is None:
        return []
    return [
        prompt for prompt in rest.prompts.values()
        if rest.choices[prompt.id] is None
        and (is_dm or prompt.ownerPlayerKey == player_key)
    ]


def choose_rest_grant(rest: PendingRest, prompt_id: str, target_ids: list[str]) -> None:
    prompt = rest.prompts.get(prompt_id)
    if prompt is None or rest.choices.get(prompt_id) is not None or rest.committing:
        raise ValueError("Rest prompt is no longer available")
    eligible = {target.sheetId for target in prompt.targets}
    selected = tuple(target_ids)
    if len(selected) != len(set(selected)) or len(selected) > prompt.maximumTargets or any(target not in eligible for target in selected):
        raise ValueError("Choose distinct eligible allies within the target limit")
    reserved = {
        target
        for other_id, choice in rest.choices.items()
        if other_id != prompt_id and rest.prompts[other_id].resource == prompt.resource
        for target in choice or ()
    }
    if any(target in reserved for target in selected):
        raise ValueError("An ally has already been chosen for this resource")
    rest.choices[prompt_id] = selected


def rest_ready_to_commit(rest: PendingRest) -> bool:
    return all(choice is not None for choice in rest.choices.values())


def apply_rest_grants(room: Room, rest: PendingRest, sheets: list[CharacterSheet]) -> list[tuple[RestGrantPrompt, str]]:
    by_id = {sheet.id: sheet for sheet in sheets}
    summaries: list[tuple[RestGrantPrompt, str]] = []
    for prompt_id, chosen in rest.choices.items():
        prompt = rest.prompts[prompt_id]
        for target_id in chosen or ():
            target = by_id.get(target_id)
            if target is None or not resource_available(target, prompt.resource):
                continue
            resource = next(item for item in target.resources if item.resource == prompt.resource)
            room.resource_uses.setdefault(target.tokenId, {})[enum_key(prompt.resource)] = min(
                resource.maxUses, resource.currentUses + 1,
            )
            summaries.append((prompt, f"{prompt.sourceName} grants {prompt.resource.value} to {target.name}"))
    return summaries
