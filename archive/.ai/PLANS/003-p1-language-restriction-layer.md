# Feature: p1-language-restriction-layer

The following plan is implementation-ready and scoped to debt item P1 for pre-execution language restriction.

## Feature Description

Add a deterministic pre-execution language restriction layer for plugin-backed skills before existing preflight signature scanning and HITL flow. This adds defense-in-depth without replacing container isolation.

## User Story

As an operator,
I want plugin code to be rejected for unsafe language constructs before runtime,
So that risky code is blocked earlier with deterministic error behavior.

## Problem Statement

Current V1 plugin security relies on string-signature preflight checks and container isolation. It does not perform structural code analysis (AST policy), leaving gaps for variants that bypass signature matching.

## Solution Statement

Implement an AST-based restriction validator (equivalent to RestrictedPython policy) that evaluates declared plugin files pre-execution and denies forbidden constructs with deterministic error envelopes.

## Feature Metadata

**Feature Type**: Enhancement (security hardening debt)
**Estimated Complexity**: Medium
**Primary Systems Affected**: `runtime.security`, plugin provider execution path, security tests, docs
**Dependencies**: No new runtime dependency in first slice (use stdlib `ast`)

## Branch Setup (Required)

```bash
PLAN_FILE=".ai/PLANS/003-p1-language-restriction-layer.md"
PLAN_SLUG="$(basename "$PLAN_FILE" .md)"
BRANCH_NAME="feat/${PLAN_SLUG}"
git show-ref --verify --quiet "refs/heads/${BRANCH_NAME}" \
  && git switch "${BRANCH_NAME}" \
  || git switch -c "${BRANCH_NAME}"
```

---

## CONTEXT REFERENCES

### Relevant Codebase Files (Read First)

- `src/lily/runtime/security.py:198` - existing `SecurityPreflightScanner` signature blocking and deterministic error mapping
- `src/lily/runtime/security.py:409` - `SecurityGate` authorization sequencing and approval semantics
- `src/lily/runtime/executors/tool_dispatch_components.py:301` - plugin execution path and security error translation to tool error envelope
- `tests/unit/runtime/test_security.py:88` - baseline preflight deny tests and expected security codes
- `docs/dev/debt/debt_tracker.md:48` - debt acceptance criteria and target
- `docs/dev/debt/issues/debt-p1-language-restriction-layer.md:1` - issue scope and non-goals

### New Files to Create

- `src/lily/runtime/security_language_policy.py` - AST restriction rules + validator
- `tests/unit/runtime/test_security_language_policy.py` - unit tests for allow/deny policy matrix

### Files to Update

- `src/lily/runtime/security.py` - integrate policy check into pre-execution security path
- `tests/unit/runtime/test_security.py` - integration tests for policy denial behavior through `SecurityGate`
- `docs/dev/debt/debt_tracker.md` - close or update debt item status/evidence
- `docs/dev/status.md` - diary entry after completion

### Relevant Documentation

- `docs/specs/agents/skills_platform_v1.md` (security/HITL contracts)
- Python AST docs: https://docs.python.org/3/library/ast.html

### Patterns to Follow

- Deterministic error objects via `SecurityAuthorizationError` in `security.py`
- No silent fallback defaults for required contract fields (`.ai/RULES.md`)
- Warning-clean policy and no new suppressions (`AGENTS.md` / `docs/dev/debt/debt_tracker.md`)

---

## IMPLEMENTATION PLAN

- [x] Phase 1: Define deterministic AST restriction policy contract
- [x] Phase 2: Integrate language policy into plugin authorization flow
- [x] Phase 3: Add deterministic language-policy scan cache
- [x] Phase 4: Add tests, docs updates, and close debt item (closure deferred by user request)

### Intent Lock: Phase 1

**Source of truth**:
- `docs/dev/debt/debt_tracker.md:48`
- `docs/dev/debt/issues/debt-p1-language-restriction-layer.md:1`

**Must**:
- Define explicit forbidden-node policy list (e.g., `Import`, `ImportFrom`, `Exec` pattern via `Call`, dangerous builtins usage by name)
- Return deterministic denial payload containing `skill`, `path`, `signature`/`rule_id`
- Keep policy implementation pure/deterministic (no runtime side effects)

**Must Not**:
- Must not remove existing preflight signature scan
- Must not broaden scope into full sandbox redesign
- Must not add non-deterministic LLM adjudication

**Provenance map**:
- `code` from policy rule id
- `message` from centralized formatter
- `data.path` from scanned plugin file manifest

**Acceptance gates**:
- `uv run pytest tests/unit/runtime/test_security_language_policy.py -q`

### Intent Lock: Phase 2

**Source of truth**:
- `src/lily/runtime/security.py:198`
- `src/lily/runtime/security.py:409`
- `src/lily/runtime/executors/tool_dispatch_components.py:343`

**Must**:
- Enforce AST policy before existing preflight marker scan in plugin authorization path
- Preserve existing HITL and hash approval behavior
- Map denial to deterministic tool envelope via existing error bridge

