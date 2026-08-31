from hades.sources.codex import (
    CodexSource, _extract_cost, _extract_title, _extract_token_breakdown, _extract_token_count, _turn_role,
)


def test_turn_role_excludes_developer_role():
    developer = {"type": "response_item", "payload": {"type": "message", "role": "developer", "content": []}}
    user = {"type": "response_item", "payload": {"type": "message", "role": "user", "content": []}}
    assert _turn_role(developer) is None
    assert _turn_role(user) == "user"


def test_turn_role_ignores_non_message_response_items():
    reasoning = {"type": "response_item", "payload": {"type": "reasoning"}}
    assert _turn_role(reasoning) is None


def test_extract_title_skips_injected_xml_content():
    turns = [
        {"type": "response_item", "payload": {"type": "message", "role": "user",
                                               "content": [{"type": "input_text", "text": "<plugins>boilerplate"}]}},
        {"type": "response_item", "payload": {"type": "message", "role": "user",
                                               "content": [{"type": "input_text", "text": "real question"}]}},
    ]
    assert _extract_title(turns) == "real question"


def test_extract_token_count_uses_last_cumulative_event_not_a_sum():
    records = [
        {"type": "event_msg", "payload": {"type": "token_count",
                                           "info": {"total_token_usage": {"total_tokens": 100}}}},
        {"type": "event_msg", "payload": {"type": "token_count",
                                           "info": {"total_token_usage": {"total_tokens": 250}}}},
    ]
    assert _extract_token_count(records) == 250


def test_extract_token_count_no_events_returns_zero():
    assert _extract_token_count([]) == 0


def test_extract_token_breakdown_uses_last_cumulative_event():
    records = [
        {"type": "event_msg", "payload": {"type": "token_count", "info": {"total_token_usage": {
            "input_tokens": 100, "output_tokens": 50, "cache_write_input_tokens": 10, "cached_input_tokens": 5,
        }}}},
    ]
    assert _extract_token_breakdown(records) == {"input": 100, "output": 50, "cache_write": 10, "cache_read": 5}


def test_extract_token_breakdown_no_events_returns_zeros():
    assert _extract_token_breakdown([]) == {"input": 0, "output": 0, "cache_write": 0, "cache_read": 0}


def test_extract_cost_unrecognized_openai_model_is_zero():
    records = [
        {"type": "world_state", "payload": {"state": {"collaboration_mode": {"model": "gpt-5.6-terra"}}}},
        {"type": "event_msg", "payload": {
            "type": "token_count",
            "info": {"total_token_usage": {"input_tokens": 1000, "output_tokens": 100}},
        }},
    ]
    assert _extract_cost(records) == 0.0


def test_parse_file_end_to_end(tmp_path):
    import json

    path = tmp_path / "rollout-x.jsonl"
    records = [
        {"timestamp": "2026-08-09T13:00:00Z", "type": "session_meta", "payload": {"cwd": "/proj"}},
        {"timestamp": "2026-08-09T13:00:01Z", "type": "response_item",
         "payload": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "hello"}]}},
        {"timestamp": "2026-08-09T13:00:02Z", "type": "response_item",
         "payload": {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "hi"}]}},
        {"timestamp": "2026-08-09T13:00:03Z", "type": "event_msg",
         "payload": {"type": "token_count", "info": {"total_token_usage": {
             "total_tokens": 42, "input_tokens": 30, "output_tokens": 10,
             "cache_write_input_tokens": 1, "cached_input_tokens": 1,
         }}}},
    ]
    path.write_text("\n".join(json.dumps(r) for r in records), encoding="utf-8")

    session = CodexSource.parse_file(path)
    assert session is not None
    assert session.project_path == "/proj"
    assert session.message_count == 2
    assert session.title == "hello"
    assert session.token_count == 42
    assert session.input_tokens == 30
    assert session.output_tokens == 10
    assert session.cache_write_tokens == 1
    assert session.cache_read_tokens == 1
