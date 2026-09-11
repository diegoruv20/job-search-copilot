---
name: profile-onboarding
description: Interview a user in short, systematic rounds to build and maintain an evidence-rich job-search profile and experience inventory, then derive realistic role families and positioning.
---

# Guided career and experience discovery

Use this skill when either private profile file is missing, incomplete, stale, or
the user wants to reconsider their direction. Do not hand the user a long form and
ask them to fill it alone.

## Core method

Interview in short rounds of three to five simple questions. Rough answers are
acceptable. After every round:

1. Summarize what was learned in plain language.
2. Distinguish confirmed facts, tentative interpretations, and unresolved details.
3. Update `local/user_profile.md` and `local/experience_inventory.md`.
4. Explain what the evidence may imply about transferable work or role families.
5. Ask only the next highest-value follow-ups.

Do not ask questions already answered in the files. Do not polish a claim before
understanding personal contribution, context, and evidence.

## Interview sequence

### 1. Motivation and definition of better

Learn why the user is considering a change, what they want to preserve, what they
want to escape, and what success would look like. Do not begin by forcing them to
choose job titles.

Simple prompts:

- What do you do in a normal week?
- Which parts do you enjoy most and least?
- Why are you considering leaving?
- What would make a new job meaningfully better?

### 2. Career timeline and current system

Build a factual timeline of employers, official titles, teams, products, users,
and responsibilities. Ask the user to explain systems in ordinary language before
requesting resume wording.

Prompts:

- What does your team or product do?
- Who uses it?
- What happens from input to output?
- Which parts are specifically yours?

### 3. Project inventory and triage

List meaningful projects from the last several years. Quickly classify each by
technical difficulty, ownership, scale, impact, leadership, recency, and relevance.
Deep-dive the strongest and most distinctive projects first.

### 4. Project deep dives

For each selected project, resolve:

- The original problem and why it mattered
- The user's exact assignment and personal contribution
- Architecture, implementation, and key decisions
- Alternatives considered and tradeoffs
- Languages, infrastructure, data stores, and tools actually used
- Scale, latency, reliability, cost, adoption, security, or business context
- Measurement source and whether metrics are exact or approximate
- Testing, validation, migration, rollout, rollback, and production operation
- Team contribution versus individual ownership
- Cross-team influence, mentoring, and technical leadership
- What failed, changed, or was learned

Never attach a system-wide metric to the wrong project or imply sole ownership of
a team result.

### 5. Skills depth and transferability

For important skills, classify:

- Strong production evidence
- Working or supporting experience
- Prototype, coursework, or old experience
- Transferable or analogous experience
- Genuine gap

Ask what the user personally built with each technology, how recently, at what
depth, and in what environment. Similar concepts are useful evidence but are not
the same technology.

### 6. Leadership and behavioral evidence

Gather examples of architecture ownership, ambiguity, disagreement, failure,
incidents, prioritization, mentoring, customer focus, difficult tradeoffs, and
delivery under constraints. Preserve factual story components and multiple
question mappings instead of inventing polished anecdotes.

### 7. Constraints and preferences

Resolve location, authorization, compensation, schedule, office cadence, travel,
on-call tolerance, company stage, industries, ethics, pace, title flexibility, and
application strategy. Separate hard constraints from preferences and recruiter
questions.

### 8. Role hypotheses and positioning

Derive roles from demonstrated work, not title matching. Produce:

- Three strongest role families
- Two or three credible adjacent families
- Stretch paths and the evidence or learning needed
- Roles to avoid or treat cautiously
- Primary, secondary, and stretch positioning statements

For each role family, explain:

| Role family | Supporting evidence | Transferable evidence | Gaps | Likely level | Search terms |
|---|---|---|---|---|---|

Test several framings of the same evidence, such as backend, data, platform,
infrastructure, security, developer tools, or AI infrastructure. Do not lock the
user into the title they already know.

### 9. Validation playback

Read back the career timeline, strongest evidence, metrics, role hypotheses,
constraints, and prohibited claims. Ask the user to correct inaccuracies. Mark
both files `ready` only after this review.

## Maintaining the files

Update the inventory when the user remembers a project, corrects a metric, explains
a contribution, receives recruiter feedback, or develops a new skill. Update the
profile when goals, constraints, compensation, target roles, or lifestyle
preferences change.

Never replace confirmed detail with shorter generic wording. Preserve the inventory
as the long factual source and select from it for resumes, LinkedIn, and interviews.
