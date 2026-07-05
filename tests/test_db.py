import sqlite_utils

from hades.db import get_db


def test_get_db_creates_expected_schema(db_path):
    db = get_db()
    assert db_path.exists()
    assert "sessions" in db.table_names()
    assert "sessions_fts" in db.table_names()

    cols = {c.name for c in db["sessions"].columns}
    assert {"id", "tool", "raw_path", "human_messages", "assistant_messages", "is_archived"} <= cols


def test_get_db_migrates_columns_onto_existing_table(db_path):
    existing = sqlite_utils.Database(db_path)
    existing["sessions"].create({"id": str, "tool": str}, pk="id")  # pylint: disable=no-member
    existing.close()

    db = get_db()
    cols = {c.name for c in db["sessions"].columns}
    assert "is_archived" in cols
    assert "human_messages" in cols
    assert "file_mtime" in cols


def test_get_db_is_idempotent(db_path):
    get_db()
    db = get_db()
    assert db_path.exists()
    assert "sessions" in db.table_names()
