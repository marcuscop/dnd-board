export enum TokenKind {
  CHARACTER = "character",
  ASSET = "asset"
}

export enum RollResolutionMode {
  NONE = "none",
  ATTACK_VS_ARMOR_CLASS = "attackVsArmorClass",
  APPLY_DAMAGE = "applyDamage",
  HEAL_SELF = "healSelf",
  APPLY_TEMPORARY_HIT_POINTS = "applyTemporaryHitPoints"
}

export enum RollLogEntryType {
  ROLL_CREATED = "rollCreated",
  ROLL_RESOLVED = "rollResolved",
  ROLL_BLOCKED = "rollBlocked"
}

export enum RollModifierType {
  NONE = "none",
  CLASS_LEVEL = "classLevel",
  PROFICIENCY_BONUS = "proficiencyBonus",
  ABILITY_MODIFIER = "abilityModifier"
}

export enum SheetSectionType {
  ATTACKS = "attacks",
  RESOURCES = "resources",
  FEATURES = "features",
  ABILITIES = "abilities",
  ABILITY_SCORES = "abilityScores",
  SPELLS = "spells",
  DICE_ROLLER = "diceRoller"
}

export type Token = {
  id: string;
  kind: TokenKind;
  name: string;
  owner: string;
  color: string;
  x: number;
  y: number;
  radius: number;
  inScene: boolean;
  avatarUrl?: string;
  lockedBy?: string;
};

export type PlayerSummary = {
  id: string;
  name: string;
};

export type RevealedArea = {
  x: number;
  y: number;
  radius: number;
};

export type FogState = {
  hideMode: boolean;
  brushSize: number;
  revealedAreas: RevealedArea[];
};

export type Board = {
  id: string;
  name: string;
  width: number;
  height: number;
  url?: string;
};

export type Asset = {
  id: string;
  kind: TokenKind.ASSET;
  name: string;
  avatarUrl: string;
};

export type AbilityType = "strength" | "dexterity" | "constitution" | "intelligence" | "wisdom" | "charisma";
export type ConditionType =
  | "bane"
  | "banished"
  | "barkskin"
  | "blinded"
  | "bladeWard"
  | "blessed"
  | "blurred"
  | "calmEmotionsImmunity"
  | "calmEmotionsIndifferent"
  | "charmed"
  | "commandApproach"
  | "commandDrop"
  | "commandFlee"
  | "commandGrovel"
  | "commandHalt"
  | "darkvision"
  | "dead"
  | "deafened"
  | "enhanceAbilityCharisma"
  | "enhanceAbilityDexterity"
  | "enhanceAbilityIntelligence"
  | "enhanceAbilityStrength"
  | "enhanceAbilityWisdom"
  | "enlarged"
  | "exhaustion"
  | "expeditiousRetreat"
  | "faerieFire"
  | "featherFall"
  | "fullCover"
  | "flying"
  | "frightened"
  | "grappled"
  | "guidance"
  | "halfCover"
  | "hasted"
  | "heavilyObscured"
  | "heroism"
  | "incapacitated"
  | "invisible"
  | "jump"
  | "levitating"
  | "longstrider"
  | "mageArmor"
  | "paralyzed"
  | "petrified"
  | "phantasmalKiller"
  | "passWithoutTrace"
  | "poisoned"
  | "prone"
  | "protectionFromPoison"
  | "rayOfEnfeeblement"
  | "reduced"
  | "resistantAcid"
  | "resistantBludgeoning"
  | "resistantCold"
  | "resistantFire"
  | "resistantForce"
  | "resistantLightning"
  | "resistantNecrotic"
  | "resistantPiercing"
  | "resistantPoison"
  | "resistantPsychic"
  | "resistantRadiant"
  | "resistantSlashing"
  | "resistantThunder"
  | "resistanceAcid"
  | "resistanceBludgeoning"
  | "resistanceCold"
  | "resistanceFire"
  | "resistanceForce"
  | "resistanceLightning"
  | "resistanceNecrotic"
  | "resistancePiercing"
  | "resistancePoison"
  | "resistancePsychic"
  | "resistanceRadiant"
  | "resistanceSlashing"
  | "resistanceThunder"
  | "restrained"
  | "shielded"
  | "shieldOfFaith"
  | "shillelagh"
  | "slowed"
  | "stable"
  | "stunned"
  | "synapticStatic"
  | "threeQuartersCover"
  | "unconscious"
  | "seeInvisibility"
  | "wardingBond"
  | "zoneOfTruth";
