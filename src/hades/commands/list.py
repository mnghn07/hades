from typing import Optional
import typer
from rich.console import Console
from rich.table import Table
import pendulum

from hades.db import get_db

console = Console()


def cmd_list(
    tool: Optional[str] = typer.Option(None, "--tool", "-t", help="Filter by tool: claude, codex, gemini, cowork"),
    active: bool = typer.Option(False, "--active", help="Show only running/idle sessions"),
    since: Optional[str] = typer.Option(None, "--since", help="Show sessions active since (e.g. 2d, 1w)"),
):
    db = get_db()
    if "sessions" not in db.table_names():
        console.print("[yellow]No sessions indexed yet. Sessions will be indexed automatically.[/yellow]")
        return

    query = "SELECT * FROM sessions ORDER BY last_active_at DESC"
    rows = list(db.execute(query).fetchall())
    col_names = [d[0] for d in db.execute(query).description]

    sessions = [dict(zip(col_names, row)) for row in rows]

    if tool:
        sessions = [s for s in sessions if s["tool"] == tool]
    if active:
        sessions = [s for s in sessions if s["status"] in ("running", "idle")]

    if not sessions:
        console.print("[dim]No sessions found.[/dim]")
        return

    table = Table(show_header=True, header_style="bold", box=None, pad_edge=False, expand=True)
    table.add_column("TOOL", style="cyan", width=10)
    table.add_column("PROJECT", style="white", max_width=30)
    table.add_column("TITLE", style="dim", max_width=40)
    table.add_column("LAST ACTIVE", style="yellow", width=14)
    table.add_column("MSGS", justify="right", width=6)
    table.add_column("STATUS", width=12)

    status_icons = {
        "running": "[green]● running[/green]",
        "idle": "[dim]○ idle[/dim]",
        "ended": "[red]✕ ended[/red]",
    }

    for s in sessions:
        last_active = pendulum.parse(s["last_active_at"]).diff_for_humans()
        project = s["project_path"].split("/")[-1] or s["project_path"]
        title = (s["title"] or "")[:38]
        status = status_icons.get(s["status"], s["status"])
        table.add_row(s["tool"], project, title, last_active, str(s["message_count"]), status)

    console.print(table)
