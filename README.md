# hades

> *The dead or the living will be seen by Hades. No AI session escapes.*

A local CLI for viewing, searching, analyzing, and managing your AI coding assistant sessions — Claude Code, Codex CLI, Gemini CLI, and Cowork — all from one place.

## Install

```bash
pip install hades-cli        # or
pipx install hades-cli       # or
uv tool install hades-cli
```

Homebrew tap coming after PyPI validation.

## Commands (v1)

```
hades list      [--tool claude|codex|gemini|cowork] [--active] [--since 2d]
hades show      <session-id>
hades attention
hades watch     [--notify]        # --notify is ON by default
```

## Commands (v1.1)

```
hades search    <term> [--tool ...] [--since ...] [--role human|assistant]
hades stats     [--by tool|day|project]
hades thinking  <session-id>
hades export    <session-id> [--md|--json] -o <file>
hades archive   <session-id> | --older-than 30d
hades rm        <session-id>
```

## Sources (v1)

| Tool | Session data location | Format |
|---|---|---|
| Claude Code | `~/.claude/projects/<encoded-path>/<session-id>.jsonl` | JSONL |
| Codex CLI | `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl` | JSONL |
| Gemini CLI | `~/.gemini/tmp/<project-hash>/chats/*.json` | JSON |
| Cowork | `~/Library/Application Support/Claude/local-agent-mode-sessions/**` | Mixed JSON |

Paths are auto-discovered: hardcoded defaults + fallback probing of known locations. Override via env vars (`HADES_CLAUDE_PATH`, `HADES_CODEX_PATH`, etc.). No config file in v1.

Cursor deferred to v2 via [`cursor-session`](https://github.com/iksnae/cursor-session).

## Out of scope for v1

- Cursor support
- Editing session content
- GUI/TUI
- Cloud sync or cross-machine aggregation
- Cost/token billing accuracy
