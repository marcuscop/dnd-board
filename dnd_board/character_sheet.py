from __future__ import annotations

import random
from dataclasses import dataclass, fields, is_dataclass
from enum import Enum, auto
from time import time_ns
from types import UnionType
from typing import Any, Union, get_args, get_origin, get_type_hints


class TokenKind(Enum):
    CHARACTER = auto()
    ASSET = auto()


class RollResolutionMode(Enum):
    NONE = auto()
    ATTACK_VS_ARMOR_CLASS = auto()
    APPLY_DAMAGE = auto()
    HEAL_SELF = auto()


class RollModifierType(Enum):
    NONE = auto()
    CLASS_LEVEL = auto()
    PROFICIENCY_BONUS = auto()


class SheetSectionType(Enum):
    ATTACKS = auto()
    RESOURCES = auto()
    FEATURES = auto()
    ABILITIES = auto()


class UIStringFormatter:
    @staticmethod
    def clean_name(identifier: str) -> str:
        return " ".join(word.capitalize() for word in identifier.replace("_", " ").split())

    @staticmethod
    def lower_camel(identifier: str) -> str:
        words = identifier.lower().split("_")
        return words[0] + "".join(word.capitalize() for word in words[1:])


class AbilityType(Enum):
    STRENGTH = auto()
    DEXTERITY = auto()
    CONSTITUTION = auto()
    INTELLIGENCE = auto()
    WISDOM = auto()
    CHARISMA = auto()


class DamageType(Enum):
    ACID = auto()
    BLUDGEONING = auto()
    COLD = auto()
    FIRE = auto()
    FORCE = auto()
    LIGHTNING = auto()
    NECROTIC = auto()
    PIERCING = auto()
    POISON = auto()
    PSYCHIC = auto()
    RADIANT = auto()
    SLASHING = auto()
    THUNDER = auto()


class DiceType(Enum):
    D4 = 4
    D6 = 6
    D8 = 8
    D10 = 10
    D12 = 12
    D20 = 20


class TimeEconomy(Enum):
    ACTION = auto()
    BONUS_ACTION = auto()
    REACTION = auto()
    MOVEMENT = auto()
    PASSIVE = auto()
    SPECIAL = auto()


class ProficiencyLevel(Enum):
    NONE = auto()
    PROFICIENT = auto()
    EXPERTISE = auto()


class RestType(Enum):
    NONE = auto()
    SHORT_REST = auto()
    LONG_REST = auto()


class ClassType(Enum):
    ADVENTURER = auto()
    CREATURE = auto()
    FIGHTER = auto()


class FightingStyleType(Enum):
    ARCHERY = auto()
    BLIND_FIGHTING = auto()
    DEFENSE = auto()
    DUELING = auto()
    GREAT_WEAPON_FIGHTING = auto()
    INTERCEPTION = auto()
    PROTECTION = auto()
    SUPERIOR_TECHNIQUE = auto()
    THROWN_WEAPON_FIGHTING = auto()
    TWO_WEAPON_FIGHTING = auto()
    UNARMED_FIGHTING = auto()


def api_field(method: Any) -> property:
    method.__api_field__ = True
    return property(method)


@dataclass
class AbilityScores:
    strength: int
    dexterity: int
    constitution: int
    intelligence: int
    wisdom: int
    charisma: int


@dataclass
class HitPoints:
    current: int
    max: int
    temporary: int


@dataclass
class AttackAction:
    id: str
    name: str
    ability: AbilityType
    damageDiceCount: int
    damageDiceType: DiceType
    proficient: bool = True
    damageType: DamageType = DamageType.SLASHING
    toHitBonus: int = 0
    damageBonus: int = 0
    activation: TimeEconomy = TimeEconomy.ACTION
    properties: list[str] | None = None

    @api_field
    def damageDie(self) -> str:
        return dice_formula(self.damageDiceCount, self.damageDiceType)


