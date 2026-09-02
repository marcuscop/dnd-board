import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { CSSProperties, MutableRefObject } from "react";
import { RollResolutionMode, SheetSectionType, TokenKind } from "./types";
import type { AbilityScores, AbilityType, Asset, Board, CharacterBuilderDraft, CharacterBuilderOptions, CharacterSheet, ConditionType, EquipmentSlot, FogState, PlayerSummary, ProgressionChoice, RollAction, RollLogEntry, RollPayload, ServerMessage, Token } from "./types";

const DEFAULT_BOARD_WIDTH = 1200;
const DEFAULT_BOARD_HEIGHT = 720;
const MOVE_FPS = 12;
const FOG_PAINT_FPS = 16;
const FOG_MIN_POINT_DISTANCE = 8;
const MIN_TOKEN_RADIUS = 8;
const MAX_TOKEN_RADIUS = 480;
const WS_URL = import.meta.env.VITE_WS_URL ?? getDefaultWebSocketUrl();
const INITIAL_ROUTE = getInitialRoute();
const REQUESTED_PLAYER_KEY = INITIAL_ROUTE.playerKey;
const DEFAULT_FOG: FogState = { hideMode: false, brushSize: 120, revealedAreas: [] };
const DEFAULT_BOARD: Board = { id: "", name: "", width: DEFAULT_BOARD_WIDTH, height: DEFAULT_BOARD_HEIGHT };
const ROLL_HISTORY_LIMIT = 10;
const SAME_ABILITY_VALUE = "__same__";
const ABILITY_SCORE_METHOD_STANDARD_ARRAY = "standardArray";
const ABILITY_SCORE_METHOD_POINT_BUY = "pointBuy";
const ABILITY_SCORE_METHOD_RANDOM = "random";
const ABILITY_SCORE_OPTIONS: { value: AbilityType; label: string }[] = [
  { value: "strength", label: "Strength" },
  { value: "dexterity", label: "Dexterity" },
  { value: "constitution", label: "Constitution" },
  { value: "intelligence", label: "Intelligence" },
  { value: "wisdom", label: "Wisdom" },
  { value: "charisma", label: "Charisma" }
];
const CONDITION_OPTIONS: ConditionType[] = [
  "blinded",
  "charmed",
  "deafened",
  "exhaustion",
  "frightened",
  "grappled",
  "incapacitated",
  "invisible",
  "paralyzed",
  "petrified",
  "poisoned",
  "prone",
  "restrained",
  "stunned",
  "unconscious"
];

type ConnectionState = "connecting" | "connected" | "disconnected";
type AppView = "board" | "sheet";
type InitialRoute = {
  roomId: string;
  playerKey: string;
  view: AppView;
};
type DragPreview = {
  tokenId: string;
  x: number;
  y: number;
  overBoard: boolean;
};
type BrushPreview = {
  x: number;
  y: number;
};
type BoardSize = {
  width: number;
  height: number;
};
type DragGhost = {
  tokenId: string;
  clientX: number;
  clientY: number;
};
type FogMaskCache = {
  canvas: HTMLCanvasElement;
  renderedCount: number;
  signature: string;
};

