import type { MutableRefObject, PointerEvent } from "react";
import type { Board, FogState, Token } from "../types";

export const DEFAULT_BOARD_WIDTH = 1200;
export const DEFAULT_BOARD_HEIGHT = 720;
export const MIN_TOKEN_RADIUS = 8;
export const MAX_TOKEN_RADIUS = 480;

export type DragPreview = {
  tokenId: string;
  x: number;
  y: number;
  overBoard: boolean;
};

export type BrushPreview = {
  x: number;
  y: number;
};

export type BoardSize = {
  width: number;
  height: number;
};

export type FogMaskCache = {
  canvas: HTMLCanvasElement;
  renderedCount: number;
  signature: string;
};

export function drawBoard(
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

export function drawBoardBackground(ctx: CanvasRenderingContext2D, board: Board, boardImages: Map<string, HTMLImageElement>, boardSize: BoardSize) {
  if (!board.url) return;

  const image = boardImages.get(board.url);
  if (!image?.complete || image.naturalWidth === 0) return;

  ctx.drawImage(image, 0, 0, boardSize.width, boardSize.height);
}

export function drawFog(ctx: CanvasRenderingContext2D, fog: FogState, boardSize: BoardSize, fogMaskRef: MutableRefObject<FogMaskCache | null>, isDm: boolean) {
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

export function drawFogRevealArea(ctx: CanvasRenderingContext2D, area: { x: number; y: number; radius: number }) {
  const gradient = ctx.createRadialGradient(area.x, area.y, 0, area.x, area.y, area.radius);
  gradient.addColorStop(0, "rgba(0, 0, 0, 1)");
  gradient.addColorStop(0.72, "rgba(0, 0, 0, 1)");
  gradient.addColorStop(1, "rgba(0, 0, 0, 0)");
  ctx.fillStyle = gradient;
  ctx.beginPath();
  ctx.arc(area.x, area.y, area.radius, 0, Math.PI * 2);
  ctx.fill();
}

export function fogMaskSignature(fog: FogState, boardSize: BoardSize, isDm: boolean) {
  const last = fog.revealedAreas.at(-1);
  return [boardSize.width, boardSize.height, isDm ? "dm" : "player", fog.revealedAreas.length, last?.x, last?.y, last?.radius].join(":");
}

export function drawBrushPreview(ctx: CanvasRenderingContext2D, fog: FogState, brushPreview: BrushPreview | null) {
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

export function drawTokenAvatar(ctx: CanvasRenderingContext2D, token: Token, images: Map<string, HTMLImageElement>) {
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

export function drawDropPreview(CanvasContext: CanvasRenderingContext2D, token: Token, x: number, y: number) {
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

export function canvasPoint(event: PointerEvent<HTMLCanvasElement>, boardSize: BoardSize) {
  return clientPointToCanvas(event.currentTarget, event.clientX, event.clientY, boardSize);
}

export function clientPointToCanvas(canvas: HTMLCanvasElement, clientX: number, clientY: number, boardSize: BoardSize) {
  const rect = canvas.getBoundingClientRect();
  return {
    x: ((clientX - rect.left) / rect.width) * boardSize.width,
    y: ((clientY - rect.top) / rect.height) * boardSize.height
  };
}

export function isPointInsideCanvas(event: PointerEvent<HTMLCanvasElement>) {
  return isClientPointInsideCanvas(event.currentTarget, event.clientX, event.clientY);
}

export function isClientPointInsideCanvas(canvas: HTMLCanvasElement, clientX: number, clientY: number) {
  const rect = canvas.getBoundingClientRect();
  return clientX >= rect.left && clientX <= rect.right && clientY >= rect.top && clientY <= rect.bottom;
}

export function getBoardSize(board: Board): BoardSize {
  return {
    width: positiveNumberOrDefault(board.width, DEFAULT_BOARD_WIDTH),
    height: positiveNumberOrDefault(board.height, DEFAULT_BOARD_HEIGHT)
  };
}

export function positiveNumberOrDefault(value: number, fallback: number) {
  return Number.isFinite(value) && value > 0 ? value : fallback;
}

export function reconcilePendingTokenRadius(token: Token, pendingRadii: Map<string, number>) {
  const pendingRadius = pendingRadii.get(token.id);
  if (pendingRadius === undefined) return token;

  if (Math.abs(token.radius - pendingRadius) < 0.001) {
    pendingRadii.delete(token.id);
    return token;
  }

  return { ...token, radius: pendingRadius };
}

export function requestTokenLockMessage(tokenId: string, tokens: Token[], pendingRadii: Map<string, number>, isDm: boolean) {
  return withDmTokenRadius({ type: "request_token_lock", tokenId }, tokenId, tokens, pendingRadii, isDm);
}

export function moveTokenMessage(tokenId: string, x: number, y: number, tokens: Token[], pendingRadii: Map<string, number>, isDm: boolean) {
  return withDmTokenRadius({ type: "move_token", tokenId, x, y }, tokenId, tokens, pendingRadii, isDm);
}

export function setTokenSceneMessage(tokenId: string, inScene: boolean, x: number, y: number, tokens: Token[], pendingRadii: Map<string, number>, isDm: boolean) {
  return withDmTokenRadius({ type: "set_token_scene", tokenId, inScene, x, y }, tokenId, tokens, pendingRadii, isDm);
}

export async function updateTokenRadius(roomId: string, tokenId: string, radius: number, playerKey: string) {
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

export function withDmTokenRadius<T extends { tokenId: string }>(message: T, tokenId: string, tokens: Token[], pendingRadii: Map<string, number>, isDm: boolean) {
  if (!isDm) return message;

  const pendingRadius = pendingRadii.get(tokenId);
  if (pendingRadius !== undefined) return { ...message, radius: pendingRadius };

  const token = tokens.find((candidate) => candidate.id === tokenId);
  return token ? { ...message, radius: token.radius } : message;
}

export function getMaxTokenRadius(boardSize: BoardSize) {
  return Math.min(MAX_TOKEN_RADIUS, Math.max(MIN_TOKEN_RADIUS, Math.floor(Math.min(boardSize.width, boardSize.height) / 3)));
}

export function canControlToken(token: Token, playerKey: string, isDm: boolean) {
  return isDm || token.owner === playerKey;
}

export function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max);
}

export function hitToken(token: Token, x: number, y: number) {
  return Math.hypot(token.x - x, token.y - y) <= token.radius;
}
