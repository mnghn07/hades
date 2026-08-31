import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from hades.commands.serve import _Handler
from hades.db import get_db
from hades.indexer import refresh_index


def _point_at_claude_root(monkeypatch, claude_session_file):
    monkeypatch.setenv("HADES_CLAUDE_PATH", str(claude_session_file.parent.parent))
    from hades.sources.claude import ClaudeSource
    monkeypatch.setattr("hades.indexer.ALL_SOURCES", [ClaudeSource])


@pytest.fixture
def running_server(db_path, claude_session_file, monkeypatch):  # pylint: disable=unused-argument
    _point_at_claude_root(monkeypatch, claude_session_file)
    db = get_db()
    refresh_index(db)

    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def _get(url):
    with urllib.request.urlopen(url) as resp:
        return resp.status, resp.headers.get("Content-Type"), resp.read()


def test_index_page_serves_html(running_server):
    status, content_type, body = _get(running_server + "/")
    assert status == 200
    assert content_type == "text/html"
    assert b"hades serve" in body


def test_summary_endpoint_returns_rows_for_range(running_server):
    status, content_type, body = _get(running_server + "/api/summary?from=2020-01-01&to=2030-01-01")
    assert status == 200
    assert content_type == "application/json"
    data = json.loads(body)
    assert data["rows"] == [{
        "tool": "claude", "project": "/Users/test/project",
        "input": 0, "output": 0, "cache_write": 0, "cache_read": 0, "cost_usd": 0.0,
    }]


def test_summary_endpoint_empty_outside_range(running_server):
    _, _, body = _get(running_server + "/api/summary?from=2019-01-01&to=2019-01-02")
    assert json.loads(body)["rows"] == []


def test_summary_endpoint_requires_date_range(running_server):
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        _get(running_server + "/api/summary")
    assert exc_info.value.code == 400


def test_daily_endpoint_returns_one_row_per_active_day(running_server):
    _, _, body = _get(running_server + "/api/daily?from=2020-01-01&to=2030-01-01")
    data = json.loads(body)
    assert data["days"] == [{
        "date": "2026-07-03",
        "input": 0, "output": 0, "cache_write": 0, "cache_read": 0,
        "input_cost": 0.0, "output_cost": 0.0, "cache_write_cost": 0.0, "cache_read_cost": 0.0,
    }]


def test_unknown_path_is_404(running_server):
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        _get(running_server + "/nope")
    assert exc_info.value.code == 404
