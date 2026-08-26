from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from dnd_board.character_sheet import (
    AbilityType,
    ArmorCategory,
    AttackAction,
    AttackActionType,
    AttackDamageAbilityModifierMode,
    AttackKind,
    AttackRangeType,
    CharacterClassLevel,
    DamageType,
    DiceType,
    EquipmentItem,
    EquipmentSlot,
    EquipmentType,
    FightingStyleType,
    RollAction,
    RollModifierBreakdown,
    RollModifierType,
    RollResolutionMode,
    SheetAbility,
    TimeEconomy,
    WeaponCategory,
    WeaponProperty,
    enum_key,
    enum_label,
)


class FeatCategory(Enum):
    FIGHTING_STYLE = auto()


class FeatEffectType(Enum):
    ARMOR_CLASS_BONUS = auto()
    ATTACK_ROLL_BONUS = auto()
    DAMAGE_DICE_REROLL = auto()
    DAMAGE_ABILITY_MODIFIER = auto()
    DAMAGE_ROLL_BONUS = auto()
    ROLL_ABILITY = auto()
    SHEET_ABILITY = auto()
    DESCRIPTION_ONLY = auto()


class FeatAttackRollBonusScope(Enum):
    RANGED_ATTACK = auto()
    RANGED_WEAPON_ATTACK = auto()


class FeatDamageRollBonusScope(Enum):
    ONE_HANDED_MELEE_WEAPON_ATTACK = auto()
    THROWN_RANGED_ATTACK = auto()


class FeatDamageAbilityModifierScope(Enum):
    TWO_WEAPON_FIGHTING_ATTACK = auto()


class FeatDamageDiceRerollScope(Enum):
    TWO_HANDED_OR_VERSATILE_MELEE_WEAPON_ATTACK = auto()


@dataclass(frozen=True)
class FeatEffect:
    effectType: FeatEffectType
    value: int = 0
    attackRollBonusScope: FeatAttackRollBonusScope | None = None
    damageAbilityModifierScope: FeatDamageAbilityModifierScope | None = None
    damageRollBonusScope: FeatDamageRollBonusScope | None = None
    damageDiceRerollScope: FeatDamageDiceRerollScope | None = None
    rollAction: RollAction | None = None
    activation: TimeEconomy = TimeEconomy.PASSIVE
    description: str = ""


@dataclass(frozen=True)
class FeatDefinition:
    featType: FightingStyleType
    category: FeatCategory
    repeatable: bool
    description: str
    effects: tuple[FeatEffect, ...]


