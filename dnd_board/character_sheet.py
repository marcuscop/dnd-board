from __future__ import annotations

import random
from dataclasses import asdict, dataclass
from enum import Enum, auto
from time import time_ns
from typing import Any, Literal

TokenKind = Literal["character", "asset"]
RollKind = Literal["attack", "damage"]


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
    DEFENSE = auto()
    DUELING = auto()
    GREAT_WEAPON_FIGHTING = auto()
    TWO_WEAPON_FIGHTING = auto()


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


@dataclass
class CharacterClassLevel:
    name: ClassType
    level: int
    subclass: Enum | None = None
    fightingStyle: FightingStyleType | None = None


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


@dataclass
class SheetFeature:
    id: str
    name: str
    source: str
    activation: TimeEconomy
    description: str


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
    kind: RollKind
    label: str
    iconUrl: str | None
    action: AttackAction
    dice: list[int]
    die: str
    modifier: int
    total: int
    createdAt: int


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
    classes = sheet_config.classes if sheet_config and sheet_config.classes else [CharacterClassLevel(name=ClassType.ADVENTURER if kind == "character" else ClassType.CREATURE, level=1)]
    total_level = sum(character_class.level for character_class in classes) or 1
    primary_class = classes[0]
    proficiency_bonus = sheet_config.proficiencyBonus if sheet_config and sheet_config.proficiencyBonus is not None else proficiency_bonus_for_level(total_level)
    ability_modifiers = ability_modifier_map(ability_scores)
    skill_proficiencies = sheet_config.skills if sheet_config and sheet_config.skills else {}
    save_proficiencies = set(sheet_config.savingThrowProficiencies if sheet_config and sheet_config.savingThrowProficiencies else default_save_proficiencies(classes))
    resources = apply_resource_overrides(sheet_config.resources if sheet_config and sheet_config.resources else default_resources(classes), resource_overrides)
    features = default_features(classes)
    if sheet_config:
        features = [*(sheet_config.traits or []), *features, *(sheet_config.features or []), *(sheet_config.feats or [])]

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
        armorClass=sheet_config.armorClass if sheet_config and sheet_config.armorClass is not None else 12 + min(3, dexterity_modifier),
        initiativeBonus=dexterity_modifier,
        speed=sheet_config.speed if sheet_config and sheet_config.speed is not None else 30,
        savingThrows=build_saving_throws(ability_modifiers, save_proficiencies, proficiency_bonus),
        skills=build_skills(ability_modifiers, skill_proficiencies, proficiency_bonus),
        passiveChecks=build_passive_checks(ability_modifiers, skill_proficiencies, proficiency_bonus),
        resources=resources,
        features=features,
        proficiencies=sheet_config.proficiencies if sheet_config and sheet_config.proficiencies else [],
        conditions=[],
        attacks=sheet_config.attacks if sheet_config and sheet_config.attacks else default_attacks(kind),
        equipment=sheet_config.equipment if sheet_config and sheet_config.equipment else [],
    )


def build_roll_payload(sheet: CharacterSheet, roller: str, action: AttackAction, roll_kind: RollKind) -> RollPayload:
    ability_score = getattr(sheet.abilityScores, enum_key(action.ability))
    modifier = ability_modifier(ability_score) + action.toHitBonus
    created_at = time_ns()
    if roll_kind == "attack":
        dice = [random.randint(1, 20)]
        die = "d20"
        label = "Attack Roll"
        icon_url = None
        if action.proficient:
            modifier += sheet.proficiencyBonus
    else:
        count = action.damageDiceCount
        sides = action.damageDiceType.value
        dice = [random.randint(1, sides) for _ in range(count)]
        die = damage_die_formula(action)
        label = "Damage Roll"
        icon_url = None
        modifier += action.damageBonus

    return RollPayload(
        id=f"roll-{created_at}",
        sheetId=sheet.id,
        tokenId=sheet.tokenId,
        roller=roller,
        kind=roll_kind,
        label=label,
        iconUrl=icon_url,
        action=action,
        dice=dice,
        die=die,
        modifier=modifier,
        total=sum(dice) + modifier,
        createdAt=created_at,
    )