@dataclass
class RollAction:
    id: Enum
    name: Enum
    diceCount: int
    diceType: DiceType
    modifier: RollModifierType = RollModifierType.NONE
    staticModifier: int = 0
    resolution: RollResolutionMode = RollResolutionMode.NONE
    consumesResource: Enum | None = None

    @api_field
    def dice(self) -> str:
        return dice_formula(self.diceCount, self.diceType)


@dataclass
class RollSource:
    section: SheetSectionType
    sourceId: str
    actionId: str


@dataclass
class CharacterClassLevel:
    name: ClassType
    level: int
    subclass: Enum | None = None
    fightingStyle: FightingStyleType | None = None
    fightingStyles: list[FightingStyleType] | None = None


@dataclass
class SkillBonus:
    name: str
    ability: AbilityType
    proficiency: ProficiencyLevel
    modifier: int
    passive: int


@dataclass
class SavingThrowBonus:
    ability: AbilityType
    proficient: bool
    modifier: int


@dataclass
class ResourceTracker:
    id: str
    name: str
    currentUses: int
    maxUses: int
    reset: RestType
    activation: TimeEconomy
    description: str
    rollActions: list[RollAction] | None = None


@dataclass
class SheetAbility:
    id: str
    name: str
    source: str
    activation: TimeEconomy
    description: str
    resourceId: str | None = None
    rollActions: list[RollAction] | None = None


@dataclass
class SheetFeature:
    id: str
    name: str
    source: str
    activation: TimeEconomy
    description: str
    rollActions: list[RollAction] | None = None


@dataclass
class EquipmentItem:
    id: str
    name: str
    equipped: bool
    quantity: int = 1
    weight: float = 0.0
    notes: str = ""


@dataclass
class PartyMemberSheet:
    race: str | None = None
    background: str | None = None
    alignment: str | None = None
    classes: list[CharacterClassLevel] | None = None
    armorClass: int | None = None
    speed: int | None = None
    proficiencyBonus: int | None = None
    skills: dict[str, ProficiencyLevel] | None = None
    savingThrowProficiencies: list[AbilityType] | None = None
    proficiencies: list[str] | None = None
    feats: list[SheetFeature] | None = None
    traits: list[SheetFeature] | None = None
    features: list[SheetFeature] | None = None
    resources: list[ResourceTracker] | None = None
    attacks: list[AttackAction] | None = None
    equipment: list[EquipmentItem] | None = None


@dataclass
class PartyMemberConfig:
    id: str
    name: str
    image: str | None = None
    maxHp: int | None = None
    abilityScores: AbilityScores | None = None
    sheet: PartyMemberSheet | None = None


@dataclass
class PartyManifest:
    members: list[PartyMemberConfig]


@dataclass
class CharacterClass:
    name: ClassType
    level: int


@dataclass
class CharacterSheet:
    id: str
    tokenId: str
    kind: TokenKind
    name: str
    owner: str
    avatarUrl: str | None
    characterClass: CharacterClass
    classes: list[CharacterClassLevel]
    race: str
    background: str
    alignment: str
    proficiencyBonus: int
    hp: HitPoints
    abilityScores: AbilityScores
    abilityModifiers: dict[str, int]
    armorClass: int
    initiativeBonus: int
    speed: int
    savingThrows: list[SavingThrowBonus]
    skills: list[SkillBonus]
    passiveChecks: dict[str, int]
    resources: list[ResourceTracker]
    abilities: list[SheetAbility]
    features: list[SheetFeature]
    proficiencies: list[str]
    conditions: list[str]
    attacks: list[AttackAction]
    equipment: list[EquipmentItem]


@dataclass
class RollPayload:
    id: str
    sheetId: str
    tokenId: str
    roller: str
    source: RollSource
    sourceLabel: str
    resolution: RollResolutionMode
    label: str
    iconUrl: str | None
    dice: list[int]
    diceType: DiceType
    die: str
    modifier: int
    total: int
    createdAt: int
    resourceSpent: RollResourceSpend | None = None


@dataclass
class RollResourceSpend:
    resourceId: str
    resourceName: str
    remainingUses: int
    maxUses: int


