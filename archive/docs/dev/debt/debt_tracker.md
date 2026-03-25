---
owner: "@jeffrichley"
last_updated: "2026-03-03"
status: "active"
source_of_truth: true
---

# Lily Debt Tracker

Purpose: track technical/product debt that should be cleaned up intentionally, not implicitly.

## Authority

This document is authoritative for:
- open debt inventory and ownership
- debt priorities (P1/P2/P3) and exit criteria

This document is not authoritative for:
- feature prioritization (`docs/dev/roadmap.md`)
- active phase checklist progress (`docs/dev/plans/`)

Next review date: `2026-03-09`.

Usage rules:
- Every debt item must have: `priority`, `owner`, `target`, `exit criteria`.
- Use checkboxes for status.
- Close debt in the same PR that resolves it.

Priority scale:
- `P1`: blocking reliability/safety/correctness debt
- `P2`: high-value maintainability/performance debt
- `P3`: useful cleanup, non-blocking

## Active Debt

### P1

- [ ] [DEBT-015] Fix debt metadata parsing boundaries in docs traceability validator
  - Issue draft: `TBD`
  - Owner: `@jeffrichley`
  - Target: `2026-03-10`
  - Current state:
    - `src/lily/docs_validator.py::_parse_debt_items` appends all non-checkbox lines to the current debt item until another checkbox appears.
    - this can incorrectly associate unrelated lines (including later section content) with the last parsed debt item.
  - Exit criteria:
    - parser captures only lines that belong to a debt item's metadata block
    - unrelated section/body lines are not attached to previous debt items
    - unit tests cover boundary cases (section breaks, blank lines, non-indented lines)

- [ ] [DEBT-016] Enforce explicit roadmap-ID requirement in status traceability validator
  - Issue draft: `TBD`
  - Owner: `@jeffrichley`
  - Target: `2026-03-10`
  - Current state:
    - status-sync policy requires explicit roadmap/debt references to use IDs (`SI-XXX`/`DEBT-XXX`)
    - validator currently requires SI IDs only when the bullet text includes `system improvement`, leaving other roadmap references under-enforced
  - Exit criteria:
    - validator rejects explicit roadmap references without `SI-XXX`
    - enforcement behavior matches `.ai/COMMANDS/status-sync.md`
    - unit tests cover positive/negative roadmap-reference patterns

### P2

- [ ] [DEBT-001] Align `tech-debt` command to canonical debt ledger path
  - Issue draft: `TBD`
  - Owner: `@jeffrichley`
  - Target: `2026-03-17`
  - Current state:
    - `.ai/COMMANDS/tech-debt.md` instructs agents to update `.ai/TECHNICAL_DEBT.md`
    - canonical debt source of truth is `docs/dev/debt/debt_tracker.md`
    - `.ai/TECHNICAL_DEBT.md` does not exist, causing workflow ambiguity
  - Exit criteria:
    - `tech-debt` command points to `docs/dev/debt/debt_tracker.md`
    - command text aligns with debt tracker structure/authority rules
    - no `.ai/TECHNICAL_DEBT.md` references remain in active command workflows

- [ ] [DEBT-002] Eliminate third-party deprecation warning workaround (`trustcall`)
  - Issue draft: `docs/dev/debt/issues/debt-p1-trustcall-warning.md`
  - Execution plan: `.ai/PLANS/004-p1-trustcall-warning-removal.md`
  - Owner: `@jeffrichley`
  - Target: `2026-03-15`
  - Current state:
    - pytest suppresses `trustcall._base` deprecation warning about `Send` import path
    - upstream latest currently still emits this warning path, so immediate no-downgrade removal is blocked
  - Exit criteria:
    - dependency path upgraded/fixed so no suppression is required
    - warning filter entry removed from `pyproject.toml`
    - quality/test runs remain warning-clean

- [ ] [DEBT-003] Add configurable safe-runtime ruleset profiles
  - Issue draft: `TBD`
  - Owner: `@jeffrichley`
  - Target: `2026-03-22`
  - Current state:
    - language restriction behavior is code-defined and not managed via a first-class ruleset/profile contract
    - operators cannot declaratively select, version, and audit policy profiles for safe-runtime enforcement
  - Exit criteria:
    - explicit ruleset/profile configuration model is defined (for example baseline/strict/paranoid/custom)
    - runtime selects ruleset from deterministic config sources with clear precedence
    - active ruleset identity/version is observable in runtime status/evidence surfaces
    - tests cover profile selection, precedence, and safe fallback/error behavior for invalid profiles

