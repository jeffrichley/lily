# Feature: session-persistence-schema-versioning

The following plan should be complete, but its important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils types and models. Import from the right files etc.

## Feature Description

Strengthen session persistence compatibility by formalizing schema-version handling and migration stubs for future persisted session payload changes. The goal is to keep reload behavior deterministic across upgrades while avoiding silent fallback behavior.

## User Story

As an operator running Lily across versions,
I want persisted session payloads to be versioned and migrated deterministically,
So that upgrades do not break resume behavior or silently corrupt/reject valid prior data.

## Problem Statement

Session payloads are already versioned (`schema_version: 1`) and migration hook points exist, but the migration contract is still minimal and not yet explicitly structured for multi-step version evolution. Without a formalized migration pipeline and tests, future schema upgrades risk regressions in CLI bootstrap/recovery behavior.

## Solution Statement

Define an explicit session migration contract in the session store layer, with deterministic version dispatch, migration stubs for future versions, and stronger tests that protect:
- roundtrip persistence behavior
- legacy V1 compatibility defaults
- unsupported-version handling behavior through CLI bootstrap and recovery messaging

## Feature Metadata

**Feature Type**: Enhancement (internal reliability)
**Estimated Complexity**: Medium
**Primary Systems Affected**: `src/lily/session/store.py`, `src/lily/cli/bootstrap.py`, session/CLI/e2e tests
**Dependencies**: stdlib JSON + Pydantic models already in repo

## Branch Setup (Required)

Branch naming must follow the plan filename:
- Plan: `.ai/PLANS/011-session-persistence-schema-versioning.md`
- Branch: `feat/011-session-persistence-schema-versioning`

Commands (must be executable as written):
```bash
PLAN_FILE=".ai/PLANS/011-session-persistence-schema-versioning.md"
PLAN_SLUG="$(basename "$PLAN_FILE" .md)"
BRANCH_NAME="feat/${PLAN_SLUG}"
git show-ref --verify --quiet "refs/heads/${BRANCH_NAME}" \
  && git switch "${BRANCH_NAME}" \
  || git switch -c "${BRANCH_NAME}"
```

---

## CONTEXT REFERENCES

### Relevant Codebase Files IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!

- `src/lily/session/store.py:13-133` - Current schema version constant, save/load path, migration hook (`_migrate_payload`) and V1 defaults migration.
- `src/lily/session/models.py:160-173` - `Session` model contract that persisted payload must satisfy.
- `src/lily/cli/bootstrap.py:254-273` - Bootstrap load/recovery semantics for decode/version failures.
- `tests/unit/session/test_store.py:31-110` - Existing store roundtrip/version/defaults coverage patterns.
- `tests/e2e/test_phase1_harness.py:8-36` - Persisted payload artifact assertions (`schema_version == 1`).
- `tests/e2e/test_phase2_session_commands.py:97-114` - Corrupt-session recovery behavior contract.
- `docs/specs/runtime/runtime_architecture_v1.md:1-84` - Runtime architecture invariants relevant to deterministic lifecycle behavior.
- `docs/dev/roadmap.md:199-202` - Priority-4 system-improvement backlog item defining this work.

### New Files to Create

- None required by default.

### Relevant Documentation YOU SHOULD READ THESE BEFORE IMPLEMENTING!

- `docs/specs/runtime/runtime_architecture_v1.md`
  - Specific section: goals/invariants.
  - Why: migration changes must preserve deterministic lifecycle behavior.
- `docs/dev/roadmap.md`
  - Specific section: System Improvements table.
  - Why: source for scope and priority framing.

### Patterns to Follow

**Error handling pattern:**
- Use explicit typed exceptions (`SessionDecodeError`, `SessionSchemaVersionError`) and surface deterministic user messaging in CLI bootstrap recovery path.

**Persistence pattern:**
- Atomic write via temp file + replace is mandatory in `save_session`.

**Migration pattern:**
- Perform migration before Pydantic model validation.
- Reject unknown schema versions explicitly; do not silently coerce unsupported data.

**Testing pattern:**
- Unit tests for store invariants and error contracts.
- E2E tests for bootstrap/recovery behavior and persisted artifact contract.

---

## IMPLEMENTATION PLAN

- [x] Phase 1: Formalize migration contract and schema version constants
- [x] Phase 2: Implement explicit migration dispatcher and stubs
- [x] Phase 3: Preserve and harden CLI bootstrap compatibility behavior
- [x] Phase 4: Expand unit/e2e coverage for versioned migration behavior
- [x] Phase 5: Update docs/status evidence surfaces

