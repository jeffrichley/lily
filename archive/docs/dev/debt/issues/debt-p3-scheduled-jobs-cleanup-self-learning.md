---
owner: "@jeffrichley"
last_updated: "2026-03-02"
status: "active"
source_of_truth: false
---

# [Debt][P3] Add scheduled jobs for run-artifact cleanup and self-learning pipelines

## Source
- Debt tracker: `docs/dev/debt/debt_tracker.md` (Active Debt → P3)

## Internal engineering tasks
- Define and implement cleanup job spec + retention policy.
- Define self-learning cadence + safety gates.
- Provide runbook for enable/disable and observability.

## User-visible features
- None.

## Acceptance criteria
- Explicit cleanup job spec and retention policy implemented.
- Explicit self-learning cadence and safety gates defined.
- Runbook covers operational controls and observability.

## Non-goals
- Shipping new end-user product capabilities unrelated to scheduling.
- One-off manual cleanup scripts as final solution.

## Required tests and gates
- Job scheduling/integration tests.
- Operational runbook validation checklist.
- `just quality test` warning-clean.

## Metadata
- Priority: `P3`
- Owner: `@jeffrichley`
- Target: `TBD`
