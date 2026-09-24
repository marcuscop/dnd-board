import { useCallback } from "react";
import type { Dispatch, SetStateAction } from "react";

import { postJson } from "../api/client";
import type { DamageDefenseType } from "../sheet/SheetView";
import type { RestHitDieSelection } from "../sheet/RestControls";
import type {
  CharacterBuilderDraft,
  CharacterSheet,
  ConditionType,
  DamageType,
  DiceType,
  EquipmentSlot,
  ResolutionInterceptorPrompt,
  RollLogEntry,
  RollPayload
} from "../types";
import {
  appendRollLogEntry,
  applyResolvedRollToSheetState,
  upsertPendingRoll,
  upsertResolutionPrompt
} from "./useRoomConnection";

type SheetStatus = "idle" | "loading" | "error";
type SheetStateResponse = {
  sheets: CharacterSheet[];
  pendingRolls: RollPayload[];
  pendingResolutionPrompts?: ResolutionInterceptorPrompt[];
  rollHistory: RollLogEntry[];
};

type SheetActionOptions = {
  roomId: string;
  playerKey: string;
  turnId?: string;
  loadSheets: (showLoading?: boolean) => Promise<void>;
  setSheets: Dispatch<SetStateAction<CharacterSheet[]>>;
  setRolls: Dispatch<SetStateAction<RollPayload[]>>;
  setResolutionPrompts: Dispatch<SetStateAction<ResolutionInterceptorPrompt[]>>;
  setRollHistory: Dispatch<SetStateAction<RollLogEntry[]>>;
  setSheetStatus: Dispatch<SetStateAction<SheetStatus>>;
};