export type ConditionDuration = "manual" | "untilShortRest" | "untilLongRest";
export type ProgressionChoiceType = "hitPoints" | "abilityScoreImprovement" | "skillProficiencies" | "expertise" | "subclass" | "fightingStyle" | "battleMasterManeuvers" | "arcaneShots" | "runes" | "spells";
export type DamageType =
  | "acid"
  | "bludgeoning"
  | "cold"
  | "fire"
  | "force"
  | "lightning"
  | "necrotic"
  | "piercing"
  | "poison"
  | "psychic"
  | "radiant"
  | "slashing"
  | "thunder";
export type CreatureType =
  | "aberration"
  | "beast"
  | "celestial"
  | "construct"
  | "dragon"
  | "elemental"
  | "fey"
  | "fiend"
  | "giant"
  | "humanoid"
  | "monstrosity"
  | "ooze"
  | "plant"
  | "undead";
export type DiceType = "d4" | "d6" | "d8" | "d10" | "d12" | "d20";
export type TimeEconomy = "action" | "bonusAction" | "reaction" | "movement" | "passive" | "special";
export type RestType = "none" | "shortRest" | "longRest";
export type ProficiencyLevel = "none" | "proficient" | "expertise";
export type WeaponProperty = "ammunition" | "finesse" | "heavy" | "light" | "thrown" | "twoHanded" | "versatile";
export type AttackRangeType = "melee" | "ranged";
export type WeaponCategory = "melee" | "ranged";
export type AttackDamageAbilityModifierMode = "included" | "excluded";
export type AttackKind = "standard" | "twoWeaponFighting";
export type AttackActionType = "standard" | "unarmedStrike" | "thrownWeapon";
export type EquipmentSlot = "carried" | "mainHand" | "offHand" | "twoHands" | "armor";
export type EquipmentType = "armor" | "gear" | "shield" | "weapon";
export type ArmorCategory = "light" | "medium" | "heavy";
export type SpellSchool = "abjuration" | "conjuration" | "divination" | "enchantment" | "evocation" | "illusion" | "necromancy" | "transmutation";
export type SpellComponent = "verbal" | "somatic" | "material";
export type SpellRangeType = "self" | "touch" | "distance" | "sight" | "unlimited" | "special";
export type SpellAreaShape = "none" | "radius" | "cone" | "cube" | "line" | "cylinder";
export type SpellDurationUnit = "instantaneous" | "round" | "minute" | "hour" | "day" | "untilDispelled" | "special";
export type SpellNoArea = {
  shape: "none";
  shapeLabel: string;
};
export type SpellRadiusArea = {
  radiusFeet: number;
  shape: "radius";
  shapeLabel: string;
  diameterFeet: number;
};
export type SpellConeArea = {
  lengthFeet: number;
  shape: "cone";
  shapeLabel: string;
};
export type SpellCubeArea = {
  sizeFeet: number;
  shape: "cube";
  shapeLabel: string;
};
export type SpellLineArea = {
  lengthFeet: number;
  widthFeet: number;
  shape: "line";
  shapeLabel: string;
};
export type SpellCylinderArea = {
  radiusFeet: number;
  heightFeet: number;
  shape: "cylinder";
  shapeLabel: string;
  diameterFeet: number;
};
export type SpellArea = SpellNoArea | SpellRadiusArea | SpellConeArea | SpellCubeArea | SpellLineArea | SpellCylinderArea;
export type SpellSaveOutcome = "none" | "negates" | "halfDamage" | "partial" | "special";
export type SpellTargeting = {
  rangeType: SpellRangeType;
  rangeTypeLabel: string;
  distanceFeet: number;
  area: SpellArea;
  summary: string;
};
export type SpellDuration = {
  unit: SpellDurationUnit;
  unitLabel: string;
  amount: number;
  maximum: boolean;
  summary: string;
};

