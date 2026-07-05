"""Single definition of "waiting on you", shared by attention, stats, and watch.

A session is *waiting* when it's a human (non-agent) session, its status is
running or idle, it was active within RECENCY_HOURS, and nothing has happened
for at least WAIT_THRESHOLD_MINUTES.
"""
from datetime import datetime, timezone, timedelta

import sqlite_utils

from hades.classify import classify_project

WAIT_THRESHOLD_MINUTES = 3
RECENCY_HOURS = 24


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
        s["_waiting_minutes"] = minutes
        s["_is_waiting"] = minutes >= WAIT_THRESHOLD_MINUTES
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
