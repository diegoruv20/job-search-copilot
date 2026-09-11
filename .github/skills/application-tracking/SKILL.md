---
name: application-tracking
description: Maintain the local job tracker when the user reports an application, interview, rejection, withdrawal, offer, follow-up, referral, or changed next action.
---

# Application tracking

Always inspect the current record through the `job-search-copilot` MCP server
before updating it. Match by company, role, requisition, and official URL; do not
create a duplicate merely because the title differs slightly.

When the user confirms an application:

1. Use `application_record` with the actual application date.
2. Preserve the exact submitted resume and other artifacts under the user's
   gitignored application directory.
3. Record the next action and a realistic follow-up date.
4. Keep compensation, location, posting dates, and verified gaps intact.

When the user reports progression or an outcome:

1. Use `outcome_record` with the exact confirmed status and stage.
2. Include concise factual context in the status note.
3. For a pre-interview rejection, use a stage such as `Resume Screen Rejection`.
4. Never interpret silence as rejection or invent recruiter feedback.

Use `followups_due` before suggesting new outreach. Avoid parallel contact at the
same company while a recruiter or referral thread is active.
