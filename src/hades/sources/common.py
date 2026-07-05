"""Parsing helpers shared by all session sources."""
import json
from datetime import datetime
from pathlib import Path


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
