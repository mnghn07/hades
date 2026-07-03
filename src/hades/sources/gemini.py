import json
from datetime import datetime, timezone
from pathlib import Path

from hades.models import Session
from .base import BaseSource


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
        messages = _read_messages(path)
        if not messages:
            return None

        timestamps = _parse_timestamps(messages)
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
            id=f"gemini:{path.stem}",
            tool="gemini",
            project_path=str(path.parent.parent),
            started_at=started_at,
            last_active_at=last_active_at,
            message_count=len(messages),
            status="idle",
            raw_path=path,
            title=title,
        )

    @classmethod
    def extract_messages(cls, path: Path) -> tuple[str, str]:
        messages = _read_messages(path)
        human = " ".join(_parts_text(m) for m in messages if m.get("role") == "user")
        assistant = " ".join(_parts_text(m) for m in messages if m.get("role") == "model")
        return human, assistant


def _read_messages(path: Path) -> list[dict]:
    try:
        with open(path) as f:
            data = json.load(f)
        return data if isinstance(data, list) else data.get("messages", [])
    except Exception:
        return []


def _parse_timestamps(messages: list[dict]) -> list[datetime]:
    timestamps = []
    for m in messages:
        ts = m.get("timestamp") or m.get("createTime")
        if ts:
            try:
                timestamps.append(datetime.fromisoformat(str(ts).replace("Z", "+00:00")))
            except Exception:
                pass
    return timestamps


def _parts_text(msg: dict) -> str:
    parts = msg.get("parts", [])
    return " ".join(
        p.get("text", "") if isinstance(p, dict) else str(p)
        for p in parts
    )
