from pathlib import Path

import pytest


@pytest.fixture
def tmp_session_dir(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def sample_claude_jsonl(tmp_session_dir: Path) -> Path:
    import json
    session_dir = tmp_session_dir / ".claude" / "projects" / "test-project"
    session_dir.mkdir(parents=True)
    session_file = session_dir / "abc123.jsonl"
    messages = [
        {"type": "human", "content": "Help me build a CLI tool", "timestamp": "2026-07-03T10:00:00Z"},
        {"type": "assistant", "content": "Sure, let's start with typer.", "timestamp": "2026-07-03T10:00:05Z"},
    ]
    with open(session_file, "w", encoding="utf-8") as f:
        for msg in messages:
            f.write(json.dumps(msg) + "\n")
    return session_file
