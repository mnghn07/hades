from pathlib import Path

from hades.models import Session
from .base import BaseSource


class CodexSource(BaseSource):
    name = "codex"
    env_var = "HADES_CODEX_PATH"
    default_paths = [
        Path("~/.codex/sessions"),
    ]

    @classmethod
    def scan(cls) -> list[Session]:
        root = cls.discover_root()
        if root is None:
            return []
        sessions = []
        for session_file in root.rglob("rollout-*.jsonl"):
            session = _parse_session(session_file)
            if session:
                sessions.append(session)
        return sessions


def _parse_session(path: Path) -> Session | None:
    import ijson
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

    all_timestamps = [m.get("timestamp") for m in messages if m.get("timestamp")]
    timestamps = []
    for ts in all_timestamps:
        try:
            timestamps.append(datetime.fromisoformat(ts.replace("Z", "+00:00")))
        except Exception:
            continue

    started_at = min(timestamps) if timestamps else datetime.now(timezone.utc)
    last_active_at = max(timestamps) if timestamps else started_at

    human_msgs = [m for m in messages if m.get("role") == "user"]
    title = None
    if human_msgs:
        content = human_msgs[0].get("content", "")
        if isinstance(content, str):
            title = content[:80]

    session_id = path.stem
    project_path = str(path.parent)

    return Session(
        id=f"codex:{session_id}",
        tool="codex",
        project_path=project_path,
        started_at=started_at,
        last_active_at=last_active_at,
        message_count=len(messages),
        status="idle",
        raw_path=path,
        title=title,
    )
