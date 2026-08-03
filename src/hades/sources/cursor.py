import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from hades.models import Session
from .base import BaseSource
from .common import read_jsonl_dicts

_QUERY_RE = re.compile(r"<user_query>\s*(.*?)\s*</user_query>", re.DOTALL)
_TIMESTAMP_RE = re.compile(
    r"<timestamp>[A-Za-z]+, ([A-Za-z]+ \d{1,2}, \d{4}, \d{1,2}:\d{2} [AP]M)"
    r" \(UTC([+-]\d{1,2})(?::(\d{2}))?\)</timestamp>"
)


class CursorSource(BaseSource):
    name = "cursor"
    env_var = "HADES_CURSOR_PATH"
    default_paths = [Path("~/.cursor/projects")]

    @classmethod
    def list_files(cls) -> list[Path]:
        root = cls.discover_root()
        if root is None:
            return []
        # <project>/agent-transcripts/<uuid>/<uuid>.jsonl is the main transcript.
        # Nested subagents/<uuid>.jsonl live one level deeper and are skipped by
        # this non-recursive glob (subagent sessions aren't tracked yet).
        return list(root.glob("*/agent-transcripts/*/*.jsonl"))

    @classmethod
    def parse_file(cls, path: Path) -> Session | None:
        messages = read_jsonl_dicts(path)
        turns = [m for m in messages if m.get("role") in ("user", "assistant")]
        if not turns:
            return None

        user_texts = [_msg_text(m) for m in turns if m.get("role") == "user"]
        embedded_timestamps = [ts for t in user_texts if (ts := _parse_embedded_timestamp(t))]
        birth, mtime = _file_times(path)

        return Session(
            id=f"cursor:{path.stem}",
            tool="cursor",
            project_path=_decode_dir(path.parent.parent.parent.name),
            started_at=min(embedded_timestamps) if embedded_timestamps else birth,
            # mtime is exact (each turn is appended live) so it's used directly
            # rather than the embedded timestamp, which only ~60% of user turns
            # carry and none of the assistant turns do.
            last_active_at=mtime,
            message_count=len(turns),
            status="idle",
            raw_path=path,
            title=_extract_title(user_texts),
        )

    @classmethod
    def extract_messages(cls, path: Path) -> tuple[str, str]:
        messages = read_jsonl_dicts(path)
        human = " ".join(_msg_text(m) for m in messages if m.get("role") == "user")
        assistant = " ".join(_msg_text(m) for m in messages if m.get("role") == "assistant")
        return human, assistant


def _msg_text(m: dict) -> str:
    content = m.get("message", {}).get("content", [])
    if not isinstance(content, list):
        return ""
    return " ".join(
        block["text"].strip()
        for block in content
        if isinstance(block, dict) and block.get("type") == "text" and block.get("text")
    )


def _extract_title(user_texts: list[str]) -> str | None:
    for text in user_texts:
        match = _QUERY_RE.search(text)
        if match:
            return match.group(1)[:80]
    return None


def _parse_embedded_timestamp(text: str) -> datetime | None:
    match = _TIMESTAMP_RE.search(text)
    if not match:
        return None
    dt_str, offset_hours, offset_minutes = match.groups()
    try:
        naive = datetime.strptime(dt_str, "%b %d, %Y, %I:%M %p")
    except ValueError:
        return None
    sign = -1 if offset_hours.startswith("-") else 1
    offset = timedelta(hours=int(offset_hours), minutes=sign * int(offset_minutes or 0))
    return naive.replace(tzinfo=timezone(offset))


def _file_times(path: Path) -> tuple[datetime, datetime]:
    st = path.stat()
    birth = getattr(st, "st_birthtime", None) or st.st_ctime
    return datetime.fromtimestamp(birth, tz=timezone.utc), datetime.fromtimestamp(st.st_mtime, tz=timezone.utc)


def _decode_dir(encoded: str) -> str:
    """Best-effort decode of Cursor's project dir encoding (/ maps to -).
    Same ambiguity as Claude's scheme for dirs whose real name contains a
    literal hyphen — imperfect but readable."""
    return "/" + encoded.replace("-", "/")
