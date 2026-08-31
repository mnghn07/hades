from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class Session:
    id: str
    tool: str  # "claude" | "codex" | "gemini" | "cowork" | "cursor" | "openclaw" | "antigravity"
    project_path: str
    started_at: datetime
    last_active_at: datetime
    message_count: int
    status: str  # "running" | "idle" | "ended"
    raw_path: Path
    title: str | None
    token_count: int = 0
    cost_usd: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_write_tokens: int = 0
    cache_read_tokens: int = 0
