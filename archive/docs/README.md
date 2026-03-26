---
owner: "@jeffrichley"
last_updated: "2026-03-02"
status: "active"
source_of_truth: true
---

# Documentation Map

Purpose: provide one stable navigation system for all project docs.

## Top-Level Structure (By Purpose)

- `docs/specs/`
  - Product and technical contracts.
- `docs/dev/`
  - Execution tracking: status diary, roadmap, plans, debt, implementation references.
- `docs/ops/`
  - Operational runbooks and production-facing procedures.
- `docs/adr/`
  - Architecture decision records.
- `docs/process/`
  - Team process and governance.
- `docs/archive/`
  - Historical/superseded material.

## Canonical Sources

| Concern | Canonical file |
|---|---|
| Current work diary | `docs/dev/status.md` |
| Priority and sequencing | `docs/dev/roadmap.md` |
| Active/deferred execution checklists | `docs/dev/plans/` |
| Open engineering debt | `docs/dev/debt/debt_tracker.md` |
| Debt issue drafts | `docs/dev/debt/issues/` |
| Dev reference material | `docs/dev/references/` |
| Active specs index | `docs/specs/README.md` |
| Archive index | `docs/archive/README.md` |

## Lifecycle Model

Use frontmatter status for document lifecycle (not folder churn):
- `active`: currently maintained.
- `reference`: useful historical/closed execution tracker.
- `archived`: retired and moved to archive domain.

Execution phase state (`planned`, `in_progress`, `done`, `deferred`) should live inside plan/checklist content, not as folder names.

## Non-Negotiables

- Do not create status-based top-level directories (for example `planned/`, `in-progress/`, `complete/`).
- Keep one canonical source per concern.
- Keep links updated when paths change.
- All docs under `docs/` require valid frontmatter.

## Quality Gate

- `just docs-check`
