from hades.sources.cursor import _decode_dir, _extract_title, _parse_embedded_timestamp


def test_parse_embedded_timestamp():
    text = "<timestamp>Thursday, Jul 30, 2026, 2:05 PM (UTC+7)</timestamp>\n<user_query>\nhi\n</user_query>"
    dt = _parse_embedded_timestamp(text)
    assert dt is not None
    assert (dt.year, dt.month, dt.day, dt.hour, dt.minute) == (2026, 7, 30, 14, 5)
    assert dt.utcoffset().total_seconds() == 7 * 3600


def test_parse_embedded_timestamp_negative_offset():
    text = "<timestamp>Monday, Jan 5, 2026, 11:30 PM (UTC-5)</timestamp>"
    dt = _parse_embedded_timestamp(text)
    assert dt.utcoffset().total_seconds() == -5 * 3600


def test_parse_embedded_timestamp_missing_returns_none():
    assert _parse_embedded_timestamp("no timestamp here") is None


def test_extract_title_strips_wrapper_tags():
    texts = [
        "<timestamp>Thursday, Jul 30, 2026, 2:05 PM (UTC+7)</timestamp>\n"
        "<user_query>\nHelp me build a CLI tool\n</user_query>"
    ]
    assert _extract_title(texts) == "Help me build a CLI tool"


def test_extract_title_skips_turns_without_user_query():
    texts = ["<hooks_context>injected context</hooks_context>", "<user_query>\nreal question\n</user_query>"]
    assert _extract_title(texts) == "real question"


def test_extract_title_returns_none_when_no_query_tag_found():
    assert _extract_title(["just plain text, no tags"]) is None


def test_decode_dir():
    assert _decode_dir("Users-test-project") == "/Users/test/project"
