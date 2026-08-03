import time
import subprocess
import platform
import select
import sys
from contextlib import contextmanager
from datetime import datetime, timezone

import typer
from rich import box
from rich.console import Group
from rich.live import Live
from rich.markup import escape
from rich.spinner import Spinner
from rich.table import Table
from rich.text import Text

from hades.commands.archive import archive_session_by_id
from hades.db import get_db
from hades.indexer import refresh_index
from hades.process_checker import update_statuses
from hades.waiting import recent_human_sessions

from hades.console import console

try:
    import termios
    import tty
    SUPPORTS_RAW_INPUT = True
except ImportError:  # Windows has neither module
    SUPPORTS_RAW_INPUT = False

REFRESH_SECONDS = 30
MIN_SPINNER_SECONDS = 0.5
LEGEND = "[dim]j/k move · d archive · Ctrl+C exit[/dim]"


def cmd_watch(
    notify: bool = typer.Option(
        True, "--notify/--no-notify", help="Fire macOS notifications for newly-waiting sessions"
    ),
):
    db = get_db()
    # Pre-seed notified with sessions already past the threshold so startup
    # doesn't fire a notification storm for everything already waiting.
    already_waiting = _fetch_sessions(db)
    notified: set[str] = {s["id"] for s in already_waiting if s["_is_waiting"]}
    cursor = 0

    console.print("[bold]hades watch[/bold] · refreshing every 30s · [dim]Ctrl+C to exit[/dim]\n")

    try:
        with Live(console=console, refresh_per_second=4, screen=False) as live, _cbreak_mode():
            while True:
                live.update(Spinner("dots", text="[dim]checking for sessions...[/dim]"))
                live.refresh()
                check_started = time.monotonic()
                sessions = _fetch_sessions(db, refresh=True)
                elapsed = time.monotonic() - check_started
                if elapsed < MIN_SPINNER_SECONDS:
                    time.sleep(MIN_SPINNER_SECONDS - elapsed)

                for s in sessions:
                    if notify and s["_is_waiting"] and s["id"] not in notified:
                        _send_notification(s)
                    if s["_is_waiting"]:
                        notified.add(s["id"])

                cursor = min(cursor, len(sessions) - 1) if sessions else 0
                footer_spinner = Spinner("dots")
                tick_started = time.monotonic()
                remaining = REFRESH_SECONDS
                while remaining > 0:
                    footer_spinner.update(text=f"[dim]next check in {remaining}s[/dim]")
                    live.update(Group(_render_table(sessions, cursor), footer_spinner, Text.from_markup(LEGEND)))

                    cursor = _handle_key(_read_key(0.1), db, sessions, cursor)

                    if time.monotonic() - tick_started >= 1:
                        tick_started = time.monotonic()
                        remaining -= 1
    except KeyboardInterrupt:
        console.print("\n[dim]Stopped.[/dim]")


def _handle_key(key: str | None, db, sessions: list[dict], cursor: int) -> int:
    if key == "j" and sessions:
        return min(cursor + 1, len(sessions) - 1)
    if key == "k" and sessions:
        return max(cursor - 1, 0)
    if key == "d" and sessions:
        try:
            archive_session_by_id(db, sessions[cursor]["id"])
        except (ValueError, FileNotFoundError):
            return cursor
        sessions.pop(cursor)
        return min(cursor, len(sessions) - 1) if sessions else 0
    return cursor


@contextmanager
def _cbreak_mode():
    """Put stdin in cbreak mode so single keypresses are readable without Enter.

    A no-op when stdin isn't a real terminal (piped input, tests) or the
    platform lacks termios (Windows) — j/k/d nav is simply unavailable then.
    """
    if not SUPPORTS_RAW_INPUT or not sys.stdin.isatty():
        yield
        return
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        yield
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def _read_key(timeout: float) -> str | None:
    if not SUPPORTS_RAW_INPUT or not sys.stdin.isatty():
        time.sleep(timeout)
        return None
    ready, _, _ = select.select([sys.stdin], [], [], timeout)
    return sys.stdin.read(1) if ready else None


def _fetch_sessions(db, refresh: bool = False) -> list[dict]:
    if refresh:
        # The CLI callback only indexes once at startup; a live view must
        # re-scan on every tick or it will never see new activity.
        refresh_index(db)
        update_statuses(db)
    return recent_human_sessions(db, datetime.now(timezone.utc))


def _render_table(sessions: list[dict], cursor: int) -> Table:
    table = Table(
        show_header=True, header_style="bold", box=box.ROUNDED,
        title=f"[dim]{datetime.now(timezone.utc).strftime('%H:%M:%S')}[/dim]",
    )
    table.add_column("TOOL", style="cyan", width=10)
    table.add_column("PROJECT", style="white", max_width=28)
    table.add_column("WAITING", style="bold yellow", width=12)
    table.add_column("TITLE", style="dim", max_width=38)
    table.add_column("STATUS", width=12)

    for idx, s in enumerate(sessions):
        mins = s["_waiting_minutes"]
        project = s["project_path"].split("/")[-1] or s["project_path"]
        wait_str = f"[bold yellow]{mins}m[/bold yellow]" if s["_is_waiting"] else f"[dim]{mins}m[/dim]"
        status = "[green]● running[/green]" if s["status"] == "running" else "[dim]○ idle[/dim]"

        table.add_row(
            escape(s["tool"]), escape(project), wait_str, escape((s["title"] or "")[:36]), status,
            style="reverse" if idx == cursor else None,
        )

    return table


def _send_notification(session: dict) -> None:
    project = session["project_path"].split("/")[-1] or session["project_path"]
    system = platform.system()
    if system == "Darwin":
        title = _osa_quote(f"hades · {session['tool']} waiting")
        message = _osa_quote(f"{project} has been waiting for your input")
        subprocess.run([
            "osascript", "-e",
            f'display notification "{message}" with title "{title}" sound name "default"'
        ], capture_output=True, check=False)
    elif system == "Linux":
        title = f"hades · {session['tool']} waiting"
        message = f"{project} has been waiting for your input"
        try:
            subprocess.run(["notify-send", title, message], capture_output=True, check=False)
        except FileNotFoundError:
            pass


def _osa_quote(text: str) -> str:
    """Escape a string for interpolation inside an AppleScript string literal.

    Session data (project names, tool names) is untrusted — without this, a
    crafted directory name could inject AppleScript (e.g. `do shell script`).
    """
    return text.replace("\\", "\\\\").replace('"', '\\"')
