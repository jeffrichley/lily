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

### P2

- [ ] Add typed skill/tool contracts (input/output schemas)
  - Owner: `@team`
  - Target: `TBD`
  - Current state: deterministic envelopes exist, but typed I/O contracts are still deferred.
  - Exit criteria:
    - skill metadata supports optional typed input/output models
    - runtime validates input pre-execution and output post-execution
    - deterministic validation errors implemented
    - at least 2 skills validated end-to-end

- [ ] Add real `/agent <name>` once agent subsystem exists
  - Owner: `@team`
  - Target: `TBD`
  - Current state: deferred in punchlist until full agent subsystem is available.
  - Exit criteria:
    - command routes to real agent registry/state
    - help/list/show/use flows are deterministic
    - command and REPL coverage added

### P3

- [ ] Add multi-process persistence safety strategy
  - Owner: `@team`
  - Target: `TBD`
  - Current state: per-session serialization exists, but multi-process locking strategy is not finalized.
  - Exit criteria:
    - documented lock strategy for session/checkpoint/memory paths
    - conflict/failure behavior defined
    - concurrency tests include multi-process cases

- [ ] Consolidate planning docs to reduce stale duplication
  - Owner: `@team`
  - Target: `2026-03-01`
  - Current state: roadmap/punchlist/memory plan overlap can drift.
  - Exit criteria:
    - single source of truth per domain is explicit
    - cross-links updated
    - stale/deprecated plan sections removed

## Recently Closed Debt

- [x] Warning-clean test/runtime policy established and enforced
  - Closed: `2026-02-17`
  - Evidence:
    - `AGENTS.md` warning policy added
    - runtime close hooks wired (`RuntimeFacade` + conversation executor)
    - pytest `ResourceWarning` escalated to error
    - `just quality test` and `pytest` run warning-clean
