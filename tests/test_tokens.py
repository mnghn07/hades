from hades.commands.list import _format_tokens
from hades.sources.claude import _extract_token_count


def test_extract_token_count_sums_usage_across_turns():
    assistant_msgs = [
        {"message": {"usage": {"input_tokens": 10, "output_tokens": 20}}},
        {"message": {"usage": {
            "input_tokens": 5, "output_tokens": 15,
            "cache_creation_input_tokens": 100, "cache_read_input_tokens": 50,
        }}},
    ]
    assert _extract_token_count(assistant_msgs) == (10 + 20) + (5 + 15 + 100 + 50)


def test_extract_token_count_ignores_missing_usage():
    assert _extract_token_count([{"message": {}}, {"message": {"usage": None}}]) == 0


def test_format_tokens():
    assert _format_tokens(0) == "-"
    assert _format_tokens(500) == "500"
    assert _format_tokens(1500) == "1.5k"
    assert _format_tokens(2_500_000) == "2.5M"
