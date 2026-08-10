import json

from hades.sources.antigravity import AntigravitySource, _strip_file_uri, history_entries_for


def test_strip_file_uri_removes_prefix():
    assert _strip_file_uri("file:///Users/me/project") == "/Users/me/project"


def test_strip_file_uri_passes_through_non_uri():
    assert _strip_file_uri("/already/a/path") == "/already/a/path"


def test_strip_file_uri_handles_none():
    assert _strip_file_uri(None) is None


def _write_conversation(tmp_path, conversation_id, history_lines, metadata=None):
    root = tmp_path
    (root / "conversations").mkdir(parents=True, exist_ok=True)
    db_path = root / "conversations" / f"{conversation_id}.db"
    db_path.write_bytes(b"sqlite-placeholder")

    history_path = root / "history.jsonl"
    with open(history_path, "w", encoding="utf-8") as f:
        for line in history_lines:
            f.write(json.dumps(line) + "\n")

    if metadata is not None:
        (root / "cache").mkdir(parents=True, exist_ok=True)
        (root / "cache" / "conversation_metadata.json").write_text(json.dumps(metadata), encoding="utf-8")

    return db_path


def test_history_entries_for_filters_by_conversation_id(tmp_path):
    db_path = _write_conversation(
        tmp_path,
        "conv-a",
        [
            {"display": "unrelated prompt", "timestamp": 1000, "conversationId": "conv-b"},
            {"display": "hello", "timestamp": 2000, "conversationId": "conv-a", "workspace": "/proj"},
            {"display": "follow up", "timestamp": 3000, "conversationId": "conv-a", "workspace": "/proj"},
        ],
    )
    entries = history_entries_for(db_path)
    assert [e["display"] for e in entries] == ["hello", "follow up"]


def test_parse_file_uses_history_for_title_and_project_path(tmp_path):
    db_path = _write_conversation(
        tmp_path,
        "conv-a",
        [{"display": "hello there", "timestamp": 1786280132725, "conversationId": "conv-a", "workspace": "/proj"}],
    )
    session = AntigravitySource.parse_file(db_path)
    assert session is not None
    assert session.tool == "antigravity"
    assert session.title == "hello there"
    assert session.project_path == "/proj"
    assert session.message_count == 1


def test_parse_file_falls_back_to_metadata_when_no_history(tmp_path):
    db_path = _write_conversation(
        tmp_path,
        "conv-a",
        [],
        metadata={
            "conversations": {
                "conv-a": {"summary": {"Title": "", "Preview": "Some preview",
                                        "WorkspaceURIs": ["file:///Users/me/proj"]}}
            }
        },
    )
    session = AntigravitySource.parse_file(db_path)
    assert session is not None
    assert session.title == "Some preview"
    assert session.project_path == "/Users/me/proj"
    assert session.message_count == 0


def test_extract_messages_has_no_assistant_text(tmp_path):
    db_path = _write_conversation(
        tmp_path,
        "conv-a",
        [{"display": "hello", "timestamp": 1000, "conversationId": "conv-a"}],
    )
    human, assistant = AntigravitySource.extract_messages(db_path)
    assert human == "hello"
    assert assistant == ""


def test_list_files_finds_conversation_dbs(tmp_path):
    _write_conversation(tmp_path, "conv-a", [])
    import os

    os.environ["HADES_ANTIGRAVITY_PATH"] = str(tmp_path)
    try:
        files = AntigravitySource.list_files()
    finally:
        del os.environ["HADES_ANTIGRAVITY_PATH"]
    assert len(files) == 1
    assert files[0].name == "conv-a.db"
