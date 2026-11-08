# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

DnD Board is a small web-based shared battle map and character sheet tool for tabletop D&D. A FastAPI backend owns realtime room state (tokens, fog of war, locks), turn-based encounters, and a generalized 5e rules/effects engine (character sheets, progression, spells, equipment, conditions, rests); a React/Vite frontend renders the board, sidebar, fog, tokens, and character sheet UI. The DM has full control over the board/scene; players control their own tokens and sheets. The system enforces what it can model (resource costs, encounter/turn timing, resolution order) and leaves unmodeled geometry and table judgment to the DM, with explicit DM override controls (see `DESIGN.md`).

## Tech stack

- Frontend: React 19 + TypeScript, built with Vite 7. No routing library or external state management library — URL parsing/route resolution is hand-rolled (`src/routing.ts`), and app state lives in a small set of custom hooks (`useState`/`useEffect` + a raw `WebSocket`), not a single monolithic component.
- Backend: FastAPI (Python 3.11+), served via Uvicorn. Managed with Poetry. Request bodies are mostly raw `dict[str, Any]`/query params, with `pydantic.BaseModel` starting to appear for some newer endpoints (e.g. rest-related requests in `server.py`).
- Realtime layer: a single `/ws` WebSocket endpoint carrying a JSON message protocol (see Architecture below), used only for board/token/fog concerns. Sheet/character/roll/encounter mutations go over HTTP REST instead.
- Storage: no database — state lives in-memory per `Room` on the server, plus JSON files on disk (`campaigns/<id>/saves/`, `party.json`, `campaign.json`) for persistence and campaign config.
- Image handling: Pillow + pillow-heif for uploads/avatars; optional `imagegen` dependency group (Torch, Diffusers, Transformers) for local FLUX-based monster art generation, used only by scripts in `utils/`.
- Deployment target: Render (`render.yaml`), single Python web service — FastAPI serves the built Vite `dist/` as static files when present.

## Commands

Install deps:
```sh
poetry install --with dev
npm install
```

Run backend (dev, port 8000):
```sh
npm run server
```

Run frontend (dev, port 5173, proxies `/api`, `/uploads`, `/boards`, `/npcs`, `/monsters` to the backend):
```sh
npm run dev -- --host 127.0.0.1
```

Type-check frontend:
```sh
npm run check
```

Build frontend:
```sh
npm run build
```

Run production-style server (serves built `dist/` from FastAPI):
```sh
npm start
```

Run dev sandbox (deletes and recreates the gitignored `campaigns/test-campaign-sandbox/` folder, seeds a level-1 Fighter, Rogue, and Wizard as `player-1` through `player-3` using the real character builder code, leaves `player-4` empty so its sheet URL shows the character builder, starts the backend on port 8000 and the frontend on port 5173, prints the page URLs, and stops both when you press Ctrl-C; never touches `campaigns/test-campaign/`; requires `lsof`, `curl`, and `poetry`, plus pulled git LFS images, since it copies board and party images from `test-campaign`):
```sh
npm run dev:sandbox
```

Backend tests (pytest):
```sh
poetry run pytest
poetry run pytest tests/test_fighter_character_sheet.py
poetry run pytest tests/test_fighter_character_sheet.py::test_some_case
poetry run pytest --cov          # pytest-cov is installed; .coverage exists at repo root
```

Frontend e2e tests (Playwright, requires build first per CI):
```sh
npx playwright install chromium   # first time only; see Fresh clone setup for Linux system libraries
npm run test:e2e
```

CI (`.github/workflows/ci.yml`) runs `poetry run pytest -vv --durations=25` for backend, and `npm ci && npm run build && npm run test:e2e` for frontend, on every push/PR.

## Directory structure

