import json
from pathlib import Path
from typing import Iterator


def iter_raw_messages(path: Path) -> Iterator[dict]:
    """Yield raw message dicts from a session file, regardless of tool format."""
    if path.suffix == ".jsonl":
        import ijson
        with open(path, "rb") as f:
            for item in ijson.items(f, "", multiple_values=True):
                if isinstance(item, dict):
                    yield item
    else:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        messages = data if isinstance(data, list) else data.get("messages", [])
        for msg in messages:
            if isinstance(msg, dict):
                yield msg


def parse_turn(msg: dict, full: bool) -> tuple[str, str] | None:
    """Normalize one raw message dict into (role, text), or None if not displayable."""
    outer_type = msg.get("type", "")

    # Claude Code format: outer type="user"/"assistant" with message.role inside
    if outer_type in ("user", "assistant") and "message" in msg:
        inner = msg["message"]
        role = inner.get("role", outer_type)
        content = inner.get("content", "")
        return _normalize_turn(role, content, full)

    # Simpler formats (Codex, Gemini, Cowork): role at top level
    role = msg.get("role", "")
    if role in ("user", "assistant", "model"):
        content = msg.get("content") or msg.get("parts", "")
        return _normalize_turn("user" if role == "user" else "assistant", content, full)

    # Cowork variant: type-based turns without an inner message
    if outer_type in ("human", "assistant") and "message" not in msg:
        content = msg.get("content", "")
        return _normalize_turn("user" if outer_type == "human" else "assistant", content, full)

    # Tool call results (only surfaced with full)
    if full and outer_type in ("tool_result", "tool_use"):
        return "tool", f"<TOOL {msg.get('name', outer_type)}>"

    return None


def _normalize_turn(role: str, content, full: bool) -> tuple[str, str] | None:
    if role not in ("user", "assistant", "model"):
        return None

    text = _extract_text(content, full)
    if not text:
        return None

    return ("user" if role == "user" else "assistant"), text


def _extract_text(content, full: bool) -> str:
    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        parts = []
        for block in content:
            if not isinstance(block, dict):
                continue
            btype = block.get("type", "")
            if btype == "text":
                text = block.get("text", "").strip()
                if text:
                    parts.append(text)
            elif btype == "thinking" and full:
                thinking = block.get("thinking", "").strip()
                if thinking:
                    parts.append(f"<thinking> {thinking[:200]}…")
            elif btype == "tool_use" and full:
                parts.append(f"<tool: {block.get('name', '?')}>")
            # Parts format (Gemini)
            elif "text" in block:
                parts.append(block["text"].strip())
        return "\n".join(parts)

    return ""