export function App() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const socketRef = useRef<WebSocket | null>(null);
  const imagesRef = useRef<Map<string, HTMLImageElement>>(new Map());
  const boardImagesRef = useRef<Map<string, HTMLImageElement>>(new Map());
  const fogMaskRef = useRef<FogMaskCache | null>(null);
  const canvasHoverRef = useRef<BrushPreview | null>(null);
  const dragRef = useRef<{ tokenId: string; lastSentAt: number } | null>(null);
  const fogPaintRef = useRef<{ lastSentAt: number; lastX: number; lastY: number; radius: number } | null>(null);
  const pendingTokenRadiiRef = useRef<Map<string, number>>(new Map());
  const pendingResizeRequestsRef = useRef<Set<Promise<void>>>(new Set());
  const [players, setPlayers] = useState<PlayerSummary[]>([]);
  const [tokens, setTokens] = useState<Token[]>([]);
  const [connection, setConnection] = useState<ConnectionState>("connecting");
  const [dragPreview, setDragPreview] = useState<DragPreview | null>(null);
  const [saveStatus, setSaveStatus] = useState<"idle" | "saving" | "saved" | "error">("idle");
  const [loadStatus, setLoadStatus] = useState<"idle" | "loading" | "loaded" | "error">("idle");
  const [fog, setFog] = useState<FogState>(DEFAULT_FOG);
  const [board, setBoard] = useState<Board>(DEFAULT_BOARD);
  const [boards, setBoards] = useState<Board[]>([]);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [sheets, setSheets] = useState<CharacterSheet[]>([]);
  const [expandedSheetId, setExpandedSheetId] = useState<string | null>(null);
  const [rolls, setRolls] = useState<RollPayload[]>([]);
  const [rollHistory, setRollHistory] = useState<RollLogEntry[]>([]);
  const [sheetStatus, setSheetStatus] = useState<"idle" | "loading" | "error">("idle");
  const [selectedAssetKey, setSelectedAssetKey] = useState("");
  const [assetSearch, setAssetSearch] = useState("");
  const [isPaintingFog, setIsPaintingFog] = useState(false);
  const [revealToolEnabled, setRevealToolEnabled] = useState(false);
  const [brushPreview, setBrushPreview] = useState<BrushPreview | null>(null);
  const [dragGhost, setDragGhost] = useState<DragGhost | null>(null);
  const [playerKey, setPlayerKey] = useState(REQUESTED_PLAYER_KEY);
  const [view, setView] = useState<AppView>(INITIAL_ROUTE.view);
  const isDm = playerKey === "dm";

  useEffect(() => {
    document.title = view === "sheet" ? "DnD Sheets" : "DnD Board";
  }, [view]);

  const ownLockedTokenId = useMemo(
    () => tokens.find((token) => token.lockedBy === playerKey)?.id,
    [playerKey, tokens]
  );
  const boardSize = useMemo(() => getBoardSize(board), [board]);
  const maxTokenRadius = useMemo(() => getMaxTokenRadius(boardSize), [boardSize]);
  const boardCanvasStyle = useMemo(
    () =>
      ({
        "--board-aspect-ratio": String(boardSize.width / boardSize.height),
        aspectRatio: `${boardSize.width} / ${boardSize.height}`
      }) as CSSProperties,
    [boardSize]
  );
  const partyTokens = useMemo(() => tokens.filter((token) => token.kind === TokenKind.CHARACTER), [tokens]);
  const otherTokens = useMemo(() => tokens.filter((token) => token.kind !== TokenKind.CHARACTER), [tokens]);
  const filteredAssets = useMemo(() => filterAssets(assets, assetSearch), [assets, assetSearch]);
  const visibleSelectedAssetKey = filteredAssets.some((asset) => assetKey(asset) === selectedAssetKey) ? selectedAssetKey : assetKey(filteredAssets[0]);

  const applyRoomState = useCallback((message: Extract<ServerMessage, { type: "room_state" }>) => {
    const resolvedPlayerKey = resolvePlayerKey(REQUESTED_PLAYER_KEY, message.tokens);
    setPlayerKey(resolvedPlayerKey);
    setPlayers(message.players);
    setTokens(message.tokens.map((token) => reconcilePendingTokenRadius(token, pendingTokenRadiiRef.current)));
    setFog(message.fog);
    setBoard(message.board);
    setBoards(message.boards);
    setAssets(message.assets);
    setSelectedAssetKey((current) => current || assetKey(message.assets[0]));
  }, []);

  useEffect(() => {
    const socket = new WebSocket(WS_URL);
    socketRef.current = socket;
    setConnection("connecting");

    socket.addEventListener("open", () => {
      socket.send(
        JSON.stringify({
          type: "join_room",
          roomId: getInitialRoomId(),
          playerName: formatPlayerName(REQUESTED_PLAYER_KEY),
          playerKey: REQUESTED_PLAYER_KEY
        })
      );
    });

    socket.addEventListener("close", () => {
      setConnection("disconnected");
    });

    socket.addEventListener("message", (event) => {
      const message = JSON.parse(event.data.toString()) as ServerMessage;
      if (message.type === "hello") {
        return;
      }

      if (message.type === "room_state") {
        setConnection("connected");
        applyRoomState(message);
        return;
      }

      if (message.type === "token_updated") {
        setTokens((current) => upsertToken(current, reconcilePendingTokenRadius(message.token, pendingTokenRadiiRef.current)));
        return;
      }

      if (message.type === "token_deleted") {
        setTokens((current) => current.filter((token) => token.id !== message.tokenId));
        return;
      }

      if (message.type === "fog_updated") {
        setFog(message.fog);
        if (!message.fog.hideMode) {
          setRevealToolEnabled(false);
          setBrushPreview(null);
        }
        return;
      }

      if (message.type === "board_updated") {
        setBoard(message.board);
        return;
      }

      if (message.type === "roll_created") {
        setRolls((current) => upsertPendingRoll(current, message.roll));
        setRollHistory((current) => appendRollLogEntry(current, message.logEntry));
        return;
      }

      if (message.type === "roll_resolved") {
        setRolls((current) => (message.resolution.responseRolls ?? []).reduce(upsertPendingRoll, current.filter((roll) => roll.id !== message.rollId)));
        setRollHistory((current) => appendRollLogEntry(current, message.logEntry));
        setSheets((current) => applyResolvedRollToSheetState(current, message.resolution));
        return;
      }

      if (message.type === "player_count") {
        setPlayers((current) => current.slice(0, message.count));
      }
    });

    return () => socket.close();
  }, [applyRoomState]);

  const loadSheets = useCallback(async () => {
    setSheetStatus("loading");
    try {
      const response = await fetch(`/api/rooms/${encodeURIComponent(getInitialRoomId())}/sheet?playerKey=${encodeURIComponent(playerKey)}`);
      if (!response.ok) {
        throw new Error(await response.text());
      }
      const body = (await response.json()) as { sheets: CharacterSheet[]; pendingRolls: RollPayload[]; rollHistory: RollLogEntry[] };
      setSheets(body.sheets);
      setRolls(body.pendingRolls);
      setRollHistory(body.rollHistory);
      setExpandedSheetId((current) => current && body.sheets.some((sheet) => sheet.id === current) ? current : null);
      setSheetStatus("idle");
    } catch (error) {
      console.error(error);
      setSheetStatus("error");
    }
  }, [playerKey]);

  useEffect(() => {
    if (view !== "sheet") return;
    void loadSheets();
    const intervalId = window.setInterval(() => void loadSheets(), 1500);
    return () => window.clearInterval(intervalId);
  }, [loadSheets, view]);

  useEffect(() => {
    let cancelled = false;
    const roomId = getInitialRoomId();

    const syncRoomState = async () => {
      try {
        const response = await fetch(`/api/rooms/${encodeURIComponent(roomId)}/state`);
        if (!response.ok || cancelled) return;
        applyRoomState((await response.json()) as Extract<ServerMessage, { type: "room_state" }>);
      } catch (error) {
        if (!cancelled) {
          console.error(error);
        }
      }
    };

    if (view === "sheet") {
      void syncRoomState();
      return () => {
        cancelled = true;
      };
    }

    const intervalId = window.setInterval(syncRoomState, 1500);
    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, [applyRoomState, view]);

  useEffect(() => {
    drawBoard(
      canvasRef.current,
      tokens,
      playerKey,
      isDm,
      dragPreview,
      imagesRef.current,
      fog,
      revealToolEnabled ? brushPreview : null,
      board,
      boardImagesRef.current,
      fogMaskRef,
      boardSize
    );
  }, [tokens, playerKey, isDm, dragPreview, fog, brushPreview, revealToolEnabled, board, boardSize]);

  useEffect(() => {
    for (const token of tokens) {
      if (!token.avatarUrl || imagesRef.current.has(token.avatarUrl)) continue;

      const image = new Image();
      image.onload = () =>
        drawBoard(
          canvasRef.current,
          tokens,
          playerKey,
          isDm,
          dragPreview,
          imagesRef.current,
          fog,
          revealToolEnabled ? brushPreview : null,
          board,
          boardImagesRef.current,
          fogMaskRef,
          boardSize
        );
      image.src = token.avatarUrl;
      imagesRef.current.set(token.avatarUrl, image);
    }
  }, [board, boardSize, brushPreview, dragPreview, fog, isDm, playerKey, revealToolEnabled, tokens]);

  useEffect(() => {
    if (!board.url || boardImagesRef.current.has(board.url)) return;

    const image = new Image();
    image.onload = () =>
      drawBoard(
        canvasRef.current,
        tokens,
        playerKey,
        isDm,
        dragPreview,
        imagesRef.current,
        fog,
        revealToolEnabled ? brushPreview : null,
        board,
        boardImagesRef.current,
        fogMaskRef,
        boardSize
      );
    image.src = board.url;
    boardImagesRef.current.set(board.url, image);
  }, [board, boardSize, brushPreview, dragPreview, fog, isDm, playerKey, revealToolEnabled, tokens]);

  const send = useCallback((message: unknown) => {
    const socket = socketRef.current;
    if (socket?.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify(message));
    }
  }, []);

  const sendRevealPoint = useCallback(
    (point: BrushPreview, force = false) => {
      const now = performance.now();
      const last = fogPaintRef.current;
      const minDistance = Math.max(FOG_MIN_POINT_DISTANCE, fog.brushSize * 0.22);
      const farEnough = !last || Math.hypot(point.x - last.lastX, point.y - last.lastY) >= minDistance || last.radius !== fog.brushSize;
      const lateEnough = !last || now - last.lastSentAt >= 1000 / FOG_PAINT_FPS;

      if (!force && (!farEnough || !lateEnough)) return;

      fogPaintRef.current = { lastSentAt: now, lastX: point.x, lastY: point.y, radius: fog.brushSize };
      send({ type: "reveal_fog", x: point.x, y: point.y, radius: fog.brushSize });
    },
    [fog.brushSize, send]
  );

  const handlePointerDown = useCallback(
    (event: React.PointerEvent<HTMLCanvasElement>) => {
      const point = canvasPoint(event, boardSize);
      if (isDm && fog.hideMode && revealToolEnabled) {
        event.currentTarget.setPointerCapture(event.pointerId);
        setBrushPreview(point);
        setIsPaintingFog(true);
        fogPaintRef.current = null;
        sendRevealPoint(point, true);
        return;
      }

      const token = [...tokens].reverse().find((candidate) => candidate.inScene && hitToken(candidate, point.x, point.y));
      if (!token || !canControlToken(token, playerKey, isDm) || (token.lockedBy && token.lockedBy !== playerKey)) return;

      event.currentTarget.setPointerCapture(event.pointerId);
      dragRef.current = { tokenId: token.id, lastSentAt: 0 };
      setDragPreview({ tokenId: token.id, x: point.x, y: point.y, overBoard: true });
      send(requestTokenLockMessage(token.id, tokens, pendingTokenRadiiRef.current, isDm));
    },
    [boardSize, fog.hideMode, isDm, playerKey, revealToolEnabled, send, sendRevealPoint, tokens]
  );

  const handlePointerMove = useCallback(
    (event: React.PointerEvent<HTMLCanvasElement>) => {
      const drag = dragRef.current;
      const point = canvasPoint(event, boardSize);
      const overBoard = isPointInsideCanvas(event);
      canvasHoverRef.current = overBoard ? point : null;
      if (isDm && fog.hideMode && revealToolEnabled && overBoard) {
        setBrushPreview(point);
      }

      if (isDm && isPaintingFog) {
        if (overBoard) {
          sendRevealPoint(point);
        }
        return;
      }

      if (!drag) return;

      const now = performance.now();
      if (now - drag.lastSentAt < 1000 / MOVE_FPS) return;

      drag.lastSentAt = now;
      setDragPreview({ tokenId: drag.tokenId, x: point.x, y: point.y, overBoard });
      if (!overBoard) return;
      send(moveTokenMessage(drag.tokenId, point.x, point.y, tokens, pendingTokenRadiiRef.current, isDm));
    },
    [boardSize, fog.hideMode, isDm, isPaintingFog, revealToolEnabled, send, sendRevealPoint, tokens]
  );

  const finishDrag = useCallback(
    (event: React.PointerEvent<HTMLCanvasElement>) => {
      const drag = dragRef.current;
      if (isDm && isPaintingFog) {
        if (isPointInsideCanvas(event)) {
          sendRevealPoint(canvasPoint(event, boardSize), true);
        }
        fogPaintRef.current = null;
        setIsPaintingFog(false);
        return;
      }

      if (!drag) return;

      if (isPointInsideCanvas(event)) {
        const point = canvasPoint(event, boardSize);
        send(moveTokenMessage(drag.tokenId, point.x, point.y, tokens, pendingTokenRadiiRef.current, isDm));
        send(setTokenSceneMessage(drag.tokenId, true, point.x, point.y, tokens, pendingTokenRadiiRef.current, isDm));
      } else {
        send({ type: "set_token_scene", tokenId: drag.tokenId, inScene: false });
      }
      send({ type: "release_token", tokenId: drag.tokenId });
      dragRef.current = null;
      setDragPreview(null);
      setDragGhost(null);
    },
    [boardSize, isDm, isPaintingFog, send, sendRevealPoint, tokens]
  );

  const handleSidebarPointerDown = useCallback(
    (event: React.PointerEvent<HTMLElement>, token: Token) => {
      event.preventDefault();
      clearTextSelection();
      if (!canControlToken(token, playerKey, isDm) || (token.lockedBy && token.lockedBy !== playerKey)) return;

      event.currentTarget.setPointerCapture(event.pointerId);
      dragRef.current = { tokenId: token.id, lastSentAt: 0 };
      setDragGhost({ tokenId: token.id, clientX: event.clientX, clientY: event.clientY });
      setDragPreview({ tokenId: token.id, x: token.x, y: token.y, overBoard: false });
      send(requestTokenLockMessage(token.id, tokens, pendingTokenRadiiRef.current, isDm));
    },
    [isDm, playerKey, send, tokens]
  );

  const handleSidebarPointerMove = useCallback(
    (event: React.PointerEvent<HTMLElement>) => {
      event.preventDefault();
      clearTextSelection();
      const drag = dragRef.current;
      const canvas = canvasRef.current;
      if (!drag || !canvas) return;
      setDragGhost({ tokenId: drag.tokenId, clientX: event.clientX, clientY: event.clientY });

      const now = performance.now();
      if (now - drag.lastSentAt < 1000 / MOVE_FPS) return;
      drag.lastSentAt = now;

      if (!isClientPointInsideCanvas(canvas, event.clientX, event.clientY)) {
        setDragPreview((current) => (current ? { ...current, overBoard: false } : current));
        return;
      }
      const point = clientPointToCanvas(canvas, event.clientX, event.clientY, boardSize);
      setDragPreview({ tokenId: drag.tokenId, x: point.x, y: point.y, overBoard: true });
      send(moveTokenMessage(drag.tokenId, point.x, point.y, tokens, pendingTokenRadiiRef.current, isDm));
    },
    [boardSize, isDm, send, tokens]
  );

  const handleSidebarPointerUp = useCallback(
    (event: React.PointerEvent<HTMLElement>) => {
      event.preventDefault();
      clearTextSelection();
      const drag = dragRef.current;
      const canvas = canvasRef.current;
      if (!drag || !canvas) return;

      if (isClientPointInsideCanvas(canvas, event.clientX, event.clientY)) {
        const point = clientPointToCanvas(canvas, event.clientX, event.clientY, boardSize);
        send(setTokenSceneMessage(drag.tokenId, true, point.x, point.y, tokens, pendingTokenRadiiRef.current, isDm));
      }
      send({ type: "release_token", tokenId: drag.tokenId });
      dragRef.current = null;
      setDragPreview(null);
      setDragGhost(null);
    },
    [boardSize, isDm, send, tokens]
  );

  const waitForPendingResizes = useCallback(async () => {
    while (pendingResizeRequestsRef.current.size > 0) {
      await Promise.all([...pendingResizeRequestsRef.current]);
    }
  }, []);

  const saveRoom = useCallback(async () => {
    setSaveStatus("saving");
    await waitForPendingResizes();
    const roomId = getInitialRoomId();
    const response = await fetch(`/api/rooms/${encodeURIComponent(roomId)}/save?playerKey=${encodeURIComponent(playerKey)}`, {
      method: "POST"
    });

    setSaveStatus(response.ok ? "saved" : "error");
    window.setTimeout(() => setSaveStatus("idle"), 1800);
  }, [playerKey, waitForPendingResizes]);

  const loadRoom = useCallback(async () => {
    setLoadStatus("loading");
    const roomId = getInitialRoomId();
    const response = await fetch(`/api/rooms/${encodeURIComponent(roomId)}/load?playerKey=${encodeURIComponent(playerKey)}`, {
      method: "POST"
    });

    setLoadStatus(response.ok ? "loaded" : "error");
    window.setTimeout(() => setLoadStatus("idle"), 1800);
  }, [playerKey]);

  const setHideMode = useCallback(
    (hideMode: boolean) => {
      send({ type: "set_fog_mode", hideMode, brushSize: fog.brushSize });
      if (!hideMode) {
        setRevealToolEnabled(false);
        setBrushPreview(null);
      }
    },
    [fog.brushSize, send]
  );

  const setBrushSize = useCallback(
    (brushSize: number) => {
      send({ type: "set_fog_mode", hideMode: fog.hideMode, brushSize });
    },
    [fog.hideMode, send]
  );

  const setActiveBoard = useCallback(
    (boardId: string) => {
      send({ type: "set_board", boardId });
    },
    [send]
  );

  const loadSelectedAsset = useCallback(() => {
    const asset = assets.find((candidate) => assetKey(candidate) === visibleSelectedAssetKey);
    if (!asset) return;
    send({ type: "load_asset", assetKind: asset.kind, assetId: asset.id });
  }, [assets, visibleSelectedAssetKey, send]);

  useEffect(() => {
    if (visibleSelectedAssetKey && visibleSelectedAssetKey !== selectedAssetKey) {
      setSelectedAssetKey(visibleSelectedAssetKey);
    }
  }, [selectedAssetKey, visibleSelectedAssetKey]);

  const deleteToken = useCallback(
    (token: Token) => {
      if (!isDm || token.kind === TokenKind.CHARACTER) return;
      send({ type: "delete_token", tokenId: token.id });
    },
    [isDm, send]
  );

  const clearScene = useCallback(() => {
    if (!isDm) return;
    dragRef.current = null;
    setDragPreview(null);
    setDragGhost(null);
    setTokens((current) => current.map((token) => ({ ...token, inScene: false, lockedBy: undefined })));
    send({ type: "clear_scene" });
  }, [isDm, send]);

  const setTokenRadius = useCallback(
    (token: Token, radius: number) => {
      if (!isDm) return;
      const nextRadius = clamp(radius, MIN_TOKEN_RADIUS, maxTokenRadius);
      pendingTokenRadiiRef.current.set(token.id, nextRadius);
      setTokens((current) => current.map((candidate) => (candidate.id === token.id ? { ...candidate, radius: nextRadius } : candidate)));
      const request = updateTokenRadius(token.id, nextRadius, playerKey)
        .catch((error: unknown) => {
          console.error(error);
        })
        .finally(() => {
          pendingResizeRequestsRef.current.delete(request);
        });
      pendingResizeRequestsRef.current.add(request);
    },
    [isDm, maxTokenRadius, playerKey]
  );

  const rollAttack = useCallback(
    async (sheet: CharacterSheet, attackId: string) => {
      const response = await fetch(
        `/api/rooms/${encodeURIComponent(getInitialRoomId())}/sheet/${encodeURIComponent(sheet.id)}/rolls/attack?playerKey=${encodeURIComponent(playerKey)}&attackId=${encodeURIComponent(attackId)}`,
        { method: "POST" }
      );
      if (!response.ok) {
        setSheetStatus("error");
      }
    },
    [playerKey]
  );

  const rollDamage = useCallback(
    async (sheet: CharacterSheet, attackId: string) => {
      const response = await fetch(
        `/api/rooms/${encodeURIComponent(getInitialRoomId())}/sheet/${encodeURIComponent(sheet.id)}/rolls/damage?playerKey=${encodeURIComponent(playerKey)}&attackId=${encodeURIComponent(attackId)}`,
        { method: "POST" }
      );
      if (!response.ok) {
        setSheetStatus("error");
      }
    },
    [playerKey]
  );

  const rollAbilityCheck = useCallback(
    async (sheet: CharacterSheet, ability: string) => {
      const response = await fetch(
        `/api/rooms/${encodeURIComponent(getInitialRoomId())}/sheet/${encodeURIComponent(sheet.id)}/rolls/ability-check?playerKey=${encodeURIComponent(playerKey)}&ability=${encodeURIComponent(ability)}`,
        { method: "POST" }
      );
      if (!response.ok) {
        setSheetStatus("error");
      }
    },
    [playerKey]
  );

  const rollSavingThrow = useCallback(
    async (sheet: CharacterSheet, ability: string) => {
      const response = await fetch(
        `/api/rooms/${encodeURIComponent(getInitialRoomId())}/sheet/${encodeURIComponent(sheet.id)}/rolls/saving-throw?playerKey=${encodeURIComponent(playerKey)}&ability=${encodeURIComponent(ability)}`,
        { method: "POST" }
      );
      if (!response.ok) {
        setSheetStatus("error");
      }
    },
    [playerKey]
  );

  const rollResourceAction = useCallback(
    async (sheet: CharacterSheet, abilityId: string, actionId: string) => {
      const response = await fetch(
        `/api/rooms/${encodeURIComponent(getInitialRoomId())}/sheet/${encodeURIComponent(sheet.id)}/abilities/${encodeURIComponent(abilityId)}/rolls/${encodeURIComponent(actionId)}?playerKey=${encodeURIComponent(playerKey)}`,
        { method: "POST" }
      );
      if (!response.ok) {
        setSheetStatus("error");
        return;
      }
      const body = (await response.json()) as { roll: RollPayload; resolution?: RollLogEntry["resolution"]; logEntry?: RollLogEntry };
      if (body.resolution && body.logEntry) {
        const resolution = body.resolution;
        const logEntry = body.logEntry;
        setSheets((current) => applyResolvedRollToSheetState(current, resolution));
        setRolls((current) => current.filter((roll) => roll.id !== body.roll.id));
        setRollHistory((current) => appendRollLogEntry(current, logEntry));
        return;
      }
      await loadSheets();
    },
    [loadSheets, playerKey]
  );

  const updateResource = useCallback(
    async (sheet: CharacterSheet, resourceId: string, currentUses: number) => {
      const response = await fetch(
        `/api/rooms/${encodeURIComponent(getInitialRoomId())}/sheet/${encodeURIComponent(sheet.id)}/resources/${encodeURIComponent(resourceId)}?playerKey=${encodeURIComponent(playerKey)}&currentUses=${encodeURIComponent(currentUses)}`,
        { method: "POST" }
      );
      if (!response.ok) {
        setSheetStatus("error");
        return;
      }
      const body = (await response.json()) as { sheet: CharacterSheet };
      setSheets((current) => current.map((candidate) => (candidate.id === body.sheet.id ? body.sheet : candidate)));
    },
    [playerKey]
  );

  const restSheets = useCallback(
    async (rest: "short" | "long") => {
      const response = await fetch(
        `/api/rooms/${encodeURIComponent(getInitialRoomId())}/sheet/rest?playerKey=${encodeURIComponent(playerKey)}&rest=${encodeURIComponent(rest)}`,
        { method: "POST" }
      );
      if (!response.ok) {
        setSheetStatus("error");
        return;
      }
      const body = (await response.json()) as { sheets: CharacterSheet[]; pendingRolls: RollPayload[]; rollHistory: RollLogEntry[] };
      setSheets(body.sheets);
      setRolls(body.pendingRolls);
      setRollHistory(body.rollHistory);
    },
    [playerKey]
  );

  const clearSheetRolls = useCallback(
    async (sheet: CharacterSheet) => {
      const response = await fetch(
        `/api/rooms/${encodeURIComponent(getInitialRoomId())}/sheet/${encodeURIComponent(sheet.id)}/rolls/clear?playerKey=${encodeURIComponent(playerKey)}`,
        { method: "POST" }
      );
      if (!response.ok) {
        setSheetStatus("error");
        return;
      }
      const body = (await response.json()) as { sheets: CharacterSheet[]; pendingRolls: RollPayload[]; rollHistory: RollLogEntry[] };
      setSheets(body.sheets);
      setRolls(body.pendingRolls);
      setRollHistory(body.rollHistory);
    },
    [playerKey]
  );

  const updateSheetLevel = useCallback(
    async (sheet: CharacterSheet, delta: 1 | -1) => {
      const response = await fetch(
        `/api/rooms/${encodeURIComponent(getInitialRoomId())}/sheet/${encodeURIComponent(sheet.id)}/level?playerKey=${encodeURIComponent(playerKey)}&delta=${encodeURIComponent(delta)}&className=${encodeURIComponent(sheet.characterClass.name)}`,
        { method: "POST" }
      );
      if (!response.ok) {
        setSheetStatus("error");
        return;
      }
      const body = (await response.json()) as { sheet: CharacterSheet };
      if (body.sheet) {
        setSheets((current) => current.map((candidate) => (candidate.id === body.sheet.id ? body.sheet : candidate)));
      }
    },
    [playerKey]
  );

  const updateProgressionChoice = useCallback(
    async (sheet: CharacterSheet, choiceId: string, values: string[]) => {
      const response = await fetch(
        `/api/rooms/${encodeURIComponent(getInitialRoomId())}/sheet/${encodeURIComponent(sheet.id)}/choices/${encodeURIComponent(choiceId)}?playerKey=${encodeURIComponent(playerKey)}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ values })
        }
      );
      if (!response.ok) {
        setSheetStatus("error");
        return;
      }
      const body = (await response.json()) as { sheet: CharacterSheet };
      if (body.sheet) {
        setSheets((current) => current.map((candidate) => (candidate.id === body.sheet.id ? body.sheet : candidate)));
      }
    },
    [playerKey]
  );

  const updateEquipmentSlot = useCallback(
    async (sheet: CharacterSheet, itemId: string, slot: EquipmentSlot) => {
      const response = await fetch(
        `/api/rooms/${encodeURIComponent(getInitialRoomId())}/sheet/${encodeURIComponent(sheet.id)}/equipment/${encodeURIComponent(itemId)}/slot?playerKey=${encodeURIComponent(playerKey)}&slot=${encodeURIComponent(slot)}`,
        { method: "POST" }
      );
      if (!response.ok) {
        setSheetStatus("error");
        return;
      }
      const body = (await response.json()) as { sheet: CharacterSheet };
      setSheets((current) => current.map((candidate) => (candidate.id === body.sheet.id ? body.sheet : candidate)));
    },
    [playerKey]
  );

  const updateCondition = useCallback(
    async (sheet: CharacterSheet, condition: ConditionType, active: boolean) => {
      const response = await fetch(
        `/api/rooms/${encodeURIComponent(getInitialRoomId())}/sheet/${encodeURIComponent(sheet.id)}/conditions/${encodeURIComponent(condition)}?playerKey=${encodeURIComponent(playerKey)}&active=${encodeURIComponent(active)}`,
        { method: "POST" }
      );
      if (!response.ok) {
        setSheetStatus("error");
        return;
      }
      const body = (await response.json()) as { sheet: CharacterSheet };
      if (body.sheet) {
        setSheets((current) => current.map((candidate) => (candidate.id === body.sheet.id ? body.sheet : candidate)));
      }
    },
    [playerKey]
  );

  const createCharacter = useCallback(
    async (draft: CharacterBuilderDraft) => {
      const response = await fetch(`/api/rooms/${encodeURIComponent(getInitialRoomId())}/characters?playerKey=${encodeURIComponent(playerKey)}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(draft)
      });
      if (!response.ok) {
        setSheetStatus("error");
        return;
      }
      const body = (await response.json()) as { sheets: CharacterSheet[]; pendingRolls: RollPayload[]; rollHistory: RollLogEntry[] };
      setSheets(body.sheets);
      setRolls(body.pendingRolls);
      setRollHistory(body.rollHistory);
      setSheetStatus("idle");
    },
    [playerKey]
  );

  if (view === "sheet") {
    return (
      <SheetView
        connection={connection}
        expandedSheetId={expandedSheetId}
        isDm={isDm}
        onCreateCharacter={createCharacter}
        onExpand={setExpandedSheetId}
        onRollDamage={rollDamage}
        onRollAttack={rollAttack}
        onRollAbilityCheck={rollAbilityCheck}
        onRollResourceAction={rollResourceAction}
        onRollSavingThrow={rollSavingThrow}
        onClearSheetRolls={clearSheetRolls}
        onRestSheets={restSheets}
        onUpdateProgressionChoice={updateProgressionChoice}
        onUpdateCondition={updateCondition}
        onUpdateEquipmentSlot={updateEquipmentSlot}
        onUpdateSheetLevel={updateSheetLevel}
        onUpdateResource={updateResource}
        playerKey={playerKey}
        rollHistory={rollHistory}
        rolls={rolls}
        sheets={sheets}
        sheetStatus={sheetStatus}
        tokens={tokens}
      />
    );
  }

  return (
    <main className={`app-shell${dragPreview ? " is-dragging" : ""}`}>
      <aside className="sidebar">
        <div>
          <h1>DnD Board</h1>
          <p className="status">
            {connection} · {players.length}/8 connected
          </p>
          <p className="status">You are {formatPlayerName(playerKey, tokens)}</p>
        </div>

        {isDm && (
          <section className="dm-tools">
            <div className="save-load-actions">
              <button className="save-button" onClick={saveRoom} disabled={saveStatus === "saving"}>
                {saveStatus === "saving" ? "Saving" : saveStatus === "saved" ? "Saved" : saveStatus === "error" ? "Save Failed" : "Save"}
              </button>
              <button onClick={loadRoom} disabled={loadStatus === "loading"}>
                {loadStatus === "loading" ? "Loading" : loadStatus === "loaded" ? "Loaded" : loadStatus === "error" ? "Load Failed" : "Load"}
              </button>
            </div>

            <button onClick={clearScene}>Clear Scene</button>

            {boards.length > 0 && (
              <label>
                Board
                <select value={board.id} onChange={(event) => setActiveBoard(event.currentTarget.value)}>
                  {boards.map((availableBoard) => (
                    <option key={availableBoard.id} value={availableBoard.id}>
                      {availableBoard.name}
                    </option>
                  ))}
                </select>
              </label>
            )}

            {assets.length > 0 && (
              <div className="asset-loader">
                <label className="asset-search">
                  Search
                  <input type="search" value={assetSearch} onChange={(event) => setAssetSearch(event.currentTarget.value)} />
                </label>
                <label>
                  Asset
                  <select value={visibleSelectedAssetKey} onChange={(event) => setSelectedAssetKey(event.currentTarget.value)}>
                    {filteredAssets.map((asset) => (
                      <option key={assetKey(asset)} value={assetKey(asset)}>
                        {asset.name}
                      </option>
                    ))}
                  </select>
                </label>
                <button onClick={loadSelectedAsset} disabled={!visibleSelectedAssetKey}>
                  Add
                </button>
              </div>
            )}

            <label className="toggle-row">
              <input checked={fog.hideMode} type="checkbox" onChange={(event) => setHideMode(event.currentTarget.checked)} />
              Hide
            </label>

            {fog.hideMode && (
              <>
                <label className="toggle-row">
                  <input
                    checked={revealToolEnabled}
                    type="checkbox"
                    onChange={(event) => {
                      const enabled = event.currentTarget.checked;
                      setRevealToolEnabled(enabled);
                      if (enabled && canvasHoverRef.current) {
                        setBrushPreview(canvasHoverRef.current);
                      }
                      if (!enabled) {
                        setBrushPreview(null);
                      }
                    }}
                  />
                  Reveal
                </label>

                <label>
                  Brush
                  <input
                    max="360"
                    min="20"
                    type="range"
                    value={fog.brushSize}
                    onChange={(event) => setBrushSize(Number(event.currentTarget.value))}
                  />
                </label>
              </>
            )}
          </section>
        )}

        <TokenSection
          onDelete={deleteToken}
          onPointerCancel={handleSidebarPointerUp}
          onPointerDown={handleSidebarPointerDown}
          onPointerMove={handleSidebarPointerMove}
          onPointerUp={handleSidebarPointerUp}
          maxTokenRadius={maxTokenRadius}
          onResizeToken={setTokenRadius}
          isDm={isDm}
          playerKey={playerKey}
          title="Party"
          tokens={partyTokens}
        />

        {otherTokens.length > 0 && (
          <TokenSection
            onDelete={deleteToken}
            onPointerCancel={handleSidebarPointerUp}
            onPointerDown={handleSidebarPointerDown}
            onPointerMove={handleSidebarPointerMove}
            onPointerUp={handleSidebarPointerUp}
            maxTokenRadius={maxTokenRadius}
            onResizeToken={setTokenRadius}
            isDm={isDm}
            playerKey={playerKey}
            title="Other"
            tokens={otherTokens}
          />
        )}

        {ownLockedTokenId && <p className="hint">Dragging {tokens.find((token) => token.id === ownLockedTokenId)?.name}</p>}
      </aside>

      <section className="board-wrap">
        <canvas
          className={dragPreview ? "is-dragging" : ""}
          ref={canvasRef}
          style={boardCanvasStyle}
          width={boardSize.width}
          height={boardSize.height}
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={finishDrag}
          onPointerCancel={finishDrag}
          onPointerEnter={(event) => {
            const point = canvasPoint(event, boardSize);
            canvasHoverRef.current = point;
            if (isDm && fog.hideMode && revealToolEnabled) {
              setBrushPreview(point);
            }
          }}
          onPointerLeave={() => {
            canvasHoverRef.current = null;
            setBrushPreview(null);
          }}
        />
      </section>
      {dragGhost && <DragGhostToken token={tokens.find((token) => token.id === dragGhost.tokenId)} x={dragGhost.clientX} y={dragGhost.clientY} />}
    </main>
  );
}