@dataclass
class RollResolution:
    id: str
    roll: RollPayload
    targetSheetId: str
    targetTokenId: str
    targetName: str
    targetArmorClass: int
    targetHp: HitPoints
    outcome: str
    createdAt: int


@dataclass
class PartyMember:
    id: str
    name: str
    owner: str
    avatarUrl: str | None
    abilityScores: AbilityScores | None = None
    maxHp: int | None = None
    sheet: PartyMemberSheet | None = None


ABILITY_NAMES = [
    AbilityType.STRENGTH,
    AbilityType.DEXTERITY,
    AbilityType.CONSTITUTION,
    AbilityType.INTELLIGENCE,
    AbilityType.WISDOM,
    AbilityType.CHARISMA,
]
SKILL_ABILITIES = {
    "athletics": AbilityType.STRENGTH,
    "acrobatics": AbilityType.DEXTERITY,
    "sleightOfHand": AbilityType.DEXTERITY,
    "stealth": AbilityType.DEXTERITY,
    "arcana": AbilityType.INTELLIGENCE,
    "history": AbilityType.INTELLIGENCE,
    "investigation": AbilityType.INTELLIGENCE,
    "nature": AbilityType.INTELLIGENCE,
    "religion": AbilityType.INTELLIGENCE,
    "animalHandling": AbilityType.WISDOM,
    "insight": AbilityType.WISDOM,
    "medicine": AbilityType.WISDOM,
    "perception": AbilityType.WISDOM,
    "survival": AbilityType.WISDOM,
    "deception": AbilityType.CHARISMA,
    "intimidation": AbilityType.CHARISMA,
    "performance": AbilityType.CHARISMA,
    "persuasion": AbilityType.CHARISMA,
}

TYPE_KEY = "$type"
FIELDS_KEY = "fields"
ITEMS_KEY = "items"
VALUE_KEY = "value"


def build_character_sheet(
    *,
    token_id: str,
    kind: TokenKind,
    name: str,
    owner: str,
    avatar_url: str | None,
    party_member: PartyMember | None,
    current_hp: int | None,
    resource_overrides: dict[str, int],
) -> CharacterSheet:
    ability_scores = party_member.abilityScores if party_member and party_member.abilityScores else generated_ability_scores(token_id)
    max_hp = party_member.maxHp if party_member and party_member.maxHp is not None else generated_max_hp(token_id, ability_scores)
    dexterity_modifier = ability_modifier(ability_scores.dexterity)
    sheet_config = party_member.sheet if party_member else None
    classes = sheet_config.classes if sheet_config and sheet_config.classes else [CharacterClassLevel(name=ClassType.ADVENTURER if kind == TokenKind.CHARACTER else ClassType.CREATURE, level=1)]
    total_level = sum(character_class.level for character_class in classes) or 1
    primary_class = classes[0]
    proficiency_bonus = sheet_config.proficiencyBonus if sheet_config and sheet_config.proficiencyBonus is not None else proficiency_bonus_for_level(total_level)
    ability_modifiers = ability_modifier_map(ability_scores)
    skill_proficiencies = sheet_config.skills if sheet_config and sheet_config.skills else {}
    save_proficiencies = set(sheet_config.savingThrowProficiencies if sheet_config and sheet_config.savingThrowProficiencies else default_save_proficiencies(classes))
    resources = apply_resource_overrides(sheet_config.resources if sheet_config and sheet_config.resources else default_resources(classes), resource_overrides)
    feat_abilities = default_feat_abilities(classes)
    abilities = [*resource_roll_abilities(resources), *feat_abilities]
    features = default_features(classes)
    if sheet_config:
        features = [*(sheet_config.traits or []), *features, *(sheet_config.features or []), *(sheet_config.feats or [])]
    armor_class = sheet_config.armorClass if sheet_config and sheet_config.armorClass is not None else 12 + min(3, dexterity_modifier)
    armor_class += default_armor_class_bonus(classes)

    return CharacterSheet(
        id=token_id,
        tokenId=token_id,
        kind=kind,
        name=name,
        owner=owner,
        avatarUrl=avatar_url,
        characterClass=CharacterClass(name=primary_class.name, level=primary_class.level),
        classes=classes,
        race=sheet_config.race if sheet_config and sheet_config.race else "",
        background=sheet_config.background if sheet_config and sheet_config.background else "",
        alignment=sheet_config.alignment if sheet_config and sheet_config.alignment else "",
        proficiencyBonus=proficiency_bonus,
        hp=HitPoints(current=clamp_int(current_hp, 0, max_hp) if current_hp is not None else max_hp, max=max_hp, temporary=0),
        abilityScores=ability_scores,
        abilityModifiers=ability_modifiers,
        armorClass=armor_class,
        initiativeBonus=dexterity_modifier,
        speed=sheet_config.speed if sheet_config and sheet_config.speed is not None else 30,
        savingThrows=build_saving_throws(ability_modifiers, save_proficiencies, proficiency_bonus),
        skills=build_skills(ability_modifiers, skill_proficiencies, proficiency_bonus),
        passiveChecks=build_passive_checks(ability_modifiers, skill_proficiencies, proficiency_bonus),
        resources=resources,
        abilities=abilities,
        features=features,
        proficiencies=sheet_config.proficiencies if sheet_config and sheet_config.proficiencies else [],
        conditions=[],
        attacks=sheet_config.attacks if sheet_config and sheet_config.attacks else default_attacks(kind),
        equipment=sheet_config.equipment if sheet_config and sheet_config.equipment else [],
    )


