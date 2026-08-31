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
from dnd_board.rules.sources import RuleSource, is_legacy_source, rule_source_label


class FeatCategory(Enum):
    GENERAL = auto()
    FIGHTING_STYLE = auto()


class GeneralFeatType(Enum):
    ACTOR = auto()
    ALERT = auto()
    ARTIFICER_INITIATE = auto()
    ATHLETE = auto()
    BOUNTIFUL_LUCK = auto()
    CHARGER = auto()
    CHEF = auto()
    CROSSBOW_EXPERT = auto()
    CRUSHER = auto()
    DEFENSIVE_DUELIST = auto()
    DRAGON_FEAR = auto()
    DRAGON_HIDE = auto()
    DROW_HIGH_MAGIC = auto()
    DUAL_WIELDER = auto()
    DUNGEON_DELVER = auto()
    DURABLE = auto()
    DWARF_FORTITUDE = auto()
    ELDRITCH_ADEPT = auto()
    ELEMENTAL_ADEPT = auto()
    ELVEN_ACCURACY = auto()
    EMBER_OF_THE_FIRE_GIANT = auto()
    FADE_AWAY = auto()
    FEY_TELEPORTATION = auto()
    FEY_TOUCHED = auto()
    FIGHTING_INITIATE = auto()
    FLAMES_OF_PHLEGETHOS = auto()
    FURY_OF_THE_FROST_GIANT = auto()
    GIFT_OF_THE_CHROMATIC_DRAGON = auto()
    GIFT_OF_THE_GEM_DRAGON = auto()
    GIFT_OF_THE_METALLIC_DRAGON = auto()
    GRAPPLER = auto()
    GREAT_WEAPON_MASTER = auto()
    GUILE_OF_THE_CLOUD_GIANT = auto()
    GUNNER = auto()
    HEALER = auto()
    HEAVILY_ARMORED = auto()
    HEAVY_ARMOR_MASTER = auto()
    INFERNAL_CONSTITUTION = auto()
    INSPIRING_LEADER = auto()
    KEEN_MIND = auto()
    KEENNESS_OF_THE_STONE_GIANT = auto()
    LIGHTLY_ARMORED = auto()
    LINGUIST = auto()
    LUCKY = auto()
    MAGE_SLAYER = auto()
    MAGIC_INITIATE = auto()
    MARTIAL_ADEPT = auto()
    MEDIUM_ARMOR_MASTER = auto()
    METAMAGIC_ADEPT = auto()
    MOBILE = auto()
    MODERATELY_ARMORED = auto()
    MOUNTED_COMBATANT = auto()
    OBSERVANT = auto()
    ORCISH_FURY = auto()
    PIERCER = auto()
    POISONER = auto()
    POLEARM_MASTER = auto()
    PRODIGY = auto()
    RESILIENT = auto()
    RITUAL_CASTER = auto()
    RUNE_SHAPER = auto()
    SAVAGE_ATTACKER = auto()
    SECOND_CHANCE = auto()
    SENTINEL = auto()
    SHADOW_TOUCHED = auto()
    SHARPSHOOTER = auto()
    SHIELD_MASTER = auto()
    SKILL_EXPERT = auto()
    SKILLED = auto()
    SKULKER = auto()
    SLASHER = auto()
    SOUL_OF_THE_STORM_GIANT = auto()
    SPELL_SNIPER = auto()
    SQUAT_NIMBLENESS = auto()
    STRIKE_OF_THE_GIANTS = auto()
    TAVERN_BRAWLER = auto()
    TELEKINETIC = auto()
    TELEPATHIC = auto()
    TOUGH = auto()
    VIGOR_OF_THE_HILL_GIANT = auto()
    WAR_CASTER = auto()
    WEAPON_MASTER = auto()
    WOOD_ELF_MAGIC = auto()


