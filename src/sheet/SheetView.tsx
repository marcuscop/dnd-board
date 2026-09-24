import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { MutableRefObject } from "react";
import { AbilityRollType, RollResolutionMode, SheetSectionType, TokenKind } from "../types";
import type {
  AbilityType,
  CharacterBuilderDraft,
  CharacterSheet,
  ConditionType,
  DamageType,
  DiceType,
  EncounterState,
  EquipmentSlot,
  ProgressionChoice,
  ResolutionInterceptorPrompt,
  RollAction,
  RollLogEntry,
  RollPayload,
  Token
} from "../types";
import { ABILITY_SCORE_OPTIONS, SAME_ABILITY_VALUE } from "../character/abilityOptions";
import { CharacterBuilderPanel, shouldShowCharacterBuilder } from "../builder/CharacterBuilderPanel";
import { AdHocDiceRoller } from "./AdHocDiceRoller";
import { EncounterControls } from "./EncounterControls";
import { ResolutionPromptPanel } from "./ResolutionPromptPanel";
import { RestControls } from "./RestControls";
import type { RestHitDieSelection } from "./RestControls";
import { InlineRolls, isTargetableRoll, RollCard, RollLogRow } from "./Rolls";
import {
  canRollSheet,
  cardResolvedRolls,
  cleanName,
  equipmentSlotOptions,
  formatHp,
  formatPlayerName,
  formatSigned,
  hasDamageDefenses,
  hasPurseCoins,
  rollMatchesSource,
  rollMatchesSourceAction,
  shortAbilityName
} from "./sheetUtils";

type ConnectionState = "connecting" | "connected" | "disconnected";

const CONDITION_OPTIONS: ConditionType[] = [
  "bane",
  "banished",
  "barkskin",
  "blinded",
  "bladeWard",
  "blessed",
  "blurred",
  "calmEmotionsImmunity",
  "calmEmotionsIndifferent",
  "charmed",
  "commandApproach",
  "commandDrop",
  "commandFlee",
  "commandGrovel",
  "commandHalt",
  "darkvision",
  "dead",
  "deafened",
  "enhanceAbilityCharisma",
  "enhanceAbilityDexterity",
  "enhanceAbilityIntelligence",
  "enhanceAbilityStrength",
  "enhanceAbilityWisdom",
  "enlarged",
  "expeditiousRetreat",
  "faerieFire",
  "featherFall",
  "fullCover",
  "flying",
  "frightened",
  "grappled",
  "guidance",
  "halfCover",
  "hasted",
  "heavilyObscured",
  "heroism",
  "incapacitated",
  "invisible",
  "jump",
  "levitating",
  "longstrider",
  "mageArmor",
  "paralyzed",
  "petrified",
  "phantasmalKiller",
  "passWithoutTrace",
  "poisoned",
  "prone",
  "protectionFromPoison",
  "rayOfEnfeeblement",
  "reduced",
  "resistantAcid",
  "resistantBludgeoning",
  "resistantCold",
  "resistantFire",
  "resistantForce",
  "resistantLightning",
  "resistantNecrotic",
  "resistantPiercing",
  "resistantPoison",
  "resistantPsychic",
  "resistantRadiant",
  "resistantSlashing",
  "resistantThunder",
  "resistanceAcid",
  "resistanceBludgeoning",
  "resistanceCold",
  "resistanceFire",
  "resistanceForce",
  "resistanceLightning",
  "resistanceNecrotic",
  "resistancePiercing",
  "resistancePoison",
  "resistancePsychic",
  "resistanceRadiant",
  "resistanceSlashing",
  "resistanceThunder",
  "restrained",
  "shielded",
  "shieldOfFaith",
  "shillelagh",
  "slowed",
  "stable",
  "stunned",
  "synapticStatic",
  "threeQuartersCover",
  "unconscious",
  "seeInvisibility",
  "wardingBond",
  "zoneOfTruth"
];
export type DamageDefenseType = "resistance" | "vulnerability" | "immunity";
const DAMAGE_TYPE_OPTIONS: DamageType[] = [
  "acid",
  "bludgeoning",
  "cold",
  "fire",
  "force",
  "lightning",
  "necrotic",
  "piercing",
  "poison",
  "psychic",
  "radiant",
  "slashing",
  "thunder"
];

export type SheetViewProps = {
  connection: ConnectionState;
  encounter: EncounterState | null;
  expandedSheetId: string | null;
  isDm: boolean;
  onReloadSheets: () => Promise<void>;
  onCreateCharacter: (draft: CharacterBuilderDraft) => Promise<void>;
  onExpand: (sheetId: string | null) => void;
  onEncounterChange: (encounter: EncounterState | null) => void;
  onClearSheetRolls: (sheet: CharacterSheet) => void;
  onRollAbilityCheck: (sheet: CharacterSheet, ability: string) => void;
  onRollAttack: (sheet: CharacterSheet, attackId: string, weaponOption?: string) => void;
  onRollDamage: (sheet: CharacterSheet, attackId: string, weaponOption?: string) => void;
  onRollResourceAction: (sheet: CharacterSheet, abilityId: string, actionId: string) => void;
  onRollSavingThrow: (sheet: CharacterSheet, ability: string) => void;
  onRollDeathSavingThrow: (sheet: CharacterSheet) => void;
  onRollSpellAttack: (sheet: CharacterSheet, spellId: string, spellSlotLevel?: number) => void;
  onRollSpellDamage: (sheet: CharacterSheet, spellId: string, effectIndex: number, spellSlotLevel?: number, instanceIndex?: number, choiceIndex?: number) => void;
  onRollBoundWeaponSpell: (sheet: CharacterSheet, spellId: string, effectIndex: number, equipmentInstanceId: string, choiceIndex?: number) => void;
  onRollSpellHealing: (sheet: CharacterSheet, spellId: string, effectIndex: number, spellSlotLevel?: number) => void;
  onRollSpellTemporaryHitPoints: (sheet: CharacterSheet, spellId: string, effectIndex: number, spellSlotLevel?: number) => void;
  onRollSpellEffect: (sheet: CharacterSheet, spellId: string, effectIndex: number, spellSlotLevel?: number, choiceIndex?: number, equipmentInstanceId?: string) => void;
  onRollAdHocDice: (dice: DiceType, count: number) => Promise<RollPayload | null>;
  onRestSheets: (rest: "short" | "long", hitDice?: RestHitDieSelection[]) => Promise<boolean>;
  onUpdateProgressionChoice: (sheet: CharacterSheet, choiceId: string, values: string[]) => void;
  onUpdateCondition: (sheet: CharacterSheet, condition: ConditionType, active: boolean) => void;
  onRemoveOngoingEffect: (sheet: CharacterSheet, resolutionSeed: number, effectNodePath: number[]) => void;
  onUpdateExhaustion: (sheet: CharacterSheet, level: number) => void;
  onUpdateDamageDefense: (sheet: CharacterSheet, defense: DamageDefenseType, damageType: DamageType, active: boolean) => void;
  onUpdateEquipmentSlot: (sheet: CharacterSheet, itemId: string, slot: EquipmentSlot) => void;
  onUpdateSheetLevel: (sheet: CharacterSheet, delta: 1 | -1) => void;
  onUpdateResource: (sheet: CharacterSheet, resourceId: string, currentUses: number) => void;
  onRespondToResolutionPrompt: (prompt: ResolutionInterceptorPrompt, use: boolean) => void;
  playerKey: string;
  roomId: string;
  resolutionPrompts: ResolutionInterceptorPrompt[];
  rollHistory: RollLogEntry[];
  rolls: RollPayload[];
  sheets: CharacterSheet[];
  sheetStatus: "idle" | "loading" | "error";
  tokens: Token[];
};

