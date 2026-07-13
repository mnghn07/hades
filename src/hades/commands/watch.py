import time
import subprocess
import platform
from datetime import datetime, timezone

import typer
from rich import box
from rich.console import Group
from rich.live import Live
from rich.markup import escape
from rich.spinner import Spinner
from rich.table import Table

from hades.db import get_db
from hades.indexer import refresh_index
from hades.process_checker import update_statuses
from hades.waiting import recent_human_sessions

from hades.console import console

REFRESH_SECONDS = 30
MIN_SPINNER_SECONDS = 0.5


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
        with Live(console=console, refresh_per_second=4, screen=False) as live:
            while True:
                live.update(Spinner("dots", text="[dim]checking for sessions...[/dim]"))
                live.refresh()
                check_started = time.monotonic()
                table, newly_waiting = _build_table(notified, refresh=True)
                elapsed = time.monotonic() - check_started
                if elapsed < MIN_SPINNER_SECONDS:
                    time.sleep(MIN_SPINNER_SECONDS - elapsed)

                if notify:
                    for s in newly_waiting:
                        _send_notification(s)
                        notified.add(s["id"])

                footer_spinner = Spinner("dots")
                for remaining in range(REFRESH_SECONDS, 0, -1):
                    footer_spinner.update(text=f"[dim]next check in {remaining}s[/dim]")
                    live.update(Group(table, footer_spinner))
                    time.sleep(1)
    except KeyboardInterrupt:
        console.print("\n[dim]Stopped.[/dim]")


def _build_table(notified: set[str], refresh: bool = False) -> tuple[Table, list[dict]]:
    db = get_db()
    if refresh:
        # The CLI callback only indexes once at startup; a live view must
        # re-scan on every tick or it will never see new activity.
        refresh_index(db)
        update_statuses(db)
    now = datetime.now(timezone.utc)

    table = Table(
        show_header=True, header_style="bold", box=box.ROUNDED,
        title=f"[dim]{now.strftime('%H:%M:%S')}[/dim]",
    )
    table.add_column("TOOL", style="cyan", width=10)
    table.add_column("PROJECT", style="white", max_width=28)
    table.add_column("WAITING", style="bold yellow", width=12)
    table.add_column("TITLE", style="dim", max_width=38)
    table.add_column("STATUS", width=12)

    newly_waiting = []
    for s in recent_human_sessions(db, now):
        mins = s["_waiting_minutes"]
        project = s["project_path"].split("/")[-1] or s["project_path"]
        wait_str = f"[bold yellow]{mins}m[/bold yellow]" if s["_is_waiting"] else f"[dim]{mins}m[/dim]"
        status = "[green]● running[/green]" if s["status"] == "running" else "[dim]○ idle[/dim]"

        table.add_row(escape(s["tool"]), escape(project), wait_str, escape((s["title"] or "")[:36]), status)

        if s["_is_waiting"] and s["id"] not in notified:
            newly_waiting.append(s)

    return table, newly_waiting


def _send_notification(session: dict) -> None:
    if platform.system() != "Darwin":
        return
    project = session["project_path"].split("/")[-1] or session["project_path"]
    title = _osa_quote(f"hades · {session['tool']} waiting")
    message = _osa_quote(f"{project} has been waiting for your input")
    subprocess.run([
        "osascript", "-e",
        f'display notification "{message}" with title "{title}" sound name "default"'
    ], capture_output=True, check=False)


def _osa_quote(text: str) -> str:
    """Escape a string for interpolation inside an AppleScript string literal.

    Session data (project names, tool names) is untrusted — without this, a
    crafted directory name could inject AppleScript (e.g. `do shell script`).
    """
    return text.replace("\\", "\\\\").replace('"', '\\"')
