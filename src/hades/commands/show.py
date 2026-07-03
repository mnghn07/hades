import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.syntax import Syntax
from rich.panel import Panel

from hades.db import get_db

console = Console()


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

    console.print(Panel(f"[bold]{session['tool']}[/bold] · {session['project_path']} · {session_id}", expand=False))

    if raw_path.suffix == ".jsonl":
        _render_jsonl(raw_path, full)
    else:
        _render_json(raw_path, full)


def _render_jsonl(path: Path, full: bool) -> None:
    import ijson
    with open(path, "rb") as f:
        for item in ijson.items(f, "", multiple_values=True):
            _render_message(item, full)


def _render_json(path: Path, full: bool) -> None:
    with open(path) as f:
        data = json.load(f)
    messages = data if isinstance(data, list) else data.get("messages", [])
    for msg in messages:
        _render_message(msg, full)


def _render_message(msg: dict, full: bool) -> None:
    role = msg.get("type") or msg.get("role", "unknown")
    content = msg.get("content", "")

    if role in ("human", "user"):
        color = "bold blue"
        label = "YOU"
    elif role in ("assistant",):
        color = "bold green"
        label = "AI"
    else:
        if not full:
            return
        color = "dim"
        label = role.upper()

    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    console.print(f"[{color}]{label}[/{color}]  {block['text']}")
                elif block.get("type") == "tool_use" and full:
                    console.print(f"[dim]TOOL {block.get('name', '')}[/dim]")
    elif isinstance(content, str) and content:
        console.print(f"[{color}]{label}[/{color}]  {content}")
