# Data ownership, backup, and privacy

## What stays local

The following paths are gitignored:

- `instance/` - SQLite database
- `local/` - profile, experience inventory, and application artifacts
- `backups/` - online SQLite backups
- `exports/` - portable JSON exports
- `runtime/` - dashboard logs and process ID

Do not remove these exclusions when publishing or sharing the repository.

## Browser-tab Working Queue state

The dashboard uses browser `sessionStorage` to keep Working Queue controls stable
across reloads in the same tab. Only controls explicitly marked for queue state
are stored: the active workflow, search text, status, recommendation, visibility,
sort, visible advanced-filter controls, and current page when those controls are
present. Values are validated against the controls currently rendered before
they are restored. Missing, malformed, outdated, or no-longer-valid state is
ignored, and Reset filters removes the saved state.

This tab-scoped state never includes jobs, notes, profile or resume data,
applications, external page content, or API responses. It is not written to the
tracker database, synchronized to another device, or sent to a hosted service.
Browsers that block `sessionStorage` continue to use the dashboard without
persistence.

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
