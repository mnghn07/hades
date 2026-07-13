import json
from pathlib import Path
from typing import Optional

import typer

from hades.db import get_db
from hades.transcript import iter_raw_messages, parse_turn

from hades.console import console

ROLE_LABELS = {"user": "YOU", "assistant": "AI", "tool": "TOOL"}


def cmd_export(
    session_id: str = typer.Argument(..., help="Session ID (from hades list)"),
    export_format: str = typer.Option("json", "--format", "-f", help="Output format: json or markdown"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file path"),
    full: bool = typer.Option(False, "--full", help="Include tool calls and thinking blocks"),
):
    if export_format not in ("json", "markdown"):
        console.print(f"[red]Unknown format:[/red] {export_format} (expected json or markdown)")
        raise typer.Exit(1)

    db = get_db()
    row = db.execute(
        "SELECT tool, project_path, title, raw_path FROM sessions WHERE id = ?", [session_id]
    ).fetchone()
    if not row:
        console.print(f"[red]Session not found:[/red] {session_id}")
        raise typer.Exit(1)

    tool, project_path, title, raw_path_str = row
    raw_path = Path(raw_path_str)
    if not raw_path.exists():
        console.print(f"[red]Session file no longer exists:[/red] {raw_path}")
        raise typer.Exit(1)

    turns = [t for msg in iter_raw_messages(raw_path) if (t := parse_turn(msg, full)) is not None]

    ext = "json" if export_format == "json" else "md"
    dest = output or Path(f"{session_id}.{ext}")

    if export_format == "json":
        payload = {
            "id": session_id,
            "tool": tool,
            "project_path": project_path,
            "title": title,
            "messages": [{"role": role, "text": text} for role, text in turns],
        }
        dest.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    else:
        lines = [f"# {title or session_id}", "", f"**{tool}** · {project_path} · `{session_id}`", ""]
        for role, text in turns:
            lines.append(f"## {ROLE_LABELS.get(role, role)}")
            lines.append("")
            lines.append(text)
            lines.append("")
        dest.write_text("\n".join(lines), encoding="utf-8")

    console.print(f"[green]Exported[/green] {session_id} → {dest}")
