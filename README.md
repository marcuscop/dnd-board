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

- `?player=1`
- `?player=2`
- `?player=3`
- `?player=4`

The room still defaults to `table`, or you can provide one with `?room=test-party`.
DM mode is selected with `?dm=1` or `?player=dm`.

To test local multiplayer with two windows:

1. Open `http://localhost:5173` in two browser windows.
2. Change one URL to `http://localhost:5173/?room=test-party&player=1`.
3. Change the other URL to `http://localhost:5173/?room=test-party&player=2`.
4. Drag Player 1 from the Party list onto the board in the player 1 window.
5. Confirm the player 2 window sees Player 1 move but cannot drag Player 1.
6. Drag Player 2 onto the board from the player 2 window.
7. Drag either character off the board from its owner window to remove it from the scene.

To test with four windows:

1. Start the backend with `npm run server`.
2. Start the frontend with `npm run dev`.
3. Open these four URLs:

```text
http://localhost:5173/?room=test-party&player=1
http://localhost:5173/?room=test-party&player=2
http://localhost:5173/?room=test-party&player=3
http://localhost:5173/?room=test-party&player=4
```

4. Drag each player’s own character from the Party list onto the board.
5. Move characters around from their matching player windows.
6. Try to grab another player’s character; it should not move.
7. Drag a character off the board from its owner window to remove it from the scene.

## Character Avatars

Each player can upload an image avatar for their own character from the Party list. The backend accepts common raster image formats, including PNG, JPEG, WebP, GIF, BMP, TIFF, and HEIC/HEIF when supported by the installed decoder, then normalizes the stored avatar to PNG. The uploaded avatar appears in the sidebar and on the board for everyone in the room.

For local development, uploads are saved under `data/uploads/` and served by FastAPI at `/uploads/...`. That directory is ignored by git.

This local upload storage is good enough for development, but it is not the final deployment storage plan. Before hosting real games, move uploaded avatars to persistent object storage such as Supabase Storage or Cloudflare R2 and keep the same `avatarUrl` behavior in the app.

For a cleaner four-player test, use separate browser profiles or one normal window plus private/incognito windows.

## Board Switching

The DM view has a **Board** selector. The default board is the green field. Campaign boards are loaded from image files in `campaigns/test-campaign/boards/`. Image boards use their native pixel dimensions, so the canvas aspect ratio changes to show the full PNG/JPEG/WebP/GIF instead of cropping it into a fixed shape.

Legacy files in the top-level `boards/` folder are still used as a fallback if that folder exists, but new board assets should go under the campaign folder. Once the board files you need have been copied into `campaigns/test-campaign/boards/`, the top-level `boards/` folder is optional.

To test board switching:

1. Open `http://localhost:5173/?room=test-party&dm=1`.
2. Change **Board** from `Green Field` to `Phandalin`.
3. Open a player window for the same room.
4. Confirm the player sees the same board background.

## NPCs, Monsters, And Beasts

The DM view has an **Asset** selector and **Add** button. Campaign assets are loaded from:

```text
campaigns/test-campaign/npcs/
campaigns/test-campaign/monsters/
campaigns/test-campaign/beasts/
```

Legacy files in the top-level `npcs/`, `monsters/`, and `beasts/` folders are still used as fallbacks if those folders exist, but new assets should go under the campaign folder. Once the asset files you need have been copied into the campaign folders, the top-level NPC/monster/beast folders are optional.

To test loading an NPC, monster, or beast:

1. Open `http://localhost:5173/?room=test-party&dm=1`.
2. Pick an NPC, monster, or beast from **Asset**.
3. Click **Add**.
4. The token should appear in the scene and sync to player windows.
5. Loaded NPCs, monsters, and beasts appear in their own sidebar sections.
6. The DM can delete loaded NPC/monster/beast tokens with the `X` button. Party characters cannot be deleted.
7. The DM can use each token's **Size** slider to resize it independently.

## Scene Controls

The DM view has a **Clear Scene** button. It removes every token from the board and releases any active token locks, but keeps the selected board and fog state unchanged.

## Campaign Layout

The active campaign is currently hardcoded to `test-campaign`. Its folder layout is:

```text
campaigns/
  test-campaign/
    campaign.json
    boards/
    npcs/
    monsters/
    beasts/
    saves/
```

Runtime save files are written to `campaigns/test-campaign/saves/`, and that path is ignored by git. Keep reusable campaign assets in the asset folders; keep generated/current game state out of git.

The top-level `backgrounds/` folder is separate from campaign board assets. It currently contains the web page background image referenced by the frontend stylesheet, so do not remove it unless that CSS reference is changed or the image is moved into another tracked frontend asset location.

## Game State Saves

Open the DM view at:

```text
http://localhost:5173/?room=test-party&dm=1
```

The DM view has **Save** and **Load** buttons. **Save** writes the current room state to `campaigns/test-campaign/saves/test-party.json`, including selected board, character positions, token sizes, scene membership, colors, owners, and avatar URLs. **Load** restores that saved state immediately and broadcasts it to everyone in the room. Local save files are ignored by git.
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
