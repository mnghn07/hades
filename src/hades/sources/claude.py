from datetime import datetime, timezone
from pathlib import Path

import ijson

from hades.models import Session
from .base import BaseSource


class ClaudeSource(BaseSource):
    name = "claude"
    env_var = "HADES_CLAUDE_PATH"
    default_paths = [Path("~/.claude/projects")]

    @classmethod
    def list_files(cls) -> list[Path]:
        root = cls.discover_root()
        return list(root.rglob("*.jsonl")) if root else []

    @classmethod
    def parse_file(cls, path: Path) -> Session | None:
        messages = _read_messages(path)
        if not messages:
            return None

        human_msgs = [m for m in messages if m.get("type") == "human"]
        assistant_msgs = [m for m in messages if m.get("type") == "assistant"]
        timestamps = _parse_timestamps(messages)

        started_at = min(timestamps) if timestamps else datetime.now(timezone.utc)
        last_active_at = max(timestamps) if timestamps else started_at
        title = _extract_title_claude(human_msgs)

        return Session(
            id=f"claude:{path.stem}",
            tool="claude",
            project_path=_decode_project_path(path.parent.name),
            started_at=started_at,
            last_active_at=last_active_at,
            message_count=len(human_msgs) + len(assistant_msgs),
            status="idle",
            raw_path=path,
            title=title,
        )

    @classmethod
    def extract_messages(cls, path: Path) -> tuple[str, str]:
        messages = _read_messages(path)
        human = " ".join(_text_content(m) for m in messages if m.get("type") == "human")
        assistant = " ".join(_text_content(m) for m in messages if m.get("type") == "assistant")
        return human, assistant


def _read_messages(path: Path) -> list[dict]:
    try:
        with open(path, "rb") as f:
            return list(ijson.items(f, "", multiple_values=True))
    except Exception:
        return []


def _parse_timestamps(messages: list[dict]) -> list[datetime]:
    timestamps = []
    for m in messages:
        ts = m.get("timestamp")
        if ts:
            try:
                timestamps.append(datetime.fromisoformat(ts.replace("Z", "+00:00")))
            except Exception:
                pass
    return timestamps


def _extract_title_claude(human_msgs: list[dict]) -> str | None:
    if not human_msgs:
        return None
    content = human_msgs[0].get("content", "")
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                return block.get("text", "")[:80]
    elif isinstance(content, str):
        return content[:80]
    return None


def _text_content(msg: dict) -> str:
    content = msg.get("content", "")
    if isinstance(content, list):
        return " ".join(
            b.get("text", "") for b in content
            if isinstance(b, dict) and b.get("type") == "text"
        )
    return str(content) if content else ""


def _decode_project_path(encoded: str) -> str:
    """Claude encodes project paths by replacing / with -. Best-effort decode."""
    return encoded.replace("-", "/")
