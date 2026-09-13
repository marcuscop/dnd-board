import { RollResolutionMode, SheetSectionType } from "../types";
import type {
  CharacterSheet,
  EquipmentSlot,
  RollLogEntry,
  RollPayload,
  Token
} from "../types";

export function rollMatchesSource(roll: RollPayload, section: SheetSectionType, sourceId: string) {
  return roll.source.section === section && roll.source.sourceId === sourceId;
}

export function rollMatchesSourceAction(roll: RollPayload, section: SheetSectionType, sourceId: string, actionId: string) {
  return rollMatchesSource(roll, section, sourceId) && roll.source.actionId === actionId;
}

export function cardResolvedRolls(sheet: CharacterSheet, rollHistory: RollLogEntry[], clearedCardRollIds: Set<string>) {
  return rollHistory
    .filter(
      (entry) =>
        entry.resolution &&
        (entry.roll.resolution === RollResolutionMode.HEAL_SELF || entry.roll.resolution === RollResolutionMode.APPLY_TEMPORARY_HIT_POINTS) &&
        entry.roll.tokenId === sheet.tokenId &&
        entry.resolution.targetSheetId === sheet.id &&
        !clearedCardRollIds.has(entry.id)
    )
    .slice(-2)
    .reverse();
}

export function hasDamageDefenses(sheet: CharacterSheet) {
  return sheet.damageResistances.length > 0 || sheet.damageVulnerabilities.length > 0 || sheet.damageImmunities.length > 0;
}

export function formatHp(hp: CharacterSheet["hp"]) {
  return `${hp.current + hp.temporary}/${hp.max}`;
}

export function normalizeIdentity(value: string) {
  return value.trim().toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
}

export function canControlToken(token: Token, playerKey: string, isDm: boolean) {
  return isDm || token.owner === playerKey;
}

export function canRollSheet(sheet: CharacterSheet, playerKey: string, isDm: boolean) {
  return isDm || sheet.owner === playerKey;
}

export function formatSigned(value: number) {
  return value >= 0 ? `+${value}` : String(value);
}

export function equipmentSlotOptions(itemType: CharacterSheet["equipment"][number]["itemType"]): EquipmentSlot[] {
  if (itemType === "armor") return ["carried", "armor"];
  if (itemType === "shield") return ["carried", "mainHand", "offHand"];
  if (itemType === "weapon") return ["carried", "mainHand", "offHand", "twoHands"];
  return ["carried"];
}

export function hasPurseCoins(sheet: CharacterSheet) {
  return sheet.purse.gold > 0 || sheet.purse.silver > 0 || sheet.purse.copper > 0;
}

export function shortAbilityName(ability: string) {
  return ability.slice(0, 3).toUpperCase();
}

export function cleanName(identifier: string) {
  return identifier.replace(/([A-Z])/g, " $1").replace(/[-_]/g, " ").replace(/\b\w/g, (match) => match.toUpperCase()).trim();
}

export function formatPlayerName(playerKey: string, tokens: Token[] = []) {
  if (playerKey === "dm") return "DM";
  return tokens.find((token) => token.kind === "character" && token.owner === playerKey)?.name
    ?? playerKey.replace("-", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}
