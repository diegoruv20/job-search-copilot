# Copilot workflows

## Discover your direction first

If you have not built a detailed profile, use the `career-discovery` agent before
searching. It asks a few simple questions at a time, learns your systems and major
projects, updates the private files continuously, and derives role families from
evidence rather than your current title.

See [profile onboarding](profile-onboarding.md).

## Discover and evaluate roles

Ask the `job-search-specialist` agent to search a role family, location, or company.
It checks live tracker state first, uses Playwright for external sites, verifies
the official posting, separates direct and transferable evidence from gaps, and
records viable roles through MCP.

Example:

> Find newly published backend and data-platform roles that fit my profile. Verify
> official postings, explain gaps, and add only strong candidates to the tracker.

## Prepare an application

Ask the `application-strategist` agent to prepare a tracked role. It verifies the
posting and application form, maps requirements to the private experience
inventory, creates and grades the resume, and prepares a company cheat sheet.

Example:

> Prepare the application package for job 12, but do not submit anything.

The workflow always stops before uploads, submission, or outreach.

## Draft outreach

The outreach skill checks for an existing company thread, researches credible
contacts, and drafts a concise message. It never sends messages or connection
requests.

## Practice interviews

Ask the `interview-coach` agent to prepare the next confirmed stage. Specify
whether the session is guided practice or a cold mock.

Example:

> Run a 45-minute cold system-design mock for job 12, score it, and give me a
> focused remediation plan.

## Record outcomes immediately

After applying or receiving a confirmed stage change, tell Copilot what happened.
The application-tracking skill preserves the actual date, stage, next action, and
follow-up without treating silence as an outcome.
