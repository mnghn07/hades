import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from hades import pricing
from hades.config import get_config
from hades.db import get_db

from hades.console import console

STATIC_DIR = Path(__file__).parent.parent / "static"


def _date_range(query: dict) -> tuple[str, str] | None:
    frm, to = query.get("from", [None])[0], query.get("to", [None])[0]
    if not frm or not to:
        return None
    return frm, to


def _summary_rows(db, frm: str, to: str) -> list[dict]:
    rows = db.execute(
        """SELECT tool, project_path,
             COALESCE(SUM(input_tokens), 0), COALESCE(SUM(output_tokens), 0),
             COALESCE(SUM(cache_write_tokens), 0), COALESCE(SUM(cache_read_tokens), 0),
             COALESCE(SUM(cost_usd), 0.0)
           FROM sessions
           WHERE is_archived IS NOT 1 AND date(last_active_at) BETWEEN ? AND ?
           GROUP BY tool, project_path""",
        [frm, to],
    ).fetchall()
    return [
        {
            "tool": tool, "project": project,
            "input": inp, "output": out, "cache_write": cw, "cache_read": cr,
            "cost_usd": cost or 0.0,
        }
        for tool, project, inp, out, cw, cr, cost in rows
    ]


def _daily_rows(db, frm: str, to: str) -> list[dict]:
    rows = db.execute(
        """SELECT date(last_active_at) as day,
             COALESCE(SUM(input_tokens), 0), COALESCE(SUM(output_tokens), 0),
             COALESCE(SUM(cache_write_tokens), 0), COALESCE(SUM(cache_read_tokens), 0),
             COALESCE(SUM(cost_usd), 0.0)
           FROM sessions
           WHERE is_archived IS NOT 1 AND date(last_active_at) BETWEEN ? AND ?
           GROUP BY day""",
        [frm, to],
    ).fetchall()
    out = []
    for day, inp, out_tok, cw, cr, cost in rows:
        shares = pricing.category_cost_shares(inp, out_tok, cw, cr, cost or 0.0)
        out.append({
            "date": day,
            "input": inp, "output": out_tok, "cache_write": cw, "cache_read": cr,
            "input_cost": shares["input"], "output_cost": shares["output"],
            "cache_write_cost": shares["cache_write"], "cache_read_cost": shares["cache_read"],
        })
    return out


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):  # pylint: disable=redefined-builtin
        pass  # quiet by default; `hades serve` prints its own startup line

    def _json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # pylint: disable=invalid-name
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)

        if parsed.path == "/":
            body = (STATIC_DIR / "serve.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if parsed.path in ("/api/summary", "/api/daily"):
            date_range = _date_range(query)
            if date_range is None:
                self._json({"error": "from and to query params are required (YYYY-MM-DD)"}, status=400)
                return
            frm, to = date_range
            db = get_db()
            if parsed.path == "/api/summary":
                self._json({"rows": _summary_rows(db, frm, to)})
            else:
                self._json({"days": _daily_rows(db, frm, to)})
            return

        self.send_response(404)
        self.end_headers()


def cmd_serve(port: int | None, host: str = "127.0.0.1") -> None:
    resolved_port = port if port is not None else get_config("serve_port")
    server = ThreadingHTTPServer((host, resolved_port), _Handler)
    console.print(f"[green]hades serve[/green] running at http://{host}:{resolved_port} — Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