export function SheetView({ connection, encounter, expandedSheetId, isDm, onReloadSheets, onCreateCharacter, onClearSheetRolls, onExpand, onEncounterChange, onRollAbilityCheck, onRollAttack, onRollDamage, onRollResourceAction, onRollSavingThrow, onRollDeathSavingThrow, onRollSpellAttack, onRollSpellDamage, onRollBoundWeaponSpell, onRollSpellHealing, onRollSpellTemporaryHitPoints, onRollSpellEffect, onRollAdHocDice, onRestSheets, onUpdateProgressionChoice, onUpdateCondition, onRemoveOngoingEffect, onUpdateExhaustion, onUpdateDamageDefense, onUpdateEquipmentSlot, onUpdateSheetLevel, onUpdateResource, onRespondToResolutionPrompt, playerKey, roomId, resolutionPrompts, rollHistory, rolls, sheets, sheetStatus, tokens }: SheetViewProps) {
  const expandedSheet = expandedSheetId ? sheets.find((sheet) => sheet.id === expandedSheetId) : null;
  const partySheets = useMemo(() => sheets.filter((sheet) => sheet.kind === TokenKind.CHARACTER), [sheets]);
  const otherSheets = useMemo(() => sheets.filter((sheet) => sheet.kind !== TokenKind.CHARACTER), [sheets]);
  const showCharacterBuilder = shouldShowCharacterBuilder(isDm, playerKey, partySheets);
  const [draggingRollId, setDraggingRollId] = useState<string | null>(null);
  const preserveDraggingRollRef = useRef(false);
  const [dropTargetSheetId, setDropTargetSheetId] = useState<string | null>(null);
  const [clearedCardRollIds, setClearedCardRollIds] = useState<Set<string>>(() => new Set());
  const draggingRoll = useMemo(() => rolls.find((roll) => roll.id === draggingRollId), [draggingRollId, rolls]);
  const canDropRoll = isDm && isTargetableRoll(draggingRoll);

  const applyRollToSheet = useCallback(
    async (rollId: string, target: CharacterSheet, preserveRoll = false) => {
      if (!isTargetableRoll(rolls.find((roll) => roll.id === rollId))) {
        setDraggingRollId(null);
        preserveDraggingRollRef.current = false;
        setDropTargetSheetId(null);
        return;
      }
      try {
        const params = new URLSearchParams({ playerKey, targetSheetId: target.id, preserveRoll: String(preserveRoll) });
        const response = await fetch(`/api/rooms/${encodeURIComponent(roomId)}/rolls/${encodeURIComponent(rollId)}/resolve?${params}`, {
          method: "POST"
        });
        if (!response.ok) {
          throw new Error(await response.text());
        }
        await onReloadSheets();
      } catch (error) {
        console.error(error);
      } finally {
        setDraggingRollId(null);
        preserveDraggingRollRef.current = false;
        setDropTargetSheetId(null);
      }
    },
    [onReloadSheets, playerKey, rolls]
  );
  useEffect(() => {
    const handleShiftRollDrop = (event: Event) => {
      const detail = (event as CustomEvent<{ rollId?: string; targetSheetId?: string }>).detail;
      if (!detail?.rollId || !detail.targetSheetId) return;
      const target = sheets.find((sheet) => sheet.id === detail.targetSheetId);
      if (!target) return;
      void applyRollToSheet(detail.rollId, target, true);
    };
    window.addEventListener("roll-card-shift-drop", handleShiftRollDrop);
    return () => window.removeEventListener("roll-card-shift-drop", handleShiftRollDrop);
  }, [applyRollToSheet, sheets]);
  const clearRollsForSheet = useCallback(
    (sheet: CharacterSheet) => {
      const resolvedCardEntryIds = rollHistory.filter((entry) => entry.resolution && entry.roll.tokenId === sheet.tokenId).map((entry) => entry.id);
      setClearedCardRollIds((current) => new Set([...current, ...resolvedCardEntryIds]));
      onClearSheetRolls(sheet);
    },
    [onClearSheetRolls, rollHistory]
  );

  return (
    <main className="sheet-shell">
      <header className="sheet-header">
        <div>
          <h1>Character Sheets</h1>
          <p className="status">
            {connection} · You are {formatPlayerName(playerKey, tokens)}
          </p>
        </div>
        {!expandedSheet && isDm && (
          <RestControls sheets={partySheets} disabled={encounter !== null} onRest={onRestSheets} />
        )}
        {!expandedSheet && (
          <EncounterControls
            encounter={encounter}
            isDm={isDm}
            onEncounterChange={onEncounterChange}
            playerKey={playerKey}
            roomId={roomId}
            sheets={sheets}
            tokens={tokens}
          />
        )}
      </header>

      <ResolutionPromptPanel
        isDm={isDm}
        prompts={resolutionPrompts}
        onRespond={onRespondToResolutionPrompt}
      />

      {expandedSheet ? (
        <FullSheet
          sheet={expandedSheet}
          encounter={encounter}
          currentParticipantName={sheets.find((sheet) => sheet.id === encounter?.currentParticipantId)?.name}
          canRoll={canRollSheet(expandedSheet, playerKey, isDm)}
          pendingRolls={rolls.filter((roll) => roll.tokenId === expandedSheet.tokenId)}
          resolvedRolls={cardResolvedRolls(expandedSheet, rollHistory, clearedCardRollIds)}
          rollDraggable={isDm}
          onClearSheetRolls={clearRollsForSheet}
          onDragRollEnd={() => {
            setDraggingRollId(null);
            preserveDraggingRollRef.current = false;
            setDropTargetSheetId(null);
          }}
          onDragRollStart={(rollId, preserveRoll) => {
            preserveDraggingRollRef.current = preserveRoll;
            setDraggingRollId(rollId);
          }}
          onRollAbilityCheck={onRollAbilityCheck}
          onRollAttack={onRollAttack}
          onRollDamage={onRollDamage}
          onRollResourceAction={onRollResourceAction}
          onRollSavingThrow={onRollSavingThrow}
          onRollDeathSavingThrow={onRollDeathSavingThrow}
          onRollSpellAttack={onRollSpellAttack}
          onRollSpellDamage={onRollSpellDamage}
          onRollBoundWeaponSpell={onRollBoundWeaponSpell}
          onRollSpellHealing={onRollSpellHealing}
          onRollSpellTemporaryHitPoints={onRollSpellTemporaryHitPoints}
          onRollSpellEffect={onRollSpellEffect}
          onUpdateProgressionChoice={onUpdateProgressionChoice}
          onUpdateCondition={onUpdateCondition}
          onRemoveOngoingEffect={onRemoveOngoingEffect}
          onUpdateExhaustion={onUpdateExhaustion}
          onUpdateDamageDefense={onUpdateDamageDefense}
          onUpdateEquipmentSlot={onUpdateEquipmentSlot}
          onUpdateSheetLevel={onUpdateSheetLevel}
          onUpdateResource={onUpdateResource}
          onClose={() => onExpand(null)}
          isDm={isDm}
        />
      ) : (
        <div className="sheet-sections" aria-busy={sheetStatus === "loading"}>
          {showCharacterBuilder && <CharacterBuilderPanel isDm={isDm} onCreateCharacter={onCreateCharacter} playerKey={playerKey} roomId={roomId} sheets={partySheets} />}
          <SheetSection
            title="Party"
            sheets={partySheets}
            canDrop={canDropRoll}
            dropTargetSheetId={dropTargetSheetId}
            onApplyRoll={applyRollToSheet}
            onClearSheetRolls={clearRollsForSheet}
            onDropTarget={setDropTargetSheetId}
            onExpand={onExpand}
            onUpdateProgressionChoice={onUpdateProgressionChoice}
            onUpdateSheetLevel={onUpdateSheetLevel}
            rolls={rolls}
            rollHistory={rollHistory}
            clearedCardRollIds={clearedCardRollIds}
            playerKey={playerKey}
            isDm={isDm}
            draggingRollId={draggingRollId}
            onDragRollEnd={() => {
              setDraggingRollId(null);
              preserveDraggingRollRef.current = false;
              setDropTargetSheetId(null);
            }}
            onDragRollStart={(rollId, preserveRoll) => {
              preserveDraggingRollRef.current = preserveRoll;
              setDraggingRollId(rollId);
            }}
            preserveDraggingRollRef={preserveDraggingRollRef}
          />
          {otherSheets.length > 0 && (
            <SheetSection
              title="Other"
              sheets={otherSheets}
              canDrop={canDropRoll}
              dropTargetSheetId={dropTargetSheetId}
              onApplyRoll={applyRollToSheet}
              onClearSheetRolls={clearRollsForSheet}
              onDropTarget={setDropTargetSheetId}
              onExpand={onExpand}
              onUpdateProgressionChoice={onUpdateProgressionChoice}
              onUpdateSheetLevel={onUpdateSheetLevel}
              rolls={rolls}
              rollHistory={rollHistory}
              clearedCardRollIds={clearedCardRollIds}
              playerKey={playerKey}
              isDm={isDm}
              draggingRollId={draggingRollId}
              onDragRollEnd={() => {
                setDraggingRollId(null);
                preserveDraggingRollRef.current = false;
                setDropTargetSheetId(null);
              }}
              onDragRollStart={(rollId, preserveRoll) => {
                preserveDraggingRollRef.current = preserveRoll;
                setDraggingRollId(rollId);
              }}
              preserveDraggingRollRef={preserveDraggingRollRef}
            />
          )}
        </div>
      )}

      <AdHocDiceRoller onRoll={onRollAdHocDice} />

      <aside className="roll-log">
        <h2>Logs</h2>
        {rollHistory.length > 0 && (
          <ol>
            {rollHistory.map((entry) => (
              <RollLogRow key={entry.id} entry={entry} roller={sheets.find((sheet) => sheet.tokenId === entry.roll.tokenId)} />
            ))}
          </ol>
        )}
      </aside>
    </main>
  );
}