### Intent Lock: Phase 1

**Source of truth**:
- `src/lily/session/store.py:13-133`
- `docs/dev/roadmap.md:199-202`

**Must**:
- keep a single canonical "current schema version" constant in session store
- define explicit migration contract comments/docstrings for future version additions
- preserve persisted payload top-level envelope shape: `{schema_version, session}`

**Must Not**:
- do not change session model semantics unrelated to migration/versioning
- do not introduce implicit fallback defaults for unknown schema versions

**Provenance map**:
- `schema_version` field source: `SESSION_SCHEMA_VERSION` in store module
- payload validation source: `Session` model contract in `session/models.py`

**Acceptance gates**:
- `uv run pytest tests/unit/session/test_store.py -q`

### Intent Lock: Phase 2

**Source of truth**:
- `src/lily/session/store.py:97-133`
- `tests/unit/session/test_store.py:49-67,86-110`

**Must**:
- implement deterministic version dispatch pathway (current version fast path + placeholder branch points)
- keep migration functions side-effect free outside intended payload mutation
- ensure unsupported versions raise explicit `SessionSchemaVersionError`

**Must Not**:
- do not silently drop unknown fields to force compatibility
- do not bypass Pydantic validation after migration

**Provenance map**:
- migration decision source: decoded payload `schema_version`
- validation source: `PersistedSessionV1.model_validate(...)`

**Acceptance gates**:
- `uv run pytest tests/unit/session/test_store.py -q`
- `uv run pytest tests/unit/cli/test_cli.py -q -k session`

### Intent Lock: Phase 3

**Source of truth**:
- `src/lily/cli/bootstrap.py:254-273`
- `tests/e2e/test_phase2_session_commands.py:97-114`

**Must**:
- preserve user-visible recovery behavior for unreadable/unsupported persisted payloads
- preserve backup-file creation semantics for invalid session files
- keep deterministic reason messaging in console output

**Must Not**:
- do not break startup path when no session file exists
- do not change unrelated runtime/config bootstrap flows

**Provenance map**:
- recovery behavior source: bootstrap exception handling branch
- operator-facing text source: console print strings in bootstrap

**Acceptance gates**:
- `uv run pytest tests/e2e/test_phase2_session_commands.py -q -k session`
- `uv run pytest tests/unit/cli/test_cli.py -q -k session`

### Intent Lock: Phase 4

**Source of truth**:
- `tests/unit/session/test_store.py`
- `tests/e2e/test_phase1_harness.py`

**Must**:
- cover current-version roundtrip, supported migration defaults, and unsupported-version failure contract
- ensure persisted artifact assertions still verify top-level version envelope
- keep tests deterministic and boundary-focused (no fragile full-message matching)

**Must Not**:
- do not weaken existing coverage for corrupt-session recovery behavior
- do not add broad integration tests unrelated to session persistence contract

**Provenance map**:
- artifact shape source: e2e session payload assertions
- exception behavior source: unit store tests

**Acceptance gates**:
- `uv run pytest tests/unit/session/test_store.py -q`
- `uv run pytest tests/e2e/test_phase1_harness.py -q`
- `uv run pytest tests/e2e/test_phase2_session_commands.py -q -k session`

### Intent Lock: Phase 5

**Source of truth**:
- `docs/dev/status.md`
- `docs/dev/roadmap.md`

**Must**:
- record completion evidence in status surfaces after implementation
- keep roadmap changes limited to ordering/priority updates only if scope changed

**Must Not**:
- do not claim behavior beyond tested migration/versioning scope

**Provenance map**:
- execution evidence source: validation command outputs in PR/plan execution report

**Acceptance gates**:
- `just docs-check`
- `just status`

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

### Phase 1

- [x] **UPDATE** `src/lily/session/store.py`
- **IMPLEMENT**: formal migration contract comments and constants for current/latest schema handling.
- **PATTERN**: existing `SESSION_SCHEMA_VERSION` + `_migrate_payload` contract.
- **IMPORTS**: none beyond current module needs.

### Phase 2

- [x] **REFACTOR** `src/lily/session/store.py`
- **IMPLEMENT**: explicit migration dispatcher structure that is ready for future `vN -> vN+1` additions.
- **PATTERN**: deterministic typed exceptions and pre-validation migration flow.
- **IMPORTS**: maintain current JSON/Pydantic stack.

