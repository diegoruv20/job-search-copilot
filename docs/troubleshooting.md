# Troubleshooting

## Run the setup check

```powershell
.\.venv\Scripts\python.exe tracker_cli.py doctor
```

`ok` becomes true after the database, MCP configuration, private profile, and
experience inventory are present.

## The agent does not show tracker or Playwright tools

1. Run `python scripts/bootstrap.py`.
2. Start the agent from the repository root.
3. Confirm its project-level MCP configuration includes `job-search-copilot` and
   `playwright`.
4. Restart the client after changing its MCP settings.

Copilot CLI uses `.github/mcp.json` automatically. Other clients can use the
portable definitions in `config/mcp.windows.json` or `config/mcp.posix.json`; see
[agent setup](agents.md).

The tracker definition calls a standard-library launcher, which then uses the
checkout's `.venv` Python. This avoids depending on shell activation. The launcher
passes paths as a subprocess argument list so repository paths containing spaces
are supported.

Playwright MCP uses a tested, pinned package version. If it does not start, verify:

```powershell
node --version
npx --version
```

Install the current Node.js LTS release and reopen the terminal if either command
is missing. The first Playwright MCP launch may take longer while `npx` downloads
the package.

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
