from dnd_board.character_sheet import (
    AbilityScores,
    CharacterClassLevel,
    ClassType,
    PartyMember,
    PartyMemberSheet,
    RollResolutionMode,
    RollSource,
    SheetFeature,
    TimeEconomy,
    SheetSectionType,
    TokenKind,
    build_character_sheet,
    build_death_saving_throw_roll_payload,
    build_roll_action_payload,
    enum_key,
    resolve_roll_against_target,
    typed_json_from_value,
    typed_json_to_value,
)
from dnd_board.rules.feats import GENERAL_FEATS, GeneralFeatType, general_feat_feature
from dnd_board.rules.shared.effects import CalculationType, FeatureMechanics, Modifier, ModifierOperation
from dnd_board.rules.shared.resources import (
    RESOURCE_DEFINITIONS,
    ResourceCost,
    ResourceId,
    ResourceRecoveryTrigger,
    ResourceState,
    recover_resources,
    spend_resources,
)


def durable_sheet(*, durable: bool = True, resources=None, classes=None):
    return build_character_sheet(
        token_id="fighter",
        kind=TokenKind.CHARACTER,
        name="Fighter",
        owner="player-1",
        avatar_url=None,
        party_member=PartyMember(
            id="fighter",
            name="Fighter",
            owner="player-1",
            avatarUrl=None,
            maxHp=40,
            abilityScores=AbilityScores(14, 10, 14, 10, 10, 10),
            sheet=PartyMemberSheet(
                classes=classes or [CharacterClassLevel(ClassType.FIGHTER, 4)],
                feats=[general_feat_feature(enum_key(GeneralFeatType.DURABLE))] if durable else None,
                resources=resources,
            ),
        ),
        current_hp=20,
        resource_overrides={},
    )


def test_hit_dice_are_typed_persistent_pools_and_long_rest_restores_all() -> None:
    sheet = durable_sheet(classes=[CharacterClassLevel(ClassType.FIGHTER, 3), CharacterClassLevel(ClassType.WIZARD, 2)])
    dice = {resource.resource: resource for resource in sheet.resources if resource.resource in {ResourceId.HIT_DIE_D10, ResourceId.HIT_DIE_D6}}
    assert dice[ResourceId.HIT_DIE_D10].maxUses == 3
    assert dice[ResourceId.HIT_DIE_D6].maxUses == 2
    assert typed_json_to_value(typed_json_from_value(dice[ResourceId.HIT_DIE_D10])) == dice[ResourceId.HIT_DIE_D10]

    spent = spend_resources(
        [ResourceState(ResourceId.HIT_DIE_D10, 3, 3)],
        [ResourceCost(ResourceId.HIT_DIE_D10)],
    )
    assert spent[0].current == 2
    assert recover_resources(spent, RESOURCE_DEFINITIONS, ResourceRecoveryTrigger.SHORT_REST)[0].current == 2
    assert recover_resources(spent, RESOURCE_DEFINITIONS, ResourceRecoveryTrigger.LONG_REST)[0].current == 3


def test_durable_action_spends_one_hit_die_and_heals_without_constitution(monkeypatch) -> None:
    mechanics = GENERAL_FEATS[GeneralFeatType.DURABLE].mechanics
    assert typed_json_to_value(typed_json_from_value(mechanics)) == mechanics
    sheet = durable_sheet()
    ability = next(ability for ability in sheet.abilities if ability.id == "durable")
    action = ability.rollActions[0]
    assert action.resolution == RollResolutionMode.HEAL_SELF
    assert action.resourceCosts[0].resource == ResourceId.HIT_DIE_D10
    monkeypatch.setattr("dnd_board.character_sheet.random.randint", lambda _minimum, _maximum: 5)
    roll = build_roll_action_payload(
        sheet,
        "player-1",
        RollSource(SheetSectionType.ABILITIES, ability.id, enum_key(action.id)),
        action,
    )
    assert roll.total == 5
    assert resolve_roll_against_target(roll, sheet).targetHp.current == 25


def test_durable_death_save_rolls_with_advantage_and_no_ability_modifier(monkeypatch) -> None:
    dice = iter([3, 17])
    monkeypatch.setattr("dnd_board.character_sheet.random.randint", lambda _minimum, _maximum: next(dice))
    roll = build_death_saving_throw_roll_payload(durable_sheet(), "player-1")
    assert roll.dice == [3, 17]
    assert roll.die == "2d20kh1"
    assert roll.total == 17
    assert any(part.source == "Durable" for part in roll.modifierBreakdown)

    monkeypatch.setattr("dnd_board.character_sheet.random.randint", lambda _minimum, _maximum: 8)
    normal = build_death_saving_throw_roll_payload(durable_sheet(durable=False), "player-1")
    assert normal.dice == [8]
    assert normal.total == 8


def test_death_save_advantage_comes_from_definition_mechanics(monkeypatch) -> None:
    sheet = durable_sheet(durable=False)
    sheet.features.append(SheetFeature(
        id="test-feature",
        name="Test Feature",
        source="Test",
        activation=TimeEconomy.PASSIVE,
        description="",
        mechanics=FeatureMechanics(passiveModifiers=[Modifier(
            CalculationType.DEATH_SAVING_THROW,
            ModifierOperation.ADVANTAGE,
        )]),
    ))
    dice = iter([4, 15])
    monkeypatch.setattr("dnd_board.character_sheet.random.randint", lambda _minimum, _maximum: next(dice))
    roll = build_death_saving_throw_roll_payload(sheet, "player-1")
    assert roll.dice == [4, 15]
    assert roll.total == 15
    assert any(part.source == "Test Feature" for part in roll.modifierBreakdown)