type SheetViewProps = {
  connection: ConnectionState;
  expandedSheetId: string | null;
  isDm: boolean;
  onCreateCharacter: (draft: CharacterBuilderDraft) => Promise<void>;
  onExpand: (sheetId: string | null) => void;
  onClearSheetRolls: (sheet: CharacterSheet) => void;
  onRollAbilityCheck: (sheet: CharacterSheet, ability: string) => void;
  onRollAttack: (sheet: CharacterSheet, attackId: string) => void;
  onRollDamage: (sheet: CharacterSheet, attackId: string) => void;
  onRollResourceAction: (sheet: CharacterSheet, abilityId: string, actionId: string) => void;
  onRollSavingThrow: (sheet: CharacterSheet, ability: string) => void;
  onRestSheets: (rest: "short" | "long") => void;
  onUpdateProgressionChoice: (sheet: CharacterSheet, choiceId: string, values: string[]) => void;
  onUpdateCondition: (sheet: CharacterSheet, condition: ConditionType, active: boolean) => void;
  onUpdateEquipmentSlot: (sheet: CharacterSheet, itemId: string, slot: EquipmentSlot) => void;
  onUpdateSheetLevel: (sheet: CharacterSheet, delta: 1 | -1) => void;
  onUpdateResource: (sheet: CharacterSheet, resourceId: string, currentUses: number) => void;
  playerKey: string;
  rollHistory: RollLogEntry[];
  rolls: RollPayload[];
  sheets: CharacterSheet[];
  sheetStatus: "idle" | "loading" | "error";
  tokens: Token[];
};