### Phase 3

- [x] **UPDATE** `src/lily/cli/bootstrap.py`
- **IMPLEMENT**: only minimal adjustments needed to keep schema-version failure behavior deterministic and user-visible.
- **PATTERN**: existing recover-corrupt + recreate session branch.
- **IMPORTS**: retain current bootstrap import boundaries.

### Phase 4

- [x] **UPDATE** `tests/unit/session/test_store.py`
- **ADD**: migration-dispatch contract tests and unsupported-version behavior checks.

- [x] **UPDATE** `tests/unit/cli/test_cli.py`
- **ADD**: focused assertions for session-load error handling where coverage is missing.

- [x] **UPDATE** `tests/e2e/test_phase1_harness.py`
- **ASSERT**: persisted payload still carries expected schema envelope.

- [x] **UPDATE** `tests/e2e/test_phase2_session_commands.py`
- **ASSERT**: schema/decode invalid payload recovery path remains deterministic.

### Phase 5

- [x] **UPDATE** `.ai/PLANS/011-session-persistence-schema-versioning.md`
- **ADD**: `## Execution Report` entries with command/result evidence.

- [x] **UPDATE** `docs/dev/status.md`
- **ADD**: diary/recently-completed updates aligned with completed phase scope.

---

## Required Tests and Gates

Targeted:
- `uv run pytest tests/unit/session/test_store.py -q`
- `uv run pytest tests/unit/cli/test_cli.py -q -k session`
- `uv run pytest tests/e2e/test_phase1_harness.py -q`
- `uv run pytest tests/e2e/test_phase2_session_commands.py -q -k session`

Repository gates:
- `just lint`
- `just format-check`
- `just types`
- `just docs-check`
- `just test`
- `just quality && just test`

## Definition of Visible Done

A human can directly verify:
1. Persisted session artifacts still contain explicit top-level `schema_version` and valid `session` payload.
2. Valid legacy-like V1 payloads load with deterministic defaults (for example missing `active_persona` gets filled).
3. Unsupported schema payloads are handled deterministically via bootstrap recovery messaging and backup creation.
4. Regression tests covering session version/migration behavior pass.

## Input/Resource Provenance

- Requirements provenance: roadmap item `docs/dev/roadmap.md` (Priority-4 system improvement).
- Behavior provenance: current store/bootstrap contracts in `src/lily/session/store.py` and `src/lily/cli/bootstrap.py`.
- Validation provenance: existing unit/e2e tests under `tests/unit/session`, `tests/unit/cli`, and `tests/e2e`.
- Prerequisite setup commands:
  - `uv sync`
  - `just --version && uv --version`

## Execution Report

Status: Completed (all planned phases implemented)

Phase intent checks run:
- Phase 1: lock verified against `src/lily/session/store.py` + `docs/dev/roadmap.md` before implementation.
- Phase 2: lock verified against store migration flow/tests before refactor.
- Phase 3: lock verified against `src/lily/cli/bootstrap.py` recovery path before adjustments.
- Phase 4: lock verified against targeted unit/e2e test contracts before test expansion.
- Phase 5: lock verified against status/roadmap authority boundaries before status-sync edits.

Commands run and outcomes:
- `uv run pytest tests/unit/session/test_store.py -q` -> pass (after AAA comment fix), `6 passed`
- `uv run pytest tests/unit/cli/test_cli.py -q -k session` -> pass, `3 passed, 14 deselected`
- `uv run pytest tests/e2e/test_phase1_harness.py -q` -> pass, `1 passed`
- `uv run pytest tests/e2e/test_phase2_session_commands.py -q -k session` -> pass, `7 passed`
- `just lint` -> pass
- `just format-check` -> pass
- `just types` -> pass
- `just docs-check` -> pass
- `just test` -> pass, `293 passed`
- `just quality && just test` -> pass, quality gates clean + `293 passed`

Status sync evidence:
- Updated status surfaces: `docs/dev/status.md`
- `just docs-check` -> pass
- `just status` -> pass

Output artifacts / behavior evidence:
- Persisted payload envelope remains `{schema_version, session}` with schema set from canonical store constant.
- Unsupported schema payloads in unit + e2e recovery paths produce deterministic invalid-session messaging and `.corrupt-*` backup creation.

Notes:
- Worktree already contained unrelated local changes before execution (including deleted diagram artifacts) and they were intentionally left untouched per user direction.
