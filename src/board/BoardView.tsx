import type { CSSProperties, PointerEvent } from "react";

import { formatPlayerName } from "../routing";
import { TokenKind } from "../types";
import type { Asset, Board, FogState, Token } from "../types";
import { MIN_TOKEN_RADIUS, canvasPoint, canControlToken } from "./boardRendering";
import type { BoardSize, DragPreview } from "./boardRendering";

type Status = "idle" | "saving" | "saved" | "error";
type LoadStatus = "idle" | "loading" | "loaded" | "error";
type DragGhost = { tokenId: string; clientX: number; clientY: number };

type BoardViewProps = {
  assetSearch: string;
  assets: Asset[];
  board: Board;
  boards: Board[];
  boardCanvasStyle: CSSProperties;
  boardSize: BoardSize;
  canvasRef: React.RefObject<HTMLCanvasElement | null>;
  connection: string;
  dragGhost: DragGhost | null;
  dragPreview: DragPreview | null;
  filteredAssets: Asset[];
  fog: FogState;
  isDm: boolean;
  loadStatus: LoadStatus;
  maxTokenRadius: number;
  ownLockedTokenId?: string;
  partyTokens: Token[];
  otherTokens: Token[];
  playerCount: number;
  playerKey: string;
  revealToolEnabled: boolean;
  saveStatus: Status;
  selectedAssetKey: string;
  tokens: Token[];
  onBoardPointerDown: (event: PointerEvent<HTMLCanvasElement>) => void;
  onBoardPointerMove: (event: PointerEvent<HTMLCanvasElement>) => void;
  onBoardPointerUp: (event: PointerEvent<HTMLCanvasElement>) => void;
  onCanvasEnter: (point: { x: number; y: number }) => void;
  onCanvasLeave: () => void;
  onClearScene: () => void;
  onDeleteToken: (token: Token) => void;
  onLoadRoom: () => void;
  onLoadSelectedAsset: () => void;
  onSaveRoom: () => void;
  onSelectAsset: (key: string) => void;
  onSearchAssets: (search: string) => void;
  onSelectBoard: (boardId: string) => void;
  onSetBrushSize: (size: number) => void;
  onSetHideMode: (hide: boolean) => void;
  onSetRevealTool: (enabled: boolean) => void;
  onResizeToken: (token: Token, radius: number) => void;
  onSidebarPointerDown: (event: PointerEvent<HTMLElement>, token: Token) => void;
  onSidebarPointerMove: (event: PointerEvent<HTMLElement>) => void;
  onSidebarPointerUp: (event: PointerEvent<HTMLElement>) => void;
};

export function BoardView(props: BoardViewProps) {
  const {
    assetSearch, assets, board, boards, boardCanvasStyle, boardSize, canvasRef,
    connection, dragGhost, dragPreview, filteredAssets, fog, isDm, loadStatus,
    maxTokenRadius, ownLockedTokenId, otherTokens, partyTokens, playerCount,
    playerKey, revealToolEnabled, saveStatus, selectedAssetKey, tokens
  } = props;
  return (
    <main className={`app-shell${dragPreview ? " is-dragging" : ""}`}>
      <aside className="sidebar">
        <div>
          <h1>DnD Board</h1>
          <p className="status">{connection} · {playerCount}/8 connected</p>
          <p className="status">You are {formatPlayerName(playerKey, tokens)}</p>
        </div>
        {isDm && (
          <section className="dm-tools">
            <div className="save-load-actions">
              <button className="save-button" onClick={props.onSaveRoom} disabled={saveStatus === "saving"}>
                {saveStatus === "saving" ? "Saving" : saveStatus === "saved" ? "Saved" : saveStatus === "error" ? "Save Failed" : "Save"}
              </button>
              <button onClick={props.onLoadRoom} disabled={loadStatus === "loading"}>
                {loadStatus === "loading" ? "Loading" : loadStatus === "loaded" ? "Loaded" : loadStatus === "error" ? "Load Failed" : "Load"}
              </button>
            </div>
            <button onClick={props.onClearScene}>Clear Scene</button>
            {boards.length > 0 && (
              <label>Board
                <select value={board.id} onChange={(event) => props.onSelectBoard(event.currentTarget.value)}>
                  {boards.map((availableBoard) => <option key={availableBoard.id} value={availableBoard.id}>{availableBoard.name}</option>)}
                </select>
              </label>
            )}
            {assets.length > 0 && (
              <div className="asset-loader">
                <label className="asset-search">Search
                  <input type="search" value={assetSearch} onChange={(event) => props.onSearchAssets(event.currentTarget.value)} />
                </label>
                <label>Asset
                  <select value={selectedAssetKey} onChange={(event) => props.onSelectAsset(event.currentTarget.value)}>
                    {filteredAssets.map((asset) => <option key={assetKey(asset)} value={assetKey(asset)}>{asset.name}</option>)}
                  </select>
                </label>
                <button onClick={props.onLoadSelectedAsset} disabled={!selectedAssetKey}>Add</button>
              </div>
            )}
            <label className="toggle-row">
              <input checked={fog.hideMode} type="checkbox" onChange={(event) => props.onSetHideMode(event.currentTarget.checked)} />
              Hide
            </label>
            {fog.hideMode && (<>
              <label className="toggle-row">
                <input checked={revealToolEnabled} type="checkbox" onChange={(event) => props.onSetRevealTool(event.currentTarget.checked)} />
                Reveal
              </label>
              <label>Brush
                <input max="360" min="20" type="range" value={fog.brushSize} onChange={(event) => props.onSetBrushSize(Number(event.currentTarget.value))} />
              </label>
            </>)}
          </section>
        )}
        <TokenSection title="Party" tokens={partyTokens} {...tokenSectionProps(props)} />
        {otherTokens.length > 0 && <TokenSection title="Other" tokens={otherTokens} {...tokenSectionProps(props)} />}
        {ownLockedTokenId && <p className="hint">Dragging {tokens.find((token) => token.id === ownLockedTokenId)?.name}</p>}
      </aside>
      <section className="board-wrap">
        <canvas
          className={dragPreview ? "is-dragging" : ""}
          ref={canvasRef}
          style={boardCanvasStyle}
          width={boardSize.width}
          height={boardSize.height}
          onPointerDown={props.onBoardPointerDown}
          onPointerMove={props.onBoardPointerMove}
          onPointerUp={props.onBoardPointerUp}
          onPointerCancel={props.onBoardPointerUp}
          onPointerEnter={(event) => props.onCanvasEnter(canvasPoint(event, boardSize))}
          onPointerLeave={props.onCanvasLeave}
        />
      </section>
      {dragGhost && <DragGhostToken token={tokens.find((token) => token.id === dragGhost.tokenId)} x={dragGhost.clientX} y={dragGhost.clientY} />}
    </main>
  );
}