def resolve_roll_against_target(roll: RollPayload, target: CharacterSheet) -> RollResolution:
    if roll.kind == "attack":
        outcome = "hits" if roll.total >= target.armorClass else "misses"
        target_hp = target.hp
    else:
        next_hp = max(0, target.hp.current - max(0, roll.total))
        target_hp = HitPoints(current=next_hp, max=target.hp.max, temporary=target.hp.temporary)
        outcome = f"deals {roll.total} damage"

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
            name="Main Hand" if kind == "character" else "Strike",
            ability=AbilityType.STRENGTH,
            damageDiceCount=1,
            damageDiceType=DiceType.D8,
            properties=[],
        )
    ]


def default_resources(classes: list[CharacterClassLevel]) -> list[ResourceTracker]:
    from dnd_board.rules.fighter import fighter_resources

    return fighter_resources(classes)


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
        )
        for resource in resources
    ]


def default_features(classes: list[CharacterClassLevel]) -> list[SheetFeature]:
    from dnd_board.rules.fighter import fighter_features

    return fighter_features(classes)


def party_member_sheet_from_dict(value: Any) -> PartyMemberSheet | None:
    if not isinstance(value, dict):
        return None

    return PartyMemberSheet(
        race=optional_text(value.get("race"), 40),
        background=optional_text(value.get("background"), 40),
        alignment=optional_text(value.get("alignment"), 40),
        classes=classes_from_list(value.get("classes")),
        armorClass=positive_int(value.get("armorClass")),
        speed=positive_int(value.get("speed")),
        proficiencyBonus=positive_int(value.get("proficiencyBonus")),
        skills=skill_proficiencies_from_dict(value.get("skills")),
        savingThrowProficiencies=ability_list_from_values(value.get("savingThrowProficiencies")),
        proficiencies=text_list(value.get("proficiencies")),
        feats=features_from_list(value.get("feats")),
        traits=features_from_list(value.get("traits")),
        features=features_from_list(value.get("features")),
        resources=resources_from_list(value.get("resources")),
        attacks=attacks_from_list(value.get("attacks")),
        equipment=equipment_from_list(value.get("equipment")),
    )


def classes_from_list(value: Any) -> list[CharacterClassLevel] | None:
    if not isinstance(value, list):
        return None

    classes: list[CharacterClassLevel] = []
    for raw_class in value:
        if not isinstance(raw_class, dict):
            continue
        class_type = enum_value(ClassType, raw_class.get("name"))
        level = positive_int(raw_class.get("level"))
        if class_type is None or level is None:
            continue
        classes.append(
            CharacterClassLevel(
                name=class_type,
                level=level,
                subclass=subclass_from_dict(class_type, raw_class.get("subclass")),
                fightingStyle=enum_value(FightingStyleType, raw_class.get("fightingStyle")),
            )
        )
    return classes or None


def subclass_from_dict(class_type: ClassType, value: Any) -> Enum | None:
    if class_type == ClassType.FIGHTER:
        from dnd_board.rules.fighter import FighterSubclassType

        return enum_value(FighterSubclassType, value)
    return None


def skill_proficiencies_from_dict(value: Any) -> dict[str, ProficiencyLevel] | None:
    if not isinstance(value, dict):
        return None

    proficiencies: dict[str, ProficiencyLevel] = {}
    for skill_name in SKILL_ABILITIES:
        proficiency = enum_value(ProficiencyLevel, value.get(skill_name))
        if proficiency is not None and proficiency != ProficiencyLevel.NONE:
            proficiencies[skill_name] = proficiency
    return proficiencies or None


