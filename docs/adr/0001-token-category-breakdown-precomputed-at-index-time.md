# Token category breakdown is precomputed at index time, not re-parsed on demand

Status: accepted

Per-session token category counts (input/output/cache-write/cache-read — see `CONTEXT.md`) will be extracted by each `Source` and stored as columns on the indexed `Session` row, the same way `token_count` and `cost_usd` already are — not recomputed by re-reading raw transcripts each time `stats`/`serve` runs.

We considered computing it on demand instead: no schema migration, always fresh. Rejected because it doesn't scale with transcript count/size, requires `raw_path` to remain valid indefinitely, and breaks the precedent every other derived Session field already follows (parse once at scan time, query the index after). A future need to re-derive from raw data (e.g. per-model breakdown) can still read `raw_path` — this ADR only settles where the *category* breakdown lives.
