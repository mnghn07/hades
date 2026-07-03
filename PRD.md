# hades — Product Requirements Document

## Problem

You run multiple AI coding sessions across projects simultaneously. Each tool (Claude Code, Codex, Gemini, Cowork) keeps its own session store with no cross-tool view. Sessions emit sound notifications when waiting for input — but you miss them when music is playing or you're deep in another project. There's no single command that tells you what's blocked, what crashed, and what's been waiting on you the longest.

## Solution

A local CLI called `hades` that indexes all AI sessions from all tools into a single SQLite database and surfaces what needs your attention — instantly, with a live watch mode that fires macOS notifications so missed audio alerts don't cost you time.

---

## Design Decisions

### Distribution
- **PyPI first** (`hades-cli` package → installs `hades` binary)
- Homebrew tap later, after PyPI validation
- Built with `uv` + `pyproject.toml` — `uv build` + `uv publish` for releases

### Runtime
- **Python** (not zsh) — portable, testable, distributable
- `uv` for local dev and packaging

### CLI name
- Binary: `hades`
- PyPI package: `hades-cli` (`hades` is taken on PyPI — a job processing daemon)

### Core libraries

| Library | Role |
|---|---|
| `typer` | CLI framework — type hints become flags automatically |
| `rich` | Terminal output — tables, colors, live display |
| `ijson` | Streaming JSONL — large session files without loading into memory |
| `psutil` | Live process check — cross-platform `ps aux` |
| `platformdirs` | Correct config/data paths per OS |
| `pendulum` | Human-friendly datetimes ("3h ago", "since 2d" parsing) |
| `sqlite-utils` | SQLite index management |
| `pytest` + `typer[testing]` | Testing |

---

## Data Model

### Normalized Session schema

```python
@dataclass
class Session:
    id: str                # tool-scoped unique id
    tool: str              # "claude" | "codex" | "gemini" | "cowork"
    project_path: str      # working directory the session ran in
    started_at: datetime   # first message timestamp
    last_active_at: datetime  # most recent message timestamp
    message_count: int     # number of turns
    status: str            # "running" | "idle" | "ended"
    raw_path: Path         # path to source file(s) on disk
    title: str | None      # first human message, truncated
```

No `token_count` or `cost` in v1 — those fields exist in some formats but not others. Promote to schema in v1.1 once each source's usage fields are verified.

---

## Storage

- **SQLite index** at `~/.local/share/hades/index.db`
- Mtime-based invalidation — only re-parses files whose mtime changed since last seen
- **FTS5 virtual table** for full-text search across `human_messages` and `assistant_messages` columns
- Index is updated transparently on every command invocation — no explicit `hades sync` needed
- Full transcript stays on disk; only `hades show` and `hades search` read raw files

---

## Source Discovery

1. Check hardcoded default paths per tool (macOS defaults)
2. Probe fallback locations if default doesn't exist
3. Env-var overrides for power users:
   - `HADES_CLAUDE_PATH`
   - `HADES_CODEX_PATH`
   - `HADES_GEMINI_PATH`
   - `HADES_COWORK_PATH`
4. No config file in v1

### Default paths

| Tool | Default path |
|---|---|
| Claude Code | `~/.claude/projects/` |
| Codex CLI | `~/.codex/sessions/` |
| Gemini CLI | `~/.gemini/tmp/` |
| Cowork | `~/Library/Application Support/Claude/local-agent-mode-sessions/` |

---

## Output

- **Rich formatting by default in TTY** — opinionated, rtk-style. Tables, colors, relative timestamps, status badges.
- **Plain text when piped** — auto-detected via TTY check, grep-friendly
- **`--json` flag** for structured output on any command
- **`--no-color`** for CI/logging contexts

Example `hades list` output:

```
TOOL      PROJECT              LAST ACTIVE    MSGS  STATUS
claude    hades                2m ago         47    ● running
claude    dotfiles             3h ago         12    ○ idle
gemini    api-server           1d ago         8     ○ idle
codex     ml-pipeline          3d ago         31    ✕ ended
```

---

## Feature Specs

### `hades list`
List all sessions across tools with normalized metadata. Filters: `--tool`, `--active`, `--since`.

### `hades show <session-id>`
Pretty-print a single transcript. Tool calls collapsed by default, `--full` to expand.

### `hades attention`
Surface sessions worth acting on, sorted by wait time (longest first).

**Heuristics:**
- **Waiting on you** — last message is an assistant turn ending with `?`, or a tool-call requesting approval/permission, AND the session has been in this state for **>3 minutes**. Wait duration shown as the primary sort key.
- **Stale/crashed** — process no longer running but session file shows `status: running`. Flagged immediately.
- Errors demoted — not a primary attention signal. Use `hades show` to investigate.

### `hades watch`
Live-updating terminal view of the attention list (like `htop`). Refreshes every 30 seconds.

- Designed to run in a persistent split pane
- **`--notify` is ON by default** — fires a macOS system notification (persistent banner, not just sound) when a new session crosses the waiting threshold
- Use `--no-notify` to disable notifications

This directly solves the missed-audio-notification problem: a visual banner persists until dismissed, unlike a sound that disappears through music.

---

## v1 Build Order

1. Source readers (Claude, Codex, Gemini, Cowork) + normalization
2. SQLite index + mtime invalidation
3. `hades list`
4. `hades show`
5. `hades attention`
6. `hades watch` + `--notify`
7. Package + publish to PyPI

## v1.1 (after first real use)

- FTS5 search → `hades search`
- `hades stats`
- `hades thinking`
- `hades export` / `hades archive` / `hades rm`
- Attention threshold config (currently hardcoded at 3 min)
- Homebrew tap

## v2

- Cursor support via `cursor-session` wrapper

---

## Out of scope (all versions until stated)

- Editing session content
- GUI/TUI
- Cloud sync or cross-machine aggregation
- Billing-accurate token/cost numbers
- PowerShell / Windows (platform detection via `platformdirs` is in place, full support later)
