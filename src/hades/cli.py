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
    since: Optional[str] = typer.Option(None, "--since", help="Show sessions active since (e.g. 2d, 1w)"),
):
    from hades.commands.list import cmd_list
    cmd_list(tool=tool, active=active, since=since)


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


@app.command("watch", help="Live view of sessions needing attention (fires macOS notifications by default).")
def watch_cmd(
    notify: bool = typer.Option(
        True, "--notify/--no-notify", help="Fire macOS notifications for newly-waiting sessions"
    ),
):
    from hades.commands.watch import cmd_watch
    cmd_watch(notify=notify)
