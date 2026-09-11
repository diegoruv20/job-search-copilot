# Architecture

Job Search Copilot is intentionally local-first and single-user.

```text
Copilot CLI --stdio--> MCP server ----\
                                      > services.py --> SQLAlchemy --> SQLite
Browser ------HTTP--> Flask REST -----/
Playwright ----------> job sites and local dashboard
```

## Boundaries

- `services.py` owns validation, lifecycle transitions, ranking data, statistics,
  history, and Sankey behavior.
- `api.py` is a thin browser-facing adapter.
- `mcp_server.py` is the typed automation adapter.
- `app.py` configures Flask, the database, and safe SQLite concurrency.
- `data_portability.py` owns backup, restore, export, import, and demo loading.
- `local/` contains private profile and application evidence and is never committed.

REST and MCP must not reimplement business rules. Add or change behavior in the
service layer, then test both adapters for parity.

## Local data

The default database is `instance/applications.db`. SQLite uses write-ahead
logging, foreign keys, and a 15-second busy timeout. Online backups use SQLite's
backup API so a running dashboard can be copied consistently.

No tracker data is sent to a hosted service by this repository. External job sites
are opened only when the user asks Copilot or Playwright to research them.

## Process safety

The MCP server launches the dashboard with the active virtual environment's Python
and records the exact process ID under `runtime/`. Stop operations require explicit
confirmation and target only that recorded process.
