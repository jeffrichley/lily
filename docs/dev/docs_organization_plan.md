---
owner: "@team"
last_updated: "2026-02-17"
status: "active"
source_of_truth: true
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
- [ ] Active work is traceable from `docs/dev/status.md` to execution plan and roadmap/debt.
- [ ] Outdated status trackers are moved to `docs/archive/` with pointer stubs.
- [ ] `docs/dev/roadmap.md` retains explicit split between user-visible and internal engineering work.

`Non-goals`
- No change to feature priority values unless explicitly requested.

`Required tests and gates`
- [ ] Three random work items are traceable to a canonical source in under 30 seconds.
- [ ] Archived docs do not present themselves as active status sources.

## Phase 3: Operating Cadence

`Acceptance criteria`
- [ ] Weekly 15-minute docs update ritual is documented and followed.
- [ ] PR template includes docs-impact checks.

`Non-goals`
- No automation in this phase.

`Required tests and gates`
- [ ] Two consecutive weekly status updates completed.
- [ ] New PRs include docs-impact decisions.

## Phase 4: Light Automation

`Acceptance criteria`
- [ ] CI gate validates frontmatter presence on active docs.
- [ ] CI gate detects stale `last_updated` on active docs.

`Non-goals`
- No docs platform migration.

`Required tests and gates`
- [ ] CI catches intentionally stale active doc fixture.
- [ ] Zero false positives on current canonical docs.
