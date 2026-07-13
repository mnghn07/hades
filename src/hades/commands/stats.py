import json
from datetime import datetime, timezone, timedelta

import typer
from rich import box
from rich.markup import escape
from rich.table import Table
import pendulum

from hades.db import get_db
from hades.waiting import format_wait, waiting_sessions

from hades.console import console

STATUS_ORDER = ["running", "idle", "ended"]


def _last_active(session: dict) -> datetime:
    dt = datetime.fromisoformat(session["last_active_at"])
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def cmd_stats(
    day: int = typer.Option(0, "--day", help="Only include sessions active within the last N days"),
    hour: int = typer.Option(0, "--hour", help="Only include sessions active within the last N hours"),
    minute: int = typer.Option(0, "--min", help="Only include sessions active within the last N minutes"),
    json_out: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    db = get_db()
    if "sessions" not in db.table_names():
        if json_out:
            typer.echo("{}")
        else:
            console.print("[dim]No sessions indexed yet.[/dim]")
        return

    rows = list(db.execute("SELECT * FROM sessions").fetchall())
    col_names = [d[0] for d in db.execute("SELECT * FROM sessions LIMIT 0").description]
    sessions = [dict(zip(col_names, row)) for row in rows]

    if day or hour or minute:
        cutoff = datetime.now(timezone.utc) - timedelta(days=day, hours=hour, minutes=minute)
        sessions = [s for s in sessions if _last_active(s) >= cutoff]

    if not sessions:
        if json_out:
            typer.echo("{}")
        else:
            console.print("[dim]No sessions found.[/dim]")
        return

    total_sessions = len(sessions)
    total_messages = sum(s["message_count"] for s in sessions)
    status_counts = {status: 0 for status in STATUS_ORDER}
    for s in sessions:
        status_counts[s["status"]] = status_counts.get(s["status"], 0) + 1

    by_tool: dict[str, dict] = {}
    for s in sessions:
        entry = by_tool.setdefault(s["tool"], {"sessions": 0, "messages": 0, "last_active": _last_active(s)})
        entry["sessions"] += 1
        entry["messages"] += s["message_count"]
        entry["last_active"] = max(entry["last_active"], _last_active(s))

    waiting = waiting_sessions(db)

    if json_out:
        typer.echo(json.dumps({
            "total_sessions": total_sessions,
            "total_messages": total_messages,
            "status_counts": status_counts,
            "by_tool": {
                tool_name: {
                    "sessions": entry["sessions"],
                    "messages": entry["messages"],
                    "last_active_at": entry["last_active"].isoformat(),
                }
                for tool_name, entry in by_tool.items()
            },
            "waiting_count": len(waiting),
            "waiting_minutes_longest": waiting[0]["_waiting_minutes"] if waiting else None,
        }, indent=2))
        return

    console.print(
        f"[bold]{total_sessions}[/bold] sessions, "
        f"[bold]{total_messages}[/bold] messages "
        f"([green]{status_counts.get('running', 0)} running[/green], "
        f"[dim]{status_counts.get('idle', 0)} idle[/dim], "
        f"[red]{status_counts.get('ended', 0)} ended[/red])\n"
    )

    table = Table(show_header=True, header_style="bold", box=box.ROUNDED)
    table.add_column("TOOL", style="cyan", width=10)
    table.add_column("SESSIONS", justify="right", width=10)
    table.add_column("MESSAGES", justify="right", width=10)
    table.add_column("LAST ACTIVE", style="yellow", width=14)

    for tool_name in sorted(by_tool, key=lambda t: by_tool[t]["sessions"], reverse=True):
        entry = by_tool[tool_name]
        last_active = pendulum.instance(entry["last_active"]).diff_for_humans()
        table.add_row(escape(tool_name), str(entry["sessions"]), str(entry["messages"]), last_active)

    console.print(table)

    # Same definition as `hades attention` — the two must never disagree.
    if waiting:
        longest = waiting[0]["_waiting_minutes"]
        console.print(
            f"\n[bold red]{len(waiting)} session(s) waiting on you[/bold red], longest {format_wait(longest)}"
        )
    else:
        console.print("\n[green]✓ No sessions waiting on you[/green]")