**Must Not**:
- Must not alter approval persistence semantics
- Must not change non-plugin tool execution paths

**Provenance map**:
- deny reason originates in AST policy violation
- tool error code/message flows through existing `SecurityAuthorizationError -> ToolExecutionError` mapping

**Acceptance gates**:
- `uv run pytest tests/unit/runtime/test_security.py -q`
- `uv run pytest tests/unit/runtime/test_tool_dispatch_executor.py -q`

### Intent Lock: Phase 3

**Source of truth**:
- `src/lily/runtime/security.py`
- `src/lily/runtime/security_language_policy.py`
- `src/lily/runtime/security.py` (`SecurityHashService` manifest/hash fields)

**Must**:
- Add deterministic cache for language policy scan outcomes keyed by file content fingerprint
- Include policy fingerprint in cache key (for example rule-set version + lockdown level + code class)
- Ensure cache supports both allow and deny outcomes and deterministic replay of deny payload fields
- Re-scan automatically when file content hash changes or policy fingerprint changes

**Must Not**:
- Must not skip security scan when cache key is missing or invalid
- Must not weaken existing authorization/HITL semantics
- Must not introduce nondeterministic timestamps into cache decision logic

**Provenance map**:
- cache key derives from file content hash + policy fingerprint
- deny payload preserves deterministic `rule_id`, `path`, and location fields

**Acceptance gates**:
- `uv run pytest tests/unit/runtime/test_security_language_policy.py -q`
- `uv run pytest tests/unit/runtime/test_security.py -q`

### Intent Lock: Phase 4

**Source of truth**:
- `docs/dev/debt/debt_tracker.md:48`
- `docs/dev/status.md`

**Must**:
- Update debt tracker with closure evidence if fully complete
- Add status diary entry with date and outcome
- Keep docs frontmatter valid

**Must Not**:
- Must not mark debt closed without passing gates

**Provenance map**:
- closure evidence references exact tests/gates
- diary entry references PR/commit or completion summary

**Acceptance gates**:
- `just docs-check`
- `just quality-check`
- `just test`

---

## STEP-BY-STEP TASKS

### CREATE `src/lily/runtime/security_language_policy.py`

- **IMPLEMENT**: deterministic AST parser and rule evaluator over declared plugin files
- **PATTERN**: mirror deterministic error payload shape from `SecurityAuthorizationError` usage in `src/lily/runtime/security.py`
- **GOTCHA**: handle syntax errors as deterministic deny path, not crash
- **VALIDATE**: `uv run pytest tests/unit/runtime/test_security_language_policy.py -q`

### UPDATE `src/lily/runtime/security.py`

- **ADD**: language policy invocation in pre-execution authorization sequence
- **PATTERN**: retain existing `security_preflight_denied` style deterministic message mapping
- **GOTCHA**: preserve approval hash and prompt logic order after policy pass
- **VALIDATE**: `uv run pytest tests/unit/runtime/test_security.py -q`

### UPDATE `tests/unit/runtime/test_security.py`

- **ADD**: tests for policy-denied plugin source and deterministic code/message/data
- **VALIDATE**: `uv run pytest tests/unit/runtime/test_security.py -q`

### CREATE `tests/unit/runtime/test_security_language_policy.py`

- **ADD**: allow/deny matrix tests for rule coverage
- **ADD**: cache hit/miss/invalidation tests keyed by file hash + policy fingerprint
- **VALIDATE**: `uv run pytest tests/unit/runtime/test_security_language_policy.py -q`

### UPDATE docs

- **UPDATE**: `docs/dev/debt/debt_tracker.md` debt item state/evidence
- **UPDATE**: `docs/dev/status.md` diary log
- **VALIDATE**: `just docs-check`

---

## TESTING STRATEGY

### Unit Tests

- AST policy parser/validator behavior for allow and deny inputs
- deterministic error code/message/data contract assertions

### Integration Tests

- plugin dispatch path returns deterministic deny envelope when AST policy fails

### Edge Cases

- syntax-invalid plugin file
- multi-file plugin manifest where one file violates rule
- benign plugin code with comments/strings containing blocked words (should not false-positive on AST)

---

## VALIDATION COMMANDS

### Level 1: Syntax & Style

- `just quality-check`

### Level 2: Unit Tests

- `uv run pytest tests/unit/runtime/test_security_language_policy.py -q`
- `uv run pytest tests/unit/runtime/test_security.py -q`

### Level 3: Integration Tests

- `uv run pytest tests/unit/runtime/test_tool_dispatch_executor.py -q`

### Level 4: Full Regression

- `just test`

---

## ACCEPTANCE CRITERIA

- [x] Deterministic pre-execution language restriction is active for plugin code.
- [x] Denial codes/messages/data are stable and test-covered.
- [x] Existing approval/hash/preflight behavior remains compatible.
- [x] `just quality-check` and `just test` pass.
- [x] Debt tracker item updated with closure evidence or residual rationale.

