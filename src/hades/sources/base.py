from abc import ABC, abstractmethod
from pathlib import Path

from hades.models import Session


class BaseSource(ABC):
    name: str
    default_paths: list[Path]
    env_var: str

    @classmethod
    def discover_root(cls) -> Path | None:
        import os
        override = os.environ.get(cls.env_var)
        if override:
            p = Path(override).expanduser()
            return p if p.exists() else None
        for candidate in cls.default_paths:
            p = candidate.expanduser()
            if p.exists():
                return p
        return None

    @classmethod
    @abstractmethod
    def list_files(cls) -> list[Path]:
        """Return all session file paths for this source."""

    @classmethod
    @abstractmethod
    def parse_file(cls, path: Path) -> Session | None:
        """Parse a single session file into a Session object."""

    @classmethod
    @abstractmethod
    def extract_messages(cls, path: Path) -> tuple[str, str]:
        """Return (human_messages_text, assistant_messages_text) for FTS indexing."""

    @classmethod
    def scan(cls) -> list[Session]:
        return [s for path in cls.list_files() if (s := cls.parse_file(path)) is not None]
