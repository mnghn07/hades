from datetime import datetime, timezone, timedelta

import typer
from rich.console import Console
from rich.table import Table
import pendulum

from hades.db import get_db

console = Console()

WAIT_THRESHOLD_MINUTES = 3
RECENCY_HOURS = 24


def cmd_attention():
    db = get_db()
    if "sessions" not in db.table_names():
        console.print("[dim]No sessions indexed yet.[/dim]")
        return

    now = datetime.now(timezone.utc)
    recency_cutoff = (now - timedelta(hours=RECENCY_HOURS)).isoformat()

    sessions = list(db.execute(
        "SELECT * FROM sessions WHERE status IN ('running', 'idle') AND last_active_at >= ? ORDER BY last_active_at ASC",
        [recency_cutoff]
    ).fetchall())
    col_names = [d[0] for d in db.execute("SELECT * FROM sessions LIMIT 0").description]

    if not sessions:
        console.print("[green]✓ No sessions need attention.[/green]")
        return

    flagged = []
    for row in sessions:
        s = dict(zip(col_names, row))
        last_active = datetime.fromisoformat(s["last_active_at"])
        if last_active.tzinfo is None:
            last_active = last_active.replace(tzinfo=timezone.utc)

        waiting_since = now - last_active
        if waiting_since >= timedelta(minutes=WAIT_THRESHOLD_MINUTES):
            s["_waiting_minutes"] = int(waiting_since.total_seconds() / 60)
            s["_reason"] = "waiting"
            flagged.append(s)

    if not flagged:
        console.print("[green]✓ No sessions need attention.[/green]")
        return

    table = Table(show_header=True, header_style="bold", box=None, pad_edge=False)
    table.add_column("TOOL", style="cyan", width=10)
    table.add_column("PROJECT", style="white", max_width=28)
    table.add_column("WAITING", style="bold yellow", width=12)
    table.add_column("TITLE", style="dim", max_width=40)
    table.add_column("ID", style="dim", max_width=20)

    for s in sorted(flagged, key=lambda x: x["_waiting_minutes"], reverse=True):
        mins = s["_waiting_minutes"]
        wait_str = f"{mins}m" if mins < 60 else f"{mins // 60}h {mins % 60}m"
        project = s["project_path"].split("/")[-1] or s["project_path"]
        table.add_row(s["tool"], project, wait_str, (s["title"] or "")[:38], s["id"])

    console.print(f"[bold red]{len(flagged)} session(s) need your attention[/bold red]\n")
    console.print(table)
