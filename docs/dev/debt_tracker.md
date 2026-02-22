---
owner: "@team"
last_updated: "2026-02-22"
status: "active"
source_of_truth: true
---

# Lily Debt Tracker

Purpose: track technical/product debt that should be cleaned up intentionally, not implicitly.

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

- [ ] Eliminate third-party deprecation warning workaround (`trustcall`)
  - Owner: `@team`
  - Target: `2026-03-15`
  - Current state: pytest suppresses `trustcall._base` deprecation warning about `Send` import path.
  - Exit criteria:
    - dependency path upgraded/fixed so no suppression is required
    - warning filter entry removed from `pyproject.toml`
    - quality/test runs remain warning-clean

- [ ] Add pre-execution language restriction layer (RestrictedPython or equivalent AST policy)
  - Owner: `@team`
  - Target: `2026-03-08`
  - Current state: V1 security relies on container isolation + hard-deny preflight patterns; no RestrictedPython-style language restriction is enforced before plugin execution.
  - Why this matters:
    - container isolation is the primary boundary, but language restriction is valuable defense-in-depth
    - catches risky constructs earlier with clearer deterministic denials
    - reduces blast radius of parser/runtime bypass attempts
  - Exit criteria:
    - deterministic pre-execution restriction layer is active for plugin code
    - denial codes/messages are stable and covered by tests
    - docs explicitly describe layered security model (language restriction + container isolation)

### P2

- [x] Integrate pytest-drill-sergeant for test quality enforcement
  - Owner: `@team`
  - Closed: `2026-02-20`
  - Current state: plugin now enforces marker classification and applies AAA/file-length policy in configured mode.
  - Reference: [pytest-drill-sergeant on PyPI](https://pypi.org/project/pytest-drill-sergeant/)
  - Evidence:
    - dev dependency added: `pytest-drill-sergeant`
    - pytest config wired in `pyproject.toml` (`drill_sergeant_*` options)
    - marker mapping aligned for existing layout: `contracts -> integration`
    - AAA enabled in `basic` mode; file-length rule configured (`max=1200`, `mode=warn`)
    - full gate run passes with plugin active via `just quality test`

- [ ] Unify duplicated memory repository behavior across file/store backends
  - Owner: `@team`
  - Target: `2026-03-20`
  - Current state:
    - `src/lily/memory/file_repository.py` and `src/lily/memory/store_repository.py` each implement similar validation/policy/upsert logic and read/filter/sort/metrics paths.
    - drift risk remains when fixes land in one backend but not the other.
  - Exit criteria:
    - shared repository-core service (or equivalent) owns common policy/validation/upsert/filter/sort behavior
    - file/store repositories are thin adapters over backend I/O
    - cross-backend parity tests validate equivalent behavior for core operations

### P3

- [ ] Add scheduled jobs for run-artifact cleanup and self-learning pipelines
  - Owner: `@team`
  - Target: `TBD`
  - Current state: V0 jobs retain all artifacts by default; no periodic cleanup/self-learning orchestration jobs are defined.
  - Exit criteria:
    - explicit cleanup job spec and retention policy are implemented
    - explicit self-learning job cadence and safety gates are defined
    - runbook covers enabling/disabling and observing these scheduled jobs

- [ ] Consolidate runtime SQLite locations under `.lily/db/`
  - Owner: `@team`
  - Target: `TBD`
  - Current state: SQLite artifacts are split across directories (for example `.lily/checkpoints/checkpointer.sqlite` and planned `.lily/db/security.sqlite`).
  - Exit criteria:
    - canonical runtime DB directory is defined as `.lily/db/`
    - existing SQLite paths (checkpointer and related runtime DBs) are migrated or compatibility-mapped
    - docs/config defaults are updated and tested for migration safety

- [ ] Add multi-process persistence safety strategy
  - Owner: `@team`
  - Target: `TBD`
  - Current state: per-session serialization exists, but multi-process locking strategy is not finalized.
  - Exit criteria:
    - documented lock strategy for session/checkpoint/memory paths
    - conflict/failure behavior defined
    - concurrency tests include multi-process cases

- [ ] Split oversized test modules into focused suites
  - Owner: `@team`
  - Target: `2026-03-10`
  - Current state:
    - `tests/unit/commands/test_command_surface.py` is large (~1142 LOC)
    - `tests/unit/cli/test_cli.py` is large (~708 LOC)
    - reviewability and targeted refactors are harder than necessary
  - Exit criteria:
    - command-surface tests are split by domain (for example skills/persona/memory/jobs)
    - CLI tests are split by concern (bootstrap/run/repl/rendering)
    - no behavior contract coverage is lost during split

- [x] Consolidate planning docs to reduce stale duplication
  - Owner: `@team`
  - Closed: `2026-02-17`
  - Evidence:
    - `docs/archive/dev/punchlist.md` converted to archived summary + canonical links
    - `ideas/later_backlog.md` reduced to curated idea list (non-status tracker)
    - `docs/dev/roadmap.md` updated with explicit status ownership and current execution rule

## Recently Closed Debt

- [x] Add typed skill/tool contracts (input/output schemas)
  - Closed: `2026-02-17`
  - Evidence:
    - phase completion: `docs/dev/skills_platform_execution_plan.md`
    - base contract defaults: `src/lily/runtime/executors/tool_base.py`
    - contract conformance lane: `just contract-conformance`
    - deterministic envelope snapshots: `tests/contracts/contract_envelopes.snapshot.json`
    - wrapper compatibility coverage: `tests/unit/contracts/test_langchain_wrappers.py`

- [x] Warning-clean test/runtime policy established and enforced
  - Closed: `2026-02-17`
  - Evidence:
    - `AGENTS.md` warning policy added
    - runtime close hooks wired (`RuntimeFacade` + conversation executor)
    - pytest `ResourceWarning` escalated to error
    - `just quality test` and `pytest` run warning-clean
