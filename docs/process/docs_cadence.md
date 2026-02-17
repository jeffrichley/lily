---
owner: "@team"
last_updated: "2026-02-17"
status: "active"
source_of_truth: true
---

# Docs Cadence

Purpose: keep docs current without creating overhead or duplicate status surfaces.

## Weekly Ritual (15 minutes)

When:
- Once per week (suggested: first workday of the week).

Who:
- Single rotating owner updates docs for that week.

Steps:
1. Update `docs/dev/status.md`:
   - `Done This Week`
   - `In Progress`
   - `Next Up`
   - `Blockers and Risks`
2. Confirm each in-progress item links to one canonical source:
   - `docs/dev/roadmap.md` or
   - `docs/dev/debt_tracker.md` or
   - an active `docs/dev/*_execution_plan.md`
3. If priorities changed, update `docs/dev/roadmap.md` in the same PR.
4. If debt ownership/target/exit criteria changed, update `docs/dev/debt_tracker.md` in the same PR.
5. If a tracker becomes stale, move it to `docs/archive/` and leave a pointer stub.

Definition of done:
- `docs/dev/status.md` has current week/date and editor.
- Every active item in status is traceable to a canonical source.
- No duplicate active status tracker exists outside `docs/dev/status.md` and active execution plans.

## PR Docs-Impact Rule

Every PR must include a docs-impact decision in `.github/pull_request_template.md`:
- `No docs update needed`
- `Docs updated in this PR`
- `Docs follow-up required`

If docs follow-up is required:
- include owner and target date in the PR body
- create/update linked debt or follow-up task in canonical docs
