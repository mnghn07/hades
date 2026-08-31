from hades.db import get_db
from hades.indexer import force_reindex

from hades.console import console


def cmd_reindex(tool: str | None, session_id: str | None) -> None:
    db = get_db()
    count = force_reindex(db, tool=tool, session_id=session_id)
    console.print(f"[green]Reindexed[/green] {count} session(s)")
