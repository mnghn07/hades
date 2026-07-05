# hades

> *The dead or the living will be seen by Hades. No AI session escapes.*

A local CLI for viewing, searching, and managing your AI coding sessions across Claude Code, Codex CLI, Gemini CLI, and Cowork — all from one terminal.

[![PyPI](https://img.shields.io/pypi/v/hades-cli)](https://pypi.org/project/hades-cli/)
[![Python](https://img.shields.io/pypi/pyversions/hades-cli)](https://pypi.org/project/hades-cli/)

## Why

You run multiple AI tools across projects. Each keeps its own session store with no cross-tool view. Sessions notify you when they're waiting — but you miss them when music's playing or you're heads-down in another project. `hades` is a single pane of glass: see what's running, what's waiting, what happened.

## Install

```bash
pipx install hades-cli       # recommended
uv tool install hades-cli    # or with uv
pip install hades-cli        # or plain pip
```

## Commands

```bash
hades list                                    # all sessions, all tools
hades list --tool claude --active             # filter by tool or status
hades show <session-id>                       # pretty-print a transcript
hades show <session-id> --full                # expand tool calls too
hades attention                               # what's been waiting on you
hades watch                                   # live view + macOS notifications
hades watch --no-notify                       # live view only
```

## How it works

On every command, `hades` scans your local session files, indexes them into a SQLite database (`~/.local/share/hades/index.db` on Linux, `~/Library/Application Support/hades/` on macOS), and cross-references running processes to show live status.

Only changed files are re-parsed (mtime-based), so subsequent runs are fast.

**`hades list`** shows all sessions across tools, sorted by most recently active:

```
TOOL      PROJECT              LAST ACTIVE    MSGS  STATUS
claude    hades                2m ago          47   ● running
claude    dotfiles             3h ago          12   ○ idle
gemini    api-server           1d ago           8   ○ idle
codex     ml-pipeline          3d ago          31   ✕ ended
```

**`hades attention`** surfaces sessions that have been waiting on you for more than 3 minutes (within the last 24 hours), sorted by longest wait first.

**`hades watch`** keeps a live view open in a split pane and fires a persistent macOS notification when a session crosses the waiting threshold — so missed audio alerts don't cost you time.

## Sources

| Tool | Default path | Format |
|---|---|---|
| Claude Code | `~/.claude/projects/` | JSONL |
| Codex CLI | `~/.codex/sessions/` | JSONL |
| Gemini CLI | `~/.gemini/tmp/` | JSON |
| Cowork | `~/Library/Application Support/Claude/local-agent-mode-sessions/` | JSON |

Paths are auto-discovered — no config needed. Override any with env vars:

```bash
HADES_CLAUDE_PATH=~/custom/path hades list
```

## Roadmap

### v1.1

- `hades search <term>` — full-text search across all transcripts
- `hades stats` — session counts, message volume, most active projects
- `hades thinking <session-id>` — extract just the model's reasoning blocks
- `hades export`, `hades archive`, `hades rm`

### v2

- Cursor support (via [`cursor-session`](https://github.com/iksnae/cursor-session))
- Homebrew tap

## License

MIT
