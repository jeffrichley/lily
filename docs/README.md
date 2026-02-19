---
owner: "@team"
last_updated: "2026-02-18"
status: "active"
source_of_truth: true
---

# Documentation Map

Purpose: keep documentation useful, minimal, and non-duplicative.

## Allowed Top-Level Directories

Only these directories should exist directly under `docs/`:
- `docs/dev`
- `docs/process`
- `docs/specs`
- `docs/adr`
- `docs/ops`
- `docs/archive`

## Canonical Documents

Use these files as the only source of truth for each concern:

| Concern | Canonical file |
|---|---|
| Weekly/current status (`done`, `in progress`, `next`, `risks`) | `docs/dev/status.md` |
| Product direction and prioritization | `docs/dev/roadmap.md` |
| Open technical debt and cleanup obligations | `docs/dev/debt_tracker.md` |
| Memory domain phase execution status | `docs/dev/memory_execution_plan.md` |
| Personality domain phase execution status | `docs/dev/personality_execution_plan.md` |
| Skills platform phase execution status | `docs/dev/skills_platform_execution_plan.md` |
| Skills tool authoring workflow | `docs/dev/skills_tool_authoring.md` |
| Skills platform exercise runbook | `docs/ops/skills_platform_v1_exercise_guide.md` |
| Blueprints contract (V0) | `docs/specs/blueprints/blueprint_spec_v0.md` |
| Jobs contract (V0) | `docs/specs/jobs/job_spec_v0.md` |
| Blueprints + jobs architecture (V0) | `docs/specs/blueprints/blueprints_jobs_architecture_v0.md` |
| Blueprints phase execution status | `docs/dev/blueprints_execution_plan.md` |
| Jobs phase execution status | `docs/dev/jobs_execution_plan.md` |
| Blueprints + jobs operations runbook | `docs/ops/blueprints_jobs_runbook_v0.md` |
| Blueprints/jobs GoF + LangChain/LangGraph implementation guide | `docs/dev/blueprints_jobs_langgraph_langchain_patterns.md` |
| Process and workflow rules | `docs/process/process.md` |
| Docs weekly operating cadence | `docs/process/docs_cadence.md` |
| Active specs index | `docs/specs/README.md` |
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
