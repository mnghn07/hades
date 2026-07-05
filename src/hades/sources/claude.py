from datetime import datetime, timezone
from pathlib import Path

from hades.models import Session
from .base import BaseSource
from .common import parse_timestamps, read_jsonl_dicts


class ClaudeSource(BaseSource):
    name = "claude"
    env_var = "HADES_CLAUDE_PATH"
    default_paths = [Path("~/.claude/projects")]

    @classmethod
    def list_files(cls) -> list[Path]:
        root = cls.discover_root()
        if root is None:
            return []
        # Exclude sessions-index.json and other non-session files
        return [p for p in root.rglob("*.jsonl") if not p.name.startswith("sessions-index")]

    @classmethod
    def parse_file(cls, path: Path) -> Session | None:
        messages = read_jsonl_dicts(path)
        if not messages:
            return None

        cwd = _extract_cwd(messages)
        user_msgs = [m for m in messages if m.get("type") == "user" and "message" in m]
        assistant_msgs = [m for m in messages if _is_assistant(m)]
        timestamps = parse_timestamps(messages)

        started_at = min(timestamps) if timestamps else datetime.now(timezone.utc)
        last_active_at = max(timestamps) if timestamps else started_at
        title = _extract_title(user_msgs)

        return Session(
            # Keyed by file stem, not the inner sessionId: resumed sessions
            # reuse the original sessionId across multiple files, and a shared
            # id would make the files shadow each other in the index.
            id=f"claude:{path.stem}",
            tool="claude",
            project_path=cwd or _decode_dir(path.parent.name),
            started_at=started_at,
            last_active_at=last_active_at,
            message_count=len(user_msgs) + len(assistant_msgs),
            status="idle",
            raw_path=path,
            title=title,
        )

    @classmethod
    def extract_messages(cls, path: Path) -> tuple[str, str]:
        messages = read_jsonl_dicts(path)
        human = " ".join(
            _msg_text(m["message"])
            for m in messages
            if m.get("type") == "user" and "message" in m
        )
        assistant = " ".join(
            _msg_text(m["message"])
            for m in messages
            if _is_assistant(m) and "message" in m
        )
        return human, assistant


def _extract_cwd(messages: list[dict]) -> str | None:
    for m in messages:
        cwd = m.get("cwd")
        if cwd:
            return cwd
    return None


def _is_assistant(m: dict) -> bool:
    msg = m.get("message", {})
    return isinstance(msg, dict) and msg.get("role") == "assistant"


def _extract_title(user_msgs: list[dict]) -> str | None:
    for m in user_msgs:
        text = _msg_text(m.get("message", {}))
        if text and _is_real_user_text(text):
            return text[:80]
    return None


def _is_real_user_text(text: str) -> bool:
    """Reject system-injected content that looks like XML tags or hook metadata."""
    stripped = text.strip()
    if stripped.startswith("<") or stripped.startswith("Base directory"):
        return False
    # Skip tool result content injected by the harness
    if stripped.startswith("[{") or stripped.startswith("Output too large"):
        return False
    return len(stripped) > 3


def _decode_dir(encoded: str) -> str:
    """Best-effort decode of Claude's project dir encoding (/ and . both map to -).
    Falls back gracefully — imperfect for paths with dots but readable."""
    # Strip leading dash, replace remaining dashes with slashes
    return "/" + encoded.lstrip("-").replace("-", "/")


def _msg_text(msg: dict) -> str:
    content = msg.get("content", "")
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text = block.get("text", "").strip()
                if text:
                    return text
        return ""
    return str(content).strip() if content else ""
