# hades

> *The dead or the living will be seen by Hades. No AI session escapes.*

A CLI for viewing, searching, and managing your AI coding sessions across Claude Code, Codex CLI, Gemini CLI, and Cowork — all from one terminal.

[![PyPI](https://img.shields.io/pypi/v/hades-cli)](https://pypi.org/project/hades-cli/)
[![Python](https://img.shields.io/pypi/pyversions/hades-cli)](https://pypi.org/project/hades-cli/)

## Why

Each AI tool keeps its own session store, so there's no single view across them — and it's easy to miss a session that's been waiting on you. `hades` gives you one place to see what's running, what's waiting, and what happened.

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
hades list --since 2d                         # filter by recency (e.g. 2d, 1w, 3h)
hades show <session-id>                       # pretty-print a transcript
hades show <session-id> --full                # expand tool calls too
hades attention                               # what's been waiting on you
hades watch                                   # live view + macOS notifications
hades watch --no-notify                       # live view only
```

## How it works

On every command, `hades` scans your local session files, indexes them into a SQLite database, and checks running processes to show live status. Only changed files are re-parsed, so runs stay fast.

**`hades list`** shows all sessions across tools, sorted by most recently active:

```
TOOL      PROJECT              LAST ACTIVE    MSGS  STATUS
claude    hades                2m ago          47   ● running
claude    dotfiles             3h ago          12   ○ idle
gemini    api-server           1d ago           8   ○ idle
codex     ml-pipeline          3d ago          31   ✕ ended
```

**`hades attention`** lists sessions that have been waiting on you for 3+ minutes, longest wait first.

**`hades watch`** keeps a live view open and fires a macOS notification when a session starts waiting.

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

## Development

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/mnghn07/hades.git
cd hades
uv sync --group dev     # install project + dev dependencies into .venv
```

```bash
uv run hades list       # run the CLI from source
uv run pytest           # run the test suite
uv run pylint $(git ls-files '*.py')   # lint
uv build                 # build sdist + wheel into dist/
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
