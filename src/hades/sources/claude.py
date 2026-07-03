from pathlib import Path

from hades.models import Session
from .base import BaseSource


class ClaudeSource(BaseSource):
    name = "claude"
    env_var = "HADES_CLAUDE_PATH"
    default_paths = [
        Path("~/.claude/projects"),
    ]

    @classmethod
    def scan(cls) -> list[Session]:
        root = cls.discover_root()
        if root is None:
            return []
        sessions = []
        for session_file in root.rglob("*.jsonl"):
            session = _parse_session(session_file)
            if session:
                sessions.append(session)
        return sessions


def _parse_session(path: Path) -> Session | None:
    import ijson
    import json
    from datetime import datetime, timezone

    messages = []
    try:
        with open(path, "rb") as f:
            for item in ijson.items(f, "", multiple_values=True):
                messages.append(item)
    except Exception:
        return None

    if not messages:
        return None

    human_msgs = [m for m in messages if m.get("type") == "human"]
    assistant_msgs = [m for m in messages if m.get("type") == "assistant"]
    all_timestamps = [m.get("timestamp") for m in messages if m.get("timestamp")]

    def parse_ts(ts: str) -> datetime:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))

    timestamps = []
    for ts in all_timestamps:
        try:
            timestamps.append(parse_ts(ts))
        except Exception:
            continue

    started_at = min(timestamps) if timestamps else datetime.now(timezone.utc)
    last_active_at = max(timestamps) if timestamps else started_at

    title = None
    if human_msgs:
        first = human_msgs[0]
        content = first.get("content", "")
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    title = block.get("text", "")[:80]
                    break
        elif isinstance(content, str):
            title = content[:80]

    session_id = path.stem
    project_path = path.parent.name  # encoded project path dir

    return Session(
        id=f"claude:{session_id}",
        tool="claude",
        project_path=project_path,
        started_at=started_at,
        last_active_at=last_active_at,
        message_count=len(human_msgs) + len(assistant_msgs),
        status="idle",
        raw_path=path,
        title=title,
    )
