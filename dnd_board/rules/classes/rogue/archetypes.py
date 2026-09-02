from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from dnd_board.character_sheet import (
    AbilityScores,
    AbilityType,
    AttackAction,
    AttackDamageAbilityModifierMode,
    AttackKind,
    AttackRangeType,
    CharacterClassLevel,
    ConditionApplicationMode,
    ConditionEffect,
    ConditionType,
    DamageType,
    DiceType,
    ResourceTracker,
    RestType,
    RollAction,
    RollResolutionMode,
    SheetAbility,
    SheetFeature,
    SpellComponent,
    SpellDuration,
    SpellDurationUnit,
    SpellEntry,
    SpellId,
    SpellRadiusArea,
    SpellRangeType,
    SpellSchool,
    SpellSource,
    SpellTargeting,
    TimeEconomy,
    WeaponCategory,
    WeaponProperty,
    ability_modifier,
    enum_key,
    enum_label,
    proficiency_bonus_for_level,
)
from dnd_board.rules.classes.rogue.base import RogueSubclassType, rogue_subclass_label


class ArcaneTricksterFeatureType(Enum):
    SPELLCASTING = auto()
    MAGE_HAND_LEGERDEMAIN = auto()
    MAGICAL_AMBUSH = auto()
    VERSATILE_TRICKSTER = auto()
    SPELL_THIEF = auto()


class AssassinFeatureType(Enum):
    ASSASSINATE = auto()
    ASSASSINS_TOOLS = auto()
    INFILTRATION_EXPERTISE = auto()
    ENVENOM_WEAPONS = auto()
    DEATH_STRIKE = auto()


class PhantomFeatureType(Enum):
    WAILS_FROM_THE_GRAVE = auto()
    WHISPERS_OF_THE_DEAD = auto()
    TOKENS_OF_THE_DEPARTED = auto()
    VOICE_OF_DEATH = auto()
    GHOST_WALK = auto()
    DEATHS_FRIEND = auto()


class ScionOfTheThreeFeatureType(Enum):
    BLOODTHIRST = auto()
    DREAD_ALLEGIANCE = auto()
    STRIKE_FEAR = auto()
    AURA_OF_MALEVOLENCE = auto()
    DREAD_INCARNATE = auto()


class SoulknifeFeatureType(Enum):
    PSIONIC_POWER = auto()
    PSYCHIC_BLADES = auto()
    SOUL_BLADES = auto()
    PSYCHIC_VEIL = auto()
    REND_MIND = auto()


class ThiefFeatureType(Enum):
    FAST_HANDS = auto()
    SECOND_STORY_WORK = auto()
    SUPREME_SNEAK = auto()
    USE_MAGIC_DEVICE = auto()
    THIEFS_REFLEXES = auto()


class LegacyRogueFeatureType(Enum):
    EAR_FOR_DECEIT = auto()
    EYE_FOR_DETAIL = auto()
    INSIGHTFUL_FIGHTING = auto()
    STEADY_EYE = auto()
    UNERRING_EYE = auto()
    EYE_FOR_WEAKNESS = auto()
    MASTER_OF_INTRIGUE = auto()
    MASTER_OF_TACTICS = auto()
    INSIGHTFUL_MANIPULATOR = auto()
    MISDIRECTION = auto()
    SOUL_OF_DECEIT = auto()
    SKIRMISHER = auto()
    SURVIVALIST = auto()
    SUPERIOR_MOBILITY = auto()
    AMBUSH_MASTER = auto()
    SUDDEN_STRIKE = auto()
    FANCY_FOOTWORK = auto()
    RAKISH_AUDACITY = auto()
    PANACHE = auto()
    ELEGANT_MANEUVER = auto()
    MASTER_DUELIST = auto()
    TOKENS_OF_PAST_LIVES = auto()
    REVIVED_NATURE = auto()
    BOLTS_FROM_THE_GRAVE = auto()
    CONNECT_WITH_THE_DEAD = auto()
    AUDIENCE_WITH_DEATH = auto()
    ETHEREAL_JAUNT = auto()


class RogueSubclassResourceType(Enum):
    ARCANE_TRICKSTER_FIRST_LEVEL_SPELL_SLOTS = auto()
    ARCANE_TRICKSTER_SECOND_LEVEL_SPELL_SLOTS = auto()
    ARCANE_TRICKSTER_THIRD_LEVEL_SPELL_SLOTS = auto()
    ARCANE_TRICKSTER_FOURTH_LEVEL_SPELL_SLOTS = auto()
    SPELL_THIEF = auto()
    WAILS_FROM_THE_GRAVE = auto()
    SOUL_TRINKETS = auto()
    VOICE_OF_DEATH = auto()
    GHOST_WALK = auto()
    BLOODTHIRST = auto()
    PSIONIC_ENERGY_DICE = auto()
    PSYCHIC_VEIL = auto()
    REND_MIND = auto()


class RogueSubclassRollActionType(Enum):
    WAILS_FROM_THE_GRAVE_DAMAGE = auto()
    PSIONIC_KNACK = auto()
    PSYCHIC_WHISPERS = auto()
    HOMING_STRIKES = auto()
    PSYCHIC_TELEPORTATION = auto()


class RogueSubclassAbilityType(Enum):
    HOMING_STRIKES = auto()
    PSYCHIC_TELEPORTATION = auto()


class RogueSubclassAttackType(Enum):
    PSYCHIC_BLADE = auto()
    PSYCHIC_BLADE_BONUS = auto()


@dataclass(frozen=True)
class SubclassFeatureProgression:
    subclass: RogueSubclassType
    featureType: Enum
    minimum_level: int
    activation: TimeEconomy
    description: str
    conditionEffects: tuple[ConditionEffect, ...] = ()


@dataclass(frozen=True)
class ArcaneTricksterSpellcastingProgression:
    rogue_level: int
    cantrips_known: int
    spells_known: int
    first_level_slots: int = 0
    second_level_slots: int = 0
    third_level_slots: int = 0
    fourth_level_slots: int = 0


