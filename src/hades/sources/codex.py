from datetime import datetime, timezone
from pathlib import Path

from hades import pricing
from hades.models import Session
from .base import BaseSource
from .common import parse_timestamps, read_jsonl_dicts


class CodexSource(BaseSource):
    name = "codex"
    env_var = "HADES_CODEX_PATH"
    default_paths = [Path("~/.codex/sessions")]
    # v2: backfills the four token-category columns (input/output/cache-write/cache-read).
    PARSER_VERSION = 2

    @classmethod
    def list_files(cls) -> list[Path]:
        root = cls.discover_root()
        return list(root.rglob("rollout-*.jsonl")) if root else []

    @classmethod
    def parse_file(cls, path: Path) -> Session | None:
        records = read_jsonl_dicts(path)
        if not records:
            return None

        timestamps = parse_timestamps(records)
        started_at = min(timestamps) if timestamps else datetime.now(timezone.utc)
        last_active_at = max(timestamps) if timestamps else started_at

        turns = [r for r in records if _turn_role(r) in ("user", "assistant")]
        breakdown = _extract_token_breakdown(records)

        return Session(
            id=f"codex:{path.stem}",
            tool="codex",
            project_path=_extract_cwd(records) or str(path.parent),
            started_at=started_at,
            last_active_at=last_active_at,
            message_count=len(turns),
            status="idle",
            raw_path=path,
            title=_extract_title(turns),
            token_count=_extract_token_count(records),
            cost_usd=_extract_cost(records),
            input_tokens=breakdown["input"],
            output_tokens=breakdown["output"],
            cache_write_tokens=breakdown["cache_write"],
            cache_read_tokens=breakdown["cache_read"],
        )

    @classmethod
    def extract_messages(cls, path: Path) -> tuple[str, str]:
        records = read_jsonl_dicts(path)
        human = " ".join(_content_text(r["payload"]) for r in records if _turn_role(r) == "user")
        assistant = " ".join(_content_text(r["payload"]) for r in records if _turn_role(r) == "assistant")
        return human, assistant


def _turn_role(record: dict) -> str | None:
    """A real conversational turn: response_item envelope, payload.type=="message".

    Excludes the "developer" role — injected app/plugin context, not something
    either party actually said (mirrors Claude source's XML-prefix filtering
    of harness-injected content).
    """
    if record.get("type") != "response_item":
        return None
    payload = record.get("payload")
    if not isinstance(payload, dict) or payload.get("type") != "message":
        return None
    role = payload.get("role")
    return role if role in ("user", "assistant") else None


def _content_text(payload: dict) -> str:
    content = payload.get("content", "")
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") in ("input_text", "output_text"):
                text = block.get("text", "").strip()
                if text:
                    parts.append(text)
        return "\n".join(parts)
    return str(content).strip() if content else ""


def _extract_title(turns: list[dict]) -> str | None:
    for r in turns:
        if _turn_role(r) != "user":
            continue
        text = _content_text(r["payload"])
        if text and not text.startswith("<"):
            return text[:80]
    return None


def _extract_cwd(records: list[dict]) -> str | None:
    """Codex rollout files carry the working directory in the session_meta
    record (payload.cwd) or as a top-level cwd on some records."""
    for r in records:
        payload = r.get("payload")
        if isinstance(payload, dict) and payload.get("cwd"):
            return payload["cwd"]
        if r.get("cwd"):
            return r["cwd"]
    return None


def _last_token_usage(records: list[dict]) -> dict | None:
    """The final token_count event carries session-cumulative totals already —
    unlike Claude/Cowork/OpenClaw's per-turn usage blocks, these aren't summed."""
    last = None
    for r in records:
        if r.get("type") != "event_msg":
            continue
        payload = r.get("payload", {})
        if payload.get("type") != "token_count":
            continue
        usage = (payload.get("info") or {}).get("total_token_usage")
        if isinstance(usage, dict):
            last = usage
    return last


def _extract_token_count(records: list[dict]) -> int:
    usage = _last_token_usage(records)
    return usage.get("total_tokens", 0) or 0 if usage else 0


def _extract_token_breakdown(records: list[dict]) -> dict[str, int]:
    """The cumulative usage dict already carries all four categories — no
    summing needed, same as _extract_cost."""
    usage = _last_token_usage(records)
    if not usage:
        return {"input": 0, "output": 0, "cache_write": 0, "cache_read": 0}
    return {
        "input": usage.get("input_tokens", 0) or 0,
        "output": usage.get("output_tokens", 0) or 0,
        "cache_write": usage.get("cache_write_input_tokens", 0) or 0,
        "cache_read": usage.get("cached_input_tokens", 0) or 0,
    }


def _extract_model(records: list[dict]) -> str | None:
    for r in records:
        if r.get("type") != "world_state":
            continue
        state = r.get("payload", {}).get("state", {})
        model = state.get("collaboration_mode", {}).get("model")
        if model:
            return model
    return None


def _extract_cost(records: list[dict]) -> float:
    """Priced via hades' own (Claude-only) table — Codex's OpenAI models aren't
    in it, so this returns 0.0 today, same as any other unrecognized model."""
    usage = _last_token_usage(records)
    if not usage:
        return 0.0
    return pricing.estimate_cost(
        _extract_model(records) or "",
        usage.get("input_tokens", 0) or 0,
        usage.get("output_tokens", 0) or 0,
        usage.get("cache_write_input_tokens", 0) or 0,
        usage.get("cached_input_tokens", 0) or 0,
    )
