# hades

A local, zero-config observer over AI coding sessions across tools (Claude Code, Codex, Gemini, Cowork, Cursor, Antigravity, OpenClaw). It reads each tool's transcript files, indexes them into a local SQLite DB, and surfaces state — never launches or orchestrates sessions.

## Language

**Source**:
A per-tool adapter (`BaseSource` subclass) that discovers a tool's transcript files on disk and parses each one into a `Session`. One source per external tool.
_Avoid_: Scanner, adapter, plugin (reserved for the future plugin-API vision in the v3 roadmap).

**Session**:
The indexed record of one AI coding conversation — one transcript file (or, for Claude, one file within a possibly-resumed chain) reduced to its metadata: tool, project, timing, status, token/cost totals. Not the transcript content itself, which stays on disk at `raw_path`.
_Avoid_: Conversation, chat, transcript (transcript is the raw file; Session is the indexed record of it).

**Token category**:
One of the four buckets Anthropic's (and Anthropic-shaped) `usage` block reports per turn: input tokens (fresh, uncached), output tokens (generated), cache-write tokens (`cache_creation_input_tokens`), cache-read tokens (`cache_read_input_tokens`). This is the finest-grained "what did the tokens go to" the transcript data actually supports — it is *not* a breakdown by content type (system prompt vs. tool call vs. tool result), which the usage API doesn't report per-block and which hades does not attempt to estimate.
_Avoid_: Token type, usage breakdown (breakdown is the aggregate view across categories; category is one bucket within it).
