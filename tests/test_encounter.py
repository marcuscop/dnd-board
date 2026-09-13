import json
from dataclasses import replace

from fastapi.testclient import TestClient

from dnd_board import server
from dnd_board.application.resource_service import payable_resource_costs
from dnd_board.character_sheet import (
    ActivationTiming,
    AbilityScores,
    AbilityType,
    AttackAction,
    CharacterClassLevel,
    ClassType,
    DamageType,
    DiceType,
    PartyManifest,
    PartyMemberConfig,
    PartyMemberSheet,
    ResourceTracker,
    TimeEconomy,
    typed_json_from_value,
)
from dnd_board.rules.encounter import (
    ActionAllowance,
    ActionCategory,
    ActivationKey,
    ActivationKind,
    AllowanceExpiration,
    AllowanceSource,
    EncounterParticipant,
    EncounterStatus,
    authorize_activation,
    grant_action_allowance,
    participant_state,
    participant_state_after_turn_start,
    synchronize_participant_capacities,
    interaction_usage_allowed,
    record_interaction_usage,
    spend_activation,
    start_encounter_state,
    transition_encounter,
)
from dnd_board.rules.shared.resources import (
    ResourceCost,
    ResourceId,
    ResourceKind,
    ResourcePaymentScope,
)
from dnd_board.rules.shared.effects import (
    ActiveScheduledEffect,
    ApplyEffectOperation,
    ApplyEffect,
    ActiveOngoingEffect,
    DamageEffect,
    EffectDuration,
    EffectDurationType,
    EffectNodeId,
    OngoingEffect,
    OngoingEffectId,
    FixedAmount,
    Interaction,
    InteractionDecision,
    InteractionDecisionType,
    InteractionTiming,
    PromptResponder,
    ResolutionEventType,
    ScheduledEffect,
    ScheduledEffectId,
    ongoing_effects_after_turn_boundary,
)
from dnd_board.rules.encounter import TurnBoundary, TurnParticipantReference, TurnTiming, UsageScope


def setup_function() -> None:
    server.rooms.clear()


def test_turn_resources_recover_and_reactions_work_off_turn() -> None:
    encounter = start_encounter_state(
        "encounter-1",
        "turn-1",
        (EncounterParticipant("a", 18), EncounterParticipant("b", 12)),
    )

    action = authorize_activation(encounter, "a", TimeEconomy.ACTION, ActionCategory.ATTACK)
    reaction = authorize_activation(encounter, "b", TimeEconomy.REACTION, ActionCategory.FEATURE)
    off_turn_action = authorize_activation(encounter, "b", TimeEconomy.ACTION, ActionCategory.ATTACK)

    assert action.allowed
    assert reaction.allowed
    assert not off_turn_action.allowed

    attack_key = ActivationKey(ActivationKind.ATTACK_ACTION, "attack")
    spent = spend_activation(
        encounter, "a", action, activation_instances=2, activation_key=attack_key
    )
    second_attack = authorize_activation(
        spent,
        "a",
        TimeEconomy.ACTION,
        ActionCategory.ATTACK,
        activation_key=attack_key,
    )
    assert second_attack.allowed
    assert second_attack.activeAction is not None
    assert not authorize_activation(spent, "a", TimeEconomy.ACTION, ActionCategory.MAGIC).allowed
    spent = spend_activation(spent, "a", second_attack)
    assert not authorize_activation(
        spent,
        "a",
        TimeEconomy.ACTION,
        ActionCategory.ATTACK,
        activation_key=attack_key,
    ).allowed

    advanced = transition_encounter(spent, "turn-2")
    assert advanced.currentParticipantId == "b"
    assert participant_state(advanced, "b").resources[0].current == 1


def test_restricted_allowance_only_authorizes_its_action_category() -> None:
    encounter = start_encounter_state("encounter-1", "turn-1", (EncounterParticipant("a", 10),))
    base_action = authorize_activation(encounter, "a", TimeEconomy.ACTION, ActionCategory.ATTACK)
    spent = spend_activation(encounter, "a", base_action)
    participant = participant_state(spent, "a")
    allowance = ActionAllowance(
        ResourceId.ACTION,
        1,
        AllowanceSource(ResourceId.ACTION_SURGE),
        (ActionCategory.ATTACK,),
    )
    spent = replace(
        spent,
        participantStates=(replace(participant, allowances=(allowance,)),),
    )

    assert authorize_activation(spent, "a", TimeEconomy.ACTION, ActionCategory.ATTACK).allowed
    assert not authorize_activation(spent, "a", TimeEconomy.ACTION, ActionCategory.MAGIC).allowed


