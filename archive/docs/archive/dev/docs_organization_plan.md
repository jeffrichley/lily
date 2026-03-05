---
owner: "@team"
last_updated: "2026-02-17"
status: "archived"
source_of_truth: false
---

# Docs Organization Plan

Purpose: establish a lean docs operating system with clear ownership and minimal duplication.

## Phase 1: Canonical Map and Guardrails

`Acceptance criteria`
- [x] Canonical map exists in `docs/README.md` with concern-to-doc mapping.
- [x] Weekly status template exists in `docs/dev/status.md`.
- [x] Frontmatter standard is defined and applied to core source-of-truth docs.

`Non-goals`
- No broad content rewrites.
- No roadmap reprioritization.
- No archive migration yet.

`Required tests and gates`
- [x] Links in canonical docs resolve.
- [x] No duplicate active status trackers claim canonical status.

## Phase 2: Consolidate Current State

`Acceptance criteria`
- [x] Active work is traceable from `docs/dev/status.md` to execution plan and roadmap/debt.
- [x] Outdated status trackers are moved to `docs/archive/` with pointer stubs.
- [x] `docs/dev/roadmap.md` retains explicit split between user-visible and internal engineering work.

`Non-goals`
- No change to feature priority values unless explicitly requested.

`Required tests and gates`
- [x] Three random work items are traceable to a canonical source in under 30 seconds.
- [x] Archived docs do not present themselves as active status sources.

## Phase 3: Operating Cadence

`Acceptance criteria`
- [x] Weekly 15-minute docs update ritual is documented and followed.
- [x] PR template includes docs-impact checks.

`Non-goals`
- No automation in this phase.

`Required tests and gates`
- [x] Two consecutive weekly status updates completed.
- [x] New PRs include docs-impact decisions.

Phase 3 gate note:
- Closed by explicit owner/user decision on `2026-02-17` to avoid artificial wait-time.

## Phase 4: Light Automation

`Acceptance criteria`
- [x] CI gate validates frontmatter presence on all docs markdown files.
- [x] CI gate detects stale `last_updated` on active docs.

`Non-goals`
- No docs platform migration.

`Required tests and gates`
- [x] CI catches intentionally stale active doc fixture.
- [x] Zero false positives on current docs tree.

Phase 4 gate note:
- Frontmatter was auto-added across all docs with placeholders where missing.
- Placeholder values were replaced with concrete `owner` and `last_updated` values.
- `just quality-check` now passes with docs validation enabled.