ARCANE_TRICKSTER_SPELLCASTING: dict[int, ArcaneTricksterSpellcastingProgression] = {
    3: ArcaneTricksterSpellcastingProgression(3, 3, 3, first_level_slots=2),
    4: ArcaneTricksterSpellcastingProgression(4, 3, 4, first_level_slots=3),
    5: ArcaneTricksterSpellcastingProgression(5, 3, 4, first_level_slots=3),
    6: ArcaneTricksterSpellcastingProgression(6, 3, 4, first_level_slots=3),
    7: ArcaneTricksterSpellcastingProgression(7, 3, 5, first_level_slots=4, second_level_slots=2),
    8: ArcaneTricksterSpellcastingProgression(8, 3, 6, first_level_slots=4, second_level_slots=2),
    9: ArcaneTricksterSpellcastingProgression(9, 3, 6, first_level_slots=4, second_level_slots=2),
    10: ArcaneTricksterSpellcastingProgression(10, 4, 7, first_level_slots=4, second_level_slots=3),
    11: ArcaneTricksterSpellcastingProgression(11, 4, 8, first_level_slots=4, second_level_slots=3),
    12: ArcaneTricksterSpellcastingProgression(12, 4, 8, first_level_slots=4, second_level_slots=3),
    13: ArcaneTricksterSpellcastingProgression(13, 4, 9, first_level_slots=4, second_level_slots=3, third_level_slots=2),
    14: ArcaneTricksterSpellcastingProgression(14, 4, 10, first_level_slots=4, second_level_slots=3, third_level_slots=2),
    15: ArcaneTricksterSpellcastingProgression(15, 4, 10, first_level_slots=4, second_level_slots=3, third_level_slots=2),
    16: ArcaneTricksterSpellcastingProgression(16, 4, 11, first_level_slots=4, second_level_slots=3, third_level_slots=3),
    17: ArcaneTricksterSpellcastingProgression(17, 4, 11, first_level_slots=4, second_level_slots=3, third_level_slots=3),
    18: ArcaneTricksterSpellcastingProgression(18, 4, 11, first_level_slots=4, second_level_slots=3, third_level_slots=3),
    19: ArcaneTricksterSpellcastingProgression(19, 4, 12, first_level_slots=4, second_level_slots=3, third_level_slots=3, fourth_level_slots=1),
    20: ArcaneTricksterSpellcastingProgression(20, 4, 13, first_level_slots=4, second_level_slots=3, third_level_slots=3, fourth_level_slots=1),
}


