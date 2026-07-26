"""Single definition of "waiting on you", shared by attention, stats, and watch.

A session is *waiting* when it's a human (non-agent) session, its status is
running or idle, it was active within RECENCY_HOURS, and nothing has happened
for at least the wait threshold (default 3 min; `hades config set
wait_threshold_minutes N`, or HADES_WAIT_THRESHOLD_MINUTES for a one-off
override).
"""
import os
from datetime import datetime, timezone, timedelta

import sqlite_utils

from hades.classify import classify_project
from hades.config import get_config

RECENCY_HOURS = 24


def wait_threshold_minutes() -> int:
    raw = os.environ.get("HADES_WAIT_THRESHOLD_MINUTES")
    if raw:
        try:
            return int(raw)
        except ValueError:
            pass
    return get_config("wait_threshold_minutes")


def recent_human_sessions(db: sqlite_utils.Database, now: datetime | None = None) -> list[dict]:
    """Human sessions active within RECENCY_HOURS, oldest-activity first.

    Each dict gains `_waiting_minutes` and `_is_waiting`.
    """
    if "sessions" not in db.table_names():
        return []

    now = now or datetime.now(timezone.utc)
    recency_cutoff = (now - timedelta(hours=RECENCY_HOURS)).isoformat()

    cursor = db.execute(
        "SELECT * FROM sessions WHERE status IN ('running', 'idle') "
        "AND last_active_at >= ? AND is_archived IS NOT 1 "
        "ORDER BY last_active_at ASC",
        [recency_cutoff],
    )
    col_names = [d[0] for d in cursor.description]

    result = []
    for row in cursor.fetchall():
        s = dict(zip(col_names, row))
        _, session_type = classify_project(s["project_path"])
        if session_type != "human":
            continue

        last_active = datetime.fromisoformat(s["last_active_at"])
        if last_active.tzinfo is None:
            last_active = last_active.replace(tzinfo=timezone.utc)

        minutes = int((now - last_active).total_seconds() / 60)
        waiting_since = s.get("waiting_since")
        if waiting_since:
            ws = datetime.fromisoformat(waiting_since)
            if ws.tzinfo is None:
                ws = ws.replace(tzinfo=timezone.utc)
            s["_waiting_minutes"] = int((now - ws).total_seconds() / 60)
            s["_is_waiting"] = True
        else:
            s["_waiting_minutes"] = minutes
            s["_is_waiting"] = minutes >= wait_threshold_minutes()
        result.append(s)

    return result


def waiting_sessions(db: sqlite_utils.Database, now: datetime | None = None) -> list[dict]:
    """Sessions currently waiting on the user, longest wait first."""
    waiting = [s for s in recent_human_sessions(db, now) if s["_is_waiting"]]
    return sorted(waiting, key=lambda s: s["_waiting_minutes"], reverse=True)


def format_wait(minutes: int) -> str:
    if minutes < 60:
        return f"{minutes}m"
    return f"{minutes // 60}h {minutes % 60}m"
