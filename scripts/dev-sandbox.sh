#!/usr/bin/env bash
# Dev-only launcher: resets a gitignored sandbox campaign (test-campaign-sandbox),
# starts the backend and frontend, and prints the page URLs. Never touches the
# real campaigns/test-campaign/ folder. Not used by the Render deployment.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SANDBOX_DIR="$REPO_ROOT/campaigns/test-campaign-sandbox"
CAMPAIGN_ID="test-campaign-sandbox"
BACKEND_PORT=8000
FRONTEND_PORT=5173
BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
  echo
  echo "Stopping dev sandbox..."
  if [ -n "$FRONTEND_PID" ]; then
    pkill -P "$FRONTEND_PID" 2>/dev/null || true
    kill "$FRONTEND_PID" 2>/dev/null || true
    wait "$FRONTEND_PID" 2>/dev/null || true
  fi
  if [ -n "$BACKEND_PID" ]; then
    pkill -P "$BACKEND_PID" 2>/dev/null || true
    kill "$BACKEND_PID" 2>/dev/null || true
    wait "$BACKEND_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

port_in_use() {
  lsof -i TCP:"$1" -sTCP:LISTEN >/dev/null 2>&1
}

if port_in_use "$BACKEND_PORT"; then
  echo "Port $BACKEND_PORT is already in use -- is the backend already running? Stop it first." >&2
  exit 1
fi
if port_in_use "$FRONTEND_PORT"; then
  echo "Port $FRONTEND_PORT is already in use -- is the frontend already running? Stop it first." >&2
  exit 1
fi

# Never delete anything unless the resolved path is exactly the sandbox folder.
case "$SANDBOX_DIR" in
  */campaigns/test-campaign-sandbox)
    ;;
  *)
    echo "Refusing to delete: resolved sandbox path does not end in campaigns/test-campaign-sandbox: $SANDBOX_DIR" >&2
    exit 1
    ;;
esac

if [ -d "$SANDBOX_DIR" ]; then
  echo "Removing existing sandbox at $SANDBOX_DIR"
  rm -rf "$SANDBOX_DIR"
fi

cd "$REPO_ROOT"

echo "Seeding sandbox campaign ($CAMPAIGN_ID) via the character builder/campaign repository code..."
poetry run python "$SCRIPT_DIR/seed_dev_sandbox.py"

echo "Starting backend on port $BACKEND_PORT..."
poetry run uvicorn dnd_board.server:app --host 127.0.0.1 --port "$BACKEND_PORT" &
BACKEND_PID=$!

echo "Waiting for backend health check..."
healthy=false
for _ in $(seq 1 60); do
  if curl -fsS "http://127.0.0.1:$BACKEND_PORT/health" >/dev/null 2>&1; then
    healthy=true
    break
  fi
  sleep 0.5
done
if [ "$healthy" != "true" ]; then
  echo "Backend did not become healthy in time." >&2
  exit 1
fi

echo "Starting frontend on port $FRONTEND_PORT..."
"$REPO_ROOT/node_modules/.bin/vite" --host 127.0.0.1 --port "$FRONTEND_PORT" &
FRONTEND_PID=$!

sleep 2

echo
echo "Dev sandbox is up. Pages (campaign: $CAMPAIGN_ID):"
echo "  DM board view:          http://127.0.0.1:$FRONTEND_PORT/$CAMPAIGN_ID/player=dm"
echo "  Player board view:      http://127.0.0.1:$FRONTEND_PORT/$CAMPAIGN_ID/player=player-1"
echo "  Character sheet view:   http://127.0.0.1:$FRONTEND_PORT/$CAMPAIGN_ID/player=player-1/sheet"
echo "  Empty-slot sheet (builder appears here): http://127.0.0.1:$FRONTEND_PORT/$CAMPAIGN_ID/player=player-4/sheet"
echo
echo "Press Ctrl+C to stop both servers."

wait "$BACKEND_PID" "$FRONTEND_PID"