SUBCLASS_FEATURES: tuple[SubclassFeatureProgression, ...] = (
    SubclassFeatureProgression(RogueSubclassType.ARCANE_TRICKSTER, ArcaneTricksterFeatureType.SPELLCASTING, 3, TimeEconomy.SPECIAL, "Prepare and cast Wizard spells using Intelligence. Mage Hand is always one of your cantrips."),
    SubclassFeatureProgression(RogueSubclassType.ARCANE_TRICKSTER, ArcaneTricksterFeatureType.MAGE_HAND_LEGERDEMAIN, 3, TimeEconomy.BONUS_ACTION, "Cast Mage Hand as a Bonus Action, make the hand Invisible, control it as a Bonus Action, and make Dexterity (Sleight of Hand) checks through it."),
    SubclassFeatureProgression(RogueSubclassType.ARCANE_TRICKSTER, ArcaneTricksterFeatureType.MAGICAL_AMBUSH, 9, TimeEconomy.SPECIAL, "If you have the Invisible condition when casting a spell on a creature, it has Disadvantage on saving throws against that spell this turn."),
    SubclassFeatureProgression(RogueSubclassType.ARCANE_TRICKSTER, ArcaneTricksterFeatureType.VERSATILE_TRICKSTER, 13, TimeEconomy.SPECIAL, "When you use the Trip Cunning Strike option, also use it on another creature within 5 feet of your Mage Hand."),
    SubclassFeatureProgression(RogueSubclassType.ARCANE_TRICKSTER, ArcaneTricksterFeatureType.SPELL_THIEF, 17, TimeEconomy.REACTION, "After a creature casts a spell affecting you, force an Intelligence save against your spell save DC. On failure, negate it against you and steal it for 8 hours. Tracked as a resource."),
    SubclassFeatureProgression(RogueSubclassType.ASSASSIN, AssassinFeatureType.ASSASSINATE, 3, TimeEconomy.PASSIVE, "Advantage on Initiative. During the first round, you have Advantage against creatures that have not acted; if Sneak Attack hits then, add Rogue level extra damage."),
    SubclassFeatureProgression(RogueSubclassType.ASSASSIN, AssassinFeatureType.ASSASSINS_TOOLS, 3, TimeEconomy.PASSIVE, "Gain a Disguise Kit and Poisoner's Kit and proficiency with them."),
    SubclassFeatureProgression(RogueSubclassType.ASSASSIN, AssassinFeatureType.INFILTRATION_EXPERTISE, 9, TimeEconomy.PASSIVE, "Mimic another person's speech or handwriting after 1 hour of study, and Steady Aim no longer reduces your Speed to 0."),
    SubclassFeatureProgression(RogueSubclassType.ASSASSIN, AssassinFeatureType.ENVENOM_WEAPONS, 13, TimeEconomy.SPECIAL, "When you use Poison from Cunning Strike, the target also takes 2d6 Poison damage whenever it fails the save, ignoring Poison Resistance."),
    SubclassFeatureProgression(RogueSubclassType.ASSASSIN, AssassinFeatureType.DEATH_STRIKE, 17, TimeEconomy.SPECIAL, "When your Sneak Attack hits in the first combat round, the target makes a Constitution save or the attack's damage is doubled.", (ConditionEffect(None, ConditionApplicationMode.TARGET_SAVE, savingThrow=AbilityType.CONSTITUTION, saveDcAbility=AbilityType.DEXTERITY, description="On a failed Constitution save, double the attack's damage."),)),
    SubclassFeatureProgression(RogueSubclassType.PHANTOM, PhantomFeatureType.WAILS_FROM_THE_GRAVE, 3, TimeEconomy.SPECIAL, "After Sneak Attack damage on your turn, deal Necrotic damage to a second creature within 30 feet of the first. Tracked as a resource."),
    SubclassFeatureProgression(RogueSubclassType.PHANTOM, PhantomFeatureType.WHISPERS_OF_THE_DEAD, 3, TimeEconomy.PASSIVE, "After each Short or Long Rest, gain one skill or tool proficiency you lack until you choose another with this feature."),
    SubclassFeatureProgression(RogueSubclassType.PHANTOM, PhantomFeatureType.TOKENS_OF_THE_DEPARTED, 9, TimeEconomy.SPECIAL, "Carry soul trinkets that can fuel Wails from the Grave, improve death and Constitution saves, or cast Augury/ask a spirit question."),
    SubclassFeatureProgression(RogueSubclassType.PHANTOM, PhantomFeatureType.VOICE_OF_DEATH, 9, TimeEconomy.ACTION, "Cast Speak with Dead once per Short or Long Rest without components, using Dexterity. You can target a soul trinket."),
    SubclassFeatureProgression(RogueSubclassType.PHANTOM, PhantomFeatureType.GHOST_WALK, 13, TimeEconomy.BONUS_ACTION, "Gain a 10-minute spectral form with hover flight, attacks against you at Disadvantage, and incorporeal movement. Tracked as a resource."),
    SubclassFeatureProgression(RogueSubclassType.PHANTOM, PhantomFeatureType.DEATHS_FRIEND, 17, TimeEconomy.PASSIVE, "Wails from the Grave can damage the first and second creature, and you gain one soul trinket on Initiative if you have none."),
    SubclassFeatureProgression(RogueSubclassType.SCION_OF_THE_THREE, ScionOfTheThreeFeatureType.BLOODTHIRST, 3, TimeEconomy.REACTION, "When a visible enemy within 30 feet becomes Bloodied by damage and is not killed, teleport within 5 feet and make one melee attack. Tracked as a resource."),
    SubclassFeatureProgression(RogueSubclassType.SCION_OF_THE_THREE, ScionOfTheThreeFeatureType.DREAD_ALLEGIANCE, 3, TimeEconomy.PASSIVE, "Choose Bane, Bhaal, or Myrkul after a Long Rest, gaining a damage Resistance and cantrip using Intelligence."),
    SubclassFeatureProgression(RogueSubclassType.SCION_OF_THE_THREE, ScionOfTheThreeFeatureType.STRIKE_FEAR, 9, TimeEconomy.SPECIAL, "Gain Terrify Cunning Strike: cost 1d6, Wisdom save or Frightened for 1 minute; you have Advantage against the target while it is Frightened.", (ConditionEffect(ConditionType.FRIGHTENED, ConditionApplicationMode.TARGET_SAVE, savingThrow=AbilityType.WISDOM, saveDcAbility=AbilityType.DEXTERITY),)),
    SubclassFeatureProgression(RogueSubclassType.SCION_OF_THE_THREE, ScionOfTheThreeFeatureType.AURA_OF_MALEVOLENCE, 13, TimeEconomy.SPECIAL, "When you use Bloodthirst and teleport, chosen creatures within 10 feet of either endpoint take Intelligence modifier damage matching Dread Allegiance, ignoring Resistance."),
    SubclassFeatureProgression(RogueSubclassType.SCION_OF_THE_THREE, ScionOfTheThreeFeatureType.DREAD_INCARNATE, 17, TimeEconomy.PASSIVE, "Regain one Bloodthirst use on Short Rest, and treat Sneak Attack dice rolls of 1 or 2 as 3."),
    SubclassFeatureProgression(RogueSubclassType.SOULKNIFE, SoulknifeFeatureType.PSIONIC_POWER, 3, TimeEconomy.SPECIAL, "Use Psionic Energy dice for Psi-Bolstered Knack and Psychic Whispers. Tracked as a resource."),
    SubclassFeatureProgression(RogueSubclassType.SOULKNIFE, SoulknifeFeatureType.PSYCHIC_BLADES, 3, TimeEconomy.SPECIAL, "Manifest a Finesse, Thrown Psychic Blade for Attack actions or Opportunity Attacks; after attacking on your turn, make a second 1d4 Psychic Blade attack as a Bonus Action if your other hand is free."),
    SubclassFeatureProgression(RogueSubclassType.SOULKNIFE, SoulknifeFeatureType.SOUL_BLADES, 9, TimeEconomy.SPECIAL, "Use Homing Strikes to add a Psionic Energy Die to missed Psychic Blade attacks, and Psychic Teleportation to teleport 10 times the die roll feet."),
    SubclassFeatureProgression(RogueSubclassType.SOULKNIFE, SoulknifeFeatureType.PSYCHIC_VEIL, 13, TimeEconomy.ACTION, "As a Magic action, become Invisible for 1 hour or until dismissed, dealing damage, or forcing a save. Tracked as a resource."),
    SubclassFeatureProgression(RogueSubclassType.SOULKNIFE, SoulknifeFeatureType.REND_MIND, 17, TimeEconomy.SPECIAL, "When Psychic Blades deal Sneak Attack damage, force a Wisdom save or Stun for 1 minute. Tracked as a resource.", (ConditionEffect(ConditionType.STUNNED, ConditionApplicationMode.TARGET_SAVE, savingThrow=AbilityType.WISDOM, saveDcAbility=AbilityType.DEXTERITY),)),
    SubclassFeatureProgression(RogueSubclassType.THIEF, ThiefFeatureType.FAST_HANDS, 3, TimeEconomy.BONUS_ACTION, "As a Bonus Action, make a Sleight of Hand check to pick locks, disarm traps, or pick pockets; take the Utilize action; or take the Magic action to use a magic item requiring that action."),
    SubclassFeatureProgression(RogueSubclassType.THIEF, ThiefFeatureType.SECOND_STORY_WORK, 3, TimeEconomy.PASSIVE, "Gain Climb Speed equal to Speed and use Dexterity instead of Strength to determine jump distance."),
    SubclassFeatureProgression(RogueSubclassType.THIEF, ThiefFeatureType.SUPREME_SNEAK, 9, TimeEconomy.SPECIAL, "Gain Stealth Attack Cunning Strike: cost 1d6, your Hide action's Invisible condition does not end if you finish behind three-quarters or total cover."),
    SubclassFeatureProgression(RogueSubclassType.THIEF, ThiefFeatureType.USE_MAGIC_DEVICE, 13, TimeEconomy.PASSIVE, "Attune to four magic items, sometimes use magic item charges for free, and use any Spell Scroll with Intelligence."),
    SubclassFeatureProgression(RogueSubclassType.THIEF, ThiefFeatureType.THIEFS_REFLEXES, 17, TimeEconomy.PASSIVE, "Take two turns during the first round of combat: one at normal Initiative and one at Initiative minus 10."),
    SubclassFeatureProgression(RogueSubclassType.INQUISITIVE, LegacyRogueFeatureType.EAR_FOR_DECEIT, 3, TimeEconomy.PASSIVE, "Legacy. Treat low Insight rolls to determine lies as an 8."),
    SubclassFeatureProgression(RogueSubclassType.INQUISITIVE, LegacyRogueFeatureType.EYE_FOR_DETAIL, 3, TimeEconomy.BONUS_ACTION, "Legacy. Use a Bonus Action for Perception checks to spot hidden creatures or objects, or Investigation checks to uncover or decipher clues."),
    SubclassFeatureProgression(RogueSubclassType.INQUISITIVE, LegacyRogueFeatureType.INSIGHTFUL_FIGHTING, 3, TimeEconomy.BONUS_ACTION, "Legacy. Contest Insight against a creature's Deception to enable Sneak Attack without Advantage for 1 minute."),
    SubclassFeatureProgression(RogueSubclassType.INQUISITIVE, LegacyRogueFeatureType.STEADY_EYE, 9, TimeEconomy.PASSIVE, "Legacy. Advantage on Perception or Investigation checks if you move no more than half Speed."),
    SubclassFeatureProgression(RogueSubclassType.INQUISITIVE, LegacyRogueFeatureType.UNERRING_EYE, 13, TimeEconomy.ACTION, "Legacy. Sense illusions, shapeshifters, or magic designed to deceive you within 30 feet."),
    SubclassFeatureProgression(RogueSubclassType.INQUISITIVE, LegacyRogueFeatureType.EYE_FOR_WEAKNESS, 17, TimeEconomy.PASSIVE, "Legacy. Insightful Fighting Sneak Attack damage increases by 3d6."),
    SubclassFeatureProgression(RogueSubclassType.MASTERMIND, LegacyRogueFeatureType.MASTER_OF_INTRIGUE, 3, TimeEconomy.PASSIVE, "Legacy. Gain disguise kit, forgery kit, gaming set, and two languages; mimic speech after study."),
    SubclassFeatureProgression(RogueSubclassType.MASTERMIND, LegacyRogueFeatureType.MASTER_OF_TACTICS, 3, TimeEconomy.BONUS_ACTION, "Legacy. Use Help as a Bonus Action; when aiding an ally attacking a creature, range is 30 feet."),
    SubclassFeatureProgression(RogueSubclassType.MASTERMIND, LegacyRogueFeatureType.INSIGHTFUL_MANIPULATOR, 9, TimeEconomy.PASSIVE, "Legacy. After observing a creature, learn how some of its mental stats compare to yours."),
    SubclassFeatureProgression(RogueSubclassType.MASTERMIND, LegacyRogueFeatureType.MISDIRECTION, 13, TimeEconomy.REACTION, "Legacy. Redirect an attack targeting you to a creature granting you cover."),
    SubclassFeatureProgression(RogueSubclassType.MASTERMIND, LegacyRogueFeatureType.SOUL_OF_DECEIT, 17, TimeEconomy.PASSIVE, "Legacy. Your thoughts cannot be read, and magic indicates you are truthful unless you allow otherwise."),
    SubclassFeatureProgression(RogueSubclassType.SCOUT, LegacyRogueFeatureType.SKIRMISHER, 3, TimeEconomy.REACTION, "Legacy. When an enemy ends its turn within 5 feet of you, move up to half Speed without provoking Opportunity Attacks."),
    SubclassFeatureProgression(RogueSubclassType.SCOUT, LegacyRogueFeatureType.SURVIVALIST, 3, TimeEconomy.PASSIVE, "Legacy. Gain Nature and Survival proficiency and Expertise in both."),
    SubclassFeatureProgression(RogueSubclassType.SCOUT, LegacyRogueFeatureType.SUPERIOR_MOBILITY, 9, TimeEconomy.PASSIVE, "Legacy. Speed increases by 10 feet, including climb or swim speed if you have them."),
    SubclassFeatureProgression(RogueSubclassType.SCOUT, LegacyRogueFeatureType.AMBUSH_MASTER, 13, TimeEconomy.PASSIVE, "Legacy. Advantage on Initiative; the first creature you hit in the first combat round grants attack Advantage to others until your next turn."),
    SubclassFeatureProgression(RogueSubclassType.SCOUT, LegacyRogueFeatureType.SUDDEN_STRIKE, 17, TimeEconomy.BONUS_ACTION, "Legacy. Make an extra Bonus Action attack and potentially Sneak Attack a second target."),
    SubclassFeatureProgression(RogueSubclassType.SWASHBUCKLER, LegacyRogueFeatureType.FANCY_FOOTWORK, 3, TimeEconomy.PASSIVE, "Legacy. Creatures you make a melee attack against cannot make Opportunity Attacks against you for the rest of the turn."),
    SubclassFeatureProgression(RogueSubclassType.SWASHBUCKLER, LegacyRogueFeatureType.RAKISH_AUDACITY, 3, TimeEconomy.PASSIVE, "Legacy. Add Charisma modifier to Initiative and enable Sneak Attack when dueling a target within 5 feet."),
    SubclassFeatureProgression(RogueSubclassType.SWASHBUCKLER, LegacyRogueFeatureType.PANACHE, 9, TimeEconomy.ACTION, "Legacy. Charm or goad a creature with Persuasion contested by Insight."),
    SubclassFeatureProgression(RogueSubclassType.SWASHBUCKLER, LegacyRogueFeatureType.ELEGANT_MANEUVER, 13, TimeEconomy.BONUS_ACTION, "Legacy. Gain Advantage on your next Acrobatics or Athletics check this turn."),
    SubclassFeatureProgression(RogueSubclassType.SWASHBUCKLER, LegacyRogueFeatureType.MASTER_DUELIST, 17, TimeEconomy.SPECIAL, "Legacy. Reroll a missed attack roll with Advantage once per Short or Long Rest."),
    SubclassFeatureProgression(RogueSubclassType.REVIVED, LegacyRogueFeatureType.TOKENS_OF_PAST_LIVES, 3, TimeEconomy.PASSIVE, "UA legacy. Gain one skill or tool proficiency after a Long Rest."),
    SubclassFeatureProgression(RogueSubclassType.REVIVED, LegacyRogueFeatureType.REVIVED_NATURE, 3, TimeEconomy.PASSIVE, "UA legacy. Need less sleep, gain death save benefits, and can change creature type detection."),
    SubclassFeatureProgression(RogueSubclassType.REVIVED, LegacyRogueFeatureType.BOLTS_FROM_THE_GRAVE, 3, TimeEconomy.BONUS_ACTION, "UA legacy. After using Cunning Action, make a ranged spell attack that deals Necrotic damage equal to Sneak Attack."),
    SubclassFeatureProgression(RogueSubclassType.REVIVED, LegacyRogueFeatureType.CONNECT_WITH_THE_DEAD, 9, TimeEconomy.PASSIVE, "UA legacy. Learn and cast spells such as Speak with Dead or other necromancy/divination options."),
    SubclassFeatureProgression(RogueSubclassType.REVIVED, LegacyRogueFeatureType.AUDIENCE_WITH_DEATH, 13, TimeEconomy.PASSIVE, "UA legacy. When reduced to 0 HP, gain a question for a death-associated entity."),
    SubclassFeatureProgression(RogueSubclassType.REVIVED, LegacyRogueFeatureType.ETHEREAL_JAUNT, 17, TimeEconomy.BONUS_ACTION, "UA legacy. Step into the Ethereal Plane after using Cunning Action."),
)


