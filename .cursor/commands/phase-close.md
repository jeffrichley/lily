# `/phase-close`

Close a completed phase with commit + push (no PR).

Canonical source of truth:
- `../../.ai/COMMANDS/validate.md`
- `../../.ai/COMMANDS/review.md`
- `../../.ai/COMMANDS/commit.md`
- `../../.ai/COMMANDS/push.md`

Strict gate order:
1. validate
2. review
3. commit
4. push

Stop condition:
- Stop on first failed gate and do not continue.

Constraint:
- This command must not create or update a PR.
