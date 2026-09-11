# Job Search Copilot

A private, local-first job-search command center for GitHub Copilot CLI. It
combines a Flask dashboard, SQLite tracker, typed MCP tools, evidence-based resume
and outreach workflows, and interview coaching without hosting personal data.

## Five-minute setup

Requirements: Python 3.10+ and GitHub Copilot CLI.

```powershell
git clone <your-private-repository-url>
cd job-search-copilot
.\scripts\setup.ps1
```

The setup creates `.venv`, installs dependencies, initializes a blank database,
copies private profile templates under `local/`, runs tests, and checks readiness.
Edit:

- `local\user_profile.md`
- `local\experience_inventory.md`

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
[data and privacy](docs/data-and-privacy.md), and
[troubleshooting](docs/troubleshooting.md).

## Development

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Change domain behavior in `services.py`, then preserve REST/MCP parity. Keep MCP
stdout protocol-clean and add tests for lifecycle transitions and destructive
guards.