function SheetSection({
  title,
  sheets,
  canDrop,
  dropTargetSheetId,
  onApplyRoll,
  onClearSheetRolls,
  onDragRollEnd,
  onDragRollStart,
  onDropTarget,
  onExpand,
  onUpdateProgressionChoice,
  onUpdateSheetLevel,
  playerKey,
  isDm,
  draggingRollId,
  rolls,
  rollHistory,
  clearedCardRollIds,
  preserveDraggingRollRef
}: {
  title: string;
  sheets: CharacterSheet[];
  canDrop: boolean;
  dropTargetSheetId: string | null;
  onApplyRoll: (rollId: string, target: CharacterSheet, preserveRoll?: boolean) => void;
  onClearSheetRolls: (sheet: CharacterSheet) => void;
  onDragRollEnd: () => void;
  onDragRollStart: (rollId: string, preserveRoll: boolean) => void;
  onDropTarget: (sheetId: string | null) => void;
  onExpand: (sheetId: string | null) => void;
  onUpdateProgressionChoice: (sheet: CharacterSheet, choiceId: string, values: string[]) => void;
  onUpdateSheetLevel: (sheet: CharacterSheet, delta: 1 | -1) => void;
  playerKey: string;
  isDm: boolean;
  draggingRollId: string | null;
  rolls: RollPayload[];
  rollHistory: RollLogEntry[];
  clearedCardRollIds: Set<string>;
  preserveDraggingRollRef: MutableRefObject<boolean>;
}) {
  if (sheets.length === 0) return null;

  return (
    <section>
      <h2>{title}</h2>
      <div className="sheet-grid">
        {sheets.map((sheet) => (
          <SheetCard
            key={sheet.id}
            sheet={sheet}
            canDrop={canDrop}
            draggingRollId={draggingRollId}
            isDropTarget={dropTargetSheetId === sheet.id}
            canClearRolls={canRollSheet(sheet, playerKey, isDm)}
            onApplyRoll={onApplyRoll}
            onClearSheetRolls={onClearSheetRolls}
            onDragRollEnd={onDragRollEnd}
            onDragRollStart={onDragRollStart}
            onDropTarget={onDropTarget}
            onExpand={() => onExpand(sheet.id)}
            onUpdateProgressionChoice={onUpdateProgressionChoice}
            onUpdateSheetLevel={onUpdateSheetLevel}
            pendingRolls={rolls.filter((roll) => roll.tokenId === sheet.tokenId)}
            preserveDraggingRollRef={preserveDraggingRollRef}
            resolvedRolls={cardResolvedRolls(sheet, rollHistory, clearedCardRollIds)}
            rollDraggable={isDm}
          />
        ))}
      </div>
    </section>
  );
}

function SheetCard({
  sheet,
  canClearRolls,
  canDrop,
  draggingRollId,
  isDropTarget,
  onApplyRoll,
  onClearSheetRolls,
  onDragRollEnd,
  onDragRollStart,
  onDropTarget,
  onExpand,
  onUpdateProgressionChoice,
  onUpdateSheetLevel,
  pendingRolls,
  preserveDraggingRollRef,
  resolvedRolls,
  rollDraggable
}: {
  sheet: CharacterSheet;
  canClearRolls: boolean;
  canDrop: boolean;
  draggingRollId: string | null;
  isDropTarget: boolean;
  onApplyRoll: (rollId: string, target: CharacterSheet, preserveRoll?: boolean) => void;
  onClearSheetRolls: (sheet: CharacterSheet) => void;
  onDragRollEnd: () => void;
  onDragRollStart: (rollId: string, preserveRoll: boolean) => void;
  onDropTarget: (sheetId: string | null) => void;
  onExpand: () => void;
  onUpdateProgressionChoice: (sheet: CharacterSheet, choiceId: string, values: string[]) => void;
  onUpdateSheetLevel: (sheet: CharacterSheet, delta: 1 | -1) => void;
  pendingRolls: RollPayload[];
  preserveDraggingRollRef: MutableRefObject<boolean>;
  resolvedRolls: RollLogEntry[];
  rollDraggable: boolean;
}) {
  const hasCardRolls = pendingRolls.length > 0 || resolvedRolls.length > 0;

  return (
    <article
      data-roll-drop-sheet-id={sheet.id}
      className={["sheet-card", canDrop ? "drop-ready" : "", isDropTarget ? "drop-target" : ""].filter(Boolean).join(" ")}
      onDragEnter={() => {
        if (canDrop) onDropTarget(sheet.id);
      }}
      onDragOver={(event) => {
        if (!canDrop) return;
        event.preventDefault();
        event.dataTransfer.dropEffect = "copy";
        onDropTarget(sheet.id);
      }}
      onDragLeave={() => {
        if (isDropTarget) onDropTarget(null);
      }}
      onDrop={(event) => {
        if (!canDrop || !draggingRollId) return;
        event.preventDefault();
        const preserveRoll = preserveDraggingRollRef.current || event.shiftKey;
        onApplyRoll(draggingRollId, sheet, preserveRoll);
      }}
    >
      <button className="sheet-portrait" onClick={onExpand} aria-label={`Open ${sheet.name}`}>
        {sheet.avatarUrl ? <img src={sheet.avatarUrl} alt="" draggable={false} /> : sheet.name.slice(0, 2).toUpperCase()}
      </button>
      <div className="sheet-card-main">
        <button className="text-button" onClick={onExpand}>
          {sheet.name}
        </button>
        <p className="status">
          HP {formatHp(sheet.hp)} · AC {sheet.armorClass} · {sheet.characterClass.nameLabel} {sheet.characterClass.level}
        </p>
        {rollDraggable && <LevelStepper sheet={sheet} onUpdateSheetLevel={onUpdateSheetLevel} />}
        {sheet.pendingChoices.length > 0 && (
          <button className="choice-alert" onClick={onExpand}>
            {pendingChoiceSummary(sheet)}
          </button>
        )}
        {(sheet.activeConcentration || sheet.conditions.length > 0) && (
          <div className="condition-list">
            {sheet.activeConcentration && <span className="concentration-pill">Concentration: {sheet.activeConcentration.spellName}</span>}
            {sheet.conditions.map((condition) => <span className={condition === "dead" ? "dead-pill" : ""} key={condition}>{cleanName(condition)}</span>)}
          </div>
        )}
      </div>
      <div className="card-roll-slot">
        {hasCardRolls ? (
          <>
            {canClearRolls && (
              <button className="clear-rolls-button" onClick={() => onClearSheetRolls(sheet)} type="button">
                Clear Rolls
              </button>
            )}
            {pendingRolls.map((pendingRoll) => (
              <RollCard
                key={pendingRoll.id}
                roll={pendingRoll}
                roller={sheet}
                draggable={rollDraggable && isTargetableRoll(pendingRoll)}
                compact
                onDragEnd={onDragRollEnd}
                onDragStart={(preserveRoll) => onDragRollStart(pendingRoll.id, preserveRoll)}
              />
            ))}
            {resolvedRolls.map((entry) => (
              <RollCard
                key={entry.id}
                roll={entry.roll}
                roller={sheet}
                draggable={false}
                compact
                onDragEnd={onDragRollEnd}
                onDragStart={() => undefined}
              />
            ))}
          </>
        ) : (
          <span className="empty-roll-slot">No roll</span>
        )}
      </div>
    </article>
  );
}