def rogue_subclass_features(subclass: RogueSubclassType | None, rogue_level_value: int) -> list[SheetFeature]:
    if subclass is None:
        return []
    return [
        subclass_feature(progression, rogue_level_value)
        for progression in SUBCLASS_FEATURES
        if progression.subclass == subclass and rogue_level_value >= progression.minimum_level
    ]


def rogue_subclass_resources(classes: list[CharacterClassLevel], ability_scores: AbilityScores | None) -> list[ResourceTracker]:
    character_class = rogue_subclass_class(classes)
    if character_class is None:
        return []
    subclass = character_class.subclass
    rogue_level_value = character_class.level
    resources: list[ResourceTracker] = []
    if subclass == RogueSubclassType.ARCANE_TRICKSTER and rogue_level_value >= 3:
        progression = arcane_trickster_spellcasting(rogue_level_value)
        for resource_type, slot_level, max_uses in arcane_trickster_spell_slot_resources(progression):
            resources.append(
                ResourceTracker(
                    id=enum_key(resource_type),
                    name=enum_label(resource_type),
                    currentUses=max_uses,
                    maxUses=max_uses,
                    reset=RestType.LONG_REST,
                    activation=TimeEconomy.ACTION,
                    description=f"Spend to cast an Arcane Trickster spell using a level {slot_level} spell slot.",
                    source=enum_label(RogueSubclassType.ARCANE_TRICKSTER),
                    spellSlotLevel=slot_level,
                )
            )
    if subclass == RogueSubclassType.ARCANE_TRICKSTER and rogue_level_value >= 17:
        resources.append(ResourceTracker(enum_key(RogueSubclassResourceType.SPELL_THIEF), enum_label(RogueSubclassResourceType.SPELL_THIEF), 1, 1, RestType.LONG_REST, TimeEconomy.REACTION, "Negate and steal a spell that targets you or includes you in its area after the caster fails an Intelligence save.", source=enum_label(RogueSubclassType.ARCANE_TRICKSTER)))
    if subclass == RogueSubclassType.PHANTOM and rogue_level_value >= 3:
        uses = max(1, ability_modifier(ability_scores.dexterity if ability_scores else 10))
        dice_count = (sneak_attack_dice_count(rogue_level_value) + 1) // 2
        resources.append(ResourceTracker(enum_key(RogueSubclassResourceType.WAILS_FROM_THE_GRAVE), enum_label(RogueSubclassResourceType.WAILS_FROM_THE_GRAVE), uses, uses, RestType.LONG_REST, TimeEconomy.SPECIAL, "Deal Necrotic damage to a second creature after Sneak Attack.", rollActions=[RollAction(RogueSubclassRollActionType.WAILS_FROM_THE_GRAVE_DAMAGE, RogueSubclassResourceType.WAILS_FROM_THE_GRAVE, dice_count, DiceType.D6, resolution=RollResolutionMode.APPLY_DAMAGE, consumesResource=RogueSubclassResourceType.WAILS_FROM_THE_GRAVE, activation=TimeEconomy.SPECIAL, source=enum_label(RogueSubclassType.PHANTOM), damageType=DamageType.NECROTIC)], source=enum_label(RogueSubclassType.PHANTOM)))
    if subclass == RogueSubclassType.PHANTOM and rogue_level_value >= 9:
        max_trinkets = 4 if rogue_level_value >= 17 else 3 if rogue_level_value >= 13 else 2
        resources.append(ResourceTracker(enum_key(RogueSubclassResourceType.SOUL_TRINKETS), enum_label(RogueSubclassResourceType.SOUL_TRINKETS), max_trinkets, max_trinkets, RestType.LONG_REST, TimeEconomy.SPECIAL, "Destroy soul trinkets for Phantom benefits or gain more when nearby creatures die.", source=enum_label(RogueSubclassType.PHANTOM)))
        resources.append(ResourceTracker(enum_key(RogueSubclassResourceType.VOICE_OF_DEATH), enum_label(RogueSubclassResourceType.VOICE_OF_DEATH), 1, 1, RestType.SHORT_REST, TimeEconomy.ACTION, "Cast Speak with Dead without spell components.", source=enum_label(RogueSubclassType.PHANTOM)))
    if subclass == RogueSubclassType.PHANTOM and rogue_level_value >= 13:
        resources.append(ResourceTracker(enum_key(RogueSubclassResourceType.GHOST_WALK), enum_label(RogueSubclassResourceType.GHOST_WALK), 1, 1, RestType.LONG_REST, TimeEconomy.BONUS_ACTION, "Assume spectral form for 10 minutes; destroy a soul trinket to restore this use.", source=enum_label(RogueSubclassType.PHANTOM)))
    if subclass == RogueSubclassType.SCION_OF_THE_THREE and rogue_level_value >= 3:
        uses = max(1, ability_modifier(ability_scores.intelligence if ability_scores else 10))
        resources.append(ResourceTracker(enum_key(RogueSubclassResourceType.BLOODTHIRST), enum_label(RogueSubclassResourceType.BLOODTHIRST), uses, uses, RestType.LONG_REST, TimeEconomy.REACTION, "Teleport to a newly Bloodied enemy and make one melee attack.", source=enum_label(RogueSubclassType.SCION_OF_THE_THREE)))
    if subclass == RogueSubclassType.SOULKNIFE and rogue_level_value >= 3:
        die = psionic_energy_die(rogue_level_value)
        uses = psionic_energy_dice_count(rogue_level_value)
        resources.append(ResourceTracker(enum_key(RogueSubclassResourceType.PSIONIC_ENERGY_DICE), enum_label(RogueSubclassResourceType.PSIONIC_ENERGY_DICE), uses, uses, RestType.LONG_REST, TimeEconomy.SPECIAL, f"Spend Psionic Energy dice ({enum_key(die)}) for Soulknife powers; regain one on Short Rest and all on Long Rest.", rollActions=[
            RollAction(RogueSubclassRollActionType.PSIONIC_KNACK, RogueSubclassRollActionType.PSIONIC_KNACK, 1, die, resolution=RollResolutionMode.NONE, consumesResource=RogueSubclassResourceType.PSIONIC_ENERGY_DICE, activation=TimeEconomy.SPECIAL, source=enum_label(RogueSubclassType.SOULKNIFE)),
            RollAction(RogueSubclassRollActionType.PSYCHIC_WHISPERS, RogueSubclassRollActionType.PSYCHIC_WHISPERS, 1, die, resolution=RollResolutionMode.NONE, consumesResource=RogueSubclassResourceType.PSIONIC_ENERGY_DICE, activation=TimeEconomy.ACTION, source=enum_label(RogueSubclassType.SOULKNIFE)),
        ], source=enum_label(RogueSubclassType.SOULKNIFE)))
    if subclass == RogueSubclassType.SOULKNIFE and rogue_level_value >= 13:
        resources.append(ResourceTracker(enum_key(RogueSubclassResourceType.PSYCHIC_VEIL), enum_label(RogueSubclassResourceType.PSYCHIC_VEIL), 1, 1, RestType.LONG_REST, TimeEconomy.ACTION, "Become Invisible for up to 1 hour; spend a Psionic Energy Die to restore this use.", source=enum_label(RogueSubclassType.SOULKNIFE)))
    if subclass == RogueSubclassType.SOULKNIFE and rogue_level_value >= 17:
        resources.append(ResourceTracker(enum_key(RogueSubclassResourceType.REND_MIND), enum_label(RogueSubclassResourceType.REND_MIND), 1, 1, RestType.LONG_REST, TimeEconomy.SPECIAL, "When Psychic Blades deal Sneak Attack, force a Wisdom save or Stun. Spend three Psionic Energy Dice to restore this use.", source=enum_label(RogueSubclassType.SOULKNIFE)))
    return resources


