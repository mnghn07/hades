from .claude import ClaudeSource
from .codex import CodexSource
from .gemini import GeminiSource
from .cowork import CoworkSource
from .cursor import CursorSource
from .openclaw import OpenclawSource
from .antigravity import AntigravitySource

ALL_SOURCES = [
    ClaudeSource, CodexSource, GeminiSource, CoworkSource, CursorSource, OpenclawSource, AntigravitySource,
]
