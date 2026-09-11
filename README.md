# Job Search Copilot

A local-first job-search workspace with a Flask dashboard, SQLite storage, and a
planned Model Context Protocol (MCP) interface for GitHub Copilot CLI.

Each user runs an independent local copy. Application history, profiles, resumes,
exports, and databases stay on that user's computer and are excluded from Git.

## Current development status

This repository is being prepared as a polished private beta. The browser tracker
is functional; MCP tools, first-run onboarding, portable profiles, and full product
documentation are being added in separate reviewed changes.

## Development setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5050`.

The first run creates an empty database under `instance\applications.db`. Never
commit that directory.

Initialize explicitly or load fictional demo data:

```powershell
python tracker_cli.py init
python tracker_cli.py demo
```

Demo loading refuses to modify a non-empty tracker unless `--replace` is supplied.

Create portable backups and exports:

```powershell
python tracker_cli.py backup
python tracker_cli.py export
```

## Tests

```powershell
python -m unittest discover -s tests -v
```

## Privacy

Do not commit:

- Application history or SQLite databases
- Names or contact details for recruiters and referrals
- Resumes, cover letters, or application answers
- Personal job-search preferences or experience inventories
- Backups and exports
