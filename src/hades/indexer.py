from pathlib import Path

import sqlite_utils

from hades.config import get_enabled_tools
from hades.sources import ALL_SOURCES


def refresh_index(db: sqlite_utils.Database) -> None:
    """Scan enabled sources, upsert changed/new/stale-parsed sessions, remove stale rows."""
    enabled_tools = get_enabled_tools()
    indexed_paths: set[str] = set()
    discovered: dict[str, type] = {}

    for source_cls in ALL_SOURCES:
        if source_cls.name not in enabled_tools:
            # Disabled tool: don't scan it, and don't touch its existing index
            # rows either — same treatment as a source whose store isn't
            # reachable right now (see _remove_stale below).
            continue
        if source_cls.discover_root() is None:
            # Source store not found (unmounted disk, bad env override, tool not
            # installed). Skip it entirely — including stale removal — so a
            # temporarily missing store doesn't wipe its slice of the index.
            continue
        discovered[source_cls.name] = source_cls

        for path in source_cls.list_files():
            path_str = str(path)
            indexed_paths.add(path_str)

            try:
                mtime = path.stat().st_mtime
            except OSError:
                continue

            existing = db.execute(
                "SELECT file_mtime, parser_version FROM sessions WHERE raw_path = ?", [path_str]
            ).fetchone()

            if existing and existing[0] == mtime and (existing[1] or 0) >= source_cls.PARSER_VERSION:
                continue

            _reparse_and_upsert(db, source_cls, path, mtime)

    _reheal_archived(db, discovered)
    _remove_stale(db, indexed_paths, set(discovered))
    db.conn.commit()


def force_reindex(db: sqlite_utils.Database, tool: str | None = None, session_id: str | None = None) -> int:
    """Bypass the mtime/parser_version checks and reparse matching sessions now.

    Escape hatch for `hades reindex` — the mtime/version check in refresh_index
    self-heals the common case, but a source whose parser changed without a
    version bump (or a one-off re-scrape request) needs a manual trigger.
    """
    source_map = {source_cls.name: source_cls for source_cls in ALL_SOURCES}

    query = "SELECT id, tool, raw_path FROM sessions WHERE 1=1"
    params: list[str] = []
    if tool:
        query += " AND tool = ?"
        params.append(tool)
    if session_id:
        query += " AND id = ?"
        params.append(session_id)

    reindexed = 0
    for _id, tool_name, raw_path in db.execute(query, params).fetchall():
        source_cls = source_map.get(tool_name)
        if source_cls is None:
            continue
        path = Path(raw_path)
        if not path.exists():
            continue
        if _reparse_and_upsert(db, source_cls, path, path.stat().st_mtime) is not None:
            reindexed += 1

    db.conn.commit()
    return reindexed


def _reparse_and_upsert(db: sqlite_utils.Database, source_cls: type, path: Path, mtime: float) -> str | None:
    """Parse `path` and upsert/refresh its row (and FTS entry). Returns the session id, or None."""
    session = source_cls.parse_file(path)
    if session is None:
        return None

    path_str = str(path)
    human_text, assistant_text = source_cls.extract_messages(path)

    row = {
        "id": session.id,
        "tool": session.tool,
        "project_path": session.project_path,
        "started_at": session.started_at.isoformat(),
        "last_active_at": session.last_active_at.isoformat(),
        "message_count": session.message_count,
        "token_count": session.token_count,
        "cost_usd": session.cost_usd,
        "input_tokens": session.input_tokens,
        "output_tokens": session.output_tokens,
        "cache_write_tokens": session.cache_write_tokens,
        "cache_read_tokens": session.cache_read_tokens,
        "status": session.status,
        "raw_path": path_str,
        "title": session.title,
        "file_mtime": mtime,
        "human_messages": human_text,
        "assistant_messages": assistant_text,
        "parser_version": source_cls.PARSER_VERSION,
    }

    # A previous version may have stored this file under a different id
    # (or this id under a different file). Clear both — including the
    # FTS row, which would otherwise be orphaned — before upserting.
    for (old_id,) in db.execute(
        "SELECT id FROM sessions WHERE raw_path = ? AND id != ?",
        [path_str, session.id],
    ).fetchall():
        db.execute("DELETE FROM sessions WHERE id = ?", [old_id])
        db.execute("DELETE FROM sessions_fts WHERE id = ?", [old_id])
    db["sessions"].upsert(row, pk="id")

    db.execute("DELETE FROM sessions_fts WHERE id = ?", [session.id])
    db.execute(
        "INSERT INTO sessions_fts (id, human_messages, assistant_messages) VALUES (?, ?, ?)",
        [session.id, human_text, assistant_text],
    )
    return session.id


def _reheal_archived(db: sqlite_utils.Database, discovered: dict[str, type]) -> None:
    """Reparse archived sessions whose parser_version is behind — they're never
    visited by the live-file scan above since their file moved out of the
    source's discover_root into the archive.
    """
    if "sessions" not in db.table_names():
        return

    for tool_name, source_cls in discovered.items():
        rows = db.execute(
            "SELECT raw_path, parser_version FROM sessions WHERE is_archived = 1 AND tool = ?", [tool_name]
        ).fetchall()
        for raw_path, parser_version in rows:
            if (parser_version or 0) >= source_cls.PARSER_VERSION:
                continue
            path = Path(raw_path)
            if not path.exists():
                continue
            _reparse_and_upsert(db, source_cls, path, path.stat().st_mtime)


def _remove_stale(db: sqlite_utils.Database, indexed_paths: set[str], discovered_tools: set[str]) -> None:
    """Delete index rows for session files that no longer exist on disk.

    Only rows belonging to sources that were actually discovered this run are
    considered — an unreachable store must not erase its history.
    """
    if "sessions" not in db.table_names() or not discovered_tools:
        return

    placeholders = ",".join("?" * len(discovered_tools))
    db_rows = db.execute(
        f"SELECT id, raw_path FROM sessions WHERE is_archived IS NOT 1 AND tool IN ({placeholders})",
        list(discovered_tools),
    ).fetchall()
    stale_rows = [(session_id, path_str) for session_id, path_str in db_rows if path_str not in indexed_paths]

    for session_id, path_str in stale_rows:
        db.execute("DELETE FROM sessions WHERE raw_path = ?", [path_str])
        db.execute("DELETE FROM sessions_fts WHERE id = ?", [session_id])
