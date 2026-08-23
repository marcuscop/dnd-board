import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { CSSProperties, MutableRefObject } from "react";
import type { Asset, Board, FogState, PlayerSummary, ServerMessage, Token } from "./types";

const DEFAULT_BOARD_WIDTH = 1200;
const DEFAULT_BOARD_HEIGHT = 720;
const MOVE_FPS = 12;
const FOG_PAINT_FPS = 16;
const FOG_MIN_POINT_DISTANCE = 8;
const MIN_TOKEN_RADIUS = 8;
const MAX_TOKEN_RADIUS = 480;
const WS_URL = import.meta.env.VITE_WS_URL ?? getDefaultWebSocketUrl();
const REQUESTED_PLAYER_KEY = getInitialPlayerKey();
const DEFAULT_FOG: FogState = { hideMode: false, brushSize: 120, revealedAreas: [] };
const DEFAULT_BOARD: Board = { id: "green", name: "Green Field", width: DEFAULT_BOARD_WIDTH, height: DEFAULT_BOARD_HEIGHT };

type ConnectionState = "connecting" | "connected" | "disconnected";
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
  const [boards, setBoards] = useState<Board[]>([DEFAULT_BOARD]);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [selectedAssetKey, setSelectedAssetKey] = useState("");
  const [assetSearch, setAssetSearch] = useState("");
  const [isPaintingFog, setIsPaintingFog] = useState(false);
  const [revealToolEnabled, setRevealToolEnabled] = useState(false);
  const [brushPreview, setBrushPreview] = useState<BrushPreview | null>(null);
  const [dragGhost, setDragGhost] = useState<DragGhost | null>(null);
  const [playerKey, setPlayerKey] = useState(REQUESTED_PLAYER_KEY);
  const isDm = playerKey === "dm";

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
  const partyTokens = useMemo(() => tokens.filter((token) => token.kind === "character"), [tokens]);
  const npcTokens = useMemo(() => tokens.filter((token) => token.kind === "npc"), [tokens]);
  const monsterTokens = useMemo(() => tokens.filter((token) => token.kind === "monster"), [tokens]);
  const filteredAssets = useMemo(() => filterAssets(assets, assetSearch), [assets, assetSearch]);
  const visibleSelectedAssetKey = filteredAssets.some((asset) => assetKey(asset) === selectedAssetKey) ? selectedAssetKey : assetKey(filteredAssets[0]);

  const applyRoomState = useCallback((message: Extract<ServerMessage, { type: "room_state" }>) => {
    const resolvedPlayerKey = resolvePlayerKey(REQUESTED_PLAYER_KEY, message.tokens);
    setPlayerKey(resolvedPlayerKey);
    window.history.replaceState(null, "", `?campaign=${message.roomId}&player=${playerUrlValue(resolvedPlayerKey, message.tokens)}`);
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
      setConnection("connected");
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

      if (message.type === "player_count") {
        setPlayers((current) => current.slice(0, message.count));
      }
    });

    return () => socket.close();
  }, [applyRoomState]);

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

    const intervalId = window.setInterval(syncRoomState, 1500);
    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, [applyRoomState]);

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
      if (!isDm || token.kind === "character") return;
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
                        {asset.kind.toUpperCase()} · {asset.name}
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

        {npcTokens.length > 0 && (
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
            title="NPCs"
            tokens={npcTokens}
          />
        )}

        {monsterTokens.length > 0 && (
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
            title="Monsters"
            tokens={monsterTokens}
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

function DragGhostToken({ token, x, y }: { token: Token | undefined; x: number; y: number }) {
  if (!token) return null;

  return (
    <div className="drag-ghost" style={{ background: token.color, left: x, top: y }}>
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
              style={{ background: token.color }}
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
            {isDm && token.kind !== "character" && (
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
    ctx.fillStyle = token.color;
    ctx.fill();
    drawTokenAvatar(ctx, token, images);
    ctx.lineWidth = token.lockedBy ? 5 : 3;
    ctx.strokeStyle = "#f8fafc";
    ctx.stroke();

    ctx.globalAlpha = 1;
    if (!token.avatarUrl) {
      ctx.fillStyle = token.color === "#f8fafc" ? "#111827" : "#ffffff";
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
  ctx.fillStyle = "#2f7d46";
  ctx.fillRect(0, 0, boardSize.width, boardSize.height);

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

function getInitialRoomId() {
  const params = new URLSearchParams(window.location.search);
  return params.get("campaign") || params.get("room") || "test-campaign";
}

function getInitialPlayerName() {
  return localStorage.getItem("dnd-board-name") || `Player ${Math.floor(Math.random() * 90 + 10)}`;
}

function getInitialPlayerKey() {
  const params = new URLSearchParams(window.location.search);
  const dm = params.get("dm")?.trim().toLowerCase();
  if (dm === "1" || dm === "true") return "dm";

  const player = params.get("player")?.trim().toLowerCase();
  if (player === "dm") return "dm";
  if (player && /^player-[1-4]$/.test(player)) return player;
  if (player && /^[1-4]$/.test(player)) return `player-${player}`;
  return player || "player-1";
}

function resolvePlayerKey(requestedPlayerKey: string, tokens: Token[]) {
  if (requestedPlayerKey === "dm") return "dm";
  if (tokens.some((token) => token.owner === requestedPlayerKey)) return requestedPlayerKey;

  const normalized = normalizeIdentity(requestedPlayerKey);
  const matchingToken = tokens.find((token) => token.kind === "character" && normalizeIdentity(token.name) === normalized);
  return matchingToken?.owner ?? "player-1";
}

function playerUrlValue(playerKey: string, tokens: Token[]) {
  if (playerKey === "dm") return "dm";
  return tokens.find((token) => token.kind === "character" && token.owner === playerKey)?.name ?? playerKey;
}

function formatPlayerName(playerKey: string, tokens: Token[] = []) {
  if (playerKey === "dm") return "DM";
  return tokens.find((token) => token.kind === "character" && token.owner === playerKey)?.name ?? playerKey.replace("-", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function normalizeIdentity(value: string) {
  return value.trim().toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
}

function canControlToken(token: Token, playerKey: string, isDm: boolean) {
  return isDm || token.owner === playerKey;
}

function assetKey(asset: Asset | undefined) {
  return asset ? `${asset.kind}:${asset.id}` : "";
}

function filterAssets(assets: Asset[], search: string) {
  const normalizedSearch = search.trim().toLowerCase();
  if (!normalizedSearch) return assets;
  return assets.filter((asset) => `${asset.kind} ${asset.name} ${asset.id}`.toLowerCase().includes(normalizedSearch));
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