```
dnd_board/             Python backend package
  server.py            FastAPI app: route handlers only (37 POST, 7 GET, 1 WebSocket) that
                        parse/validate requests and delegate into application/. Thin compared
                        to before — most logic now lives one layer down. (~2500 lines)
  character_sheet.py   Core rules dataclasses/enums: AbilityType, SkillType, DamageType,
                        ConditionType, SpellId + spell definitions, equipment, dice types,
                        the CharacterSheet dataclass itself (~4500 lines, still the largest file)
  character_builder.py Character creation flow (options, draft -> CharacterSheet)

  application/          Service layer between server.py's routes and the rules engine — each
                        module owns one concern and is imported piecemeal by server.py:
    room_state.py        Room/Player/Token/Board/Fog/Campaign dataclasses (the realtime state
                          shape itself — moved out of server.py)
    action_service.py    Builds RollPayloads for attacks/spells/ability checks/saves/ad-hoc
                          dice/death saves (~1600 lines)
    resolution_service.py Resolves a pending roll against a target: damage/healing/conditions/
                          concentration/temp-HP, chained response rolls, interaction prompts
                          (~1800 lines, the roll pipeline's core)
    resolution_interactions.py  Computes interceptor prompts for d20 tests / effect resolution
                          (reactions, proactive choices, etc.)
    character_state_service.py  Conditions, exhaustion, equipment slots, concentration,
                          rest-driven state resets (~1000 lines)
    progression_service.py  Level-up and progression-choice application (ASI, skills,
                          subclass, spells, feats, etc.)
    encounter_service.py Turn-based encounter orchestration: initiative, turn order/advance,
                          action/resource authorization per turn, turn-boundary resolution
    rest_service.py      Short/long rest grant prompts and application
    resource_service.py  Generic resource spend/payability (spell slots, hit dice, feature
                          uses, ammo, action economy)
    proactive_roll_service.py  Proactive reroll mechanics (e.g. Heroic Inspiration-style
                          choices made before a roll instead of after)
    board_service.py     Token move/lock/release/radius, fog reveal/mode, board select, asset
                          load, scene clear — the logic behind the WS message handlers
    campaign_repository.py  Campaign/party JSON file I/O (party.json, campaign.json, asset dirs)
    persistence.py       Room save/load to `campaigns/<id>/saves/`
    sheet_projection.py  Projects a CharacterSheet + its effect definitions into the wire/dict
                          shape the frontend consumes

  rules/
    encounter.py        Turn-based encounter/turn state model, action categories, activation
                        authorization (used by application/encounter_service.py)
    rest.py             Hit die spends and rest mechanics
    progression.py       Level-up / progression choice tables (ASI, skills, subclass, spells)
    classes/{fighter,rogue,wizard}/  Per-class base rules + subclass ("archetype") rules —
                        still the only three classes implemented
    shared/
      effects.py          The generalized effect-node primitive system (EffectNode,
                          ApplyEffect, DamageEffect, HealingEffect, ConditionalEffect,
                          SavingThrowEffect, SequenceEffect, ActivatedEffect, FeatureMechanics,
                          etc.) — the engine every feat/spell/class feature composes instead of
                          being special-cased by name (see DESIGN.md)
      character_effects.py, condition_effects.py, weapon_effects.py  Effect primitives
                          specialized for character state, conditions, and weapons
      proactive_rerolls.py, progression_definitions.py, resources.py, tool_types.py
      combat_superiority.py  (fighter-specific shared mechanic)
    backgrounds.py, equipment.py, feats.py, species.py, spells.py, sources.py, tools.py

src/                   React frontend, organized by feature rather than one flat file
  App.tsx              Composition root only: wires useRoomConnection + useBoardInteractions +
                        useSheetActions into <BoardView> or <SheetView> by route (~120 lines)
  routing.ts           URL -> {roomId, playerKey, view} parsing, player-key normalization,
                        WS URL resolution — no routing library
  api/client.ts         Shared `apiUrl`/`postJson` fetch helpers used by the hooks below
  hooks/
    useRoomConnection.ts  Owns the WebSocket connection, room/board/fog/token/sheet state,
                          and periodic REST sync (sheets, room state)
    useSheetActions.ts    REST calls for rolls, progression, rest, equipment, resources, etc.
    useBoardInteractions.ts  Board canvas pointer/drag interactions, token move/lock, fog paint
  board/                BoardView.tsx + boardRendering.ts (canvas drawing, hit-testing)
  sheet/                SheetView.tsx (~1700 lines, largest frontend file) + feature panels:
                        Rolls.tsx, EncounterControls.tsx, RestControls.tsx,
                        RestGrantPromptPanel.tsx, ResolutionPromptPanel.tsx,
                        AdHocDiceRoller.tsx, sheetUtils.ts
  builder/              CharacterBuilderPanel.tsx (character creation UI)
  character/            abilityOptions.ts
  types.ts              All frontend TypeScript types/enums, hand-kept in sync with the
                        Python dataclasses/enums in dnd_board/ (~1100 lines)
  main.tsx, styles.css, vite-env.d.ts

design-docs/            Per-topic 5e rules reference/planning notes (not code) — read before
                        implementing a new feat/spell/class/item to see the intended design:
  feats-2014.md, feats-2024.md, spells.md, magic-item.md, equipment.md, conditions.md,
  backgrounds.md, races.md, ability-scores.md, creature-types.md, cover.md, tools.md
  fighter-design/, rogue-design/, wizard-design/   Per-class subclass design notes

tests/
  test_*.py            Backend pytest suite, one file per subsystem — now includes
                        test_encounter.py, test_effects.py, test_rest.py, test_resources.py,
                        test_proactive_rerolls.py, test_durable.py, test_sheet_projection.py,
                        test_armor_training_feats.py, test_elemental_adept.py alongside the
                        per-class/progression/equipment/spells/tools/server suites
  e2e/board-and-sheet.spec.ts  Playwright end-to-end test

campaigns/<campaign-id>/   Per-campaign content and runtime state (see README for full shape)
  campaign.json       {"id", "name"}
  boards/             Board images (png/jpg/webp/gif)
  party/party.json    Party member config + saved CharacterSheet state (schema has changed
                      significantly as the effects/progression system evolved — don't assume
                      an old shape, re-check `sheet_projection.py`/`persistence.py` if unsure)
  saves/              Runtime save files (gitignored, local state only)

shared/assets/        Non-party images shared across campaigns (monsters, NPCs, items, props);
                       searchable/placeable from the DM sidebar
backgrounds/           (background images, see .gitattributes for LFS-tracked types)
utils/                Standalone scripts, not imported by the app:
  generate_flux_monster_test.py, generate_flux_monsters_batch.py,
  generate_flux2_klein_local.py, build_dndbeyond_monster_names.py
scripts/                Dev-only helper scripts, not imported by the app:
  dev-sandbox.sh, seed_dev_sandbox.py
```

