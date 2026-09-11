# Job Search Copilot

A private, local-first job-search command center for GitHub Copilot CLI. It
combines a Flask dashboard, SQLite tracker, typed MCP tools, evidence-based resume
and outreach workflows, and interview coaching without hosting personal data.

## Five-minute setup

Requirements: Python 3.10+ with the Windows `py` launcher and GitHub Copilot CLI.

```powershell
git clone <your-private-repository-url>
cd job-search-copilot
.\scripts\setup.ps1
```

The setup creates `.venv`, installs dependencies, initializes a blank database,
copies private profile templates under `local/`, runs tests, and checks readiness.
The files intentionally begin as `not started`; the guided interview completes
them:

- `local\user_profile.md`
- `local\experience_inventory.md`

You do not need to fill them out alone. Start Copilot CLI and say:

> Use the career-discovery agent. Interview me to build my profile and experience
> inventory. Ask three to five simple questions at a time, update the files after
> each round, and help me identify realistic roles and positioning.

The interview begins with your actual work and goals, deep-dives major projects,
separates personal ownership from team results, verifies skills and metrics, and
ends with evidence-backed role families and positioning statements.

Then start Copilot CLI from this repository, trust the folder, and use `/mcp` to
confirm that `job-search-copilot` is enabled. The committed launcher automatically
uses this checkout's virtual environment.

To preview the product with fictional jobs:

```powershell
.\scripts\setup.ps1 -Demo
```

## Use it

Ask Copilot:

> Start my dashboard and show the highest-priority next actions.

> Find newly published roles that fit my profile. Verify the official postings and
> add only strong candidates.

> Prepare the application package for job 12, but do not submit anything.

> Run a cold interview mock for my next confirmed stage.

Copilot inspects live tracker state through MCP, uses Playwright for job sites and
the dashboard, and follows the repository's skills and agents. It never submits an
application, uploads a file, or sends outreach without explicit approval.

The dashboard is available at `http://127.0.0.1:5050` after:

```powershell
.\.venv\Scripts\python.exe app.py
```

## Local data and portability

The first run is blank. Private state is excluded from Git:

- `instance\applications.db`
- `local\`
- `backups\`
- `exports\`
- `runtime\`

Useful commands:

```powershell
.\.venv\Scripts\python.exe tracker_cli.py doctor
.\.venv\Scripts\python.exe tracker_cli.py demo
.\.venv\Scripts\python.exe tracker_cli.py backup
.\.venv\Scripts\python.exe tracker_cli.py export
```

Import, restore, and replacement demo loading require deliberate flags. Restore
creates a safety backup before changing the database.

## How it works

- **Dashboard:** visual pipeline, follow-ups, freshness, conversion, and Sankey
  history.
- **MCP server:** safe tracker CRUD, application/outcome recording, dashboard
  lifecycle, recommendations, statistics, backup, and portability.
- **Repository skills:** job discovery, resume preparation, outreach drafting,
  application tracking, and interview practice.
- **Private evidence:** local profile and experience inventory keep recommendations
  personal without committing user data.

See [architecture](docs/architecture.md), [Copilot workflows](docs/workflows.md),
[profile onboarding](docs/profile-onboarding.md),
[data and privacy](docs/data-and-privacy.md), and
[troubleshooting](docs/troubleshooting.md).

The committed MCP configuration targets Windows. On macOS or Linux, change its
launcher command from `py` with `-3` to `python3`; the launcher still selects the
checkout's `.venv`.

## Development

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts\release_check.py
```

Change domain behavior in `services.py`, then preserve REST/MCP parity. Keep MCP
stdout protocol-clean and add tests for lifecycle transitions and destructive
guards.
