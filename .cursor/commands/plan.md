# `/plan`

Create or refresh the implementation plan before coding.

Canonical source of truth:
- `../../.ai/COMMANDS/create-prd.md`
- `../../.ai/COMMANDS/plan.md`
- `../../.ai/COMMANDS/phase-intent-check.md`

Required gate:
- PRD must exist at `.ai/SPECS/<NNN>-<feature>/PRD.md`.
- If missing, run `create-prd` first, then continue with `plan`.

Plan expectations:
- Includes `## Branch Setup`.
- Includes phase `Intent Lock` requirements (acceptance criteria, non-goals, tests/gates).