def rogue_subclass_abilities(classes: list[CharacterClassLevel]) -> list[SheetAbility]:
    character_class = rogue_subclass_class(classes)
    if character_class is None:
        return []
    subclass = character_class.subclass
    rogue_level_value = character_class.level
    abilities: list[SheetAbility] = []
    if subclass == RogueSubclassType.SOULKNIFE and rogue_level_value >= 9:
        die = psionic_energy_die(rogue_level_value)
        abilities.extend([
            SheetAbility(
                enum_key(RogueSubclassAbilityType.HOMING_STRIKES),
                enum_label(RogueSubclassAbilityType.HOMING_STRIKES),
                enum_label(RogueSubclassType.SOULKNIFE),
                TimeEconomy.SPECIAL,
                "If your Psychic Blade misses, roll a Psionic Energy Die and add it to the attack roll; expend it only if this turns the miss into a hit.",
                resourceId=enum_key(RogueSubclassResourceType.PSIONIC_ENERGY_DICE),
                rollActions=[RollAction(RogueSubclassRollActionType.HOMING_STRIKES, RogueSubclassRollActionType.HOMING_STRIKES, 1, die, consumesResource=RogueSubclassResourceType.PSIONIC_ENERGY_DICE)],
            ),
            SheetAbility(
                enum_key(RogueSubclassAbilityType.PSYCHIC_TELEPORTATION),
                enum_label(RogueSubclassAbilityType.PSYCHIC_TELEPORTATION),
                enum_label(RogueSubclassType.SOULKNIFE),
                TimeEconomy.BONUS_ACTION,
                "Teleport to an unoccupied space up to 10 times your Psionic Energy Die roll in feet.",
                resourceId=enum_key(RogueSubclassResourceType.PSIONIC_ENERGY_DICE),
                rollActions=[RollAction(RogueSubclassRollActionType.PSYCHIC_TELEPORTATION, RogueSubclassRollActionType.PSYCHIC_TELEPORTATION, 1, die, consumesResource=RogueSubclassResourceType.PSIONIC_ENERGY_DICE)],
            ),
        ])
    return abilities


