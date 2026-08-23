# DnD Board

A small web-based shared battle map for remote players. The first version uses a green canvas board and four fixed player-character tokens. The Python/FastAPI server owns the room state, grants token locks, and broadcasts low-FPS movement updates to everyone in the room.

## Local Development

This project has two parts:

- **Python backend:** FastAPI WebSocket server, managed with Poetry.
- **JS frontend:** React/Vite canvas app, managed with npm.

You need both environments installed locally:

- Python 3.11+
- Poetry
- Node.js 20+ and npm

Install Python backend dependencies:

```sh
poetry install
```

Install JS frontend dependencies:

```sh
npm install
```

Run the FastAPI realtime server:

```sh
npm run server
```

That command runs:

```sh
poetry run uvicorn dnd_board.server:app --host 127.0.0.1 --port 8000
```

In another terminal, run the Vite web client:

```sh
npm run dev
```

Open the Vite URL, usually `http://localhost:5173`.

Player identity is selected through the URL for now:

- `?player=Marina`
- `?player=Edward`
- `?player=Hal`
- `?player=Valarie`

The campaign defaults to `test-campaign`, or you can provide one with `?campaign=test-campaign`.
DM mode is selected with `?dm=1` or `?player=dm`.

To test local multiplayer with two windows:

1. Open `http://localhost:5173` in two browser windows.
2. Change one URL to `http://localhost:5173/?campaign=test-campaign&player=Marina`.
3. Change the other URL to `http://localhost:5173/?campaign=test-campaign&player=Edward`.
4. Drag Player 1 from the Party list onto the board in the player 1 window.
5. Confirm the player 2 window sees Player 1 move but cannot drag Player 1.
6. Drag Player 2 onto the board from the player 2 window.
7. Drag either character off the board from its owner window to remove it from the scene.

To test with four windows:

1. Start the backend with `npm run server`.
2. Start the frontend with `npm run dev`.
3. Open these four URLs:

```text
http://localhost:5173/?campaign=test-campaign&player=Marina
http://localhost:5173/?campaign=test-campaign&player=Edward
http://localhost:5173/?campaign=test-campaign&player=Hal
http://localhost:5173/?campaign=test-campaign&player=Valarie
```

4. Drag each player’s own character from the Party list onto the board.
5. Move characters around from their matching player windows.
6. Try to grab another player’s character; it should not move.
7. Drag a character off the board from its owner window to remove it from the scene.

## Static Party

Party characters are loaded from static campaign files at startup. For the test campaign, put party images in:

```text
campaigns/test-campaign/party/
```

The party manifest is:

```text
campaigns/test-campaign/party/party.json
```

Each manifest entry maps a fixed player slot to a display name, image file, and token color:

```json
{
  "members": [
    { "id": "player-1", "name": "Player 1", "image": "ex1.png", "color": "#2563eb" }
  ]
}
```

This keeps party assets deployment-friendly: update files in git, redeploy, and the sidebar uses the new static party. Saved room state preserves character scene placement and token size, but character name/color/avatar come from the current party manifest.

For a cleaner four-player test, use separate browser profiles or one normal window plus private/incognito windows.

## Board Switching

The DM view has a **Board** selector. The default board is the green field. Campaign boards are loaded from image files in `campaigns/test-campaign/boards/`. Image boards use their native pixel dimensions, so the canvas aspect ratio changes to show the full PNG/JPEG/WebP/GIF instead of cropping it into a fixed shape.

Legacy files in the top-level `boards/` folder are still used as a fallback if that folder exists, but new board assets should go under the campaign folder. Once the board files you need have been copied into `campaigns/test-campaign/boards/`, the top-level `boards/` folder is optional.

To test board switching:

1. Open `http://localhost:5173/?campaign=test-campaign&dm=1`.
2. Change **Board** from `Green Field` to `Phandalin`.
3. Open a player window for the same room.
4. Confirm the player sees the same board background.

## NPCs And Monsters

The DM view has an **Asset** selector and **Add** button. Actor assets are shared across all campaigns and loaded from:

```text
shared/npcs/
shared/monsters/
```

Legacy files in the top-level `npcs/` and `monsters/` folders are still used as fallbacks if those folders exist, but new actor assets should go under `shared/`. Beasts are treated as monsters for now, so put beast images in `shared/monsters/`.

To test loading an NPC or monster:

1. Open `http://localhost:5173/?campaign=test-campaign&dm=1`.
2. Search for and pick an NPC or monster from **Asset**.
3. Click **Add**.
4. The token should appear in the scene and sync to player windows.
5. Loaded NPCs and monsters appear in their own sidebar sections.
6. The DM can delete loaded NPC/monster tokens with the `X` button. Party characters cannot be deleted.
7. The DM can use each token's **Size** slider to resize it independently.

## Scene Controls

The DM view has a **Clear Scene** button. It removes every token from the board and releases any active token locks, but keeps the selected board and fog state unchanged.

## Campaign Layout

