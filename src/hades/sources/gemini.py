from pathlib import Path

from hades.models import Session
from .base import BaseSource


class GeminiSource(BaseSource):
    name = "gemini"
    env_var = "HADES_GEMINI_PATH"
    default_paths = [
        Path("~/.gemini/tmp"),
    ]

    @classmethod
    def scan(cls) -> list[Session]:
        root = cls.discover_root()
        if root is None:
            return []
        sessions = []
        for session_file in root.rglob("chats/*.json"):
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

    all_timestamps = [m.get("timestamp") or m.get("createTime") for m in messages if m.get("timestamp") or m.get("createTime")]
    timestamps = []
    for ts in all_timestamps:
        try:
            timestamps.append(datetime.fromisoformat(str(ts).replace("Z", "+00:00")))
        except Exception:
            continue

    started_at = min(timestamps) if timestamps else datetime.now(timezone.utc)
    last_active_at = max(timestamps) if timestamps else started_at

    human_msgs = [m for m in messages if m.get("role") == "user"]
    title = None
    if human_msgs:
        parts = human_msgs[0].get("parts", [])
        if parts and isinstance(parts[0], dict):
            title = parts[0].get("text", "")[:80]
        elif parts and isinstance(parts[0], str):
            title = parts[0][:80]

    session_id = path.stem
    project_path = str(path.parent.parent)

    return Session(
        id=f"gemini:{session_id}",
        tool="gemini",
        project_path=project_path,
        started_at=started_at,
        last_active_at=last_active_at,
        message_count=len(messages),
        status="idle",
        raw_path=path,
        title=title,
    )
