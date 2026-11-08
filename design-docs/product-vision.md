# Table experience vision (proposal)

Status: draft proposal, not agreed by anyone yet. Written 2026-11-07 against `origin/main` at `b854654` plus the dev sandbox launcher on branch `launcher-sandbox`. Nothing tagged Proposed below is implemented.

Purpose: record where the app stands and one possible direction, so everyone working on the repo (people and AI agents) can react before anything is built. Edit, cut or disagree freely. Every statement carries a tag:

- **[Verified]** confirmed by running the app or by a read-only trace of the code
- **[Proposed]** an idea for discussion
- **[Open]** a question that needs an answer before building

## 1. Where the app is today

| Area | Today | Tag |
|---|---|---|
| Roll history | `Room.roll_history` keeps the last 10 resolved rolls (the roll plus its resolution: target HP, conditions, outcome) | Verified |
| Roll visibility | History and pending rolls go unfiltered to every player. The visibility helpers accept a `visible_token_ids` argument that is never used | Verified |
| Roll log display | Only on the sheet view's Logs panel. Nothing on the board view | Verified |
| "Scene" messages | `set_token_scene` flips one token's `inScene` flag and repositions it. `clear_scene` (DM-only) clears every token's `inScene` and lock. Neither touches the board image or fog | Verified |
| Maps | One `board_id` per room, changed by DM-only `set_board`. Tokens have no board field, so they are shared across whichever board is active. `board_id` persists through save/load | Verified |
| Sheet change history | None. Condition, HP and resource updates overwrite state in place. Only changes made during a roll's resolution appear, inside that roll's log entry | Verified |
| Storage | No database. Live state in memory per room. JSON on disk: `campaign.json`, `party/party.json`, `saves/` | Verified |
| Identity | `player=<name>` in the URL. `dm` unlocks DM powers. An unrecognized key silently falls back to `player-1` | Verified |
| Sync | WebSocket push plus REST polling (1.5s room sync on the board view, 10s sheet sync on the sheet view). Both write state through one function with no version check, so a stale poll can briefly overwrite a fresher push | Verified |

## 2. Core idea: one event log

**[Proposed]** Most of the ideas below are views over a single record of everything that happens at the table: roll logs on the map, party alerts, the lorebook, recaps, world prompts and any AI assistance. Build that record once and each feature becomes a filter or a display.

**[Proposed]** Rough shape of one event: id, timestamp, scene, actor, kind, payload, visibility (who may see it). Following `DESIGN.md`, `kind` and payload would be typed enums and dataclasses, not strings or loose dicts.

**[Proposed]** Likely sources: roll resolutions, condition/HP/resource changes, rests, DM actions on the board, DM notes and (later) dialogue. Token movement is probably too noisy to log by default.

Open questions:

- **[Open]** Where events get emitted. The `application/` services look like natural choke points, but sheet changes are spread across several of them.
- **[Open]** Whether the event log replaces `roll_history` or `roll_history` feeds it.
- **[Open]** Whether `roll_history` survives a save/load today (not traced).
- **[Open]** Retention and size. `roll_history` is capped at 10. A lorebook needs a durable, uncapped record.
- **[Open]** The unused `visible_token_ids` parameter: dead code, or half-finished filtering? Any "only players nearby see this" behavior depends on the answer.

## 3. Features as views over the log

In rough order of dependency. Sizes are guesses.

1. **Roll log on the map** (small, **[Proposed]**). `roll_history` already exists and is only displayed on the sheet view, so this is mostly a display job. Open: whether 10 entries is enough, and whether some rolls should be DM-only.
2. **Condition and HP alerts to the party** (small, **[Proposed]**). Needs events for sheet changes, which do not exist today.
3. **Lorebook and session recaps** (medium, **[Proposed]**). The event log, cleaned up and summarized, readable between sessions. Works without AI; AI could write the summaries.
4. **World prompts** (large, **[Proposed]**). DM-prepared interactions attached to a scene ("Investigate bookshelf") that appear for characters whose proficiencies or background fit. Clicking one starts the roll, plus any follow-up abilities other players are prompted for. Depends on scenes, the roll pipeline and an ordering model.

## 4. Scenes (multiple maps)

**[Proposed]** The DM prepares several scenes before a session (a world map, a town, an inn). Each scene has a map, tokens and NPCs, fog, and optional prompts. One scene is live at a time and the party sees only that one.