export function useSheetActions(options: SheetActionOptions) {
  const { roomId, playerKey, turnId, loadSheets, setSheets, setRolls, setResolutionPrompts, setRollHistory, setSheetStatus } = options;
  const sheetPath = useCallback((sheet: CharacterSheet) => `/api/rooms/${encodeURIComponent(roomId)}/sheet/${encodeURIComponent(sheet.id)}`, [roomId]);
  const fail = useCallback((error: unknown) => {
    console.error(error);
    setSheetStatus("error");
  }, [setSheetStatus]);
  const reloadAfter = useCallback(async (request: Promise<unknown>) => {
    try {
      await request;
      await loadSheets();
    } catch (error) {
      fail(error);
    }
  }, [fail, loadSheets]);
  const replaceSheet = useCallback((sheet: CharacterSheet) => {
    setSheets((current) => current.map((candidate) => candidate.id === sheet.id ? sheet : candidate));
  }, [setSheets]);
  const applySheetState = useCallback((body: SheetStateResponse) => {
    setSheets(body.sheets);
    setRolls(body.pendingRolls);
    setResolutionPrompts(body.pendingResolutionPrompts ?? []);
    setRollHistory(body.rollHistory);
  }, [setResolutionPrompts, setRollHistory, setRolls, setSheets]);

  const rollAttack = useCallback((sheet: CharacterSheet, attackId: string, weaponOption?: string) => reloadAfter(
    postJson(`${sheetPath(sheet)}/rolls/attack`, { playerKey, attackId, weaponOption, turnId })
  ), [playerKey, reloadAfter, sheetPath, turnId]);

  const rollDamage = useCallback((sheet: CharacterSheet, attackId: string, weaponOption?: string) => reloadAfter(
    postJson(`${sheetPath(sheet)}/rolls/damage`, { playerKey, attackId, weaponOption, turnId })
  ), [playerKey, reloadAfter, sheetPath, turnId]);

  const rollAbilityCheck = useCallback(async (sheet: CharacterSheet, ability: string) => {
    try { await postJson(`${sheetPath(sheet)}/rolls/ability-check`, { playerKey, ability }); } catch (error) { fail(error); }
  }, [fail, playerKey, sheetPath]);

  const rollSavingThrow = useCallback(async (sheet: CharacterSheet, ability: string) => {
    try { await postJson(`${sheetPath(sheet)}/rolls/saving-throw`, { playerKey, ability }); } catch (error) { fail(error); }
  }, [fail, playerKey, sheetPath]);

  const rollDeathSavingThrow = useCallback(async (sheet: CharacterSheet) => {
    try { await postJson(`${sheetPath(sheet)}/rolls/death-saving-throw`, { playerKey }); } catch (error) { fail(error); }
  }, [fail, playerKey, sheetPath]);

  const rollResourceAction = useCallback(async (sheet: CharacterSheet, abilityId: string, actionId: string) => {
    try {
      const body = await postJson<{ roll: RollPayload; resolution?: RollLogEntry["resolution"]; logEntry?: RollLogEntry }>(
        `${sheetPath(sheet)}/abilities/${encodeURIComponent(abilityId)}/rolls/${encodeURIComponent(actionId)}`,
        { playerKey, turnId }
      );
      if (body.resolution && body.logEntry) {
        setSheets((current) => applyResolvedRollToSheetState(current, body.resolution!));
        setRolls((current) => current.filter((roll) => roll.id !== body.roll.id));
        setRollHistory((current) => appendRollLogEntry(current, body.logEntry!));
      } else {
        await loadSheets();
      }
    } catch (error) { fail(error); }
  }, [fail, loadSheets, playerKey, setRollHistory, setRolls, setSheets, sheetPath, turnId]);

  const rollSpellAttack = useCallback((sheet: CharacterSheet, spellId: string, spellSlotLevel?: number) => reloadAfter(
    postJson(`${sheetPath(sheet)}/spells/${encodeURIComponent(spellId)}/rolls/attack`, { playerKey, spellSlotLevel, turnId })
  ), [playerKey, reloadAfter, sheetPath, turnId]);

  const rollSpellDamage = useCallback((sheet: CharacterSheet, spellId: string, effectIndex: number, spellSlotLevel?: number, instanceIndex?: number, choiceIndex?: number) => reloadAfter(
    postJson(`${sheetPath(sheet)}/spells/${encodeURIComponent(spellId)}/rolls/damage`, { playerKey, effectIndex, spellSlotLevel, instanceIndex, choiceIndex, turnId })
  ), [playerKey, reloadAfter, sheetPath, turnId]);

  const rollBoundWeaponSpell = useCallback((sheet: CharacterSheet, spellId: string, effectIndex: number, equipmentInstanceId: string, choiceIndex?: number) => reloadAfter(
    postJson(`${sheetPath(sheet)}/spells/${encodeURIComponent(spellId)}/rolls/weapon-attack`, { playerKey, effectIndex, equipmentInstanceId, choiceIndex, turnId })
  ), [playerKey, reloadAfter, sheetPath, turnId]);

  const rollSpellHealing = useCallback((sheet: CharacterSheet, spellId: string, effectIndex: number, spellSlotLevel?: number) => reloadAfter(
    postJson(`${sheetPath(sheet)}/spells/${encodeURIComponent(spellId)}/rolls/healing`, { playerKey, effectIndex, spellSlotLevel, turnId })
  ), [playerKey, reloadAfter, sheetPath, turnId]);

  const rollSpellTemporaryHitPoints = useCallback((sheet: CharacterSheet, spellId: string, effectIndex: number, spellSlotLevel?: number) => reloadAfter(
    postJson(`${sheetPath(sheet)}/spells/${encodeURIComponent(spellId)}/rolls/temporary-hit-points`, { playerKey, effectIndex, spellSlotLevel, turnId })
  ), [playerKey, reloadAfter, sheetPath, turnId]);

  const rollSpellEffect = useCallback((sheet: CharacterSheet, spellId: string, effectIndex: number, spellSlotLevel?: number, choiceIndex?: number, equipmentInstanceId?: string) => reloadAfter(
    postJson(`${sheetPath(sheet)}/spells/${encodeURIComponent(spellId)}/rolls/effect`, { playerKey, effectIndex, spellSlotLevel, choiceIndex, equipmentInstanceId, turnId })
  ), [playerKey, reloadAfter, sheetPath, turnId]);

  const updateResource = useCallback(async (sheet: CharacterSheet, resourceId: string, currentUses: number) => {
    try { replaceSheet((await postJson<{ sheet: CharacterSheet }>(`${sheetPath(sheet)}/resources/${encodeURIComponent(resourceId)}`, { playerKey, currentUses })).sheet); }
    catch (error) { fail(error); }
  }, [fail, playerKey, replaceSheet, sheetPath]);

  const respondToResolutionPrompt = useCallback(async (prompt: ResolutionInterceptorPrompt, use: boolean) => {
    try {
      const body = await postJson<{ prompt?: ResolutionInterceptorPrompt; resolution?: RollLogEntry["resolution"]; logEntry?: RollLogEntry }>(
        `/api/rooms/${encodeURIComponent(roomId)}/resolution-prompts/${encodeURIComponent(prompt.id)}/respond`, { playerKey, use }
      );
      setResolutionPrompts((current) => current.filter((candidate) => candidate.id !== prompt.id));
      if (body.prompt) setResolutionPrompts((current) => upsertResolutionPrompt(current, body.prompt!));
      if (body.resolution && body.logEntry) {
        setRolls((current) => (body.resolution!.responseRolls ?? []).reduce(upsertPendingRoll, current.filter((roll) => roll.id !== prompt.sourceRoll.id)));
        setRollHistory((current) => appendRollLogEntry(current, body.logEntry!));
        setSheets((current) => applyResolvedRollToSheetState(current, body.resolution!));
      }
    } catch (error) { fail(error); }
  }, [fail, playerKey, roomId, setResolutionPrompts, setRollHistory, setRolls, setSheets]);

  const restSheets = useCallback(async (rest: "short" | "long", hitDice: RestHitDieSelection[] = []): Promise<boolean> => {
    try {
      applySheetState(await postJson<SheetStateResponse>(`/api/rooms/${encodeURIComponent(roomId)}/sheet/rest`, { playerKey, rest }, hitDice));
      return true;
    } catch (error) {
      fail(error);
      return false;
    }
  }, [applySheetState, fail, playerKey, roomId]);

  const clearSheetRolls = useCallback(async (sheet: CharacterSheet) => {
    try { applySheetState(await postJson<SheetStateResponse>(`${sheetPath(sheet)}/rolls/clear`, { playerKey })); }
    catch (error) { fail(error); }
  }, [applySheetState, fail, playerKey, sheetPath]);

  const updateSheetLevel = useCallback(async (sheet: CharacterSheet, delta: 1 | -1) => {
    try { replaceSheet((await postJson<{ sheet: CharacterSheet }>(`${sheetPath(sheet)}/level`, { playerKey, delta, className: sheet.characterClass.name })).sheet); }
    catch (error) { fail(error); }
  }, [fail, playerKey, replaceSheet, sheetPath]);

  const updateProgressionChoice = useCallback(async (sheet: CharacterSheet, choiceId: string, values: string[]) => {
    try { replaceSheet((await postJson<{ sheet: CharacterSheet }>(`${sheetPath(sheet)}/choices/${encodeURIComponent(choiceId)}`, { playerKey }, { values })).sheet); }
    catch (error) { fail(error); }
  }, [fail, playerKey, replaceSheet, sheetPath]);

  const updateEquipmentSlot = useCallback(async (sheet: CharacterSheet, itemId: string, slot: EquipmentSlot) => {
    try { replaceSheet((await postJson<{ sheet: CharacterSheet }>(`${sheetPath(sheet)}/equipment/${encodeURIComponent(itemId)}/slot`, { playerKey, slot })).sheet); }
    catch (error) { fail(error); }
  }, [fail, playerKey, replaceSheet, sheetPath]);

  const updateCondition = useCallback(async (sheet: CharacterSheet, condition: ConditionType, active: boolean) => {
    try { replaceSheet((await postJson<{ sheet: CharacterSheet }>(`${sheetPath(sheet)}/conditions/${encodeURIComponent(condition)}`, { playerKey, active })).sheet); }
    catch (error) { fail(error); }
  }, [fail, playerKey, replaceSheet, sheetPath]);

  const removeOngoingEffect = useCallback(async (sheet: CharacterSheet, resolutionSeed: number, effectNodePath: number[]) => {
    try {
      replaceSheet((await postJson<{ sheet: CharacterSheet }>(
        `${sheetPath(sheet)}/ongoing-effects/remove`,
        { playerKey },
        { resolutionSeed, effectNodePath }
      )).sheet);
    } catch (error) { fail(error); }
  }, [fail, playerKey, replaceSheet, sheetPath]);

  const updateExhaustion = useCallback(async (sheet: CharacterSheet, level: number) => {
    try { replaceSheet((await postJson<{ sheet: CharacterSheet }>(`${sheetPath(sheet)}/exhaustion`, { playerKey, level })).sheet); }
    catch (error) { fail(error); }
  }, [fail, playerKey, replaceSheet, sheetPath]);

  const updateDamageDefense = useCallback(async (sheet: CharacterSheet, defense: DamageDefenseType, damageType: DamageType, active: boolean) => {
    try { replaceSheet((await postJson<{ sheet: CharacterSheet }>(`${sheetPath(sheet)}/defenses/${encodeURIComponent(defense)}/${encodeURIComponent(damageType)}`, { playerKey, active })).sheet); }
    catch (error) { fail(error); }
  }, [fail, playerKey, replaceSheet, sheetPath]);

  const rollAdHocDice = useCallback(async (dice: DiceType, count: number) => {
    try { return (await postJson<{ roll: RollPayload }>(`/api/rooms/${encodeURIComponent(roomId)}/dice`, { playerKey, dice, count })).roll; }
    catch (error) { fail(error); return null; }
  }, [fail, playerKey, roomId]);

  const createCharacter = useCallback(async (draft: CharacterBuilderDraft) => {
    try {
      applySheetState(await postJson<SheetStateResponse>(`/api/rooms/${encodeURIComponent(roomId)}/characters`, { playerKey }, draft));
      setSheetStatus("idle");
    } catch (error) { fail(error); }
  }, [applySheetState, fail, playerKey, roomId, setSheetStatus]);

  return {
    clearSheetRolls,
    createCharacter,
    respondToResolutionPrompt,
    restSheets,
    rollAbilityCheck,
    rollAdHocDice,
    rollAttack,
    rollDamage,
    rollResourceAction,
    rollSavingThrow,
    rollDeathSavingThrow,
    rollSpellAttack,
    rollSpellDamage,
    rollSpellEffect,
    rollSpellHealing,
    rollSpellTemporaryHitPoints,
    rollBoundWeaponSpell,
    removeOngoingEffect,
    updateCondition,
    updateDamageDefense,
    updateEquipmentSlot,
    updateExhaustion,
    updateProgressionChoice,
    updateResource,
    updateSheetLevel
  };
}
