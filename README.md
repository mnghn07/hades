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

## Usage

```bash
hades list                                    # sessions from the last 3 days (default)
hades list --tool claude --active             # filter by tool or status
hades list --day 1 --hour 12                  # sessions active within the last 1d 12h
hades list --all                              # every session ever indexed
hades show <session-id>                       # pretty-print a transcript
hades show <session-id> --full                # expand tool calls too
hades attention                               # what's been waiting on you
hades stats                                   # summary + per-tool breakdown
hades stats --day 1                           # scoped to the last 24h
hades search "some query"                     # full-text search across transcripts
hades search "some query" --tool claude -n 5  # filter by tool, cap results
hades export <session-id>                     # dump transcript as JSON
hades export <session-id> --format markdown -o out.md
hades archive <session-id>                    # move transcript to the archive, hide it from list/search
hades purge <session-id>                      # permanently delete a transcript (asks to confirm)
hades watch                                   # live view + macOS notifications
hades watch --no-notify                       # live view only
```

## How it works

On every command, `hades` scans your local session files, indexes them into a SQLite database, and checks running processes to show live status. Only changed files are re-parsed, so runs stay fast. Everything stays on your machine — nothing is sent anywhere.

## Commands

**`hades list`** shows all sessions across tools, sorted by most recently active. Background sessions spawned by other tooling (observers, hooks, ...) are grouped into a single summary row per tool, instead of flooding the table:

```
TOOL      PROJECT              TYPE      LAST ACTIVE    MSGS  STATUS
claude    hades                human     2m ago          47   ● running
claude    claude-mem           agent     2m ago         512   ● running
claude    dotfiles             human     3h ago          12   ○ idle
gemini    api-server           human     1d ago           8   ○ idle
codex     ml-pipeline          human     3d ago          31   ✕ ended
```

**`hades show`** pretty-prints a single transcript, tool calls collapsed by default (`--full` to expand).

**`hades attention`** lists sessions that have been waiting on you for 3+ minutes, longest wait first.

**`hades stats`** summarizes total sessions/messages, a per-tool breakdown, and how many sessions are currently waiting on you.

**`hades search`** does a full-text search across every transcript's human and assistant messages, with a highlighted snippet for each match.

**`hades export`** dumps a session's transcript to a JSON or Markdown file, for sharing or archiving outside `hades`.

**`hades archive`** relocates a session's raw file into `hades`'s own archive directory and hides it from `list`/`search` by default (pass `--show-archived` to see it again). The file isn't deleted — `hades purge` is the destructive one.

**`hades purge`** permanently deletes a session's transcript file and its index entry. Prompts for confirmation unless you pass `--yes`.

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

Versioning is derived from git tags (via `hatch-vcs`) — there's nothing to bump by hand. Pushing a tag like `v0.1.1` builds and publishes that version to PyPI automatically:

```bash
git tag v0.1.1
git push origin v0.1.1
```

## License

MIT