class FeatEffectType(Enum):
    ARMOR_CLASS_BONUS = auto()
    ATTACK_ROLL_BONUS = auto()
    DAMAGE_DICE_REROLL = auto()
    DAMAGE_ABILITY_MODIFIER = auto()
    DAMAGE_ROLL_BONUS = auto()
    ROLL_ABILITY = auto()
    SHEET_ABILITY = auto()
    DESCRIPTION_ONLY = auto()
    RESOURCE = auto()


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
    source: RuleSource = RuleSource.PLAYERS_HANDBOOK_2024


FIGHTING_STYLE_SOURCES: dict[FightingStyleType, RuleSource] = {
    FightingStyleType.ARCHERY: RuleSource.PLAYERS_HANDBOOK_2024,
    FightingStyleType.BLIND_FIGHTING: RuleSource.PLAYERS_HANDBOOK_2024,
    FightingStyleType.DEFENSE: RuleSource.PLAYERS_HANDBOOK_2024,
    FightingStyleType.DUELING: RuleSource.PLAYERS_HANDBOOK_2024,
    FightingStyleType.GREAT_WEAPON_FIGHTING: RuleSource.PLAYERS_HANDBOOK_2024,
    FightingStyleType.INTERCEPTION: RuleSource.PLAYERS_HANDBOOK_2024,
    FightingStyleType.PACK_FIGHTING: RuleSource.DND_BEYOND_DROPS_2026,
    FightingStyleType.PRONE_FIGHTING: RuleSource.DND_BEYOND_DROPS_2026,
    FightingStyleType.PROTECTION: RuleSource.PLAYERS_HANDBOOK_2024,
    FightingStyleType.THROWN_WEAPON_FIGHTING: RuleSource.PLAYERS_HANDBOOK_2024,
    FightingStyleType.TWO_WEAPON_FIGHTING: RuleSource.PLAYERS_HANDBOOK_2024,
    FightingStyleType.UNARMED_FIGHTING: RuleSource.PLAYERS_HANDBOOK_2024,
}


def fighting_style_label(style: FightingStyleType) -> str:
    label = enum_label(style)
    return f"{label} (Legacy)" if is_legacy_source(fighting_style_source(style)) else label


def fighting_style_source(style: FightingStyleType) -> RuleSource:
    return FIGHTING_STYLE_SOURCES.get(style, RuleSource.LEGACY)


@dataclass(frozen=True)
class GeneralFeatDefinition:
    featType: GeneralFeatType
    source: str
    prerequisite: str
    description: str
    repeatable: bool = False


def general_feat(feat_type: GeneralFeatType, source: str, description: str, prerequisite: str = "-", repeatable: bool = False) -> GeneralFeatDefinition:
    return GeneralFeatDefinition(featType=feat_type, source=source, prerequisite=prerequisite, description=description, repeatable=repeatable)


