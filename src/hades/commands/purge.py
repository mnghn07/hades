from pathlib import Path

import typer
from rich.console import Console

from hades.db import get_db

console = Console()


def cmd_purge(
    session_id: str = typer.Argument(..., help="Session ID (from hades list)"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
):
    db = get_db()
    row = db.execute("SELECT raw_path FROM sessions WHERE id = ?", [session_id]).fetchone()
    if not row:
        console.print(f"[red]Session not found:[/red] {session_id}")
        raise typer.Exit(1)

    raw_path = Path(row[0])

    if not yes:
        confirmed = typer.confirm(
            f"Permanently delete session {session_id} and its transcript at {raw_path}?",
            default=False,
        )
        if not confirmed:
            console.print("[dim]Aborted.[/dim]")
            raise typer.Exit(0)

    if raw_path.exists():
        raw_path.unlink()

    db.execute("DELETE FROM sessions WHERE id = ?", [session_id])
    db.execute("DELETE FROM sessions_fts WHERE id = ?", [session_id])
    db.conn.commit()

    console.print(f"[green]Purged[/green] {session_id}")
