import json

from hades.sources.cowork import _extract_title, _msg_text, _read_metadata


def test_msg_text_extracts_from_content_list():
    content = [{"type": "thinking", "thinking": ""}, {"type": "text", "text": "hi there"}]
    assert _msg_text({"content": content}) == "hi there"


def test_msg_text_handles_plain_string_content():
    assert _msg_text({"content": "plain text"}) == "plain text"


def test_extract_title_skips_turns_with_no_text():
    user_msgs = [
        {"message": {"content": [{"type": "thinking", "thinking": ""}]}},
        {"message": {"content": "real question"}},
    ]
    assert _extract_title(user_msgs) == "real question"


def test_extract_title_returns_none_when_no_text_found():
    assert _extract_title([{"message": {"content": ""}}]) is None


def test_read_metadata_finds_sibling_json(tmp_path):
    session_dir = tmp_path / "local_abc"
    session_dir.mkdir()
    (tmp_path / "local_abc.json").write_text(json.dumps({"title": "hello"}), encoding="utf-8")
    audit_path = session_dir / "audit.jsonl"
    audit_path.write_text("", encoding="utf-8")
    assert _read_metadata(audit_path) == {"title": "hello"}


def test_read_metadata_missing_file_returns_empty_dict(tmp_path):
    session_dir = tmp_path / "local_missing"
    session_dir.mkdir()
    assert _read_metadata(session_dir / "audit.jsonl") == {}
