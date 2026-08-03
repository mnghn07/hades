# hades — Roadmap

> Status: draft for review — 2026-07-06

## Positioning

The ecosystem splits into three camps: **launchers** that spawn and control agent sessions (ccmanager, claude-squad, agent-deck), **analytics** for tokens and cost (ccusage, sniffly), and **history viewers** (claude-code-history-viewer, claude-history, clauhist).

Nobody owns the **passive, zero-config, cross-tool observer**: install nothing per-project, spawn nothing, just run `hades` and see the state of everything. `attention` and `watch` are the differentiators. Lightness is the edge — the goal is not to become a worse ccmanager.

**Guiding promise (keep):** everything stays local. No cloud, no registration, no telemetry.

---

## v1.2 — Make the core signal honest ✅ done

The 3-minute mtime heuristic is the weakest link in the core feature. Replace inference with facts where facts are available.

- ~~**`hades hook install`**~~ — done: registers `Stop`/`Notification`/`UserPromptSubmit` hooks in `~/.claude/settings.json`; `waiting.py` prefers the hook-reported `waiting_since` over the mtime heuristic when present. Time heuristic remains fallback for codex/gemini (no hook API). (Context: [anthropics/claude-code#36885](https://github.com/anthropics/claude-code/issues/36885).)
- ~~**Verify process detection per tool**~~ — done: `_classify` covered by tests (`test_process_checker.py`).
- ~~**`--json` on every command**~~ — done: JSON output across list/attention/stats/search, with test coverage.
- ~~**`--no-color` / plain output when piped**~~ — done: shared `Console` instance, `--no-color` flag on the main callback.

## v1.3 — Close the loop ✅ done

Attention list becomes actionable instead of read-only. (Dropped `hades resume` and fuzzy picking — hades observes and surfaces, it doesn't launch; the user switches to the tool directly when a session needs attention.)

- ~~**Linux notifications**~~ — done: `notify-send` alongside `osascript` in `watch.py`, silently no-ops if the binary is missing.
- ~~**Interactive `watch`**~~ — done: `j`/`k` moves a highlighted row cursor, `d` archives the highlighted session in place, footer legend always visible. cbreak-mode stdin reading via `termios`/`tty`/`select` (POSIX only — falls back to view-only when stdin isn't a real tty or on Windows). Archive logic factored out of `cmd_archive` into `archive_session_by_id` so both the CLI command and the watch keybinding share it.
- ~~**Attention threshold config**~~ — done: `hades config get/set/list` reads/writes a small typed-default registry (`hades/config.py`) persisted to `config.json` next to the index DB; `HADES_WAIT_THRESHOLD_MINUTES` still works as a one-off env override on top of it. Backs `attention`, `stats`, and `watch` via `waiting.wait_threshold_minutes()`. (Only affects the mtime-heuristic path — hook-reported `waiting_since` sessions are already known-waiting regardless of threshold.) Adding a future setting is one line in `config.DEFAULTS`.

## v2 — Widen the funnel

- **More sources** — OpenCode, Copilot CLI, Aider still open. Each is ~80 lines given the `BaseSource` ABC; this is where the architecture pays off.
  - ~~**Cursor**~~ — done: `hades/sources/cursor.py` reads `~/.cursor/projects/*/agent-transcripts/*/*.jsonl` (the CLI agent's own transcripts, not the IDE's chat storage, which lives in a separate VSCode-style SQLite store and wasn't targeted). No `cwd` or per-turn timestamps in the format — `project_path` is decoded from the dash-encoded project dir name (same ambiguity as Claude's decoder for literal hyphens/dots), `last_active_at` uses file mtime (exact — each turn is appended live), `started_at` uses an embedded `<timestamp>` tag on the first user turn when present (~60% of turns have one) else file birthtime. No token/cost data in the format. "Running" status not yet wired into `process_checker._classify` — the live process name for the Cursor CLI agent is unconfirmed, so cursor sessions stay idle/ended. Verified against 428 real transcripts on a dev machine.
- ~~**Per-session token count**~~ — done: `models.Session.token_count`, populated for Claude (summed input/output/cache tokens from each turn's `usage` block) and shown in `list`/`stats` (table + `--json`). Codex/gemini/cowork report 0 — no local sample data to confirm their usage field shape yet.
- ~~**$ cost column**~~ — done: `hades/pricing.py` prices each turn by its own `usage.model` (prefix-matched against a small `$/1M` table for current Claude models; cache write/read derived as 1.25x/0.1x of input price per Anthropic's published multipliers). `models.Session.cost_usd` populated for Claude, summed per session, shown in `list`/`stats` (table + `--json`). Unrecognized models price at $0 rather than guessing. Still open: live-ticking token/cost in `watch`, and token/cost parsing for codex/gemini/cowork once their usage format is confirmed.
- **Homebrew tap** — after PyPI validation (per PRD).

## v3 — The ambitious version

- **`hades serve`** — localhost dashboard (sniffly-style) reading the same SQLite DB. The CLI stays the primary interface; the dashboard is a view, not a second product.
- **Daemon mode** — `watch` decoupled from a terminal pane; notifications fire even with no terminal open.
- **Plugin API** — a source is a pip entry point; the community adds tools without touching core.
- **Multi-machine (only if demanded)** — sync the SQLite *index*, never transcripts. The everything-stays-local promise is a selling point; don't spend it cheaply.

---

## Positioning decision (settled 2026-07-06)

hades serves the person running a handful of sessions who needs a **nudge**, not a control plane. It observes and surfaces; it does not spawn or orchestrate. v1.2/v1.3 serve this user fully.

Consequences: daemon + dashboard (v3) stay *views* over the same local index, never orchestration. Competing with agent-deck/ccmanager on launching is explicitly out of scope — lightness is the moat.

---

## Landscape reference

| Tool | Camp | Worth stealing |
|---|---|---|
| [ccmanager](https://github.com/kbwo/ccmanager) | launcher | hooks on status change; worktree awareness |
| [claude-squad](https://github.com/smtg-ai/claude-squad) | launcher | tmux workspace isolation |
| [agent-deck](https://github.com/asheshgoplani/agent-deck) | launcher/observer | notify daemon on state *transitions*; tmux status bar integration |
| [ccusage](https://ccusage.com/) | analytics | breadth of supported CLIs; npx zero-install UX |
| [sniffly](https://github.com/chiphuyen/sniffly) | analytics | localhost dashboard; error analysis |
| [claude-history](https://github.com/raine/claude-history) | viewer | resume/fork directly from search picker (not adopting — out of scope for hades) |
| [claude-code-history-viewer](https://github.com/jhlee0409/claude-code-history-viewer) | viewer | multi-provider ambition (claims 25) |
| [clauhist](https://dev.to/lef237/clauhist-browse-full-claude-code-history-and-resume-sessions-across-projects-1c1o) | viewer | thin fzf wrapper, no extra DB — honest minimalism |
