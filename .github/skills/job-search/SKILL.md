---
name: job-search
description: Discover, verify, rank, deduplicate, and track job opportunities using the live tracker, Playwright, official postings, and the user's private profile.
---

# Evidence-first job search

## Start with live state

Call `stats_get`, `followups_due`, and `recommendations_get`. Search existing jobs
before adding anything. Read `local/user_profile.md` and
`local/experience_inventory.md`; if either is missing or incomplete, ask focused
questions before making personalized claims.

## Discovery

Search several relevant role families and responsibility keywords, not only one
title. Use Playwright on human-facing job sites. Treat aggregators and social
networks as discovery sources, not final authority.

## Official verification

Open every promising role on the employer's careers site or official ATS. Record:

- Active or closed status
- Exact company, title, team, requisition, and official URL
- Original publication date
- Last substantive update date
- Repost or promotion date separately
- Verification date and confidence
- Location eligibility and office expectations
- Base compensation versus total compensation
- Required versus preferred qualifications
- Responsibilities and likely first-year outcomes
- On-call, incident response, support, travel, and application limits

If original publication cannot be verified, record it as unknown. Never reset age
from a repost.

## Fit analysis

Classify each requirement as:

- Direct evidence
- Transferable evidence
- Genuine gap
- Unknown requiring recruiter confirmation

Hard-screen inactive postings, unsupported locations, clearly inadequate
compensation, unrealistic mandatory specialization, and duplicate applications
that could harm active candidacy. Otherwise rank using the user's private profile:
technical match, scope, work preferences, compensation, location, operational
risk, and product interest.

## Persistence and reporting

Use `job_create` or `job_update` only after official verification. Include a
specific next action and date. Report newly published roles before updated or older
roles, explain real gaps, and list the sources reviewed.

Do not submit applications, save jobs on external sites, or contact anyone.