def build_attack_roll_payload(sheet: CharacterSheet, roller: str, action: AttackAction) -> RollPayload:
    ability_score = getattr(sheet.abilityScores, enum_key(action.ability))
    modifier = ability_modifier(ability_score) + action.toHitBonus
    created_at = time_ns()
    if action.proficient:
        modifier += sheet.proficiencyBonus

    dice = [random.randint(1, 20)]
    return RollPayload(
        id=f"roll-{created_at}",
        sheetId=sheet.id,
        tokenId=sheet.tokenId,
        roller=roller,
        source=RollSource(section=SheetSectionType.ATTACKS, sourceId=action.id, actionId=enum_key(RollResolutionMode.ATTACK_VS_ARMOR_CLASS)),
        sourceLabel=action.name,
        resolution=RollResolutionMode.ATTACK_VS_ARMOR_CLASS,
        label="Attack Roll",
        iconUrl=None,
        dice=dice,
        diceType=DiceType.D20,
        die=enum_key(DiceType.D20),
        modifier=modifier,
        total=sum(dice) + modifier,
        createdAt=created_at,
    )


def build_damage_roll_payload(sheet: CharacterSheet, roller: str, action: AttackAction) -> RollPayload:
    ability_score = getattr(sheet.abilityScores, enum_key(action.ability))
    modifier = ability_modifier(ability_score) + action.toHitBonus + action.damageBonus
    count = action.damageDiceCount
    sides = action.damageDiceType.value
    dice = [random.randint(1, sides) for _ in range(count)]
    created_at = time_ns()
    return RollPayload(
        id=f"roll-{created_at}",
        sheetId=sheet.id,
        tokenId=sheet.tokenId,
        roller=roller,
        source=RollSource(section=SheetSectionType.ATTACKS, sourceId=action.id, actionId=enum_key(RollResolutionMode.APPLY_DAMAGE)),
        sourceLabel=action.name,
        resolution=RollResolutionMode.APPLY_DAMAGE,
        label="Damage Roll",
        iconUrl=None,
        dice=dice,
        diceType=action.damageDiceType,
        die=damage_die_formula(action),
        modifier=modifier,
        total=sum(dice) + modifier,
        createdAt=created_at,
    )


def build_roll_action_payload(sheet: CharacterSheet, roller: str, source: RollSource, action: RollAction) -> RollPayload:
    dice = [random.randint(1, action.diceType.value) for _ in range(action.diceCount)]
    modifier = roll_action_modifier(sheet, action)
    created_at = time_ns()
    return RollPayload(
        id=f"roll-{created_at}",
        sheetId=sheet.id,
        tokenId=sheet.tokenId,
        roller=roller,
        source=source,
        sourceLabel=enum_label(action.name),
        resolution=action.resolution,
        label=enum_label(action.name),
        iconUrl=None,
        dice=dice,
        diceType=action.diceType,
        die=dice_formula(action.diceCount, action.diceType),
        modifier=modifier,
        total=sum(dice) + modifier,
        createdAt=created_at,
    )


