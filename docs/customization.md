# Safe customization

This repository is a baseline for a personal job-search system, not a fixed
one-size-fits-all product. A capable coding agent can change its design,
workflows, analytics, and features as the user's needs become clearer.

Give the agent the `safe-customization` playbook and a concrete outcome. Copilot
users can select the dedicated `product-customizer` agent:

> Use the product-customizer agent to add a weekly planning view. Preserve my
> current data and workflows, show me any important design decision, and validate
> the finished feature.

## What can be customized

- Dashboard layout, navigation, accessibility, and visual design
- Tracker fields, filters, recommendations, and analytics
- Personal workflow steps and reminders
- MCP tools and agent-assisted workflows
- Import, export, backup, and reporting features
- Setup and onboarding for the user's environment

## Safety model

The customization agent follows four layers of protection:

1. **Architecture boundaries:** business rules stay in
   `job_search_copilot/services.py`, with REST and MCP using the same
   implementation.
2. **Data protection:** schema and destructive changes require compatibility
   planning, temporary-database tests, and a verified backup.
3. **Experience protection:** changes preserve familiar behavior and include
   usable empty, loading, success, and error states on desktop and mobile.
4. **Release protection:** privacy checks, unit tests, MCP smoke tests, Python
   compilation, and JavaScript syntax validation run through
   `scripts/release_check.py`.

The agent should ask before choices involving product scope, data meaning,
privacy, destructive behavior, or a major workflow replacement. It can make
routine implementation decisions independently when they follow established
patterns.

## Database changes

User data is more important than a new feature. A database customization must:

- Preserve existing columns and meanings unless the user approves a migration.
- Upgrade old databases through a repeatable, idempotent path.
- Initialize blank databases to the same final schema.
- Keep JSON import/export and SQLite backup/restore compatible.
- Be tested on a temporary database or backup copy.

Normal tracker changes still go through services or MCP tools rather than direct
SQLite edits.

## Recommended workflow

1. Describe the need in user terms.
2. Let the agent inspect the live product and relevant code.
3. Resolve any consequential design questions.
4. Review the implemented behavior in the dashboard.
5. Keep the change only after the release check passes.

Use small, coherent commits so an unwanted customization can be reverted without
discarding unrelated improvements or private state.
