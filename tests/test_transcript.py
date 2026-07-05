import json
from pathlib import Path

from hades.transcript import iter_raw_messages, parse_turn


def test_iter_raw_messages_reads_jsonl(tmp_path: Path):
    path = tmp_path / "session.jsonl"
    path.write_text(
        json.dumps({"type": "user", "message": {"role": "user", "content": "hi"}}) + "\n"
        + json.dumps({"type": "assistant", "message": {"role": "assistant", "content": "hello"}}) + "\n"
    )
    messages = list(iter_raw_messages(path))
    assert len(messages) == 2
    assert messages[0]["type"] == "user"


def test_iter_raw_messages_reads_json_list(tmp_path: Path):
    path = tmp_path / "session.json"
    path.write_text(json.dumps([
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
    ]))
    assert len(list(iter_raw_messages(path))) == 2


def test_iter_raw_messages_reads_json_with_messages_key(tmp_path: Path):
    path = tmp_path / "session.json"
    path.write_text(json.dumps({"messages": [{"role": "user", "content": "hi"}]}))
    assert len(list(iter_raw_messages(path))) == 1


def test_parse_turn_claude_user_format():
    msg = {"type": "user", "message": {"role": "user", "content": "hi there"}}
    assert parse_turn(msg, full=False) == ("user", "hi there")


def test_parse_turn_claude_assistant_text_blocks():
    msg = {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "hello"}]}}
    assert parse_turn(msg, full=False) == ("assistant", "hello")


def test_parse_turn_simple_role_format_normalizes_model_to_assistant():
    msg = {"role": "model", "parts": "hi from gemini"}
    assert parse_turn(msg, full=False) == ("assistant", "hi from gemini")


def test_parse_turn_thinking_block_hidden_unless_full():
    msg = {"type": "assistant", "message": {"role": "assistant", "content": [
        {"type": "thinking", "thinking": "pondering..."},
    ]}}
    assert parse_turn(msg, full=False) is None

    role, text = parse_turn(msg, full=True)
    assert role == "assistant"
    assert "pondering" in text


def test_parse_turn_tool_result_only_shown_with_full():
    msg = {"type": "tool_result", "name": "Read"}
    assert parse_turn(msg, full=False) is None
    assert parse_turn(msg, full=True) == ("tool", "<TOOL Read>")


def test_parse_turn_returns_none_for_unrecognized_message():
    assert parse_turn({"type": "summary"}, full=False) is None


def test_parse_turn_returns_none_for_blank_content():
    msg = {"type": "user", "message": {"role": "user", "content": "   "}}
    assert parse_turn(msg, full=False) is None
