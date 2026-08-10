import json

import pytest

from hades.config import get_enabled_tools, set_tool_enabled


@pytest.fixture
def isolated_config(tmp_path, monkeypatch):
    """Unlike db_path, this starts with NO config file — a genuine fresh install."""
    monkeypatch.setattr("hades.config.CONFIG_PATH", tmp_path / "config.json")
    return tmp_path / "config.json"


@pytest.mark.usefixtures("isolated_config")
def test_fresh_install_only_claude_enabled():
    assert get_enabled_tools() == {"claude"}


@pytest.mark.usefixtures("isolated_config")
def test_enable_adds_a_tool():
    set_tool_enabled("codex", True)
    assert get_enabled_tools() == {"claude", "codex"}


@pytest.mark.usefixtures("isolated_config")
def test_disable_removes_a_tool_including_claude():
    set_tool_enabled("claude", False)
    assert get_enabled_tools() == set()


def test_enable_persists_across_loads(isolated_config):
    set_tool_enabled("cowork", True)
    assert get_enabled_tools() == {"claude", "cowork"}
    # Simulate a fresh process re-reading the same config file.
    assert json.loads(isolated_config.read_text())["enabled_tools"] == ["claude", "cowork"]


@pytest.mark.usefixtures("isolated_config")
def test_disable_then_enable_is_idempotent():
    set_tool_enabled("codex", False)  # not enabled to begin with — no-op
    set_tool_enabled("codex", True)
    set_tool_enabled("codex", True)  # already enabled — no-op
    assert get_enabled_tools() == {"claude", "codex"}
