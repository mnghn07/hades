from datetime import datetime, timezone, timedelta

import typer
from rich import box
from rich.console import Console
from rich.table import Table
import pendulum

from hades.classify import classify_project
from hades.db import get_db

console = Console()

WAIT_THRESHOLD_MINUTES = 3
STATUS_ORDER = ["running", "idle", "ended"]


def _last_active(session: dict) -> datetime:
    dt = datetime.fromisoformat(session["last_active_at"])
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def cmd_stats(
    day: int = typer.Option(0, "--day", help="Only include sessions active within the last N days"),
    hour: int = typer.Option(0, "--hour", help="Only include sessions active within the last N hours"),
    minute: int = typer.Option(0, "--min", help="Only include sessions active within the last N minutes"),
):
    db = get_db()
    if "sessions" not in db.table_names():
        console.print("[dim]No sessions indexed yet.[/dim]")
        return

    rows = list(db.execute("SELECT * FROM sessions").fetchall())
    col_names = [d[0] for d in db.execute("SELECT * FROM sessions LIMIT 0").description]
    sessions = [dict(zip(col_names, row)) for row in rows]

    if day or hour or minute:
        cutoff = datetime.now(timezone.utc) - timedelta(days=day, hours=hour, minutes=minute)
        sessions = [s for s in sessions if _last_active(s) >= cutoff]

    if not sessions:
        console.print("[dim]No sessions found.[/dim]")
        return

    total_sessions = len(sessions)
    total_messages = sum(s["message_count"] for s in sessions)
    status_counts = {status: 0 for status in STATUS_ORDER}
    for s in sessions:
        status_counts[s["status"]] = status_counts.get(s["status"], 0) + 1

    console.print(
        f"[bold]{total_sessions}[/bold] sessions, "
        f"[bold]{total_messages}[/bold] messages "
        f"([green]{status_counts.get('running', 0)} running[/green], "
        f"[dim]{status_counts.get('idle', 0)} idle[/dim], "
        f"[red]{status_counts.get('ended', 0)} ended[/red])\n"
    )

    by_tool: dict[str, dict] = {}
    for s in sessions:
        entry = by_tool.setdefault(s["tool"], {"sessions": 0, "messages": 0, "last_active": _last_active(s)})
        entry["sessions"] += 1
        entry["messages"] += s["message_count"]
        entry["last_active"] = max(entry["last_active"], _last_active(s))

    table = Table(show_header=True, header_style="bold", box=box.ROUNDED)
    table.add_column("TOOL", style="cyan", width=10)
    table.add_column("SESSIONS", justify="right", width=10)
    table.add_column("MESSAGES", justify="right", width=10)
    table.add_column("LAST ACTIVE", style="yellow", width=14)

    for tool_name in sorted(by_tool, key=lambda t: by_tool[t]["sessions"], reverse=True):
        entry = by_tool[tool_name]
        last_active = pendulum.instance(entry["last_active"]).diff_for_humans()
        table.add_row(tool_name, str(entry["sessions"]), str(entry["messages"]), last_active)

    console.print(table)

    now = datetime.now(timezone.utc)
    waiting = []
    for s in sessions:
        if s["status"] not in ("running", "idle"):
            continue
        _, session_type = classify_project(s["project_path"])
        if session_type != "human":
            continue
        waiting_minutes = int((now - _last_active(s)).total_seconds() / 60)
        if waiting_minutes >= WAIT_THRESHOLD_MINUTES:
            waiting.append(waiting_minutes)

    if waiting:
        longest = max(waiting)
        longest_str = f"{longest}m" if longest < 60 else f"{longest // 60}h {longest % 60}m"
        console.print(f"\n[bold red]{len(waiting)} session(s) waiting on you[/bold red], longest {longest_str}")
    else:
        console.print("\n[green]✓ No sessions waiting on you[/green]")
