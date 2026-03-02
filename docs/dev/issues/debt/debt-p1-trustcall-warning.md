# [Debt][P1] Eliminate third-party deprecation warning workaround (`trustcall`)

## Source
- Debt tracker: `docs/dev/debt_tracker.md` (Active Debt → P1)

## Internal engineering tasks
- Upgrade/fix dependency path so no suppression is required.
- Remove warning filter entry from `pyproject.toml`.
- Keep quality/test runs warning-clean.

## User-visible features
- None.

## Acceptance criteria
- The `trustcall._base` deprecation warning about `Send` import path no longer appears in test/runtime output.
- Warning suppression for this warning is removed from `pyproject.toml`.
- `just quality test` passes warning-clean.

## Non-goals
- Refactoring unrelated warning filters.
- Broad dependency upgrades not required for this warning path.

## Required tests and gates
- `just quality test`
- Targeted pytest invocation covering paths that previously emitted the warning.

## Metadata
- Priority: `P1`
- Owner: `@team`
- Target: `2026-03-15`
