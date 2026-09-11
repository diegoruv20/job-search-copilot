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
