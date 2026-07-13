import io
import json

import pytest

from hades.db import get_db
from hades.hooks import install_hooks


@pytest.fixture
def hook_session(db_path):
    db = get_db()
    db["sessions"].insert({
        "id": "claude:abc123",
        "tool": "claude",
        "project_path": "/tmp/project",
        "started_at": "2026-07-13T10:00:00Z",
        "last_active_at": "2026-07-13T10:00:00Z",
        "message_count": 1,
        "status": "running",
        "raw_path": "/tmp/abc123.jsonl",
        "title": "test",
    }, pk="id")
    return db


def _send_event(monkeypatch, event: str, session_id: str = "abc123") -> None:
    from hades import hooks
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({"session_id": session_id})))
    hooks.handle_hook_event(event)


def test_stop_sets_waiting_since(hook_session, monkeypatch):
    _send_event(monkeypatch, "Stop")
    row = hook_session["sessions"].get("claude:abc123")
    assert row["waiting_since"] is not None


def test_user_prompt_submit_clears_waiting_since(hook_session, monkeypatch):
    _send_event(monkeypatch, "Stop")
    _send_event(monkeypatch, "UserPromptSubmit")
    row = hook_session["sessions"].get("claude:abc123")
    assert row["waiting_since"] is None


def test_second_stop_does_not_overwrite_first_timestamp(hook_session, monkeypatch):
    _send_event(monkeypatch, "Stop")
    first = hook_session["sessions"].get("claude:abc123")["waiting_since"]
    _send_event(monkeypatch, "Stop")
    second = hook_session["sessions"].get("claude:abc123")["waiting_since"]
    assert first == second


def test_unknown_session_id_does_not_raise(db_path, monkeypatch):
    get_db()  # ensure schema exists
    _send_event(monkeypatch, "Stop", session_id="does-not-exist")


def test_install_hooks_idempotent(tmp_path, monkeypatch):
    monkeypatch.setattr("hades.hooks.SETTINGS_PATH", tmp_path / "settings.json")
    first = install_hooks()
    assert set(first) == {"Stop", "Notification", "UserPromptSubmit"}
    second = install_hooks()
    assert second == []