FIGHTING_STYLE_FEATS: dict[FightingStyleType, FeatDefinition] = {
    FightingStyleType.ARCHERY: FeatDefinition(
        featType=FightingStyleType.ARCHERY,
        category=FeatCategory.FIGHTING_STYLE,
        repeatable=False,
        description="Gain a +2 bonus to attack rolls you make with ranged weapons.",
        effects=(
            FeatEffect(
                effectType=FeatEffectType.ATTACK_ROLL_BONUS,
                value=2,
                attackRollBonusScope=FeatAttackRollBonusScope.RANGED_WEAPON_ATTACK,
                description="Ranged weapon attack bonus.",
            ),
        ),
    ),
    FightingStyleType.BLIND_FIGHTING: FeatDefinition(
        featType=FightingStyleType.BLIND_FIGHTING,
        category=FeatCategory.FIGHTING_STYLE,
        repeatable=False,
        description="You have blindsight with a range of 10 feet, letting you effectively see anything in range that is not behind total cover.",
        effects=(FeatEffect(effectType=FeatEffectType.DESCRIPTION_ONLY),),
    ),
    FightingStyleType.CLOSE_QUARTERS_SHOOTER: FeatDefinition(
        featType=FightingStyleType.CLOSE_QUARTERS_SHOOTER,
        category=FeatCategory.FIGHTING_STYLE,
        repeatable=False,
        description="Ranged attacks do not have Disadvantage within 5 feet of a hostile creature, ignore half and three-quarters cover within 30 feet, and gain a +1 attack bonus.",
        effects=(
            FeatEffect(
                effectType=FeatEffectType.ATTACK_ROLL_BONUS,
                value=1,
                attackRollBonusScope=FeatAttackRollBonusScope.RANGED_ATTACK,
                description="Ranged attack bonus.",
            ),
        ),
    ),
    FightingStyleType.DEFENSE: FeatDefinition(
        featType=FightingStyleType.DEFENSE,
        category=FeatCategory.FIGHTING_STYLE,
        repeatable=False,
        description="While wearing armor, gain a +1 bonus to Armor Class.",
        effects=(FeatEffect(effectType=FeatEffectType.ARMOR_CLASS_BONUS, value=1),),
    ),
    FightingStyleType.DUELING: FeatDefinition(
        featType=FightingStyleType.DUELING,
        category=FeatCategory.FIGHTING_STYLE,
        repeatable=False,
        description="When wielding a melee weapon in one hand and no other weapons, gain a +2 bonus to damage rolls with that weapon.",
        effects=(
            FeatEffect(
                effectType=FeatEffectType.DAMAGE_ROLL_BONUS,
                value=2,
                damageRollBonusScope=FeatDamageRollBonusScope.ONE_HANDED_MELEE_WEAPON_ATTACK,
                description="Eligible one-handed melee weapon damage bonus.",
            ),
        ),
    ),
    FightingStyleType.GREAT_WEAPON_FIGHTING: FeatDefinition(
        featType=FightingStyleType.GREAT_WEAPON_FIGHTING,
        category=FeatCategory.FIGHTING_STYLE,
        repeatable=False,
        description="When rolling damage with an eligible two-handed or versatile melee weapon, reroll weapon damage dice of 1 or 2 and use the new roll.",
        effects=(
            FeatEffect(
                effectType=FeatEffectType.DAMAGE_DICE_REROLL,
                damageDiceRerollScope=FeatDamageDiceRerollScope.TWO_HANDED_OR_VERSATILE_MELEE_WEAPON_ATTACK,
                description="Reroll weapon damage dice of 1 or 2.",
            ),
        ),
    ),
    FightingStyleType.MARINER: FeatDefinition(
        featType=FightingStyleType.MARINER,
        category=FeatCategory.FIGHTING_STYLE,
        repeatable=False,
        description="While not wearing heavy armor or using a shield, gain a swimming speed and climbing speed equal to your Speed, and gain a +1 bonus to Armor Class.",
        effects=(FeatEffect(effectType=FeatEffectType.ARMOR_CLASS_BONUS, value=1),),
    ),
    FightingStyleType.PROTECTION: FeatDefinition(
        featType=FightingStyleType.PROTECTION,
        category=FeatCategory.FIGHTING_STYLE,
        repeatable=False,
        description="Use a Reaction while wielding a shield to impose Disadvantage when a creature you can see attacks another target within 5 feet of you.",
        effects=(
            FeatEffect(
                effectType=FeatEffectType.SHEET_ABILITY,
                activation=TimeEconomy.REACTION,
                description="Impose Disadvantage on an attack against a nearby target other than you while wielding a shield.",
            ),
        ),
    ),
    FightingStyleType.SUPERIOR_TECHNIQUE: FeatDefinition(
        featType=FightingStyleType.SUPERIOR_TECHNIQUE,
        category=FeatCategory.FIGHTING_STYLE,
        repeatable=False,
        description="Learn one Battle Master maneuver and gain one d6 superiority die. Full tracking is skipped until Battle Master maneuvers are implemented.",
        effects=(FeatEffect(effectType=FeatEffectType.DESCRIPTION_ONLY),),
    ),
    FightingStyleType.THROWN_WEAPON_FIGHTING: FeatDefinition(
        featType=FightingStyleType.THROWN_WEAPON_FIGHTING,
        category=FeatCategory.FIGHTING_STYLE,
        repeatable=False,
        description="You can draw a thrown weapon as part of the attack, and gain a +2 damage bonus when you hit with a ranged attack using a thrown weapon.",
        effects=(
            FeatEffect(
                effectType=FeatEffectType.DAMAGE_ROLL_BONUS,
                value=2,
                damageRollBonusScope=FeatDamageRollBonusScope.THROWN_RANGED_ATTACK,
                description="Thrown weapon ranged attack damage bonus.",
            ),
        ),
    ),
    FightingStyleType.TUNNEL_FIGHTER: FeatDefinition(
        featType=FightingStyleType.TUNNEL_FIGHTER,
        category=FeatCategory.FIGHTING_STYLE,
        repeatable=False,
        description="Use a Bonus Action to enter a defensive stance until the start of your next turn, enabling extra opportunity control.",
        effects=(
            FeatEffect(
                effectType=FeatEffectType.SHEET_ABILITY,
                activation=TimeEconomy.BONUS_ACTION,
                description="Enter a defensive stance until your next turn: opportunity attacks do not use your Reaction, and you can use your Reaction to attack a creature that moves more than 5 feet within your reach.",
            ),
        ),
    ),
    FightingStyleType.INTERCEPTION: FeatDefinition(
        featType=FightingStyleType.INTERCEPTION,
        category=FeatCategory.FIGHTING_STYLE,
        repeatable=False,
        description="Use a Reaction to reduce damage to a nearby target by 1d10 plus your Proficiency Bonus.",
        effects=(
            FeatEffect(
                effectType=FeatEffectType.ROLL_ABILITY,
                rollAction=RollAction(
                    id=FightingStyleType.INTERCEPTION,
                    name=FightingStyleType.INTERCEPTION,
                    diceCount=1,
                    diceType=DiceType.D10,
                    modifier=RollModifierType.PROFICIENCY_BONUS,
                    resolution=RollResolutionMode.NONE,
                ),
                activation=TimeEconomy.REACTION,
                description="Reduce damage by 1d10 plus Proficiency Bonus.",
            ),
        ),
    ),
    FightingStyleType.TWO_WEAPON_FIGHTING: FeatDefinition(
        featType=FightingStyleType.TWO_WEAPON_FIGHTING,
        category=FeatCategory.FIGHTING_STYLE,
        repeatable=False,
        description="When making the extra attack from a Light weapon, add your ability modifier to the damage if it is not already included.",
        effects=(
            FeatEffect(
                effectType=FeatEffectType.DAMAGE_ABILITY_MODIFIER,
                damageAbilityModifierScope=FeatDamageAbilityModifierScope.TWO_WEAPON_FIGHTING_ATTACK,
                description="Add the attack ability modifier to two-weapon fighting bonus attack damage.",
            ),
        ),
    ),
    FightingStyleType.UNARMED_FIGHTING: FeatDefinition(
        featType=FightingStyleType.UNARMED_FIGHTING,
        category=FeatCategory.FIGHTING_STYLE,
        repeatable=False,
        description="Your Unarmed Strikes deal improved damage; you can also deal 1d4 damage to a creature grappled by you.",
        effects=(
            FeatEffect(
                effectType=FeatEffectType.ROLL_ABILITY,
                rollAction=RollAction(
                    id=FightingStyleType.UNARMED_FIGHTING,
                    name=FightingStyleType.UNARMED_FIGHTING,
                    diceCount=1,
                    diceType=DiceType.D4,
                    resolution=RollResolutionMode.NONE,
                ),
                activation=TimeEconomy.SPECIAL,
                description="Roll 1d4 damage for the grapple rider when appropriate.",
            ),
        ),
    ),
}


