# Contributing

Contributions are welcome. Fixes and broadly useful features should arrive through
a GitHub pull request so they can be validated and reviewed without exposing
anyone's private job-search data.

## Decide whether the change belongs upstream

Classify the proposed work before editing.

### Universal fix

Submit upstream when the change corrects behavior that is wrong for everyone:

- Data loss, corruption, unsafe replacement, or migration defects
- Broken tracker, REST, MCP, setup, import/export, or dashboard behavior
- Security, privacy, accessibility, portability, or reliability problems
- Incorrect documentation or missing validation
- Regressions covered by the repository's existing product contract

### Shared feature

A personal idea can become a shared feature when it is generalized. Submit it
upstream when:

- A meaningful group of users could benefit
- The behavior is configurable or opt-in when preferences differ
- Defaults remain useful for a new user with a blank database
- It contains no personal companies, paths, resume content, scoring assumptions,
  credentials, or private workflow state
- Existing databases and workflows remain compatible
- REST, MCP, dashboard, setup, portability, documentation, and tests stay in sync

Examples include configurable scoring weights, optional planning views, reusable
reminder rules, new export formats, or accessibility improvements.

### Personal customization

Keep the change local or in your own fork when it encodes one person's:

- Profile, experience, applications, resumes, contacts, or compensation
- Preferred employers, excluded companies, role rankings, or outreach state
- Absolute paths, local tool locations, or machine-specific secrets
- One-off dashboard layout or workflow that cannot be generalized cleanly

Private content belongs under ignored paths such as `local/`, `instance/`,
`backups/`, and `exports/`. Do not add it to a pull request.

If classification is unclear, open a feature request describing the underlying
user need. Maintainers can help decide whether to generalize it.

## Pull request workflow

1. Fork the repository or create a branch from the latest `main`.
2. Inspect existing architecture, tests, and related issues before editing.
3. Load the `safe-customization` skill for product, workflow, schema, or design
   changes.
4. Make one coherent change. Do not combine personal customization with an
   upstream fix.
5. Add or update tests and documentation.
6. Run:

   ```powershell
   .\.venv\Scripts\python.exe scripts\release_check.py
   ```

7. Inspect `git diff` and confirm no private files or generated artifacts are
   staged.
8. Push the branch and open a pull request against `main`.
9. Complete the pull-request template, including classification, user benefit,
   compatibility, privacy, and validation evidence.
10. Address GitHub checks and review comments before merge.

For dashboard changes, include desktop and mobile verification. For MCP changes,
document the typed contract. For schema changes, include an idempotent upgrade
test using temporary data.

## Agent instructions

An automated coding agent may prepare a branch and pull request only when the user
has approved publishing the change. It must:

- Never push directly to `main`
- Never include ignored or private data
- Classify the change as a universal fix, shared feature, or personal customization
- Generalize personal ideas before proposing them upstream
- Stop if tests fail or product-scope decisions remain unresolved
- Provide a factual PR description and request maintainer review

Agents should use GitHub's pull-request review workflow rather than treating a
successful local test as permission to merge.

## Review criteria

Reviewers evaluate:

- Is the change broadly useful or appropriately configurable?
- Does it preserve local-first, single-user privacy?
- Are existing databases and blank first runs safe?
- Do services, REST, MCP, dashboard, setup, and portability remain consistent?
- Are errors explicit and user-facing states accessible?
- Do tests verify the actual behavior and regression?
- Is the implementation understandable and maintainable?

Small, focused pull requests are easier to review and safer to merge.
