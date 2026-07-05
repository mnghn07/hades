from typing import Optional
import typer
from hades import __version__

app = typer.Typer(
    name="hades",
    help="View, search, and manage AI coding sessions across Claude, Codex, Gemini, and Cowork.",
    no_args_is_help=True,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"hades {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    _version: Optional[bool] = typer.Option(
        None, "--version", "-v", callback=_version_callback, is_eager=True, help="Show version and exit"
    ),
):
    from hades.db import get_db
    from hades.indexer import refresh_index
    from hades.process_checker import update_statuses
    db = get_db()
    refresh_index(db)
    update_statuses(db)


@app.command("list", help="List sessions across all tools.")
def list_cmd(
    tool: Optional[str] = typer.Option(None, "--tool", "-t", help="Filter by tool: claude, codex, gemini, cowork"),
    active: bool = typer.Option(False, "--active", help="Show only running/idle sessions"),
    day: int = typer.Option(0, "--day", help="Show sessions active within the last N days"),
    hour: int = typer.Option(0, "--hour", help="Show sessions active within the last N hours"),
    minute: int = typer.Option(0, "--min", help="Show sessions active within the last N minutes"),
    show_all: bool = typer.Option(False, "--all", help="Show every session, ignoring recency"),
    show_archived: bool = typer.Option(False, "--show-archived", help="Include archived sessions"),
):
    from hades.commands.list import cmd_list
    cmd_list(
        tool=tool, active=active, day=day, hour=hour, minute=minute,
        show_all=show_all, show_archived=show_archived,
    )


@app.command("show", help="Pretty-print a session transcript.")
def show_cmd(
    session_id: str = typer.Argument(..., help="Session ID (from hades list)"),
    full: bool = typer.Option(False, "--full", help="Expand tool calls"),
):
    from hades.commands.show import cmd_show
    cmd_show(session_id=session_id, full=full)


@app.command("attention", help="Surface sessions waiting on you.")
def attention_cmd():
    from hades.commands.attention import cmd_attention
    cmd_attention()


@app.command("stats", help="Summary stats across all sessions.")
def stats_cmd(
    day: int = typer.Option(0, "--day", help="Only include sessions active within the last N days"),
    hour: int = typer.Option(0, "--hour", help="Only include sessions active within the last N hours"),
    minute: int = typer.Option(0, "--min", help="Only include sessions active within the last N minutes"),
):
    from hades.commands.stats import cmd_stats
    cmd_stats(day=day, hour=hour, minute=minute)


@app.command("search", help="Full-text search across session transcripts.")
def search_cmd(
    query: str = typer.Argument(..., help="Full-text search query"),
    tool: Optional[str] = typer.Option(None, "--tool", "-t", help="Filter by tool: claude, codex, gemini, cowork"),
    limit: int = typer.Option(20, "--limit", "-n", help="Max results to show"),
    show_archived: bool = typer.Option(False, "--show-archived", help="Include archived sessions"),
):
    from hades.commands.search import cmd_search
    cmd_search(query=query, tool=tool, limit=limit, show_archived=show_archived)


@app.command("export", help="Export a session transcript to json or markdown.")
def export_cmd(
    session_id: str = typer.Argument(..., help="Session ID (from hades list)"),
    export_format: str = typer.Option("json", "--format", "-f", help="Output format: json or markdown"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path"),
    full: bool = typer.Option(False, "--full", help="Include tool calls and thinking blocks"),
):
    from pathlib import Path
    from hades.commands.export import cmd_export
    cmd_export(
        session_id=session_id, export_format=export_format,
        output=Path(output) if output else None, full=full,
    )


@app.command("archive", help="Move a session's transcript to the archive and hide it from list/search.")
def archive_cmd(
    session_id: str = typer.Argument(..., help="Session ID (from hades list)"),
):
    from hades.commands.archive import cmd_archive
    cmd_archive(session_id=session_id)


@app.command("purge", help="Permanently delete a session's transcript and index entry.")
def purge_cmd(
    session_id: str = typer.Argument(..., help="Session ID (from hades list)"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
):
    from hades.commands.purge import cmd_purge
    cmd_purge(session_id=session_id, yes=yes)


@app.command("watch", help="Live view of sessions needing attention (fires macOS notifications by default).")
def watch_cmd(
    notify: bool = typer.Option(
        True, "--notify/--no-notify", help="Fire macOS notifications for newly-waiting sessions"
    ),
):
    from hades.commands.watch import cmd_watch
    cmd_watch(notify=notify)
