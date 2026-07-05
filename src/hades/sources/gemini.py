from datetime import datetime, timezone
from pathlib import Path

from hades.models import Session
from .base import BaseSource
from .common import messages_of, parse_timestamps, read_json_document


class GeminiSource(BaseSource):
    name = "gemini"
    env_var = "HADES_GEMINI_PATH"
    default_paths = [Path("~/.gemini/tmp")]

    @classmethod
    def list_files(cls) -> list[Path]:
        root = cls.discover_root()
        return list(root.rglob("chats/*.json")) if root else []

    @classmethod
    def parse_file(cls, path: Path) -> Session | None:
        data = read_json_document(path)
        messages = messages_of(data)
        if not messages:
            return None

        timestamps = parse_timestamps(messages, keys=("timestamp", "createTime"))
        started_at = min(timestamps) if timestamps else datetime.now(timezone.utc)
        last_active_at = max(timestamps) if timestamps else started_at

        human_msgs = [m for m in messages if m.get("role") == "user"]
        title = None
        if human_msgs:
            parts = human_msgs[0].get("parts", [])
            if parts:
                first = parts[0]
                title = (first.get("text", "") if isinstance(first, dict) else str(first))[:80]

        return Session(
            # Include the project-hash directory: chat filenames (session-1.json)
            # repeat across projects and would otherwise collide.
            id=f"gemini:{path.parent.parent.name}:{path.stem}",
            tool="gemini",
            project_path=_extract_project_path(data) or str(path.parent.parent),
            started_at=started_at,
            last_active_at=last_active_at,
            message_count=len(messages),
            status="idle",
            raw_path=path,
            title=title,
        )

    @classmethod
    def extract_messages(cls, path: Path) -> tuple[str, str]:
        messages = messages_of(read_json_document(path))
        human = " ".join(_parts_text(m) for m in messages if m.get("role") == "user")
        assistant = " ".join(_parts_text(m) for m in messages if m.get("role") == "model")
        return human, assistant


def _extract_project_path(data: dict | list) -> str | None:
    if not isinstance(data, dict):
        return None
    for key in ("projectPath", "cwd", "workingDirectory"):
        if data.get(key):
            return data[key]
    return None


def _parts_text(msg: dict) -> str:
    parts = msg.get("parts", [])
    return " ".join(
        p.get("text", "") if isinstance(p, dict) else str(p)
        for p in parts
    )