GENERAL_FEATS: dict[GeneralFeatType, GeneralFeatDefinition] = {
    GeneralFeatType.ACTOR: general_feat(GeneralFeatType.ACTOR, "Player's Handbook", "+1 Charisma; improve deception, performance, and mimicry."),
    GeneralFeatType.ALERT: general_feat(GeneralFeatType.ALERT, "Player's Handbook", "+5 initiative, cannot be surprised, and unseen attackers do not gain advantage."),
    GeneralFeatType.ARTIFICER_INITIATE: general_feat(GeneralFeatType.ARTIFICER_INITIATE, "Tasha's Cauldron of Everything", "Learn artificer magic and one artisan tool proficiency."),
    GeneralFeatType.ATHLETE: general_feat(GeneralFeatType.ATHLETE, "Player's Handbook", "+1 Strength or Dexterity; improve climbing, standing, and jumping."),
    GeneralFeatType.BOUNTIFUL_LUCK: general_feat(GeneralFeatType.BOUNTIFUL_LUCK, "Xanathar's Guide to Everything", "Let a nearby ally reroll a 1 on a d20.", "Halfling"),
    GeneralFeatType.CHARGER: general_feat(GeneralFeatType.CHARGER, "Player's Handbook", "Dash into a melee attack with an added bonus after moving far enough."),
    GeneralFeatType.CHEF: general_feat(GeneralFeatType.CHEF, "Tasha's Cauldron of Everything", "+1 Constitution or Wisdom; gain cook's utensils and prepare restorative food."),
    GeneralFeatType.CROSSBOW_EXPERT: general_feat(GeneralFeatType.CROSSBOW_EXPERT, "Player's Handbook", "Improve crossbow handling and close-range ranged attacks."),
    GeneralFeatType.CRUSHER: general_feat(GeneralFeatType.CRUSHER, "Tasha's Cauldron of Everything", "+1 Strength or Constitution; add control and critical riders to bludgeoning hits."),
    GeneralFeatType.DEFENSIVE_DUELIST: general_feat(GeneralFeatType.DEFENSIVE_DUELIST, "Player's Handbook", "Use a reaction with a finesse weapon to add proficiency bonus to AC.", "Dexterity 13 or higher"),
    GeneralFeatType.DRAGON_FEAR: general_feat(GeneralFeatType.DRAGON_FEAR, "Xanathar's Guide to Everything", "+1 Strength, Constitution, or Charisma; turn Breath Weapon into fear.", "Dragonborn"),
    GeneralFeatType.DRAGON_HIDE: general_feat(GeneralFeatType.DRAGON_HIDE, "Xanathar's Guide to Everything", "+1 Strength, Constitution, or Charisma; gain natural armor and claws.", "Dragonborn"),
    GeneralFeatType.DROW_HIGH_MAGIC: general_feat(GeneralFeatType.DROW_HIGH_MAGIC, "Xanathar's Guide to Everything", "Gain drow innate spells.", "Elf (drow)"),
    GeneralFeatType.DUAL_WIELDER: general_feat(GeneralFeatType.DUAL_WIELDER, "Player's Handbook", "Improve AC, weapon options, and drawing weapons while dual wielding."),
    GeneralFeatType.DUNGEON_DELVER: general_feat(GeneralFeatType.DUNGEON_DELVER, "Player's Handbook", "Improve trap detection, trap saves, and dungeon exploration."),
    GeneralFeatType.DURABLE: general_feat(GeneralFeatType.DURABLE, "Player's Handbook", "+1 Constitution; improve healing from Hit Dice."),
    GeneralFeatType.DWARF_FORTITUDE: general_feat(GeneralFeatType.DWARF_FORTITUDE, "Xanathar's Guide to Everything", "+1 Constitution; spend a Hit Die when taking the Dodge action.", "Dwarf"),
    GeneralFeatType.ELDRITCH_ADEPT: general_feat(GeneralFeatType.ELDRITCH_ADEPT, "Tasha's Cauldron of Everything", "Learn one Eldritch Invocation.", "Spellcasting or Pact Magic feature"),
    GeneralFeatType.ELEMENTAL_ADEPT: general_feat(GeneralFeatType.ELEMENTAL_ADEPT, "Player's Handbook", "Choose a damage type for spells to ignore resistance and improve low damage dice.", "The ability to cast at least one spell"),
    GeneralFeatType.ELVEN_ACCURACY: general_feat(GeneralFeatType.ELVEN_ACCURACY, "Xanathar's Guide to Everything", "+1 Dexterity, Intelligence, Wisdom, or Charisma; improve advantaged attack rolls.", "Elf or half-elf"),
    GeneralFeatType.EMBER_OF_THE_FIRE_GIANT: general_feat(GeneralFeatType.EMBER_OF_THE_FIRE_GIANT, "Glory of the Giants", "+1 Strength, Constitution, or Wisdom; fire resistance and fire-blind burst.", "4th level, Strike of the Giants (Fire Strike) feat"),
    GeneralFeatType.FADE_AWAY: general_feat(GeneralFeatType.FADE_AWAY, "Xanathar's Guide to Everything", "+1 Dexterity or Intelligence; turn invisible after taking damage.", "Gnome"),
    GeneralFeatType.FEY_TELEPORTATION: general_feat(GeneralFeatType.FEY_TELEPORTATION, "Xanathar's Guide to Everything", "+1 Intelligence or Charisma; gain Sylvan and misty step.", "Elf (high)"),
    GeneralFeatType.FEY_TOUCHED: general_feat(GeneralFeatType.FEY_TOUCHED, "Tasha's Cauldron of Everything", "+1 Intelligence, Wisdom, or Charisma; learn misty step and another spell."),
    GeneralFeatType.FIGHTING_INITIATE: general_feat(GeneralFeatType.FIGHTING_INITIATE, "Tasha's Cauldron of Everything", "Learn one Fighting Style option from the fighter class.", "Proficiency with a martial weapon"),
    GeneralFeatType.FLAMES_OF_PHLEGETHOS: general_feat(GeneralFeatType.FLAMES_OF_PHLEGETHOS, "Xanathar's Guide to Everything", "+1 Intelligence or Charisma; improve fire spells and fiery retaliation.", "Tiefling"),
    GeneralFeatType.FURY_OF_THE_FROST_GIANT: general_feat(GeneralFeatType.FURY_OF_THE_FROST_GIANT, "Glory of the Giants", "+1 Strength, Constitution, or Wisdom; cold resistance and frost retaliation.", "4th level, Strike of the Giants (Frost Strike) feat"),
    GeneralFeatType.GIFT_OF_THE_CHROMATIC_DRAGON: general_feat(GeneralFeatType.GIFT_OF_THE_CHROMATIC_DRAGON, "Fizban's Treasury of Dragons", "Add elemental weapon damage and gain reactive elemental resistance."),
    GeneralFeatType.GIFT_OF_THE_GEM_DRAGON: general_feat(GeneralFeatType.GIFT_OF_THE_GEM_DRAGON, "Fizban's Treasury of Dragons", "+1 Intelligence, Wisdom, or Charisma; telekinetic retaliation.", "-"),
    GeneralFeatType.GIFT_OF_THE_METALLIC_DRAGON: general_feat(GeneralFeatType.GIFT_OF_THE_METALLIC_DRAGON, "Fizban's Treasury of Dragons", "Learn cure wounds and protect with a reactive AC bonus."),
    GeneralFeatType.GRAPPLER: general_feat(GeneralFeatType.GRAPPLER, "Player's Handbook (SRD)", "Improve attacks and restraint options against grappled creatures.", "Strength 13 or higher"),
    GeneralFeatType.GREAT_WEAPON_MASTER: general_feat(GeneralFeatType.GREAT_WEAPON_MASTER, "Player's Handbook", "Gain heavy-weapon damage tradeoffs and bonus attacks after key hits."),
    GeneralFeatType.GUILE_OF_THE_CLOUD_GIANT: general_feat(GeneralFeatType.GUILE_OF_THE_CLOUD_GIANT, "Glory of the Giants", "+1 Strength, Constitution, or Wisdom; reduce damage and teleport.", "4th level, Strike of the Giants (Cloud Strike) feat"),
    GeneralFeatType.GUNNER: general_feat(GeneralFeatType.GUNNER, "Tasha's Cauldron of Everything", "+1 Dexterity; firearm proficiency and improved firearm attacks."),
    GeneralFeatType.HEALER: general_feat(GeneralFeatType.HEALER, "Player's Handbook", "Use a healer's kit to stabilize or restore hit points."),
    GeneralFeatType.HEAVILY_ARMORED: general_feat(GeneralFeatType.HEAVILY_ARMORED, "Player's Handbook", "+1 Strength; gain heavy armor proficiency.", "Proficiency with medium armor"),
    GeneralFeatType.HEAVY_ARMOR_MASTER: general_feat(GeneralFeatType.HEAVY_ARMOR_MASTER, "Player's Handbook", "+1 Strength; reduce mundane weapon damage while wearing heavy armor.", "Proficiency with heavy armor"),
    GeneralFeatType.INFERNAL_CONSTITUTION: general_feat(GeneralFeatType.INFERNAL_CONSTITUTION, "Xanathar's Guide to Everything", "+1 Constitution; gain cold and poison resilience.", "Tiefling"),
    GeneralFeatType.INSPIRING_LEADER: general_feat(GeneralFeatType.INSPIRING_LEADER, "Player's Handbook", "Give temporary hit points to a small group after a speech.", "Charisma 13 or higher"),
    GeneralFeatType.KEEN_MIND: general_feat(GeneralFeatType.KEEN_MIND, "Player's Handbook", "+1 Intelligence; improve recall and orientation."),
    GeneralFeatType.KEENNESS_OF_THE_STONE_GIANT: general_feat(GeneralFeatType.KEENNESS_OF_THE_STONE_GIANT, "Glory of the Giants", "+1 Strength, Constitution, or Wisdom; darkvision and stone strike.", "4th level, Strike of the Giants (Stone Strike) feat"),
    GeneralFeatType.LIGHTLY_ARMORED: general_feat(GeneralFeatType.LIGHTLY_ARMORED, "Player's Handbook", "+1 Strength or Dexterity; gain light armor proficiency."),
    GeneralFeatType.LINGUIST: general_feat(GeneralFeatType.LINGUIST, "Player's Handbook", "+1 Intelligence; learn languages and make ciphers."),
    GeneralFeatType.LUCKY: general_feat(GeneralFeatType.LUCKY, "Player's Handbook", "Spend luck points to affect d20 rolls.", "-"),
    GeneralFeatType.MAGE_SLAYER: general_feat(GeneralFeatType.MAGE_SLAYER, "Player's Handbook", "Punish nearby spellcasters and resist close-range spells."),
    GeneralFeatType.MAGIC_INITIATE: general_feat(GeneralFeatType.MAGIC_INITIATE, "Player's Handbook", "Learn two cantrips and one 1st-level spell from a class list."),
    GeneralFeatType.MARTIAL_ADEPT: general_feat(GeneralFeatType.MARTIAL_ADEPT, "Player's Handbook", "Learn Battle Master maneuvers and gain a superiority die."),
    GeneralFeatType.MEDIUM_ARMOR_MASTER: general_feat(GeneralFeatType.MEDIUM_ARMOR_MASTER, "Player's Handbook", "Improve medium armor stealth and Dexterity AC cap.", "Proficiency with medium armor"),
    GeneralFeatType.METAMAGIC_ADEPT: general_feat(GeneralFeatType.METAMAGIC_ADEPT, "Tasha's Cauldron of Everything", "Learn metamagic and gain sorcery points.", "Spellcasting or Pact Magic feature"),
    GeneralFeatType.MOBILE: general_feat(GeneralFeatType.MOBILE, "Player's Handbook", "Increase speed and improve difficult-terrain dashes and skirmishing."),
    GeneralFeatType.MODERATELY_ARMORED: general_feat(GeneralFeatType.MODERATELY_ARMORED, "Player's Handbook", "+1 Strength or Dexterity; gain medium armor and shield proficiency.", "Proficiency with light armor"),
    GeneralFeatType.MOUNTED_COMBATANT: general_feat(GeneralFeatType.MOUNTED_COMBATANT, "Player's Handbook", "Improve mounted attacks and protect your mount."),
    GeneralFeatType.OBSERVANT: general_feat(GeneralFeatType.OBSERVANT, "Player's Handbook", "+1 Intelligence or Wisdom; read lips and improve passive Investigation/Perception."),
    GeneralFeatType.ORCISH_FURY: general_feat(GeneralFeatType.ORCISH_FURY, "Xanathar's Guide to Everything", "+1 Strength or Constitution; add weapon damage and retaliate after endurance.", "Half-orc"),
    GeneralFeatType.PIERCER: general_feat(GeneralFeatType.PIERCER, "Tasha's Cauldron of Everything", "+1 Strength or Dexterity; improve piercing damage dice and criticals."),
    GeneralFeatType.POISONER: general_feat(GeneralFeatType.POISONER, "Tasha's Cauldron of Everything", "Gain poisoner tools, faster poison application, and better poison attacks."),
    GeneralFeatType.POLEARM_MASTER: general_feat(GeneralFeatType.POLEARM_MASTER, "Player's Handbook", "Make extra polearm attacks and opportunity attacks when foes enter reach."),
    GeneralFeatType.PRODIGY: general_feat(GeneralFeatType.PRODIGY, "Xanathar's Guide to Everything", "Gain a skill, tool, language, and expertise.", "Half-elf, half-orc, or human"),
    GeneralFeatType.RESILIENT: general_feat(GeneralFeatType.RESILIENT, "Player's Handbook", "+1 in one ability and proficiency in that ability's saving throws."),
    GeneralFeatType.RITUAL_CASTER: general_feat(GeneralFeatType.RITUAL_CASTER, "Player's Handbook", "Gain a ritual book and cast ritual spells.", "Intelligence or Wisdom 13 or higher"),
    GeneralFeatType.RUNE_SHAPER: general_feat(GeneralFeatType.RUNE_SHAPER, "Glory of the Giants", "Learn rune magic spells.", "Spellcasting feature or Rune Carver background"),
    GeneralFeatType.SAVAGE_ATTACKER: general_feat(GeneralFeatType.SAVAGE_ATTACKER, "Player's Handbook", "Reroll melee weapon damage once per turn."),
    GeneralFeatType.SECOND_CHANCE: general_feat(GeneralFeatType.SECOND_CHANCE, "Xanathar's Guide to Everything", "+1 Dexterity, Constitution, or Charisma; force an attacker to reroll.", "Halfling"),
    GeneralFeatType.SENTINEL: general_feat(GeneralFeatType.SENTINEL, "Player's Handbook", "Improve opportunity attacks and lock down nearby enemies."),
    GeneralFeatType.SHADOW_TOUCHED: general_feat(GeneralFeatType.SHADOW_TOUCHED, "Tasha's Cauldron of Everything", "+1 Intelligence, Wisdom, or Charisma; learn invisibility and another spell."),
    GeneralFeatType.SHARPSHOOTER: general_feat(GeneralFeatType.SHARPSHOOTER, "Player's Handbook", "Ignore common ranged penalties and trade accuracy for damage."),
    GeneralFeatType.SHIELD_MASTER: general_feat(GeneralFeatType.SHIELD_MASTER, "Player's Handbook", "Add shield tactics to attacks and Dexterity saves."),
    GeneralFeatType.SKILL_EXPERT: general_feat(GeneralFeatType.SKILL_EXPERT, "Tasha's Cauldron of Everything", "+1 in one ability; gain one skill proficiency and one expertise."),
    GeneralFeatType.SKILLED: general_feat(GeneralFeatType.SKILLED, "Player's Handbook", "Gain proficiency with three skills or tools."),
    GeneralFeatType.SKULKER: general_feat(GeneralFeatType.SKULKER, "Player's Handbook", "Improve hiding and ranged stealth.", "Dexterity 13 or higher"),
    GeneralFeatType.SLASHER: general_feat(GeneralFeatType.SLASHER, "Tasha's Cauldron of Everything", "+1 Strength or Dexterity; add control and critical riders to slashing hits."),
    GeneralFeatType.SOUL_OF_THE_STORM_GIANT: general_feat(GeneralFeatType.SOUL_OF_THE_STORM_GIANT, "Glory of the Giants", "+1 Strength, Constitution, or Wisdom; lightning/thunder resilience and storm aura.", "4th level, Strike of the Giants (Storm Strike) feat"),
    GeneralFeatType.SPELL_SNIPER: general_feat(GeneralFeatType.SPELL_SNIPER, "Player's Handbook", "Improve ranged spell attacks and learn an attack cantrip.", "The ability to cast at least one spell"),
    GeneralFeatType.SQUAT_NIMBLENESS: general_feat(GeneralFeatType.SQUAT_NIMBLENESS, "Xanathar's Guide to Everything", "+1 Strength or Dexterity; improve speed and escape checks.", "Dwarf or a Small race"),
    GeneralFeatType.STRIKE_OF_THE_GIANTS: general_feat(GeneralFeatType.STRIKE_OF_THE_GIANTS, "Glory of the Giants", "Choose a giant strike option for extra weapon damage and riders.", "Proficiency with a martial weapon or Giant Foundling background"),
    GeneralFeatType.TAVERN_BRAWLER: general_feat(GeneralFeatType.TAVERN_BRAWLER, "Player's Handbook", "+1 Strength or Constitution; improve improvised weapons, unarmed strikes, and grapples."),
    GeneralFeatType.TELEKINETIC: general_feat(GeneralFeatType.TELEKINETIC, "Tasha's Cauldron of Everything", "+1 Intelligence, Wisdom, or Charisma; improve mage hand and shove telekinetically."),
    GeneralFeatType.TELEPATHIC: general_feat(GeneralFeatType.TELEPATHIC, "Tasha's Cauldron of Everything", "+1 Intelligence, Wisdom, or Charisma; speak telepathically and cast detect thoughts."),
    GeneralFeatType.TOUGH: general_feat(GeneralFeatType.TOUGH, "Player's Handbook", "Increase hit point maximum by 2 per level."),
    GeneralFeatType.VIGOR_OF_THE_HILL_GIANT: general_feat(GeneralFeatType.VIGOR_OF_THE_HILL_GIANT, "Glory of the Giants", "+1 Strength, Constitution, or Wisdom; improve prone resistance and Hit Dice healing.", "4th level, Strike of the Giants (Hill Strike) feat"),
    GeneralFeatType.WAR_CASTER: general_feat(GeneralFeatType.WAR_CASTER, "Player's Handbook", "Improve concentration saves, somatic casting, and reaction spellcasting.", "The ability to cast at least one spell"),
    GeneralFeatType.WEAPON_MASTER: general_feat(GeneralFeatType.WEAPON_MASTER, "Player's Handbook", "+1 Strength or Dexterity; gain weapon proficiencies."),
    GeneralFeatType.WOOD_ELF_MAGIC: general_feat(GeneralFeatType.WOOD_ELF_MAGIC, "Xanathar's Guide to Everything", "Learn druid magic and wood elf spells.", "Elf (wood)"),
}


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
        source=RuleSource.LEGACY,
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
        description="When rolling damage with an eligible two-handed or versatile melee weapon, treat any 1 or 2 on a damage die as a 3.",
        effects=(
            FeatEffect(
                effectType=FeatEffectType.DAMAGE_DICE_REROLL,
                damageDiceRerollScope=FeatDamageDiceRerollScope.TWO_HANDED_OR_VERSATILE_MELEE_WEAPON_ATTACK,
                description="Treat damage dice of 1 or 2 as 3.",
            ),
        ),
    ),
    FightingStyleType.MARINER: FeatDefinition(
        featType=FightingStyleType.MARINER,
        category=FeatCategory.FIGHTING_STYLE,
        repeatable=False,
        description="While not wearing heavy armor or using a shield, gain a swimming speed and climbing speed equal to your Speed, and gain a +1 bonus to Armor Class.",
        effects=(FeatEffect(effectType=FeatEffectType.ARMOR_CLASS_BONUS, value=1),),
        source=RuleSource.LEGACY,
    ),
    FightingStyleType.PACK_FIGHTING: FeatDefinition(
        featType=FightingStyleType.PACK_FIGHTING,
        category=FeatCategory.FIGHTING_STYLE,
        repeatable=False,
        description="When you make a melee attack with a weapon or Unarmed Strike against a creature, gain +1 damage if at least one non-incapacitated ally is within 5 feet of it; +2 if such an ally also has this feat.",
        effects=(
            FeatEffect(
                effectType=FeatEffectType.DESCRIPTION_ONLY,
                description="Conditional damage bonus; apply manually when an ally is within 5 feet of the target.",
            ),
        ),
        source=RuleSource.DND_BEYOND_DROPS_2026,
    ),
    FightingStyleType.PRONE_FIGHTING: FeatDefinition(
        featType=FightingStyleType.PRONE_FIGHTING,
        category=FeatCategory.FIGHTING_STYLE,
        repeatable=False,
        description="When you have the Prone condition, you do not have Disadvantage on attack rolls from being Prone, and attack rolls against you do not have Advantage from you being Prone.",
        effects=(FeatEffect(effectType=FeatEffectType.DESCRIPTION_ONLY),),
        source=RuleSource.DND_BEYOND_DROPS_2026,
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
        description="Learn one Battle Master maneuver and gain one superiority die, which is a d6 unless added to Battle Master superiority dice from another source. The die fuels your maneuver and returns when you finish a short or long rest. Maneuver save DC is 8 + Proficiency Bonus + Strength or Dexterity modifier.",
        effects=(FeatEffect(effectType=FeatEffectType.RESOURCE),),
        source=RuleSource.LEGACY,
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
        source=RuleSource.LEGACY,
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
                    resolution=RollResolutionMode.APPLY_DAMAGE,
                    damageType=DamageType.BLUDGEONING,
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
                name=fighting_style_label(style),
                source=enum_label(FeatCategory.FIGHTING_STYLE),
                activation=TimeEconomy.PASSIVE,
                description=f"{definition.description} Source: {rule_source_label(definition.source)}.",
            )
        )
    return features


