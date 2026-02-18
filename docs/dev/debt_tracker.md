---
owner: "@team"
last_updated: "2026-02-18"
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

- [ ] Add real `/agent <name>` once agent subsystem exists
  - Owner: `@team`
  - Target: `TBD`
  - Current state: deferred in punchlist until full agent subsystem is available.
  - Exit criteria:
    - command routes to real agent registry/state
    - help/list/show/use flows are deterministic
    - command and REPL coverage added

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
