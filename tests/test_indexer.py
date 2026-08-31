from pathlib import Path

import pytest

from hades.config import set_tool_enabled
from hades.db import get_db
from hades.indexer import force_reindex, refresh_index
from hades.sources.claude import ClaudeSource
from hades.sources.cowork import CoworkSource
from hades.sources.cursor import CursorSource


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


@pytest.mark.usefixtures("db_path")
def test_refresh_index_indexes_cursor_session(cursor_session_file, monkeypatch):
    monkeypatch.setenv("HADES_CURSOR_PATH", str(cursor_session_file.parent.parent.parent.parent))
    monkeypatch.setattr("hades.indexer.ALL_SOURCES", [CursorSource])
    db = get_db()

    refresh_index(db)

    rows = list(db.execute("SELECT id, tool, project_path, message_count, title FROM sessions").fetchall())
    assert len(rows) == 1
    session_id, tool, project_path, message_count, title = rows[0]
    assert tool == "cursor"
    assert project_path == "/Users/test/project"
    assert message_count == 2
    assert title == "Help me build a CLI tool"

    fts_row = db.execute(
        "SELECT human_messages, assistant_messages FROM sessions_fts WHERE id = ?", [session_id]
    ).fetchone()
    assert fts_row is not None
    assert "CLI tool" in fts_row[0]
    assert "typer" in fts_row[1]


@pytest.mark.usefixtures("db_path")
def test_refresh_index_reparses_unchanged_file_when_parser_version_bumps(claude_session_file, monkeypatch):
    _point_at_claude_root(monkeypatch, claude_session_file)
    db = get_db()
    refresh_index(db)
    session_id, mtime, version = db.execute(
        "SELECT id, file_mtime, parser_version FROM sessions"
    ).fetchone()
    assert version == ClaudeSource.PARSER_VERSION

    # Simulate a parser bugfix that needs a one-time backfill: bump the
    # version without touching the file, and force the stored value stale.
    db.execute("UPDATE sessions SET parser_version = 0 WHERE id = ?", [session_id])
    refresh_index(db)

    new_mtime, new_version = db.execute(
        "SELECT file_mtime, parser_version FROM sessions WHERE id = ?", [session_id]
    ).fetchone()
    assert new_mtime == mtime
    assert new_version == ClaudeSource.PARSER_VERSION


@pytest.mark.usefixtures("db_path")
def test_refresh_index_heals_archived_session_on_version_bump(claude_session_file, monkeypatch):
    _point_at_claude_root(monkeypatch, claude_session_file)
    db = get_db()
    refresh_index(db)
    session_id = db.execute("SELECT id FROM sessions").fetchone()[0]
    db.execute("UPDATE sessions SET is_archived = 1, parser_version = 0 WHERE id = ?", [session_id])

    # Archived rows are never revisited by the live-file scan (their path
    # moved out of discover_root), so a stale version must be healed too.
    refresh_index(db)

    version = db.execute("SELECT parser_version FROM sessions WHERE id = ?", [session_id]).fetchone()[0]
    assert version == ClaudeSource.PARSER_VERSION


@pytest.mark.usefixtures("db_path")
def test_force_reindex_bypasses_mtime_and_version_check(claude_session_file, monkeypatch):
    _point_at_claude_root(monkeypatch, claude_session_file)
    db = get_db()
    refresh_index(db)
    session_id = db.execute("SELECT id FROM sessions").fetchone()[0]

    count = force_reindex(db, tool="claude")

    assert count == 1
    assert db.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 1

    filtered_out = force_reindex(db, tool="codex")
    assert filtered_out == 0

    by_id = force_reindex(db, session_id=session_id)
    assert by_id == 1


@pytest.mark.usefixtures("db_path")
def test_refresh_index_skips_disabled_tool(claude_session_file, monkeypatch):
    _point_at_claude_root(monkeypatch, claude_session_file)
    set_tool_enabled("claude", False)
    db = get_db()

    refresh_index(db)

    assert db.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 0


@pytest.mark.usefixtures("db_path")
def test_refresh_index_disabling_a_tool_does_not_delete_its_existing_rows(claude_session_file, monkeypatch):
    _point_at_claude_root(monkeypatch, claude_session_file)
    db = get_db()
    refresh_index(db)
    assert db.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 1

    set_tool_enabled("claude", False)
    refresh_index(db)

    assert db.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 1


@pytest.mark.usefixtures("db_path")
def test_refresh_index_indexes_cowork_session(cowork_session_file, monkeypatch):
    monkeypatch.setenv("HADES_COWORK_PATH", str(cowork_session_file.parent.parent))
    monkeypatch.setattr("hades.indexer.ALL_SOURCES", [CoworkSource])
    db = get_db()

    refresh_index(db)

    rows = list(db.execute(
        "SELECT id, tool, project_path, message_count, title, token_count, cost_usd, "
        "input_tokens, output_tokens, cache_write_tokens, cache_read_tokens FROM sessions"
    ).fetchall())
    assert len(rows) == 1
    session_id, tool, project_path, message_count, title, token_count, cost_usd, \
        input_tokens, output_tokens, cache_write_tokens, cache_read_tokens = rows[0]
    assert tool == "cowork"
    assert project_path == "Build a CLI tool"
    assert title == "Build a CLI tool"
    assert message_count == 2
    assert token_count == 30
    assert cost_usd > 0
    assert token_count == input_tokens + output_tokens + cache_write_tokens + cache_read_tokens

    fts_row = db.execute(
        "SELECT human_messages, assistant_messages FROM sessions_fts WHERE id = ?", [session_id]
    ).fetchone()
    assert fts_row is not None
    assert "CLI tool" in fts_row[0]
    assert "typer" in fts_row[1]