def test_multipart_activation_is_scoped_and_special_timing_is_independent_of_cost() -> None:
    encounter = start_encounter_state(
        "encounter-1",
        "turn-1",
        (EncounterParticipant("a", 18), EncounterParticipant("b", 12)),
    )
    first_spell = ActivationKey(ActivationKind.SPELL, "magicMissile", "0:1:0")
    other_spell = ActivationKey(ActivationKind.SPELL, "scorchingRay", "0:2:0")
    authorization = authorize_activation(
        encounter,
        "a",
        TimeEconomy.ACTION,
        ActionCategory.MAGIC,
        activation_key=first_spell,
    )
    spent = spend_activation(
        encounter,
        "a",
        authorization,
        activation_instances=3,
        activation_key=first_spell,
        part_id=0,
    )

    continuation = authorize_activation(
        spent,
        "a",
        TimeEconomy.ACTION,
        ActionCategory.MAGIC,
        activation_key=first_spell,
        part_id=1,
    )
    assert continuation.allowed
    assert continuation.activeAction is not None
    after_second_part = spend_activation(
        spent,
        "a",
        continuation,
        activation_key=first_spell,
        part_id=1,
    )
    assert not authorize_activation(
        after_second_part,
        "a",
        TimeEconomy.ACTION,
        ActionCategory.MAGIC,
        activation_key=first_spell,
        part_id=1,
    ).allowed
    assert authorize_activation(
        after_second_part,
        "a",
        TimeEconomy.ACTION,
        ActionCategory.MAGIC,
        activation_key=first_spell,
        part_id=2,
    ).allowed
    assert not authorize_activation(
        spent,
        "a",
        TimeEconomy.ACTION,
        ActionCategory.MAGIC,
        activation_key=other_spell,
    ).allowed
    assert not authorize_activation(
        encounter,
        "b",
        TimeEconomy.SPECIAL,
        ActionCategory.FEATURE,
        timing=ActivationTiming.OWN_TURN,
    ).allowed


def test_continuation_pays_per_part_costs_but_not_activation_costs() -> None:
    spell_slot = ResourceCost(ResourceId.SPELL_SLOT)
    arrow = ResourceCost(
        ResourceId.ARROWS,
        paymentScope=ResourcePaymentScope.PART,
    )

    assert payable_resource_costs(
        (spell_slot, arrow), continuation=False
    ) == (spell_slot, arrow)
    assert payable_resource_costs(
        (spell_slot, arrow), continuation=True
    ) == (arrow,)


def test_resolution_reactions_are_allowed_during_turn_transition() -> None:
    encounter = replace(
        start_encounter_state("encounter-1", "turn-1", (EncounterParticipant("a", 10),)),
        status=EncounterStatus.TRANSITIONING,
    )

    ordinary = authorize_activation(
        encounter, "a", TimeEconomy.REACTION, ActionCategory.FEATURE
    )
    response = authorize_activation(
        encounter,
        "a",
        TimeEconomy.REACTION,
        ActionCategory.FEATURE,
        resolution_response=True,
    )

    assert not ordinary.allowed
    assert response.allowed


def test_interaction_usage_scope_is_enforced_and_recovers() -> None:
    encounter = start_encounter_state(
        "encounter-1",
        "turn-1",
        (EncounterParticipant("a", 18), EncounterParticipant("b", 12)),
    )
    assert interaction_usage_allowed(
        encounter, "a", ResourceId.INDOMITABLE, UsageScope.ONCE_PER_ROUND
    )
    used = record_interaction_usage(
        encounter, "a", ResourceId.INDOMITABLE, UsageScope.ONCE_PER_ROUND
    )
    assert not interaction_usage_allowed(
        used, "a", ResourceId.INDOMITABLE, UsageScope.ONCE_PER_ROUND
    )
    next_turn = transition_encounter(used, "turn-2")
    next_round = transition_encounter(next_turn, "turn-3")
    assert interaction_usage_allowed(
        next_round, "a", ResourceId.INDOMITABLE, UsageScope.ONCE_PER_ROUND
    )


