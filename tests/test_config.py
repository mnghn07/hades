from pathlib import Path

import pytest

from hades.config import DEFAULTS, get_config, load_config, set_config


@pytest.fixture(autouse=True)
def config_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "config.json"
    monkeypatch.setattr("hades.config.CONFIG_PATH", path)
    return path


def test_load_config_returns_defaults_when_no_file():
    assert load_config() == DEFAULTS


def test_get_config_unknown_key_raises():
    with pytest.raises(KeyError):
        get_config("nope")


def test_set_config_persists_and_coerces_type(config_path: Path):
    value = set_config("wait_threshold_minutes", "15")
    assert value == 15
    assert isinstance(value, int)
    assert get_config("wait_threshold_minutes") == 15
    assert config_path.exists()


def test_set_config_unknown_key_raises():
    with pytest.raises(KeyError):
        set_config("nope", "1")


def test_set_config_invalid_value_raises():
    with pytest.raises(ValueError):
        set_config("wait_threshold_minutes", "not-a-number")


def test_load_config_survives_corrupt_file(config_path: Path):
    config_path.write_text("not json")
    assert load_config() == DEFAULTS
