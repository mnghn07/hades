# `hades serve` uses stdlib `http.server`, not a web framework

Status: accepted

`hades serve` starts a foreground localhost HTTP server (stdlib `http.server`) that serves one static HTML/JS page plus a couple of JSON endpoints reading the SQLite index. No Flask/FastAPI/etc. dependency is added.

We considered a micro-framework for nicer routing/templating. Rejected: the surface is one page and two read-only endpoints against local data — a framework buys nothing at this size and adds a dependency (plus its own attack surface) to a tool whose value proposition is staying lightweight and local-only (`pyproject.toml` carries no web dependency today; `typer`/`rich`/`sqlite-utils` are all it needs). Revisit only if `serve` grows enough routes/state that hand-rolled dispatch becomes the harder path.
