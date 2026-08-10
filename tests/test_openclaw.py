import json

from hades.sources.openclaw import OpenclawSource, _extract_cost, _extract_title, _extract_token_count, _msg_text


def test_msg_text_extracts_from_content_list():
    content = [{"type": "text", "text": "hi there"}]
    assert _msg_text({"content": content}) == "hi there"


def test_msg_text_handles_plain_string_content():
    assert _msg_text({"content": "plain text"}) == "plain text"


def test_extract_title_returns_none_when_no_user_msgs():
    assert _extract_title([]) is None


def test_extract_token_count_sums_usage_components():
    assistant_msgs = [
        {"message": {"usage": {"input": 2, "output": 3, "cacheRead": 100, "cacheWrite": 5}}},
        {"message": {"usage": {"input": 1, "output": 1}}},
    ]
    assert _extract_token_count(assistant_msgs) == (2 + 3 + 100 + 5) + (1 + 1)


def test_extract_cost_ignores_unreliable_embedded_zero_and_prices_from_model():
    assistant_msgs = [
        {
            "message": {
                "model": "claude-opus-4-8",
                "usage": {"input": 1_000_000, "output": 0, "cost": {"total": 0}},
            }
        }
    ]
    assert _extract_cost(assistant_msgs) == 5.00


def _write_session(tmp_path, records):
    session_dir = tmp_path / "main" / "sessions"
    session_dir.mkdir(parents=True)
    path = session_dir / "abc123.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in records), encoding="utf-8")
    return path


def test_parse_file_end_to_end(tmp_path):
    path = _write_session(
        tmp_path,
        [
            {"type": "session", "id": "abc123", "timestamp": "2026-08-05T08:26:10.143Z", "cwd": "/proj"},
            {
                "type": "message",
                "timestamp": "2026-08-05T08:26:10.143Z",
                "message": {"role": "user", "content": "hello there"},
            },
            {
                "type": "message",
                "timestamp": "2026-08-05T08:26:48.135Z",
                "message": {
                    "role": "assistant",
                    "content": [{"type": "text", "text": "hi"}],
                    "model": "claude-opus-4-8",
                    "usage": {"input": 10, "output": 10, "cacheRead": 0, "cacheWrite": 0},
                },
            },
        ],
    )
    session = OpenclawSource.parse_file(path)
    assert session is not None
    assert session.tool == "openclaw"
    assert session.project_path == "/proj"
    assert session.message_count == 2
    assert session.title == "hello there"
    assert session.token_count == 20
    assert session.cost_usd > 0


def test_list_files_finds_session_jsonl(tmp_path):
    _write_session(tmp_path, [{"type": "session", "id": "abc123", "timestamp": "t", "cwd": "/proj"}])
    import os

    os.environ["HADES_OPENCLAW_PATH"] = str(tmp_path)
    try:
        files = OpenclawSource.list_files()
    finally:
        del os.environ["HADES_OPENCLAW_PATH"]
    assert len(files) == 1
    assert files[0].name == "abc123.jsonl"
