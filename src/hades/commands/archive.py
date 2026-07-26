import shutil
from pathlib import Path

import typer
from platformdirs import user_data_dir

from hades.db import get_db

from hades.console import console

ARCHIVE_ROOT = Path(user_data_dir("hades")) / "archive"


def archive_session_by_id(db, session_id: str) -> tuple[Path, bool]:
    """Move a session's file into the archive and mark it archived in the DB.

    Returns (dest_path, already_archived). Raises ValueError if the session id
    is unknown, FileNotFoundError if its source file is already gone.
    """
    row = db.execute(
        "SELECT tool, raw_path, is_archived FROM sessions WHERE id = ?", [session_id]
    ).fetchone()
    if not row:
        raise ValueError(session_id)

    tool, raw_path_str, is_archived = row
    if is_archived:
        return Path(raw_path_str), True

    raw_path = Path(raw_path_str)
    if not raw_path.exists():
        raise FileNotFoundError(raw_path)

    dest_dir = ARCHIVE_ROOT / tool
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = _unique_dest(dest_dir, raw_path.name)

    shutil.move(str(raw_path), str(dest_path))

    db.execute(
        "UPDATE sessions SET raw_path = ?, is_archived = 1 WHERE id = ?",
        [str(dest_path), session_id],
    )
    db.conn.commit()

    return dest_path, False


def cmd_archive(
    session_id: str = typer.Argument(..., help="Session ID (from hades list)"),
):
    db = get_db()
    try:
        dest_path, already_archived = archive_session_by_id(db, session_id)
    except ValueError:
        console.print(f"[red]Session not found:[/red] {session_id}")
        raise typer.Exit(1)
    except FileNotFoundError as e:
        console.print(f"[red]Session file no longer exists:[/red] {e}")
        raise typer.Exit(1)

    if already_archived:
        console.print(f"[yellow]Already archived:[/yellow] {session_id}")
        return

    console.print(f"[green]Archived[/green] {session_id} → {dest_path}")


def _unique_dest(dest_dir: Path, name: str) -> Path:
    """Never overwrite an existing archived file — suffix a counter instead.

    Same-named session files from different projects (e.g. Gemini's
    chats/session-1.json) would otherwise clobber each other.
    """
    dest = dest_dir / name
    if not dest.exists():
        return dest
    stem, suffix = dest.stem, dest.suffix
    counter = 1
    while (dest := dest_dir / f"{stem}.{counter}{suffix}").exists():
        counter += 1
    return dest
