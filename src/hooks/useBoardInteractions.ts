import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { CSSProperties, Dispatch, MutableRefObject, PointerEvent, SetStateAction } from "react";

import {
  MIN_TOKEN_RADIUS,
  canControlToken,
  canvasPoint,
  clamp,
  clientPointToCanvas,
  drawBoard,
  getBoardSize,
  getMaxTokenRadius,
  hitToken,
  isClientPointInsideCanvas,
  isPointInsideCanvas,
  moveTokenMessage,
  requestTokenLockMessage,
  setTokenSceneMessage,
  updateTokenRadius
} from "../board/boardRendering";
import type { BrushPreview, DragPreview, FogMaskCache } from "../board/boardRendering";
import { TokenKind } from "../types";
import type { Asset, Board, FogState, Token } from "../types";

const MOVE_FPS = 12;
const FOG_PAINT_FPS = 16;
const FOG_MIN_POINT_DISTANCE = 8;

type DragGhost = { tokenId: string; clientX: number; clientY: number };
type Send = (message: unknown) => void;

type BoardInteractionOptions = {
  roomId: string;
  playerKey: string;
  isDm: boolean;
  assets: Asset[];
  board: Board;
  fog: FogState;
  tokens: Token[];
  send: Send;
  setTokens: Dispatch<SetStateAction<Token[]>>;
  pendingTokenRadiiRef: MutableRefObject<Map<string, number>>;
};

