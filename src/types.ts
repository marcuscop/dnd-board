export type TokenKind = "character" | "asset";

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
  kind: "asset";
  name: string;
  avatarUrl: string;
};

export type AttackAction = {
  id: string;
  name: string;
  ability: string;
  damageDie: string;
};

export type AbilityScores = {
  strength: number;
  dexterity: number;
  constitution: number;
  intelligence: number;
  wisdom: number;
  charisma: number;
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
    level: number;
  };
  hp: {
    current: number;
    max: number;
    temporary: number;
  };
  abilityScores: AbilityScores;
  armorClass: number;
  initiativeBonus: number;
  conditions: string[];
  attacks: AttackAction[];
};

export type RollPayload = {
  id: string;
  sheetId: string;
  tokenId: string;
  roller: string;
  kind: "attack" | "damage";
  label: string;
  iconUrl?: string;
  action: AttackAction;
  dice: number[];
  die: string;
  modifier: number;
  total: number;
  createdAt: number;
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
  outcome: string;
  createdAt: number;
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
  | { type: "roll_created"; roll: RollPayload }
  | { type: "roll_resolved"; rollId: string; tokenId: string; resolution: RollResolution }
  | { type: "token_lock_denied"; tokenId: string; lockedBy?: string }
  | { type: "player_count"; count: number };
