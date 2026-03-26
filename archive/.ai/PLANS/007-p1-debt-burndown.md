# Feature: p1-debt-burndown

Resolve all currently open P1 debt items in the canonical debt tracker with explicit closure evidence and warning-clean validation.

The following plan should be complete, but its important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils types and models. Import from the right files etc.

## Feature Description

Close both P1 debt items currently listed in `docs/dev/debt/debt_tracker.md` by (1) hardening language-policy file read/decode/parse failures into deterministic denial envelopes and (2) explicitly closing or patching the pre-execution language-restriction debt item based on current implementation evidence.

## User Story

As a repo operator,
I want all P1 debt items to be either resolved with evidence or explicitly re-scoped,
So that blocking reliability/security debt is no longer ambiguous and the debt queue reflects reality.

## Problem Statement

The debt tracker currently has two open P1 items. One appears implemented but not formally closed, while the other has explicit correctness-risk behaviors around decode/read failure handling that can leak non-deterministic errors. This leaves security/reliability priorities unclear and weakens confidence in the warning-clean, deterministic runtime contract.

## Solution Statement

Implement a focused P1 burndown sequence:
1. Re-validate and decide closure status for the language-restriction-layer debt item.
2. Implement deterministic deny-envelope handling for language-policy read/decode/parse failure paths.
3. Add tests that prove boundary behavior through security gate + dispatch surfaces.
4. Update debt/status/docs evidence and close both P1 items (or explicitly patch with blocker + retarget if truly blocked).

## Feature Metadata

**Feature Type**: Bug Fix / Reliability Hardening  
**Estimated Complexity**: Medium  
**Primary Systems Affected**: `src/lily/runtime/security*.py`, `src/lily/runtime/tool_dispatch_executor.py`, `tests/unit/runtime/*`, `docs/dev/debt/debt_tracker.md`, `docs/dev/status.md`  
**Dependencies**: Existing security policy scan path, SecurityGate deterministic error envelope contract, current tests in `tests/unit/runtime/`

## Branch Setup (Required)

```bash
PLAN_FILE=".ai/PLANS/007-p1-debt-burndown.md"
PLAN_SLUG="$(basename "$PLAN_FILE" .md)"
BRANCH_NAME="feat/${PLAN_SLUG}"
git show-ref --verify --quiet "refs/heads/${BRANCH_NAME}" \
  && git switch "${BRANCH_NAME}" \
  || git switch -c "${BRANCH_NAME}"
```

## CONTEXT REFERENCES

### Relevant Codebase Files IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!

- `docs/dev/debt/debt_tracker.md` - authoritative P1 debt definitions and closure expectations.
- `.ai/PLANS/003-p1-language-restriction-layer.md` - prior implementation context and acceptance evidence for restriction layer.
- `src/lily/runtime/security.py` - SecurityGate behavior and deterministic denial pathways.
- `src/lily/runtime/security_language_policy.py` - language-policy scan path and failure handling surface.
- `src/lily/runtime/tool_dispatch_executor.py` - tool-dispatch envelope mapping boundary.
- `tests/unit/runtime/test_security_language_policy.py` - scanner behavior and cache matrix tests.
- `tests/unit/runtime/test_security.py` - SecurityGate integration tests.
- `tests/unit/runtime/test_tool_dispatch_executor.py` - deterministic tool-envelope mapping tests.
- `.ai/COMMANDS/status-sync.md` - required post-phase status/doc sync workflow.
- `.ai/COMMANDS/validate.md` - canonical validation order and final gate.

### New Files to Create

- None required by default.
- Optional: create debt issue draft file only if a P1 item cannot be closed and must be re-scoped with blocker evidence.

### Relevant Documentation YOU SHOULD READ THESE BEFORE IMPLEMENTING!

- `docs/dev/debt/debt_tracker.md`
  - Specific section: `## Active Debt` -> `### P1`
  - Why: Defines exact closure contract and targets.
