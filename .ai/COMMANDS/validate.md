---
description: "Run coding validation workflow (tests, quality checks, and feature smoke validation)"
argument-hint: [optional-plan-path]
---

# Validate: Prove The Change Works

## Objective

Run the project validation workflow in a consistent order and capture evidence that code is correct, safe, and ready for commit/push.

Use this command as the canonical validation reference from other workflows.

## Inputs

- Optional: active plan path (for example `.ai/PLANS/007-some-feature.md`)
- If provided, include all plan-specific validation/smoke commands in addition to baseline checks.

## Validation Order

### Level 0: Environment sanity

- Confirm tools are available:
  - `uv --version`
  - `just --version`

### Level 1: Fast local confidence

- `just lint`
- `just format-check`
- `just types`
- `just docs-check`
- `just test`

Use this level during development loops.

### Level 2: Full quality gate

- Preferred final gate:
  - `just quality && just test`

Use one of the above before commit/PR handoff.

### Level 3: Feature-specific validation

Run all validation commands defined in the active plan:
- unit/integration tests
- smoke/e2e checks
- artifact or API verification commands

For user-visible outputs, include proof commands (examples):
- file/artifact checks (`ls`, `test -f`)
- status/report checks (`just status`, `just status-ready`)
- targeted pytest invocation for changed areas (`uv run pytest tests/<area> -q`)

## Failure Handling

- If a command fails:
  - fix the issue
  - re-run that command
  - continue only when it passes
- Do not claim completion with known failing validation unless explicitly accepted by the user.

## Warning Handling

- Treat warnings as actionable by default.
- Resolve warnings whenever feasible, especially from security/lint/type tooling.
- If a warning cannot be removed safely, document:
  - why it remains
  - why it is acceptable for now
  - follow-up action (or add to `docs/dev/debt/debt_tracker.md` with a `DEBT-XXX` ID)
- Do not ignore warning-heavy output during final gate checks.

## Parallel Fix Policy

When remediating validation failures, parallelization is allowed only for single-file-safe fixes.

Allowed parallel category:
- single-file lint/format nits where each fix is isolated to one file and does not change shared types/contracts.

Required serialized categories:
- typecheck failures (`mypy`, `pyright`, protocol/type contract issues)
- test failures (unit/integration/smoke)
- any issue requiring edits across multiple files/modules
- dependency, build, config, or shared-interface changes

Execution rule:
- batch and fix single-file-safe lint/format issues in parallel
- re-run lint/format checks
- then handle remaining failures sequentially by dependency order
- finish with full validation rerun

## Required Output Evidence

Report validation results with command + outcome:
- `command` -> `pass/fail` (+ key output line when relevant)

For user-visible features, include:
- exact artifact/surface verified
- exact verification command run

## Recommended Command Set (This Repo)

- `just lint`
- `just format-check`
- `just types`
- `just docs-check`
- `just test`
- `just quality && just test` (required final gate)

Project-specific examples:
- `just status-ready`
- `just test-cov`

## Completion Criteria

- Baseline checks pass (or documented, user-approved exception).
- Plan-required validation commands pass.
- Final big-check gate passes (`just quality && just test`).
- Warnings are addressed where feasible, with explicit documentation for any accepted residual warnings.
- Evidence is captured in execution summary and/or plan `## Execution Report`.
