---
description: "Run structured self-review before commit/PR"
argument-hint: [optional-plan-path]
---

# Review: Structured Self-Review

## Objective

Perform a focused self-review before commit/PR to catch bugs, regressions, missing tests, and untracked risks.

Reference checklist:
- `.ai/COMMANDS/_shared/review-checklist.md`

## Process

### 1. Gather review context

- Read active plan and `## Execution Report` (if available).
- Inspect effective diff:
  - `git diff HEAD`
  - `git diff --cached`
- Review validation evidence from `.ai/COMMANDS/validate.md` workflow.
- Review warning output from final gate commands and confirm warnings were resolved or explicitly justified.

### 2. Review findings by severity

Prioritize:
1. Correctness bugs
2. Regressions
3. Missing/weak tests
4. Risk gaps (security, migration, compatibility, performance, ops)

### 3. Resolve or document

- Fix issues immediately where feasible.
- If not fixed now, document:
  - impact
  - reason deferred
  - follow-up action

## Required Output

- Findings list ordered by severity with file references.
- Explicit statement when no findings are found.
- Residual risks/testing gaps (if any).
- Residual warnings and rationale (if any).

## Quality Bar

- No known high-severity bug/regression left unaddressed without explicit user acceptance.
- Validation evidence supports claims.
- Review output is actionable and specific.