Terminology collision: **[Verified]** "scene" already means "this token is on the board" (`inScene`, `set_token_scene`, `clear_scene`). **[Open]** Rename the new concept (map, location, encounter-set?) or rename the existing token flag.

Gaps against today's code:

- **[Verified]** Tokens have no board or scene field, so each scene would need its own token positions.
- **[Open]** What `set_board` does to fog when switching. Tests suggest fog reveals reset in some cases. Not traced.
- **[Open]** Storage. Several scenes with tokens, fog and prompts is a lot of new data. This is where issue #1 (consolidated `CampaignState`) matters most, so scene data should be designed together with it, not bolted onto the current three-file layout.

## 5. Character sheet redesign

**[Proposed]** A cleaner player-facing sheet: the numbers that matter at the top, hints derived from proficiencies and background (for example, investigation prompts for characters proficient in it), the dice roller and the other players still visible while the sheet is open. The roll log moves to the map view.

This is frontend work (`SheetView.tsx` is about 1,700 lines) and does not depend on the storage decision, so it can start at any time.

## 6. Assets

Two separate problems:

- **[Proposed, later]** Per-scene asset manifests, so players load only what the live scene uses. A performance optimization. Wait until loading is actually slow.
- **[Open]** Ruleset asset packs (for example, a Beginner's Guide set versus a fuller set). Open: what the project ships versus what each group supplies, given that official art and text are copyrighted.

## 7. AI layer (optional, last)

**[Proposed]** An agent fed the campaign by the DM, reading the event log to help during play: NPC attitude notes, suggested dialogue routes, optional pre-written NPC speech with a voice matched to the NPC. Principle: the AI suggests and the DM decides.

Open: provider, cost per session, response latency, voice generation, and how much campaign material gets sent to an outside service. This layer is worth building only after the event log is useful without it.

## 8. Interaction ordering and "broadcast of intent"

**[Proposed]** When several characters could react to the same event, there needs to be a strict order and a way to announce intent, possibly only to players within range.

**[Open]** The encounter system already models turn order and action economy, and this should build on it. It also depends on the unused visibility filter above. This is the largest and riskiest item.

## 9. Dependencies and a suggested order

| Step | Work | Depends on |
|---|---|---|
| 1 | Decide the storage design with issue #1, including where events and scenes live | Conversation among contributors |
| 2 | Event log skeleton | Step 1 |
| 3 | Roll log on map, sheet redesign (these two can run in parallel) | Step 2 (roll log); nothing (sheet) |
| 4 | Scenes | Step 1 |
| 5 | Condition alerts, world prompts, lorebook | Steps 2 and 4 |
| 6 | Ordering and intent broadcast | Steps 2 and 4, encounter system |
| 7 | AI layer | Steps 2 to 5 |

Open issues for reference: #1 (consolidate campaign state), #2 (equipment and inventory primitives), #5 (campaign builder toolbox). **[Proposed]** Leave #1 until its design is agreed, since scenes and events both write new data into whatever it settles on.

## 10. Other issues found along the way

All **[Verified]**, and all matter more once real data and more players are involved:

- A bad or mistyped `player=` key silently becomes `player-1` and controls that character. With `dm` being only a URL value, this belongs with whatever identity work happens later.
- The sync race in section 1 (low severity, self-corrects on the board view).
- Running the Playwright e2e tests modifies tracked `campaigns/spell-test-campaign/party/party.json`.
- A server test hangs instead of failing when board images are git LFS pointer files (a fresh clone without `git lfs install`).
- The full backend suite takes about 5.5 minutes, so targeted test runs matter for AI-assisted work.

## 11. Working agreements (proposal)

**[Proposed]** A small shared workflow so that people and their AI tools stay on the same page:

- `CLAUDE.md` holds project facts only: stack, commands, layout, architecture, known gaps. It is safe for any agent to load.
- Personal workflow rules live in separate files (see `Matt_CLAUDE.md`) and are not loaded unless someone opts in.
- Investigate before changing code. Review the real diff, not a summary. Keep commits small and stage files by name.
- Larger changes (storage, identity, anything in issue #1) get a short design discussion first.

**[Open]** Which AI tools other contributors use. Claude Code reads `CLAUDE.md` and not `AGENTS.md`, so another agent may need its own entry point.

## 12. Questions for discussion

1. Is the target a game among friends, or something broader later? This changes auth, hosting and AI costs.
2. Who decides the storage design for issue #1, and when?
3. Is a typed event log the right foundation, or is there a simpler path to the first few features?
4. What should "scene" mean going forward?
5. Which of these ideas does anyone not want?
