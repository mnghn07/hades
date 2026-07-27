from hades.pricing import estimate_cost, price_per_mtok


def test_price_per_mtok_matches_known_model():
    assert price_per_mtok("claude-sonnet-5") == (3.00, 15.00)


def test_price_per_mtok_matches_dated_suffix():
    assert price_per_mtok("claude-haiku-4-5-20251001") == (1.00, 5.00)


def test_price_per_mtok_unknown_model_returns_none():
    assert price_per_mtok("claude-nonexistent") is None


def test_estimate_cost_input_output_only():
    # 1M input + 1M output tokens on Sonnet 5 ($3 in, $15 out)
    cost = estimate_cost("claude-sonnet-5", 1_000_000, 1_000_000, 0, 0)
    assert cost == 18.00


def test_estimate_cost_includes_cache_write_and_read():
    # cache write is 1.25x input price, cache read is 0.1x input price
    cost = estimate_cost("claude-sonnet-5", 0, 0, 1_000_000, 1_000_000)
    assert cost == (3.00 * 1.25) + (3.00 * 0.1)


def test_estimate_cost_unknown_model_is_zero():
    assert estimate_cost("claude-nonexistent", 1_000_000, 1_000_000, 0, 0) == 0.0