def ability_list_from_values(value: Any) -> list[AbilityType] | None:
    if not isinstance(value, list):
        return None
    abilities = [ability for raw_ability in value if (ability := enum_value(AbilityType, raw_ability)) is not None]
    return abilities or None


def attacks_from_list(value: Any) -> list[AttackAction] | None:
    if not isinstance(value, list):
        return None

    attacks: list[AttackAction] = []
    for raw_attack in value:
        if not isinstance(raw_attack, dict):
            continue
        attack_id = sanitize_identifier(str(raw_attack.get("id", "")))
        ability = enum_value(AbilityType, raw_attack.get("ability"))
        if not attack_id or ability is None:
            continue
        dice_count, dice_type = damage_dice_from_dict(raw_attack)
        attacks.append(
            AttackAction(
                id=attack_id,
                name=optional_text(raw_attack.get("name"), 60) or UIStringFormatter.clean_name(attack_id),
                ability=ability,
                damageDiceCount=dice_count,
                damageDiceType=dice_type,
                proficient=bool(raw_attack.get("proficient", True)),
                damageType=enum_value(DamageType, raw_attack.get("damageType")) or DamageType.SLASHING,
                toHitBonus=safe_int(raw_attack.get("toHitBonus"), 0),
                damageBonus=safe_int(raw_attack.get("damageBonus"), 0),
                activation=enum_value(TimeEconomy, raw_attack.get("activation")) or TimeEconomy.ACTION,
                properties=text_list(raw_attack.get("properties")),
            )
        )
    return attacks or None


def damage_dice_from_dict(value: dict[str, Any]) -> tuple[int, DiceType]:
    explicit_type = enum_value(DiceType, value.get("damageDiceType"))
    explicit_count = positive_int(value.get("damageDiceCount"))
    if explicit_type is not None:
        return explicit_count or 1, explicit_type

    raw_formula = value.get("damageDie")
    if raw_formula is not None:
        parsed = parse_damage_die(str(raw_formula))
        if parsed is not None:
            return parsed

    return 1, DiceType.D8


def parse_damage_die(value: str) -> tuple[int, DiceType] | None:
    try:
        count_text, sides_text = value.lower().split("d", 1)
        count = int(count_text or "1")
        dice_type = DiceType(int(sides_text))
    except (ValueError, TypeError):
        return None
    return (count, dice_type) if 1 <= count <= 20 else None


def resources_from_list(value: Any) -> list[ResourceTracker] | None:
    if not isinstance(value, list):
        return None

    resources: list[ResourceTracker] = []
    for raw_resource in value:
        if not isinstance(raw_resource, dict):
            continue
        resource_id = sanitize_identifier(str(raw_resource.get("id", "")))
        max_uses = positive_int(raw_resource.get("maxUses"))
        if not resource_id or max_uses is None:
            continue
        resources.append(
            ResourceTracker(
                id=resource_id,
                name=optional_text(raw_resource.get("name"), 60) or UIStringFormatter.clean_name(resource_id),
                currentUses=clamp_int(safe_int(raw_resource.get("currentUses"), max_uses), 0, max_uses),
                maxUses=max_uses,
                reset=enum_value(RestType, raw_resource.get("reset")) or RestType.SHORT_REST,
                activation=enum_value(TimeEconomy, raw_resource.get("activation")) or TimeEconomy.SPECIAL,
                description=optional_text(raw_resource.get("description"), 240) or "",
            )
        )
    return resources or None


def features_from_list(value: Any) -> list[SheetFeature] | None:
    if not isinstance(value, list):
        return None

    features: list[SheetFeature] = []
    for raw_feature in value:
        if not isinstance(raw_feature, dict):
            continue
        feature_id = sanitize_identifier(str(raw_feature.get("id", "")))
        if not feature_id:
            continue
        features.append(
            SheetFeature(
                id=feature_id,
                name=optional_text(raw_feature.get("name"), 80) or UIStringFormatter.clean_name(feature_id),
                source=optional_text(raw_feature.get("source"), 40) or "",
                activation=enum_value(TimeEconomy, raw_feature.get("activation")) or TimeEconomy.PASSIVE,
                description=optional_text(raw_feature.get("description"), 320) or "",
            )
        )
    return features or None