def roll_action_modifier(sheet: CharacterSheet, action: RollAction) -> int:
    if action.modifier == RollModifierType.CLASS_LEVEL:
        return sheet.characterClass.level + action.staticModifier
    if action.modifier == RollModifierType.PROFICIENCY_BONUS:
        return sheet.proficiencyBonus + action.staticModifier
    return action.staticModifier


def resolve_roll_against_target(roll: RollPayload, target: CharacterSheet) -> RollResolution:
    if roll.resolution == RollResolutionMode.ATTACK_VS_ARMOR_CLASS:
        outcome = "hits" if roll.total >= target.armorClass else "misses"
        target_hp = target.hp
    elif roll.resolution == RollResolutionMode.APPLY_DAMAGE:
        next_hp = max(0, target.hp.current - max(0, roll.total))
        target_hp = HitPoints(current=next_hp, max=target.hp.max, temporary=target.hp.temporary)
        outcome = f"deals {roll.total} damage"
    elif roll.resolution == RollResolutionMode.HEAL_SELF:
        next_hp = min(target.hp.max, target.hp.current + max(0, roll.total))
        target_hp = HitPoints(current=next_hp, max=target.hp.max, temporary=target.hp.temporary)
        outcome = f"heals {roll.total} hit points"
    else:
        target_hp = target.hp
        outcome = f"rolls {roll.total}"

    return RollResolution(
        id=f"resolution-{time_ns()}",
        roll=roll,
        targetSheetId=target.id,
        targetTokenId=target.tokenId,
        targetName=target.name,
        targetArmorClass=target.armorClass,
        targetHp=target_hp,
        outcome=outcome,
        createdAt=time_ns(),
    )


def generated_ability_scores(seed: str) -> AbilityScores:
    rng = random.Random(seed)
    return AbilityScores(
        strength=rng.randint(8, 15),
        dexterity=rng.randint(8, 15),
        constitution=rng.randint(8, 15),
        intelligence=rng.randint(8, 15),
        wisdom=rng.randint(8, 15),
        charisma=rng.randint(8, 15),
    )


def generated_max_hp(seed: str, ability_scores: AbilityScores) -> int:
    rng = random.Random(f"{seed}:hp")
    return max(1, rng.randint(8, 24) + ability_modifier(ability_scores.constitution))


def ability_modifier(score: int) -> int:
    return (score - 10) // 2


def proficiency_bonus_for_level(level: int) -> int:
    return 2 + max(0, min(19, level - 1)) // 4


def ability_modifier_map(ability_scores: AbilityScores) -> dict[str, int]:
    return {enum_key(ability): ability_modifier(getattr(ability_scores, enum_key(ability))) for ability in ABILITY_NAMES}


def build_saving_throws(ability_modifiers: dict[str, int], proficient_abilities: set[AbilityType], proficiency_bonus: int) -> list[SavingThrowBonus]:
    return [
        SavingThrowBonus(
            ability=ability,
            proficient=ability in proficient_abilities,
            modifier=ability_modifiers[enum_key(ability)] + (proficiency_bonus if ability in proficient_abilities else 0),
        )
        for ability in ABILITY_NAMES
    ]


def build_skills(ability_modifiers: dict[str, int], skill_proficiencies: dict[str, ProficiencyLevel], proficiency_bonus: int) -> list[SkillBonus]:
    return [
        SkillBonus(
            name=skill,
            ability=ability,
            proficiency=skill_proficiencies.get(skill, ProficiencyLevel.NONE),
            modifier=ability_modifiers[enum_key(ability)] + proficiency_multiplier(skill_proficiencies.get(skill, ProficiencyLevel.NONE)) * proficiency_bonus,
            passive=10 + ability_modifiers[enum_key(ability)] + proficiency_multiplier(skill_proficiencies.get(skill, ProficiencyLevel.NONE)) * proficiency_bonus,
        )
        for skill, ability in SKILL_ABILITIES.items()
    ]