def general_feat_options(selected_feats=None):
    from dnd_board.character_sheet import ProgressionChoiceOption

    selected = set(selected_general_feat_keys(selected_feats))
    return [
        ProgressionChoiceOption(value=enum_key(feat_type), label=enum_label(feat_type))
        for feat_type, definition in GENERAL_FEATS.items()
        if definition.repeatable or enum_key(feat_type) not in selected
    ]


def general_feat_feature(feat_key: str):
    from dnd_board.character_sheet import SheetFeature

    feat_type = parse_general_feat(feat_key)
    if feat_type is None:
        return None
    definition = GENERAL_FEATS[feat_type]
    prerequisite = "" if definition.prerequisite == "-" else f" Prerequisite: {definition.prerequisite}."
    return SheetFeature(
        id=enum_key(feat_type),
        name=enum_label(feat_type),
        source=definition.source,
        activation=TimeEconomy.PASSIVE,
        description=f"{definition.description}{prerequisite}",
    )


def selected_general_feat_keys(feats) -> list[str]:
    keys: list[str] = []
    for feat in feats or []:
        feat_type = parse_general_feat(getattr(feat, "id", ""))
        if feat_type is not None:
            key = enum_key(feat_type)
            if key not in keys:
                keys.append(key)
    return keys


def parse_general_feat(value: str) -> GeneralFeatType | None:
    normalized = normalize_feat_key(value)
    for feat_type in GeneralFeatType:
        if normalized in {normalize_feat_key(feat_type.name), normalize_feat_key(enum_key(feat_type)), normalize_feat_key(enum_label(feat_type))}:
            return feat_type
    return None


def normalize_feat_key(value: str) -> str:
    return value.strip().replace("-", "").replace("_", "").replace(" ", "").lower()


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
