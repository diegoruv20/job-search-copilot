# Build your profile through a guided interview

Do not start by filling every blank in the templates. The strongest profile comes
from a conversation in which Copilot learns how your job actually works, follows
up on important details, and helps you recognize transferable experience.

## Start the interview

From Copilot CLI in this repository:

> Use the career-discovery agent. Interview me to build my job-search profile and
> experience inventory. Ask three to five simple questions at a time, update the
> files after every round, and help me identify realistic role families and
> positioning. Do not assume I already know which titles fit me.

Copilot should check `profile_status` first and resume from existing information.

## The interview stages

1. **Motivation:** why you may leave and what a better job means.
2. **Career timeline:** employers, official titles, teams, products, and users.
3. **System map:** what your systems do and how information or requests flow.
4. **Project inventory:** the major things you built, changed, fixed, or led.
5. **Deep dives:** personal ownership, decisions, technology, scale, metrics,
   rollout, operations, collaborators, and lessons.
6. **Skills depth:** direct production experience, supporting experience,
   transferable concepts, and genuine gaps.
7. **Leadership and stories:** ambiguity, disagreement, failure, mentoring,
   incidents, prioritization, and customer impact.
8. **Constraints:** location, compensation, work style, schedule, on-call, company
   types, ethics, and non-negotiables.
9. **Role synthesis:** strongest roles, adjacent roles, stretch paths, and several
   evidence-backed positionings.
10. **Validation:** you correct the final summary before the files become ready.

The assistant should not mechanically finish one stage if an answer reveals a
high-value follow-up. It should still keep each round small and easy to answer.

## What good answers look like

Rough language is better than polished language:

> We had a batch job that usually took three hours. I found one customer caused
> most of the join skew, tried salting, and rolled it out gradually. I think it
> dropped to about 35 minutes, but I need to verify that.

That answer gives Copilot useful follow-ups:

- Was the user the person who diagnosed and implemented the change?
- What data volume and production impact were involved?
- How was correctness validated?
- Is 35 minutes measured or remembered?
- Did other engineers contribute?

Copilot should preserve uncertainty until resolved rather than silently turning it
into an exact resume metric.

## How the original workflow was developed

The workflow was proven through a multi-round career interview:

1. Start with the person's normal work and what they wanted from the next job.
2. Learn the product and end-to-end system before discussing job titles.
3. Inventory several years of projects because the person did not know which work
   would be transferable.
4. Deep-dive one project at a time, especially performance work, migrations,
   platform architecture, operations, and newer market-relevant work.
5. Quantify scale and outcomes while keeping every metric attached to its project.
6. Separate individual contribution from team results and technical leadership
   from formal management.
7. Translate the accumulated evidence into several role families and resume
   positionings.
8. Reuse the same factual inventory for resumes, LinkedIn, behavioral stories, and
   interview preparation.

This repository generalizes that method without including the original user's
private work history.

## Updating later

Use the same interview process rather than rewriting the files from scratch:

> I remembered another major project. Interview me about it and add only confirmed
> evidence to my experience inventory.

> My location and on-call preferences changed. Update my profile and tell me how
> that changes the search.

> Recruiters keep asking about a skill I have not documented. Probe my actual
> experience and decide whether it is direct, transferable, or a gap.

Run `tracker_cli.py doctor` or call `profile_status` to see whether the files exist,
their interview status, and unresolved follow-ups.
