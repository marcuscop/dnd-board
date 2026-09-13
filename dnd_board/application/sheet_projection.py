from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from dnd_board.character_sheet import (
    CharacterSheet,
    DamageType,
    SpellEntry,
    enum_label,
    serialize_dataclass,
)
from dnd_board.rules.shared.character_effects import (
    activated_effect_label,
    activated_effect_node,
    first_applied_effect,
    first_attack_roll_effect,
    scaled_instance_count,
)
from dnd_board.rules.shared.effects import (
    ActivatedEffect,
    ApplyEffect,
    AttackRollEffect,
    ChoiceEffect,
    ConditionalEffect,
    ConditionChangeEffect,
    ContestedCheckEffect,
    DamageEffect,
    EffectNode,
    HealingEffect,
    RepeatedEffect,
    SavingThrowEffect,
    ScalingBasis,
    SequenceEffect,
    TemporaryHitPointsEffect,
    SelectWeaponEffect,
)
from dnd_board.rules.shared.weapon_effects import eligible_weapon_attacks, weapon_selection_effect
from dnd_board.rules.shared.resources import ResourceId


class SpellControlKind(Enum):
    ATTACK = "attack"
    DAMAGE = "damage"
    HEALING = "healing"
    TEMPORARY_HIT_POINTS = "temporaryHitPoints"
    EFFECT = "effect"
    BOUND_WEAPON_ATTACK = "boundWeaponAttack"
    BOUND_WEAPON_EFFECT = "boundWeaponEffect"


@dataclass(frozen=True)
class SpellControlChoice:
    index: int
    label: str


@dataclass(frozen=True)
class SpellActionControl:
    kind: SpellControlKind
    label: str
    effectIndex: int | None = None
    instanceCount: int = 1
    choices: tuple[SpellControlChoice, ...] = ()
    attackId: str | None = None
    damageType: DamageType | None = None


@dataclass(frozen=True)
class SpellCastOption:
    slotLevel: int
    actions: tuple[SpellActionControl, ...]


@dataclass(frozen=True)
class SpellControlProjection:
    requiresSpellSlot: bool
    actions: tuple[SpellActionControl, ...]
    castOptions: tuple[SpellCastOption, ...] = ()


def project_sheet(sheet: CharacterSheet) -> dict[str, object]:
    projected = serialize_dataclass(sheet)
    projected["spells"] = [
        {
            **serialized,
            "controls": serialize_dataclass(spell_control_projection(sheet, spell)),
        }
        for spell, serialized in zip(sheet.spells, projected["spells"])
    ]
    return projected


def spell_control_projection(sheet: CharacterSheet, spell: SpellEntry) -> SpellControlProjection:
    requires_spell_slot = any(cost.resource == ResourceId.SPELL_SLOT for cost in (spell.resourceCosts or ()))
    return SpellControlProjection(
        requiresSpellSlot=requires_spell_slot,
        actions=spell_action_controls(sheet, spell, None),
        castOptions=tuple(
            SpellCastOption(slot_level, spell_action_controls(sheet, spell, slot_level))
            for slot_level in spell_slot_levels_for_cast(sheet, spell)
        ),
    )


def spell_slot_levels_for_cast(sheet: CharacterSheet, spell: SpellEntry) -> tuple[int, ...]:
    requires_spell_slot = any(cost.resource == ResourceId.SPELL_SLOT for cost in (spell.resourceCosts or ()))
    scales_by_spell_slot = any(
        effect_scales_by_spell_slot(effect)
        for effect in (spell.mechanics.activatedEffects if spell.mechanics is not None else ())
    )
    if not requires_spell_slot and not scales_by_spell_slot:
        return ()
    return tuple(sorted({
        resource.spellSlotLevel
        for resource in sheet.resources
        if resource.currentUses > 0
        and resource.spellSlotLevel is not None
        and resource.spellSlotLevel >= spell.level
    }))