def selected_fighting_styles(classes: list[CharacterClassLevel]) -> list[FightingStyleType]:
    styles: list[FightingStyleType] = []
    for character_class in classes:
        for fighting_style in character_class.fightingStyles or []:
            if fighting_style not in styles:
                styles.append(fighting_style)
        if character_class.fightingStyle is not None and character_class.fightingStyle not in styles:
            styles.append(character_class.fightingStyle)
    return styles


def fighting_style_features(classes: list[CharacterClassLevel]):
    from dnd_board.character_sheet import SheetFeature

    features: list[SheetFeature] = []
    for style in selected_fighting_styles(classes):
        definition = FIGHTING_STYLE_FEATS.get(style)
        if definition is None:
            continue
        features.append(
            SheetFeature(
                id=enum_key(style),
                name=enum_label(style),
                source=enum_label(FeatCategory.FIGHTING_STYLE),
                activation=TimeEconomy.PASSIVE,
                description=definition.description,
            )
        )
    return features


def feat_resources(classes: list[CharacterClassLevel]):
    return []


def feat_abilities(classes: list[CharacterClassLevel]) -> list[SheetAbility]:
    abilities: list[SheetAbility] = []
    for style in selected_fighting_styles(classes):
        definition = FIGHTING_STYLE_FEATS.get(style)
        if definition is None:
            continue
        for effect in definition.effects:
            if effect.effectType == FeatEffectType.ROLL_ABILITY and effect.rollAction is not None:
                abilities.append(
                    SheetAbility(
                        id=enum_key(style),
                        name=enum_label(style),
                        source=enum_label(FeatCategory.FIGHTING_STYLE),
                        activation=effect.activation,
                        description=effect.description,
                        rollActions=[effect.rollAction],
                    )
                )
            elif effect.effectType == FeatEffectType.SHEET_ABILITY:
                abilities.append(
                    SheetAbility(
                        id=enum_key(style),
                        name=enum_label(style),
                        source=enum_label(FeatCategory.FIGHTING_STYLE),
                        activation=effect.activation,
                        description=effect.description,
                    )
                )
    return abilities


