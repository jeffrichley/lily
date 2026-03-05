# Feature: roadmap-traceability-consistency-check

## Feature Description

Add stable roadmap system-improvement IDs and enforce cross-doc traceability/consistency checks so completed work in status/plan surfaces cannot silently drift from roadmap status.

## User Story

As a maintainer,
I want roadmap items to have stable IDs and docs-check to verify references,
So that status/debt/plan updates remain traceable and inconsistency is caught in CI.

## Problem Statement

Current docs checks validate frontmatter freshness but do not validate cross-document consistency. This allows cases where a roadmap item remains marked Open after status and plan docs indicate completion.

## Solution Statement

1. Add stable IDs to `docs/dev/roadmap.md` system-improvement rows.
2. Require `docs/dev/status.md` focus/completion bullets to reference those IDs.
3. Extend docs validation to enforce:
   - roadmap IDs are unique and structurally valid
   - status references unknown IDs are rejected
   - status marks an item complete while roadmap says Open is rejected
4. Add unit tests for pass/fail scenarios.

## Feature Metadata

**Feature Type**: Internal reliability
**Estimated Complexity**: Medium
**Primary Systems Affected**: `docs/dev/roadmap.md`, `docs/dev/status.md`, `src/lily/docs_validator.py`, `tests/unit/config/test_docs_frontmatter_validator.py`

## Branch Setup (Required)

```bash
PLAN_FILE=".ai/PLANS/012-roadmap-traceability-consistency-check.md"
PLAN_SLUG="$(basename "$PLAN_FILE" .md)"
BRANCH_NAME="feat/${PLAN_SLUG}"
git show-ref --verify --quiet "refs/heads/${BRANCH_NAME}" \
  && git switch "${BRANCH_NAME}" \
  || git switch -c "${BRANCH_NAME}"
```

## Implementation Plan

- [x] Phase 1: Add roadmap IDs and status references
- [x] Phase 2: Implement docs validator consistency checks
- [x] Phase 3: Add/adjust unit tests
- [x] Phase 4: Run validation gates

### Intent Lock: Phase 1

**Acceptance criteria**
- Roadmap system-improvement table includes a stable ID column with all rows populated.
- Status bullets for roadmap-driven focus/completed entries include these IDs.

**Non-goals**
- Re-prioritize roadmap items.
- Rewrite roadmap structure beyond ID column/reference updates.

**Required tests/gates**
- `just docs-check`

### Intent Lock: Phase 2

**Acceptance criteria**
- Docs validator parses roadmap system-improvement IDs and status references.
- Validator emits deterministic errors for unknown IDs and completion/open mismatch.

**Non-goals**
- NLP/fuzzy matching of arbitrary bullet text.
- Cross-validating all docs in repo against roadmap.

**Required tests/gates**
- `uv run pytest tests/unit/config/test_docs_frontmatter_validator.py -q`

### Intent Lock: Phase 3

**Acceptance criteria**
- Unit tests cover new validation pass/fail cases.
- Existing validator tests still pass.

**Non-goals**
- Broad refactor of validator architecture.

**Required tests/gates**
- `uv run pytest tests/unit/config/test_docs_frontmatter_validator.py -q`

### Intent Lock: Phase 4

**Acceptance criteria**
- Targeted test and docs-check gates pass.
- `just status` still renders correctly.

**Non-goals**
- Full repository quality/test run.

**Required tests/gates**
- `uv run pytest tests/unit/config/test_docs_frontmatter_validator.py -q`
- `just docs-check`
- `just status`

## Execution Report

Status: Completed

Files updated:
- `docs/dev/roadmap.md`
- `docs/dev/status.md`
- `src/lily/docs_validator.py`
- `tests/unit/config/test_docs_frontmatter_validator.py`

Commands run:
- `uv run pytest tests/unit/config/test_docs_frontmatter_validator.py -q` -> pass (`6 passed`)
- `just docs-check` -> pass
- `just status` -> pass

## Plan Patch (2026-03-03)

Scope extension approved by user: include debt-surface traceability in the same feature branch/plan.

Added scope:
- introduce stable debt item IDs (`DEBT-xxx`) in `docs/dev/debt/debt_tracker.md`
- add optional debt-to-roadmap linkage field (`Roadmap: SI-xxx`) for roadmap-backed debt
- extend docs validator to enforce debt ID uniqueness and roadmap-link validity

Additional acceptance criteria:
- debt tracker checkbox items have unique `DEBT-xxx` identifiers
- debt roadmap references point to known roadmap IDs
- debt roadmap references cannot target roadmap system improvements already marked `Completed`

Additional required gates:
- `uv run pytest tests/unit/config/test_docs_frontmatter_validator.py -q`
- `just docs-check`
- `just status`

Debt traceability extension execution:
- Added stable debt item identifiers (`DEBT-001` through `DEBT-014`) in `docs/dev/debt/debt_tracker.md`.
- Added debt-to-roadmap mapping field on roadmap-backed debt item: `Roadmap: SI-008`.
- Extended docs validator with debt checks:
  - every debt checkbox item must include exactly one `DEBT-XXX` ID
  - debt IDs must be unique
  - each `Roadmap: SI-XXX` reference must resolve to a roadmap item
  - debt cannot reference roadmap items already marked `Completed`
- Added validator tests for debt pass/fail cases.

Additional commands run and outcomes:
- `uv run ruff check src/lily/docs_validator.py tests/unit/config/test_docs_frontmatter_validator.py` -> pass
- `uv run pytest tests/unit/config/test_docs_frontmatter_validator.py -q` -> pass (`9 passed`)
- `just docs-check` -> pass
- `just status` -> pass

Command workflow alignment updates:
- Updated `.ai/COMMANDS/status-sync.md` to require SI/DEBT traceability in status maintenance steps.
- Updated `.ai/COMMANDS/tech-debt.md` to use `docs/dev/debt/debt_tracker.md`, `DEBT-XXX` IDs, and optional `Roadmap: SI-XXX` links.
- Updated `.ai/COMMANDS/validate.md` warning follow-up guidance to point to debt tracker (`DEBT-XXX`) instead of `.ai/TECHNICAL_DEBT.md`.
