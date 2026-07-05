import typer
from rich import box
from rich.console import Console
from rich.table import Table
import pendulum

from hades.classify import classify_project
from hades.db import get_db

console = Console()

DEFAULT_LIMIT = 20


def cmd_search(
    query: str = typer.Argument(..., help="Full-text search query"),
    tool: str | None = typer.Option(None, "--tool", "-t", help="Filter by tool: claude, codex, gemini, cowork"),
    limit: int = typer.Option(DEFAULT_LIMIT, "--limit", "-n", help="Max results to show"),
    show_archived: bool = typer.Option(False, "--show-archived", help="Include archived sessions"),
):
    db = get_db()
    if "sessions" not in db.table_names():
        console.print("[yellow]No sessions indexed yet. Sessions will be indexed automatically.[/yellow]")
        return

    sql = """
        SELECT
            sessions.tool, sessions.project_path, sessions.title,
            sessions.last_active_at, sessions.status,
            snippet(sessions_fts, -1, '[bold yellow]', '[/bold yellow]', '…', 12) AS snippet
        FROM sessions_fts
        JOIN sessions ON sessions.id = sessions_fts.id
        WHERE sessions_fts MATCH ?
    """
    params: list = [query]
    if not show_archived:
        sql += " AND (sessions.is_archived IS NULL OR sessions.is_archived = 0)"
    if tool:
        sql += " AND sessions.tool = ?"
        params.append(tool)
    sql += " ORDER BY rank LIMIT ?"
    params.append(limit)

    rows = list(db.execute(sql, params).fetchall())
    if not rows:
        console.print("[dim]No matches found.[/dim]")
        return

    table = Table(show_header=True, header_style="bold", box=box.ROUNDED, expand=True)
    table.add_column("TOOL", style="cyan", width=10)
    table.add_column("PROJECT", style="white", max_width=25)
    table.add_column("TITLE", style="dim", max_width=25)
    table.add_column("MATCH", max_width=45)
    table.add_column("LAST ACTIVE", style="yellow", width=14)
    table.add_column("STATUS", width=12)

    status_icons = {
        "running": "[green]● running[/green]",
        "idle": "[dim]○ idle[/dim]",
        "ended": "[red]✕ ended[/red]",
    }

    for tool_name, project_path, title, last_active_at, status, snippet in rows:
        display_project, _ = classify_project(project_path)
        last_active = pendulum.parse(last_active_at).diff_for_humans()
        status_display = status_icons.get(status, status)
        table.add_row(
            tool_name, display_project, (title or "")[:23],
            snippet.replace("\n", " "), last_active, status_display,
        )

    console.print(table)