def armor_class_bonus(classes: list[CharacterClassLevel], equipment: list[EquipmentItem]) -> int:
    bonus = 0
    for style in selected_fighting_styles(classes):
        definition = FIGHTING_STYLE_FEATS.get(style)
        if definition is None:
            continue
        bonus += sum(effect.value for effect in definition.effects if effect.effectType == FeatEffectType.ARMOR_CLASS_BONUS and armor_class_bonus_applies(style, equipment))
    return bonus


def attack_roll_modifiers(classes: list[CharacterClassLevel], action: AttackAction) -> list[RollModifierBreakdown]:
    modifiers: list[RollModifierBreakdown] = []
    for definition in selected_fighting_style_definitions(classes):
        for effect in definition.effects:
            if effect.effectType == FeatEffectType.ATTACK_ROLL_BONUS and attack_roll_bonus_applies(effect, action):
                modifiers.append(RollModifierBreakdown(source=enum_label(definition.featType), value=effect.value, description=effect.description))
    return modifiers


def damage_roll_modifiers(classes: list[CharacterClassLevel], equipment: list[EquipmentItem], action: AttackAction, ability_modifier_value: int) -> list[RollModifierBreakdown]:
    modifiers: list[RollModifierBreakdown] = []
    for definition in selected_fighting_style_definitions(classes):
        for effect in definition.effects:
            if effect.effectType == FeatEffectType.DAMAGE_ROLL_BONUS and damage_roll_bonus_applies(effect, equipment, action):
                modifiers.append(RollModifierBreakdown(source=enum_label(definition.featType), value=effect.value, description=effect.description))
            elif effect.effectType == FeatEffectType.DAMAGE_ABILITY_MODIFIER and damage_ability_modifier_applies(effect, action):
                modifiers.append(RollModifierBreakdown(source=enum_label(definition.featType), value=ability_modifier_value, description=effect.description))
    return modifiers


def great_weapon_fighting_applies(classes: list[CharacterClassLevel], action: AttackAction) -> bool:
    return any(
        effect.effectType == FeatEffectType.DAMAGE_DICE_REROLL and damage_dice_reroll_applies(effect, action)
        for definition in selected_fighting_style_definitions(classes)
        for effect in definition.effects
    )


def selected_fighting_style_definitions(classes: list[CharacterClassLevel]) -> list[FeatDefinition]:
    return [definition for style in selected_fighting_styles(classes) if (definition := FIGHTING_STYLE_FEATS.get(style)) is not None]


def attack_roll_bonus_applies(effect: FeatEffect, action: AttackAction) -> bool:
    if effect.attackRollBonusScope == FeatAttackRollBonusScope.RANGED_ATTACK:
        return is_ranged_attack(action)
    if effect.attackRollBonusScope == FeatAttackRollBonusScope.RANGED_WEAPON_ATTACK:
        return is_ranged_weapon_attack(action)
    return False


def damage_roll_bonus_applies(effect: FeatEffect, equipment: list[EquipmentItem], action: AttackAction) -> bool:
    if effect.damageRollBonusScope == FeatDamageRollBonusScope.ONE_HANDED_MELEE_WEAPON_ATTACK:
        return is_one_handed_melee_weapon_attack(action) and is_wielding_exactly_one_one_handed_weapon(equipment)
    if effect.damageRollBonusScope == FeatDamageRollBonusScope.THROWN_RANGED_ATTACK:
        return is_thrown_weapon_attack(action)
    return False


def damage_ability_modifier_applies(effect: FeatEffect, action: AttackAction) -> bool:
    if effect.damageAbilityModifierScope == FeatDamageAbilityModifierScope.TWO_WEAPON_FIGHTING_ATTACK:
        return action.attackKind == AttackKind.TWO_WEAPON_FIGHTING and action.damageAbilityModifier == AttackDamageAbilityModifierMode.EXCLUDED
    return False


def damage_dice_reroll_applies(effect: FeatEffect, action: AttackAction) -> bool:
    if effect.damageDiceRerollScope == FeatDamageDiceRerollScope.TWO_HANDED_OR_VERSATILE_MELEE_WEAPON_ATTACK:
        return is_two_handed_or_versatile_melee_weapon_attack(action)
    return False


