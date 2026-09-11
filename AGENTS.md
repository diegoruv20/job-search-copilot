# Job Search Copilot Agent Guide

Use the local `job-search-copilot` MCP server as the source of truth for tracker
state. Use Playwright for human-visible job sites, official application pages, and
dashboard testing. Never write directly to the SQLite database.

Before personalized work, read:

- `local/user_profile.md`
- `local/experience_inventory.md`

If either file is missing, use the examples under `config/` to help the user create
it. Never infer or invent skills, metrics, employment history, compensation,
location eligibility, work authorization, or personal preferences.

Do not submit an application, upload a resume, send outreach, or replace tracker
data without explicit approval.

For repository fixes or reusable features, follow `CONTRIBUTING.md`. Classify the
change before editing:

- Universal fixes belong in a focused pull request.
- Personal ideas belong upstream only after they are generalized into reusable,
  configurable, privacy-safe behavior.
- One-person data, preferences, paths, and workflow state stay local or in a fork.

Never push directly to `main`. After user approval, create a branch, run the full
release gate, open a pull request, and request GitHub review.