def equipment_from_list(value: Any) -> list[EquipmentItem] | None:
    if not isinstance(value, list):
        return None
    items: list[EquipmentItem] = []
    for raw_item in value:
        if not isinstance(raw_item, dict):
            continue
        item_id = sanitize_identifier(str(raw_item.get("id", "")))
        if not item_id:
            continue
        items.append(
            EquipmentItem(
                id=item_id,
                name=optional_text(raw_item.get("name"), 80) or UIStringFormatter.clean_name(item_id),
                equipped=bool(raw_item.get("equipped", False)),
                quantity=positive_int(raw_item.get("quantity")) or 1,
                weight=to_float(raw_item.get("weight", 0)),
                notes=optional_text(raw_item.get("notes"), 160) or "",
            )
        )
    return items or None


def ability_scores_from_dict(value: Any) -> AbilityScores | None:
    if not isinstance(value, dict):
        return None

    try:
        return AbilityScores(
            strength=clamped_ability_score(value.get("strength")),
            dexterity=clamped_ability_score(value.get("dexterity")),
            constitution=clamped_ability_score(value.get("constitution")),
            intelligence=clamped_ability_score(value.get("intelligence")),
            wisdom=clamped_ability_score(value.get("wisdom")),
            charisma=clamped_ability_score(value.get("charisma")),
        )
    except (TypeError, ValueError):
        return None


def sheet_to_dict(sheet: CharacterSheet) -> dict[str, Any]:
    data = serialize_dataclass(sheet)
    data["characterClass"]["name"] = enum_label(sheet.characterClass.name)
    for index, character_class in enumerate(sheet.classes):
        data["classes"][index]["name"] = enum_label(character_class.name)
        if character_class.subclass is not None:
            data["classes"][index]["subclass"] = enum_label(character_class.subclass)
        if character_class.fightingStyle is not None:
            data["classes"][index]["fightingStyle"] = enum_label(character_class.fightingStyle)
    for index, resource in enumerate(sheet.resources):
        data["resources"][index]["activationLabel"] = enum_label(resource.activation)
        data["resources"][index]["resetLabel"] = enum_label(resource.reset)
    for index, feature in enumerate(sheet.features):
        data["features"][index]["activationLabel"] = enum_label(feature.activation)
    for index, attack in enumerate(sheet.attacks):
        data["attacks"][index]["abilityLabel"] = enum_label(attack.ability)
        data["attacks"][index]["damageTypeLabel"] = enum_label(attack.damageType)
        data["attacks"][index]["activationLabel"] = enum_label(attack.activation)
        data["attacks"][index]["damageDie"] = damage_die_formula(attack)
    if data.get("avatarUrl") is None:
        data.pop("avatarUrl")
    return data


def roll_payload_to_dict(payload: RollPayload) -> dict[str, Any]:
    data = serialize_dataclass(payload)
    data["action"]["damageDie"] = damage_die_formula(payload.action)
    return data


def roll_resolution_to_dict(resolution: RollResolution) -> dict[str, Any]:
    return serialize_dataclass(resolution)


def serialize_dataclass(value: Any) -> Any:
    if isinstance(value, Enum):
        return enum_key(value)
    if isinstance(value, list):
        return [serialize_dataclass(item) for item in value]
    if isinstance(value, dict):
        return {key: serialize_dataclass(item) for key, item in value.items()}
    if hasattr(value, "__dataclass_fields__"):
        return {key: serialize_dataclass(item) for key, item in asdict(value).items()}
    return value


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
    return f"{attack.damageDiceCount}d{attack.damageDiceType.value}"


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