def build_passive_checks(ability_modifiers: dict[str, int], skill_proficiencies: dict[str, ProficiencyLevel], proficiency_bonus: int) -> dict[str, int]:
    skills = build_skills(ability_modifiers, skill_proficiencies, proficiency_bonus)
    return {skill.name: skill.passive for skill in skills if skill.name in {"perception", "investigation", "insight"}}


def proficiency_multiplier(level: ProficiencyLevel | None) -> int:
    if level == ProficiencyLevel.EXPERTISE:
        return 2
    return 1 if level == ProficiencyLevel.PROFICIENT else 0


def default_save_proficiencies(classes: list[CharacterClassLevel]) -> list[AbilityType]:
    primary = classes[0].name if classes else None
    if primary == ClassType.FIGHTER:
        return [AbilityType.STRENGTH, AbilityType.CONSTITUTION]
    return []


def default_attacks(kind: TokenKind) -> list[AttackAction]:
    return [
        AttackAction(
            id="main-hand",
            name="Main Hand" if kind == TokenKind.CHARACTER else "Strike",
            ability=AbilityType.STRENGTH,
            damageDiceCount=1,
            damageDiceType=DiceType.D8,
            properties=[],
        )
    ]


def default_resources(classes: list[CharacterClassLevel]) -> list[ResourceTracker]:
    from dnd_board.rules.fighter import fighter_resources

    return fighter_resources(classes)


def resource_roll_abilities(resources: list[ResourceTracker]) -> list[SheetAbility]:
    abilities: list[SheetAbility] = []
    for resource in resources:
        for action in resource.rollActions or []:
            abilities.append(
                SheetAbility(
                    id=enum_key(action.id),
                    name=enum_label(action.name),
                    source=resource.name,
                    activation=resource.activation,
                    description=dice_formula(action.diceCount, action.diceType),
                    resourceId=resource.id,
                    rollActions=[action],
                )
            )
    return abilities


def apply_resource_overrides(resources: list[ResourceTracker], overrides: dict[str, int]) -> list[ResourceTracker]:
    return [
        ResourceTracker(
            id=resource.id,
            name=resource.name,
            currentUses=clamp_int(overrides.get(resource.id, resource.currentUses), 0, resource.maxUses),
            maxUses=resource.maxUses,
            reset=resource.reset,
            activation=resource.activation,
            description=resource.description,
            rollActions=resource.rollActions,
        )
        for resource in resources
    ]


def default_features(classes: list[CharacterClassLevel]) -> list[SheetFeature]:
    from dnd_board.rules.fighter import fighter_features

    return fighter_features(classes)


def default_feat_abilities(classes: list[CharacterClassLevel]) -> list[SheetAbility]:
    from dnd_board.rules.feats import feat_abilities

    return feat_abilities(classes)


def default_armor_class_bonus(classes: list[CharacterClassLevel]) -> int:
    from dnd_board.rules.feats import armor_class_bonus

    return armor_class_bonus(classes)


def party_manifest_from_dict(value: Any) -> PartyManifest | None:
    loaded = typed_json_to_value(value, PartyManifest)
    return loaded if isinstance(loaded, PartyManifest) else None