Assets (`*.png`, `*.jpg`, `*.jpeg`, `*.webp`, `*.avif`, `*.gif`, `*.bmp`, `*.tif`, `*.tiff`, `*.heic`, `*.heif`, `*.svg`, `*.blend`) are tracked via git LFS (`.gitattributes`).

## Architecture

**Layering.** `server.py` is now a thin route layer: it parses the request, resolves the `Room`/`Player`/`CharacterSheet` involved, and calls into one `application/*_service.py` module to do the actual work, then broadcasts the result. The `Room`/`Player`/`Token`/`Board`/`Fog` dataclasses themselves live in `application/room_state.py`, not in `server.py`. If you're looking for where a given piece of behavior actually happens, start in `application/`, not `server.py` — `server.py` mostly tells you *which* service function handles a route, via its large per-module import blocks at the top of the file.

**Rooms and state.** A `Room` is the unit of realtime state: players, tokens, board, fog, character sheets (via per-sheet runtime state), pending/resolved rolls, encounter state. Rooms are created on demand and keyed by a sanitized room id derived from the campaign in the URL. There is no database; all live state is in-process, and `application/persistence.py` (`load_room`/`save_room`, wired to `/api/rooms/{room_id}/save` and `/load`) persists/restores a room to/from `campaigns/<id>/saves/`; `application/campaign_repository.py` handles the separate campaign/party JSON files.

