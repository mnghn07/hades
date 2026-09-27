from unittest.mock import patch

from hades.commands.watch import _Ui, _decode_key, _handle_key, _read_key, _render_table

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


def test_render_table_no_highlight_without_cursor():
    table = _render_table(SESSIONS, cursor=None)
    assert all(row.style is None for row in table.rows)


def test_archive_flow_menu_select_confirm():
    sessions = [dict(s) for s in SESSIONS]
    ui = _Ui()
    with patch("hades.commands.watch.archive_session_by_id") as archive:
        for key in ["j", "d", "j", "\r"]:  # j ignored in table mode
            _handle_key(key, None, sessions, ui)
        assert (ui.mode, ui.target["id"]) == ("confirm", "b")
        archive.assert_not_called()

        _handle_key("y", None, sessions, ui)
        archive.assert_called_once_with(None, "b")
    assert [s["id"] for s in sessions] == ["a"]
    assert (ui.mode, ui.cursor) == ("table", 0)


def test_archive_flow_cancel_does_not_archive():
    sessions = [dict(s) for s in SESSIONS]
    ui = _Ui()
    with patch("hades.commands.watch.archive_session_by_id") as archive:
        for key in ["d", "\r", "n", "\x1b"]:
            _handle_key(key, None, sessions, ui)
        archive.assert_not_called()
    assert ui.mode == "table"
    assert len(sessions) == 2


def test_decode_key_maps_arrows_and_keeps_plain_esc():
    assert _decode_key("\x1b[A") == "k"
    assert _decode_key("\x1b[B") == "j"
    assert _decode_key("\x1bOB") == "j"
    assert _decode_key("\x1b[C") is None
    assert _decode_key("\x1b") == "\x1b"
    assert _decode_key("d") == "d"
