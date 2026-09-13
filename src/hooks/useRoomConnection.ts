import { useCallback, useEffect, useRef, useState } from "react";
import type { MutableRefObject } from "react";

import { DEFAULT_BOARD_HEIGHT, DEFAULT_BOARD_WIDTH, reconcilePendingTokenRadius } from "../board/boardRendering";
import { formatPlayerName, resolvePlayerKey } from "../routing";
import type { AppView, ConnectionState } from "../routing";
import type {
  Asset,
  Board,
  CharacterSheet,
  FogState,
  PlayerSummary,
  ResolutionInterceptorPrompt,
  RollLogEntry,
  RollPayload,
  ServerMessage,
  Token
} from "../types";

const SHEET_SYNC_INTERVAL_MS = 10000;
const ROOM_SYNC_INTERVAL_MS = 1500;
const ROLL_HISTORY_LIMIT = 10;
const DEFAULT_FOG: FogState = { hideMode: false, brushSize: 120, revealedAreas: [] };
const DEFAULT_BOARD: Board = { id: "", name: "", width: DEFAULT_BOARD_WIDTH, height: DEFAULT_BOARD_HEIGHT };

type RoomConnectionOptions = {
  roomId: string;
  requestedPlayerKey: string;
  view: AppView;
  webSocketUrl: string;
  pendingTokenRadiiRef: MutableRefObject<Map<string, number>>;
};

