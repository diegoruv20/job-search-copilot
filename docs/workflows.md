# Portable agent workflows

The workflow playbooks under `.github/skills/` are plain Markdown. GitHub Copilot
CLI can discover them as skills; any other agent can read the same files directly.
Always start with `AGENTS.md`, connect the tracker and Playwright MCP servers, and
then select the playbook matching the user's goal.

## Discover your direction first

Read `.github/skills/profile-onboarding/SKILL.md`. If the private profile is
incomplete, interview the user in short rounds, update the files continuously,
and derive role families from evidence rather than the current title.

> Read `AGENTS.md` and the profile-onboarding workflow. Interview me three to five
> questions at a time, maintain my private profile and evidence inventory, and
> help me validate realistic role families.

## Discover and evaluate roles

Read `.github/skills/job-search/SKILL.md` and
`.github/skills/application-tracking/SKILL.md`. Inspect live tracker state first,
verify official postings with Playwright, separate direct and transferable
evidence from gaps, and persist viable roles through MCP.

> Read the job-search workflow. Find newly published backend and data-platform
> roles that fit my profile, verify official postings, explain gaps, and add only
> strong candidates to the tracker.

## Prepare an application

Read `.github/skills/resume-making/SKILL.md`. Reverify the posting and application
form, map requirements to the private inventory, create and grade the resume, and
prepare a company cheat sheet.

> Read the resume-making workflow and prepare the application package for job 12,
> but do not upload or submit anything.

## Draft outreach

Read `.github/skills/outreach/SKILL.md`. Check for an existing company thread,
research credible contacts, and draft a concise message. Never send it.

> Read the outreach workflow, find the strongest credible contact for job 12, and
> draft a message for me to send manually.

## Practice interviews

Read `.github/skills/interview-prep/SKILL.md`. Start from the tracked role,
official posting, current stage, and confirmed evidence. Run realistic timed
practice with explicit scoring and targeted remediation.

> Read the interview-prep workflow and run a 45-minute cold system-design mock for
> job 12. Score it and give me a focused remediation plan.

## Record outcomes immediately

Read `.github/skills/application-tracking/SKILL.md` whenever the user reports an
application, interview, rejection, withdrawal, offer, referral, or changed next
action. Preserve the actual date and never infer outcomes from silence.

> Read the application-tracking workflow. I applied today using the final resume;
> update the tracker and set the next follow-up.

## Customize the product

Read `.github/skills/safe-customization/SKILL.md` before changing design,
workflows, schema, setup, or features. Preserve private data and existing
behavior, inspect all affected surfaces, and run the full release gate.

> Read the safe-customization workflow and add a weekly planning view without
> breaking my current data or workflow.

Copilot users may select the matching named agent under `.github/agents/`.
Other clients can create equivalent personas from these prompts or use a
general-purpose agent with the relevant playbook.
