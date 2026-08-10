import json
from pathlib import Path

import pytest


@pytest.fixture
def db_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point hades.db at an isolated per-test SQLite file, and hades.config at an
    isolated config with every source pre-enabled (tests predate per-tool
    enable/disable and assume multi-tool scanning; see test_tools.py for the
    enable/disable mechanics themselves, which use their own isolated config)."""
    path = tmp_path / "index.db"
    monkeypatch.setattr("hades.db.DB_PATH", path)

    from hades.sources import ALL_SOURCES
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"enabled_tools": [s.name for s in ALL_SOURCES]}))
    monkeypatch.setattr("hades.config.CONFIG_PATH", config_path)

    return path


@pytest.fixture
def claude_session_file(tmp_path: Path) -> Path:
    """A minimal but realistic Claude Code session JSONL file."""
    session_dir = tmp_path / "claude_sessions" / "-Users-test-project"
    session_dir.mkdir(parents=True)
    session_file = session_dir / "abc123.jsonl"
    lines = [
        {
            "type": "user",
            "sessionId": "abc123",
            "cwd": "/Users/test/project",
            "timestamp": "2026-07-03T10:00:00Z",
            "message": {"role": "user", "content": "Help me build a CLI tool"},
        },
        {
            "type": "assistant",
            "sessionId": "abc123",
            "timestamp": "2026-07-03T10:00:05Z",
            "message": {
                "role": "assistant",
                "content": [{"type": "text", "text": "Sure, let's start with typer."}],
            },
        },
    ]
    with open(session_file, "w", encoding="utf-8") as f:
        for msg in lines:
            f.write(json.dumps(msg) + "\n")
    return session_file


@pytest.fixture
def cowork_session_file(tmp_path: Path) -> Path:
    """A minimal but realistic Cowork session: metadata json + audit.jsonl."""
    session_root = tmp_path / "cowork_sessions"
    session_dir = session_root / "local_test123"
    session_dir.mkdir(parents=True)
    metadata = {"sessionId": "local_test123", "title": "Build a CLI tool", "cwd": str(session_dir / "outputs")}
    (session_root / "local_test123.json").write_text(json.dumps(metadata), encoding="utf-8")

    audit_file = session_dir / "audit.jsonl"
    lines = [
        {
            "type": "user", "message": {"role": "user", "content": "Help me build a CLI tool"},
            "_audit_timestamp": "2026-07-03T10:00:00.000Z",
        },
        {
            "type": "assistant",
            "message": {
                "role": "assistant", "model": "claude-sonnet-5",
                "content": [{"type": "text", "text": "Sure, let's start with typer."}],
                "usage": {"input_tokens": 10, "output_tokens": 20},
            },
            "_audit_timestamp": "2026-07-03T10:00:05.000Z",
        },
        {"type": "system", "subtype": "hook_started"},
    ]
    with open(audit_file, "w", encoding="utf-8") as f:
        for msg in lines:
            f.write(json.dumps(msg) + "\n")
    return audit_file


@pytest.fixture
def cursor_session_file(tmp_path: Path) -> Path:
    """A minimal but realistic Cursor CLI agent transcript."""
    transcript_dir = tmp_path / "cursor_projects" / "Users-test-project" / "agent-transcripts" / "abc123"
    transcript_dir.mkdir(parents=True)
    session_file = transcript_dir / "abc123.jsonl"
    lines = [
        {
            "role": "user",
            "message": {"content": [{
                "type": "text",
                "text": "<timestamp>Thursday, Jul 30, 2026, 2:05 PM (UTC+7)</timestamp>\n"
                        "<user_query>\nHelp me build a CLI tool\n</user_query>",
            }]},
        },
        {
            "role": "assistant",
            "message": {"content": [{"type": "text", "text": "Sure, let's start with typer."}]},
        },
        {"type": "turn_ended", "status": "success"},
    ]
    with open(session_file, "w", encoding="utf-8") as f:
        for msg in lines:
            f.write(json.dumps(msg) + "\n")
    return session_file
