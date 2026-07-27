from hades.commands.list import _format_cost, _format_tokens
from hades.sources.claude import _extract_cost, _extract_token_count


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


def test_extract_cost_prices_by_each_turns_own_model():
    assistant_msgs = [
        {"message": {"model": "claude-sonnet-5", "usage": {"input_tokens": 1_000_000, "output_tokens": 0}}},
        {"message": {"model": "claude-haiku-4-5-20251001", "usage": {"input_tokens": 1_000_000, "output_tokens": 0}}},
    ]
    assert _extract_cost(assistant_msgs) == 3.00 + 1.00


def test_extract_cost_ignores_missing_usage():
    assert _extract_cost([{"message": {}}, {"message": {"usage": None}}]) == 0.0


def test_format_cost():
    assert _format_cost(0) == "-"
    assert _format_cost(1.5) == "$1.50"
    assert _format_cost(0.004) == "$0.00"