def rogue_subclass_attacks(classes: list[CharacterClassLevel], attacks: list[AttackAction]) -> list[AttackAction]:
    character_class = rogue_subclass_class(classes)
    if character_class is None or character_class.subclass != RogueSubclassType.SOULKNIFE or character_class.level < 3:
        return attacks
    attack_types = {attack.id for attack in attacks}
    next_attacks = list(attacks)
    if enum_key(RogueSubclassAttackType.PSYCHIC_BLADE) not in attack_types:
        next_attacks.append(psychic_blade_attack(RogueSubclassAttackType.PSYCHIC_BLADE, DiceType.D6, TimeEconomy.ACTION, AttackKind.STANDARD))
    if enum_key(RogueSubclassAttackType.PSYCHIC_BLADE_BONUS) not in attack_types:
        next_attacks.append(psychic_blade_attack(RogueSubclassAttackType.PSYCHIC_BLADE_BONUS, DiceType.D4, TimeEconomy.BONUS_ACTION, AttackKind.TWO_WEAPON_FIGHTING))
    return next_attacks


def psychic_blade_attack(attack_type: RogueSubclassAttackType, die: DiceType, activation: TimeEconomy, kind: AttackKind) -> AttackAction:
    return AttackAction(
        id=enum_key(attack_type),
        name=enum_label(attack_type),
        ability=AbilityType.DEXTERITY,
        damageDiceCount=1,
        damageDiceType=die,
        damageType=DamageType.PSYCHIC,
        activation=activation,
        attackRange=AttackRangeType.RANGED,
        weaponCategory=WeaponCategory.MELEE,
        damageAbilityModifier=AttackDamageAbilityModifierMode.INCLUDED,
        attackKind=kind,
        properties=[WeaponProperty.FINESSE, WeaponProperty.THROWN],
    )


