from hades.process_checker import _classify


def test_claude_interactive_session_stream_json():
    assert _classify("claude", "/x/claude --output-format stream-json --verbose") == "claude"


def test_claude_version_named_binary():
    assert _classify("2.1.199", "/x/claude --output-format stream-json") == "claude"


def test_codex_native_binary_child_process():
    assert _classify("codex", "/x/vendor/aarch64-apple-darwin/bin/codex") == "codex"


def test_gemini_npx_launched_script_path():
    cmdline = "/x/node --max-old-space-size=24576 /x/.npm/_npx/hash/node_modules/.bin/gemini"
    assert _classify("node", cmdline) == "gemini"


def test_gemini_direct_binary_name():
    assert _classify("gemini", "/x/gemini") == "gemini"


def test_unrelated_node_process_not_classified():
    assert _classify("node", "node -e some_unrelated_script.js") is None
