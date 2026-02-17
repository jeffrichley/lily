# Lily Punchlist (Archived)

Purpose: preserve the original v0 hardening checklist for historical context.

Status:
- Core punchlist work is complete.
- Open follow-on items moved to canonical trackers to avoid duplicate status drift.

Canonical trackers:
- Active debt: `docs/dev/debt_tracker.md`
- Memory migration phases/history: `docs/dev/memory_execution_plan.md`
- Feature prioritization and user-story direction: `docs/dev/roadmap.md`

Archived completion summary:
- Removed prototype hardcoding.
- Implemented real `tool_dispatch`.
- Expanded command surface (`/reload_skills`, `/help`, aliases).
- Standardized deterministic command envelope.
- Added session persistence + reload semantics.
- Added per-session execution serialization.
- Added reliability coverage (restart/snapshot/concurrency).

Former open items now tracked in debt:
- Typed skill/tool contracts.
- Real `/agent <name>` once agent subsystem exists.