function SheetView({ connection, expandedSheetId, isDm, onCreateCharacter, onClearSheetRolls, onExpand, onRollAbilityCheck, onRollAttack, onRollDamage, onRollResourceAction, onRollSavingThrow, onRestSheets, onUpdateProgressionChoice, onUpdateCondition, onUpdateEquipmentSlot, onUpdateSheetLevel, onUpdateResource, playerKey, rollHistory, rolls, sheets, sheetStatus, tokens }: SheetViewProps) {
  const expandedSheet = expandedSheetId ? sheets.find((sheet) => sheet.id === expandedSheetId) : null;
  const partySheets = useMemo(() => sheets.filter((sheet) => sheet.kind === TokenKind.CHARACTER), [sheets]);
  const otherSheets = useMemo(() => sheets.filter((sheet) => sheet.kind !== TokenKind.CHARACTER), [sheets]);
  const showCharacterBuilder = shouldShowCharacterBuilder(isDm, playerKey, partySheets);
  const [draggingRollId, setDraggingRollId] = useState<string | null>(null);
  const [dropTargetSheetId, setDropTargetSheetId] = useState<string | null>(null);
  const [clearedCardRollIds, setClearedCardRollIds] = useState<Set<string>>(() => new Set());
  const draggingRoll = useMemo(() => rolls.find((roll) => roll.id === draggingRollId), [draggingRollId, rolls]);
  const canDropRoll = isDm && isTargetableRoll(draggingRoll);

  const applyRollToSheet = useCallback(
    async (rollId: string, target: CharacterSheet) => {
      if (!isTargetableRoll(rolls.find((roll) => roll.id === rollId))) {
        setDraggingRollId(null);
        setDropTargetSheetId(null);
        return;
      }
      try {
        const params = new URLSearchParams({ playerKey, targetSheetId: target.id });
        const response = await fetch(`/api/rooms/${encodeURIComponent(getInitialRoomId())}/rolls/${encodeURIComponent(rollId)}/resolve?${params}`, {
          method: "POST"
        });
        if (!response.ok) {
          throw new Error(await response.text());
        }
      } catch (error) {
        console.error(error);
      } finally {
        setDraggingRollId(null);
        setDropTargetSheetId(null);
      }
    },
    [playerKey, rolls]
  );
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
          <div className="rest-actions">
            <button onClick={() => onRestSheets("short")}>Short Rest</button>
            <button onClick={() => onRestSheets("long")}>Long Rest</button>
          </div>
        )}
      </header>

      {expandedSheet ? (
        <FullSheet
          sheet={expandedSheet}
          canRoll={canRollSheet(expandedSheet, playerKey, isDm)}
          pendingRolls={rolls.filter((roll) => roll.tokenId === expandedSheet.tokenId)}
          resolvedRolls={cardResolvedRolls(expandedSheet, rollHistory, clearedCardRollIds)}
          rollDraggable={isDm}
          onClearSheetRolls={clearRollsForSheet}
          onDragRollEnd={() => {
            setDraggingRollId(null);
            setDropTargetSheetId(null);
          }}
          onDragRollStart={setDraggingRollId}
          onRollAbilityCheck={onRollAbilityCheck}
          onRollAttack={onRollAttack}
          onRollDamage={onRollDamage}
          onRollResourceAction={onRollResourceAction}
          onRollSavingThrow={onRollSavingThrow}
          onUpdateProgressionChoice={onUpdateProgressionChoice}
          onUpdateCondition={onUpdateCondition}
          onUpdateEquipmentSlot={onUpdateEquipmentSlot}
          onUpdateSheetLevel={onUpdateSheetLevel}
          onUpdateResource={onUpdateResource}
          onClose={() => onExpand(null)}
          isDm={isDm}
        />
      ) : (
        <div className="sheet-sections" aria-busy={sheetStatus === "loading"}>
          {showCharacterBuilder && <CharacterBuilderPanel isDm={isDm} onCreateCharacter={onCreateCharacter} playerKey={playerKey} sheets={partySheets} />}
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
              setDropTargetSheetId(null);
            }}
            onDragRollStart={setDraggingRollId}
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
                setDropTargetSheetId(null);
              }}
              onDragRollStart={setDraggingRollId}
            />
          )}
        </div>
      )}

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

