---
owner: "@team"
last_updated: "2026-03-02"
status: "active"
source_of_truth: false
---

# [Debt][P3] Consolidate runtime SQLite locations under `.lily/db/`

## Source
- Debt tracker: `docs/dev/debt/debt_tracker.md` (Active Debt → P3)

## Internal engineering tasks
- Define canonical runtime DB directory as `.lily/db/`.
- Migrate or compatibility-map existing SQLite paths.
- Update docs/config defaults and validate migration safety.

## User-visible features
- None.

## Acceptance criteria
- Canonical runtime DB location is `.lily/db/`.
- Existing SQLite paths are migrated or compatibility-mapped safely.
- Docs/config defaults are updated and migration path is tested.

## Non-goals
- Replacing SQLite with another storage technology.
- Data model redesign unrelated to path consolidation.

## Required tests and gates
- Migration and backward-compatibility tests.
- Startup/runtime tests with pre-existing directories.
- `just quality test` warning-clean.

## Metadata
- Priority: `P3`
- Owner: `@team`
- Target: `TBD`