export type EffectAmount = {
  diceCount?: number;
  diceType?: DiceType;
  staticBonus?: number;
  value?: number;
};
export type AmountScaling = {
  basis: "characterLevel" | "casterLevel" | "spellSlotLevel";
  interval: number;
  additionalDice?: EffectAmount;
  additionalFixedAmount: number;
};
export type AppliedEffect = {
  kind: "damage" | "healing" | "temporaryHitPoints" | "conditionChange" | "maximumHitPoints" | "damageDefense" | "rest" | "movement";
  amount?: EffectAmount;
  damageType?: DamageType;
  defense?: "resistance" | "vulnerability" | "immunity";
  condition?: ConditionType;
  operation?: "add" | "remove" | "suppress";
  movementType?: "forced" | "teleport";
  distanceFeet?: number;
  scaling?: AmountScaling[];
  multiplierNumerator?: number;
  multiplierDenominator?: number;
};
export type EffectNode = {
  label?: string;
  description?: string;
  effect?: AppliedEffect | EffectNode;
  effects?: EffectNode[];
  attack?: {
    attackType: "weapon" | "spell";
    ability?: AbilityType;
  };
  contest?: {
    sourceCheck: {
      ability: AbilityType;
      skill?: string;
    };
    targetChecks: {
      ability: AbilityType;
      skill?: string;
    }[];
  };
  onFailure?: EffectNode;
  onSuccess?: EffectNode;
  onHit?: EffectNode;
  onMiss?: EffectNode;
  onSourceWin?: EffectNode;
  onTargetWin?: EffectNode;
  whenTrue?: EffectNode;
  whenFalse?: EffectNode;
  choices?: {
    option: DamageType | ConditionType;
    effect: EffectNode;
  }[];
  instances?: {
    baseInstances: number;
    basis?: "characterLevel" | "casterLevel" | "spellSlotLevel";
    interval: number;
    additionalInstances: number;
    thresholds: number[];
  };
};
export type FeatureMechanics = {
  activatedEffects: EffectNode[];
  passiveModifiers: unknown[];
  interactions: unknown[];
};
export type ResourceKind = "spellSlot" | "featureUse" | "itemCharge" | "ammunition" | "action" | "bonusAction" | "reaction";
export type ResourceId =
  | "spellSlot"
  | "firstLevelSpellSlots"
  | "secondLevelSpellSlots"
  | "thirdLevelSpellSlots"
  | "fourthLevelSpellSlots"
  | "fifthLevelSpellSlots"
  | "sixthLevelSpellSlots"
  | "seventhLevelSpellSlots"
  | "eighthLevelSpellSlots"
  | "ninthLevelSpellSlots"
  | "secondWind"
  | "actionSurge"
  | "indomitable"
  | "arcaneRecovery"
  | "superiorityDice"
  | "psiWarriorPsionicEnergyDice"
  | "soulknifePsionicEnergyDice"
  | "strokeOfLuck"
  | "luckPoints"
  | "mageSlayer"
  | "boonOfCombatProwess"
  | "boonOfDimensionalTravel"
  | "boonOfFate"
  | "boonOfRecovery"
  | "magicInitiateFreeCast"
  | "groupRecovery"
  | "knowYourEnemy"
  | "arcaneShot"
  | "unwaveringMark"
  | "wardingManeuver"
  | "fightingSpirit"
  | "strengthBeforeDeath"
  | "steadyAim"
  | "protectionFromEvilAndGood"
  | "giantsMight"
  | "runicShield"
  | "cloudRune"
  | "fireRune"
  | "frostRune"
  | "stoneRune"
  | "hillRune"
  | "stormRune"
  | "unleashIncarnation"
  | "shadowMartyr"
  | "reclaimPotential"
  | "psionicEnergyRecovery"
  | "telekineticMovement"
  | "psiPoweredLeap"
  | "bulwarkOfForce"
  | "telekineticMaster"
  | "spellThief"
  | "wailsFromTheGrave"
  | "soulTrinkets"
  | "voiceOfDeath"
  | "ghostWalk"
  | "bloodthirst"
  | "psychicVeil"
  | "rendMind"
  | "arcaneWard"
  | "portent"
  | "greaterPortent"
  | "bladesong"
  | "illusorySelf"
  | "arrows"
  | "bolts"
  | "action"
  | "bonusAction"
  | "reaction";
