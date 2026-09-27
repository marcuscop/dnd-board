from dnd_board.character_sheet import (
    DamageType,
    DiceType,
    RollDamageComponent,
    RollPayload,
    RollResolutionMode,
    RollSource,
    SheetSectionType,
)
from dnd_board.rules.shared.effects import EffectAmountInput, EffectNodeId, EffectResolutionInputs
from dnd_board.rules.shared.proactive_rerolls import reroll_failed_d20, reroll_minimum_damage_die


def test_failed_d20_rerolls_only_the_determining_die() -> None:
    roll = _roll(dice=[4, 12], die="2d20kl1", total=9, modifier=5)

    result = reroll_failed_d20(roll, "Inspiration", lambda _minimum, _maximum: 17)

    assert result is not None
    assert result.roll.dice == [17, 12]
    assert result.roll.total == 17
    assert roll.dice == [4, 12]
    assert "Rerolled 4 to 17" in result.roll.modifierBreakdown[-1].description


def test_minimum_damage_die_updates_component_and_effect_input_without_changing_attack() -> None:
    node = EffectNodeId((0, 1))
    component = RollDamageComponent(DamageType.FIRE, [1, 5], DiceType.D6, "2d6", 2, [], 8, [node])
    roll = _roll(dice=[15], die="d20", total=20, modifier=5)
    roll.resolution = RollResolutionMode.ATTACK_VS_ARMOR_CLASS
    roll.damageComponents = [component]
    roll.effectInputs = EffectResolutionInputs(amounts=[EffectAmountInput(node, 8)])

    result = reroll_minimum_damage_die(roll, "Inspiration", node, lambda _minimum, _maximum: 4)

    assert result is not None
    assert result.roll.total == 20
    assert result.roll.damageComponents[0].dice == [4, 5]
    assert result.roll.damageComponents[0].total == 11
    assert result.roll.effectInputs.amounts[0].amount == 11
    assert roll.damageComponents[0].total == 8


def _roll(*, dice: list[int], die: str, total: int, modifier: int) -> RollPayload:
    return RollPayload(
        id="roll-test",
        sheetId="player-1",
        tokenId="player-1",
        roller="player-1",
        source=RollSource(SheetSectionType.ATTACKS, "attack", "attack"),
        sourceLabel="Attack",
        resolution=RollResolutionMode.ATTACK_VS_ARMOR_CLASS,
        label="Attack",
        iconUrl=None,
        dice=dice,
        diceType=DiceType.D20,
        die=die,
        modifier=modifier,
        modifierBreakdown=[],
        total=total,
        createdAt=1,
    )
