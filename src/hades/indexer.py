import sqlite_utils

from hades.sources import ALL_SOURCES


def refresh_index(db: sqlite_utils.Database) -> None:
    """Scan all sources, upsert changed/new sessions, remove stale rows."""
    indexed_paths: set[str] = set()

    for source_cls in ALL_SOURCES:
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

            db["sessions"].upsert(row, pk="id")

    _remove_stale(db, indexed_paths)


def _remove_stale(db: sqlite_utils.Database, indexed_paths: set[str]) -> None:
    """Delete index rows for session files that no longer exist on disk."""
    if "sessions" not in db.table_names():
        return

    db_paths = [row[0] for row in db.execute("SELECT raw_path FROM sessions").fetchall()]
    stale = [p for p in db_paths if p not in indexed_paths]

    for path_str in stale:
        db.execute("DELETE FROM sessions WHERE raw_path = ?", [path_str])
