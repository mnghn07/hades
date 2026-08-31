"""Parsing helpers shared by all session sources."""
import json
from datetime import datetime
from pathlib import Path

from hades import pricing


def read_jsonl_dicts(path: Path) -> list[dict]:
    """Read a JSONL file into a list of dicts, skipping non-dict entries."""
    import ijson
    try:
        with open(path, "rb") as f:
            return [
                item for item in ijson.items(f, "", multiple_values=True)
                if isinstance(item, dict)
            ]
    except Exception:
        return []


def read_json_document(path: Path) -> dict | list:
    """Read a whole JSON document; {} on failure."""
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def messages_of(data: dict | list) -> list[dict]:
    """Extract the message list from a JSON document (list or {'messages': [...]})."""
    items = data if isinstance(data, list) else data.get("messages", [])
    return [m for m in items if isinstance(m, dict)]


def parse_timestamps(messages: list[dict], keys: tuple[str, ...] = ("timestamp",)) -> list[datetime]:
    timestamps = []
    for m in messages:
        ts = next((m[k] for k in keys if m.get(k)), None)
        if ts:
            try:
                timestamps.append(datetime.fromisoformat(str(ts).replace("Z", "+00:00")))
            except Exception:
                pass
    return timestamps


def extract_token_count(assistant_msgs: list[dict]) -> int:
    """Sum input+output+cache tokens across each assistant turn's usage block.

    Shared by any source whose transcript format nests a Claude-shaped
    message.usage block (Claude Code and Cowork both do).
    """
    total = 0
    for m in assistant_msgs:
        usage = m.get("message", {}).get("usage")
        if not isinstance(usage, dict):
            continue
        total += sum(
            usage.get(key, 0) or 0
            for key in ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")
        )
    return total


def extract_token_breakdown(assistant_msgs: list[dict]) -> dict[str, int]:
    """Sum each of the four token categories across every assistant turn's
    usage block. Shared by any source whose transcript format nests a
    Claude-shaped message.usage block (Claude Code and Cowork both do)."""
    totals = {"input": 0, "output": 0, "cache_write": 0, "cache_read": 0}
    for m in assistant_msgs:
        usage = m.get("message", {}).get("usage")
        if not isinstance(usage, dict):
            continue
        totals["input"] += usage.get("input_tokens", 0) or 0
        totals["output"] += usage.get("output_tokens", 0) or 0
        totals["cache_write"] += usage.get("cache_creation_input_tokens", 0) or 0
        totals["cache_read"] += usage.get("cache_read_input_tokens", 0) or 0
    return totals


def extract_cost(assistant_msgs: list[dict]) -> float:
    """Sum per-turn USD cost, priced by that turn's own model."""
    total = 0.0
    for m in assistant_msgs:
        message = m.get("message", {})
        usage = message.get("usage")
        if not isinstance(usage, dict):
            continue
        total += pricing.estimate_cost(
            message.get("model", ""),
            usage.get("input_tokens", 0) or 0,
            usage.get("output_tokens", 0) or 0,
            usage.get("cache_creation_input_tokens", 0) or 0,
            usage.get("cache_read_input_tokens", 0) or 0,
        )
    return total