def test_shared_turn_start_bookkeeping_expires_allowances_and_usage() -> None:
    encounter = start_encounter_state(
        "encounter-1", "turn-1", (EncounterParticipant("a", 10),)
    )
    participant = replace(
        participant_state(encounter, "a"),
        allowances=(
            ActionAllowance(
                ResourceId.ACTION,
                1,
                AllowanceSource(ResourceId.ACTION_SURGE),
                expires=AllowanceExpiration.TURN_START,
            ),
        ),
    )
    encounter = replace(encounter, participantStates=(participant,))
    encounter = record_interaction_usage(
        encounter, "a", ResourceId.INDOMITABLE, UsageScope.UNTIL_NEXT_TURN
    )

    started = participant_state_after_turn_start(
        participant_state(encounter, "a"),
        round_number=1,
    )

    assert started.allowances == ()
    assert started.interactionUsages == ()


def test_capacity_recalculation_does_not_refill_but_turn_start_does() -> None:
    encounter = start_encounter_state(
        "encounter-1", "turn-1", (EncounterParticipant("a", 10),)
    )
    action = authorize_activation(
        encounter, "a", TimeEconomy.ACTION, ActionCategory.ATTACK
    )
    spent = spend_activation(encounter, "a", action)
    expanded = synchronize_participant_capacities(
        spent,
        "a",
        {
            ResourceId.ACTION: 2,
            ResourceId.BONUS_ACTION: 1,
            ResourceId.REACTION: 1,
        },
    )
    expanded_action = next(
        resource
        for resource in participant_state(expanded, "a").resources
        if resource.resource == ResourceId.ACTION
    )
    started = participant_state_after_turn_start(
        participant_state(expanded, "a"),
        round_number=1,
    )
    recovered_action = next(
        resource for resource in started.resources
        if resource.resource == ResourceId.ACTION
    )

    assert (expanded_action.current, expanded_action.maximum) == (0, 2)
    assert (recovered_action.current, recovered_action.maximum) == (2, 2)


def test_ongoing_effect_duration_uses_typed_turn_anchor_and_occurrence_count() -> None:
    active = ActiveOngoingEffect(
        id=OngoingEffectId(1, EffectNodeId(())),
        sourceSheetId="caster",
        targetSheetId="target",
        ownerSheetId="owner",
        sourceLabel="Ward",
        effect=OngoingEffect(EffectDuration(
            EffectDurationType.UNTIL_END_OF_TURN,
            timing=TurnTiming(TurnParticipantReference.OWNER, TurnBoundary.END, count=2),
        )),
    )

    unchanged = ongoing_effects_after_turn_boundary([active], "target", TurnBoundary.END)
    after_first = ongoing_effects_after_turn_boundary(unchanged, "owner", TurnBoundary.END)
    expired = ongoing_effects_after_turn_boundary(after_first, "owner", TurnBoundary.END)

    assert unchanged == [active]
    assert after_first[0].effect.duration.timing is not None
    assert after_first[0].effect.duration.timing.count == 1
    assert expired == []


def test_next_turn_timing_does_not_expire_on_installing_turn_boundary() -> None:
    active = ActiveOngoingEffect(
        id=OngoingEffectId(1, EffectNodeId(())),
        sourceSheetId="caster",
        targetSheetId="target",
        ownerSheetId="caster",
        sourceLabel="Ward",
        effect=OngoingEffect(EffectDuration(
            EffectDurationType.UNTIL_END_OF_TURN,
            timing=TurnTiming(
                TurnParticipantReference.OWNER,
                TurnBoundary.END,
            ),
        )),
        installedTurnId="turn-1",
    )

    same_turn = ongoing_effects_after_turn_boundary(
        [active], "caster", TurnBoundary.END, "turn-1"
    )
    next_turn = ongoing_effects_after_turn_boundary(
        same_turn, "caster", TurnBoundary.END, "turn-2"
    )

    assert same_turn == [active]
    assert next_turn == []


