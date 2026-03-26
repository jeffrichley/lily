---
owner: "@jeffrichley"
last_updated: "2026-03-02"
status: "active"
source_of_truth: true
---

# Dev Docs Index

Purpose: make development tracking and execution state easy to find without duplication.

## Directory Layout

- `docs/dev/status.md`
  - Running diary for current focus, recent completions, and risks.
- `docs/dev/roadmap.md`
  - Priority/story ordering and long-range sequencing.
- `docs/dev/plans/`
  - Domain execution plans with checklists and gates.
- `docs/dev/debt/`
  - Debt tracker and debt issue drafts.
- `docs/dev/references/`
  - Implementation references and authoring guidance.

## How To Use

- Looking for what changed recently:
  - read `status.md`
- Looking for what to prioritize next:
  - read `roadmap.md`
- Looking for implementation progress inside a domain:
  - read files in `plans/`
- Looking for unresolved engineering cleanup:
  - read `debt/debt_tracker.md`
- Looking for one-command summary:
  - run `just status`

## Authority Boundaries

This index is authoritative for:
- where each development concern lives in `docs/dev`

This index is not authoritative for:
- feature priorities (`roadmap.md`)
- execution checklist truth (`plans/*`)
- debt ownership and closure criteria (`debt/debt_tracker.md`)