export type ResourceRecoveryTrigger = "shortRest" | "longRest";
export type ResourceCost = {
  resource: ResourceId;
  amount: number;
};

export type AttackAction = {
  id: string;
  name: string;
  ability: AbilityType;
  abilityLabel: string;
  damageDiceCount: number;
  damageDiceType: DiceType;
  damageDie: string;
  damageType: DamageType;
  damageTypeLabel: string;
  proficient: boolean;
  toHitBonus: number;
  damageBonus: number;
  activation: TimeEconomy;
  activationLabel: string;
  attackRange: AttackRangeType;
  attackRangeLabel: string;
  weaponCategory: WeaponCategory;
  weaponCategoryLabel: string;
  damageAbilityModifier: AttackDamageAbilityModifierMode;
  damageAbilityModifierLabel: string;
  attackKind: AttackKind;
  attackKindLabel: string;
  attackType: AttackActionType;
  attackTypeLabel: string;
  properties: WeaponProperty[];
  propertiesLabel?: string[];
  activeSpellConditions?: string[];
  mechanics?: FeatureMechanics;
  resourceCosts: ResourceCost[];
};

export type RollAction = {
  id: string;
  name: string;
  nameLabel: string;
  diceCount: number;
  diceType: DiceType;
  dice: string;
  modifier: RollModifierType;
  modifierAbility?: AbilityType;
  modifierAbilityLabel?: string;
  staticModifier: number;
  resolution: RollResolutionMode;
  description?: string;
  activation?: TimeEconomy;
  damageType?: DamageType;
  damageTypeLabel?: string;
  mechanics?: FeatureMechanics;
  resourceCosts: ResourceCost[];
};

export type AbilityScores = {
  strength: number;
  dexterity: number;
  constitution: number;
  intelligence: number;
  wisdom: number;
  charisma: number;
};

export type ProgressionChoice = {
  id: string;
  choiceType: ProgressionChoiceType;
  choiceTypeLabel: string;
  label: string;
  description: string;
  minimum: number;
  maximum: number;
  selected: string[];
  options: {
    value: string;
    label: string;
  }[];
};

export type CharacterBuilderOption = {
  value: string;
  label: string;
};

export type CharacterBuilderOptions = {
  roomId: string;
  classes: CharacterBuilderOption[];
  races: CharacterBuilderOption[];
  backgrounds: CharacterBuilderOption[];
  abilityScoreMethods: CharacterBuilderOption[];
  standardArray: number[];
  pointBuyCosts: Record<string, number>;
  pointBuyPoints: number;
  backgroundDetails: Record<string, CharacterBuilderBackgroundDetail>;
  classDetails: Record<string, CharacterBuilderClassDetail>;
  toolDetails: Record<string, CharacterBuilderToolDetail>;
};

export type CharacterBuilderChoiceDetail = {
  minimum: number;
  maximum: number;
  options?: CharacterBuilderOption[];
};

export type CharacterBuilderWizardSpellChoices = {
  cantripsKnown: number;
  spellbookSpellsKnown: number;
  preparedSpellsKnown: number;
  cantrips: CharacterBuilderSpellOption[];
  spellbookSpells: CharacterBuilderSpellOption[];
  preparedSpells: CharacterBuilderSpellOption[];
};

export type CharacterBuilderClassDetail = {
  skillProficiencies: CharacterBuilderChoiceDetail;
  expertise: CharacterBuilderChoiceDetail;
  fightingStyles: CharacterBuilderChoiceDetail;
  wizardSpells: CharacterBuilderWizardSpellChoices;
};

