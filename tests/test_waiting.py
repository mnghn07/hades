from pathlib import Path

import pytest

from hades.waiting import wait_threshold_minutes
from hades.config import DEFAULTS


@pytest.fixture(autouse=True)
def config_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Isolate config.json so these tests never touch the real user config."""
    path = tmp_path / "config.json"
    monkeypatch.setattr("hades.config.CONFIG_PATH", path)
    monkeypatch.delenv("HADES_WAIT_THRESHOLD_MINUTES", raising=False)
    return path


def test_wait_threshold_defaults_when_unset():
    assert wait_threshold_minutes() == DEFAULTS["wait_threshold_minutes"]


def test_wait_threshold_reads_env_override(monkeypatch):
    monkeypatch.setenv("HADES_WAIT_THRESHOLD_MINUTES", "10")
    assert wait_threshold_minutes() == 10


def test_wait_threshold_falls_back_on_garbage_env_value(monkeypatch):
    monkeypatch.setenv("HADES_WAIT_THRESHOLD_MINUTES", "not-a-number")
    assert wait_threshold_minutes() == DEFAULTS["wait_threshold_minutes"]


def test_wait_threshold_reads_persisted_config():
    from hades.config import set_config
    set_config("wait_threshold_minutes", "7")
    assert wait_threshold_minutes() == 7


def test_env_override_wins_over_persisted_config(monkeypatch):
    from hades.config import set_config
    set_config("wait_threshold_minutes", "7")
    monkeypatch.setenv("HADES_WAIT_THRESHOLD_MINUTES", "10")
    assert wait_threshold_minutes() == 10
