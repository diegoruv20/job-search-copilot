# Data ownership, backup, and privacy

## What stays local

The following paths are gitignored:

- `instance/` - SQLite database
- `local/` - profile, experience inventory, and application artifacts
- `backups/` - online SQLite backups
- `exports/` - portable JSON exports
- `runtime/` - dashboard logs and process ID

Do not remove these exclusions when publishing or sharing the repository.

## Backup

Create a consistent backup while the dashboard is running:

```powershell
.\.venv\Scripts\python.exe tracker_cli.py backup
```

Backups are timestamped under `backups/` by default.

## Export and import

JSON exports are useful for moving state between installations:

```powershell
.\.venv\Scripts\python.exe tracker_cli.py export
.\.venv\Scripts\python.exe tracker_cli.py import exports\tracker-export.json
```

Import refuses to replace a non-empty tracker unless `--replace` is explicit.
Records are validated before existing state is deleted.

## Restore

Restore is destructive and therefore requires confirmation:

```powershell
.\.venv\Scripts\python.exe tracker_cli.py restore backups\applications.db --confirm
```

A safety backup is created before replacement.

## Before sharing

Run `python scripts/privacy_scan.py` or the complete
`python scripts/release_check.py` gate. The scan rejects tracked databases,
profiles, resumes, backups, exports, private absolute paths, and optional private
markers supplied through `JOB_SEARCH_PRIVATE_MARKERS`.
