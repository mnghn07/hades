from pathlib import Path

import pytest

from hades.db import get_db
from hades.indexer import refresh_index
from hades.sources.claude import ClaudeSource


def _point_at_claude_root(monkeypatch, claude_session_file: Path):
    monkeypatch.setenv("HADES_CLAUDE_PATH", str(claude_session_file.parent.parent))
    monkeypatch.setattr("hades.indexer.ALL_SOURCES", [ClaudeSource])


@pytest.mark.usefixtures("db_path")
def test_refresh_index_indexes_session_and_populates_fts(claude_session_file, monkeypatch):
    _point_at_claude_root(monkeypatch, claude_session_file)
    db = get_db()

    refresh_index(db)

    rows = list(db.execute("SELECT id, tool, message_count FROM sessions").fetchall())
    assert len(rows) == 1
    session_id, tool, message_count = rows[0]
    assert tool == "claude"
    assert message_count == 2

    fts_row = db.execute(
        "SELECT human_messages, assistant_messages FROM sessions_fts WHERE id = ?", [session_id]
    ).fetchone()
    assert fts_row is not None
    assert "CLI tool" in fts_row[0]
    assert "typer" in fts_row[1]


@pytest.mark.usefixtures("db_path")
def test_refresh_index_skips_reparsing_unchanged_files(claude_session_file, monkeypatch):
    _point_at_claude_root(monkeypatch, claude_session_file)
    db = get_db()

    refresh_index(db)
    first_mtime = db.execute("SELECT file_mtime FROM sessions").fetchone()[0]

    refresh_index(db)
    second_mtime = db.execute("SELECT file_mtime FROM sessions").fetchone()[0]

    assert first_mtime == second_mtime


@pytest.mark.usefixtures("db_path")
def test_refresh_index_removes_rows_for_deleted_files(claude_session_file, monkeypatch):
    _point_at_claude_root(monkeypatch, claude_session_file)
    db = get_db()
    refresh_index(db)
    session_id = db.execute("SELECT id FROM sessions").fetchone()[0]

    claude_session_file.unlink()
    refresh_index(db)

    assert db.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 0
    assert db.execute("SELECT COUNT(*) FROM sessions_fts WHERE id = ?", [session_id]).fetchone()[0] == 0


@pytest.mark.usefixtures("db_path")
def test_refresh_index_keeps_archived_rows_when_source_file_is_gone(claude_session_file, monkeypatch):
    _point_at_claude_root(monkeypatch, claude_session_file)
    db = get_db()
    refresh_index(db)
    session_id = db.execute("SELECT id FROM sessions").fetchone()[0]
    db.execute("UPDATE sessions SET is_archived = 1 WHERE id = ?", [session_id])

    claude_session_file.unlink()
    refresh_index(db)

    rows = list(db.execute("SELECT id FROM sessions").fetchall())
    assert len(rows) == 1
    assert rows[0][0] == session_id