def typed_json_to_value(node: Any, expected_type: Any = Any) -> Any:
    if not isinstance(node, dict) or TYPE_KEY not in node:
        return None

    expected_type = non_null_type(expected_type)
    type_name = str(node.get(TYPE_KEY))
    if type_name == "None":
        return None
    if type_name == "list":
        expected_item_type = Any
        if get_origin(expected_type) is list:
            expected_args = get_args(expected_type)
            expected_item_type = expected_args[0] if expected_args else Any
        items = node.get(ITEMS_KEY)
        if not isinstance(items, list):
            return None
        return [typed_json_to_value(item, expected_item_type) for item in items]
    if type_name.startswith("dict"):
        expected_value_type = Any
        if get_origin(expected_type) is dict:
            expected_args = get_args(expected_type)
            expected_value_type = expected_args[1] if len(expected_args) > 1 else Any
        raw_items = node.get(VALUE_KEY)
        if not isinstance(raw_items, dict):
            return None
        return {str(key): typed_json_to_value(item, expected_value_type) for key, item in raw_items.items()}
    if type_name in {"str", "int", "float", "bool"}:
        value = typed_primitive_value(type_name, node.get(VALUE_KEY))
        return value if value_matches_type(value, expected_type) else None

    registry = typed_json_registry()
    model_type = registry.get(type_name)
    if model_type is None:
        return None
    if isinstance(model_type, type) and issubclass(model_type, Enum):
        value = enum_value(model_type, node.get(VALUE_KEY))
        return value if value_matches_type(value, expected_type) else None
    if isinstance(model_type, type) and is_dataclass(model_type):
        value = typed_dataclass_from_json(model_type, node)
        return value if value_matches_type(value, expected_type) else None
    return None


def non_null_type(expected_type: Any) -> Any:
    origin = get_origin(expected_type)
    if origin not in {Union, UnionType}:
        return expected_type
    options = [option for option in get_args(expected_type) if option is not type(None)]
    return options[0] if len(options) == 1 else expected_type


def value_matches_type(value: Any, expected_type: Any) -> bool:
    if value is None:
        return False
    if expected_type is Any:
        return True

    origin = get_origin(expected_type)
    if origin in {Union, UnionType}:
        return any(value_matches_type(value, option) for option in get_args(expected_type) if option is not type(None))
    if origin is list:
        return isinstance(value, list)
    if origin is dict:
        return isinstance(value, dict)
    if not isinstance(expected_type, type):
        return True
    if expected_type is bool:
        return isinstance(value, bool)
    if expected_type is int:
        return isinstance(value, int) and not isinstance(value, bool)
    if expected_type is float:
        return isinstance(value, float)
    return isinstance(value, expected_type)


def typed_dataclass_from_json(model_type: type[Any], node: dict[str, Any]) -> Any | None:
    raw_fields = node.get(FIELDS_KEY)
    if not isinstance(raw_fields, dict):
        return None

    type_hints = get_type_hints(model_type)
    kwargs: dict[str, Any] = {}
    for field in fields(model_type):
        if field.name not in raw_fields:
            continue
        raw_value = raw_fields[field.name]
        converted = typed_json_to_value(raw_value, type_hints.get(field.name, field.type))
        if converted is not None:
            kwargs[field.name] = converted

    try:
        return model_type(**kwargs)
    except (TypeError, ValueError):
        return None


def typed_primitive_value(type_name: str, value: Any) -> Any:
    if type_name == "str" and isinstance(value, str):
        return value
    if type_name == "int" and isinstance(value, int) and not isinstance(value, bool):
        return value
    if type_name == "float" and isinstance(value, float):
        return value
    if type_name == "bool" and isinstance(value, bool):
        return value
    return None


def typed_json_registry() -> dict[str, type[Any]]:
    from dnd_board.rules.fighter import FighterSubclassType

    return {
        type_.__name__: type_
        for type_ in [
            AbilityScores,
            AbilityType,
            AttackAction,
            CharacterClassLevel,
            ClassType,
            DamageType,
            DiceType,
            EquipmentItem,
            FightingStyleType,
            FighterSubclassType,
            PartyManifest,
            PartyMemberConfig,
            PartyMemberSheet,
            ProficiencyLevel,
            RestType,
            RollAction,
            RollModifierType,
            RollResolutionMode,
            ResourceTracker,
            SheetFeature,
            SheetAbility,
            TimeEconomy,
        ]
    }


