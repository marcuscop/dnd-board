# DnD Board

A small web-based shared battle map. The FastAPI backend owns realtime room state and token locks; the React/Vite frontend renders the board, sidebar, fog, and tokens.

## Local Dev

Install dependencies:

```sh
poetry install --with dev
npm install
```

For local FLUX/image generation utilities, install the heavier optional group:

```sh
poetry install --with dev,imagegen
```

Start the backend:

```sh
npm run server
```

Start the frontend in another terminal:

```sh
npm run dev -- --host 127.0.0.1
```

Open:

```text
http://127.0.0.1:5173/?campaign=test-campaign&player=dm
http://127.0.0.1:5173/?campaign=test-campaign&player=Marina
http://127.0.0.1:5173/?campaign=test-campaign&player=Edward
```

`player=dm` opens DM controls. Player names come from the party config.

Useful checks:

```sh
poetry run pytest
npm run check
```

## Campaign Setup

Current campaign assets are loaded from `campaigns/test-campaign/`. The URL `campaign=test-campaign` should match the active room/state name.

```text
campaigns/
  test-campaign/
    campaign.json
    boards/
    party/
      party.json
    saves/
```

`campaign.json`:

```json
{
  "id": "test-campaign",
  "name": "Test Campaign"
}
```

Board images go in:

```text
campaigns/test-campaign/boards/
```

Supported image formats include PNG, JPG/JPEG, WebP, and GIF. Board images use their native aspect ratio.

Runtime saves are written to:

```text
campaigns/test-campaign/saves/
```

Save files are local runtime state and should stay ignored by git.

## Party Characters

Party character images go in:

```text
campaigns/test-campaign/party/
```

Party members are configured in:

```text
campaigns/test-campaign/party/party.json
```

Example:

```json
{
  "members": [
    { "id": "player-1", "name": "Marina", "image": "ex1.png" },
    { "id": "player-2", "name": "Edward", "image": "ex2.png" }
  ]
}
```

Use the configured names in player URLs:

```text
http://127.0.0.1:5173/?campaign=test-campaign&player=Marina
```

## Shared Assets

Non-party images are shared across campaigns. This can include monsters, NPCs, beasts, objects, items, props, or anything else the DM wants to place on the board.

```text
shared/
  assets/
```

Add shared images to:

```text
shared/assets/
```

The DM can search shared assets in the sidebar and click **Add**. Added assets appear on the board and sync to player windows. The DM can resize or delete shared asset tokens.

## DM Controls

DM URL:

```text
http://127.0.0.1:5173/?campaign=test-campaign&player=dm
```

The DM can:

- choose a board
- add shared assets
- resize tokens
- delete shared asset tokens
- clear the scene
- enable fog of war and reveal areas
- save/load the current campaign state

## Monster Image Generation

Install image generation dependencies first:

```sh
poetry install --with imagegen
```

Generate one monster image with the BFL API:

```sh
poetry run python utils/generate_flux_monster_test.py --monster "Goblin"
```

Generate a batch from `shared/dndbeyond_monster_names.json`:

```sh
poetry run python utils/generate_flux_monsters_batch.py --start 0 --limit 50
```

The script skips existing files in `shared/assets/`. Moderated requests are written to:

```text
shared/assets/request-moderated.json
```

Timed-out tasks are written to:

```text
shared/assets/generated/flux_pending.jsonl
```

Debug polling:

```sh
poetry run python utils/generate_flux_monsters_batch.py --debug-polls --debug-every 10 --timeout 60
```

## Static Assets And Git LFS

Image assets are served as normal static files by the app. Large image libraries should use Git LFS.

Track common asset formats:

```sh
git lfs track "*.png" "*.jpg" "*.jpeg" "*.webp" "*.avif" "*.gif" "*.bmp" "*.tif" "*.tiff" "*.heic" "*.heif" "*.svg" "*.blend"
```

When ready to commit image assets:

```sh
git add .gitattributes
git add shared campaigns backgrounds
git lfs status
```

## Production Shape

Build the frontend:

```sh
npm run build
```

Run the production-style Python server:

```sh
npm start
```

When `dist/` exists, FastAPI serves the built frontend and static assets from one Python web service.

## Render

This repo includes `render.yaml` for a Render web service.

Render build command:

```sh
poetry install --only main --no-root && npm ci && npm run build
```

Render start command:

```sh
poetry run uvicorn dnd_board.server:app --host 0.0.0.0 --port $PORT
```

Render environment variables:

```text
PYTHON_VERSION=3.11.15
NODE_VERSION=22
POETRY_VERSION=2.3.4
```

`--only main` keeps Render from installing local-only test and image-generation dependencies such as Torch and Diffusers.
