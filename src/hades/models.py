from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class Session:
    id: str
    tool: str  # "claude" | "codex" | "gemini" | "cowork"
    project_path: str
    started_at: datetime
    last_active_at: datetime
    message_count: int
    status: str  # "running" | "idle" | "ended"
    raw_path: Path
    title: str | None