## COMPLETION CHECKLIST

- [x] All implementation tasks completed
- [x] All validation commands executed successfully
- [x] Docs updated (`status.md`, `debt_tracker.md`)

## NOTES

- This plan intentionally avoids adding `RestrictedPython` dependency in first slice; stdlib `ast` policy is chosen for deterministic, low-risk delivery.

## Execution Report

- Status: Phase 1 complete; Phase 2/3 not started.
- Branch: `feat/003-p1-language-restriction-layer`
- Intent check:
  - `Intent Lock: Phase 1` verified manually from this plan file.
  - `.ai/COMMANDS/phase-intent-check.md` was referenced by execute workflow but does not exist in repo.
- Implemented:
  - Added `src/lily/runtime/security_language_policy.py` with deterministic AST policy contract and configurable lockdown/trust levels.
  - Added `tests/unit/runtime/test_security_language_policy.py` allow/deny matrix and deterministic payload assertions.
- Commands run:
  - `uv run pytest tests/unit/runtime/test_security_language_policy.py -q` ✅
  - `uv run ruff check src/lily/runtime/security_language_policy.py tests/unit/runtime/test_security_language_policy.py` ✅
  - `uv run mypy src/lily/runtime/security_language_policy.py` ✅
- Acceptance gate evidence:
  - Phase 1 gate passed: `uv run pytest tests/unit/runtime/test_security_language_policy.py -q` (7 passed).
- Partial/blocked:
  - Phase 2 and 3 tasks were intentionally deferred at that time per user request to execute only Phase 1.

### 2026-03-02 Phase 2 Update

- Status: Phase 2 complete; Phase 3/4 not started.
- Implemented:
  - Integrated AST policy scan into `SecurityGate.authorize` before preflight marker scan.
  - Preserved downstream deterministic bridge via existing `SecurityAuthorizationError -> ToolExecutionError` mapping.
  - Added security gate test for policy denial in `tests/unit/runtime/test_security.py`.
  - Added tool-dispatch mapping test for policy denial envelope in `tests/unit/runtime/test_tool_dispatch_executor.py`.
- Commands run:
  - `uv run ruff check src/lily/runtime/security.py tests/unit/runtime/test_security.py tests/unit/runtime/test_tool_dispatch_executor.py` ✅
  - `uv run pytest tests/unit/runtime/test_security.py -q` ✅
  - `uv run pytest tests/unit/runtime/test_tool_dispatch_executor.py -q` ✅
- Acceptance gate evidence:
  - `tests/unit/runtime/test_security.py`: 5 passed.
  - `tests/unit/runtime/test_tool_dispatch_executor.py`: 12 passed.

### 2026-03-02 Phase 3 Update

- Status: Phase 3 complete; Phase 4 not started.
- Implemented:
  - Added deterministic content-addressed scan cache in `security_language_policy` keyed by `sha256(file_bytes)` + policy fingerprint.
  - Added deterministic policy fingerprint including policy version, trust class, lockdown level, Python minor version, and rule-set payload.
  - Added sqlite-backed language policy cache persistence in `SecurityApprovalStore` (`language_policy_cache` table + lookup/upsert methods).
  - Wired `SecurityGate` language policy to store-backed cache adapter.
  - Added cache hit/miss/invalidation tests in `tests/unit/runtime/test_security_language_policy.py`.
  - Added security store cache roundtrip test in `tests/unit/runtime/test_security.py`.
- Commands run:
  - `uv run ruff check src/lily/runtime/security_language_policy.py src/lily/runtime/security.py tests/unit/runtime/test_security_language_policy.py tests/unit/runtime/test_security.py` ✅
  - `uv run pytest tests/unit/runtime/test_security_language_policy.py -q` ✅
  - `uv run pytest tests/unit/runtime/test_security.py -q` ✅
  - `uv run mypy src/lily/runtime/security_language_policy.py src/lily/runtime/security.py` ✅
- Acceptance gate evidence:
  - `tests/unit/runtime/test_security_language_policy.py`: 12 passed.
  - `tests/unit/runtime/test_security.py`: 6 passed.

### 2026-03-02 Phase 4 Update (User-Scoped: Debt Closure Deferred)

- Status: Phase 4 implementation/docs/validation complete; debt item intentionally left open pending user review discussion.
- Implemented:
  - Added status diary entry in `docs/dev/status.md` summarizing completed language policy phases and explicit closure deferral.
  - Updated debt item narrative/evidence in `docs/dev/debt/debt_tracker.md` without marking it closed.
- Commands run:
  - `just docs-check` ✅
  - `just quality-check` ✅
  - `just test` ✅
- Acceptance gate evidence:
  - docs frontmatter validation passed.
  - quality-check passed including lint/type/security/docstring/docs gates.
  - full test suite passed: 268 passed.
- Deferred/blocked by request:
  - Debt item closure checkbox remains open until follow-up discussion and explicit close approval.
