from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from dnd_board.character_sheet import (
    CharacterClassLevel,
    DiceType,
    FightingStyleType,
    RollAction,
    RollModifierType,
    RollResolutionMode,
    SheetAbility,
    TimeEconomy,
    enum_key,
    enum_label,
)


class FeatCategory(Enum):
    FIGHTING_STYLE = auto()


class FeatEffectType(Enum):
    ARMOR_CLASS_BONUS = auto()
    ROLL_ABILITY = auto()
    DESCRIPTION_ONLY = auto()


@dataclass(frozen=True)
class FeatEffect:
    effectType: FeatEffectType
    value: int = 0
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
        effects=(FeatEffect(effectType=FeatEffectType.DESCRIPTION_ONLY),),
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
        effects=(FeatEffect(effectType=FeatEffectType.DESCRIPTION_ONLY),),
    ),
    FightingStyleType.GREAT_WEAPON_FIGHTING: FeatDefinition(
        featType=FightingStyleType.GREAT_WEAPON_FIGHTING,
        category=FeatCategory.FIGHTING_STYLE,
        repeatable=False,
        description="When rolling damage with an eligible two-handed or versatile melee weapon, low weapon damage dice can be improved.",
        effects=(FeatEffect(effectType=FeatEffectType.DESCRIPTION_ONLY),),
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
        effects=(FeatEffect(effectType=FeatEffectType.DESCRIPTION_ONLY),),
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


def feat_abilities(classes: list[CharacterClassLevel]) -> list[SheetAbility]:
    abilities: list[SheetAbility] = []
    for style in selected_fighting_styles(classes):
        definition = FIGHTING_STYLE_FEATS.get(style)
        if definition is None:
            continue
        for effect in definition.effects:
            if effect.effectType != FeatEffectType.ROLL_ABILITY or effect.rollAction is None:
                continue
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
    return abilities


def armor_class_bonus(classes: list[CharacterClassLevel]) -> int:
    bonus = 0
    for style in selected_fighting_styles(classes):
        definition = FIGHTING_STYLE_FEATS.get(style)
        if definition is None:
            continue
        bonus += sum(effect.value for effect in definition.effects if effect.effectType == FeatEffectType.ARMOR_CLASS_BONUS)
    return bonus
