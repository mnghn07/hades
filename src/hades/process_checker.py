import re
from pathlib import Path

import psutil
import sqlite_utils


def get_running_sessions() -> dict[str, str]:
    """Return {cwd: tool_name} for all active AI coding CLI sessions.

    Excludes desktop app processes (cwd == '/') and unrelated processes.
    """
    running: dict[str, str] = {}

    for proc in psutil.process_iter(["pid", "name", "cmdline", "cwd"]):
        try:
            name = (proc.info.get("name") or "").lower()
            cmdline = " ".join(proc.info.get("cmdline") or []).lower()
            cwd = proc.info.get("cwd") or "/"

            # Desktop apps have cwd=/; skip them
            if cwd == "/":
                continue
            try:
                if not Path(cwd).exists():
                    continue
            except (PermissionError, OSError):
                continue

            tool = _classify(name, cmdline)
            if tool:
                running[cwd] = tool

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    return running


def update_statuses(db: sqlite_utils.Database) -> None:
    """Update session status column based on currently running processes."""
    if "sessions" not in db.table_names():
        return

    running = get_running_sessions()
    running_cwds = set(running.keys())

    # For each running CWD, find only the most recent session — a process works
    # on one session at a time, so only the latest should be marked running.
    latest_per_cwd: dict[str, str] = {}
    for cwd in running_cwds:
        row = db.execute(
            "SELECT id FROM sessions WHERE project_path = ? ORDER BY last_active_at DESC LIMIT 1",
            [cwd],
        ).fetchone()
        if row:
            latest_per_cwd[cwd] = row[0]

    running_ids = set(latest_per_cwd.values())

    rows = db.execute("SELECT id, status FROM sessions").fetchall()
    for session_id, current_status in rows:
        if session_id in running_ids:
            new_status = "running"
        elif current_status == "running":
            new_status = "ended"
        else:
            new_status = current_status

        if new_status != current_status:
            db.execute(
                "UPDATE sessions SET status = ? WHERE id = ?",
                [new_status, session_id],
            )

    db.conn.commit()


def _classify(name: str, cmdline: str) -> str | None:
    # Claude Code CLI: binary named 'claude' or a semver string (e.g. '2.1.199'),
    # always passes --output-format stream-json
    if "stream-json" in cmdline and ("claude" in name or re.match(r"\d+\.\d+\.\d+", name)):
        return "claude"

    # Codex CLI: JS shim spawns a native binary named 'codex' as a child
    # process (verified against a real npx-launched session), so the
    # eventual process name is 'codex', not 'node'.
    if "codex" in name:
        return "codex"

    # Gemini CLI (not the desktop app — already excluded by cwd check above).
    # It's a pure-JS process (no native binary), so `name` is 'node', not
    # 'gemini' — match the invoked script path instead (verified against a
    # real npx-launched session, e.g. ".../node_modules/.bin/gemini").
    if name == "gemini":
        return "gemini"
    if name == "node":
        for part in cmdline.split():
            basename = part.rsplit("/", 1)[-1]
            if basename == "gemini":
                return "gemini"

    return None
