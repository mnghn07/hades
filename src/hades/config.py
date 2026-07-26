"""Persistent, user-editable settings (`hades config get/set/list`).

A tiny key -> typed-default registry backed by a JSON file. Adding a new
setting means adding one entry to DEFAULTS; get/set/list all pick it up.
"""
import json
from pathlib import Path

from platformdirs import user_data_dir

CONFIG_PATH = Path(user_data_dir("hades")) / "config.json"

DEFAULTS = {
    "wait_threshold_minutes": 3,
}


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return dict(DEFAULTS)
    try:
        data = json.loads(CONFIG_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return dict(DEFAULTS)
    return {**DEFAULTS, **data}


def get_config(key: str):
    if key not in DEFAULTS:
        raise KeyError(key)
    return load_config()[key]


def set_config(key: str, raw_value: str):
    """Coerce raw_value to the type of the key's default, persist, and return it."""
    if key not in DEFAULTS:
        raise KeyError(key)
    coerced = type(DEFAULTS[key])(raw_value)
    data = load_config()
    data[key] = coerced
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(data, indent=2))
    return coerced
