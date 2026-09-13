import { useEffect, useRef } from "react";

import { BoardView } from "./board/BoardView";
import { useBoardInteractions } from "./hooks/useBoardInteractions";
import { useRoomConnection } from "./hooks/useRoomConnection";
import { useSheetActions } from "./hooks/useSheetActions";
import { getDefaultWebSocketUrl, getInitialRoute } from "./routing";
import { SheetView } from "./sheet/SheetView";

const INITIAL_ROUTE = getInitialRoute();
const WS_URL = import.meta.env.VITE_WS_URL ?? getDefaultWebSocketUrl();

export function App() {
  const pendingTokenRadiiRef = useRef<Map<string, number>>(new Map());
  const view = INITIAL_ROUTE.view;
  const room = useRoomConnection({
    roomId: INITIAL_ROUTE.roomId,
    requestedPlayerKey: INITIAL_ROUTE.playerKey,
    view,
    webSocketUrl: WS_URL,
    pendingTokenRadiiRef
  });
  const isDm = room.playerKey === "dm";
  const sheetActions = useSheetActions({
    roomId: INITIAL_ROUTE.roomId,
    playerKey: room.playerKey,
    loadSheets: room.loadSheets,
    setSheets: room.setSheets,
    setRolls: room.setRolls,
    setResolutionPrompts: room.setResolutionPrompts,
    setRollHistory: room.setRollHistory,
    setSheetStatus: room.setSheetStatus
  });
  const boardInteractions = useBoardInteractions({
    roomId: INITIAL_ROUTE.roomId,
    playerKey: room.playerKey,
    isDm,
    assets: room.assets,
    board: room.board,
    fog: room.fog,
    tokens: room.tokens,
    send: room.send,
    setTokens: room.setTokens,
    pendingTokenRadiiRef
  });

  useEffect(() => {
    document.title = view === "sheet" ? "DnD Sheets" : "DnD Board";
  }, [view]);

  if (view === "sheet") {
    return (
      <SheetView
        connection={room.connection}
        expandedSheetId={room.expandedSheetId}
        isDm={isDm}
        onReloadSheets={room.loadSheets}
        onCreateCharacter={sheetActions.createCharacter}
        onExpand={room.setExpandedSheetId}
        onRollDamage={sheetActions.rollDamage}
        onRollAttack={sheetActions.rollAttack}
        onRollAbilityCheck={sheetActions.rollAbilityCheck}
        onRollResourceAction={sheetActions.rollResourceAction}
        onRollSavingThrow={sheetActions.rollSavingThrow}
        onRollSpellAttack={sheetActions.rollSpellAttack}
        onRollSpellDamage={sheetActions.rollSpellDamage}
        onRollBoundWeaponSpell={sheetActions.rollBoundWeaponSpell}
        onRollSpellHealing={sheetActions.rollSpellHealing}
        onRollSpellTemporaryHitPoints={sheetActions.rollSpellTemporaryHitPoints}
        onRollSpellEffect={sheetActions.rollSpellEffect}
        onRollAdHocDice={sheetActions.rollAdHocDice}
        onClearSheetRolls={sheetActions.clearSheetRolls}
        onRestSheets={sheetActions.restSheets}
        onUpdateProgressionChoice={sheetActions.updateProgressionChoice}
        onUpdateCondition={sheetActions.updateCondition}
        onRemoveOngoingEffect={sheetActions.removeOngoingEffect}
        onUpdateExhaustion={sheetActions.updateExhaustion}
        onUpdateDamageDefense={sheetActions.updateDamageDefense}
        onUpdateEquipmentSlot={sheetActions.updateEquipmentSlot}
        onUpdateSheetLevel={sheetActions.updateSheetLevel}
        onUpdateResource={sheetActions.updateResource}
        playerKey={room.playerKey}
        roomId={INITIAL_ROUTE.roomId}
        resolutionPrompts={room.resolutionPrompts}
        rollHistory={room.rollHistory}
        rolls={room.rolls}
        sheets={room.sheets}
        sheetStatus={room.sheetStatus}
        tokens={room.tokens}
        onRespondToResolutionPrompt={sheetActions.respondToResolutionPrompt}
      />
    );
  }

  return (
    <BoardView
      {...boardInteractions}
      assets={room.assets}
      board={room.board}
      boards={room.boards}
      connection={room.connection}
      fog={room.fog}
      isDm={isDm}
      playerCount={room.players.length}
      playerKey={room.playerKey}
      tokens={room.tokens}
      onLoadRoom={boardInteractions.loadRoom}
      onSaveRoom={boardInteractions.saveRoom}
      onResizeToken={boardInteractions.setTokenRadius}
    />
  );
}
