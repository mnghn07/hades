from pathlib import Path

from hades.models import Session
from .base import BaseSource


class CoworkSource(BaseSource):
    name = "cowork"
    env_var = "HADES_COWORK_PATH"
    default_paths = [
        Path("~/Library/Application Support/Claude/local-agent-mode-sessions"),
        Path("~/.config/claude/local-agent-mode-sessions"),
    ]

    @classmethod
    def scan(cls) -> list[Session]:
        root = cls.discover_root()
        if root is None:
            return []
        sessions = []
        for session_file in root.rglob("*.json"):
            session = _parse_session(session_file)
            if session:
                sessions.append(session)
        return sessions


def _parse_session(path: Path) -> Session | None:
    import json
    from datetime import datetime, timezone

    try:
        with open(path) as f:
            data = json.load(f)
    except Exception:
        return None

    messages = data if isinstance(data, list) else data.get("messages", [])
    if not messages:
        return None

    all_timestamps = [m.get("timestamp") for m in messages if m.get("timestamp")]
    timestamps = []
    for ts in all_timestamps:
        try:
            timestamps.append(datetime.fromisoformat(str(ts).replace("Z", "+00:00")))
        except Exception:
            continue

    started_at = min(timestamps) if timestamps else datetime.now(timezone.utc)
    last_active_at = max(timestamps) if timestamps else started_at

    human_msgs = [m for m in messages if m.get("role") == "user" or m.get("type") == "human"]
    title = None
    if human_msgs:
        content = human_msgs[0].get("content", "")
        if isinstance(content, str):
            title = content[:80]

    session_id = path.stem

    return Session(
        id=f"cowork:{session_id}",
        tool="cowork",
        project_path=str(path.parent),
        started_at=started_at,
        last_active_at=last_active_at,
        message_count=len(messages),
        status="idle",
        raw_path=path,
        title=title,
    )
