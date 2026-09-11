# Troubleshooting

## Run the setup check

```powershell
.\.venv\Scripts\python.exe tracker_cli.py doctor
```

`ok` becomes true after the database, MCP configuration, private profile, and
experience inventory are present.

## Copilot does not show tracker tools

1. Run `python scripts/bootstrap.py`.
2. Start Copilot CLI from the repository root.
3. Trust the repository when prompted.
4. Open `/mcp` and confirm `job-search-copilot` is enabled.
5. Restart the CLI after changing `.github/mcp.json`.

The committed MCP configuration calls a standard-library launcher, which then
uses the checkout's `.venv` Python. This avoids depending on shell activation.
The launcher passes paths as a subprocess argument list so repository paths
containing spaces are supported.
It uses the Windows `py -3` launcher. On macOS or Linux, use `python3` and remove
the `-3` argument in `.github/mcp.json`.

## Dashboard does not start

Run:

```powershell
.\.venv\Scripts\python.exe app.py
```

Then open `http://127.0.0.1:5050`. If port 5050 is occupied, set
`JOB_TRACKER_PORT` before starting both the MCP server and dashboard.

MCP-managed dashboard logs are written to `runtime/dashboard.log`.

## SQLite is locked

Stop duplicate dashboard processes and retry. The application already enables
WAL and a 15-second busy timeout. Do not copy a live database file manually; use
the backup command.

## Demo loading is refused

The tracker is not empty. Use the existing data, create a backup and pass
`--replace`, or initialize a separate database with `JOB_TRACKER_DATABASE_PATH`.
