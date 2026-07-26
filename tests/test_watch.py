from unittest.mock import patch

from hades.commands.watch import _read_key, _render_table

SESSIONS = [
    {"id": "a", "tool": "claude", "project_path": "/x/foo", "title": "t1",
     "status": "idle", "_waiting_minutes": 5, "_is_waiting": True},
    {"id": "b", "tool": "codex", "project_path": "/x/bar", "title": "t2",
     "status": "running", "_waiting_minutes": 1, "_is_waiting": False},
]


def test_render_table_highlights_cursor_row():
    table = _render_table(SESSIONS, cursor=1)
    assert table.rows[0].style is None
    assert table.rows[1].style == "reverse"


def test_render_table_empty_sessions():
    table = _render_table([], cursor=0)
    assert len(table.rows) == 0


def test_read_key_returns_none_when_not_a_tty():
    with patch("hades.commands.watch.sys.stdin.isatty", return_value=False):
        assert _read_key(0) is None