def test_encounter_endpoints_enforce_turns_and_persist(tmp_path, monkeypatch) -> None:
    campaign_id = "encounter-flow-test"
    campaign = tmp_path / campaign_id
    party = campaign / "party"
    party.mkdir(parents=True)
    (campaign / "campaign.json").write_text(json.dumps({"id": campaign_id, "name": "Encounter"}), encoding="utf-8")
    attack = AttackAction(
        id="sword",
        name="Sword",
        ability=AbilityType.STRENGTH,
        damageDiceCount=1,
        damageDiceType=DiceType.D8,
        damageType=DamageType.SLASHING,
        resourceCosts=(
            ResourceCost(
                ResourceId.ARROWS,
                paymentScope=ResourcePaymentScope.PART,
            ),
        ),
    )
    members = [
        PartyMemberConfig(
            id=f"player-{index}",
            name=name,
            maxHp=20,
            abilityScores=AbilityScores(16, 12, 14, 10, 10, 10),
            sheet=PartyMemberSheet(
                classes=[CharacterClassLevel(ClassType.FIGHTER, 2 if index == 1 else 5)],
                attacks=[attack],
                resources=[
                    ResourceTracker(
                        "arrows",
                        "Arrows",
                        3 if index == 1 else 2,
                        3 if index == 1 else 2,
                        TimeEconomy.SPECIAL,
                        "Ammunition.",
                        resource=ResourceId.ARROWS,
                        kind=ResourceKind.AMMUNITION,
                    ),
                ],
            ),
        )
        for index, name in ((1, "Alice"), (2, "Bob"))
    ]
    (party / "party.json").write_text(
        json.dumps(typed_json_from_value(PartyManifest(members))),
        encoding="utf-8",
    )
    monkeypatch.setattr(server, "CAMPAIGN_DIR", tmp_path)
    monkeypatch.setattr(server, "SAVE_DIR", tmp_path / "runtime-saves")
    monkeypatch.setattr(server, "LEGACY_SAVE_DIR", tmp_path / "legacy-saves")
    client = TestClient(server.app)

    started = client.post(
        f"/api/rooms/{campaign_id}/encounter?playerKey=dm",
        json=[
            {"participantId": "player-1", "initiative": 18},
            {"participantId": "player-2", "initiative": 12},
        ],
    )
    assert started.status_code == 200
    encounter = started.json()["encounter"]
    turn_id = encounter["turnId"]
    assert encounter["currentParticipantId"] == "player-1"

    off_turn = client.post(
        f"/api/rooms/{campaign_id}/sheet/player-2/rolls/attack?playerKey=dm&attackId=sword&turnId={turn_id}"
    )
    assert off_turn.status_code == 409

    first = client.post(
        f"/api/rooms/{campaign_id}/sheet/player-1/rolls/attack?playerKey=player-1&attackId=sword&turnId={turn_id}"
    )
    assert first.status_code == 200
    assert any(entry["resource"] == "action" for entry in first.json()["roll"]["resourcesSpent"])

    second = client.post(
        f"/api/rooms/{campaign_id}/sheet/player-1/rolls/attack?playerKey=player-1&attackId=sword&turnId={turn_id}"
    )
    assert second.status_code == 409

    room = server.rooms[campaign_id]
    room.encounter = grant_action_allowance(
        room.encounter,
        "player-1",
        ActionAllowance(
            ResourceId.ACTION,
            1,
            AllowanceSource(ResourceId.ACTION_SURGE),
        ),
    )
    surged_attack = client.post(
        f"/api/rooms/{campaign_id}/sheet/player-1/rolls/attack?playerKey=player-1&attackId=sword&turnId={turn_id}"
    )
    assert surged_attack.status_code == 200
    exhausted_action = client.post(
        f"/api/rooms/{campaign_id}/sheet/player-1/rolls/attack?playerKey=player-1&attackId=sword&turnId={turn_id}"
    )
    assert exhausted_action.status_code == 409

    damage = client.post(
        f"/api/rooms/{campaign_id}/sheet/player-1/rolls/damage?playerKey=player-1&attackId=sword&turnId={turn_id}"
    )
    assert damage.status_code == 200
    client.post(f"/api/rooms/{campaign_id}/sheet/player-1/rolls/clear?playerKey=player-1")
    room.scheduled_effects["player-1"] = [ActiveScheduledEffect(
        id=ScheduledEffectId(2, EffectNodeId(())),
        sourceSheetId="player-1",
        targetSheetId="player-1",
        sourceLabel="Turn-End Hazard",
        effect=ScheduledEffect(
            ResolutionEventType.TURN_ENDED,
            ApplyEffect(DamageEffect(FixedAmount(2), DamageType.FIRE)),
        ),
        remainingOccurrences=1,
    )]
    room.ongoing_effects["player-1"] = [ActiveOngoingEffect(
        id=OngoingEffectId(3, EffectNodeId(())),
        sourceSheetId="player-1",
        targetSheetId="player-1",
        ownerSheetId="player-1",
        sourceLabel="Turn-End Choice",
        effect=OngoingEffect(
            EffectDuration(EffectDurationType.MANUAL),
            interactions=[Interaction(
                trigger=ResolutionEventType.TURN_ENDED,
                timing=InteractionTiming.BEFORE_EVENT,
                decision=InteractionDecision(
                    InteractionDecisionType.PROMPT,
                    PromptResponder.OWNER_OR_DM,
                ),
                operations=[ApplyEffectOperation(
                    ApplyEffect(DamageEffect(FixedAmount(1), DamageType.COLD)),
                )],
            )],
        ),
    )]

    advanced = client.post(
        f"/api/rooms/{campaign_id}/encounter/advance?playerKey=player-1&turnId={turn_id}"
    )
    assert advanced.status_code == 200
    assert advanced.json()["encounter"]["status"] == "transitioning"
    assert advanced.json()["encounter"]["currentParticipantId"] == "player-1"
    prompt_id = next(iter(room.pending_resolution_prompts))
    prompt_response = client.post(
        f"/api/rooms/{campaign_id}/resolution-prompts/{prompt_id}/respond"
        "?playerKey=player-1&use=true"
    )
    assert prompt_response.status_code == 200
    assert room.encounter is not None
    next_turn_id = room.encounter.turnId
    assert next_turn_id != turn_id
    assert room.encounter.currentParticipantId == "player-2"
    assert room.encounter.status.value == "active"
    assert room.hit_points["player-1"] == 17
    assert room.scheduled_effects.get("player-1") is None

    stale = client.post(
        f"/api/rooms/{campaign_id}/sheet/player-2/rolls/attack?playerKey=player-2&attackId=sword&turnId={turn_id}"
    )
    assert stale.status_code == 409
    current = client.post(
        f"/api/rooms/{campaign_id}/sheet/player-2/rolls/attack?playerKey=player-2&attackId=sword&turnId={next_turn_id}"
    )
    assert current.status_code == 200
    extra_attack = client.post(
        f"/api/rooms/{campaign_id}/sheet/player-2/rolls/attack?playerKey=player-2&attackId=sword&turnId={next_turn_id}"
    )
    assert extra_attack.status_code == 200
    assert room.resource_uses["player-2"]["arrows"] == 0
    no_third_attack = client.post(
        f"/api/rooms/{campaign_id}/sheet/player-2/rolls/attack?playerKey=player-2&attackId=sword&turnId={next_turn_id}"
    )
    assert no_third_attack.status_code == 409

    saved = json.loads((tmp_path / "runtime-saves" / f"{campaign_id}.json").read_text(encoding="utf-8"))
    assert "encounter" not in saved

    player_one_state = participant_state(room.encounter, "player-1")
    room.encounter = replace(
        room.encounter,
        participantStates=tuple(
            replace(
                participant,
                allowances=(
                    ActionAllowance(
                        ResourceId.ACTION,
                        1,
                        AllowanceSource(ResourceId.ACTION_SURGE),
                        expires=AllowanceExpiration.TURN_START,
                    ),
                ),
                interactionUsages=(
                    record_interaction_usage(
                        replace(room.encounter, participantStates=(player_one_state,)),
                        "player-1",
                        ResourceId.INDOMITABLE,
                        UsageScope.UNTIL_NEXT_TURN,
                    ).participantStates[0].interactionUsages
                ),
            )
            if participant.participantId == "player-1"
            else participant
            for participant in room.encounter.participantStates
        ),
    )
    removed_current = client.put(
        f"/api/rooms/{campaign_id}/encounter?playerKey=dm",
        json=[{"participantId": "player-1", "initiative": 18}],
    )
    assert removed_current.status_code == 200
    replacement = participant_state(room.encounter, "player-1")
    assert replacement.allowances == ()
    assert replacement.interactionUsages == ()
    excluded = client.post(
        f"/api/rooms/{campaign_id}/sheet/player-2/rolls/attack"
        f"?playerKey=dm&attackId=sword&turnId={room.encounter.turnId}"
    )
    assert excluded.status_code == 409
    assert excluded.json()["detail"] == "This character is not participating in the encounter"


def test_only_dm_can_start_or_end_encounter(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(server, "CAMPAIGN_DIR", tmp_path)
    client = TestClient(server.app)
    response = client.post(
        "/api/rooms/empty-encounter/encounter?playerKey=player-1",
        json=[{"participantId": "player-1", "initiative": 10}],
    )
    assert response.status_code == 403