function LevelStepper({ sheet, onUpdateSheetLevel }: { sheet: CharacterSheet; onUpdateSheetLevel: (sheet: CharacterSheet, delta: 1 | -1) => void }) {
  const hasPendingChoices = sheet.pendingChoices.length > 0;
  const pendingSummary = pendingChoiceSummary(sheet);
  return (
    <>
      <div className="level-stepper">
        <button disabled={sheet.characterClass.level <= 1} onClick={() => onUpdateSheetLevel(sheet, -1)} aria-label={`Level down ${sheet.name}`}>
          -
        </button>
        <span>Level {sheet.characterClass.level}</span>
        <button
          disabled={sheet.characterClass.level >= 20 || hasPendingChoices}
          onClick={() => onUpdateSheetLevel(sheet, 1)}
          aria-label={`Level up ${sheet.name}`}
        >
          +
        </button>
      </div>
      {hasPendingChoices && <span className="level-blocker">Resolve: {pendingSummary}</span>}
    </>
  );
}

function pendingChoiceSummary(sheet: CharacterSheet): string {
  if (sheet.pendingChoices.length === 0) return "";
  return sheet.pendingChoices.map((choice) => choice.label).join(", ");
}

function ConditionPanel({
  canRoll,
  sheet,
  onUpdateCondition,
  onUpdateExhaustion
}: {
  canRoll: boolean;
  sheet: CharacterSheet;
  onUpdateCondition: (sheet: CharacterSheet, condition: ConditionType, active: boolean) => void;
  onUpdateExhaustion: (sheet: CharacterSheet, level: number) => void;
}) {
  const activeConditions = new Set(sheet.conditions);
  const exhaustionLevel = sheet.exhaustionLevel ?? (activeConditions.has("exhaustion") ? 1 : 0);

  return (
    <section className="sheet-panel">
      <h2>Conditions</h2>
      <div className="resource-row">
        <span>Exhaustion</span>
        <div className="resource-controls">
          <button disabled={!canRoll || exhaustionLevel <= 0} onClick={() => onUpdateExhaustion(sheet, exhaustionLevel - 1)} type="button">-</button>
          <strong>{exhaustionLevel}</strong>
          <button disabled={!canRoll || exhaustionLevel >= 6} onClick={() => onUpdateExhaustion(sheet, exhaustionLevel + 1)} type="button">+</button>
        </div>
      </div>
      <div className="condition-toggle-grid">
        {CONDITION_OPTIONS.map((condition) => {
          const active = activeConditions.has(condition);
          return (
            <button
              className={active ? "active" : ""}
              disabled={!canRoll}
              key={condition}
              onClick={() => onUpdateCondition(sheet, condition, !active)}
              type="button"
            >
              {cleanName(condition)}
            </button>
          );
        })}
      </div>
    </section>
  );
}

function DamageDefensePanel({
  isDm,
  sheet,
  onUpdateDamageDefense
}: {
  isDm: boolean;
  sheet: CharacterSheet;
  onUpdateDamageDefense: (sheet: CharacterSheet, defense: DamageDefenseType, damageType: DamageType, active: boolean) => void;
}) {
  return (
    <section className="sheet-panel">
      <h2>Defenses</h2>
      {hasDamageDefenses(sheet) && (
        <div className="compact-list">
          {sheet.damageResistances.length > 0 && <span>Resist {sheet.damageResistancesLabel.join(", ")}</span>}
          {sheet.damageVulnerabilities.length > 0 && <span>Vulnerable {sheet.damageVulnerabilitiesLabel.join(", ")}</span>}
          {sheet.damageImmunities.length > 0 && <span>Immune {sheet.damageImmunitiesLabel.join(", ")}</span>}
        </div>
      )}
      {isDm && (
        <div className="damage-defense-list">
          <DamageDefenseToggleRow
            activeDamageTypes={sheet.damageResistances}
            defense="resistance"
            label="Resist"
            onUpdateDamageDefense={onUpdateDamageDefense}
            sheet={sheet}
          />
          <DamageDefenseToggleRow
            activeDamageTypes={sheet.damageVulnerabilities}
            defense="vulnerability"
            label="Vulnerable"
            onUpdateDamageDefense={onUpdateDamageDefense}
            sheet={sheet}
          />
          <DamageDefenseToggleRow
            activeDamageTypes={sheet.damageImmunities}
            defense="immunity"
            label="Immune"
            onUpdateDamageDefense={onUpdateDamageDefense}
            sheet={sheet}
          />
        </div>
      )}
    </section>
  );
}

function DamageDefenseToggleRow({
  activeDamageTypes,
  defense,
  label,
  sheet,
  onUpdateDamageDefense
}: {
  activeDamageTypes: DamageType[];
  defense: DamageDefenseType;
  label: string;
  sheet: CharacterSheet;
  onUpdateDamageDefense: (sheet: CharacterSheet, defense: DamageDefenseType, damageType: DamageType, active: boolean) => void;
}) {
  const active = new Set(activeDamageTypes);
  return (
    <div className="damage-defense-row">
      <span>{label}</span>
      <div className="damage-defense-toggle-grid">
        {DAMAGE_TYPE_OPTIONS.map((damageType) => {
          const isActive = active.has(damageType);
          return (
            <button
              className={isActive ? "active" : ""}
              key={`${defense}-${damageType}`}
              onClick={() => onUpdateDamageDefense(sheet, defense, damageType, !isActive)}
              type="button"
            >
              {cleanName(damageType)}
            </button>
          );
        })}
      </div>
    </div>
  );
}

function ProgressionChoicePanel({
  sheet,
  onUpdateProgressionChoice
}: {
  sheet: CharacterSheet;
  onUpdateProgressionChoice: (sheet: CharacterSheet, choiceId: string, values: string[]) => void;
}) {
  return (
    <section className="sheet-panel progression-panel">
      <h2>Level Choices</h2>
      <div className="progression-choice-list">
        {sheet.pendingChoices.map((choice) => (
          <ProgressionChoiceRow key={choice.id} sheet={sheet} choice={choice} onUpdateProgressionChoice={onUpdateProgressionChoice} />
        ))}
      </div>
    </section>
  );
}

