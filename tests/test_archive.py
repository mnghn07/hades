from pathlib import Path

import pytest

from hades.commands.archive import archive_session_by_id
from hades.db import get_db


@pytest.fixture
def archived_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    dest = tmp_path / "archive"
    monkeypatch.setattr("hades.commands.archive.ARCHIVE_ROOT", dest)
    return dest


@pytest.mark.usefixtures("db_path")
def test_archive_unknown_session_raises_value_error():
    db = get_db()
    with pytest.raises(ValueError):
        archive_session_by_id(db, "nope")


@pytest.mark.usefixtures("db_path", "archived_dir")
def test_archive_moves_file_and_marks_row(tmp_path: Path):
    db = get_db()
    session_file = tmp_path / "sess.jsonl"
    session_file.write_text("{}")
    db["sessions"].insert({  # pylint: disable=no-member  # sqlite_utils stubs return Table | View
        "id": "claude:sess", "tool": "claude", "raw_path": str(session_file), "is_archived": 0,
    }, pk="id")

    dest_path, already_archived = archive_session_by_id(db, "claude:sess")

    assert not already_archived
    assert dest_path.exists()
    assert not session_file.exists()
    row = db["sessions"].get("claude:sess")  # pylint: disable=no-member  # sqlite_utils stubs return Table | View
    assert row["is_archived"] == 1
    assert row["raw_path"] == str(dest_path)


@pytest.mark.usefixtures("db_path", "archived_dir")
def test_archive_already_archived_is_a_noop(tmp_path: Path):
    db = get_db()
    dest_file = tmp_path / "already.jsonl"
    dest_file.write_text("{}")
    db["sessions"].insert({  # pylint: disable=no-member  # sqlite_utils stubs return Table | View
        "id": "claude:sess", "tool": "claude", "raw_path": str(dest_file), "is_archived": 1,
    }, pk="id")

    dest_path, already_archived = archive_session_by_id(db, "claude:sess")

    assert already_archived
    assert dest_path == dest_file


@pytest.mark.usefixtures("db_path", "archived_dir")
def test_archive_missing_source_file_raises(tmp_path: Path):
    db = get_db()
    missing = tmp_path / "gone.jsonl"
    db["sessions"].insert({  # pylint: disable=no-member  # sqlite_utils stubs return Table | View
        "id": "claude:sess", "tool": "claude", "raw_path": str(missing), "is_archived": 0,
    }, pk="id")

    with pytest.raises(FileNotFoundError):
        archive_session_by_id(db, "claude:sess")
