import typer
from rich import box
from rich.table import Table

from hades.config import get_enabled_tools, set_tool_enabled
from hades.sources import ALL_SOURCES

from hades.console import console

TOOL_NAMES = [source_cls.name for source_cls in ALL_SOURCES]


def cmd_setup() -> None:
    enabled = get_enabled_tools()

    table = Table(box=box.SIMPLE_HEAD)
    table.add_column("tool")
    table.add_column("detected")
    table.add_column("enabled")

    for source_cls in ALL_SOURCES:
        detected = source_cls.discover_root() is not None
        table.add_row(
            source_cls.name,
            "[green]yes[/green]" if detected else "[dim]no[/dim]",
            "[green]on[/green]" if source_cls.name in enabled else "[dim]off[/dim]",
        )

    console.print(table)
    console.print("\n[dim]Toggle with `hades tools enable <name>` / `hades tools disable <name>`.[/dim]")


def cmd_tools_enable(tool: str) -> None:
    _validate_tool(tool)
    set_tool_enabled(tool, True)
    console.print(f"[green]enabled[/green] {tool}")


def cmd_tools_disable(tool: str) -> None:
    _validate_tool(tool)
    set_tool_enabled(tool, False)
    console.print(f"[yellow]disabled[/yellow] {tool}")


def _validate_tool(tool: str) -> None:
    if tool not in TOOL_NAMES:
        console.print(f"[red]Unknown tool:[/red] {tool} (known: {', '.join(TOOL_NAMES)})")
        raise typer.Exit(1)