export function useBoardInteractions(options: BoardInteractionOptions) {
  const { roomId, playerKey, isDm, assets, board, fog, tokens, send, setTokens, pendingTokenRadiiRef } = options;
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const imagesRef = useRef<Map<string, HTMLImageElement>>(new Map());
  const boardImagesRef = useRef<Map<string, HTMLImageElement>>(new Map());
  const fogMaskRef = useRef<FogMaskCache | null>(null);
  const canvasHoverRef = useRef<BrushPreview | null>(null);
  const dragRef = useRef<{ tokenId: string; lastSentAt: number } | null>(null);
  const fogPaintRef = useRef<{ lastSentAt: number; lastX: number; lastY: number; radius: number } | null>(null);
  const pendingResizeRequestsRef = useRef<Set<Promise<void>>>(new Set());
  const [dragPreview, setDragPreview] = useState<DragPreview | null>(null);
  const [dragGhost, setDragGhost] = useState<DragGhost | null>(null);
  const [isPaintingFog, setIsPaintingFog] = useState(false);
  const [revealToolEnabled, setRevealToolEnabled] = useState(false);
  const [brushPreview, setBrushPreview] = useState<BrushPreview | null>(null);
  const [selectedAssetKey, setSelectedAssetKey] = useState("");
  const [assetSearch, setAssetSearch] = useState("");
  const [saveStatus, setSaveStatus] = useState<"idle" | "saving" | "saved" | "error">("idle");
  const [loadStatus, setLoadStatus] = useState<"idle" | "loading" | "loaded" | "error">("idle");

  const boardSize = useMemo(() => getBoardSize(board), [board]);
  const maxTokenRadius = useMemo(() => getMaxTokenRadius(boardSize), [boardSize]);
  const boardCanvasStyle = useMemo(() => ({
    "--board-aspect-ratio": String(boardSize.width / boardSize.height),
    aspectRatio: `${boardSize.width} / ${boardSize.height}`
  }) as CSSProperties, [boardSize]);
  const partyTokens = useMemo(() => tokens.filter((token) => token.kind === TokenKind.CHARACTER), [tokens]);
  const otherTokens = useMemo(() => tokens.filter((token) => token.kind !== TokenKind.CHARACTER), [tokens]);
  const filteredAssets = useMemo(() => filterAssets(assets, assetSearch), [assets, assetSearch]);
  const visibleSelectedAssetKey = filteredAssets.some((asset) => assetKey(asset) === selectedAssetKey)
    ? selectedAssetKey
    : assetKey(filteredAssets[0]);
  const ownLockedTokenId = useMemo(() => tokens.find((token) => token.lockedBy === playerKey)?.id, [playerKey, tokens]);

  const redraw = useCallback(() => drawBoard(
    canvasRef.current, tokens, playerKey, isDm, dragPreview, imagesRef.current, fog,
    revealToolEnabled ? brushPreview : null, board, boardImagesRef.current, fogMaskRef, boardSize
  ), [board, boardSize, brushPreview, dragPreview, fog, isDm, playerKey, revealToolEnabled, tokens]);

  useEffect(redraw, [redraw]);
  useEffect(() => {
    for (const token of tokens) {
      if (!token.avatarUrl || imagesRef.current.has(token.avatarUrl)) continue;
      const image = new Image();
      image.onload = redraw;
      image.src = token.avatarUrl;
      imagesRef.current.set(token.avatarUrl, image);
    }
  }, [redraw, tokens]);
  useEffect(() => {
    if (!board.url || boardImagesRef.current.has(board.url)) return;
    const image = new Image();
    image.onload = redraw;
    image.src = board.url;
    boardImagesRef.current.set(board.url, image);
  }, [board.url, redraw]);
  useEffect(() => {
    if (!fog.hideMode) {
      setRevealToolEnabled(false);
      setBrushPreview(null);
    }
  }, [fog.hideMode]);
  useEffect(() => {
    if (visibleSelectedAssetKey && visibleSelectedAssetKey !== selectedAssetKey) setSelectedAssetKey(visibleSelectedAssetKey);
  }, [selectedAssetKey, visibleSelectedAssetKey]);

  const sendRevealPoint = useCallback((point: BrushPreview, force = false) => {
    const now = performance.now();
    const last = fogPaintRef.current;
    const minimumDistance = Math.max(FOG_MIN_POINT_DISTANCE, fog.brushSize * 0.22);
    const farEnough = !last || Math.hypot(point.x - last.lastX, point.y - last.lastY) >= minimumDistance || last.radius !== fog.brushSize;
    const lateEnough = !last || now - last.lastSentAt >= 1000 / FOG_PAINT_FPS;
    if (!force && (!farEnough || !lateEnough)) return;
    fogPaintRef.current = { lastSentAt: now, lastX: point.x, lastY: point.y, radius: fog.brushSize };
    send({ type: "reveal_fog", x: point.x, y: point.y, radius: fog.brushSize });
  }, [fog.brushSize, send]);

  const onBoardPointerDown = useCallback((event: PointerEvent<HTMLCanvasElement>) => {
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
  }, [boardSize, fog.hideMode, isDm, playerKey, revealToolEnabled, send, sendRevealPoint, tokens, pendingTokenRadiiRef]);

  const onBoardPointerMove = useCallback((event: PointerEvent<HTMLCanvasElement>) => {
    const drag = dragRef.current;
    const point = canvasPoint(event, boardSize);
    const overBoard = isPointInsideCanvas(event);
    canvasHoverRef.current = overBoard ? point : null;
    if (isDm && fog.hideMode && revealToolEnabled && overBoard) setBrushPreview(point);
    if (isDm && isPaintingFog) {
      if (overBoard) sendRevealPoint(point);
      return;
    }
    if (!drag) return;
    const now = performance.now();
    if (now - drag.lastSentAt < 1000 / MOVE_FPS) return;
    drag.lastSentAt = now;
    setDragPreview({ tokenId: drag.tokenId, x: point.x, y: point.y, overBoard });
    if (overBoard) send(moveTokenMessage(drag.tokenId, point.x, point.y, tokens, pendingTokenRadiiRef.current, isDm));
  }, [boardSize, fog.hideMode, isDm, isPaintingFog, revealToolEnabled, send, sendRevealPoint, tokens, pendingTokenRadiiRef]);

  const onBoardPointerUp = useCallback((event: PointerEvent<HTMLCanvasElement>) => {
    const drag = dragRef.current;
    if (isDm && isPaintingFog) {
      if (isPointInsideCanvas(event)) sendRevealPoint(canvasPoint(event, boardSize), true);
      fogPaintRef.current = null;
      setIsPaintingFog(false);
      return;
    }
    if (!drag) return;
    if (isPointInsideCanvas(event)) {
      const point = canvasPoint(event, boardSize);
      send(moveTokenMessage(drag.tokenId, point.x, point.y, tokens, pendingTokenRadiiRef.current, isDm));
      send(setTokenSceneMessage(drag.tokenId, true, point.x, point.y, tokens, pendingTokenRadiiRef.current, isDm));
    } else send({ type: "set_token_scene", tokenId: drag.tokenId, inScene: false });
    send({ type: "release_token", tokenId: drag.tokenId });
    clearDrag();
  }, [boardSize, isDm, isPaintingFog, send, sendRevealPoint, tokens, pendingTokenRadiiRef]);

  const onSidebarPointerDown = useCallback((event: PointerEvent<HTMLElement>, token: Token) => {
    event.preventDefault();
    clearTextSelection();
    if (!canControlToken(token, playerKey, isDm) || (token.lockedBy && token.lockedBy !== playerKey)) return;
    event.currentTarget.setPointerCapture(event.pointerId);
    dragRef.current = { tokenId: token.id, lastSentAt: 0 };
    setDragGhost({ tokenId: token.id, clientX: event.clientX, clientY: event.clientY });
    setDragPreview({ tokenId: token.id, x: token.x, y: token.y, overBoard: false });
    send(requestTokenLockMessage(token.id, tokens, pendingTokenRadiiRef.current, isDm));
  }, [isDm, playerKey, send, tokens, pendingTokenRadiiRef]);

  const onSidebarPointerMove = useCallback((event: PointerEvent<HTMLElement>) => {
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
      setDragPreview((current) => current ? { ...current, overBoard: false } : current);
      return;
    }
    const point = clientPointToCanvas(canvas, event.clientX, event.clientY, boardSize);
    setDragPreview({ tokenId: drag.tokenId, x: point.x, y: point.y, overBoard: true });
    send(moveTokenMessage(drag.tokenId, point.x, point.y, tokens, pendingTokenRadiiRef.current, isDm));
  }, [boardSize, isDm, send, tokens, pendingTokenRadiiRef]);

  const onSidebarPointerUp = useCallback((event: PointerEvent<HTMLElement>) => {
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
    clearDrag();
  }, [boardSize, isDm, send, tokens, pendingTokenRadiiRef]);

  function clearDrag() {
    dragRef.current = null;
    setDragPreview(null);
    setDragGhost(null);
  }

  const saveRoom = useCallback(async () => {
    setSaveStatus("saving");
    while (pendingResizeRequestsRef.current.size > 0) await Promise.all([...pendingResizeRequestsRef.current]);
    const response = await fetch(`/api/rooms/${encodeURIComponent(roomId)}/save?playerKey=${encodeURIComponent(playerKey)}`, { method: "POST" });
    setSaveStatus(response.ok ? "saved" : "error");
    window.setTimeout(() => setSaveStatus("idle"), 1800);
  }, [playerKey, roomId]);

  const loadRoom = useCallback(async () => {
    setLoadStatus("loading");
    const response = await fetch(`/api/rooms/${encodeURIComponent(roomId)}/load?playerKey=${encodeURIComponent(playerKey)}`, { method: "POST" });
    setLoadStatus(response.ok ? "loaded" : "error");
    window.setTimeout(() => setLoadStatus("idle"), 1800);
  }, [playerKey, roomId]);

  const setTokenRadius = useCallback((token: Token, radius: number) => {
    if (!isDm) return;
    const nextRadius = clamp(radius, MIN_TOKEN_RADIUS, maxTokenRadius);
    pendingTokenRadiiRef.current.set(token.id, nextRadius);
    setTokens((current) => current.map((candidate) => candidate.id === token.id ? { ...candidate, radius: nextRadius } : candidate));
    const request = updateTokenRadius(roomId, token.id, nextRadius, playerKey)
      .catch(console.error)
      .finally(() => pendingResizeRequestsRef.current.delete(request));
    pendingResizeRequestsRef.current.add(request);
  }, [isDm, maxTokenRadius, pendingTokenRadiiRef, playerKey, roomId, setTokens]);

  return {
    assetSearch, boardCanvasStyle, boardSize, brushPreview, canvasRef, dragGhost, dragPreview,
    filteredAssets, loadRoom, loadStatus, maxTokenRadius, ownLockedTokenId, otherTokens,
    partyTokens, revealToolEnabled, saveRoom, saveStatus, selectedAssetKey: visibleSelectedAssetKey,
    onSearchAssets: setAssetSearch, setTokenRadius,
    onBoardPointerDown, onBoardPointerMove, onBoardPointerUp,
    onCanvasEnter: (point: BrushPreview) => {
      canvasHoverRef.current = point;
      if (isDm && fog.hideMode && revealToolEnabled) setBrushPreview(point);
    },
    onCanvasLeave: () => { canvasHoverRef.current = null; setBrushPreview(null); },
    onClearScene: () => {
      if (!isDm) return;
      clearDrag();
      setTokens((current) => current.map((token) => ({ ...token, inScene: false, lockedBy: undefined })));
      send({ type: "clear_scene" });
    },
    onDeleteToken: (token: Token) => {
      if (isDm && token.kind !== TokenKind.CHARACTER) send({ type: "delete_token", tokenId: token.id });
    },
    onLoadSelectedAsset: () => {
      const asset = assets.find((candidate) => assetKey(candidate) === visibleSelectedAssetKey);
      if (asset) send({ type: "load_asset", assetKind: asset.kind, assetId: asset.id });
    },
    onSelectAsset: setSelectedAssetKey,
    onSelectBoard: (boardId: string) => send({ type: "set_board", boardId }),
    onSetBrushSize: (brushSize: number) => send({ type: "set_fog_mode", hideMode: fog.hideMode, brushSize }),
    onSetHideMode: (hideMode: boolean) => send({ type: "set_fog_mode", hideMode, brushSize: fog.brushSize }),
    onSetRevealTool: (enabled: boolean) => {
      setRevealToolEnabled(enabled);
      if (enabled && canvasHoverRef.current) setBrushPreview(canvasHoverRef.current);
      if (!enabled) setBrushPreview(null);
    },
    onSidebarPointerDown, onSidebarPointerMove, onSidebarPointerUp
  };
}

function assetKey(asset: Asset | undefined) {
  return asset ? `${asset.kind}:${asset.id}` : "";
}

function filterAssets(assets: Asset[], search: string) {
  const normalized = search.trim().toLowerCase();
  return normalized ? assets.filter((asset) => `${asset.name} ${asset.id}`.toLowerCase().includes(normalized)) : assets;
}

function clearTextSelection() {
  window.getSelection()?.removeAllRanges();
}
