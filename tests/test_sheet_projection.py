from dataclasses import replace

from dnd_board.application.sheet_projection import SpellControlKind, spell_control_projection
from dnd_board.character_sheet import (
    AbilityScores,
    AbilityType,
    AttackAction,
    CharacterClassLevel,
    ClassType,
    DamageType,
    DiceType,
    EquipmentItem,
    EquipmentSlot,
    EquipmentType,
    PartyMember,
    PartyMemberSheet,
    SpellId,
    TokenKind,
    build_character_sheet,
)
from dnd_board.rules.spells import wizard_spell_entry


def test_magic_missile_projection_exposes_upcast_instance_counts() -> None:
    spell = wizard_spell_entry(SpellId.MAGIC_MISSILE)
    assert spell is not None
    sheet = wizard_sheet(3, [spell])

    controls = spell_control_projection(sheet, sheet.spells[0])

    assert controls.requiresSpellSlot is False
    assert [option.slotLevel for option in controls.castOptions] == [1, 2]
    assert [option.actions[0].instanceCount for option in controls.castOptions] == [3, 4]
    assert controls.castOptions[0].actions[0].kind == SpellControlKind.DAMAGE
    assert controls.castOptions[0].actions[0].label == "Dart"


def test_automatic_spell_slot_cost_is_part_of_projection() -> None:
    spell = wizard_spell_entry(SpellId.BURNING_HANDS)
    assert spell is not None
    sheet = wizard_sheet(1, [spell])

    controls = spell_control_projection(sheet, sheet.spells[0])

    assert controls.requiresSpellSlot is True
    assert [option.slotLevel for option in controls.castOptions] == [1]
    assert controls.castOptions[0].actions[0].kind == SpellControlKind.DAMAGE


def test_true_strike_projection_uses_weapon_name_for_wielded_weapon_controls() -> None:
    spell = wizard_spell_entry(SpellId.TRUE_STRIKE)
    assert spell is not None
    longsword = AttackAction(
        "longsword",
        "Longsword",
        AbilityType.STRENGTH,
        1,
        DiceType.D8,
        damageType=DamageType.SLASHING,
    )
    sheet = replace(
        wizard_sheet(5, [spell]),
        attacks=[longsword],
        equipment=[
            EquipmentItem(
                id="longsword",
                name="Longsword",
                itemType=EquipmentType.WEAPON,
                slot=EquipmentSlot.MAIN_HAND,
            ),
        ],
    )

    controls = spell_control_projection(sheet, sheet.spells[0])

    assert [control.label for control in controls.actions] == ["Cast Longsword"]
    assert controls.actions[0].kind == SpellControlKind.BOUND_WEAPON_ATTACK
    assert [choice.label for choice in controls.actions[0].choices] == ["Normal", "Radiant"]


def wizard_sheet(level: int, spells):
    return build_character_sheet(
        token_id="wizard",
        kind=TokenKind.CHARACTER,
        name="Wizard",
        owner="player-1",
        avatar_url=None,
        party_member=PartyMember(
            id="wizard",
            name="Wizard",
            owner="player-1",
            avatarUrl=None,
            maxHp=20,
            abilityScores=AbilityScores(8, 14, 14, 16, 10, 10),
            sheet=PartyMemberSheet(
                classes=[CharacterClassLevel(ClassType.WIZARD, level)],
                spells=spells,
            ),
        ),
        current_hp=None,
        resource_overrides={},
    )
