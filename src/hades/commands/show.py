from pathlib import Path

import typer
from rich.markup import escape
from rich.panel import Panel

from hades.db import get_db
from hades.transcript import iter_raw_messages, parse_turn

from hades.console import console


def cmd_show(
    session_id: str = typer.Argument(..., help="Session ID (from hades list)"),
    full: bool = typer.Option(False, "--full", help="Expand tool calls (collapsed by default)"),
):
    db = get_db()
    row = db.execute("SELECT * FROM sessions WHERE id = ?", [session_id]).fetchone()
    if not row:
        console.print(f"[red]Session not found:[/red] {session_id}")
        raise typer.Exit(1)

    col_names = [d[0] for d in db.execute("SELECT * FROM sessions WHERE id = ?", [session_id]).description]
    session = dict(zip(col_names, row))
    raw_path = Path(session["raw_path"])

    if not raw_path.exists():
        console.print(f"[red]Session file no longer exists:[/red] {raw_path}")
        raise typer.Exit(1)

    console.print(Panel(
        f"[bold]{escape(session['tool'])}[/bold] · {escape(session['project_path'])} · {escape(session_id)}",
        expand=False
    ))

    _render(raw_path, full)


def _render(path: Path, full: bool) -> None:
    rendered = 0
    for msg in iter_raw_messages(path):
        turn = parse_turn(msg, full)
        if turn is None:
            continue
        _print_turn(*turn)
        rendered += 1
    if rendered == 0:
        console.print("[dim]No displayable messages found.[/dim]")


def _print_turn(role: str, text: str) -> None:
    if role == "user":
        console.print(f"[bold blue]YOU[/bold blue]  {escape(text)}")
    elif role == "tool":
        console.print(f"[dim]── {escape(text.strip('<>'))} ──[/dim]")
    else:
        console.print(f"[bold green] AI[/bold green]  {escape(text)}")