**Two transport paths, split by purpose:**
- WebSocket (`/ws`), one connection per browser tab, JSON `{"type": ..., ...}` messages dispatched in `handle_message` (`server.py`). Used only for board/token/fog concerns that need low-latency broadcast: `join_room`, `move_token`, `request_token_lock`/`release_token`, `set_token_scene`, `set_token_radius`, `set_fog_mode`, `reveal_fog`, `set_board`, `load_asset`, `delete_token`, `clear_scene` — each delegates into `application/board_service.py`. After most mutations the server broadcasts a fresh state snapshot to every connected player.
- HTTP REST (`/api/rooms/{room_id}/...`, 37 POST + 7 GET routes), used for everything else: character builder, sheet fetch, rolls (attack/spell/ability/saving-throw/ad-hoc/death save), roll resolution against a target, resource/exhaustion/condition/equipment updates, leveling and progression choices, rest grant prompts, and turn-based encounter management (start/advance/end, initiative, resource authorization per turn). These mutate `Room`/`CharacterSheet` state via the relevant `application/` service and then also broadcast over the room's open websockets so other tabs stay in sync.

**Turn-based encounters.** `application/encounter_service.py` + `rules/encounter.py` model initiative, turn order/advancement, and per-turn action/resource authorization (`authorize_action`/`authorize_activation`) — actions now go through an authorization check tied to whose turn it is and what action economy (action/bonus action/reaction/movement) they have left, rather than being freely triggerable at any time.

**Player identity & visibility.** A `playerKey` query param (not a real auth token) identifies who's acting — `player=dm` grants DM privileges; other names are ordinary players scoped to their own party member/sheet. Visibility/control checks (in `board_service.py`/`action_service.py`) gate what a given player can see or roll (e.g. invisibility affects visibility to other players, not the DM).

**The effects engine — this is the big architectural change, read `rules/shared/effects.py` and `DESIGN.md` before adding rules.** Feats, spells, class features, conditions, and items no longer get hand-written branches in application code. They're defined as compositions of generic primitives in `rules/shared/effects.py` (`EffectNode`, `ApplyEffect`, `DamageEffect`, `HealingEffect`, `ConditionalEffect`, `ConditionChangeEffect`, `SavingThrowEffect`, `ContestedCheckEffect`, `SequenceEffect`, `RepeatedEffect`, `TemporaryHitPointsEffect`, `ActivatedEffect`, `FeatureMechanics`, etc.), interpreted by shared engines (`sheet_projection.py`, `action_service.py`, `resolution_service.py`, `encounter_service.py`) that must not special-case a specific feat/spell/class/item by name/identity to decide what it does. A feature definition should carry its *entire* mechanical contract in one place — timing, costs, choices, modifiers, effects, interactions, limitations — composed from these primitives, rather than requiring a named branch somewhere else in the engine to work. `rules/shared/character_effects.py`, `condition_effects.py`, and `weapon_effects.py` hold domain-specific primitives built on top of the generic ones.

**Content vs. runtime state.** Rule *definitions* (what a feat/spell/class does) are separate from a character's/encounter's *runtime state* (selections made, bound targets/items, spent resources, active ongoing effects, provenance of grants). Loading or recomputing a sheet must never refill spent uses, reroll stored results, or duplicate grants — this is why `application/sheet_projection.py` exists as a dedicated read-side projection rather than mutating state as a side effect of display.

**Frontend/backend type sync.** `src/types.ts` mirrors the Python enums/dataclasses in `dnd_board/character_sheet.py`, `rules/shared/effects.py`, and the `application/` services (e.g. `AbilityType`, `ConditionType`, `ResourceId`, `EncounterState`, `ResolutionInterceptorPrompt`, `RollPayload`, `ServerMessage`) by hand — there is no code generation. When changing a shared shape on the backend, update `types.ts` to match.

**Roll pipeline.** Rolls (attacks, spell effects, ability checks, saves, ad-hoc dice, death saves) are built by `application/action_service.py`'s `create_*_action` functions into `RollPayload`s, stored pending on the room, and separately resolved against a target via `application/resolution_service.py`'s `resolve_pending_roll` (wired to `/api/rooms/{room_id}/rolls/{roll_id}/resolve`), which applies damage/healing/conditions/concentration/temp-HP/max-HP effects, can raise interaction prompts (`resolution_interactions.py` — reactions, proactive reroll choices) and chain further response rolls (e.g. saving throws, damage-on-fail effects).

