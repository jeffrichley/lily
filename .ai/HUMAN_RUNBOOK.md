# Human Runbook: Command Order and Cadence

This is for humans operating AI sessions in this repo.

Use these commands in this order from idea to merged/usable work.

## Canonical Command Order (Idea -> Main -> Usable)

### A) Idea and scoping
1. `.ai/COMMANDS/prime.md`
2. Optional: `.ai/COMMANDS/create-prd.md` (default output: `.ai/SPECS/<NNN>-<feature>/PRD.md`)
3. `.ai/COMMANDS/plan.md` -> write `.ai/PLANS/<NNN>-<feature>.md`
4. Ensure the plan contains `## Branch Setup` commands (plan-derived branch name) and per-phase `Intent Lock` blocks.

### B) Build and verify
5. For each implementation phase: `.ai/COMMANDS/phase-intent-check.md <plan> "<phase-heading>"`
6. `.ai/COMMANDS/execute.md <plan>` (executes `## Branch Setup` first)
7. `.ai/COMMANDS/validate.md`
8. `.ai/COMMANDS/review.md`

### C) Record and publish
9. `.ai/COMMANDS/commit.md`
10. `.ai/COMMANDS/push.md`
11. `.ai/COMMANDS/pr.md`

### D) Finish and operationalize
12. `.ai/COMMANDS/handoff.md` (required if work remains; recommended always)

If any of the following create/modify tracked files, run them BEFORE step 8 so changes are included in the same branch/PR:
- `.ai/COMMANDS/release-notes.md`
- `.ai/COMMANDS/retro.md`
- `.ai/COMMANDS/tech-debt.md`

If run AFTER step 10 and they produce tracked changes, commit/push them as:
- a follow-up commit on the same open PR, or
- a separate follow-up PR (preferred after merge to `main`)

## Definition of Done (Usable on Main)

- Merged to `main`
- Validation evidence captured
- Required docs/workflow updates included
- Release notes generated when applicable

## Notes on Artifact-Producing Commands

- `handoff.md` is usually session output and may not require a commit unless it updates tracked docs.
- `release-notes.md`, `retro.md`, and `tech-debt.md` often update tracked markdown files.
- Any tracked file changes must be committed and pushed to be visible in git/PR.

## Periodic Cadence

- Every session start:
  - `.ai/COMMANDS/prime.md`
- Before each implementation phase starts:
  - `.ai/COMMANDS/phase-intent-check.md <plan> "<phase-heading>"`
- Before commit:
  - `.ai/COMMANDS/validate.md`
  - `.ai/COMMANDS/review.md`
- Before/at PR publish:
  - `.ai/COMMANDS/push.md`
  - `.ai/COMMANDS/pr.md`
- End of session:
  - `.ai/COMMANDS/handoff.md`
- Weekly:
  - `.ai/COMMANDS/tech-debt.md`
- After meaningful delivery or repeated friction:
  - `.ai/COMMANDS/retro.md`
- Per release/tag:
  - `.ai/COMMANDS/release-notes.md`
