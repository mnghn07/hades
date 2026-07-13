"""Claude Code hook integration: precise "waiting on you" signal.

Claude Code fires `Stop` when it finishes responding and `Notification` when
it's idle or needs permission — both mean "waiting on you". `UserPromptSubmit`
fires when the user replies, which clears the wait. Wired into
~/.claude/settings.json by `hades hook install`, and read by hades.waiting to
replace the mtime-heuristic fallback with a fact whenever it's available.
"""
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

SETTINGS_PATH = Path.home() / ".claude" / "settings.json"

WAITING_EVENTS = ("Stop", "Notification")
RESUMED_EVENTS = ("UserPromptSubmit",)
ALL_EVENTS = WAITING_EVENTS + RESUMED_EVENTS


def _hades_command() -> str:
    return shutil.which("hades") or "hades"


def _hook_entry(command: str) -> dict:
    return {"matcher": "", "hooks": [{"type": "command", "command": command}]}


def install_hooks() -> list[str]:
    """Register hades hooks in ~/.claude/settings.json. Idempotent.

    Returns the list of event names newly installed (empty if already present).
    """
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    settings = {}
    if SETTINGS_PATH.exists():
        settings = json.loads(SETTINGS_PATH.read_text())

    hooks = settings.setdefault("hooks", {})
    hades_cmd = _hades_command()
    installed = []

    for event in ALL_EVENTS:
        command = f"{hades_cmd} hook event {event}"
        entries = hooks.setdefault(event, [])
        already_installed = any(
            command in h.get("command", "")
            for entry in entries
            for h in entry.get("hooks", [])
        )
        if not already_installed:
            entries.append(_hook_entry(command))
            installed.append(event)

    SETTINGS_PATH.write_text(json.dumps(settings, indent=2) + "\n")
    return installed


def handle_hook_event(event: str) -> None:
    """Update waiting_since for the session named in the hook payload on stdin.

    Never raises — a broken hook must not block Claude Code.
    """
    try:
        payload = json.load(sys.stdin)
        session_id = payload.get("session_id")
        if not session_id:
            return

        from hades.db import get_db
        db = get_db()
        if "sessions" not in db.table_names():
            return

        db_id = f"claude:{session_id}"
        if event in WAITING_EVENTS:
            db.execute(
                "UPDATE sessions SET waiting_since = ? WHERE id = ? AND waiting_since IS NULL",
                [datetime.now(timezone.utc).isoformat(), db_id],
            )
        elif event in RESUMED_EVENTS:
            db.execute("UPDATE sessions SET waiting_since = NULL WHERE id = ?", [db_id])
        db.conn.commit()
    except Exception:
        pass
