import typer

from hades.config import DEFAULTS, get_config, load_config, set_config

from hades.console import console


def cmd_config_list():
    for key, value in load_config().items():
        console.print(f"{key} = {value}")


def cmd_config_get(key: str):
    try:
        console.print(str(get_config(key)))
    except KeyError:
        console.print(f"[red]Unknown config key:[/red] {key} (known: {', '.join(DEFAULTS)})")
        raise typer.Exit(1)


def cmd_config_set(key: str, value: str):
    try:
        coerced = set_config(key, value)
    except KeyError:
        console.print(f"[red]Unknown config key:[/red] {key} (known: {', '.join(DEFAULTS)})")
        raise typer.Exit(1)
    except ValueError:
        console.print(f"[red]Invalid value for {key}:[/red] {value!r}")
        raise typer.Exit(1)
    console.print(f"[green]{key}[/green] = {coerced}")