export type CharacterBuilderBackgroundDetail = {
  abilityScores: CharacterBuilderOption[];
  skillProficiencies: CharacterBuilderOption[];
  toolOptions: CharacterBuilderOption[];
  equipmentChoices: CharacterBuilderOption[];
  magicInitiateSpellChoices?: CharacterBuilderMagicInitiateSpellChoices | null;
};

export type CharacterBuilderToolDetail = {
  category: string;
  ability: AbilityType;
  weightLb?: number | null;
  cost: string;
  utilizeActions: {
    description: string;
    dc: number;
  }[];
  craftOutputs: string[];
  hasVariants: boolean;
  variantParent?: string | null;
};

export type CharacterBuilderSpellOption = CharacterBuilderOption & {
  school: SpellSchool;
  level: number;
  castingTime: TimeEconomy;
  castingTimeLabel: string;
  range: string;
  duration: string;
  components: string[];
};

export type CharacterBuilderMagicInitiateSpellChoices = {
  spellList: string;
  cantripsKnown: number;
  firstLevelSpellsKnown: number;
  cantrips: CharacterBuilderSpellOption[];
  firstLevelSpells: CharacterBuilderSpellOption[];
};

export type CharacterBuilderDraft = {
  memberId: string;
  name: string;
  className: string;
  race: string;
  background: string;
  abilityScoreMethod: string;
  baseAbilityScores: AbilityScores;
  rolledAbilityScores: number[];
  backgroundAbilityIncreases: AbilityScores;
  toolProficiency?: string;
  equipmentChoice: string;
  magicInitiateSpells: string[];
  classSkillProficiencies: string[];
  classExpertise: string[];
  fightingStyle: string;
  wizardCantrips: string[];
  wizardSpellbookSpells: string[];
  wizardPreparedSpells: string[];
};