def typed_json_from_value(value: Any) -> dict[str, Any]:
    if value is None:
        return {TYPE_KEY: "None", VALUE_KEY: None}
    if isinstance(value, Enum):
        return {TYPE_KEY: value.__class__.__name__, VALUE_KEY: value.name}
    if isinstance(value, list):
        return {TYPE_KEY: "list", ITEMS_KEY: [typed_json_from_value(item) for item in value]}
    if isinstance(value, dict):
        return {
            TYPE_KEY: "dict",
            VALUE_KEY: {str(key): typed_json_from_value(item) for key, item in value.items()},
        }
    if isinstance(value, str):
        return {TYPE_KEY: "str", VALUE_KEY: value}
    if isinstance(value, bool):
        return {TYPE_KEY: "bool", VALUE_KEY: value}
    if isinstance(value, int):
        return {TYPE_KEY: "int", VALUE_KEY: value}
    if isinstance(value, float):
        return {TYPE_KEY: "float", VALUE_KEY: value}
    if is_dataclass(value):
        return {
            TYPE_KEY: value.__class__.__name__,
            FIELDS_KEY: {
                field.name: typed_json_from_value(getattr(value, field.name))
                for field in fields(value)
                if getattr(value, field.name) is not None
            },
        }
    raise TypeError(f"Unsupported typed JSON value: {value.__class__.__name__}")


def sheet_to_dict(sheet: CharacterSheet) -> dict[str, Any]:
    return serialize_dataclass(sheet)


def roll_payload_to_dict(payload: RollPayload) -> dict[str, Any]:
    return serialize_dataclass(payload)


def roll_resolution_to_dict(resolution: RollResolution) -> dict[str, Any]:
    return serialize_dataclass(resolution)


def serialize_dataclass(value: Any) -> Any:
    return serialize_value(value)


def serialize_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return enum_key(value)
    if isinstance(value, list):
        return [serialize_value(item) for item in value]
    if isinstance(value, dict):
        return {key: serialize_value(item) for key, item in value.items()}
    if hasattr(value, "__dataclass_fields__"):
        data: dict[str, Any] = {}
        for field in fields(value):
            field_value = getattr(value, field.name)
            if field_value is None:
                continue
            data[field.name] = serialize_value(field_value)
            field_label = serialize_label_value(field_value)
            if field_label is not None:
                data[f"{field.name}Label"] = field_label
        for key, computed_value in computed_api_values(value).items():
            data[key] = serialize_value(computed_value)
        return data
    return value


def serialize_label_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return enum_label(value)
    if isinstance(value, list) and value and all(isinstance(item, Enum) for item in value):
        return [enum_label(item) for item in value]
    return None


def computed_api_values(value: Any) -> dict[str, Any]:
    return {
        name: getattr(value, name)
        for name, attribute in vars(value.__class__).items()
        if isinstance(attribute, property) and attribute.fget is not None and getattr(attribute.fget, "__api_field__", False)
    }


def enum_value(enum_type: type[Enum], value: Any) -> Any:
    if value is None:
        return None
    normalized = str(value).strip().replace("-", "_").replace(" ", "_").upper()
    for member in enum_type:
        if normalized in {member.name, enum_key(member).upper(), enum_label(member).replace(" ", "_").upper()}:
            return member
    return None


def enum_key(member: Enum) -> str:
    return UIStringFormatter.lower_camel(member.name)


def enum_label(member: Enum) -> str:
    return UIStringFormatter.clean_name(member.name)


def damage_die_formula(attack: AttackAction) -> str:
    return dice_formula(attack.damageDiceCount, attack.damageDiceType)


def dice_formula(count: int, dice_type: DiceType) -> str:
    return f"{count}d{dice_type.value}"


def clamped_ability_score(value: Any) -> int:
    score = int(value)
    if score < 1 or score > 30:
        raise ValueError("Ability scores must be between 1 and 30")
    return score


def positive_int(value: Any) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def optional_text(value: Any, limit: int) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text[:limit] if text else None


def text_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [text for item in value if (text := optional_text(item, 80)) is not None]


def sanitize_identifier(value: str) -> str:
    return "".join(character for character in value.strip().lower() if character.isalnum() or character == "-")[:60]


def to_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0


def clamp_int(value: int, minimum: int, maximum: int) -> int:
    return min(maximum, max(minimum, value))
