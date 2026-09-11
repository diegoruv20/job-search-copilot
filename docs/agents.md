# Use your preferred agent

Job Search Copilot is not tied to one model or CLI. The dashboard, SQLite
database, REST API, command-line utilities, and MCP server are ordinary local
software. GitHub Copilot CLI is the preconfigured default, but any MCP-capable
coding agent that can read repository instructions can use the same tracker and
workflows.

## Portable contract

Every agent should:

1. Read `AGENTS.md` as the authoritative safety and architecture contract.
2. Read `local/user_profile.md` and `local/experience_inventory.md` before
   personalized work.
3. Connect to the `job-search-copilot` and `playwright` MCP servers.
4. Select the relevant Markdown playbook under `.github/skills/`.
5. Use tracker MCP tools for mutations and Playwright for human-visible websites.

The `.github/skills/` files use Copilot-compatible frontmatter, but their bodies
are portable instructions. Other agents can read them directly.

## Connect MCP

MCP clients use different configuration file names and settings screens, but the
two stdio server definitions are the same. Start the client from the repository
root so relative paths resolve correctly.

### Windows

Use `config/mcp.windows.json` as the source configuration:

```json
{
  "mcpServers": {
    "job-search-copilot": {
      "type": "stdio",
      "command": "py",
      "args": ["-3", "scripts/mcp_launcher.py"]
    },
    "playwright": {
      "type": "stdio",
      "command": "npx",
      "args": ["@playwright/mcp@0.0.80"]
    }
  }
}
```

### macOS and Linux

Use `config/mcp.posix.json`, which replaces the Windows Python launcher with
`python3`:

```json
{
  "mcpServers": {
    "job-search-copilot": {
      "type": "stdio",
      "command": "python3",
      "args": ["scripts/mcp_launcher.py"]
    },
    "playwright": {
      "type": "stdio",
      "command": "npx",
      "args": ["@playwright/mcp@0.0.80"]
    }
  }
}
```

Copy the `mcpServers` object into the project-level MCP configuration expected by
your client. Do not commit machine-specific absolute paths or private data.

## Client options

| Client type | How to use this repository |
|---|---|
| GitHub Copilot CLI | Uses `.github/mcp.json`, `.github/copilot-instructions.md`, agents, and skills automatically |
| MCP-capable coding agent | Point its project MCP settings at one of the portable configs and tell it to follow `AGENTS.md` |
| Agent without MCP | Use `tracker_cli.py` and the dashboard for read-only or manual work; do not let the agent edit SQLite |
| Human-only workflow | Run the dashboard directly and use the CLI for backup, import, export, and diagnostics |

Client capabilities and configuration formats change over time. Prefer the
client's official MCP documentation when choosing where to place the server
definitions.

## Pick a workflow

You can use a named specialist when the client supports custom agents, or give
the same workflow file to a general-purpose agent:

| Goal | Portable workflow | Copilot specialist |
|---|---|---|
| Discover career direction | `.github/skills/profile-onboarding/SKILL.md` | `career-discovery` |
| Find and verify jobs | `.github/skills/job-search/SKILL.md` | `job-search-specialist` |
| Prepare an application | `.github/skills/resume-making/SKILL.md` | `application-strategist` |
| Draft outreach | `.github/skills/outreach/SKILL.md` | General agent with the outreach skill |
| Practice interviews | `.github/skills/interview-prep/SKILL.md` | `interview-coach` |
| Customize the product | `.github/skills/safe-customization/SKILL.md` | `product-customizer` |

Example for any agent:

> Read `AGENTS.md` and `.github/skills/job-search/SKILL.md`. Inspect my live
> tracker through MCP, then find newly published roles that fit my private
> profile. Verify official postings with Playwright and record only strong,
> deduplicated candidates.

## Verify the connection

Run:

```powershell
.\.venv\Scripts\python.exe tracker_cli.py doctor
.\.venv\Scripts\python.exe scripts\mcp_smoke.py
```

The smoke check should report the tracker tools without writing to the database.