- [ ] [DEBT-004] Unify duplicated memory repository behavior across file/store backends
  - Issue draft: `docs/dev/debt/issues/debt-p2-unify-memory-repository-core.md`
  - Owner: `@jeffrichley`
  - Target: `2026-03-20`
  - Current state:
    - `src/lily/memory/file_repository.py` and `src/lily/memory/store_repository.py` each implement similar validation/policy/upsert logic and read/filter/sort/metrics paths.
    - drift risk remains when fixes land in one backend but not the other.
  - Exit criteria:
    - shared repository-core service (or equivalent) owns common policy/validation/upsert/filter/sort behavior
    - file/store repositories are thin adapters over backend I/O
    - cross-backend parity tests validate equivalent behavior for core operations

### P3

- [ ] [DEBT-005] Add scheduled jobs for run-artifact cleanup and self-learning pipelines
  - Issue draft: `docs/dev/debt/issues/debt-p3-scheduled-jobs-cleanup-self-learning.md`
  - Owner: `@jeffrichley`
  - Target: `TBD`
  - Current state: V0 jobs retain all artifacts by default; no periodic cleanup/self-learning orchestration jobs are defined.
  - Exit criteria:
    - explicit cleanup job spec and retention policy are implemented
    - explicit self-learning job cadence and safety gates are defined
    - runbook covers enabling/disabling and observing these scheduled jobs

- [ ] [DEBT-006] Consolidate runtime SQLite locations under `.lily/db/`
  - Issue draft: `docs/dev/debt/issues/debt-p3-consolidate-runtime-sqlite-location.md`
  - Owner: `@jeffrichley`
  - Target: `TBD`
  - Current state: SQLite artifacts are split across directories (for example `.lily/checkpoints/checkpointer.sqlite` and planned `.lily/db/security.sqlite`).
  - Exit criteria:
    - canonical runtime DB directory is defined as `.lily/db/`
    - existing SQLite paths (checkpointer and related runtime DBs) are migrated or compatibility-mapped
    - docs/config defaults are updated and tested for migration safety

- [ ] [DEBT-007] Add multi-process persistence safety strategy
  - Issue draft: `docs/dev/debt/issues/debt-p3-multiprocess-persistence-safety.md`
  - Roadmap: `SI-008`
  - Owner: `@jeffrichley`
  - Target: `TBD`
  - Current state: per-session serialization exists, but multi-process locking strategy is not finalized.
  - Exit criteria:
    - documented lock strategy for session/checkpoint/memory paths
    - conflict/failure behavior defined
    - concurrency tests include multi-process cases

## Recently Closed Debt

- [x] [DEBT-008] Harden language-policy file-read/decode failure path to deterministic deny envelope
  - Issue draft: `TBD`
  - Owner: `@jeffrichley`
  - Closed: `2026-03-03`
  - Current state:
    - language-policy scan now converts read and UTF-8 decode failures into deterministic `security_language_policy_denied` envelopes
    - syntax parse failures remain deterministic `syntax_error` denials
  - Exit criteria:
    - plugin file read/decode/parsing failures are converted to deterministic security denial codes/messages/data
    - tests cover non-UTF8 and unreadable plugin file scenarios through the security gate + tool-dispatch bridge
    - no unexpected raw decode/read exceptions leak to command/tool surfaces
  - Closure evidence:
    - `src/lily/runtime/security_language_policy.py` (deterministic `file_read_error` and `file_decode_error` mapping)
    - `tests/unit/runtime/test_security_language_policy.py` (scanner-level decode/read/syntax failure coverage)
    - `tests/unit/runtime/test_security.py` (SecurityGate boundary mapping for decode/read failures)
    - `tests/unit/runtime/test_tool_dispatch_executor.py` (tool-dispatch bridge mapping for decode/read failures)