- `docs/dev/status.md`
  - Specific section: `## Update Workflow`, `## Current Focus`
  - Why: Required for status-sync and focus freshness after phase completion.
- `.ai/RULES.md`
  - Specific sections: validation invariants, warning policy, plan/phase contract
  - Why: Non-negotiable execution and quality gates.
- `.ai/REF/testing-and-gates.md`
  - Why: command mapping for baseline/final validation.

### Patterns to Follow

**Naming Conventions:**
- Use existing security denial terminology and deterministic envelope fields already used by SecurityGate/tool dispatch tests.

**Error Handling:**
- Convert boundary exceptions to deterministic security denials; do not leak raw decode/read exceptions to command/tool surfaces.

**Testing Pattern:**
- Mirror existing runtime unit-test style in `tests/unit/runtime/` with explicit behavior assertions, not brittle message matching.

**Docs Pattern:**
- Update debt/status in same PR when debt state changes.
- Run `just docs-check` and `just status` after docs updates.

## IMPLEMENTATION PLAN

- [x] Phase 1: Re-validate and close (or patch) P1 language-restriction debt status
- [x] Phase 2: Implement deterministic deny-envelope handling for read/decode/parse failures
- [x] Phase 3: Expand tests for failure-path coverage through security + dispatch boundaries
- [x] Phase 4: Close P1 debt records and sync status surfaces

### Intent Lock: Phase 1

**Source of truth**:
- `docs/dev/debt/debt_tracker.md` (`### P1` restriction-layer item)
- `.ai/PLANS/003-p1-language-restriction-layer.md`
- `tests/unit/runtime/test_security_language_policy.py`
- `tests/unit/runtime/test_security.py`
- `tests/unit/runtime/test_tool_dispatch_executor.py`

**Must**:
- determine with evidence whether restriction-layer item is truly complete
- close debt item if all exit criteria are already met
- if not complete, patch debt item with concrete remaining gaps + new target date

**Must Not**:
- do not leave status ambiguous (“implemented but open”) after this phase
- do not close without concrete test/doc evidence

**Provenance map**:
- debt item current-state text -> closure or patch decision
- tests/docs evidence -> closure rationale

**Acceptance gates**:
- targeted policy/security/dispatch test commands (existing suites)
- `just docs-check` when debt tracker is edited

### Intent Lock: Phase 2

**Source of truth**:
- `docs/dev/debt/debt_tracker.md` (decode/read failure item)
- `src/lily/runtime/security_language_policy.py`
- `src/lily/runtime/security.py`
- `src/lily/runtime/tool_dispatch_executor.py`

**Must**:
- enforce deterministic deny envelope for file read/decode/parse failures in policy scan path
- ensure boundary behavior aligns with existing security denial contracts

**Must Not**:
- do not add broad exception swallowing without explicit mapping to denial codes/data
- do not introduce silent fallback defaults

**Provenance map**:
- file I/O/decode/parse failure conditions -> deterministic denial envelope fields

**Acceptance gates**:
- targeted failure-path unit tests for policy scanner + security gate/tool dispatch bridge

### Intent Lock: Phase 3

**Source of truth**:
- `tests/unit/runtime/test_security_language_policy.py`
- `tests/unit/runtime/test_security.py`
- `tests/unit/runtime/test_tool_dispatch_executor.py`

**Must**:
- add/adjust tests for non-UTF8, unreadable file, and parse-failure scenarios
- assert deterministic denial behavior at relevant boundaries

**Must Not**:
- do not rely on full exact error-string matches when asserting behavior
- do not skip failure-path coverage for any documented exit criterion

**Provenance map**:
- each debt exit criterion -> at least one explicit test assertion path

**Acceptance gates**:
- targeted test files pass
- `just test` passes

### Intent Lock: Phase 4

