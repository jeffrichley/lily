# Status Surfaces Reference

Purpose: define ownership and update expectations for status-related docs and trackers.

## Canonical Surfaces

- `docs/dev/status.md`
  - owns: current focus, diary timeline, recently completed snapshot
  - update when: a phase completes or active focus changes

- `docs/dev/roadmap.md`
  - owns: priority/order and user-facing feature sequencing
  - update when: priority or ordering decisions change

- `docs/dev/debt/debt_tracker.md`
  - owns: debt inventory, ownership, target dates, exit criteria
  - update when: debt is created, closed, re-scoped, or retargeted

- `.ai/PLANS/*.md`
  - owns: implementation-phase checklist state + execution reports
  - update when: plan tasks/phase outcomes change

- `docs/dev/plans/*_execution_plan.md`
  - owns: domain execution checklists and lifecycle state
  - update when: domain-plan phase state changes

## Required Sync Loop

After each completed implementation phase:
1. update affected plan tracker(s)
2. update `docs/dev/status.md` diary/completed/focus as needed
3. update roadmap/debt only when their authority domain changes
4. run:
   - `just docs-check`
   - `just status`

## Current Focus Quality Rules

- keep 2-4 active bullets
- each bullet must map to a canonical source path
- use outcome language, not vague activity labels
- if unchanged for 7+ days, document blocker rationale in diary
