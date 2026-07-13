"""Single shared Console so `--no-color` (set in cli.py's main callback) reaches
every command. Rich already auto-disables color when not a tty or when
NO_COLOR is set — this flag is for the tty-but-still-want-plain-text case.
"""
from rich.console import Console

console = Console()