The active campaign is currently hardcoded to `test-campaign`. Its folder layout is:

```text
shared/
  npcs/
  monsters/
campaigns/
  test-campaign/
    campaign.json
    boards/
    party/
      party.json
    saves/
```

`shared/npcs/` and `shared/monsters/` are global actor libraries. Actors in these folders are available to every campaign. Campaign folders own campaign-specific boards, party members, and runtime save state.

Runtime save files are written to `campaigns/test-campaign/saves/`, and that path is ignored by git. Keep reusable campaign assets in the asset folders; keep generated/current game state out of git.

The top-level `backgrounds/` folder is separate from campaign board assets. It currently contains the web page background image referenced by the frontend stylesheet, so do not remove it unless that CSS reference is changed or the image is moved into another tracked frontend asset location.

## Game State Saves

Open the DM view at:

```text
http://localhost:5173/?campaign=test-campaign&dm=1
```

The DM view has **Save** and **Load** buttons. **Save** writes the current room state to `campaigns/test-campaign/saves/test-campaign.json`, including selected board, character positions, token sizes, scene membership, loaded NPC/monster tokens, and fog state. Static party metadata is loaded from `party.json`. **Load** restores the saved state immediately and broadcasts it to everyone in the room. Local save files are ignored by git.
It also saves fog-of-war state: whether hide mode is enabled, the brush size, and all revealed areas.

Saved state also auto-loads when a room is created, such as after restarting the backend or after everyone leaves and rejoins the room. Older local saves under `data/saves/` are still loaded as a fallback if no campaign save exists.

To manually test save/load:

1. Open a player window, place a character on the board, and move it.
2. Open the DM URL for the same room.
3. Turn on **Hide**; the **Reveal** tool and **Brush** slider should appear.
4. Turn on **Reveal**, hover over the board to see the brush circle, and paint a few clear areas.
5. Click **Save**.
6. Change the board state again.
7. Click **Load**; the saved character, board, NPC/monster, and fog state should return.

## Useful Commands

Check TypeScript:

```sh
npm run check
```

Run Python backend tests:

```sh
poetry run pytest
```

Generate one test monster image with Black Forest Labs:

```sh
poetry run python utils/generate_flux_monster_test.py
```

This reads `BFL_API_KEY` from your environment, or from a local `flux-api` file that is ignored by git. Generated images are saved under `shared/monsters/generated/`.

Generate one local FLUX.2 Klein 4B test image with Diffusers:

```sh
poetry run python utils/generate_flux2_klein_local.py --prompt "A cat holding a sign that says hello world" --output flux-klein.png
```

The first run downloads `black-forest-labs/FLUX.2-klein-4B` from Hugging Face. The script auto-selects CUDA, Apple MPS, or CPU; use `--device` to override it. Local generation defaults to `512x512` and enables VAE tiling/slicing to reduce memory pressure. To debug Apple MPS memory use:

```sh
poetry run python utils/generate_flux2_klein_local.py --device mps --debug-memory --width 512 --height 512
```

Generate FLUX monster images from the first 50 names in the D&D Beyond name list:

```sh
poetry run python utils/generate_flux_monsters_batch.py
```

By default this reads `shared/dndbeyond_monster_names.json`, skips monster PNGs that already exist, and writes generated images into `shared/monsters/`. Use `--start` and `--limit` to process another slice.

Build a D&D Beyond monster name list from the public monster listing pages:

```sh
poetry run python utils/build_dndbeyond_monster_names.py
```

By default this reads pages `1` through `179` from `https://www.dndbeyond.com/monsters?page=N` and writes only the monster names to `shared/dndbeyond_monster_names.json`.

You can test against one local HTML fixture instead of hitting the network:

```sh
poetry run python utils/build_dndbeyond_monster_names.py --source-file path/to/dndbeyond-monsters.html
```

Build the frontend:

```sh
npm run build
```

Run the production-style Python server locally after building:

```sh
npm start
```

The FastAPI app serves files from `dist/` when that directory exists, so deployment can run a single Python web service after the frontend is built. `npm start` binds to `0.0.0.0` and reads the platform `PORT`, which is the shape Render expects.

## Dependency Management

Use Poetry for Python dependencies:

```sh
poetry add package-name
```

Use npm for browser/build dependencies:

```sh
npm install package-name
```

Do not add Python packages with `pip install` unless you are only doing a temporary local experiment. Project Python dependencies should be captured in `pyproject.toml` and `poetry.lock`.

## Deployment Direction

The easiest first public test target is a Render free web service running the FastAPI server plus the static client build. For a stronger long-term realtime architecture, migrate rooms to Cloudflare Workers + Durable Objects with WebSocket Hibernation.

## Next Milestones

- Add token renaming.
- Add persistent party character records for names, items, gear, stats, and notes.
- Persist room state outside server memory.
- Add map image upload.
- Add sprite/image tokens exported from Blender.
- Add optional Three.js rendering once gameplay is stable.