- [x] [DEBT-009] Add pre-execution language restriction layer (RestrictedPython or equivalent AST policy)
  - Issue draft: `docs/dev/debt/issues/debt-p1-language-restriction-layer.md`
  - Owner: `@jeffrichley`
  - Closed: `2026-03-03`
  - Current state: AST restriction layer is implemented and integrated before preflight in plugin authorization flow with deterministic deny envelopes and store-backed scan caching.
  - Why this matters:
    - container isolation is the primary boundary, but language restriction is valuable defense-in-depth
    - catches risky constructs earlier with clearer deterministic denials
    - reduces blast radius of parser/runtime bypass attempts
  - Exit criteria:
    - deterministic pre-execution restriction layer is active for plugin code
    - denial codes/messages are stable and covered by tests
    - docs explicitly describe layered security model (language restriction + container isolation)
  - Closure evidence:
    - `tests/unit/runtime/test_security_language_policy.py` (policy + cache matrix)
    - `tests/unit/runtime/test_security.py` (SecurityGate integration + store cache roundtrip)
    - `tests/unit/runtime/test_tool_dispatch_executor.py` (deterministic tool-envelope mapping)
    - `docs/dev/debt/issues/debt-p1-language-restriction-layer.md` (layered security model documented: language restriction + container isolation)

- [x] [DEBT-010] Integrate pytest-drill-sergeant for test quality enforcement
  - Owner: `@jeffrichley`
  - Closed: `2026-02-20`
  - Current state: plugin now enforces marker classification and applies AAA/file-length policy in configured mode.
  - Reference: [pytest-drill-sergeant on PyPI](https://pypi.org/project/pytest-drill-sergeant/)
  - Evidence:
    - dev dependency added: `pytest-drill-sergeant`
    - pytest config wired in `pyproject.toml` (`drill_sergeant_*` options)
    - marker mapping aligned for existing layout: `contracts -> integration`
    - AAA enabled in `basic` mode; file-length rule configured (`max=1200`, `mode=warn`)
    - full gate run passes with plugin active via `just quality test`

- [x] [DEBT-011] Split oversized test modules into focused suites
  - Issue draft: `docs/dev/debt/issues/debt-p3-split-oversized-test-modules.md`
  - Owner: `@jeffrichley`
  - Closed: `2026-03-03`
  - Exit criteria:
    - command-surface tests are split by domain (for example skills/persona/memory/jobs)
    - CLI tests are split by concern (bootstrap/run/repl/rendering)
    - no behavior contract coverage is lost during split
  - Closure evidence:
    - `tests/unit/commands/test_command_surface.py` + `tests/unit/commands/test_command_surface_stateful.py`
    - `tests/unit/cli/test_cli.py` + `tests/unit/cli/test_cli_recovery_init.py`
    - shared fixture extraction in `tests/unit/commands/command_surface_shared.py` and `tests/unit/cli/cli_shared.py`
    - runtime conversation split into `tests/unit/runtime/test_conversation.py` + `tests/unit/runtime/test_conversation_executor.py`
    - matrix deduplication in `tests/unit/config/test_global_config.py`, `tests/unit/runtime/test_security_language_policy.py`, and `tests/unit/runtime/test_tool_dispatch_executor.py`
    - `just quality` passes warning-clean after refactor set

- [x] [DEBT-012] Add typed skill/tool contracts (input/output schemas)
  - Closed: `2026-02-17`
  - Evidence:
    - phase completion: `docs/dev/plans/skills_platform_execution_plan.md`
    - base contract defaults: `src/lily/runtime/executors/tool_base.py`
    - contract conformance lane: `just contract-conformance`
    - deterministic envelope snapshots: `tests/contracts/contract_envelopes.snapshot.json`
    - wrapper compatibility coverage: `tests/unit/contracts/test_langchain_wrappers.py`

- [x] [DEBT-013] Warning-clean test/runtime policy established and enforced
  - Closed: `2026-02-17`
  - Evidence:
    - `AGENTS.md` warning policy added
    - runtime close hooks wired (`RuntimeFacade` + conversation executor)
    - pytest `ResourceWarning` escalated to error
    - `just quality test` and `pytest` run warning-clean

- [x] [DEBT-014] Consolidate planning docs to reduce stale duplication
  - Owner: `@jeffrichley`
  - Closed: `2026-02-17`
  - Evidence:
    - `docs/archive/dev/punchlist.md` converted to archived summary + canonical links
    - `ideas/later_backlog.md` reduced to curated idea list (non-status tracker)
    - `docs/dev/roadmap.md` updated with explicit status ownership and current execution rule