def rogue_subclass_spells(classes: list[CharacterClassLevel]) -> list[SpellEntry]:
    character_class = rogue_subclass_class(classes)
    if character_class is None:
        return []
    if character_class.subclass == RogueSubclassType.PHANTOM and character_class.level >= 9:
        return [
            SpellEntry(SpellId.AUGURY, SpellId.AUGURY, SpellSource.PHANTOM, 2, SpellSchool.DIVINATION, AbilityType.CONSTITUTION, TimeEconomy.ACTION, SpellTargeting(SpellRangeType.SELF), SpellDuration(SpellDurationUnit.INSTANTANEOUS), [], "Destroy a soul trinket to receive an omen or ask the associated spirit one question.", ritual=True, resourceId=enum_key(RogueSubclassResourceType.SOUL_TRINKETS)),
            SpellEntry(SpellId.SPEAK_WITH_DEAD, SpellId.SPEAK_WITH_DEAD, SpellSource.PHANTOM, 3, SpellSchool.NECROMANCY, AbilityType.DEXTERITY, TimeEconomy.ACTION, SpellTargeting(SpellRangeType.DISTANCE, distanceFeet=10), SpellDuration(SpellDurationUnit.MINUTE, amount=10), [], "Ask questions of a corpse or soul trinket.", resourceId=enum_key(RogueSubclassResourceType.VOICE_OF_DEATH), reset=RestType.SHORT_REST),
        ]
    if character_class.subclass == RogueSubclassType.SCION_OF_THE_THREE and character_class.level >= 3:
        return [
            SpellEntry(SpellId.MINOR_ILLUSION, SpellId.MINOR_ILLUSION, SpellSource.SCION_OF_THE_THREE, 0, SpellSchool.ILLUSION, AbilityType.INTELLIGENCE, TimeEconomy.ACTION, SpellTargeting(SpellRangeType.DISTANCE, distanceFeet=30), SpellDuration(SpellDurationUnit.MINUTE, amount=1), [SpellComponent.SOMATIC, SpellComponent.MATERIAL], "Bane Dread Allegiance cantrip option."),
            SpellEntry(SpellId.BLADE_WARD, SpellId.BLADE_WARD, SpellSource.SCION_OF_THE_THREE, 0, SpellSchool.ABJURATION, AbilityType.INTELLIGENCE, TimeEconomy.ACTION, SpellTargeting(SpellRangeType.SELF), SpellDuration(SpellDurationUnit.ROUND, amount=1), [SpellComponent.VERBAL, SpellComponent.SOMATIC], "Bhaal Dread Allegiance cantrip option."),
            SpellEntry(SpellId.CHILL_TOUCH, SpellId.CHILL_TOUCH, SpellSource.SCION_OF_THE_THREE, 0, SpellSchool.NECROMANCY, AbilityType.INTELLIGENCE, TimeEconomy.ACTION, SpellTargeting(SpellRangeType.DISTANCE, distanceFeet=120), SpellDuration(SpellDurationUnit.ROUND, amount=1), [SpellComponent.VERBAL, SpellComponent.SOMATIC], "Myrkul Dread Allegiance cantrip option."),
        ]
    return []


def normalized_arcane_trickster_spells(classes: list[CharacterClassLevel], spells: list[SpellEntry]) -> list[SpellEntry]:
    character_class = rogue_subclass_class(classes)
    if character_class is None or character_class.subclass != RogueSubclassType.ARCANE_TRICKSTER:
        return spells
    return [normalized_arcane_trickster_spell(spell) for spell in spells]


def arcane_trickster_spellcasting(rogue_level_value: int) -> ArcaneTricksterSpellcastingProgression:
    eligible_level = max(level for level in ARCANE_TRICKSTER_SPELLCASTING if rogue_level_value >= level)
    return ARCANE_TRICKSTER_SPELLCASTING[eligible_level]


def arcane_trickster_spell_slot_resources(progression: ArcaneTricksterSpellcastingProgression) -> list[tuple[RogueSubclassResourceType, int, int]]:
    return [
        item
        for item in [
            (RogueSubclassResourceType.ARCANE_TRICKSTER_FIRST_LEVEL_SPELL_SLOTS, 1, progression.first_level_slots),
            (RogueSubclassResourceType.ARCANE_TRICKSTER_SECOND_LEVEL_SPELL_SLOTS, 2, progression.second_level_slots),
            (RogueSubclassResourceType.ARCANE_TRICKSTER_THIRD_LEVEL_SPELL_SLOTS, 3, progression.third_level_slots),
            (RogueSubclassResourceType.ARCANE_TRICKSTER_FOURTH_LEVEL_SPELL_SLOTS, 4, progression.fourth_level_slots),
        ]
        if item[2] > 0
    ]


def arcane_trickster_spell_options(rogue_level_value: int, selected_spell_keys: list[str] | None = None) -> list[SpellEntry]:
    from dnd_board.rules.classes.fighter.archetypes import ELDRITCH_KNIGHT_SPELL_CATALOG
    from dnd_board.rules.spells import wizard_spell_entries

    selected = set(selected_spell_keys or [])
    progression = arcane_trickster_spellcasting(rogue_level_value)
    max_spell_level = 4 if progression.fourth_level_slots else 3 if progression.third_level_slots else 2 if progression.second_level_slots else 1
    shared_spells = wizard_spell_entries(maximum_level=max_spell_level)
    catalog = {spell.id: spell for spell in shared_spells}
    catalog.update(ELDRITCH_KNIGHT_SPELL_CATALOG)
    catalog.update(ARCANE_TRICKSTER_SPELL_CATALOG)
    return [
        spell
        for spell in catalog.values()
        if enum_key(spell.id) not in selected and (spell.level == 0 or spell.level <= max_spell_level)
    ]