**Proactive-choice pattern.** Per `DESIGN.md`, optional abilities that would otherwise interrupt nearly every roll (e.g. Heroic Inspiration-style rerolls) are offered as an explicit choice *before* the roll (`application/proactive_roll_service.py`, frontend "prepared proactive resource" state) rather than a mandatory prompt after every single roll. This is called out as a deliberate house-rule deviation from the published timing where applicable — if you're implementing something similar, declare that explicitly in the feature definition/UI rather than treating it as mechanically identical to the book rule.

## Conventions

- Python: dataclasses + `Enum` throughout, `from __future__ import annotations`, full type hints on function signatures, snake_case functions, PascalCase classes/enums. `pydantic.BaseModel` is starting to appear for a few newer request bodies (`server.py`) alongside the older raw-dict/query-param style — not yet a repo-wide convention.
- TypeScript: PascalCase for types/enums (matching the Python enum names), camelCase for fields/functions; server message field names are camelCase JSON (not snake_case) even though the Python side is snake_case — check existing serialization in the relevant `application/` service when adding new fields.
- Frontend is organized by feature, not by component type: `board/`, `sheet/`, `builder/`, `hooks/`, `api/`. `App.tsx` is a thin composition root — new UI should land in the relevant feature folder (or a new one) and be wired in via a hook, not added inline to `App.tsx`.
- No linter/formatter config was found for either language (no ruff/black/eslint/prettier config in the repo) — match surrounding style.

## Known gaps

- No linter/formatter configuration found for Python or TypeScript.
- No obvious in-code TODO/FIXME markers were found (a grep for "TODO/FIXME/XXX/HACK" only matched an unrelated `FIRE_RUNE_SHACKLES` identifier).
- Only three classes have rules implemented (fighter, rogue, wizard). `DESIGN.md`'s current framing is "develop breadth through complete representative features" (pick a class/species/background/feat/spell/item and implement its *real* behavior rather than filling the catalog with description-only entries) rather than the earlier strict "one class, levels 1-20, before starting the next" framing — check `DESIGN.md` directly, as this has already shifted once.
- `campaigns/test-campaign/party/party.json`'s schema has changed significantly as the effects/progression system evolved (e.g. a `skills` field was renamed `baseSkills`, a `progressionGrants` structure was added). Treat it as generated/derived data, not something to hand-edit against an assumed shape.
- `src/hooks/useRoomConnection.ts` combines WebSocket push updates and periodic REST polling for both room and sheet state, and the two polls aren't symmetric: room sync (`syncRoomState`, hitting `/api/rooms/{roomId}/state`) repeats every 1.5s but only on the board view — on the sheet view it fires once on mount and never repeats; sheet sync (`loadSheets`, hitting `/api/rooms/{roomId}/sheet`) only runs on the sheet view, firing once then repeating every 10s. Both the WebSocket `room_state` handler and the REST room-sync poll call the same `applyRoomState` function, which unconditionally overwrites state — there's no timestamp/version field on `room_state` to establish precedence. This creates a real but currently low-severity race: a stale poll response can land after a fresher WebSocket push and overwrite it. On the board view this self-corrects within ~1.5s (the next room-sync poll fixes it); on the sheet view there's no repeating room-sync poll to self-correct a room-state clobber the same way. One narrow existing mitigation, `reconcilePendingTokenRadius`, guards token radius specifically against this race — nothing equivalent covers fog, board, token position, or players.
- Running the end-to-end tests modifies the tracked file `campaigns/spell-test-campaign/party/party.json`. Check `git status` after running them and restore that file before committing.
- A test that loads a board image hangs instead of failing when the image is an LFS pointer file (i.e. git LFS content wasn't pulled) rather than the real binary.

## Fresh clone setup

- Install git-lfs first, e.g. `sudo apt install git-lfs` on Ubuntu.
- After cloning, run `git lfs install --local` and then `git lfs pull`. Without this, board and party images are left as text pointer files instead of real binaries, and roughly ten server tests fail or hang.
- Before running the end-to-end tests, install the Playwright browser: `npx playwright install chromium`. On Ubuntu 20.04, headless Chromium also needed these packages: `libatk1.0-0`, `libatk-bridge2.0-0`, `libatspi2.0-0`, `libgbm1`, `libxkbcommon0`.
- The full backend test suite takes about five and a half minutes. Run targeted test files while iterating, and the full suite before commits.
