from rich import box
from rich.console import Console
from rich.markup import escape
from rich.table import Table

from hades.db import get_db
from hades.waiting import format_wait, waiting_sessions

console = Console()


def cmd_attention():
    db = get_db()
    if "sessions" not in db.table_names():
        console.print("[dim]No sessions indexed yet.[/dim]")
        return

    flagged = waiting_sessions(db)
    if not flagged:
        console.print("[green]✓ No sessions need attention.[/green]")
        return

    table = Table(show_header=True, header_style="bold", box=box.ROUNDED)
    table.add_column("TOOL", style="cyan", width=10)
    table.add_column("PROJECT", style="white", max_width=28)
    table.add_column("WAITING", style="bold yellow", width=12)
    table.add_column("TITLE", style="dim", max_width=40)
    table.add_column("ID", style="dim", max_width=20)

    for s in flagged:
        project = s["project_path"].split("/")[-1] or s["project_path"]
        table.add_row(
            escape(s["tool"]), escape(project), format_wait(s["_waiting_minutes"]),
            escape((s["title"] or "")[:38]), escape(s["id"]),
        )

    console.print(f"[bold red]{len(flagged)} session(s) need your attention[/bold red]\n")
    console.print(table)
