from pathlib import Path

import sqlite_utils
from platformdirs import user_data_dir

DB_PATH = Path(user_data_dir("hades")) / "index.db"


def get_db() -> sqlite_utils.Database:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite_utils.Database(DB_PATH)
    db.conn.execute("PRAGMA journal_mode=WAL")
    db.conn.execute("PRAGMA busy_timeout=5000")
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
            "human_messages": str,
            "assistant_messages": str,
            "is_archived": int,
        }, pk="id")
        db["sessions"].create_index(["raw_path"], unique=True)
    else:
        # Migrate: add columns added after initial schema
        existing_cols = {col.name for col in db["sessions"].columns}
        for col, col_type in [
            ("human_messages", str), ("assistant_messages", str),
            ("file_mtime", float), ("is_archived", int),
        ]:
            if col not in existing_cols:
                db["sessions"].add_column(col, col_type)

    if "sessions_fts" not in db.table_names():
        db.execute("""
            CREATE VIRTUAL TABLE sessions_fts USING fts5(
                id UNINDEXED,
                human_messages,
                assistant_messages
            )
        """)
