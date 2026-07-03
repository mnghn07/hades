import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
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

    console.print(Panel(
        f"[bold]{session['tool']}[/bold] · {session['project_path']} · {session_id}",
        expand=False
    ))

    if raw_path.suffix == ".jsonl":
        _render_jsonl(raw_path, full)
    else:
        _render_json(raw_path, full)


def _render_jsonl(path: Path, full: bool) -> None:
    import ijson
    rendered = 0
    with open(path, "rb") as f:
        for item in ijson.items(f, "", multiple_values=True):
            if isinstance(item, dict) and _render_message(item, full):
                rendered += 1
    if rendered == 0:
        console.print("[dim]No displayable messages found.[/dim]")


def _render_json(path: Path, full: bool) -> None:
    with open(path) as f:
        data = json.load(f)
    messages = data if isinstance(data, list) else data.get("messages", [])
    rendered = 0
    for msg in messages:
        if _render_message(msg, full):
            rendered += 1
    if rendered == 0:
        console.print("[dim]No displayable messages found.[/dim]")


def _render_message(msg: dict, full: bool) -> bool:
    """Render one message entry. Returns True if something was printed."""
    outer_type = msg.get("type", "")

    # Claude Code format: outer type="user"/"assistant" with message.role inside
    if outer_type in ("user", "assistant") and "message" in msg:
        inner = msg["message"]
        role = inner.get("role", outer_type)
        content = inner.get("content", "")
        return _print_turn(role, content, full)

    # Simpler formats (Codex, Gemini, Cowork): role at top level
    role = msg.get("role", "")
    if role in ("user", "assistant", "model"):
        content = msg.get("content") or msg.get("parts", "")
        return _print_turn("user" if role == "user" else "assistant", content, full)

    # Tool call results (show only with --full)
    if full and outer_type in ("tool_result", "tool_use"):
        console.print(f"[dim]── TOOL {msg.get('name', outer_type)} ──[/dim]")
        return True

    return False


def _print_turn(role: str, content, full: bool) -> bool:
    if role == "user":
        color = "bold blue"
        label = "YOU"
    elif role in ("assistant", "model"):
        color = "bold green"
        label = " AI"
    else:
        return False

    text = _extract_text(content, full)
    if not text:
        return False

    console.print(f"[{color}]{label}[/{color}]  {text}")
    return True


def _extract_text(content, full: bool) -> str:
    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        parts = []
        for block in content:
            if not isinstance(block, dict):
                continue
            btype = block.get("type", "")
            if btype == "text":
                text = block.get("text", "").strip()
                if text:
                    parts.append(text)
            elif btype == "thinking" and full:
                thinking = block.get("thinking", "").strip()
                if thinking:
                    parts.append(f"[dim italic]<thinking> {thinking[:200]}…[/dim italic]")
            elif btype == "tool_use" and full:
                parts.append(f"[dim]<tool: {block.get('name', '?')}>[/dim]")
            # Parts format (Gemini)
            elif "text" in block:
                parts.append(block["text"].strip())
        return "\n".join(parts)

    return ""
