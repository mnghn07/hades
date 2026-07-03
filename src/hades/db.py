from pathlib import Path

import sqlite_utils
from platformdirs import user_data_dir

DB_PATH = Path(user_data_dir("hades")) / "index.db"


def get_db() -> sqlite_utils.Database:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite_utils.Database(DB_PATH)
    _ensure_schema(db)
    return db


def _ensure_schema(db: sqlite_utils.Database) -> None:
    if "sessions" not in db.table_names():
        db["sessions"].create({
            "id": str,
            "tool": str,
            "project_path": str,
            "started_at": str,
            "last_active_at": str,
            "message_count": int,
            "status": str,
            "raw_path": str,
            "title": str,
            "file_mtime": float,
        }, pk="id")

    if "sessions_fts" not in db.table_names():
        db["sessions_fts"].create({
            "session_id": str,
            "human_messages": str,
            "assistant_messages": str,
        }, pk="session_id")
        db.execute("CREATE VIRTUAL TABLE IF NOT EXISTS sessions_fts_idx USING fts5(session_id UNINDEXED, human_messages, assistant_messages, content=sessions_fts, content_rowid=rowid)")
