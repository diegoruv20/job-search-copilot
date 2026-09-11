# Security and privacy

Job Search Copilot is a local, single-user application. It does not provide
authentication and must not be exposed directly to the public internet.

## Private data

Databases, profiles, resumes, application artifacts, backups, exports, runtime
files, and browser-test output are excluded from Git. Run the complete release
gate before publishing changes:

```powershell
.\.venv\Scripts\python.exe scripts\release_check.py
```

The privacy scan checks the tracked tree and reachable Git history for private
directories, private artifact types, personal absolute paths, and optional
markers supplied through `JOB_SEARCH_PRIVATE_MARKERS`.

## Reporting a vulnerability

Please report a suspected vulnerability privately through GitHub's security
advisory interface rather than opening a public issue. Include reproduction
steps, affected versions or commits, and the potential impact.
