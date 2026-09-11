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
- `workspace.py` reports local profile and MCP readiness to setup, MCP, and the
  dashboard without exposing file contents.
- `local/` contains private profile and application evidence and is never committed.

REST and MCP must not reimplement business rules. Add or change behavior in the
service layer, then test both adapters for parity.

## Customization contract

The repository is intended to evolve for each user. The `product-customizer`
agent and `safe-customization` skill define the guarded workflow for design,
feature, workflow, and schema changes.

Customizations must preserve local-first privacy, current data, REST/MCP parity,
and blank-first-run behavior. A schema change needs an idempotent upgrade path
that produces the same final schema for old and new databases. Export, import,
backup, restore, setup, documentation, and relevant UI states are part of the
feature surface rather than optional follow-up work.

## Local data

The default database is `instance/applications.db`. SQLite uses write-ahead
logging, foreign keys, and a 15-second busy timeout. Online backups use SQLite's
backup API so a running dashboard can be copied consistently.

No tracker data is sent to a hosted service by this repository. External job sites
are opened only when the user asks Copilot or Playwright to research them.

The dashboard reads `/api/workspace` to show onboarding steps until the private
career interview is complete.

## Process safety

The MCP server launches the dashboard with the active virtual environment's Python
and records the exact process ID under `runtime/`. Stop operations require explicit
confirmation and target only that recorded process.
