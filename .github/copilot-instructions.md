# GitHub Copilot adapter

Follow the complete vendor-neutral repository contract in `AGENTS.md`.

GitHub Copilot CLI additionally supports the repository's automatically
discoverable integrations:

- `.github/mcp.json` starts the tracker and Playwright MCP servers.
- `.github/agents/` provides named specialist personas.
- `.github/skills/` provides reusable workflow playbooks.

When a named agent or skill matches the user's request, load it before acting.
Agents that do not support Copilot's discovery format can read the same Markdown
files directly, as described in `docs/agents.md`.