def arcane_trickster_catalog_spell(value: str | SpellId) -> SpellEntry | None:
    from dnd_board.rules.classes.fighter.archetypes import ELDRITCH_KNIGHT_SPELL_CATALOG
    from dnd_board.rules.spells import wizard_spell_entry

    spell_key = value if isinstance(value, SpellId) else next((spell_id for spell_id in SpellId if enum_key(spell_id) == value or spell_id.value == value), None)
    if spell_key is None:
        return None
    return ARCANE_TRICKSTER_SPELL_CATALOG.get(spell_key) or ELDRITCH_KNIGHT_SPELL_CATALOG.get(spell_key) or wizard_spell_entry(spell_key)


def normalized_arcane_trickster_spell(spell: SpellEntry) -> SpellEntry:
    return SpellEntry(
        id=spell.id,
        name=spell.name,
        source=SpellSource.ARCANE_TRICKSTER,
        level=spell.level,
        school=spell.school,
        castingAbility=AbilityType.INTELLIGENCE,
        castingTime=spell.castingTime,
        targeting=spell.targeting,
        duration=spell.duration,
        components=spell.components,
        description=spell.description,
        concentration=spell.concentration,
        ritual=spell.ritual,
        resourceId=spell.resourceId,
        reset=spell.reset,
    )


def is_arcane_trickster_spell_selection_valid(rogue_level_value: int, spells: list[SpellEntry]) -> bool:
    progression = arcane_trickster_spellcasting(rogue_level_value)
    cantrips = [spell for spell in spells if spell.level == 0]
    leveled = [spell for spell in spells if spell.level > 0]
    return len(cantrips) == progression.cantrips_known and len(leveled) == progression.spells_known and any(spell.id == SpellId.MAGE_HAND for spell in cantrips)


def pruned_arcane_trickster_spells(rogue_level_value: int, spells: list[SpellEntry]) -> list[SpellEntry]:
    progression = arcane_trickster_spellcasting(rogue_level_value)
    cantrips = [spell for spell in spells if spell.level == 0][: progression.cantrips_known]
    leveled = [spell for spell in spells if spell.level > 0][: progression.spells_known]
    return [*cantrips, *leveled]


def subclass_feature(progression: SubclassFeatureProgression, rogue_level_value: int) -> SheetFeature:
    description = progression.description
    if progression.subclass == RogueSubclassType.ARCANE_TRICKSTER and progression.featureType == ArcaneTricksterFeatureType.SPELLCASTING:
        spellcasting = arcane_trickster_spellcasting(rogue_level_value)
        description = f"{description} You know {spellcasting.cantrips_known} cantrips and prepare {spellcasting.spells_known} leveled spells."
    return SheetFeature(enum_key(progression.featureType), enum_label(progression.featureType), rogue_subclass_label(progression.subclass), progression.activation, description, conditionEffects=list(progression.conditionEffects) or None)


def rogue_subclass_class(classes: list[CharacterClassLevel]) -> CharacterClassLevel | None:
    return next((character_class for character_class in classes if character_class.subclass in set(RogueSubclassType)), None)


def sneak_attack_dice_count(rogue_level_value: int) -> int:
    return (rogue_level_value + 1) // 2


def psionic_energy_die(rogue_level_value: int) -> DiceType:
    if rogue_level_value >= 17:
        return DiceType.D12
    if rogue_level_value >= 11:
        return DiceType.D10
    if rogue_level_value >= 5:
        return DiceType.D8
    return DiceType.D6


def psionic_energy_dice_count(rogue_level_value: int) -> int:
    return 2 * proficiency_bonus_for_level(rogue_level_value)


ARCANE_TRICKSTER_SPELL_CATALOG: dict[SpellId, SpellEntry] = {
    SpellId.MIND_SLIVER: SpellEntry(SpellId.MIND_SLIVER, SpellId.MIND_SLIVER, SpellSource.WIZARD, 0, SpellSchool.ENCHANTMENT, AbilityType.INTELLIGENCE, TimeEconomy.ACTION, SpellTargeting(SpellRangeType.DISTANCE, distanceFeet=60), SpellDuration(SpellDurationUnit.ROUND, amount=1), [SpellComponent.VERBAL], "Assault a creature's mind with psychic damage and impair its next saving throw."),
    SpellId.CHARM_PERSON: SpellEntry(SpellId.CHARM_PERSON, SpellId.CHARM_PERSON, SpellSource.WIZARD, 1, SpellSchool.ENCHANTMENT, AbilityType.INTELLIGENCE, TimeEconomy.ACTION, SpellTargeting(SpellRangeType.DISTANCE, distanceFeet=30), SpellDuration(SpellDurationUnit.HOUR, amount=1), [SpellComponent.VERBAL, SpellComponent.SOMATIC], "Charm a humanoid that fails a Wisdom save."),
    SpellId.DISGUISE_SELF: SpellEntry(SpellId.DISGUISE_SELF, SpellId.DISGUISE_SELF, SpellSource.WIZARD, 1, SpellSchool.ILLUSION, AbilityType.INTELLIGENCE, TimeEconomy.ACTION, SpellTargeting(SpellRangeType.SELF), SpellDuration(SpellDurationUnit.HOUR, amount=1), [SpellComponent.VERBAL, SpellComponent.SOMATIC], "Make yourself and your equipment look different."),
    SpellId.FOG_CLOUD: SpellEntry(SpellId.FOG_CLOUD, SpellId.FOG_CLOUD, SpellSource.WIZARD, 1, SpellSchool.CONJURATION, AbilityType.INTELLIGENCE, TimeEconomy.ACTION, SpellTargeting(SpellRangeType.DISTANCE, distanceFeet=120, area=SpellRadiusArea(radiusFeet=20)), SpellDuration(SpellDurationUnit.HOUR, amount=1, maximum=True), [SpellComponent.VERBAL, SpellComponent.SOMATIC], "Create a heavily obscured sphere of fog.", concentration=True),
}
