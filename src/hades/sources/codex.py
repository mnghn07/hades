from datetime import datetime, timezone
from pathlib import Path

from hades.models import Session
from .base import BaseSource
from .common import parse_timestamps, read_jsonl_dicts


class CodexSource(BaseSource):
    name = "codex"
    env_var = "HADES_CODEX_PATH"
    default_paths = [Path("~/.codex/sessions")]

    @classmethod
    def list_files(cls) -> list[Path]:
        root = cls.discover_root()
        return list(root.rglob("rollout-*.jsonl")) if root else []

    @classmethod
    def parse_file(cls, path: Path) -> Session | None:
        messages = read_jsonl_dicts(path)
        if not messages:
            return None

        timestamps = parse_timestamps(messages)
        started_at = min(timestamps) if timestamps else datetime.now(timezone.utc)
        last_active_at = max(timestamps) if timestamps else started_at

        turns = [m for m in messages if m.get("role") in ("user", "assistant")]
        human_msgs = [m for m in turns if m.get("role") == "user"]
        title = None
        if human_msgs:
            content = human_msgs[0].get("content", "")
            if isinstance(content, str):
                title = content[:80]

        return Session(
            id=f"codex:{path.stem}",
            tool="codex",
            project_path=_extract_cwd(messages) or str(path.parent),
            started_at=started_at,
            last_active_at=last_active_at,
            message_count=len(turns),
            status="idle",
            raw_path=path,
            title=title,
        )

    @classmethod
    def extract_messages(cls, path: Path) -> tuple[str, str]:
        messages = read_jsonl_dicts(path)
        human = " ".join(str(m.get("content", "")) for m in messages if m.get("role") == "user")
        assistant = " ".join(str(m.get("content", "")) for m in messages if m.get("role") == "assistant")
        return human, assistant


def _extract_cwd(messages: list[dict]) -> str | None:
    """Codex rollout files carry the working directory in the session_meta
    record (payload.cwd) or as a top-level cwd on some records."""
    for m in messages:
        payload = m.get("payload")
        if isinstance(payload, dict) and payload.get("cwd"):
            return payload["cwd"]
        if m.get("cwd"):
            return m["cwd"]
    return None
