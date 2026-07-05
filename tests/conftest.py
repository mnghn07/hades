import json
from pathlib import Path

import pytest


@pytest.fixture
def db_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point hades.db at an isolated per-test SQLite file."""
    path = tmp_path / "index.db"
    monkeypatch.setattr("hades.db.DB_PATH", path)
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