function ProgressionChoiceRow({
  sheet,
  choice,
  onUpdateProgressionChoice
}: {
  sheet: CharacterSheet;
  choice: ProgressionChoice;
  onUpdateProgressionChoice: (sheet: CharacterSheet, choiceId: string, values: string[]) => void;
}) {
  const [selected, setSelected] = useState<string[]>(choice.selected);
  const choiceStateKey = [
    choice.id,
    choice.minimum,
    choice.maximum,
    choice.selected.join(","),
    choice.options.map((option) => option.value).join(",")
  ].join(":");

  useEffect(() => {
    setSelected(choice.selected);
  }, [choiceStateKey]);

  if (choice.choiceType === "abilityScoreImprovement") {
    return <AbilityScoreImprovementChoice sheet={sheet} choice={choice} onUpdateProgressionChoice={onUpdateProgressionChoice} />;
  }

  if (choice.options.length === 0) {
    return (
      <article className="progression-choice">
        <div>
          <strong>{choice.label}</strong>
          <span>{choice.description}</span>
        </div>
      </article>
    );
  }

  const canApply = selected.length >= choice.minimum && selected.length <= choice.maximum;
  const single = choice.maximum === 1;

  return (
    <article className="progression-choice">
      <div>
        <strong>{choice.label}</strong>
        <span>
          {choice.description} Choose {choice.maximum}.
        </span>
      </div>
      {single ? (
        <select value={selected[0] ?? ""} onChange={(event) => setSelected(event.currentTarget.value ? [event.currentTarget.value] : [])}>
          <option value="">Choose...</option>
          {choice.options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      ) : (
        <div className="choice-options">
          {choice.options.map((option) => {
            const checked = selected.includes(option.value);
            return (
              <label className="choice-option" key={option.value}>
                <input
                  type="checkbox"
                  checked={checked}
                  disabled={!checked && selected.length >= choice.maximum}
                  onChange={(event) => {
                    if (event.currentTarget.checked) {
                      setSelected((current) => [...current, option.value].slice(0, choice.maximum));
                    } else {
                      setSelected((current) => current.filter((value) => value !== option.value));
                    }
                  }}
                />
                {option.label}
              </label>
            );
          })}
        </div>
      )}
      <button disabled={!canApply} onClick={() => onUpdateProgressionChoice(sheet, choice.id, selected)}>
        Apply
      </button>
    </article>
  );
}

function AbilityScoreImprovementChoice({
  sheet,
  choice,
  onUpdateProgressionChoice
}: {
  sheet: CharacterSheet;
  choice: ProgressionChoice;
  onUpdateProgressionChoice: (sheet: CharacterSheet, choiceId: string, values: string[]) => void;
}) {
  const [mode, setMode] = useState<"scores" | "feat">("scores");
  const [firstAbility, setFirstAbility] = useState<AbilityType>("strength");
  const [secondAbility, setSecondAbility] = useState<AbilityType | typeof SAME_ABILITY_VALUE>(SAME_ABILITY_VALUE);
  const [selectedFeat, setSelectedFeat] = useState("");
  const values = mode === "feat" ? [`feat:${selectedFeat}`] : [firstAbility, secondAbility === SAME_ABILITY_VALUE ? firstAbility : secondAbility];
  const canApply = mode === "scores" || selectedFeat.length > 0;

  return (
    <article className="progression-choice">
      <div>
        <strong>{choice.label}</strong>
        <span>{choice.description}</span>
      </div>
      <div className="asi-choice-controls">
        <div className="choice-mode-toggle" role="group" aria-label="Ability Score Improvement type">
          <button className={mode === "scores" ? "active" : ""} type="button" onClick={() => setMode("scores")}>
            Scores
          </button>
          <button className={mode === "feat" ? "active" : ""} type="button" onClick={() => setMode("feat")}>
            Feat
          </button>
        </div>
        {mode === "scores" ? (
          <>
            <label>
              <span>First +1</span>
              <select value={firstAbility} onChange={(event) => setFirstAbility(event.currentTarget.value as AbilityType)}>
                {ABILITY_SCORE_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>Second +1</span>
              <select value={secondAbility} onChange={(event) => setSecondAbility(event.currentTarget.value as AbilityType | typeof SAME_ABILITY_VALUE)}>
                <option value={SAME_ABILITY_VALUE}>Same ability</option>
                {ABILITY_SCORE_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
          </>
        ) : (
          <label>
            <span>Feat</span>
            <select value={selectedFeat} onChange={(event) => setSelectedFeat(event.currentTarget.value)}>
              <option value="">Choose...</option>
              {choice.options.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
        )}
      </div>
      <button disabled={!canApply} onClick={() => onUpdateProgressionChoice(sheet, choice.id, values)}>
        Apply
      </button>
    </article>
  );
}

function RollActionList({
  canRoll,
  pendingRolls,
  resolvedRolls = [],
  roller,
  rollActions,
  rollDraggable,
  onDragRollEnd,
  onDragRollStart,
  onRollAction
}: {
  canRoll: boolean;
  pendingRolls: RollPayload[];
  resolvedRolls?: RollLogEntry[];
  roller: CharacterSheet;
  rollActions: RollAction[];
  rollDraggable: boolean;
  onDragRollEnd: () => void;
  onDragRollStart: (rollId: string, preserveRoll: boolean) => void;
  onRollAction: (actionId: string) => void;
}) {
  if (rollActions.length === 0 && pendingRolls.length === 0 && resolvedRolls.length === 0) return null;

  return (
    <div className="inline-roll-area">
      {rollActions.length > 0 && (
        <div className="roll-action-buttons">
          {rollActions.map((action) => (
            <button key={action.id} disabled={!canRoll} onClick={() => onRollAction(action.id)}>
              Roll
            </button>
          ))}
        </div>
      )}
      <InlineRolls
        pendingRolls={pendingRolls}
        resolvedRolls={resolvedRolls}
        roller={roller}
        rollDraggable={rollDraggable}
        onDragRollEnd={onDragRollEnd}
        onDragRollStart={onDragRollStart}
      />
    </div>
  );
}

function SheetAbilityList({
  canRoll,
  onDragRollEnd,
  onDragRollStart,
  onRollResourceAction,
  onUpdateResource,
  pendingRolls,
  resolvedRolls = [],
  rollDraggable,
  sheet
}: {
  canRoll: boolean;
  onDragRollEnd: () => void;
  onDragRollStart: (rollId: string, preserveRoll: boolean) => void;
  onRollResourceAction: (sheet: CharacterSheet, resourceId: string, actionId: string) => void;
  onUpdateResource: (sheet: CharacterSheet, resourceId: string, currentUses: number) => void;
  pendingRolls: RollPayload[];
  resolvedRolls?: RollLogEntry[];
  rollDraggable: boolean;
  sheet: CharacterSheet;
}) {
  if (sheet.abilities.length === 0) return null;

  return (
    <section className="sheet-panel">
      <h2>Abilities</h2>
      <div className="resource-list">
        {sheet.abilities.map((ability) => {
          const resource = ability.resourceId ? sheet.resources.find((candidate) => candidate.resource === ability.resourceId) : undefined;
          const matchingRolls = pendingRolls.filter((roll) => rollMatchesSource(roll, SheetSectionType.ABILITIES, ability.id));
          const matchingResolvedRolls = resolvedRolls.filter((entry) => rollMatchesSource(entry.roll, SheetSectionType.ABILITIES, ability.id));

          return (
            <div className="resource-row" key={ability.id}>
              <div>
                <strong>{ability.name}</strong>
                <span>
                  {ability.source}
                  {ability.source ? " · " : ""}
                  {ability.activationLabel}
                </span>
              </div>
              {resource && (
                <ResourceStepper
                  canRoll={canRoll}
                  currentUses={resource.currentUses}
                  maxUses={resource.maxUses}
                  onUpdate={(currentUses) => onUpdateResource(sheet, resource.id, currentUses)}
                />
              )}
              {ability.description && <p>{ability.description}</p>}
              {ability.controls.some((control) => control.kind === "boundWeaponAttack") && (
                <div className="ability-roll-actions">
                  {ability.controls.map((control) => control.kind === "boundWeaponAttack" && control.attackId ? (
                    <button
                      disabled={!canRoll || Boolean(resource && resource.currentUses === 0)}
                      key={`${control.effectIndex ?? 0}:${control.attackId}`}
                      onClick={() => onRollResourceAction(sheet, ability.id, control.attackId!)}
                    >
                      {control.label}
                    </button>
                  ) : null)}
                </div>
              )}
              {(ability.rollActions ?? []).length > 0 ? (
                <RollActionList
                  canRoll={canRoll && (!resource || resource.currentUses > 0)}
                  pendingRolls={matchingRolls}
                  resolvedRolls={matchingResolvedRolls}
                  roller={sheet}
                  rollDraggable={rollDraggable}
                  rollActions={ability.rollActions ?? []}
                  onDragRollEnd={onDragRollEnd}
                  onDragRollStart={onDragRollStart}
                  onRollAction={(actionId) => onRollResourceAction(sheet, ability.id, actionId)}
                />
              ) : (
                <InlineRolls
                  pendingRolls={matchingRolls}
                  resolvedRolls={matchingResolvedRolls}
                  roller={sheet}
                  rollDraggable={rollDraggable}
                  onDragRollEnd={onDragRollEnd}
                  onDragRollStart={onDragRollStart}
                />
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}

function ResourceStepper({
  canRoll,
  currentUses,
  maxUses,
  onUpdate
}: {
  canRoll: boolean;
  currentUses: number;
  maxUses: number;
  onUpdate: (currentUses: number) => void;
}) {
  return (
    <div className="stepper">
      <button disabled={!canRoll || currentUses <= 0} onClick={() => onUpdate(currentUses - 1)}>
        -
      </button>
      <strong>
        {currentUses}/{maxUses}
      </strong>
      <button disabled={!canRoll || currentUses >= maxUses} onClick={() => onUpdate(currentUses + 1)}>
        +
      </button>
    </div>
  );
}

function FullSheet({
  sheet,
  encounter,
  currentParticipantName,
  canRoll,
  isDm,
  onClearSheetRolls,
  pendingRolls,
  resolvedRolls,
  rollDraggable,
  onDragRollEnd,
  onDragRollStart,
  onClose,
  onRollAbilityCheck,
  onRollAttack,
  onRollDamage,
  onRollResourceAction,
  onRollSavingThrow,
  onRollDeathSavingThrow,
  onRollSpellAttack,
  onRollSpellDamage,
  onRollBoundWeaponSpell,
  onRollSpellHealing,
  onRollSpellTemporaryHitPoints,
  onRollSpellEffect,
  onUpdateProgressionChoice,
  onUpdateCondition,
  onRemoveOngoingEffect,
  onUpdateExhaustion,
  onUpdateDamageDefense,
  onUpdateEquipmentSlot,
  onUpdateSheetLevel,
  onUpdateResource
}: {
  sheet: CharacterSheet;
  encounter: EncounterState | null;
  currentParticipantName?: string;
  canRoll: boolean;
  isDm: boolean;
  onClearSheetRolls: (sheet: CharacterSheet) => void;
  pendingRolls: RollPayload[];
  resolvedRolls: RollLogEntry[];
  rollDraggable: boolean;
  onDragRollEnd: () => void;
  onDragRollStart: (rollId: string, preserveRoll: boolean) => void;
  onClose: () => void;
  onRollAbilityCheck: (sheet: CharacterSheet, ability: string) => void;
  onRollAttack: (sheet: CharacterSheet, attackId: string, weaponOption?: string) => void;
  onRollDamage: (sheet: CharacterSheet, attackId: string, weaponOption?: string) => void;
  onRollResourceAction: (sheet: CharacterSheet, resourceId: string, actionId: string) => void;
  onRollSavingThrow: (sheet: CharacterSheet, ability: string) => void;
  onRollDeathSavingThrow: (sheet: CharacterSheet) => void;
  onRollSpellAttack: (sheet: CharacterSheet, spellId: string, spellSlotLevel?: number) => void;
  onRollSpellDamage: (sheet: CharacterSheet, spellId: string, effectIndex: number, spellSlotLevel?: number, instanceIndex?: number, choiceIndex?: number) => void;
  onRollBoundWeaponSpell: (sheet: CharacterSheet, spellId: string, effectIndex: number, equipmentInstanceId: string, choiceIndex?: number) => void;
  onRollSpellHealing: (sheet: CharacterSheet, spellId: string, effectIndex: number, spellSlotLevel?: number) => void;
  onRollSpellTemporaryHitPoints: (sheet: CharacterSheet, spellId: string, effectIndex: number, spellSlotLevel?: number) => void;
  onRollSpellEffect: (sheet: CharacterSheet, spellId: string, effectIndex: number, spellSlotLevel?: number, choiceIndex?: number, equipmentInstanceId?: string) => void;
  onUpdateProgressionChoice: (sheet: CharacterSheet, choiceId: string, values: string[]) => void;
  onUpdateCondition: (sheet: CharacterSheet, condition: ConditionType, active: boolean) => void;
  onRemoveOngoingEffect: (sheet: CharacterSheet, resolutionSeed: number, effectNodePath: number[]) => void;
  onUpdateExhaustion: (sheet: CharacterSheet, level: number) => void;
  onUpdateDamageDefense: (sheet: CharacterSheet, defense: DamageDefenseType, damageType: DamageType, active: boolean) => void;
  onUpdateEquipmentSlot: (sheet: CharacterSheet, itemId: string, slot: EquipmentSlot) => void;
  onUpdateSheetLevel: (sheet: CharacterSheet, delta: 1 | -1) => void;
  onUpdateResource: (sheet: CharacterSheet, resourceId: string, currentUses: number) => void;
}) {
  const scores = Object.entries(sheet.abilityScores);
  const metadata = [sheet.race, sheet.background, sheet.alignment].filter(Boolean).join(" · ");
  const [selectedWeaponOptions, setSelectedWeaponOptions] = useState<Record<string, string>>({});
  const encounterParticipant = encounter?.participantStates.find((participant) => participant.participantId === sheet.id);
  const actionBudget = encounterParticipant?.resources.find((resource) => resource.resource === "action");
  const bonusActionBudget = encounterParticipant?.resources.find((resource) => resource.resource === "bonusAction");
  const reactionBudget = encounterParticipant?.resources.find((resource) => resource.resource === "reaction");

  return (
    <section className="full-sheet">
      <div className="full-sheet-title">
        <button className="back-button" onClick={onClose} aria-label="Back to sheets">
          &lt;
        </button>
        <div className="full-sheet-identity">
          <span className="full-sheet-portrait">{sheet.avatarUrl ? <img src={sheet.avatarUrl} alt="" draggable={false} /> : sheet.name.slice(0, 2).toUpperCase()}</span>
          <div>
            <h2>{sheet.name}</h2>
            <p className="status">
              {sheet.characterClass.nameLabel} {sheet.characterClass.level}
              {metadata ? ` · ${metadata}` : ""}
            </p>
            {isDm && <LevelStepper sheet={sheet} onUpdateSheetLevel={onUpdateSheetLevel} />}
            {canRoll && (pendingRolls.length > 0 || resolvedRolls.length > 0) && (
              <button className="clear-rolls-button" onClick={() => onClearSheetRolls(sheet)} type="button">
                Clear Rolls
              </button>
            )}
          </div>
        </div>
      </div>
      {canRoll && sheet.pendingChoices.length > 0 && (
        <ProgressionChoicePanel sheet={sheet} onUpdateProgressionChoice={onUpdateProgressionChoice} />
      )}
      {encounter && (
        <div className="encounter-turn-notice">
          {encounter.currentParticipantId === sheet.id
            ? `Current turn · Action ${actionBudget?.current ?? 0}/${actionBudget?.maximum ?? 0} · Bonus Action ${bonusActionBudget?.current ?? 0}/${bonusActionBudget?.maximum ?? 0} · Reaction ${reactionBudget?.current ?? 0}/${reactionBudget?.maximum ?? 0}`
            : `Waiting for ${currentParticipantName ?? "current participant"} · Reactions ${reactionBudget?.current ?? 0}/${reactionBudget?.maximum ?? 0}`}
        </div>
      )}

      <div className="ability-grid">
        {scores.map(([ability, score]) => (
          <div key={ability}>
            <span>{shortAbilityName(ability)}</span>
            <strong>{score}</strong>
            <small>{formatSigned(Math.floor((score - 10) / 2))}</small>
            <div className="ability-roll-actions">
              <button disabled={!canRoll} onClick={() => onRollAbilityCheck(sheet, ability)}>
                Roll Check
              </button>
            </div>
            <InlineRolls
              pendingRolls={pendingRolls.filter((roll) => rollMatchesSourceAction(roll, SheetSectionType.ABILITY_SCORES, ability, "check"))}
              roller={sheet}
              rollDraggable={rollDraggable}
              onDragRollEnd={onDragRollEnd}
              onDragRollStart={onDragRollStart}
            />
          </div>
        ))}
      </div>

      <div className="sheet-stat-row">
        <SheetStat label="Armor" value={String(sheet.armorClass)} />
        <SheetStat label="Initiative" value={formatSigned(sheet.initiativeBonus)} />
        <SheetStat label="Speed" value={`${sheet.speed} ft`} />
        <SheetStat label="Proficiency" value={formatSigned(sheet.proficiencyBonus)} />
        <SheetStat label="HP" value={formatHp(sheet.hp)} />
        <SheetStat label="Temp HP" value={String(sheet.hp.temporary)} />
      </div>

      <div className="sheet-columns">
        <section className="sheet-panel">
          <h2>Saving Throws</h2>
          <div className="saving-throw-list">
            {sheet.savingThrows.map((save) => (
              <div className="saving-throw-row" key={save.ability}>
                <span>
                  {cleanName(save.ability)} {save.proficient ? "*" : ""} <strong>{formatSigned(save.modifier)}</strong>
                </span>
                <button disabled={!canRoll} onClick={() => onRollSavingThrow(sheet, save.ability)}>
                  Roll Save
                </button>
                <InlineRolls
                  pendingRolls={pendingRolls.filter((roll) => rollMatchesSourceAction(roll, SheetSectionType.ABILITY_SCORES, save.ability, "save"))}
                  roller={sheet}
                  rollDraggable={rollDraggable}
                  onDragRollEnd={onDragRollEnd}
                  onDragRollStart={onDragRollStart}
                />
              </div>
            ))}
            <div className="saving-throw-row">
              <span>Death Save</span>
              <button disabled={!canRoll || sheet.hp.current > 0 || sheet.conditions.includes("dead")} onClick={() => onRollDeathSavingThrow(sheet)}>
                Roll Save
              </button>
              <InlineRolls
                pendingRolls={pendingRolls.filter((roll) => rollMatchesSourceAction(roll, SheetSectionType.ABILITY_SCORES, AbilityRollType.DEATH_SAVE, AbilityRollType.DEATH_SAVE))}
                roller={sheet}
                rollDraggable={rollDraggable}
                onDragRollEnd={onDragRollEnd}
                onDragRollStart={onDragRollStart}
              />
            </div>
          </div>
        </section>

        <section className="sheet-panel">
          <h2>Passive</h2>
          <div className="compact-list">
            {Object.entries(sheet.passiveChecks).map(([name, value]) => (
              <span key={name}>
                {cleanName(name)} <strong>{value}</strong>
              </span>
            ))}
          </div>
        </section>

        <ConditionPanel canRoll={canRoll} sheet={sheet} onUpdateCondition={onUpdateCondition} onUpdateExhaustion={onUpdateExhaustion} />
        {sheet.ongoingEffects.length > 0 && (
          <section className="sheet-panel">
            <h2>Active Effects</h2>
            <div className="compact-list">
              {sheet.ongoingEffects.map((active) => {
                const manual = active.effect.endingConditions.some((ending) => ending.endingCondition === "manual");
                return <span key={`${active.id.resolutionSeed}:${active.id.effectNodeId.path.join(".")}`}>
                  {active.sourceLabel}
                  {manual && (
                    <button
                      disabled={!canRoll}
                      onClick={() => onRemoveOngoingEffect(sheet, active.id.resolutionSeed, active.id.effectNodeId.path)}
                    >
                      Remove
                    </button>
                  )}
                </span>;
              })}
            </div>
          </section>
        )}
        {(isDm || hasDamageDefenses(sheet)) && (
          <DamageDefensePanel isDm={isDm} sheet={sheet} onUpdateDamageDefense={onUpdateDamageDefense} />
        )}
      </div>

      <SheetAbilityList
        canRoll={canRoll}
        pendingRolls={pendingRolls}
        resolvedRolls={resolvedRolls}
        rollDraggable={rollDraggable}
        sheet={sheet}
        onDragRollEnd={onDragRollEnd}
        onDragRollStart={onDragRollStart}
        onRollResourceAction={onRollResourceAction}
        onUpdateResource={onUpdateResource}
      />

      <SheetSpellList
        canRoll={canRoll}
        pendingRolls={pendingRolls}
        resolvedRolls={resolvedRolls}
        rollDraggable={rollDraggable}
        sheet={sheet}
        onDragRollEnd={onDragRollEnd}
        onDragRollStart={onDragRollStart}
        onRollSpellAttack={onRollSpellAttack}
        onRollSpellDamage={onRollSpellDamage}
        onRollBoundWeaponSpell={onRollBoundWeaponSpell}
        onRollSpellHealing={onRollSpellHealing}
        onRollSpellTemporaryHitPoints={onRollSpellTemporaryHitPoints}
        onRollSpellEffect={onRollSpellEffect}
        onUpdateResource={onUpdateResource}
      />

      <section className="attack-list sheet-panel">
        <h2>Attacks</h2>
        {sheet.attacks.map((attack) => {
          const weaponOption = selectedWeaponOptions[attack.id] ?? attack.weaponAttackOptions?.[0]?.id;
          return <div className="attack-actions" key={attack.id}>
            <span>
              {attack.name} · {attack.abilityLabel} · {attack.damageDie} {attack.damageTypeLabel}
              {attack.activeSpellConditions?.map((spellId) => (
                <small className="attack-condition-pill" key={spellId}>{cleanName(spellId)}</small>
              ))}
            </span>
            {attack.weaponAttackOptions && attack.weaponAttackOptions.length > 1 && (
              <select
                disabled={!canRoll}
                value={weaponOption}
                onChange={(event) => setSelectedWeaponOptions((current) => ({
                  ...current,
                  [attack.id]: event.target.value,
                }))}
              >
                {attack.weaponAttackOptions.map((option) => (
                  <option key={option.id} value={option.id}>{option.label}</option>
                ))}
              </select>
            )}
            <button
              disabled={!canRoll || !attack.available}
              title={attack.unavailableReason}
              onClick={() => onRollAttack(sheet, attack.id, weaponOption)}
            >
              Attack
            </button>
            <InlineRolls
              pendingRolls={pendingRolls.filter((roll) => rollMatchesSource(roll, SheetSectionType.ATTACKS, attack.id))}
              roller={sheet}
              rollDraggable={rollDraggable}
              onDragRollEnd={onDragRollEnd}
              onDragRollStart={onDragRollStart}
            />
          </div>;
        })}
      </section>

      <section className="sheet-panel">
        <h2>Skills</h2>
        <div className="skill-grid">
          {sheet.skills.map((skill) => (
            <span key={skill.name} className={skill.proficiency !== "none" ? "proficient" : ""}>
              {cleanName(skill.name)} <strong>{formatSigned(skill.modifier)}</strong>
            </span>
          ))}
        </div>
      </section>

      {(sheet.features.length > 0 || sheet.proficiencies.length > 0 || sheet.equipment.length > 0 || hasPurseCoins(sheet)) && (
        <div className="sheet-columns">
          {sheet.features.length > 0 && (
            <section className="sheet-panel">
              <h2>Features</h2>
              <div className="feature-list">
                {sheet.features.map((feature) => (
                  <article key={feature.id}>
                    <strong>{feature.name}</strong>
                    <span>
                      {feature.source}
                      {feature.source ? " · " : ""}
                      {feature.activationLabel}
                    </span>
                    {feature.description && <p>{feature.description}</p>}
                    <RollActionList
                      canRoll={canRoll}
                      pendingRolls={pendingRolls.filter((roll) => rollMatchesSource(roll, SheetSectionType.FEATURES, feature.id))}
                      roller={sheet}
                      rollDraggable={rollDraggable}
                      rollActions={feature.rollActions ?? []}
                      onDragRollEnd={onDragRollEnd}
                      onDragRollStart={onDragRollStart}
                      onRollAction={() => undefined}
                    />
                  </article>
                ))}
              </div>
            </section>
          )}

          {sheet.proficiencies.length > 0 && (
            <section className="sheet-panel">
              <h2>Proficiencies</h2>
              <div className="tag-list">{sheet.proficiencies.map((proficiency) => <span key={proficiency}>{proficiency}</span>)}</div>
            </section>
          )}

          {hasPurseCoins(sheet) && (
            <section className="sheet-panel">
              <h2>Purse</h2>
              <div className="purse-list">
                <span>{sheet.purse.gold} GP</span>
                <span>{sheet.purse.silver} SP</span>
                <span>{sheet.purse.copper} CP</span>
              </div>
            </section>
          )}

          {sheet.equipment.length > 0 && (
            <section className="sheet-panel">
              <h2>Equipment</h2>
              <div className="equipment-list">
                {sheet.equipment.map((item) => (
                  <div className="equipment-row" key={item.id}>
                    <span>
                      <strong>{item.name}</strong>
                      {item.quantity > 1 ? ` x${item.quantity}` : ""}
                      <small>{item.itemTypeLabel} · {item.slotLabel}</small>
                    </span>
                    <select disabled={!canRoll} value={item.slot} onChange={(event) => onUpdateEquipmentSlot(sheet, item.id, event.target.value as EquipmentSlot)}>
                      {equipmentSlotOptions(item).map((slot) => (
                        <option key={slot} value={slot}>{cleanName(slot)}</option>
                      ))}
                    </select>
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>
      )}
    </section>
  );
}

function SheetSpellList({
  canRoll,
  onDragRollEnd,
  onDragRollStart,
  onRollSpellAttack,
  onRollSpellDamage,
  onRollBoundWeaponSpell,
  onRollSpellHealing,
  onRollSpellTemporaryHitPoints,
  onRollSpellEffect,
  onUpdateResource,
  pendingRolls,
  resolvedRolls = [],
  rollDraggable,
  sheet
}: {
  canRoll: boolean;
  onDragRollEnd: () => void;
  onDragRollStart: (rollId: string, preserveRoll: boolean) => void;
  onRollSpellAttack: (sheet: CharacterSheet, spellId: string, spellSlotLevel?: number) => void;
  onRollSpellDamage: (sheet: CharacterSheet, spellId: string, effectIndex: number, spellSlotLevel?: number, instanceIndex?: number, choiceIndex?: number) => void;
  onRollBoundWeaponSpell: (sheet: CharacterSheet, spellId: string, effectIndex: number, equipmentInstanceId: string, choiceIndex?: number) => void;
  onRollSpellHealing: (sheet: CharacterSheet, spellId: string, effectIndex: number, spellSlotLevel?: number) => void;
  onRollSpellTemporaryHitPoints: (sheet: CharacterSheet, spellId: string, effectIndex: number, spellSlotLevel?: number) => void;
  onRollSpellEffect: (sheet: CharacterSheet, spellId: string, effectIndex: number, spellSlotLevel?: number, choiceIndex?: number, equipmentInstanceId?: string) => void;
  onUpdateResource: (sheet: CharacterSheet, resourceId: string, currentUses: number) => void;
  pendingRolls: RollPayload[];
  resolvedRolls?: RollLogEntry[];
  rollDraggable: boolean;
  sheet: CharacterSheet;
}) {
  const [selectedSpellSlots, setSelectedSpellSlots] = useState<Record<string, number>>({});
  const [selectedSpellChoices, setSelectedSpellChoices] = useState<Record<string, number>>({});
  if (sheet.spells.length === 0 && sheet.spellbook.length === 0) return null;

  return (
    <section className="sheet-panel">
      <h2>Spells</h2>
      {sheet.spells.length > 0 && <div className="spell-list">
        {sheet.spells.map((spell) => {
          const resource = spell.resourceId ? sheet.resources.find((candidate) => candidate.resource === spell.resourceId) : undefined;
          const matchingRolls = pendingRolls.filter((roll) => rollMatchesSource(roll, SheetSectionType.SPELLS, spell.id));
          const matchingResolvedRolls = resolvedRolls.filter((entry) => rollMatchesSource(entry.roll, SheetSectionType.SPELLS, spell.id));
          const slotControlKey = `${spell.source}:${spell.id}`;
          const slotLevels = spell.controls.castOptions.map((option) => option.slotLevel);
          const cachedSlotLevel = selectedSpellSlots[slotControlKey];
          const selectedSlotLevel = cachedSlotLevel !== undefined && slotLevels.includes(cachedSlotLevel)
            ? cachedSlotLevel
            : slotLevels[0];
          const selectedCastOption = spell.controls.castOptions.find((option) => option.slotLevel === selectedSlotLevel);
          const actions = selectedCastOption?.actions ?? spell.controls.actions;
          const spellCanRoll = canRoll
            && (!spell.controls.requiresSpellSlot || selectedSlotLevel !== undefined)
            && (!resource || resource.currentUses > 0);
          const tags = [
            spell.sourceLabel,
            spell.level === 0 ? "Cantrip" : `Level ${spell.level}`,
            spell.schoolLabel,
            spell.castingAbilityLabel,
            spell.ritual ? "Ritual" : "",
            spell.concentration ? "Concentration" : ""
          ].filter(Boolean);

          return (
            <article className="spell-row" key={`${spell.source}:${spell.id}`}>
              <div>
                <strong>{spell.nameLabel}</strong>
                <span>{tags.join(" · ")}</span>
                <small>
                  {spell.castingTimeLabel} · {spell.targeting.summary} · {spell.duration.summary} · {spell.componentsLabel.join(", ")}
                  {spell.reset !== "none" ? ` · ${spell.resetLabel}` : ""}
                </small>
              </div>
              {resource && (
                <ResourceStepper
                  canRoll={canRoll}
                  currentUses={resource.currentUses}
                  maxUses={resource.maxUses}
                  onUpdate={(currentUses) => onUpdateResource(sheet, resource.id, currentUses)}
                />
              )}
              {spell.description && <p>{spell.description}</p>}
              {(actions.length > 0 || matchingRolls.length > 0 || matchingResolvedRolls.length > 0) && (
                <div className="inline-roll-area">
                  {actions.length > 0 && (
                    <div className="roll-action-buttons">
                      {slotLevels.length > 0 && (
                        <select
                          disabled={!canRoll}
                          value={selectedSlotLevel}
                          onChange={(event) => setSelectedSpellSlots((current) => ({ ...current, [slotControlKey]: Number(event.target.value) }))}
                        >
                          {slotLevels.map((slotLevel) => (
                            <option key={slotLevel} value={slotLevel}>L{slotLevel}</option>
                          ))}
                        </select>
                      )}
                      {actions.map((action, actionIndex) => {
                        const choiceKey = `${spell.source}:${spell.id}:${action.kind}:${action.effectIndex ?? actionIndex}`;
                        const selectedChoice = selectedSpellChoices[choiceKey] ?? action.choices[0]?.index ?? 0;
                        const choiceIndex = action.choices.length > 0 ? selectedChoice : undefined;
                        const effectIndex = action.effectIndex ?? 0;
                        return (
                          <span className="spell-roll-control" key={`${action.kind}-${effectIndex}-${action.attackId ?? actionIndex}-${action.damageType ?? ""}`}>
                            {action.choices.length > 0 && (
                              <select
                                disabled={!spellCanRoll}
                                value={selectedChoice}
                                onChange={(event) => setSelectedSpellChoices((current) => ({ ...current, [choiceKey]: Number(event.target.value) }))}
                              >
                                {action.choices.map((choice) => (
                                  <option key={choice.index} value={choice.index}>{choice.label}</option>
                                ))}
                              </select>
                            )}
                            {action.kind === "attack" && (
                              <button disabled={!spellCanRoll} onClick={() => onRollSpellAttack(sheet, spell.id, selectedSlotLevel)}>{action.label}</button>
                            )}
                            {action.kind === "damage" && Array.from({ length: action.instanceCount }, (_value, instanceIndex) => (
                              <button
                                disabled={!spellCanRoll}
                                key={instanceIndex}
                                onClick={() => onRollSpellDamage(sheet, spell.id, effectIndex, selectedSlotLevel, action.instanceCount > 1 ? instanceIndex : undefined, choiceIndex)}
                              >
                                {action.label}{action.instanceCount > 1 ? ` ${instanceIndex + 1}` : ""}
                              </button>
                            ))}
                            {action.kind === "healing" && (
                              <button disabled={!spellCanRoll} onClick={() => onRollSpellHealing(sheet, spell.id, effectIndex, selectedSlotLevel)}>{action.label}</button>
                            )}
                            {action.kind === "temporaryHitPoints" && (
                              <button disabled={!spellCanRoll} onClick={() => onRollSpellTemporaryHitPoints(sheet, spell.id, effectIndex, selectedSlotLevel)}>{action.label}</button>
                            )}
                            {action.kind === "effect" && (
                              <button disabled={!spellCanRoll} onClick={() => onRollSpellEffect(sheet, spell.id, effectIndex, selectedSlotLevel, choiceIndex)}>{action.label}</button>
                            )}
                            {action.kind === "boundWeaponAttack" && action.attackId && (
                              <button disabled={!spellCanRoll} onClick={() => onRollBoundWeaponSpell(sheet, spell.id, effectIndex, action.attackId!, choiceIndex)}>{action.label}</button>
                            )}
                            {action.kind === "boundWeaponEffect" && action.attackId && (
                              <button disabled={!spellCanRoll} onClick={() => onRollSpellEffect(sheet, spell.id, effectIndex, selectedSlotLevel, choiceIndex, action.attackId!)}>{action.label}</button>
                            )}
                          </span>
                        );
                      })}
                    </div>
                  )}
                  <InlineRolls
                    pendingRolls={matchingRolls}
                    resolvedRolls={matchingResolvedRolls}
                    roller={sheet}
                    rollDraggable={rollDraggable}
                    onDragRollEnd={onDragRollEnd}
                    onDragRollStart={onDragRollStart}
                  />
                </div>
              )}
            </article>
          );
        })}
      </div>}
      {sheet.spellbook.length > 0 && (
        <>
          <h3>Spellbook</h3>
          <div className="spell-list">
            {sheet.spellbook.map((spell) => {
              const tags = [
                spell.level === 0 ? "Cantrip" : `Level ${spell.level}`,
                spell.schoolLabel,
                spell.ritual ? "Ritual" : "",
                spell.concentration ? "Concentration" : ""
              ].filter(Boolean);

              return (
                <article className="spell-row" key={`spellbook:${spell.id}`}>
                  <div>
                    <strong>{spell.nameLabel}</strong>
                    <span>{tags.join(" · ")}</span>
                    <small>
                      {spell.castingTimeLabel} · {spell.targeting.summary} · {spell.duration.summary} · {spell.componentsLabel.join(", ")}
                    </small>
                  </div>
                </article>
              );
            })}
          </div>
        </>
      )}
    </section>
  );
}

function SheetStat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
