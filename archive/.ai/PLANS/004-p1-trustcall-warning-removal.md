# Feature: p1-trustcall-warning-removal

This plan removes the temporary pytest warning suppression for `trustcall` deprecation and restores warning-clean execution without that suppression.

## Feature Description

Eliminate the `trustcall` deprecation-warning workaround from pytest config by upgrading/remediating dependency path and proving warning-clean gates.

## User Story

As a maintainer,
I want warning-clean test runs without dependency-specific suppression hacks,
So that warning policy remains strict and reliable.

## Problem Statement

`pyproject.toml` currently suppresses a known `trustcall._base` deprecation warning around `Send` import path. This violates the “warnings are defects” policy when left unresolved.

## Solution Statement

Trace `trustcall` introduction path (currently via `langmem`), upgrade to a compatible version path that no longer emits the warning, remove suppression filter, and verify all quality/test gates remain warning-clean.

## Feature Metadata

**Feature Type**: Maintenance (P1 debt)
**Estimated Complexity**: Medium
**Primary Systems Affected**: dependency graph (`pyproject.toml`, `uv.lock`), tests, docs
**Dependencies**: `langmem`, `trustcall` (transitive)

## Branch Setup (Required)

```bash
PLAN_FILE=".ai/PLANS/004-p1-trustcall-warning-removal.md"
PLAN_SLUG="$(basename "$PLAN_FILE" .md)"
BRANCH_NAME="feat/${PLAN_SLUG}"
git show-ref --verify --quiet "refs/heads/${BRANCH_NAME}" \
  && git switch "${BRANCH_NAME}" \
  || git switch -c "${BRANCH_NAME}"
```

---

## CONTEXT REFERENCES

### Relevant Codebase Files (Read First)

- `pyproject.toml:75` - current warning filter configuration containing trustcall suppression
- `uv.lock:794` - `langmem` pin currently introducing `trustcall`
- `uv.lock:1954` - `trustcall` resolved version and metadata
- `docs/dev/debt/debt_tracker.md:38` - debt acceptance criteria
- `docs/dev/debt/issues/debt-p1-trustcall-warning.md:1` - issue scope

### Files to Update

- `pyproject.toml` - remove suppression entry once underlying warning path fixed
- `uv.lock` - updated resolved dependency graph
- `docs/dev/debt/debt_tracker.md` - debt closure evidence
- `docs/dev/status.md` - completion diary entry

### Relevant Documentation

- `AGENTS.md` warning policy
- `docs/dev/debt/debt_tracker.md` warning-clean debt item

### Patterns to Follow

- Keep warnings as errors where feasible; no new suppressions
- Minimal, reversible dependency changes

---

## IMPLEMENTATION PLAN

- [ ] Phase 1: Reproduce and isolate warning origin
- [ ] Phase 2: Apply dependency remediation strategy
- [ ] Phase 3: Remove suppression and validate full gates

### Intent Lock: Phase 1

**Source of truth**:
- `pyproject.toml:75`
- `uv.lock:794`
- `uv.lock:1954`

**Must**:
- Reproduce warning when suppression is temporarily removed in a controlled branch
- Confirm exact package/version chain emitting warning

**Must Not**:
- Must not commit speculative dependency bumps without warning reproduction evidence

**Provenance map**:
- warning signature captured from pytest output
- dependency path captured via lock/tree inspection

**Acceptance gates**:
- `uv run pytest tests/unit/runtime/test_langchain_backend.py -q` (or narrower reproducer)

### Intent Lock: Phase 2

**Source of truth**:
- `docs/dev/debt/debt_tracker.md:38`

**Must**:
- Upgrade/adjust dependency path to eliminate warning at source
- Keep runtime/test compatibility for memory/langmem features

**Must Not**:
- Must not add permanent warning suppression
- Must not broaden to unrelated dependency upgrades

**Provenance map**:
- old vs new resolved versions in `uv.lock`
- warning absence in targeted runs

**Acceptance gates**:
- `just quality-check`
- targeted pytest lane covering prior warning path

### Intent Lock: Phase 3

**Source of truth**:
- `pyproject.toml:75`
- debt issue doc + tracker

**Must**:
- Remove trustcall suppression line from `filterwarnings`
- Verify full warning-clean quality/test run
- Update debt tracker evidence

**Must Not**:
- Must not close debt with partial/targeted-only validation

**Provenance map**:
- suppression removal diff in `pyproject.toml`
- `just quality test` output

**Acceptance gates**:
- `just quality test`
- `just docs-check`

---

## STEP-BY-STEP TASKS

### UPDATE dependency graph

- **IMPLEMENT**: apply minimal dependency version change to remove warning path
- **VALIDATE**: targeted pytest that previously emitted warning

### UPDATE `pyproject.toml`

- **REMOVE**: trustcall-specific ignore line in `filterwarnings`
- **VALIDATE**: `just quality-check`

### UPDATE docs

- **UPDATE**: `docs/dev/debt/debt_tracker.md` closure evidence
- **UPDATE**: `docs/dev/status.md` diary entry
- **VALIDATE**: `just docs-check`

---

## TESTING STRATEGY

### Unit/Targeted

- run narrow tests that exercise langmem/trustcall import path

### Full Gate

- `just quality test` to prove warning-clean policy holds end-to-end

### Edge Cases

- ensure dependency change does not regress memory functionality using langmem-backed tooling

---

## VALIDATION COMMANDS

### Targeted Repro

- `uv run pytest tests/unit/runtime/test_langchain_backend.py -q`

### Quality + Tests

- `just quality-check`
- `just test`
- `just quality test`

### Docs

- `just docs-check`

---

## ACCEPTANCE CRITERIA

- [ ] Trustcall deprecation warning no longer appears in runs.
- [ ] Suppression line removed from `pyproject.toml`.
- [ ] `just quality test` passes warning-clean.
- [ ] Debt tracker updated with closure evidence.

## COMPLETION CHECKLIST

- [ ] Dependency remediation implemented
- [ ] Suppression removed
- [ ] Full gates green
- [ ] Docs updated

## NOTES

- If upstream fix is unavailable, document blocker with exact version constraints and owner/target date; do not reintroduce permanent suppression.
