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
  ROLL_RESOLVED = "rollResolved"
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
  SPELLS = "spells"
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
  | "blinded"
  | "charmed"
  | "deafened"
  | "exhaustion"
  | "frightened"
  | "grappled"
  | "incapacitated"
  | "invisible"
  | "paralyzed"
  | "petrified"
  | "poisoned"
  | "prone"
  | "restrained"
  | "stunned"
  | "unconscious";
export type ConditionApplicationMode = "targetSave" | "sourceCheck" | "direct" | "manual";
export type ConditionDuration = "manual" | "untilShortRest" | "untilLongRest";
export type ConditionEffect = {
  condition?: ConditionType;
  conditionLabel?: string;
  mode: ConditionApplicationMode;
  modeLabel: string;
  savingThrow?: AbilityType;
  savingThrowLabel?: string;
  saveDcAbility?: AbilityType;
  saveDcAbilityLabel?: string;
  saveDc?: number;
  sourceCheck?: AbilityType;
  sourceCheckLabel?: string;
  contestChecks?: AbilityType[];
  contestChecksLabel?: string[];
  duration: ConditionDuration;
  durationLabel: string;
  description: string;
};
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
  consumesResource?: string;
  description?: string;
  activation?: TimeEconomy;
  damageType?: DamageType;
  damageTypeLabel?: string;
  conditionEffects?: ConditionEffect[];
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
  toolDetails: Record<string, CharacterBuilderToolDetail>;
};

export type CharacterBuilderBackgroundDetail = {
  abilityScores: CharacterBuilderOption[];
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
    resourceId?: string;
    rollActions?: RollAction[];
    conditionEffects?: ConditionEffect[];
  }[];
  resources: {
    id: string;
    name: string;
    currentUses: number;
    maxUses: number;
    reset: RestType;
    resetLabel: string;
    activation: TimeEconomy;
    activationLabel: string;
    description: string;
    rollActions?: RollAction[];
    source?: string;
  }[];
  features: {
    id: string;
    name: string;
    source: string;
    activation: TimeEconomy;
    activationLabel: string;
    description: string;
    rollActions?: RollAction[];
    conditionEffects?: ConditionEffect[];
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
    resourceId?: string;
    reset: RestType;
    resetLabel: string;
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
    resourceId?: string;
    reset: RestType;
    resetLabel: string;
  }[];
  proficiencies: string[];
  conditions: ConditionType[];
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
  damageType?: DamageType;
  damageTypeLabel?: string;
  conditionEffects?: ConditionEffect[];
  resourceSpent?: {
    resourceId: string;
    resourceName: string;
    remainingUses: number;
    maxUses: number;
  };
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
  | { type: "roll_resolved"; rollId: string; tokenId: string; resolution: RollResolution; logEntry: RollLogEntry }
  | { type: "token_lock_denied"; tokenId: string; lockedBy?: string }
  | { type: "player_count"; count: number };
