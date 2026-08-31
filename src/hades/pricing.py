"""USD pricing for Claude models, $/1M tokens (Anthropic API rates, cached 2026-06-24).

Matched by prefix so dated/suffixed model strings (e.g. "claude-haiku-4-5-20251001")
still resolve. Cache write/read aren't in the public per-model table — Anthropic
publishes them as multipliers of the input price (1.25x write, 0.1x read), so we
derive them instead of hardcoding a second table.
# ponytail: Sonnet 5's 2026-08-31 introductory discount isn't modeled — flat
# standard rate only. Unrecognized models price at $0. Add a rate lookup from the
# live Models API if this ever needs to be exact.
"""

# (input $/1M, output $/1M) — most specific prefix wins, so order longer/newer first.
_PRICES: dict[str, tuple[float, float]] = {
    "claude-fable-5": (10.00, 50.00),
    "claude-mythos-5": (10.00, 50.00),
    "claude-opus-5": (5.00, 25.00),
    "claude-opus-4-8": (5.00, 25.00),
    "claude-opus-4-7": (5.00, 25.00),
    "claude-opus-4-6": (5.00, 25.00),
    "claude-sonnet-5": (3.00, 15.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-sonnet-4-5": (3.00, 15.00),
    "claude-haiku-4-5": (1.00, 5.00),
}

CACHE_WRITE_MULTIPLIER = 1.25
CACHE_READ_MULTIPLIER = 0.1
OUTPUT_MULTIPLIER = 5.0  # every priced model above uses a flat 5x input:output ratio


def category_cost_shares(
    input_tokens: int, output_tokens: int, cache_write_tokens: int, cache_read_tokens: int, total_cost_usd: float
) -> dict[str, float]:
    """Split an already-known total cost across the four token categories.

    Sessions store one total cost_usd (priced per-turn by that turn's own
    model), not a per-category dollar amount — so this apportions the total
    by each category's token count weighted by its price multiplier relative
    to input, rather than re-pricing per model (which would need per-day
    model attribution we don't store).
    # ponytail: approximation, not exact per-model pricing. Upgrade path: store
    # per-category cost at index time (like cost_usd) if per-model precision
    # ever matters here.
    """
    weighted = {
        "input": input_tokens,
        "output": output_tokens * OUTPUT_MULTIPLIER,
        "cache_write": cache_write_tokens * CACHE_WRITE_MULTIPLIER,
        "cache_read": cache_read_tokens * CACHE_READ_MULTIPLIER,
    }
    total_weight = sum(weighted.values())
    if total_weight <= 0:
        return dict.fromkeys(weighted, 0.0)
    return {k: total_cost_usd * w / total_weight for k, w in weighted.items()}


def price_per_mtok(model: str) -> tuple[float, float] | None:
    for prefix, prices in _PRICES.items():
        if model.startswith(prefix):
            return prices
    return None


def estimate_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_creation_tokens: int = 0,
    cache_read_tokens: int = 0,
) -> float:
    """USD cost of one turn's usage block. Returns 0.0 for an unrecognized model."""
    prices = price_per_mtok(model)
    if prices is None:
        return 0.0
    input_price, output_price = prices
    return (
        input_tokens * input_price
        + output_tokens * output_price
        + cache_creation_tokens * input_price * CACHE_WRITE_MULTIPLIER
        + cache_read_tokens * input_price * CACHE_READ_MULTIPLIER
    ) / 1_000_000
