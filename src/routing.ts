import { TokenKind } from "./types";
import type { Token } from "./types";

export type ConnectionState = "connecting" | "connected" | "disconnected";
export type AppView = "board" | "sheet";
export type InitialRoute = {
  roomId: string;
  playerKey: string;
  view: AppView;
};

export function getInitialRoute(): InitialRoute {
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

export function routePath(roomId: string, player: string, view: AppView) {
  const basePath = `/${encodeURIComponent(roomId)}/player=${encodeURIComponent(player)}`;
  return view === "sheet" ? `${basePath}/sheet` : basePath;
}

export function resolvePlayerKey(requestedPlayerKey: string, tokens: Token[]) {
  if (requestedPlayerKey === "dm") return "dm";
  if (isPlayerSlot(requestedPlayerKey)) return requestedPlayerKey;
  if (tokens.some((token) => token.owner === requestedPlayerKey)) return requestedPlayerKey;
  const normalized = normalizeIdentity(requestedPlayerKey);
  const matchingToken = tokens.find((token) => token.kind === TokenKind.CHARACTER && normalizeIdentity(token.name) === normalized);
  return matchingToken?.owner ?? "player-1";
}

export function playerUrlValue(playerKey: string, tokens: Token[]) {
  if (playerKey === "dm") return "dm";
  return tokens.find((token) => token.kind === TokenKind.CHARACTER && token.owner === playerKey)?.name ?? playerKey;
}

export function formatPlayerName(playerKey: string, tokens: Token[] = []) {
  if (playerKey === "dm") return "DM";
  return tokens.find((token) => token.kind === TokenKind.CHARACTER && token.owner === playerKey)?.name ?? playerKey.replace("-", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function getDefaultWebSocketUrl() {
  if (import.meta.env.DEV) {
    return "ws://localhost:8000/ws";
  }

  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}/ws`;
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

function isPlayerSlot(playerKey: string) {
  return /^player-[1-8]$/.test(playerKey);
}

function normalizeIdentity(value: string) {
  return value.trim().toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
}
