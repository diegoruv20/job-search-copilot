# Architecture

Job Search Copilot is intentionally local-first and single-user.

```text
Coding agent --stdio--> MCP server ----\
                                        > job_search_copilot/services.py
Browser --------HTTP--> Flask REST -----/              |
Playwright ------------> job sites and dashboard       v
                                                       SQLite
```

## Boundaries

- `job_search_copilot/services.py` owns validation, lifecycle transitions,
  ranking data, statistics, history, and Sankey behavior.
- `job_search_copilot/api.py` is a thin browser-facing adapter.
- `mcp_server.py` is the typed automation adapter.
- `app.py` configures Flask, the database, and safe SQLite concurrency.
- `job_search_copilot/data_portability.py` owns backup, restore, export, import,
  and demo loading.
- `job_search_copilot/workspace.py` reports local profile and MCP readiness to
  setup, MCP, and the dashboard without exposing file contents.
- `local/` contains private profile and application evidence and is never committed.

REST and MCP must not reimplement business rules. Add or change behavior in the
service layer, then test both adapters for parity.

## Customization contract

The repository is intended to evolve for each user. The portable
`safe-customization` playbook defines the guarded workflow for design, feature,
workflow, and schema changes. Copilot users may invoke the `product-customizer`
agent; other clients can give the same playbook to a general-purpose agent.

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
are opened only when the user asks an agent or Playwright to research them.

The dashboard reads `/api/workspace` to show onboarding steps until the private
career interview is complete.

The dashboard polls the lightweight `/api/revision` endpoint while the page is
open. A changed revision triggers a full refresh, so mutations made through MCP,
REST, or another browser tab appear without a manual reload. Refresh is deferred
while a job form, historical Sankey frame, or timeline playback is active. Focus
and visibility events trigger immediate checks when the user returns.

The Sankey timeline defaults to a daily summary. Highlights retains meaningful
within-day transitions, All activity preserves every exact snapshot, and
playback supports 1x or 2x speed without changing stored history. Current graphs
distinguish initial screens, technical interviews, and final or onsite rounds.
Older snapshots retain their original graph data; a separate read-only display
view reconstructs the expanded stage presentation from timestamped status
history. The chart measures labels to create a responsive layout and exposes an
accessible horizontal-scroll hint when every stage cannot fit.

Job rows and recommendation cards expose an Open resume link only when the local
applications directory contains one unambiguous role-matched PDF. The browser
opens the PDF through a read-only localhost endpoint; arbitrary client paths and
paths outside the configured applications root are rejected.

The Working Queue provides New opportunities, Current pursuits, My applications,
and All jobs over the standard jobs table. Search, status, recommendation,
visibility, and sorting controls narrow the selected view. Results paginate in
fixed groups of ten on desktop and mobile, while reset restores each workflow's
defaults.

Current pursuits is derived in the service layer without a schema field or
personal flag. It includes unarchived active interview stages and Applied roles
whose current stage, next action, or current-status history records a confirmed
recruiter or hiring-manager response or scheduled conversation. Ordinary
applications awaiting a response, preparation and hold work, offers, and closed
outcomes are excluded. `/api/jobs?workflow=pursuits`,
`/api/current-pursuits`, and `current_pursuits_get` share the same domain rule.

## Process safety

The MCP server launches the dashboard with the active virtual environment's Python
and records the exact process ID under `runtime/`. Stop operations require explicit
confirmation and target only that recorded process.