**Source of truth**:
- `docs/dev/debt/debt_tracker.md`
- `docs/dev/status.md`
- `.ai/COMMANDS/status-sync.md`
- `.ai/COMMANDS/validate.md`

**Must**:
- close both P1 items when criteria are met, with evidence
- update status diary/current focus/recently completed as needed
- run required docs + status + final quality/test gates

**Must Not**:
- do not claim P1 closure without passing validation evidence
- do not leave docs/plan state unsynced at end of phase

**Provenance map**:
- implementation/tests -> debt closure entries
- phase completion -> status diary + current focus update

**Acceptance gates**:
- `just docs-check`
- `just status`
- `just quality && just test`

## STEP-BY-STEP TASKS

### Phase 1

- **REVIEW** `docs/dev/debt/debt_tracker.md` P1 entries against current code/tests.
- **RUN** targeted tests already listed as evidence for restriction-layer item.
- **UPDATE** debt item status: close with evidence or patch with explicit missing criteria and new target.

### Phase 2

- **UPDATE** security language-policy scan handling to normalize read/decode/parse failures into deterministic denial envelopes.
- **MIRROR** existing denial envelope patterns already used by security gate and tool dispatch boundaries.

### Phase 3

- **ADD**/update targeted unit tests for non-UTF8, unreadable file, and parse-failure scenarios.
- **VALIDATE** denial behavior through both scanner-level and boundary-level tests.

### Phase 4

- **UPDATE** `docs/dev/debt/debt_tracker.md` with closure evidence for both P1 items.
- **UPDATE** `docs/dev/status.md` (`Current Focus`, `Recently Completed`, `Diary Log`) per phase outcomes.
- **RUN** `.ai/COMMANDS/status-sync.md .ai/PLANS/007-p1-debt-burndown.md`.
- **RUN** final validation gates and append execution evidence to this plan.

## Required Tests and Gates

Targeted first:
- `uv run pytest tests/unit/runtime/test_security_language_policy.py -q`
- `uv run pytest tests/unit/runtime/test_security.py -q`
- `uv run pytest tests/unit/runtime/test_tool_dispatch_executor.py -q`

Full gates:
- `just docs-check`
- `just status`
- `just quality && just test`

## Definition of Visible Done

A human can directly verify:
1. `docs/dev/debt/debt_tracker.md` shows no open P1 items (or explicit blocker/retarget rationale if truly blocked).
2. `just status` reports updated debt/status surfaces with current dates and aligned focus.
3. `just quality && just test` passes with warning-clean output.
4. Plan `## Execution Report` documents exact commands and outcomes.

## Input/Resource Provenance

- All required inputs are pre-existing in-repo artifacts:
  - debt definitions in `docs/dev/debt/debt_tracker.md`
  - prior implementation context in `.ai/PLANS/003-p1-language-restriction-layer.md`
  - current runtime/test implementation under `src/lily/runtime/` and `tests/unit/runtime/`
- No external datasets or third-party provisioning required.

## Execution Report

### 2026-03-03

- Completion status: Completed
- Phase intent checks run:
  - Phase 1 lock validated against `docs/dev/debt/debt_tracker.md`, `.ai/PLANS/003-p1-language-restriction-layer.md`, and runtime security test suites.
  - Phase 2/3/4 intent locks reviewed and executed in-order with no ambiguity patches required.
- Commands run and outcomes:
  - `uv run pytest tests/unit/runtime/test_security_language_policy.py -q` -> pass
  - `uv run pytest tests/unit/runtime/test_security.py -q` -> pass
  - `uv run pytest tests/unit/runtime/test_tool_dispatch_executor.py -q` -> pass
  - `just docs-check` -> pass
  - `just status` -> pass
  - `just quality && just test` -> pass
- Output artifacts verified:
  - `docs/dev/debt/debt_tracker.md` now has no open P1 items.
  - `docs/dev/status.md` reflects P1 closure outcomes and updated current focus.
  - `just status` reports open debt reduced and plan tracker updated for this plan.
