<div align="center">

# Job Search Copilot

**A private job-search command center for GitHub Copilot CLI**

Turn your real experience and preferences into evidence-backed job discovery,
application materials, outreach drafts, interview practice, and a measurable
application pipeline—all from a local workspace you control.

</div>

## What you get

| Capability | What it does |
|---|---|
| Guided career discovery | Interviews you in short rounds, builds an evidence inventory, and identifies realistic role families and positioning |
| Verified job search | Uses Playwright to inspect human-visible job sites and official postings before recording opportunities |
| Private application tracker | Stores jobs, follow-ups, outcomes, freshness, conversion, and application-flow history in local SQLite |
| Application strategy | Creates evidence-based resumes, application answers, company notes, and outreach drafts without submitting or sending |
| Interview coaching | Builds role-specific plans and runs realistic, scored practice using your confirmed experience |
| Safe customization | Lets Copilot redesign workflows and add features while protecting local data, shared contracts, and existing behavior |

## Quick start

### 1. Clone and set up

Requirements:

- Python 3.10+ with the Windows `py` launcher
- Current Node.js LTS with `npx`
- GitHub Copilot CLI

```powershell
git clone https://github.com/diegoruv20/job-search-copilot.git
cd job-search-copilot
.\scripts\setup.ps1
```

Setup explains each stage, creates `.venv`, installs dependencies, initializes an
empty local database, creates private profile templates, runs tests, and checks
MCP readiness. Existing profiles and tracker data are never overwritten.

### 2. Start Copilot

Run `copilot` from the repository, trust the folder, and open `/mcp`. Both servers
should be enabled:

- `job-search-copilot` manages local tracker state.
- `playwright` researches job sites and checks the dashboard.

### 3. Build your profile

Do not fill out a giant form alone. Start the guided interview:

> Use the career-discovery agent. Interview me to build my job-search profile and
> experience inventory. Ask three to five simple questions at a time, update the
> files after each round, and help me identify realistic role families and
> positioning.

Copilot learns your systems and projects, resolves personal ownership and metrics,
classifies direct versus transferable experience, gathers constraints, and
produces an evidence-backed role map.

### 4. Open the dashboard

Ask Copilot:

> Start my dashboard and show my highest-priority next actions.

Or run it directly:

```powershell
.\.venv\Scripts\python.exe app.py
```

Open [http://127.0.0.1:5050](http://127.0.0.1:5050).

## Common workflows

| Goal | Example prompt |
|---|---|
| Find roles | `Find newly published backend and data-platform roles that fit my profile. Verify official postings and add only strong candidates.` |
| Prepare an application | `Prepare the application package for job 12, but do not submit anything.` |
| Draft outreach | `Research the best warm contact for job 12 and draft a message for me to send manually.` |
| Practice an interview | `Run a 45-minute cold system-design mock for my next confirmed stage.` |
| Record progress | `I applied today using the final resume. Update the tracker and set the next follow-up.` |
| Customize the product | `Use the product-customizer agent to add a weekly planning view without breaking my current data or workflow.` |

Copilot never submits applications, uploads documents, or sends outreach without
explicit approval.

## Private by design

Your personal state stays outside Git:

| Local path | Contents |
|---|---|
| `instance\` | SQLite application database |
| `local\` | Profile, experience inventory, and application artifacts |
| `backups\` | Online SQLite backups |
| `exports\` | Portable JSON exports |
| `runtime\` | Dashboard logs and process state |

The browser dashboard and tracker MCP run locally. Playwright accesses external
sites only when job research or browser verification is requested.

## Useful commands

```powershell
# Check setup and profile readiness
.\.venv\Scripts\python.exe tracker_cli.py doctor

# Load fictional sample jobs
.\.venv\Scripts\python.exe tracker_cli.py demo

# Protect or move your data
.\.venv\Scripts\python.exe tracker_cli.py backup
.\.venv\Scripts\python.exe tracker_cli.py export

# Validate a development change
.\.venv\Scripts\python.exe scripts\release_check.py
```

Import and restore operations validate their source and require deliberate
replacement flags. Restore creates a safety backup before changing the database.

## Architecture

```text
Copilot CLI --> tracker MCP ----\
                                 > services.py --> SQLAlchemy --> local SQLite
Dashboard ----> Flask REST -----/
Playwright ---> job sites and dashboard
```

Business rules live in `services.py`; REST and MCP are adapters over the same
validated lifecycle.

## Documentation

- [Guided profile onboarding](docs/profile-onboarding.md)
- [Safe customization](docs/customization.md)
- [Copilot workflows](docs/workflows.md)
- [Architecture](docs/architecture.md)
- [Data ownership and recovery](docs/data-and-privacy.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Security and privacy](SECURITY.md)

## License

Licensed under the [MIT License](LICENSE). Fork it, adapt the local workflows,
and make it your own while keeping personal tracker data outside Git.

## Platform notes

The committed MCP configuration targets Windows. On macOS or Linux, change the
tracker command in `.github/mcp.json` from `py` with `-3` to `python3`; the
launcher still selects the checkout's `.venv`.
