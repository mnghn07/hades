import time
import subprocess
import platform
from datetime import datetime, timezone, timedelta

import typer
from rich.console import Console
from rich.live import Live
from rich.table import Table

from hades.db import get_db
from hades.commands.attention import WAIT_THRESHOLD_MINUTES, RECENCY_HOURS

console = Console()

REFRESH_SECONDS = 30


def cmd_watch(
    notify: bool = typer.Option(
        True, "--notify/--no-notify", help="Fire macOS notifications for newly-waiting sessions"
    ),
):
    # Pre-seed notified with sessions already past the threshold so startup
    # doesn't fire a notification storm for everything already waiting.
    _, already_waiting = _build_table(set())
    notified: set[str] = {s["id"] for s in already_waiting}

    console.print("[bold]hades watch[/bold] · refreshing every 30s · [dim]Ctrl+C to exit[/dim]\n")

    try:
        with Live(console=console, refresh_per_second=1, screen=False) as live:
            while True:
                table, newly_waiting = _build_table(notified)
                live.update(table)

                if notify:
                    for s in newly_waiting:
                        _send_notification(s)
                        notified.add(s["id"])

                time.sleep(REFRESH_SECONDS)
    except KeyboardInterrupt:
        console.print("\n[dim]Stopped.[/dim]")


def _build_table(notified: set[str]) -> tuple[Table, list[dict]]:
    db = get_db()
    now = datetime.now(timezone.utc)

    table = Table(
        show_header=True, header_style="bold", box=None, pad_edge=False,
        title=f"[dim]{now.strftime('%H:%M:%S')}[/dim]",
    )
    table.add_column("TOOL", style="cyan", width=10)
    table.add_column("PROJECT", style="white", max_width=28)
    table.add_column("WAITING", style="bold yellow", width=12)
    table.add_column("TITLE", style="dim", max_width=38)
    table.add_column("STATUS", width=12)

    if "sessions" not in db.table_names():
        return table, []

    recency_cutoff = (now - timedelta(hours=RECENCY_HOURS)).isoformat()
    sessions = list(db.execute(
        "SELECT * FROM sessions WHERE status IN ('running', 'idle') "
        "AND last_active_at >= ? ORDER BY last_active_at ASC",
        [recency_cutoff]
    ).fetchall())
    col_names = [d[0] for d in db.execute("SELECT * FROM sessions LIMIT 0").description]

    newly_waiting = []
    for row in sessions:
        s = dict(zip(col_names, row))
        last_active = datetime.fromisoformat(s["last_active_at"])
        if last_active.tzinfo is None:
            last_active = last_active.replace(tzinfo=timezone.utc)

        waiting_since = now - last_active
        mins = int(waiting_since.total_seconds() / 60)
        is_waiting = mins >= WAIT_THRESHOLD_MINUTES
        project = s["project_path"].split("/")[-1] or s["project_path"]
        wait_str = f"[bold yellow]{mins}m[/bold yellow]" if is_waiting else f"[dim]{mins}m[/dim]"
        status = "[green]● running[/green]" if s["status"] == "running" else "[dim]○ idle[/dim]"

        table.add_row(s["tool"], project, wait_str, (s["title"] or "")[:36], status)

        if is_waiting and s["id"] not in notified:
            newly_waiting.append(s)

    return table, newly_waiting


def _send_notification(session: dict) -> None:
    if platform.system() != "Darwin":
        return
    project = session["project_path"].split("/")[-1] or session["project_path"]
    title = f"hades · {session['tool']} waiting"
    message = f"{project} has been waiting for your input"
    subprocess.run([
        "osascript", "-e",
        f'display notification "{message}" with title "{title}" sound name "default"'
    ], capture_output=True, check=False)