export type CharacterSheet = {
  id: string;
  tokenId: string;
  kind: TokenKind;
  name: string;
  owner: string;
  avatarUrl?: string;
  characterClass: {
    name: string;
    nameLabel: string;
    level: number;
  };
  classes: {
    name: string;
    nameLabel: string;
    level: number;
    subclassLabel?: string;
    subclass?: string;
    fightingStyleLabel?: string;
    fightingStyle?: string;
    fightingStyles?: string[];
    fightingStylesLabel?: string[];
  }[];
  race: string;
  background: string;
  alignment: string;
  proficiencyBonus: number;
  hp: {
    current: number;
    max: number;
    temporary: number;
  };
  abilityScores: AbilityScores;
  abilityModifiers: AbilityScores;
  armorClass: number;
  initiativeBonus: number;
  speed: number;
  savingThrows: {
    ability: AbilityType;
    proficient: boolean;
    modifier: number;
  }[];
  skills: {
    name: string;
    ability: AbilityType;
    proficiency: ProficiencyLevel;
    modifier: number;
    passive: number;
  }[];
  passiveChecks: Record<string, number>;
  pendingChoices: ProgressionChoice[];
  abilities: {
    id: string;
    name: string;
    source: string;
    activation: TimeEconomy;
    activationLabel: string;
    description: string;
    resourceId?: ResourceId;
    rollActions?: RollAction[];
    mechanics?: FeatureMechanics;
  }[];
  resources: {
    id: string;
    name: string;
    currentUses: number;
    maxUses: number;
    activation: TimeEconomy;
    activationLabel: string;
    description: string;
    rollActions?: RollAction[];
    source?: string;
    spellSlotLevel?: number;
    mechanics?: FeatureMechanics;
    resource: ResourceId;
    resourceLabel?: string;
    kind: ResourceKind;
    kindLabel: string;
    recoveries: {
      trigger: ResourceRecoveryTrigger;
      triggerLabel: string;
      amount?: number;
    }[];
    key: {
      id: ResourceId;
      idLabel: string;
      kind: ResourceKind;
      kindLabel: string;
    };
    state: {
      resource: ResourceId;
      resourceLabel: string;
      current: number;
      maximum: number;
    };
  }[];
  features: {
    id: string;
    name: string;
    source: string;
    activation: TimeEconomy;
    activationLabel: string;
    description: string;
    rollActions?: RollAction[];
    mechanics?: FeatureMechanics;
  }[];
  spells: {
    id: string;
    name: string;
    nameLabel: string;
    source: string;
    sourceLabel: string;
    level: number;
    school: SpellSchool;
    schoolLabel: string;
    castingAbility: AbilityType;
    castingAbilityLabel: string;
    castingTime: TimeEconomy;
    castingTimeLabel: string;
    castingDuration?: SpellDuration;
    targeting: SpellTargeting;
    duration: SpellDuration;
    components: SpellComponent[];
    componentsLabel: string[];
    description: string;
    concentration: boolean;
    ritual: boolean;
    resourceId?: ResourceId;
    reset: RestType;
    resetLabel: string;
    mechanics?: FeatureMechanics;
    resourceCosts?: ResourceCost[];
  }[];
  spellbook: {
    id: string;
    name: string;
    nameLabel: string;
    source: string;
    sourceLabel: string;
    level: number;
    school: SpellSchool;
    schoolLabel: string;
    castingAbility: AbilityType;
    castingAbilityLabel: string;
    castingTime: TimeEconomy;
    castingTimeLabel: string;
    castingDuration?: SpellDuration;
    targeting: SpellTargeting;
    duration: SpellDuration;
    components: SpellComponent[];
    componentsLabel: string[];
    description: string;
    concentration: boolean;
    ritual: boolean;
    resourceId?: ResourceId;
    reset: RestType;
    resetLabel: string;
    mechanics?: FeatureMechanics;
    resourceCosts?: ResourceCost[];
  }[];
  proficiencies: string[];
  conditions: ConditionType[];
  exhaustionLevel: number;
  activeConcentration?: {
    spellId: string;
    spellIdLabel: string;
    spellName: string;
  };
  ongoingEffects: unknown[];
  suppressedConditions: ConditionType[];
  creatureTypes: CreatureType[];
  creatureTypesLabel: string[];
  damageResistances: DamageType[];
  damageResistancesLabel: string[];
  damageVulnerabilities: DamageType[];
  damageVulnerabilitiesLabel: string[];
  damageImmunities: DamageType[];
  damageImmunitiesLabel: string[];
  attacks: AttackAction[];
  equipment: {
    id: string;
    name: string;
    equipped: boolean;
    quantity: number;
    weight: number;
    notes: string;
    itemType: EquipmentType;
    itemTypeLabel: string;
    slot: EquipmentSlot;
    slotLabel: string;
    armorCategory?: ArmorCategory;
    armorCategoryLabel?: string;
    armorClass: number;
    armorClassBonus: number;
  }[];
  purse: {
    copper: number;
    silver: number;
    gold: number;
  };
};

export type ActiveConcentrationStatus = {
  spellId: string;
  spellIdLabel: string;
  spellName: string;
};

export type RollPayload = {
  id: string;
  sheetId: string;
  tokenId: string;
  roller: string;
  source: {
    section: SheetSectionType;
    sectionLabel: string;
    sourceId: string;
    actionId: string;
  };
  sourceLabel: string;
  resolution: RollResolutionMode;
  label: string;
  iconUrl?: string;
  dice: number[];
  diceType: DiceType;
  die: string;
  modifier: number;
  modifierBreakdown: {
    source: string;
    value: number;
    description: string;
  }[];
  total: number;
  createdAt: number;
  advantageConditions?: ConditionType[];
  advantageConditionsLabel?: string[];
  disadvantageConditions?: ConditionType[];
  disadvantageConditionsLabel?: string[];
  sourceConditions?: ConditionType[];
  sourceConditionsLabel?: string[];
  damageType?: DamageType;
  damageTypeLabel?: string;
  damageComponents?: RollDamageComponent[];
  damageSavingThrow?: AbilityType;
  damageSavingThrowLabel?: string;
  damageSaveDc?: number;
  damageSaveOutcome?: SpellSaveOutcome;
  damageSaveOutcomeLabel?: string;
  damageSaveDisadvantageCreatureTypes?: CreatureType[];
  damageSaveDisadvantageCreatureTypesLabel?: string[];
  damageSaveForcedFailureCreatureTypes?: CreatureType[];
  damageSaveForcedFailureCreatureTypesLabel?: string[];
  targetCreatureTypes?: CreatureType[];
  targetCreatureTypesLabel?: string[];
  resourcesSpent?: {
    resource: ResourceId;
    resourceLabel: string;
    label: string;
    current: number;
    maximum: number;
  }[];
  pendingEffect?: EffectNode;
  effectInputs?: {
    rolls: { effectNodeId: { path: number[] }; outcome: "success" | "failure" | "hit" | "miss" }[];
    amounts: { effectNodeId: { path: number[] }; amount: number }[];
  };
  criticalHit?: boolean;
};

