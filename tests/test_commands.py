"""End-to-end command tests through the real CLI entry point.

These cover the layer the unit tests miss: rendering, FTS query handling,
and cross-command consistency.
"""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from typer.testing import CliRunner

from hades.cli import app

runner = CliRunner()


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


@pytest.fixture
def stores(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, db_path) -> Path:  # pylint: disable=unused-argument
    """A fake claude + codex store; gemini/cowork point at nothing."""
    now = datetime.now(timezone.utc)

    claude_dir = tmp_path / "claude" / "-Users-me-projects-alpha"
    claude_dir.mkdir(parents=True)
    with open(claude_dir / "sess-a.jsonl", "w", encoding="utf-8") as f:
        f.write(json.dumps({
            "type": "user", "sessionId": "sess-a", "cwd": "/Users/me/projects/alpha",
            "timestamp": _iso(now - timedelta(hours=2)),
            "message": {"role": "user", "content": "fix the auth-token bug [red]urgent[/red]"},
        }) + "\n")
        f.write(json.dumps({
            "type": "assistant", "sessionId": "sess-a",
            "timestamp": _iso(now - timedelta(hours=2)),
            "message": {"role": "assistant",
                        "content": [{"type": "text", "text": "Looking at the auth-token issue."}]},
        }) + "\n")
    # Resumed session: new file, same inner sessionId.
    with open(claude_dir / "sess-b.jsonl", "w", encoding="utf-8") as f:
        f.write(json.dumps({
            "type": "user", "sessionId": "sess-a", "cwd": "/Users/me/projects/alpha",
            "timestamp": _iso(now - timedelta(hours=1)),
            "message": {"role": "user", "content": "continue the auth fix"},
        }) + "\n")

    codex_dir = tmp_path / "codex" / "2026" / "07" / "05"
    codex_dir.mkdir(parents=True)
    with open(codex_dir / "rollout-x.jsonl", "w", encoding="utf-8") as f:
        f.write(json.dumps({"timestamp": _iso(now - timedelta(hours=3)), "type": "session_meta",
                            "payload": {"cwd": "/Users/me/projects/ml-pipeline"}}) + "\n")
        f.write(json.dumps({"timestamp": _iso(now - timedelta(hours=3)),
                            "role": "user", "content": "train the model"}) + "\n")

    monkeypatch.setenv("HADES_CLAUDE_PATH", str(tmp_path / "claude"))
    monkeypatch.setenv("HADES_CODEX_PATH", str(tmp_path / "codex"))
    monkeypatch.setenv("HADES_GEMINI_PATH", str(tmp_path / "missing"))
    monkeypatch.setenv("HADES_COWORK_PATH", str(tmp_path / "missing"))
    monkeypatch.setenv("COLUMNS", "200")  # keep tables from truncating in assertions
    return tmp_path


@pytest.fixture
def empty_stores(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, db_path) -> None:  # pylint: disable=unused-argument
    """All sources point at a missing dir, isolating tests from the real ~/.claude."""
    missing = tmp_path / "missing"
    for env_var in ("HADES_CLAUDE_PATH", "HADES_CODEX_PATH", "HADES_GEMINI_PATH", "HADES_COWORK_PATH"):
        monkeypatch.setenv(env_var, str(missing))


@pytest.mark.usefixtures("stores")
def test_search_survives_hyphens_and_quotes():
    result = runner.invoke(app, ["search", "auth-token"])
    assert result.exit_code == 0, result.output
    assert "auth" in result.output

    result = runner.invoke(app, ["search", 'what"s up ('])
    assert result.exit_code == 0, result.output


@pytest.mark.usefixtures("stores")
def test_list_escapes_rich_markup_in_titles():
    result = runner.invoke(app, ["list", "--all"])
    assert result.exit_code == 0, result.output
    # The [red] tag must appear as literal text, not be swallowed as markup.
    assert "[red]" in result.output


@pytest.mark.usefixtures("stores")
def test_resumed_session_files_are_indexed_separately():
    result = runner.invoke(app, ["search", "continue"])
    assert result.exit_code == 0, result.output
    assert "continue" in result.output

    result = runner.invoke(app, ["list", "--all"])
    assert result.output.count("alpha") == 2


@pytest.mark.usefixtures("stores")
def test_codex_project_path_comes_from_session_meta():
    result = runner.invoke(app, ["list", "--all"])
    assert result.exit_code == 0, result.output
    assert "ml-pipeline" in result.output
    assert " 05 " not in result.output


