from datetime import datetime, timezone
from pathlib import Path

from hades.models import Session
from .base import BaseSource
from .common import read_json_document, read_jsonl_dicts


class AntigravitySource(BaseSource):
    """Antigravity's own transcript store (conversations/<id>.db) is undocumented
    protobuf in SQLite blob columns — no shipped .proto schema, unreadable without
    reverse engineering it. history.jsonl (a flat, shared prompt log) is the only
    plain-JSON record available, so this source is deliberately partial: it has
    your own prompts, but never Antigravity's replies, and no token/cost data.
    """

    name = "antigravity"
    env_var = "HADES_ANTIGRAVITY_PATH"
    default_paths = [Path("~/.gemini/antigravity-cli")]

    @classmethod
    def list_files(cls) -> list[Path]:
        root = cls.discover_root()
        return list(root.glob("conversations/*.db")) if root else []

    @classmethod
    def parse_file(cls, path: Path) -> Session | None:
        conversation_id = path.stem
        entries = history_entries_for(path)
        summary = _metadata_summary(path, conversation_id)

        timestamps = [_from_epoch_ms(e["timestamp"]) for e in entries if e.get("timestamp")]
        if timestamps:
            started_at, last_active_at = min(timestamps), max(timestamps)
        else:
            mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
            started_at = last_active_at = mtime

        title = None
        if entries and entries[0].get("display"):
            title = entries[0]["display"][:80]
        elif summary.get("Title") or summary.get("Preview"):
            title = summary.get("Title") or summary.get("Preview")

        workspace_uris = summary.get("WorkspaceURIs") or []
        project_path = (
            (entries[0].get("workspace") if entries else None)
            or _strip_file_uri(workspace_uris[0] if workspace_uris else None)
            or str(path.parent)
        )

        return Session(
            id=f"antigravity:{conversation_id}",
            tool="antigravity",
            project_path=project_path,
            started_at=started_at,
            last_active_at=last_active_at,
            message_count=len(entries),
            status="idle",
            raw_path=path,
            title=title,
        )

    @classmethod
    def extract_messages(cls, path: Path) -> tuple[str, str]:
        human = " ".join(e.get("display", "") for e in history_entries_for(path))
        return human, ""


def _history_path(path: Path) -> Path:
    return path.parent.parent / "history.jsonl"


def history_entries_for(path: Path) -> list[dict]:
    """All history.jsonl prompts tagged with this session's conversation id."""
    conversation_id = path.stem
    all_entries = read_jsonl_dicts(_history_path(path))
    return [e for e in all_entries if e.get("conversationId") == conversation_id]


def _metadata_summary(path: Path, conversation_id: str) -> dict:
    metadata_path = path.parent.parent / "cache" / "conversation_metadata.json"
    data = read_json_document(metadata_path)
    if not isinstance(data, dict):
        return {}
    conv = data.get("conversations", {}).get(conversation_id, {})
    return conv.get("summary", {}) if isinstance(conv, dict) else {}


def _strip_file_uri(uri: str | None) -> str | None:
    if uri and uri.startswith("file://"):
        return uri[len("file://"):]
    return uri


def _from_epoch_ms(ms: int) -> datetime:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