def feat_attacks(classes: list[CharacterClassLevel], equipment: list[EquipmentItem], attacks: list[AttackAction]) -> list[AttackAction]:
    styles = selected_fighting_styles(classes)
    next_attacks = list(attacks)
    attack_types = {attack.attackType for attack in next_attacks}
    if FightingStyleType.UNARMED_FIGHTING in styles and AttackActionType.UNARMED_STRIKE not in attack_types:
        next_attacks.append(
            AttackAction(
                id=enum_key(AttackActionType.UNARMED_STRIKE),
                name=enum_label(AttackActionType.UNARMED_STRIKE),
                ability=AbilityType.STRENGTH,
                damageDiceCount=1,
                damageDiceType=DiceType.D8 if has_empty_hands_for_unarmed_fighting(equipment) else DiceType.D6,
                damageType=DamageType.BLUDGEONING,
                attackRange=AttackRangeType.MELEE,
                weaponCategory=WeaponCategory.MELEE,
                attackType=AttackActionType.UNARMED_STRIKE,
                properties=[],
            )
        )
    if FightingStyleType.THROWN_WEAPON_FIGHTING in styles and AttackActionType.THROWN_WEAPON not in attack_types:
        next_attacks.append(
            AttackAction(
                id=enum_key(AttackActionType.THROWN_WEAPON),
                name=enum_label(AttackActionType.THROWN_WEAPON),
                ability=AbilityType.STRENGTH,
                damageDiceCount=1,
                damageDiceType=DiceType.D6,
                damageType=DamageType.SLASHING,
                attackRange=AttackRangeType.RANGED,
                weaponCategory=WeaponCategory.MELEE,
                attackType=AttackActionType.THROWN_WEAPON,
                properties=[WeaponProperty.THROWN],
            )
        )
    return next_attacks


def armor_class_bonus_applies(style: FightingStyleType, equipment: list[EquipmentItem]) -> bool:
    if style == FightingStyleType.DEFENSE:
        return is_wearing_armor(equipment)
    if style == FightingStyleType.MARINER:
        return not is_wearing_heavy_armor(equipment) and not is_wielding_shield(equipment)
    return True


def is_wearing_armor(equipment: list[EquipmentItem]) -> bool:
    return any(item.itemType == EquipmentType.ARMOR and item.slot == EquipmentSlot.ARMOR for item in equipment)


def is_wearing_heavy_armor(equipment: list[EquipmentItem]) -> bool:
    return any(item.itemType == EquipmentType.ARMOR and item.slot == EquipmentSlot.ARMOR and item.armorCategory == ArmorCategory.HEAVY for item in equipment)


def is_wielding_shield(equipment: list[EquipmentItem]) -> bool:
    return any(item.itemType == EquipmentType.SHIELD and item.slot in {EquipmentSlot.MAIN_HAND, EquipmentSlot.OFF_HAND} for item in equipment)


def wielded_weapons(equipment: list[EquipmentItem]) -> list[EquipmentItem]:
    return [item for item in equipment if item.itemType == EquipmentType.WEAPON and item.slot in {EquipmentSlot.MAIN_HAND, EquipmentSlot.OFF_HAND, EquipmentSlot.TWO_HANDS}]


def is_wielding_exactly_one_one_handed_weapon(equipment: list[EquipmentItem]) -> bool:
    weapons = wielded_weapons(equipment)
    return len(weapons) == 1 and weapons[0].slot in {EquipmentSlot.MAIN_HAND, EquipmentSlot.OFF_HAND}


def has_empty_hands_for_unarmed_fighting(equipment: list[EquipmentItem]) -> bool:
    return not wielded_weapons(equipment) and not is_wielding_shield(equipment)


def weapon_properties(action: AttackAction) -> set[WeaponProperty]:
    return set(action.properties or [])


def is_ranged_weapon_attack(action: AttackAction) -> bool:
    return action.weaponCategory == WeaponCategory.RANGED and action.attackRange == AttackRangeType.RANGED


def is_ranged_attack(action: AttackAction) -> bool:
    return action.attackRange == AttackRangeType.RANGED


def is_thrown_weapon_attack(action: AttackAction) -> bool:
    return action.attackRange == AttackRangeType.RANGED and WeaponProperty.THROWN in weapon_properties(action)


def is_melee_weapon_attack(action: AttackAction) -> bool:
    return action.attackRange == AttackRangeType.MELEE and action.damageType in {DamageType.BLUDGEONING, DamageType.PIERCING, DamageType.SLASHING}


def is_one_handed_melee_weapon_attack(action: AttackAction) -> bool:
    return is_melee_weapon_attack(action) and WeaponProperty.TWO_HANDED not in weapon_properties(action)


def is_two_handed_or_versatile_melee_weapon_attack(action: AttackAction) -> bool:
    return is_melee_weapon_attack(action) and bool(weapon_properties(action) & {WeaponProperty.TWO_HANDED, WeaponProperty.VERSATILE})
