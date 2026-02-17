---
owner: "@team"
last_updated: "2026-02-17"
status: "active"
source_of_truth: true
---

# Documentation Map

Purpose: keep documentation useful, minimal, and non-duplicative.

## Canonical Documents

Use these files as the only source of truth for each concern:

| Concern | Canonical file |
|---|---|
| Weekly/current status (`done`, `in progress`, `next`, `risks`) | `docs/dev/status.md` |
| Product direction and prioritization | `docs/dev/roadmap.md` |
| Open technical debt and cleanup obligations | `docs/dev/debt_tracker.md` |
| Memory domain phase execution status | `docs/dev/memory_execution_plan.md` |
| Personality domain phase execution status | `docs/dev/personality_execution_plan.md` |
| Process and workflow rules | `docs/process/process.md` |
| Docs weekly operating cadence | `docs/process/docs_cadence.md` |
| This docs governance rollout plan | `docs/dev/docs_organization_plan.md` |
| Historical docs index | `docs/archive/README.md` |

## Promotion Rules

- `ideas/` is incubation only; no active status lives there.
- A document becomes active only when linked from this file.
- Completed phase reports and obsolete trackers move to `docs/archive/` with a short pointer note.
- Pointer stubs may remain at the original path, but must clearly link to archived location and canonical active docs.

## Frontmatter Standard

All docs under `docs/` must start with:

```yaml
---
owner: "@team-or-handle"
last_updated: "YYYY-MM-DD"
status: "active|reference|archived"
source_of_truth: true|false
---
```

Field rules:
- `owner`: accountable maintainer.
- `last_updated`: set in the same PR as material edits.
- `status`: lifecycle state.
- `source_of_truth`: only one `true` doc per concern.

## Quality Gates

- Links in canonical docs must resolve.
- Every `docs/**/*.md` file must have frontmatter with non-placeholder values.
- Docs frontmatter validation runs in CI via `just quality-check` (`docs-check` target).
- Active status updates happen only in `docs/dev/status.md` and active execution plans.
- If two active docs claim authority for the same concern, this map must be corrected before merge.
