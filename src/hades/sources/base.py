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
    def scan(cls) -> list[Session]:
        ...