@pytest.mark.usefixtures("stores")
def test_attention_and_stats_agree_on_waiting_count():
    attention = runner.invoke(app, ["attention"])
    stats = runner.invoke(app, ["stats"])
    assert attention.exit_code == 0 and stats.exit_code == 0

    # Three sessions, all idle for hours: both commands must report 3.
    assert "3 session(s) need your attention" in attention.output
    assert "3 session(s) waiting on you" in stats.output


def test_missing_store_does_not_wipe_index(stores, monkeypatch):
    runner.invoke(app, ["list", "--all"])

    # Simulate the store becoming unreachable (unmounted disk, bad override).
    monkeypatch.setenv("HADES_CLAUDE_PATH", str(stores / "gone"))
    monkeypatch.setenv("HADES_CODEX_PATH", str(stores / "gone"))
    result = runner.invoke(app, ["list", "--all"])

    assert result.exit_code == 0, result.output
    assert "alpha" in result.output
    assert "ml-pipeline" in result.output


@pytest.mark.usefixtures("stores")
def test_show_renders_transcript():
    result = runner.invoke(app, ["show", "codex:rollout-x"])
    assert result.exit_code == 0, result.output
    assert "train the model" in result.output


@pytest.mark.usefixtures("stores")
def test_list_json_is_valid_and_matches_table():
    result = runner.invoke(app, ["list", "--all", "--json"])
    assert result.exit_code == 0, result.output
    rows = json.loads(result.output)
    assert {r["project"] for r in rows} == {"alpha", "ml-pipeline"}
    assert all("id" in r and "status" in r for r in rows)


@pytest.mark.usefixtures("stores")
def test_list_json_escapes_nothing_raw_in_titles():
    # Rich markup escaping is a table-rendering concern; JSON must carry the
    # raw title untouched, not the [red]-escaped display string.
    result = runner.invoke(app, ["list", "--all", "--json"])
    rows = json.loads(result.output)
    alpha = next(r for r in rows if r["title"] and "auth-token bug" in r["title"])
    assert alpha["title"] == "fix the auth-token bug [red]urgent[/red]"


def test_list_json_empty_index_returns_empty_array(empty_stores):  # pylint: disable=unused-argument
    result = runner.invoke(app, ["list", "--json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == []


@pytest.mark.usefixtures("stores")
def test_attention_json_matches_table_count():
    result = runner.invoke(app, ["attention", "--json"])
    assert result.exit_code == 0, result.output
    rows = json.loads(result.output)
    assert len(rows) == 3
    assert {"id", "tool", "project", "title", "waiting_minutes"} <= rows[0].keys()


@pytest.mark.usefixtures("stores")
def test_stats_json_matches_attention_waiting_count():
    stats = json.loads(runner.invoke(app, ["stats", "--json"]).output)
    attention = json.loads(runner.invoke(app, ["attention", "--json"]).output)
    assert stats["waiting_count"] == len(attention)
    assert stats["total_sessions"] == 3
    assert set(stats["by_tool"]) == {"claude", "codex"}


@pytest.mark.usefixtures("stores")
def test_search_json_includes_id_and_plain_snippet():
    result = runner.invoke(app, ["search", "auth-token", "--json"])
    assert result.exit_code == 0, result.output
    rows = json.loads(result.output)
    assert rows
    assert rows[0]["id"].startswith("claude:")
    # No leftover private-use highlight sentinels in the JSON snippet.
    assert "" not in rows[0]["snippet"] and "" not in rows[0]["snippet"]


def test_search_json_no_matches_returns_empty_array(empty_stores):  # pylint: disable=unused-argument
    result = runner.invoke(app, ["search", "nothing-will-match-this", "--json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == []


@pytest.mark.usefixtures("stores")
def test_no_color_flag_strips_ansi_codes():
    plain = runner.invoke(app, ["--no-color", "list", "--all"])
    colored = runner.invoke(app, ["list", "--all"])
    assert plain.exit_code == 0, plain.output
    assert "\x1b[" not in plain.output
    # Sanity check the fixture actually distinguishes the two paths in some
    # environment; CliRunner output is captured non-tty either way, so rich
    # may already suppress color in `colored` too — this just guards against
    # --no-color *adding* escape codes, which would be the real regression.
    assert "\x1b[" not in colored.output
