from datetime import datetime, timezone
from pathlib import Path

from hades.models import Session
from .base import BaseSource
from .common import (
    extract_cost, extract_token_breakdown, extract_token_count, parse_timestamps, read_json_document, read_jsonl_dicts,
)


class CoworkSource(BaseSource):
    name = "cowork"
    env_var = "HADES_COWORK_PATH"
    default_paths = [
        Path("~/Library/Application Support/Claude/local-agent-mode-sessions"),
        Path("~/.config/claude/local-agent-mode-sessions"),
    ]
    # v2: backfills the four token-category columns (input/output/cache-write/cache-read).
    PARSER_VERSION = 2

    @classmethod
    def list_files(cls) -> list[Path]:
        root = cls.discover_root()
        if root is None:
            return []
        # Each session is local_<uuid>/audit.jsonl. The sibling local_<uuid>.json
        # is metadata only (no messages) — read separately, below, for its title.
        return list(root.rglob("audit.jsonl"))

    @classmethod
    def parse_file(cls, path: Path) -> Session | None:
        messages = read_jsonl_dicts(path)
        user_msgs = [m for m in messages if m.get("type") == "user" and "message" in m]
        assistant_msgs = [m for m in messages if m.get("type") == "assistant" and "message" in m]
        if not user_msgs and not assistant_msgs:
            return None

        timestamps = parse_timestamps(messages, keys=("_audit_timestamp",))
        started_at = min(timestamps) if timestamps else datetime.now(timezone.utc)
        last_active_at = max(timestamps) if timestamps else started_at

        # Cowork runs sessions in a sandboxed VM — every cwd field in the data
        # (metadata file and audit log alike) points inside hades' own storage,
        # not a real host project path. The session's own title is the closest
        # thing to a project label, so it's used for both fields below.
        title = _read_metadata(path).get("title") or _extract_title(user_msgs)
        breakdown = extract_token_breakdown(assistant_msgs)

        return Session(
            id=f"cowork:{path.parent.name}",
            tool="cowork",
            project_path=title or path.parent.name,
            started_at=started_at,
            last_active_at=last_active_at,
            message_count=len(user_msgs) + len(assistant_msgs),
            status="idle",
            raw_path=path,
            title=title,
            token_count=extract_token_count(assistant_msgs),
            cost_usd=extract_cost(assistant_msgs),
            input_tokens=breakdown["input"],
            output_tokens=breakdown["output"],
            cache_write_tokens=breakdown["cache_write"],
            cache_read_tokens=breakdown["cache_read"],
        )

    @classmethod
    def extract_messages(cls, path: Path) -> tuple[str, str]:
        messages = read_jsonl_dicts(path)
        human = " ".join(
            _msg_text(m["message"]) for m in messages if m.get("type") == "user" and "message" in m
        )
        assistant = " ".join(
            _msg_text(m["message"]) for m in messages if m.get("type") == "assistant" and "message" in m
        )
        return human, assistant


def _read_metadata(path: Path) -> dict:
    metadata_path = path.parent.parent / f"{path.parent.name}.json"
    data = read_json_document(metadata_path)
    return data if isinstance(data, dict) else {}


def _extract_title(user_msgs: list[dict]) -> str | None:
    for m in user_msgs:
        text = _msg_text(m.get("message", {}))
        if text:
            return text[:80]
    return None


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
