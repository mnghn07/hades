from datetime import datetime, timezone
from pathlib import Path

from hades import pricing
from hades.models import Session
from .base import BaseSource
from .common import parse_timestamps, read_jsonl_dicts


class OpenclawSource(BaseSource):
    name = "openclaw"
    env_var = "HADES_OPENCLAW_PATH"
    default_paths = [Path("~/.openclaw/agents")]

    @classmethod
    def list_files(cls) -> list[Path]:
        root = cls.discover_root()
        return list(root.glob("*/sessions/*.jsonl")) if root else []

    @classmethod
    def parse_file(cls, path: Path) -> Session | None:
        records = read_jsonl_dicts(path)
        if not records:
            return None

        cwd = _extract_cwd(records)
        user_msgs = [r for r in records if _role(r) == "user"]
        assistant_msgs = [r for r in records if _role(r) == "assistant"]
        if not user_msgs and not assistant_msgs:
            return None

        timestamps = parse_timestamps(records)
        started_at = min(timestamps) if timestamps else datetime.now(timezone.utc)
        last_active_at = max(timestamps) if timestamps else started_at
        title = _extract_title(user_msgs)

        return Session(
            id=f"openclaw:{path.stem}",
            tool="openclaw",
            project_path=cwd or str(path.parent),
            started_at=started_at,
            last_active_at=last_active_at,
            message_count=len(user_msgs) + len(assistant_msgs),
            status="idle",
            raw_path=path,
            title=title,
            token_count=_extract_token_count(assistant_msgs),
            cost_usd=_extract_cost(assistant_msgs),
        )

    @classmethod
    def extract_messages(cls, path: Path) -> tuple[str, str]:
        records = read_jsonl_dicts(path)
        human = " ".join(_msg_text(r["message"]) for r in records if _role(r) == "user")
        assistant = " ".join(_msg_text(r["message"]) for r in records if _role(r) == "assistant")
        return human, assistant


def _role(record: dict) -> str | None:
    if record.get("type") != "message":
        return None
    message = record.get("message")
    return message.get("role") if isinstance(message, dict) else None


def _extract_cwd(records: list[dict]) -> str | None:
    for r in records:
        if r.get("type") == "session" and r.get("cwd"):
            return r["cwd"]
    return None


def _extract_title(user_msgs: list[dict]) -> str | None:
    for r in user_msgs:
        text = _msg_text(r.get("message", {}))
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


def _extract_token_count(assistant_msgs: list[dict]) -> int:
    """Sum input+output+cache tokens across each assistant turn's usage block.

    OpenClaw's own usage.totalTokens is unreliable (observed far smaller than
    input+output+cache on real transcripts), so this sums the components
    directly like the other sources do.
    """
    total = 0
    for r in assistant_msgs:
        usage = r["message"].get("usage")
        if not isinstance(usage, dict):
            continue
        total += sum(usage.get(key, 0) or 0 for key in ("input", "output", "cacheRead", "cacheWrite"))
    return total


def _extract_cost(assistant_msgs: list[dict]) -> float:
    """Sum per-turn USD cost, priced by that turn's own model.

    OpenClaw's own usage.cost block is observed as always 0 on real
    transcripts, so this reuses hades' own pricing table instead of trusting it.
    """
    total = 0.0
    for r in assistant_msgs:
        message = r["message"]
        usage = message.get("usage")
        if not isinstance(usage, dict):
            continue
        total += pricing.estimate_cost(
            message.get("model", ""),
            usage.get("input", 0) or 0,
            usage.get("output", 0) or 0,
            usage.get("cacheWrite", 0) or 0,
            usage.get("cacheRead", 0) or 0,
        )
    return total