def spell_action_controls(
    sheet: CharacterSheet,
    spell: SpellEntry,
    spell_slot_level: int | None,
) -> tuple[SpellActionControl, ...]:
    if spell.mechanics is None:
        return ()

    roots = spell.mechanics.activatedEffects
    weapon_controls = _bound_weapon_controls(sheet, roots)
    damage_actions = [
        root for root in roots
        if weapon_selection_effect(root) is None
        and first_applied_effect(root, DamageEffect) is not None
    ]
    healing_actions = [
        root for root in roots
        if weapon_selection_effect(root) is None
        and first_applied_effect(root, HealingEffect) is not None
        and first_applied_effect(root, DamageEffect) is None
    ]
    temporary_hit_point_actions = [
        root for root in roots
        if weapon_selection_effect(root) is None
        and first_applied_effect(root, TemporaryHitPointsEffect) is not None
    ]
    condition_actions = [
        root for root in roots
        if weapon_selection_effect(root) is None
        and _contains_condition_change(root)
        and first_applied_effect(root, DamageEffect) is None
    ]
    controls: list[SpellActionControl] = list(weapon_controls)
    has_attack = any(
        weapon_selection_effect(root) is None and first_attack_roll_effect(root) is not None
        for root in roots
    )
    has_combined_attack = any(first_attack_roll_effect(root) is not None for root in damage_actions)
    if has_attack and not has_combined_attack:
        controls.append(SpellActionControl(SpellControlKind.ATTACK, "Attack Roll"))

    for effect_index, root in enumerate(damage_actions):
        repeated = _direct_repeated_effect(root)
        instance_count = (
            scaled_instance_count(repeated.instances, sheet, spell.level, spell_slot_level)
            if repeated is not None
            else 1
        )
        authored_label = activated_effect_label(root, "")
        controls.append(SpellActionControl(
            kind=SpellControlKind.DAMAGE,
            label=(authored_label or "Instance") if instance_count > 1
            else (authored_label or "Cast") if first_attack_roll_effect(root) is not None
            else (authored_label or "Damage"),
            effectIndex=effect_index,
            instanceCount=instance_count,
            choices=_effect_choices(root),
        ))
    for effect_index, root in enumerate(healing_actions):
        controls.append(SpellActionControl(
            SpellControlKind.HEALING,
            activated_effect_label(root, "Heal"),
            effectIndex=effect_index,
        ))
    for effect_index, root in enumerate(temporary_hit_point_actions):
        controls.append(SpellActionControl(
            SpellControlKind.TEMPORARY_HIT_POINTS,
            activated_effect_label(root, "Temp HP"),
            effectIndex=effect_index,
        ))
    for effect_index, root in enumerate(condition_actions):
        controls.append(SpellActionControl(
            SpellControlKind.EFFECT,
            activated_effect_label(root, "Effect"),
            effectIndex=effect_index,
            choices=_effect_choices(root),
        ))
    return tuple(controls)


def effect_scales_by_spell_slot(effect: EffectNode | None) -> bool:
    if effect is None:
        return False
    if isinstance(effect, RepeatedEffect) and effect.instances.basis == ScalingBasis.SPELL_SLOT_LEVEL:
        return True
    if isinstance(effect, ApplyEffect):
        return any(scaling.basis == ScalingBasis.SPELL_SLOT_LEVEL for scaling in getattr(effect.effect, "scaling", ()))
    return any(effect_scales_by_spell_slot(child) for child in _effect_children(effect))


def _contains_condition_change(effect: EffectNode | None) -> bool:
    if isinstance(effect, ApplyEffect):
        return isinstance(effect.effect, ConditionChangeEffect)
    return any(_contains_condition_change(child) for child in _effect_children(effect)) if effect is not None else False


def _effect_children(effect: EffectNode) -> tuple[EffectNode | None, ...]:
    if isinstance(effect, ActivatedEffect):
        return (effect.effect,)
    if isinstance(effect, SequenceEffect):
        return tuple(effect.effects)
    if isinstance(effect, SavingThrowEffect):
        return (effect.onFailure, effect.onSuccess)
    if isinstance(effect, AttackRollEffect):
        return (effect.onHit, effect.onMiss)
    if isinstance(effect, ConditionalEffect):
        return (effect.whenTrue, effect.whenFalse)
    if isinstance(effect, ContestedCheckEffect):
        return (effect.onSourceWin, effect.onTargetWin)
    if isinstance(effect, RepeatedEffect):
        return (effect.effect,)
    if isinstance(effect, ChoiceEffect):
        return tuple(choice.effect for choice in effect.choices)
    if isinstance(effect, SelectWeaponEffect):
        return (effect.effect,)
    return ()


def _direct_repeated_effect(effect: EffectNode) -> RepeatedEffect | None:
    core = activated_effect_node(effect)
    return core if isinstance(core, RepeatedEffect) else None


def _effect_choices(effect: EffectNode) -> tuple[SpellControlChoice, ...]:
    core = activated_effect_node(effect)
    if not isinstance(core, ChoiceEffect):
        return ()
    return tuple(SpellControlChoice(index, enum_label(choice.option)) for index, choice in enumerate(core.choices))


def _bound_weapon_controls(
    sheet: CharacterSheet,
    roots: list[EffectNode],
) -> tuple[SpellActionControl, ...]:
    controls: list[SpellActionControl] = []
    for effect_index, root in enumerate(roots):
        found = weapon_selection_effect(root)
        if found is None:
            continue
        _node_id, selection = found
        kind = (
            SpellControlKind.BOUND_WEAPON_ATTACK
            if first_attack_roll_effect(selection.effect) is not None
            else SpellControlKind.BOUND_WEAPON_EFFECT
        )
        choices = _effect_choices(selection.effect)
        label = activated_effect_label(root, "Use")
        for attack in eligible_weapon_attacks(sheet, selection.eligibility):
            controls.append(SpellActionControl(
                kind,
                f"{label} {attack.name}",
                effectIndex=effect_index,
                choices=choices,
                attackId=attack.id,
            ))
    return tuple(controls)
