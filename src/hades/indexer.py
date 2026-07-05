import sqlite_utils

from hades.sources import ALL_SOURCES


def refresh_index(db: sqlite_utils.Database) -> None:
    """Scan all sources, upsert changed/new sessions, remove stale rows."""
    indexed_paths: set[str] = set()
    discovered_tools: set[str] = set()

    for source_cls in ALL_SOURCES:
        if source_cls.discover_root() is None:
            # Source store not found (unmounted disk, bad env override, tool not
            # installed). Skip it entirely — including stale removal — so a
            # temporarily missing store doesn't wipe its slice of the index.
            continue
        discovered_tools.add(source_cls.name)

        for path in source_cls.list_files():
            path_str = str(path)
            indexed_paths.add(path_str)

            try:
                mtime = path.stat().st_mtime
            except OSError:
                continue

            existing = db.execute(
                "SELECT file_mtime FROM sessions WHERE raw_path = ?", [path_str]
            ).fetchone()

            if existing and existing[0] == mtime:
                continue

            session = source_cls.parse_file(path)
            if session is None:
                continue

            human_text, assistant_text = source_cls.extract_messages(path)

            row = {
                "id": session.id,
                "tool": session.tool,
                "project_path": session.project_path,
                "started_at": session.started_at.isoformat(),
                "last_active_at": session.last_active_at.isoformat(),
                "message_count": session.message_count,
                "status": session.status,
                "raw_path": path_str,
                "title": session.title,
                "file_mtime": mtime,
                "human_messages": human_text,
                "assistant_messages": assistant_text,
            }

            # A previous version may have stored this file under a different id
            # (or this id under a different file). Clear both to keep the
            # unique raw_path index and pk consistent before upserting.
            db.execute(
                "DELETE FROM sessions WHERE raw_path = ? AND id != ?",
                [path_str, session.id],
            )
            db["sessions"].upsert(row, pk="id")

            db.execute("DELETE FROM sessions_fts WHERE id = ?", [session.id])
            db.execute(
                "INSERT INTO sessions_fts (id, human_messages, assistant_messages) VALUES (?, ?, ?)",
                [session.id, human_text, assistant_text],
            )

    _remove_stale(db, indexed_paths, discovered_tools)
    db.conn.commit()


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
