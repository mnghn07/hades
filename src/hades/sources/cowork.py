from datetime import datetime, timezone
from pathlib import Path

from hades.models import Session
from .base import BaseSource
from .common import messages_of, parse_timestamps, read_json_document


class CoworkSource(BaseSource):
    name = "cowork"
    env_var = "HADES_COWORK_PATH"
    default_paths = [
        Path("~/Library/Application Support/Claude/local-agent-mode-sessions"),
        Path("~/.config/claude/local-agent-mode-sessions"),
    ]

    @classmethod
    def list_files(cls) -> list[Path]:
        root = cls.discover_root()
        if root is None:
            return []
        return [
            p for p in root.rglob("*.json")
            if "node_modules" not in p.parts
        ]

    @classmethod
    def parse_file(cls, path: Path) -> Session | None:
        data = read_json_document(path)
        messages = messages_of(data)
        if not messages:
            return None

        timestamps = parse_timestamps(messages)
        started_at = min(timestamps) if timestamps else datetime.now(timezone.utc)
        last_active_at = max(timestamps) if timestamps else started_at

        human_msgs = [m for m in messages if m.get("role") == "user" or m.get("type") == "human"]
        title = None
        if human_msgs:
            content = human_msgs[0].get("content", "")
            if isinstance(content, str):
                title = content[:80]

        return Session(
            id=f"cowork:{path.stem}",
            tool="cowork",
            project_path=_extract_project_path(data) or str(path.parent),
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
        human = " ".join(
            str(m.get("content", "")) for m in messages
            if m.get("role") == "user" or m.get("type") == "human"
        )
        assistant = " ".join(
            str(m.get("content", "")) for m in messages
            if m.get("role") == "assistant" or m.get("type") == "assistant"
        )
        return human, assistant


def _extract_project_path(data: dict | list) -> str | None:
    if not isinstance(data, dict):
        return None
    for key in ("cwd", "workingDirectory", "projectPath", "workspacePath"):
        if data.get(key):
            return data[key]
    return None