function tokenSectionProps(props: BoardViewProps) {
  return {
    isDm: props.isDm,
    maxTokenRadius: props.maxTokenRadius,
    onDelete: props.onDeleteToken,
    onPointerCancel: props.onSidebarPointerUp,
    onPointerDown: props.onSidebarPointerDown,
    onPointerMove: props.onSidebarPointerMove,
    onPointerUp: props.onSidebarPointerUp,
    onResizeToken: props.onResizeToken,
    playerKey: props.playerKey
  };
}

function DragGhostToken({ token, x, y }: { token: Token | undefined; x: number; y: number }) {
  if (!token) return null;
  return <div className="drag-ghost" style={{ left: x, top: y }}>
    {token.avatarUrl ? <img src={token.avatarUrl} alt="" draggable={false} /> : token.name.slice(0, 3).toUpperCase()}
  </div>;
}

type TokenSectionProps = ReturnType<typeof tokenSectionProps> & { title: string; tokens: Token[] };

function TokenSection({ title, tokens, isDm, maxTokenRadius, onDelete, onPointerCancel, onPointerDown, onPointerMove, onPointerUp, onResizeToken, playerKey }: TokenSectionProps) {
  return <section>
    <h2>{title}</h2>
    <ul className={`token-list ${isDm ? "dm-token-list" : "player-token-list"}`}>
      {tokens.map((token) => <li className={[
        !canControlToken(token, playerKey, isDm) || (token.lockedBy && token.lockedBy !== playerKey) ? "locked" : "",
        token.inScene ? "in-scene" : ""
      ].filter(Boolean).join(" ")} key={token.id}>
        <span className="swatch drag-handle" draggable={false}
          onPointerDown={(event) => onPointerDown(event, token)} onPointerMove={onPointerMove}
          onPointerUp={onPointerUp} onPointerCancel={onPointerCancel} onDragStart={(event) => event.preventDefault()}>
          {token.avatarUrl && <img src={token.avatarUrl} alt="" draggable={false} />}
        </span>
        <span className="token-name" title={token.name}>{token.name}</span>
        {isDm && <label className="token-size-control"><input aria-label={`${token.name} size`} max={maxTokenRadius} min={MIN_TOKEN_RADIUS}
          type="range" value={token.radius} onChange={(event) => onResizeToken(token, Number(event.currentTarget.value))} /></label>}
        {isDm && token.kind !== TokenKind.CHARACTER && <button className="icon-button danger" onClick={() => onDelete(token)} onPointerDown={(event) => event.stopPropagation()}>X</button>}
      </li>)}
    </ul>
  </section>;
}

function assetKey(asset: Asset | undefined) {
  return asset ? `${asset.kind}:${asset.id}` : "";
}
