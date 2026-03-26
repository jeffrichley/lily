# Feature: docs-dev-cleanup-pass1

## Feature Description
Minimal-safe cleanup of `docs/dev` so current state is discoverable and tracker documents no longer contradict implementation status.

## Branch Setup
```bash
PLAN_FILE=".ai/PLANS/001-docs-dev-cleanup-pass1.md"
PLAN_SLUG="$(basename "$PLAN_FILE" .md)"
BRANCH_NAME="feat/${PLAN_SLUG}"
git show-ref --verify --quiet "refs/heads/${BRANCH_NAME}" \
  && git switch "${BRANCH_NAME}" \
  || git switch -c "${BRANCH_NAME}"
```

## Implementation Plan
- [x] Update `docs/dev/status.md` to become the running diary and fix stale Jobs entries.
- [x] Update `docs/dev/roadmap.md` with explicit role boundaries (priority/story map only).
- [x] Add `docs/dev/README.md` index mapping each doc to purpose/authority.
- [x] Reconcile execution plan lifecycle frontmatter (`active|reference|archived`).
- [x] Reconcile deferred/open checklists in `personality_execution_plan.md` and `runtime_facade_refactor_plan.md`.
- [x] Update `docs/dev/debt/debt_tracker.md` with explicit authority and review cadence.
- [x] Run docs quality gates.

## Validation Commands
- `just docs-check`

## Acceptance Criteria
- `status.md` has no stale Jobs J0 references and acts as diary.
- Completed execution plans are labeled `status: "reference"` per docs frontmatter contract.
- Roadmap clearly states it is not the execution checklist tracker.
- Debt tracker remains canonical for open engineering debt.
- `just docs-check` passes.

## Execution Report

- 2026-03-02: Updated `docs/dev/status.md` into a diary model and removed stale Jobs J0 references.
- 2026-03-02: Added `docs/dev/README.md` as the dev-doc entrypoint map.
- 2026-03-02: Added authority boundaries in roadmap, debt tracker, and execution plans.
- 2026-03-02: Reconciled execution plan lifecycle statuses to `reference` for completed trackers.
- 2026-03-02: Reconciled outstanding checklist items in personality/runtime-facade plan docs.
- 2026-03-02: Added required frontmatter to debt issue draft docs under `docs/dev/debt/issues/`.
- 2026-03-02: Validation complete via `just docs-check`.
