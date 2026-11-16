# Matt's personal workflow rules for Claude Code

This file is not loaded automatically; it is pulled in by a gitignored `CLAUDE.local.md` containing the line `@Matt_CLAUDE.md`, and other contributors can ignore it.

## Working with Claude (chat) — review checkpoints

The user runs a second Claude instance ("chat") as an independent reviewer and
teaching aid. Copy/paste between chat and this session is manual and
intentionally infrequent — do not assume chat has seen anything in this
session unless the user tells you so.

### Teaching mode (current default)

The user is new to this codebase and to this stack (FastAPI, WebSockets,
typed Python rules engines) generally. Until they say otherwise:

- Do not add, edit, or refactor code. Read and explain only.
- When walking through a subsystem (e.g. the roll pipeline, a class's rules
  file, the WS message handler), stop at natural checkpoints — end of a file,
  end of a concept, a good "does this make sense so far" point — and prompt
  the user to relay a short summary to chat before continuing. Don't wait
  until an entire subsystem is covered; checkpoint more often than that.
- When surfacing something to relay, give the user a short paste-ready
  summary block (what was covered, what file/lines, one open question if
  any) rather than making them write it themselves.

### Implementation mode (once changes start)

Follow the three-phase pattern: investigate-only, then implement only after
explicit user approval, then produce a real diff.

- Investigate-only prompts must make no changes.
- After any implementation step, before staging anything, output the
  complete real diff (`git diff`, or full before/after text for untracked
  files) — not a prose summary of what changed.
- **Pause before any `git add` or `git commit` and wait for the user.** Do
  not stage or commit on your own initiative even if the diff looks clean.
  At this pause, give the user a short paste-ready summary (files touched,
  what changed, why, and the diff itself if short enough) to relay to chat
  for review before they approve the commit.
- If you discover something unexpected mid-investigation (a rule that
  doesn't match DESIGN.md's philosophy, a place two files disagree, a gap
  bigger than the scoped task) — stop and flag it to the user rather than
  deciding how to handle it yourself.
- Scope stays tight: touch only the files/functions the user named. If a
  change seems to require touching something outside that scope, stop and
  say so instead of expanding scope silently.
