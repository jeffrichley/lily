# Human Runbook: Cursor Slash Command Flow

This is the human-facing lifecycle for the rebooted `.cursor/commands` wrappers.

Canonical lifecycle:

- `/start -> /plan -> (/work -> /phase-close)* -> /plan-close`

Wrappers stay minimal by design and defer procedure details to `.ai/COMMANDS/*`.

## Canonical Command Order (Idea -> Main -> Usable)

### A) Session bootstrap
1. `/start`
   - Canonical: `../../.ai/COMMANDS/prime.md`

### B) Plan and intent lock
2. `/plan`
   - Canonical: `../../.ai/COMMANDS/create-prd.md`, `../../.ai/COMMANDS/plan.md`, `../../.ai/COMMANDS/phase-intent-check.md`
   - Required gate: PRD must exist at `.ai/SPECS/<NNN>-<feature>/PRD.md`.

### C) Phase loop (repeat for each phase)
3. `/work`
   - Canonical: `../../.ai/COMMANDS/execute.md`, `../../.ai/COMMANDS/status-sync.md`
4. `/phase-close`
   - Canonical: `../../.ai/COMMANDS/validate.md`, `../../.ai/COMMANDS/review.md`, `../../.ai/COMMANDS/commit.md`, `../../.ai/COMMANDS/push.md`
   - Gate order: `validate -> review -> commit -> push`
   - Stop condition: stop on first failed gate.
   - Constraint: must not create/update PR.

### D) Plan completion
5. `/plan-close`
   - Canonical: `../../.ai/COMMANDS/pr.md`, `../../.ai/COMMANDS/handoff.md`
   - Precondition: all plan phases complete.

## Optional Commands (not in the per-phase close path)

- `/release-notes` -> `../../.ai/COMMANDS/release-notes.md`
- `/retro` -> `../../.ai/COMMANDS/retro.md`
- `/tech-debt` -> `../../.ai/COMMANDS/tech-debt.md`
- `/audit-tests` -> `../../.ai/COMMANDS/check_tests.md`

## Definition of Done

- Every planned phase has been closed via `/phase-close`.
- `/plan-close` has been executed (PR prepared + handoff written).
- Required validation evidence is present in commit/PR artifacts.
