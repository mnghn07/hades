import shutil
from pathlib import Path

import typer
from platformdirs import user_data_dir
from rich.console import Console

from hades.db import get_db

console = Console()

ARCHIVE_ROOT = Path(user_data_dir("hades")) / "archive"


def cmd_archive(
    session_id: str = typer.Argument(..., help="Session ID (from hades list)"),
):
    db = get_db()
    row = db.execute(
        "SELECT tool, raw_path, is_archived FROM sessions WHERE id = ?", [session_id]
    ).fetchone()
    if not row:
        console.print(f"[red]Session not found:[/red] {session_id}")
        raise typer.Exit(1)

    tool, raw_path_str, is_archived = row
    if is_archived:
        console.print(f"[yellow]Already archived:[/yellow] {session_id}")
        return

    raw_path = Path(raw_path_str)
    if not raw_path.exists():
        console.print(f"[red]Session file no longer exists:[/red] {raw_path}")
        raise typer.Exit(1)

    dest_dir = ARCHIVE_ROOT / tool
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / raw_path.name

    shutil.move(str(raw_path), str(dest_path))

    db.execute(
        "UPDATE sessions SET raw_path = ?, is_archived = 1 WHERE id = ?",
        [str(dest_path), session_id],
    )
    db.conn.commit()

    console.print(f"[green]Archived[/green] {session_id} → {dest_path}")