export type RollDamageComponent = {
  damageType: DamageType;
  damageTypeLabel: string;
  dice: number[];
  diceType: DiceType;
  diceTypeLabel: string;
  die: string;
  modifier: number;
  modifierBreakdown: {
    source: string;
    value: number;
    description: string;
  }[];
  total: number;
  effectNodeIds: { path: number[] }[];
};

export type RollResolution = {
  id: string;
  roll: RollPayload;
  targetSheetId: string;
  targetTokenId: string;
  targetName: string;
  targetArmorClass: number;
  targetHp: {
    current: number;
    max: number;
    temporary: number;
  };
  targetConditions: ConditionType[];
  outcome: string;
  createdAt: number;
  responseRolls?: RollPayload[];
  concentrationUpdates?: {
    sheetId: string;
    activeConcentration?: ActiveConcentrationStatus;
  }[];
  sheetUpdates?: {
    sheetId: string;
    tokenId: string;
    hp?: CharacterSheet["hp"];
    conditions?: ConditionType[];
    damageResistances?: DamageType[];
    damageVulnerabilities?: DamageType[];
    damageImmunities?: DamageType[];
    appliedEffects?: {
      effect: AppliedEffect;
      amount?: number;
    }[];
    scheduledEffects?: unknown[];
    ongoingEffects?: unknown[];
    suppressedConditions?: ConditionType[];
  }[];
};

export type ResolutionInterceptorPrompt = {
  id: string;
  interceptorType: string;
  interceptorTypeLabel: string;
  trigger: string;
  triggerLabel: string;
  sourceRoll: RollPayload;
  pendingRoll: RollPayload;
  targetSheetId: string;
  targetTokenId: string;
  targetName: string;
  ownerSheetId: string;
  ownerTokenId: string;
  ownerName: string;
  ownerPlayerKey: string;
  label: string;
  description: string;
  useLabel: string;
  declineLabel: string;
  createdAt: number;
  interaction: unknown;
  ignoredInterceptors: string[];
  responseRolls?: RollPayload[];
};

export type RollLogEntry = {
  id: string;
  entryType: RollLogEntryType;
  entryTypeLabel: string;
  createdAt: number;
  roll: RollPayload;
  resolution?: RollResolution;
};

export type ServerMessage =
  | { type: "hello"; playerId: string }
  | {
      type: "room_state";
      roomId: string;
      players: PlayerSummary[];
      tokens: Token[];
      fog: FogState;
      board: Board;
      boards: Board[];
      assets: Asset[];
    }
  | { type: "token_updated"; token: Token }
  | { type: "token_deleted"; tokenId: string }
  | { type: "fog_updated"; fog: FogState }
  | { type: "board_updated"; board: Board }
  | { type: "roll_created"; roll: RollPayload; logEntry: RollLogEntry }
  | { type: "roll_resolved"; rollId: string; tokenId: string; preserveRoll?: boolean; resolution: RollResolution; logEntry: RollLogEntry }
  | { type: "resolution_prompt_created"; prompt: ResolutionInterceptorPrompt }
  | { type: "resolution_prompt_resolved"; promptId: string }
  | { type: "roll_blocked"; logEntry: RollLogEntry }
  | { type: "roll_logged"; logEntry: RollLogEntry }
  | { type: "token_lock_denied"; tokenId: string; lockedBy?: string }
  | { type: "player_count"; count: number };
