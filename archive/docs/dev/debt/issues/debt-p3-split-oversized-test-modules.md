---
owner: "@team"
last_updated: "2026-03-03"
status: "archived"
source_of_truth: false
---

# [Debt][P3] Split oversized test modules into focused suites

## Source
- Debt tracker: `docs/dev/debt/debt_tracker.md` (Active Debt → P3)

## Internal engineering tasks
- Split command-surface tests by domain (skills/persona/memory/jobs).
- Split CLI tests by concern (bootstrap/run/repl/rendering).
- Preserve behavior contract coverage while improving reviewability.

## User-visible features
- None.

## Acceptance criteria
- `tests/unit/commands/test_command_surface.py` is split into focused suites.
- `tests/unit/cli/test_cli.py` is split into focused suites.
- No behavior contract coverage is lost.

## Non-goals
- Changing command or CLI behavior semantics.
- Rewriting unrelated test infrastructure.

## Required tests and gates
- Full unit test run for command + CLI suites.
- Contract regression checks for command behavior.
- `just quality test` warning-clean.

## Metadata
- Priority: `P3`
- Owner: `@team`
- Target: `2026-03-10`