function CharacterBuilderPanel({
  isDm,
  onCreateCharacter,
  playerKey,
  sheets
}: {
  isDm: boolean;
  onCreateCharacter: (draft: CharacterBuilderDraft) => Promise<void>;
  playerKey: string;
  sheets: CharacterSheet[];
}) {
  const [options, setOptions] = useState<CharacterBuilderOptions | null>(null);
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const memberOptions = useMemo(() => characterBuilderMemberOptions(isDm, playerKey, sheets), [isDm, playerKey, sheets]);
  const [draft, setDraft] = useState<CharacterBuilderDraft>(() => defaultCharacterBuilderDraft(memberOptions[0]?.value ?? playerKey));
  const backgroundDetail = options?.backgroundDetails[draft.background];
  const selectedToolDetail = draft.toolProficiency ? options?.toolDetails[draft.toolProficiency] : undefined;
  const magicInitiateChoices = backgroundDetail?.magicInitiateSpellChoices;
  const usesScorePool = draft.abilityScoreMethod !== ABILITY_SCORE_METHOD_POINT_BUY;
  const scorePool = draft.abilityScoreMethod === ABILITY_SCORE_METHOD_RANDOM ? draft.rolledAbilityScores : options?.standardArray ?? [];
  const availableScoreCounts = countScoreValues(scorePool);
  const pointBuySpent = ABILITY_SCORE_OPTIONS.reduce((sum, ability) => sum + (options?.pointBuyCosts[String(draft.baseAbilityScores[ability.value])] ?? 0), 0);
  const backgroundIncreaseMode = Object.values(draft.backgroundAbilityIncreases).filter((increase) => increase > 0).length === 3 ? "oneEach" : "twoOne";
  const backgroundPlusTwo = ABILITY_SCORE_OPTIONS.find((ability) => draft.backgroundAbilityIncreases[ability.value] === 2)?.value ?? (backgroundDetail?.abilityScores[0]?.value as AbilityType | undefined);
  const backgroundPlusOne = ABILITY_SCORE_OPTIONS.find((ability) => draft.backgroundAbilityIncreases[ability.value] === 1)?.value ?? (backgroundDetail?.abilityScores[1]?.value as AbilityType | undefined);

  useEffect(() => {
    let active = true;
    fetch(`/api/rooms/${encodeURIComponent(getInitialRoomId())}/character-builder/options`)
      .then((response) => response.json())
      .then((body: CharacterBuilderOptions) => {
        if (active) {
          setOptions(body);
          setDraft((current) => normalizeCharacterBuilderDraft(current, body));
        }
      })
      .catch((error) => console.error(error));
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    setDraft((current) => {
      const fallbackMemberId = memberOptions[0]?.value ?? playerKey;
      const memberId = isDm && memberOptions.some((option) => option.value === current.memberId) ? current.memberId : fallbackMemberId;
      return { ...current, memberId };
    });
  }, [isDm, memberOptions, playerKey]);

  const updateDraft = (patch: Partial<CharacterBuilderDraft>) => {
    setDraft((current) => ({ ...current, ...patch }));
  };
  const updateBaseAbilityScore = (ability: AbilityType, value: number) => {
    setDraft((current) => ({
      ...current,
      baseAbilityScores: updatedBaseAbilityScores(current, ability, value)
    }));
  };
  const updateBackground = (background: string) => {
    if (!options) {
      updateDraft({ background });
      return;
    }
    setDraft((current) => normalizeCharacterBuilderDraft({ ...current, background }, options));
  };
  const updateIncreaseMode = (mode: "twoOne" | "oneEach") => {
    if (!backgroundDetail) return;
    const abilities = backgroundDetail.abilityScores.map((option) => option.value as AbilityType);
    updateDraft({ backgroundAbilityIncreases: abilityIncreasesForMode(mode, abilities) });
  };
  const updateTwoOneIncrease = (amount: 1 | 2, ability: AbilityType) => {
    if (!backgroundDetail) return;
    const abilities = backgroundDetail.abilityScores.map((option) => option.value as AbilityType);
    const otherAmount = amount === 2 ? 1 : 2;
    const otherAbility = ABILITY_SCORE_OPTIONS.find((option) => draft.backgroundAbilityIncreases[option.value] === otherAmount)?.value;
    updateDraft({ backgroundAbilityIncreases: abilityIncreasesForTwoOne(abilities, amount === 2 ? ability : otherAbility, amount === 1 ? ability : otherAbility) });
  };

  const updateMagicInitiateSpell = (index: number, spellId: string) => {
    const nextSpells = [...draft.magicInitiateSpells];
    nextSpells[index] = spellId;
    updateDraft({ magicInitiateSpells: nextSpells });
  };
  const updateAbilityScoreMethod = (abilityScoreMethod: string) => {
    if (!options) {
      updateDraft({ abilityScoreMethod });
      return;
    }
    const rolledAbilityScores = abilityScoreMethod === ABILITY_SCORE_METHOD_RANDOM && draft.rolledAbilityScores.length !== 6 ? rollAbilityScorePool() : draft.rolledAbilityScores;
    setDraft((current) => ({
      ...current,
      abilityScoreMethod,
      rolledAbilityScores,
      baseAbilityScores: baseAbilityScoresForMethod(abilityScoreMethod, options, rolledAbilityScores)
    }));
  };
  const rerollAbilityScores = () => {
    if (!options) return;
    const rolledAbilityScores = rollAbilityScorePool();
    updateDraft({
      abilityScoreMethod: ABILITY_SCORE_METHOD_RANDOM,
      rolledAbilityScores,
      baseAbilityScores: baseAbilityScoresForMethod(ABILITY_SCORE_METHOD_RANDOM, options, rolledAbilityScores)
    });
  };
  const characterBuilderInvalid = draft.abilityScoreMethod === ABILITY_SCORE_METHOD_POINT_BUY && pointBuySpent > (options?.pointBuyPoints ?? 0);

  const create = async () => {
    setSaving(true);
    try {
      await onCreateCharacter(draft);
      setOpen(false);
    } finally {
      setSaving(false);
    }
  };

  if (!options) return null;
  if (memberOptions.length === 0) return null;

  return (
    <section className="sheet-panel character-builder-panel">
      <div className="panel-title-row">
        <h2>Character Builder</h2>
        <button type="button" onClick={() => setOpen((current) => !current)}>
          {open ? "Close" : "Build"}
        </button>
      </div>
      {open && (
        <div className="character-builder-grid">
          <label>
            Slot
            <select value={draft.memberId} disabled={!isDm} onChange={(event) => updateDraft({ memberId: event.currentTarget.value })}>
              {memberOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            Name
            <input value={draft.name} onChange={(event) => updateDraft({ name: event.currentTarget.value })} />
          </label>
          <label>
            Class
            <select value={draft.className} onChange={(event) => updateDraft({ className: event.currentTarget.value })}>
              {options.classes.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            Race
            <select value={draft.race} onChange={(event) => updateDraft({ race: event.currentTarget.value })}>
              {options.races.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            Background
            <select value={draft.background} onChange={(event) => updateBackground(event.currentTarget.value)}>
              {options.backgrounds.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            Scores
            <select value={draft.abilityScoreMethod} onChange={(event) => updateAbilityScoreMethod(event.currentTarget.value)}>
              {options.abilityScoreMethods.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            Tool
            <select value={draft.toolProficiency ?? ""} onChange={(event) => updateDraft({ toolProficiency: event.currentTarget.value })}>
              {(backgroundDetail?.toolOptions ?? []).length === 0 && <option value="">None</option>}
              {(backgroundDetail?.toolOptions ?? []).map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          {selectedToolDetail && (
            <div className="builder-detail-list">
              <span>{selectedToolDetail.category} · {abilityLabel(selectedToolDetail.ability)} · {selectedToolDetail.cost}{selectedToolDetail.weightLb != null ? ` · ${selectedToolDetail.weightLb} lb.` : ""}</span>
              {selectedToolDetail.utilizeActions.length > 0 && <small>Utilize: {selectedToolDetail.utilizeActions.map((action) => `${action.description} DC ${action.dc}`).join("; ")}</small>}
              {selectedToolDetail.craftOutputs.length > 0 && <small>Craft: {selectedToolDetail.craftOutputs.join(", ")}</small>}
            </div>
          )}
          <label>
            Equipment
            <select value={draft.equipmentChoice} onChange={(event) => updateDraft({ equipmentChoice: event.currentTarget.value })}>
              {(backgroundDetail?.equipmentChoices ?? []).map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          {magicInitiateChoices && (
            <div className="builder-spell-choices">
              <div className="builder-subsection-title">Magic Initiate ({magicInitiateChoices.spellList})</div>
              {Array.from({ length: magicInitiateChoices.cantripsKnown }).map((_, index) => (
                <label key={`magic-initiate-cantrip-${index}`}>
                  Cantrip {index + 1}
                  <select value={draft.magicInitiateSpells[index] ?? ""} onChange={(event) => updateMagicInitiateSpell(index, event.currentTarget.value)}>
                    {magicInitiateChoices.cantrips.map((option) => (
                      <option key={option.value} value={option.value} disabled={draft.magicInitiateSpells.includes(option.value) && draft.magicInitiateSpells[index] !== option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>
              ))}
              {Array.from({ length: magicInitiateChoices.firstLevelSpellsKnown }).map((_, index) => {
                const spellIndex = magicInitiateChoices.cantripsKnown + index;
                return (
                  <label key={`magic-initiate-first-${index}`}>
                    1st-Level Spell
                    <select value={draft.magicInitiateSpells[spellIndex] ?? ""} onChange={(event) => updateMagicInitiateSpell(spellIndex, event.currentTarget.value)}>
                      {magicInitiateChoices.firstLevelSpells.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </label>
                );
              })}
              <div className="builder-detail-list">
                {draft.magicInitiateSpells.map((spellId) => selectedMagicInitiateSpellOption(magicInitiateChoices, spellId)).filter(Boolean).map((spell) => (
                  <small key={spell!.value}>{spell!.label}: {spell!.level === 0 ? "Cantrip" : `Level ${spell!.level}`} · {spell!.range} · {spell!.duration} · {spell!.components.join(", ") || "None"}</small>
                ))}
              </div>
            </div>
          )}
          <label>
            Ability Boost
            <select value={backgroundIncreaseMode} onChange={(event) => updateIncreaseMode(event.currentTarget.value as "twoOne" | "oneEach")}>
              <option value="twoOne">+2 / +1</option>
              <option value="oneEach">+1 / +1 / +1</option>
            </select>
          </label>
          {backgroundIncreaseMode === "twoOne" && (
            <>
              <label>
                +2
                <select value={backgroundPlusTwo ?? ""} onChange={(event) => updateTwoOneIncrease(2, event.currentTarget.value as AbilityType)}>
                  {(backgroundDetail?.abilityScores ?? []).map((option) => (
                    <option key={option.value} value={option.value} disabled={option.value === backgroundPlusOne}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                +1
                <select value={backgroundPlusOne ?? ""} onChange={(event) => updateTwoOneIncrease(1, event.currentTarget.value as AbilityType)}>
                  {(backgroundDetail?.abilityScores ?? []).map((option) => (
                    <option key={option.value} value={option.value} disabled={option.value === backgroundPlusTwo}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
            </>
          )}
          <div className="ability-score-editor">
            <div className="ability-score-editor-meta">
              {draft.abilityScoreMethod === ABILITY_SCORE_METHOD_POINT_BUY && <span>Point Buy {pointBuySpent} / {options.pointBuyPoints}</span>}
              {draft.abilityScoreMethod === ABILITY_SCORE_METHOD_RANDOM && (
                <>
                  <span>Rolled {draft.rolledAbilityScores.join(", ")}</span>
                  <button type="button" onClick={rerollAbilityScores}>Roll</button>
                </>
              )}
            </div>
            {ABILITY_SCORE_OPTIONS.map((ability) => (
              <label key={ability.value}>
                {ability.label}
                <span className="ability-score-select-row">
                  <select value={draft.baseAbilityScores[ability.value]} onChange={(event) => updateBaseAbilityScore(ability.value, Number(event.currentTarget.value))}>
                    {scoreOptionsForMethod(draft.abilityScoreMethod, options, scorePool).map((score) => (
                      <option key={score} value={score} disabled={scoreOptionDisabled(score, ability.value, draft, options, usesScorePool, availableScoreCounts, pointBuySpent)}>
                        {score}
                      </option>
                    ))}
                  </select>
                  <span className="ability-score-total">{draft.baseAbilityScores[ability.value] + draft.backgroundAbilityIncreases[ability.value]}</span>
                </span>
              </label>
            ))}
          </div>
          <button className="builder-submit" type="button" disabled={saving || characterBuilderInvalid} onClick={create}>
            {saving ? "Creating" : "Create Character"}
          </button>
        </div>
      )}
    </section>
  );
}

function defaultCharacterBuilderDraft(playerKey: string): CharacterBuilderDraft {
  return {
    memberId: playerKey.startsWith("player-") ? playerKey : "player-1",
    name: "New Character",
    className: "rogue",
    race: "dwarf",
    background: "criminal",
    abilityScoreMethod: ABILITY_SCORE_METHOD_STANDARD_ARRAY,
    baseAbilityScores: defaultBaseAbilityScores(),
    rolledAbilityScores: [],
    backgroundAbilityIncreases: abilityIncreasesForTwoOne(["dexterity", "constitution", "intelligence"], "dexterity", "constitution"),
    toolProficiency: "thievesTools",
    equipmentChoice: "package",
    magicInitiateSpells: []
  };
}

function defaultBaseAbilityScores(): AbilityScores {
  return {
    strength: 8,
    dexterity: 15,
    constitution: 14,
    intelligence: 13,
    wisdom: 10,
    charisma: 12
  };
}

function abilityLabel(ability: AbilityType): string {
  return ABILITY_SCORE_OPTIONS.find((option) => option.value === ability)?.label ?? ability;
}

function normalizeCharacterBuilderDraft(draft: CharacterBuilderDraft, options: CharacterBuilderOptions): CharacterBuilderDraft {
  const detail = options.backgroundDetails[draft.background];
  if (!detail) return draft;
  const toolProficiency = detail.toolOptions.some((option) => option.value === draft.toolProficiency) ? draft.toolProficiency : detail.toolOptions[0]?.value;
  const equipmentChoice = detail.equipmentChoices.some((option) => option.value === draft.equipmentChoice) ? draft.equipmentChoice : detail.equipmentChoices[0]?.value ?? "package";
  const magicInitiateSpells = normalizedMagicInitiateSpells(draft.magicInitiateSpells, detail);
  const abilities = detail.abilityScores.map((option) => option.value as AbilityType);
  const validIncreases = abilities.length > 0 && ABILITY_SCORE_OPTIONS.every((ability) => {
    const increase = draft.backgroundAbilityIncreases[ability.value];
    return increase >= 0 && increase <= 2 && (increase === 0 || abilities.includes(ability.value));
  });
  const totalIncrease = Object.values(draft.backgroundAbilityIncreases).reduce((sum, increase) => sum + increase, 0);
  return {
    ...draft,
    toolProficiency,
    equipmentChoice,
    magicInitiateSpells,
    backgroundAbilityIncreases: validIncreases && totalIncrease === 3 ? draft.backgroundAbilityIncreases : abilityIncreasesForMode("twoOne", abilities)
  };
}

function normalizedMagicInitiateSpells(selectedSpells: string[], detail: CharacterBuilderOptions["backgroundDetails"][string]): string[] {
  const choices = detail.magicInitiateSpellChoices;
  if (!choices) return [];
  const selectedCantrips = selectedSpells.slice(0, choices.cantripsKnown).filter((spellId, index, spells) => choices.cantrips.some((option) => option.value === spellId) && spells.indexOf(spellId) === index);
  const selectedFirstLevel = selectedSpells.slice(choices.cantripsKnown).filter((spellId) => choices.firstLevelSpells.some((option) => option.value === spellId));
  const cantrips = [...selectedCantrips];
  for (const option of choices.cantrips) {
    if (cantrips.length >= choices.cantripsKnown) break;
    if (!cantrips.includes(option.value)) cantrips.push(option.value);
  }
  const firstLevelSpells = selectedFirstLevel.slice(0, choices.firstLevelSpellsKnown);
  for (const option of choices.firstLevelSpells) {
    if (firstLevelSpells.length >= choices.firstLevelSpellsKnown) break;
    if (!firstLevelSpells.includes(option.value)) firstLevelSpells.push(option.value);
  }
  return [...cantrips, ...firstLevelSpells];
}

function selectedMagicInitiateSpellOption(choices: NonNullable<CharacterBuilderOptions["backgroundDetails"][string]["magicInitiateSpellChoices"]>, spellId: string) {
  return [...choices.cantrips, ...choices.firstLevelSpells].find((option) => option.value === spellId);
}

function baseAbilityScoresForMethod(method: string, options: CharacterBuilderOptions, rolledScores: number[]): AbilityScores {
  if (method === ABILITY_SCORE_METHOD_POINT_BUY) {
    return {
      strength: 8,
      dexterity: 15,
      constitution: 14,
      intelligence: 10,
      wisdom: 10,
      charisma: 8
    };
  }
  const pool = method === ABILITY_SCORE_METHOD_RANDOM ? rolledScores : options.standardArray;
  return abilityScoresFromPool(pool.length === 6 ? pool : options.standardArray);
}

function abilityScoresFromPool(pool: number[]): AbilityScores {
  const sorted = [...pool].sort((left, right) => right - left);
  return {
    strength: sorted[5] ?? 8,
    dexterity: sorted[0] ?? 15,
    constitution: sorted[1] ?? 14,
    intelligence: sorted[2] ?? 13,
    wisdom: sorted[4] ?? 10,
    charisma: sorted[3] ?? 12
  };
}

function scoreOptionsForMethod(method: string, options: CharacterBuilderOptions, scorePool: number[]): number[] {
  if (method === ABILITY_SCORE_METHOD_POINT_BUY) {
    return Object.keys(options.pointBuyCosts).map(Number).sort((left, right) => left - right);
  }
  return Array.from(new Set(scorePool)).sort((left, right) => right - left);
}

function scoreOptionDisabled(
  score: number,
  ability: AbilityType,
  draft: CharacterBuilderDraft,
  options: CharacterBuilderOptions,
  usesScorePool: boolean,
  availableScoreCounts: Map<number, number>,
  pointBuySpent: number
): boolean {
  if (!usesScorePool) {
    const currentScore = draft.baseAbilityScores[ability];
    const currentCost = options.pointBuyCosts[String(currentScore)] ?? 0;
    const nextCost = options.pointBuyCosts[String(score)] ?? 0;
    return pointBuySpent - currentCost + nextCost > options.pointBuyPoints;
  }
  return (availableScoreCounts.get(score) ?? 0) === 0;
}

function countScoreValues(scores: number[]): Map<number, number> {
  const counts = new Map<number, number>();
  scores.forEach((score) => counts.set(score, (counts.get(score) ?? 0) + 1));
  return counts;
}

function updatedBaseAbilityScores(draft: CharacterBuilderDraft, ability: AbilityType, nextScore: number): AbilityScores {
  if (draft.abilityScoreMethod === ABILITY_SCORE_METHOD_POINT_BUY) {
    return { ...draft.baseAbilityScores, [ability]: nextScore };
  }
  const currentScore = draft.baseAbilityScores[ability];
  const holder = ABILITY_SCORE_OPTIONS.find((option) => option.value !== ability && draft.baseAbilityScores[option.value] === nextScore)?.value;
  if (!holder) {
    return { ...draft.baseAbilityScores, [ability]: nextScore };
  }
  return {
    ...draft.baseAbilityScores,
    [ability]: nextScore,
    [holder]: currentScore
  };
}

function rollAbilityScorePool(): number[] {
  return Array.from({ length: 6 }, rollAbilityScore);
}

function rollAbilityScore(): number {
  const dice = Array.from({ length: 4 }, () => Math.floor(Math.random() * 6) + 1).sort((left, right) => left - right);
  return dice.slice(1).reduce((sum, die) => sum + die, 0);
}

function abilityIncreasesForMode(mode: "twoOne" | "oneEach", abilities: AbilityType[]): AbilityScores {
  if (mode === "oneEach") {
    return abilityIncreasesFromEntries(abilities.map((ability) => [ability, 1]));
  }
  return abilityIncreasesForTwoOne(abilities, abilities[0], abilities[1]);
}

function abilityIncreasesForTwoOne(abilities: AbilityType[], plusTwo?: AbilityType, plusOne?: AbilityType): AbilityScores {
  const selectedPlusTwo = plusTwo && abilities.includes(plusTwo) ? plusTwo : abilities[0];
  const selectedPlusOne = plusOne && abilities.includes(plusOne) && plusOne !== selectedPlusTwo ? plusOne : abilities.find((ability) => ability !== selectedPlusTwo);
  return abilityIncreasesFromEntries([
    [selectedPlusTwo, 2],
    [selectedPlusOne, 1]
  ]);
}

function abilityIncreasesFromEntries(entries: ([AbilityType | undefined, number])[]): AbilityScores {
  const scores: AbilityScores = {
    strength: 0,
    dexterity: 0,
    constitution: 0,
    intelligence: 0,
    wisdom: 0,
    charisma: 0
  };
  entries.forEach(([ability, increase]) => {
    if (ability) scores[ability] = increase;
  });
  return scores;
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
  clearedCardRollIds
}: {
  title: string;
  sheets: CharacterSheet[];
  canDrop: boolean;
  dropTargetSheetId: string | null;
  onApplyRoll: (rollId: string, target: CharacterSheet) => void;
  onClearSheetRolls: (sheet: CharacterSheet) => void;
  onDragRollEnd: () => void;
  onDragRollStart: (rollId: string) => void;
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
  resolvedRolls,
  rollDraggable
}: {
  sheet: CharacterSheet;
  canClearRolls: boolean;
  canDrop: boolean;
  draggingRollId: string | null;
  isDropTarget: boolean;
  onApplyRoll: (rollId: string, target: CharacterSheet) => void;
  onClearSheetRolls: (sheet: CharacterSheet) => void;
  onDragRollEnd: () => void;
  onDragRollStart: (rollId: string) => void;
  onDropTarget: (sheetId: string | null) => void;
  onExpand: () => void;
  onUpdateProgressionChoice: (sheet: CharacterSheet, choiceId: string, values: string[]) => void;
  onUpdateSheetLevel: (sheet: CharacterSheet, delta: 1 | -1) => void;
  pendingRolls: RollPayload[];
  resolvedRolls: RollLogEntry[];
  rollDraggable: boolean;
}) {
  const hasCardRolls = pendingRolls.length > 0 || resolvedRolls.length > 0;

  return (
    <article
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
        onApplyRoll(draggingRollId, sheet);
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
        {sheet.conditions.length > 0 && <div className="condition-list">{sheet.conditions.map((condition) => <span key={condition}>{cleanName(condition)}</span>)}</div>}
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
                onDragStart={() => onDragRollStart(pendingRoll.id)}
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
  onUpdateCondition
}: {
  canRoll: boolean;
  sheet: CharacterSheet;
  onUpdateCondition: (sheet: CharacterSheet, condition: ConditionType, active: boolean) => void;
}) {
  const activeConditions = new Set(sheet.conditions);

  return (
    <section className="sheet-panel">
      <h2>Conditions</h2>
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

function RollCard({
  compact = false,
  roll,
  roller,
  draggable,
  onDragEnd,
  onDragStart
}: {
  compact?: boolean;
  roll: RollPayload;
  roller: CharacterSheet | undefined;
  draggable: boolean;
  onDragEnd: () => void;
  onDragStart: () => void;
}) {
  const rollParentLabel = roll.sourceLabel && roll.sourceLabel !== roll.label ? roll.sourceLabel : roll.source.sectionLabel;

  return (
    <li
      className={["roll-card", draggable ? "draggable" : "", compact ? "compact" : ""].filter(Boolean).join(" ")}
      draggable={draggable}
      onDragEnd={onDragEnd}
      onDragStart={(event) => {
        event.dataTransfer.effectAllowed = "copy";
        event.dataTransfer.setData("text/plain", roll.id);
        onDragStart();
      }}
    >
      <span className="die-badge">
        <img src={diceImagePath(roll.diceType)} alt="" draggable={false} />
        <strong>{roll.total}</strong>
      </span>
      <span className="roll-main">
        <strong>{roll.label}</strong>
        <small>{roll.damageTypeLabel ? `${rollParentLabel} · ${roll.damageTypeLabel}` : rollParentLabel}</small>
      </span>
      {!compact && <span className="roll-total roll-result-number">{rollMathText(roll)}</span>}
    </li>
  );
}

function RollLogRow({ entry, roller }: { entry: RollLogEntry; roller: CharacterSheet | undefined }) {
  const roll = entry.roll;
  const actor = roller?.name ?? formatPlayerName(roll.roller);

  return (
    <li className="roll-log-row">
      <time dateTime={logEntryDate(entry).toISOString()}>{formatLogTime(entry)}</time>
      <span>
        <strong>{roll.sourceLabel}</strong>
        {entry.resolution
          ? ` ${actor}: ${roll.label} ${rollMathText(roll)}; ${entry.resolution.outcome} to ${entry.resolution.targetName}`
          : ` ${actor}: ${roll.label} `}
        {!entry.resolution && <span className="roll-result-number">{rollMathText(roll)}</span>}
        {roll.resourceSpent ? ` · ${roll.resourceSpent.resourceName} ${roll.resourceSpent.remainingUses}/${roll.resourceSpent.maxUses}` : ""}
      </span>
    </li>
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
  onDragRollStart: (rollId: string) => void;
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
  onDragRollStart: (rollId: string) => void;
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
          const resource = ability.resourceId ? sheet.resources.find((candidate) => candidate.id === ability.resourceId) : undefined;
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
              {(ability.rollActions ?? []).length > 0 ? (
                <RollActionList
                  canRoll={canRoll}
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

function InlineRolls({
  pendingRolls,
  resolvedRolls = [],
  roller,
  rollDraggable,
  onDragRollEnd,
  onDragRollStart
}: {
  pendingRolls: RollPayload[];
  resolvedRolls?: RollLogEntry[];
  roller: CharacterSheet;
  rollDraggable: boolean;
  onDragRollEnd: () => void;
  onDragRollStart: (rollId: string) => void;
}) {
  if (pendingRolls.length === 0 && resolvedRolls.length === 0) return null;

  return (
    <div className="inline-rolls">
      {pendingRolls.map((pendingRoll) => (
        <RollCard
          key={pendingRoll.id}
          roll={pendingRoll}
          roller={roller}
          draggable={rollDraggable && isTargetableRoll(pendingRoll)}
          compact
          onDragEnd={onDragRollEnd}
          onDragStart={() => onDragRollStart(pendingRoll.id)}
        />
      ))}
      {resolvedRolls.map((entry) => (
        <RollCard
          key={entry.id}
          roll={entry.roll}
          roller={roller}
          draggable={false}
          compact
          onDragEnd={onDragRollEnd}
          onDragStart={() => undefined}
        />
      ))}
    </div>
  );
}

function FullSheet({
  sheet,
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
  onUpdateProgressionChoice,
  onUpdateCondition,
  onUpdateEquipmentSlot,
  onUpdateSheetLevel,
  onUpdateResource
}: {
  sheet: CharacterSheet;
  canRoll: boolean;
  isDm: boolean;
  onClearSheetRolls: (sheet: CharacterSheet) => void;
  pendingRolls: RollPayload[];
  resolvedRolls: RollLogEntry[];
  rollDraggable: boolean;
  onDragRollEnd: () => void;
  onDragRollStart: (rollId: string) => void;
  onClose: () => void;
  onRollAbilityCheck: (sheet: CharacterSheet, ability: string) => void;
  onRollAttack: (sheet: CharacterSheet, attackId: string) => void;
  onRollDamage: (sheet: CharacterSheet, attackId: string) => void;
  onRollResourceAction: (sheet: CharacterSheet, resourceId: string, actionId: string) => void;
  onRollSavingThrow: (sheet: CharacterSheet, ability: string) => void;
  onUpdateProgressionChoice: (sheet: CharacterSheet, choiceId: string, values: string[]) => void;
  onUpdateCondition: (sheet: CharacterSheet, condition: ConditionType, active: boolean) => void;
  onUpdateEquipmentSlot: (sheet: CharacterSheet, itemId: string, slot: EquipmentSlot) => void;
  onUpdateSheetLevel: (sheet: CharacterSheet, delta: 1 | -1) => void;
  onUpdateResource: (sheet: CharacterSheet, resourceId: string, currentUses: number) => void;
}) {
  const scores = Object.entries(sheet.abilityScores);
  const metadata = [sheet.race, sheet.background, sheet.alignment].filter(Boolean).join(" · ");

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

        <ConditionPanel canRoll={canRoll} sheet={sheet} onUpdateCondition={onUpdateCondition} />
        {hasDamageDefenses(sheet) && (
          <section className="sheet-panel">
            <h2>Defenses</h2>
            <div className="compact-list">
              {sheet.damageResistances.length > 0 && <span>Resist {sheet.damageResistancesLabel.join(", ")}</span>}
              {sheet.damageVulnerabilities.length > 0 && <span>Vulnerable {sheet.damageVulnerabilitiesLabel.join(", ")}</span>}
              {sheet.damageImmunities.length > 0 && <span>Immune {sheet.damageImmunitiesLabel.join(", ")}</span>}
            </div>
          </section>
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

      <SheetSpellList canRoll={canRoll} sheet={sheet} onUpdateResource={onUpdateResource} />

      <section className="attack-list sheet-panel">
        <h2>Attacks</h2>
        {sheet.attacks.map((attack) => (
          <div className="attack-actions" key={attack.id}>
            <span>
              {attack.name} · {attack.abilityLabel} · {attack.damageDie} {attack.damageTypeLabel}
            </span>
            <button disabled={!canRoll} onClick={() => onRollAttack(sheet, attack.id)}>
              Attack Roll
            </button>
            <button disabled={!canRoll} onClick={() => onRollDamage(sheet, attack.id)}>
              Damage
            </button>
            <InlineRolls
              pendingRolls={pendingRolls.filter((roll) => rollMatchesSource(roll, SheetSectionType.ATTACKS, attack.id))}
              roller={sheet}
              rollDraggable={rollDraggable}
              onDragRollEnd={onDragRollEnd}
              onDragRollStart={onDragRollStart}
            />
          </div>
        ))}
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
                      {equipmentSlotOptions(item.itemType).map((slot) => (
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
  onUpdateResource,
  sheet
}: {
  canRoll: boolean;
  onUpdateResource: (sheet: CharacterSheet, resourceId: string, currentUses: number) => void;
  sheet: CharacterSheet;
}) {
  if (sheet.spells.length === 0 && sheet.spellbook.length === 0) return null;

  return (
    <section className="sheet-panel">
      <h2>Spells</h2>
      {sheet.spells.length > 0 && <div className="spell-list">
        {sheet.spells.map((spell) => {
          const resource = spell.resourceId ? sheet.resources.find((candidate) => candidate.id === spell.resourceId) : undefined;
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

function DragGhostToken({ token, x, y }: { token: Token | undefined; x: number; y: number }) {
  if (!token) return null;

  return (
    <div className="drag-ghost" style={{ left: x, top: y }}>
      {token.avatarUrl ? <img src={token.avatarUrl} alt="" draggable={false} /> : token.name.slice(0, 3).toUpperCase()}
    </div>
  );
}

type TokenSectionProps = {
  title: string;
  tokens: Token[];
  isDm: boolean;
  maxTokenRadius: number;
  onDelete: (token: Token) => void;
  onPointerCancel: (event: React.PointerEvent<HTMLElement>) => void;
  onPointerDown: (event: React.PointerEvent<HTMLElement>, token: Token) => void;
  onPointerMove: (event: React.PointerEvent<HTMLElement>) => void;
  onPointerUp: (event: React.PointerEvent<HTMLElement>) => void;
  onResizeToken: (token: Token, radius: number) => void;
  playerKey: string;
};

function TokenSection({
  title,
  tokens,
  isDm,
  maxTokenRadius,
  onDelete,
  onPointerCancel,
  onPointerDown,
  onPointerMove,
  onPointerUp,
  onResizeToken,
  playerKey
}: TokenSectionProps) {
  return (
    <section>
      <h2>{title}</h2>
      <ul className={`token-list ${isDm ? "dm-token-list" : "player-token-list"}`}>
        {tokens.map((token) => (
          <li
            className={[
              !canControlToken(token, playerKey, isDm) || (token.lockedBy && token.lockedBy !== playerKey) ? "locked" : "",
              token.inScene ? "in-scene" : ""
            ]
              .filter(Boolean)
              .join(" ")}
            key={token.id}
          >
            <span
              className="swatch drag-handle"
              draggable={false}
              onPointerDown={(event) => onPointerDown(event, token)}
              onPointerMove={onPointerMove}
              onPointerUp={onPointerUp}
              onPointerCancel={onPointerCancel}
              onDragStart={(event) => event.preventDefault()}
            >
              {token.avatarUrl && <img src={token.avatarUrl} alt="" draggable={false} />}
            </span>
            <span className="token-name" title={token.name}>
              {token.name}
            </span>
            {isDm && (
              <label className="token-size-control">
                <input
                  aria-label={`${token.name} size`}
                  max={maxTokenRadius}
                  min={MIN_TOKEN_RADIUS}
                  type="range"
                  value={token.radius}
                  onChange={(event) => onResizeToken(token, Number(event.currentTarget.value))}
                />
              </label>
            )}
            {isDm && token.kind !== TokenKind.CHARACTER && (
              <button className="icon-button danger" onClick={() => onDelete(token)} onPointerDown={(event) => event.stopPropagation()}>
                X
              </button>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}

function drawBoard(
  canvas: HTMLCanvasElement | null,
  tokens: Token[],
  playerKey: string,
  isDm: boolean,
  dragPreview: DragPreview | null,
  images: Map<string, HTMLImageElement>,
  fog: FogState,
  brushPreview: BrushPreview | null,
  board: Board,
  boardImages: Map<string, HTMLImageElement>,
  fogMaskRef: MutableRefObject<FogMaskCache | null>,
  boardSize: BoardSize
) {
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  ctx.clearRect(0, 0, boardSize.width, boardSize.height);
  drawBoardBackground(ctx, board, boardImages, boardSize);

  ctx.strokeStyle = "rgba(255, 255, 255, 0.14)";
  ctx.lineWidth = 1;
  for (let x = 0; x <= boardSize.width; x += 60) {
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, boardSize.height);
    ctx.stroke();
  }
  for (let y = 0; y <= boardSize.height; y += 60) {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(boardSize.width, y);
    ctx.stroke();
  }

  for (const token of tokens.filter((candidate) => candidate.inScene)) {
    const isLockedByOther = token.lockedBy && token.lockedBy !== playerKey;
    ctx.globalAlpha = isLockedByOther ? 0.72 : 1;
    ctx.beginPath();
    ctx.arc(token.x, token.y, token.radius, 0, Math.PI * 2);
    ctx.fillStyle = "#111827";
    ctx.fill();
    drawTokenAvatar(ctx, token, images);
    ctx.lineWidth = token.lockedBy ? 5 : 3;
    ctx.strokeStyle = "#f8fafc";
    ctx.stroke();

    ctx.globalAlpha = 1;
    if (!token.avatarUrl) {
      ctx.fillStyle = "#ffffff";
      ctx.font = "700 12px system-ui, sans-serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(token.name.slice(0, 3).toUpperCase(), token.x, token.y);
    }
  }

  if (dragPreview?.overBoard) {
    const token = tokens.find((candidate) => candidate.id === dragPreview.tokenId);
    if (token) {
      drawDropPreview(ctx, token, dragPreview.x, dragPreview.y);
    }
  }

  drawFog(ctx, fog, boardSize, fogMaskRef, isDm);
  drawBrushPreview(ctx, fog, brushPreview);
}

function drawBoardBackground(ctx: CanvasRenderingContext2D, board: Board, boardImages: Map<string, HTMLImageElement>, boardSize: BoardSize) {
  if (!board.url) return;

  const image = boardImages.get(board.url);
  if (!image?.complete || image.naturalWidth === 0) return;

  ctx.drawImage(image, 0, 0, boardSize.width, boardSize.height);
}

function drawFog(ctx: CanvasRenderingContext2D, fog: FogState, boardSize: BoardSize, fogMaskRef: MutableRefObject<FogMaskCache | null>, isDm: boolean) {
  if (!fog.hideMode) {
    fogMaskRef.current = null;
    return;
  }

  const signature = fogMaskSignature(fog, boardSize, isDm);
  const needsFullRebuild =
    !fogMaskRef.current ||
    fogMaskRef.current.canvas.width !== boardSize.width ||
    fogMaskRef.current.canvas.height !== boardSize.height ||
    fogMaskRef.current.renderedCount > fog.revealedAreas.length ||
    (fogMaskRef.current.renderedCount === fog.revealedAreas.length && fogMaskRef.current.signature !== signature);

  if (needsFullRebuild) {
    const mask = document.createElement("canvas");
    mask.width = boardSize.width;
    mask.height = boardSize.height;
    const maskCtx = mask.getContext("2d");
    if (!maskCtx) return;

    maskCtx.fillStyle = isDm ? "rgba(5, 5, 5, 0.68)" : "#050505";
    maskCtx.fillRect(0, 0, boardSize.width, boardSize.height);
    fogMaskRef.current = { canvas: mask, renderedCount: 0, signature };
  }

  const cache = fogMaskRef.current;
  if (!cache) return;

  const maskCtx = cache.canvas.getContext("2d");
  if (!maskCtx) return;

  maskCtx.globalCompositeOperation = "destination-out";
  for (const area of fog.revealedAreas.slice(cache.renderedCount)) {
    drawFogRevealArea(maskCtx, area);
  }
  maskCtx.globalCompositeOperation = "source-over";
  cache.renderedCount = fog.revealedAreas.length;
  cache.signature = signature;

  ctx.drawImage(cache.canvas, 0, 0);
}

function drawFogRevealArea(ctx: CanvasRenderingContext2D, area: { x: number; y: number; radius: number }) {
  const gradient = ctx.createRadialGradient(area.x, area.y, 0, area.x, area.y, area.radius);
  gradient.addColorStop(0, "rgba(0, 0, 0, 1)");
  gradient.addColorStop(0.72, "rgba(0, 0, 0, 1)");
  gradient.addColorStop(1, "rgba(0, 0, 0, 0)");
  ctx.fillStyle = gradient;
  ctx.beginPath();
  ctx.arc(area.x, area.y, area.radius, 0, Math.PI * 2);
  ctx.fill();
}

function fogMaskSignature(fog: FogState, boardSize: BoardSize, isDm: boolean) {
  const last = fog.revealedAreas.at(-1);
  return [boardSize.width, boardSize.height, isDm ? "dm" : "player", fog.revealedAreas.length, last?.x, last?.y, last?.radius].join(":");
}

function drawBrushPreview(ctx: CanvasRenderingContext2D, fog: FogState, brushPreview: BrushPreview | null) {
  if (!fog.hideMode || !brushPreview) return;

  ctx.save();
  ctx.beginPath();
  ctx.arc(brushPreview.x, brushPreview.y, fog.brushSize, 0, Math.PI * 2);
  ctx.fillStyle = "rgba(255, 255, 255, 0.08)";
  ctx.fill();
  ctx.lineWidth = 3;
  ctx.setLineDash([10, 8]);
  ctx.strokeStyle = "rgba(255, 255, 255, 0.95)";
  ctx.stroke();

  ctx.beginPath();
  ctx.arc(brushPreview.x, brushPreview.y, 3, 0, Math.PI * 2);
  ctx.fillStyle = "#ffffff";
  ctx.fill();
  ctx.restore();
}

function drawTokenAvatar(ctx: CanvasRenderingContext2D, token: Token, images: Map<string, HTMLImageElement>) {
  if (!token.avatarUrl) return;

  const image = images.get(token.avatarUrl);
  if (!image?.complete || image.naturalWidth === 0) return;

  ctx.save();
  ctx.beginPath();
  ctx.arc(token.x, token.y, token.radius - 2, 0, Math.PI * 2);
  ctx.clip();

  const sourceSize = Math.min(image.naturalWidth, image.naturalHeight);
  const sourceX = (image.naturalWidth - sourceSize) / 2;
  const sourceY = (image.naturalHeight - sourceSize) / 2;
  const targetSize = token.radius * 2 - 4;
  ctx.drawImage(
    image,
    sourceX,
    sourceY,
    sourceSize,
    sourceSize,
    token.x - targetSize / 2,
    token.y - targetSize / 2,
    targetSize,
    targetSize
  );
  ctx.restore();
}

function drawDropPreview(CanvasContext: CanvasRenderingContext2D, token: Token, x: number, y: number) {
  const ctx = CanvasContext;
  ctx.save();
  ctx.globalAlpha = 0.92;
  ctx.beginPath();
  ctx.arc(x, y, token.radius + 7, 0, Math.PI * 2);
  ctx.fillStyle = "rgba(255, 255, 255, 0.18)";
  ctx.fill();
  ctx.lineWidth = 3;
  ctx.setLineDash([8, 7]);
  ctx.strokeStyle = "#ffffff";
  ctx.stroke();

  ctx.beginPath();
  ctx.arc(x, y, 4, 0, Math.PI * 2);
  ctx.fillStyle = "#111827";
  ctx.fill();
  ctx.restore();
}

function canvasPoint(event: React.PointerEvent<HTMLCanvasElement>, boardSize: BoardSize) {
  return clientPointToCanvas(event.currentTarget, event.clientX, event.clientY, boardSize);
}

function clientPointToCanvas(canvas: HTMLCanvasElement, clientX: number, clientY: number, boardSize: BoardSize) {
  const rect = canvas.getBoundingClientRect();
  return {
    x: ((clientX - rect.left) / rect.width) * boardSize.width,
    y: ((clientY - rect.top) / rect.height) * boardSize.height
  };
}

function isPointInsideCanvas(event: React.PointerEvent<HTMLCanvasElement>) {
  return isClientPointInsideCanvas(event.currentTarget, event.clientX, event.clientY);
}

function isClientPointInsideCanvas(canvas: HTMLCanvasElement, clientX: number, clientY: number) {
  const rect = canvas.getBoundingClientRect();
  return clientX >= rect.left && clientX <= rect.right && clientY >= rect.top && clientY <= rect.bottom;
}

function getBoardSize(board: Board): BoardSize {
  return {
    width: positiveNumberOrDefault(board.width, DEFAULT_BOARD_WIDTH),
    height: positiveNumberOrDefault(board.height, DEFAULT_BOARD_HEIGHT)
  };
}

function positiveNumberOrDefault(value: number, fallback: number) {
  return Number.isFinite(value) && value > 0 ? value : fallback;
}

function reconcilePendingTokenRadius(token: Token, pendingRadii: Map<string, number>) {
  const pendingRadius = pendingRadii.get(token.id);
  if (pendingRadius === undefined) return token;

  if (Math.abs(token.radius - pendingRadius) < 0.001) {
    pendingRadii.delete(token.id);
    return token;
  }

  return { ...token, radius: pendingRadius };
}

function requestTokenLockMessage(tokenId: string, tokens: Token[], pendingRadii: Map<string, number>, isDm: boolean) {
  return withDmTokenRadius({ type: "request_token_lock", tokenId }, tokenId, tokens, pendingRadii, isDm);
}

function moveTokenMessage(tokenId: string, x: number, y: number, tokens: Token[], pendingRadii: Map<string, number>, isDm: boolean) {
  return withDmTokenRadius({ type: "move_token", tokenId, x, y }, tokenId, tokens, pendingRadii, isDm);
}

function setTokenSceneMessage(tokenId: string, inScene: boolean, x: number, y: number, tokens: Token[], pendingRadii: Map<string, number>, isDm: boolean) {
  return withDmTokenRadius({ type: "set_token_scene", tokenId, inScene, x, y }, tokenId, tokens, pendingRadii, isDm);
}

async function updateTokenRadius(tokenId: string, radius: number, playerKey: string) {
  const roomId = getInitialRoomId();
  const params = new URLSearchParams({
    playerKey,
    radius: String(radius)
  });
  const response = await fetch(`/api/rooms/${encodeURIComponent(roomId)}/tokens/${encodeURIComponent(tokenId)}/radius?${params}`, {
    method: "POST"
  });

  if (!response.ok) {
    throw new Error(await response.text());
  }
}

function withDmTokenRadius<T extends { tokenId: string }>(message: T, tokenId: string, tokens: Token[], pendingRadii: Map<string, number>, isDm: boolean) {
  if (!isDm) return message;

  const pendingRadius = pendingRadii.get(tokenId);
  if (pendingRadius !== undefined) return { ...message, radius: pendingRadius };

  const token = tokens.find((candidate) => candidate.id === tokenId);
  return token ? { ...message, radius: token.radius } : message;
}

function getMaxTokenRadius(boardSize: BoardSize) {
  return Math.min(MAX_TOKEN_RADIUS, Math.max(MIN_TOKEN_RADIUS, Math.floor(Math.min(boardSize.width, boardSize.height) / 3)));
}

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max);
}

function hitToken(token: Token, x: number, y: number) {
  return Math.hypot(token.x - x, token.y - y) <= token.radius;
}

function upsertToken(tokens: Token[], token: Token) {
  const index = tokens.findIndex((candidate) => candidate.id === token.id);
  if (index === -1) return [...tokens, token];

  const next = [...tokens];
  next[index] = token;
  return next;
}

function upsertPendingRoll(rolls: RollPayload[], roll: RollPayload) {
  return [roll, ...rolls.filter((candidate) => rollKey(candidate) !== rollKey(roll))];
}

function appendRollLogEntry(entries: RollLogEntry[], entry: RollLogEntry) {
  return [...entries.filter((candidate) => candidate.id !== entry.id), entry].slice(-ROLL_HISTORY_LIMIT);
}

function applyResolvedRollToSheetState(sheets: CharacterSheet[], resolution: NonNullable<RollLogEntry["resolution"]>) {
  return sheets.map((sheet) =>
    sheet.id === resolution.targetSheetId ? { ...sheet, hp: resolution.targetHp, conditions: resolution.targetConditions } : sheet
  );
}

function rollKey(roll: RollPayload) {
  return `${roll.tokenId}:${roll.source.section}:${roll.source.sourceId}:${roll.source.actionId}`;
}

function rollMatchesSource(roll: RollPayload, section: SheetSectionType, sourceId: string) {
  return roll.source.section === section && roll.source.sourceId === sourceId;
}

function rollMatchesSourceAction(roll: RollPayload, section: SheetSectionType, sourceId: string, actionId: string) {
  return rollMatchesSource(roll, section, sourceId) && roll.source.actionId === actionId;
}

function cardResolvedRolls(sheet: CharacterSheet, rollHistory: RollLogEntry[], clearedCardRollIds: Set<string>) {
  return rollHistory
    .filter(
      (entry) =>
        entry.resolution &&
        entry.roll.resolution === RollResolutionMode.HEAL_SELF &&
        entry.roll.tokenId === sheet.tokenId &&
        entry.resolution.targetSheetId === sheet.id &&
        !clearedCardRollIds.has(entry.id)
    )
    .slice(-2)
    .reverse();
}

function isTargetableRoll(roll: RollPayload | undefined) {
  if (!roll) return false;
  if (
    roll.resolution === RollResolutionMode.ATTACK_VS_ARMOR_CLASS ||
    roll.resolution === RollResolutionMode.APPLY_DAMAGE ||
    roll.resolution === RollResolutionMode.APPLY_TEMPORARY_HIT_POINTS
  ) {
    return true;
  }
  return (roll.conditionEffects ?? []).some((effect) => effect.mode === "targetSave" || effect.mode === "sourceCheck" || effect.mode === "direct");
}

function hasDamageDefenses(sheet: CharacterSheet) {
  return sheet.damageResistances.length > 0 || sheet.damageVulnerabilities.length > 0 || sheet.damageImmunities.length > 0;
}

function getInitialRoute(): InitialRoute {
  const params = new URLSearchParams(window.location.search);
  const pathParts = window.location.pathname.split("/").filter(Boolean);
  const pathView = pathParts.at(-1);
  const pathPlayer = pathParts.find((part) => part.startsWith("player="))?.slice("player=".length);
  const pathCampaign = pathParts[0] && !pathParts[0].startsWith("player=") && pathParts[0] !== "sheet" && pathParts[0] !== "board" ? pathParts[0] : null;

  return {
    roomId: params.get("campaign") || params.get("room") || pathCampaign || "test-campaign",
    playerKey: normalizeRequestedPlayerKey(params.get("player") || pathPlayer || ""),
    view: pathView === "sheet" || pathParts[0] === "sheet" ? "sheet" : "board"
  };
}

function getInitialRoomId() {
  return INITIAL_ROUTE.roomId;
}

function routePath(roomId: string, player: string, view: AppView) {
  const basePath = `/${encodeURIComponent(roomId)}/player=${encodeURIComponent(player)}`;
  if (view === "sheet") {
    return `${basePath}/sheet`;
  }
  return basePath;
}

function normalizeRequestedPlayerKey(value: string) {
  const params = new URLSearchParams(window.location.search);
  const dm = params.get("dm")?.trim().toLowerCase();
  if (dm === "1" || dm === "true") return "dm";

  const player = value.trim().toLowerCase();
  if (player === "dm") return "dm";
  if (player && /^player-[1-8]$/.test(player)) return player;
  if (player && /^[1-8]$/.test(player)) return `player-${player}`;
  return player || "player-1";
}

function resolvePlayerKey(requestedPlayerKey: string, tokens: Token[]) {
  if (requestedPlayerKey === "dm") return "dm";
  if (isPlayerSlot(requestedPlayerKey)) return requestedPlayerKey;
  if (tokens.some((token) => token.owner === requestedPlayerKey)) return requestedPlayerKey;

  const normalized = normalizeIdentity(requestedPlayerKey);
  const matchingToken = tokens.find((token) => token.kind === TokenKind.CHARACTER && normalizeIdentity(token.name) === normalized);
  return matchingToken?.owner ?? "player-1";
}

function playerUrlValue(playerKey: string, tokens: Token[]) {
  if (playerKey === "dm") return "dm";
  return tokens.find((token) => token.kind === TokenKind.CHARACTER && token.owner === playerKey)?.name ?? playerKey;
}

function shouldShowCharacterBuilder(isDm: boolean, playerKey: string, sheets: CharacterSheet[]) {
  const occupiedSheets = sheets.filter(isPlayerSlotSheet);
  if (occupiedSheets.length >= 8) return false;
  if (isDm) return true;
  if (!isPlayerSlot(playerKey)) return false;
  return !occupiedSheets.some((sheet) => sheet.id === playerKey || sheet.owner === playerKey);
}

function characterBuilderMemberOptions(isDm: boolean, playerKey: string, sheets: CharacterSheet[]) {
  const occupiedSheets = sheets.filter(isPlayerSlotSheet);
  if (!isDm) {
    return isPlayerSlot(playerKey) && !occupiedSheets.some((sheet) => sheet.id === playerKey || sheet.owner === playerKey)
      ? [{ value: playerKey, label: formatPlayerName(playerKey, []) }]
      : [];
  }
  return Array.from({ length: 8 }, (_value, index) => {
    const value = `player-${index + 1}`;
    return occupiedSheets.some((sheet) => sheet.id === value || sheet.owner === value) ? null : { value, label: value };
  }).filter((option): option is { value: string; label: string } => option !== null);
}

function isPlayerSlotSheet(sheet: CharacterSheet) {
  return isPlayerSlot(sheet.id) || isPlayerSlot(sheet.owner);
}

function isPlayerSlot(playerKey: string) {
  return /^player-[1-8]$/.test(playerKey);
}

function formatPlayerName(playerKey: string, tokens: Token[] = []) {
  if (playerKey === "dm") return "DM";
  return tokens.find((token) => token.kind === TokenKind.CHARACTER && token.owner === playerKey)?.name ?? playerKey.replace("-", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatHp(hp: CharacterSheet["hp"]) {
  return `${hp.current + hp.temporary}/${hp.max}`;
}

function normalizeIdentity(value: string) {
  return value.trim().toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
}

function canControlToken(token: Token, playerKey: string, isDm: boolean) {
  return isDm || token.owner === playerKey;
}

function canRollSheet(sheet: CharacterSheet, playerKey: string, isDm: boolean) {
  return isDm || sheet.owner === playerKey;
}

function formatSigned(value: number) {
  return value >= 0 ? `+${value}` : String(value);
}

function rollMathText(roll: RollPayload) {
  const dice = roll.dice.join("+");
  const modifierParts = (roll.modifierBreakdown ?? []).filter((part) => part.value !== 0);
  const modifiers = modifierParts.length
    ? modifierParts.map((part) => `${part.value >= 0 ? "+" : "-"} ${part.source} (${Math.abs(part.value)})`).join(" ")
    : formatSigned(roll.modifier);
  return `${dice} ${modifiers} = ${roll.total}`;
}

function diceImagePath(diceType: RollPayload["diceType"]) {
  return `/${diceType}.png`;
}

function formatLogTime(entry: RollLogEntry) {
  return logEntryDate(entry).toLocaleTimeString([], { hour: "numeric", minute: "2-digit", second: "2-digit" });
}

function logEntryDate(entry: RollLogEntry) {
  return new Date(Math.floor(entry.createdAt / 1_000_000));
}

function equipmentSlotOptions(itemType: CharacterSheet["equipment"][number]["itemType"]): EquipmentSlot[] {
  if (itemType === "armor") return ["carried", "armor"];
  if (itemType === "shield") return ["carried", "mainHand", "offHand"];
  if (itemType === "weapon") return ["carried", "mainHand", "offHand", "twoHands"];
  return ["carried"];
}

function hasPurseCoins(sheet: CharacterSheet) {
  return sheet.purse.gold > 0 || sheet.purse.silver > 0 || sheet.purse.copper > 0;
}

function shortAbilityName(ability: string) {
  return ability.slice(0, 3).toUpperCase();
}

function cleanName(identifier: string) {
  return identifier.replace(/([A-Z])/g, " $1").replace(/[-_]/g, " ").replace(/\b\w/g, (match) => match.toUpperCase()).trim();
}

function assetKey(asset: Asset | undefined) {
  return asset ? `${asset.kind}:${asset.id}` : "";
}

function filterAssets(assets: Asset[], search: string) {
  const normalizedSearch = search.trim().toLowerCase();
  if (!normalizedSearch) return assets;
  return assets.filter((asset) => `${asset.name} ${asset.id}`.toLowerCase().includes(normalizedSearch));
}

function clearTextSelection() {
  window.getSelection()?.removeAllRanges();
}

function getDefaultWebSocketUrl() {
  if (import.meta.env.DEV) {
    return "ws://localhost:8000/ws";
  }

  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}/ws`;
}
