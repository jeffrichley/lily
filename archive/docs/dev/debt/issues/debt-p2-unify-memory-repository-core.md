---
owner: "@jeffrichley"
last_updated: "2026-03-02"
status: "active"
source_of_truth: false
---

# [Debt][P2] Unify duplicated memory repository behavior across file/store backends

## Source
- Debt tracker: `docs/dev/debt/debt_tracker.md` (Active Debt → P2)

## Internal engineering tasks
- Create a shared repository core for policy/validation/upsert/filter/sort behavior.
- Convert file/store repositories into thin backend I/O adapters.
- Add parity tests across backends for core operations.

## User-visible features
- None.

## Acceptance criteria
- Shared core service (or equivalent) owns common repository behavior.
- File/store repositories are thin adapters.
- Cross-backend parity tests validate equivalent behavior.

## Non-goals
- Introducing new memory features beyond behavior parity.
- Changing memory API contracts unless required for parity.

## Required tests and gates
- Unit tests for shared core behavior.
- Cross-backend parity tests.
- `just quality test` warning-clean.

## Metadata
- Priority: `P2`
- Owner: `@jeffrichley`
- Target: `2026-03-20`
