import json
from datetime import datetime, timezone, timedelta

import typer
from rich import box
from rich.markup import escape
from rich.table import Table
import pendulum

from hades.classify import classify_project
from hades.db import get_db

from hades.console import console

DEFAULT_RECENCY_DAYS = 3
STATUS_RANK = {"running": 2, "idle": 1, "ended": 0}


def _last_active(session: dict) -> datetime:
    dt = datetime.fromisoformat(session["last_active_at"])
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _group_agent_sessions(sessions: list[dict]) -> list[dict]:
    """Collapse background/observer sessions into one summary row per (tool, project)."""
    groups: dict[tuple[str, str], dict] = {}
    for s in sessions:
        key = (s["tool"], s["_display_project"])
        group = groups.get(key)
        if group is None:
            groups[key] = {
                "tool": s["tool"],
                "_display_project": s["_display_project"],
                "_session_type": "agent",
                "title": None,
                "last_active_at": s["last_active_at"],
                "message_count": s["message_count"],
                "status": s["status"],
                "_count": 1,
            }
            continue
        group["message_count"] += s["message_count"]
        group["_count"] += 1
        if _last_active(s) > _last_active(group):
            group["last_active_at"] = s["last_active_at"]
        if STATUS_RANK[s["status"]] > STATUS_RANK[group["status"]]:
            group["status"] = s["status"]
    return list(groups.values())


def cmd_list(
    tool: str | None = typer.Option(None, "--tool", "-t", help="Filter by tool: claude, codex, gemini, cowork"),
    active: bool = typer.Option(False, "--active", help="Show only running/idle sessions"),
    day: int = typer.Option(0, "--day", help="Show sessions active within the last N days"),
    hour: int = typer.Option(0, "--hour", help="Show sessions active within the last N hours"),
    minute: int = typer.Option(0, "--min", help="Show sessions active within the last N minutes"),
    show_all: bool = typer.Option(False, "--all", help="Show every session, ignoring recency"),
    show_archived: bool = typer.Option(False, "--show-archived", help="Include archived sessions"),
    json_out: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    db = get_db()
    if "sessions" not in db.table_names():
        if json_out:
            typer.echo("[]")
        else:
            console.print("[yellow]No sessions indexed yet. Sessions will be indexed automatically.[/yellow]")
        return

    query = "SELECT * FROM sessions ORDER BY last_active_at DESC"
    rows = list(db.execute(query).fetchall())
    col_names = [d[0] for d in db.execute(query).description]

    sessions = [dict(zip(col_names, row)) for row in rows]

    if not show_archived:
        sessions = [s for s in sessions if not s["is_archived"]]

    if tool:
        sessions = [s for s in sessions if s["tool"] == tool]
    if active:
        sessions = [s for s in sessions if s["status"] in ("running", "idle")]
    if not show_all:
        if day or hour or minute:
            recency = timedelta(days=day, hours=hour, minutes=minute)
        else:
            recency = timedelta(days=DEFAULT_RECENCY_DAYS)
        cutoff = datetime.now(timezone.utc) - recency
        sessions = [s for s in sessions if _last_active(s) >= cutoff]

    if not sessions:
        if json_out:
            typer.echo("[]")
        else:
            console.print("[dim]No sessions found.[/dim]")
        return

    human_sessions = []
    agent_sessions = []
    for s in sessions:
        display_project, session_type = classify_project(s["project_path"])
        s["_display_project"] = display_project
        s["_session_type"] = session_type
        (human_sessions if session_type == "human" else agent_sessions).append(s)

    rows = human_sessions + _group_agent_sessions(agent_sessions)
    rows.sort(key=_last_active, reverse=True)

    if json_out:
        typer.echo(json.dumps([
            {
                "id": s.get("id"),
                "tool": s["tool"],
                "project": s["_display_project"],
                "type": s["_session_type"],
                "title": None if s["_session_type"] == "agent" else s["title"],
                "session_count": s.get("_count", 1),
                "last_active_at": s["last_active_at"],
                "message_count": s["message_count"],
                "status": s["status"],
            }
            for s in rows
        ], indent=2))
        return

    table = Table(show_header=True, header_style="bold", box=box.ROUNDED, expand=True)
    table.add_column("TOOL", style="cyan", width=10)
    table.add_column("PROJECT", style="white", max_width=30)
    table.add_column("TYPE", style="magenta", width=8)
    table.add_column("TITLE", style="dim", max_width=40)
    table.add_column("LAST ACTIVE", style="yellow", width=14)
    table.add_column("MSGS", justify="right", width=6)
    table.add_column("STATUS", width=12)

    status_icons = {
        "running": "[green]● running[/green]",
        "idle": "[dim]○ idle[/dim]",
        "ended": "[red]✕ ended[/red]",
    }

    for s in rows:
        last_active = pendulum.parse(s["last_active_at"]).diff_for_humans()
        if s["_session_type"] == "agent":
            title = f"{s['_count']} session{'s' if s['_count'] != 1 else ''}"
        else:
            title = (s["title"] or "")[:38]
        status = status_icons.get(s["status"], s["status"])
        table.add_row(
            escape(s["tool"]), escape(s["_display_project"]), s["_session_type"], escape(title),
            last_active, str(s["message_count"]), status,
        )

    console.print(table)
