---
description: "Synchronize status surfaces and validate docs/status output"
argument-hint: [optional-plan-path]
---

# Status Sync: Keep Status Surfaces Trustworthy

## Objective

Run a deterministic status maintenance loop so `just status` stays accurate and docs validation remains green.

## Inputs

- Optional active plan path (for example `.ai/PLANS/006-status-sync-system.md`)
- Files changed in the current phase/session

## Required Steps

1. Update canonical status docs impacted by the phase:
   - `docs/dev/status.md` (`## Current Focus`, `## Recently Completed`, `## Diary Log`)
   - `docs/dev/roadmap.md` (only when priority/order changed)
   - `docs/dev/debt/debt_tracker.md` (only when debt created/closed/retargeted)
2. Update `last_updated` frontmatter date for each changed canonical doc.
3. Update plan progress state in all relevant plan trackers:
   - `.ai/PLANS/*.md` (implementation plans)
   - `docs/dev/plans/*_execution_plan.md` (domain execution plans), when impacted
4. Validate docs metadata and staleness:
   - `just docs-check`
5. Smoke-check status output:
   - `just status`

## Current Focus Quality Criteria

Use these rules whenever `## Current Focus` is edited in `docs/dev/status.md`.

1. Selection scope:
   - Include only items expected to be actively executed in the next 3-7 days.
   - Keep 2-4 bullets maximum.
   - Every bullet must map to a canonical source (`docs/dev/roadmap.md`, `docs/dev/debt/debt_tracker.md`, or a specific plan path).
   - If any open `P1` debt exists, include at least one `P1` debt outcome from `docs/dev/debt/debt_tracker.md`.
   - AI agents must not add `P2`/`P3` debt items unless a human explicitly prioritizes that exact item for current focus.
2. Bullet quality:
   - Write each bullet as `outcome + source path`.
   - Prefer concrete outcomes ("close P1 decode failure path") over activity labels ("work on docs").
3. Freshness:
   - On each phase completion, either keep and advance the same bullet or replace it with the next active item.
   - If a focus item remains unchanged for 7+ days, add an explicit blocker rationale in `## Diary Log`.
4. Non-goals:
   - Do not list already completed work.
   - Do not list long-horizon ideas that are not in active execution.
   - Do not mix internal implementation detail into user-visible feature bullets.
5. Validation:
   - If `## Current Focus` changes, update `last_updated` in the same edit.
   - Run `just docs-check` and `just status` after edits.

## Evidence to Report

- Which docs/plans were updated (paths)
- `just docs-check` -> pass/fail
- `just status` -> pass/fail

## Completion Criteria

- Canonical status docs reflect current phase outcome.
- Relevant plan checklists are updated.
- Docs validation passes.
- Status command renders without errors.