export function useRoomConnection({
  roomId,
  requestedPlayerKey,
  view,
  webSocketUrl,
  pendingTokenRadiiRef
}: RoomConnectionOptions) {
  const socketRef = useRef<WebSocket | null>(null);
  const sheetLoadInFlightRef = useRef(false);
  const [players, setPlayers] = useState<PlayerSummary[]>([]);
  const [tokens, setTokens] = useState<Token[]>([]);
  const [connection, setConnection] = useState<ConnectionState>("connecting");
  const [fog, setFog] = useState<FogState>(DEFAULT_FOG);
  const [board, setBoard] = useState<Board>(DEFAULT_BOARD);
  const [boards, setBoards] = useState<Board[]>([]);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [sheets, setSheets] = useState<CharacterSheet[]>([]);
  const [expandedSheetId, setExpandedSheetId] = useState<string | null>(null);
  const [rolls, setRolls] = useState<RollPayload[]>([]);
  const [resolutionPrompts, setResolutionPrompts] = useState<ResolutionInterceptorPrompt[]>([]);
  const [rollHistory, setRollHistory] = useState<RollLogEntry[]>([]);
  const [sheetStatus, setSheetStatus] = useState<"idle" | "loading" | "error">("idle");
  const [playerKey, setPlayerKey] = useState(requestedPlayerKey);

  const applyRoomState = useCallback((message: Extract<ServerMessage, { type: "room_state" }>) => {
    setPlayerKey(resolvePlayerKey(requestedPlayerKey, message.tokens));
    setPlayers(message.players);
    setTokens(message.tokens.map((token) => reconcilePendingTokenRadius(token, pendingTokenRadiiRef.current)));
    setFog(message.fog);
    setBoard(message.board);
    setBoards(message.boards);
    setAssets(message.assets);
  }, [pendingTokenRadiiRef, requestedPlayerKey]);

  useEffect(() => {
    const socket = new WebSocket(webSocketUrl);
    socketRef.current = socket;
    setConnection("connecting");

    socket.addEventListener("open", () => {
      socket.send(JSON.stringify({
        type: "join_room",
        roomId,
        playerName: formatPlayerName(requestedPlayerKey),
        playerKey: requestedPlayerKey
      }));
    });
    socket.addEventListener("close", () => setConnection("disconnected"));
    socket.addEventListener("message", (event) => {
      const message = JSON.parse(event.data.toString()) as ServerMessage;
      switch (message.type) {
        case "hello":
          return;
        case "room_state":
          setConnection("connected");
          applyRoomState(message);
          return;
        case "token_updated":
          setTokens((current) => upsertToken(current, reconcilePendingTokenRadius(message.token, pendingTokenRadiiRef.current)));
          return;
        case "token_deleted":
          setTokens((current) => current.filter((token) => token.id !== message.tokenId));
          return;
        case "fog_updated":
          setFog(message.fog);
          return;
        case "board_updated":
          setBoard(message.board);
          return;
        case "roll_created":
          setRolls((current) => upsertPendingRoll(current, message.roll));
          setRollHistory((current) => appendRollLogEntry(current, message.logEntry));
          return;
        case "roll_resolved":
          setRolls((current) => (message.resolution.responseRolls ?? []).reduce(
            upsertPendingRoll,
            message.preserveRoll ? current : current.filter((roll) => roll.id !== message.rollId)
          ));
          setRollHistory((current) => appendRollLogEntry(current, message.logEntry));
          setSheets((current) => applyResolvedRollToSheetState(current, message.resolution));
          return;
        case "resolution_prompt_created":
          setResolutionPrompts((current) => upsertResolutionPrompt(current, message.prompt));
          return;
        case "resolution_prompt_resolved":
          setResolutionPrompts((current) => current.filter((prompt) => prompt.id !== message.promptId));
          return;
        case "roll_blocked":
        case "roll_logged":
          setRollHistory((current) => appendRollLogEntry(current, message.logEntry));
          return;
        case "player_count":
          setPlayers((current) => current.slice(0, message.count));
      }
    });

    return () => socket.close();
  }, [applyRoomState, pendingTokenRadiiRef, requestedPlayerKey, roomId, webSocketUrl]);

  const send = useCallback((message: unknown) => {
    const socket = socketRef.current;
    if (socket?.readyState === WebSocket.OPEN) socket.send(JSON.stringify(message));
  }, []);

  const loadSheets = useCallback(async (showLoading = true) => {
    if (sheetLoadInFlightRef.current) return;
    sheetLoadInFlightRef.current = true;
    if (showLoading) setSheetStatus("loading");
    try {
      const response = await fetch(`/api/rooms/${encodeURIComponent(roomId)}/sheet?playerKey=${encodeURIComponent(playerKey)}`);
      if (!response.ok) throw new Error(await response.text());
      const body = (await response.json()) as SheetStateResponse;
      setSheets(body.sheets);
      setRolls(body.pendingRolls);
      setResolutionPrompts(body.pendingResolutionPrompts);
      setRollHistory(body.rollHistory);
      setExpandedSheetId((current) => current && body.sheets.some((sheet) => sheet.id === current) ? current : null);
      setSheetStatus("idle");
    } catch (error) {
      console.error(error);
      setSheetStatus("error");
    } finally {
      sheetLoadInFlightRef.current = false;
    }
  }, [playerKey, roomId]);

  useEffect(() => {
    if (view !== "sheet") return;
    void loadSheets();
    const intervalId = window.setInterval(() => void loadSheets(false), SHEET_SYNC_INTERVAL_MS);
    return () => window.clearInterval(intervalId);
  }, [loadSheets, view]);

  useEffect(() => {
    let cancelled = false;
    const syncRoomState = async () => {
      try {
        const response = await fetch(`/api/rooms/${encodeURIComponent(roomId)}/state`);
        if (!response.ok || cancelled) return;
        applyRoomState((await response.json()) as Extract<ServerMessage, { type: "room_state" }>);
      } catch (error) {
        if (!cancelled) console.error(error);
      }
    };

    if (view === "sheet") {
      void syncRoomState();
      return () => { cancelled = true; };
    }
    const intervalId = window.setInterval(syncRoomState, ROOM_SYNC_INTERVAL_MS);
    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, [applyRoomState, roomId, view]);

  return {
    assets,
    board,
    boards,
    connection,
    expandedSheetId,
    fog,
    loadSheets,
    playerKey,
    players,
    resolutionPrompts,
    rollHistory,
    rolls,
    send,
    setExpandedSheetId,
    setFog,
    setResolutionPrompts,
    setRollHistory,
    setRolls,
    setSheets,
    setSheetStatus,
    setTokens,
    sheetStatus,
    sheets,
    tokens
  };
}

export type SheetStateResponse = {
  sheets: CharacterSheet[];
  pendingRolls: RollPayload[];
  pendingResolutionPrompts: ResolutionInterceptorPrompt[];
  rollHistory: RollLogEntry[];
};

export function upsertPendingRoll(rolls: RollPayload[], roll: RollPayload) {
  return [roll, ...rolls.filter((candidate) => rollKey(candidate) !== rollKey(roll))];
}

export function appendRollLogEntry(entries: RollLogEntry[], entry: RollLogEntry) {
  return [...entries.filter((candidate) => candidate.id !== entry.id), entry].slice(-ROLL_HISTORY_LIMIT);
}

export function upsertResolutionPrompt(prompts: ResolutionInterceptorPrompt[], prompt: ResolutionInterceptorPrompt) {
  return [prompt, ...prompts.filter((candidate) => candidate.id !== prompt.id)];
}

export function applyResolvedRollToSheetState(sheets: CharacterSheet[], resolution: NonNullable<RollLogEntry["resolution"]>) {
  const concentrationUpdates = new Map((resolution.concentrationUpdates ?? []).map((update) => [update.sheetId, update.activeConcentration]));
  const sheetUpdates = new Map((resolution.sheetUpdates ?? []).map((update) => [update.sheetId, update]));
  return sheets.map((sheet) => {
    const update = sheetUpdates.get(sheet.id);
    const targetUpdate = sheet.id === resolution.targetSheetId
      ? { hp: resolution.targetHp, conditions: resolution.targetConditions }
      : {};
    return {
      ...sheet,
      ...targetUpdate,
      ...(update?.hp ? { hp: update.hp } : {}),
      ...(update?.conditions ? { conditions: update.conditions } : {}),
      ...(update?.damageResistances ? { damageResistances: update.damageResistances } : {}),
      ...(update?.damageVulnerabilities ? { damageVulnerabilities: update.damageVulnerabilities } : {}),
      ...(update?.damageImmunities ? { damageImmunities: update.damageImmunities } : {}),
      ...(concentrationUpdates.has(sheet.id) ? { activeConcentration: concentrationUpdates.get(sheet.id) } : {})
    };
  });
}

function upsertToken(tokens: Token[], token: Token) {
  const index = tokens.findIndex((candidate) => candidate.id === token.id);
  if (index === -1) return [...tokens, token];
  const next = [...tokens];
  next[index] = token;
  return next;
}

function rollKey(roll: RollPayload) {
  return `${roll.tokenId}:${roll.source.section}:${roll.source.sourceId}:${roll.source.actionId}`;
}
