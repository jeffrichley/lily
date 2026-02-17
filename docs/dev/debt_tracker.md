---
owner: "@team"
last_updated: "2026-02-17"
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

### P2

- [ ] Add typed skill/tool contracts (input/output schemas)
  - Owner: `@team`
  - Target: `TBD`
  - Current state: typed I/O validation is implemented for `tool_dispatch` command tools, but generalized skill-declared I/O contracts are not yet implemented across all skills/modes.
  - Exit criteria:
    - skill metadata supports optional skill-declared input/output schema fields
    - runtime validates input pre-execution and output post-execution for both `tool_dispatch` and `llm_orchestration`
    - deterministic validation errors are stable across both execution modes
    - at least 2 non-demo skills use skill-declared typed I/O end-to-end

- [ ] Add real `/agent <name>` once agent subsystem exists
  - Owner: `@team`
  - Target: `TBD`
  - Current state: deferred in punchlist until full agent subsystem is available.
  - Exit criteria:
    - command routes to real agent registry/state
    - help/list/show/use flows are deterministic
    - command and REPL coverage added

### P3

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

- [x] Warning-clean test/runtime policy established and enforced
  - Closed: `2026-02-17`
  - Evidence:
    - `AGENTS.md` warning policy added
    - runtime close hooks wired (`RuntimeFacade` + conversation executor)
    - pytest `ResourceWarning` escalated to error
    - `just quality test` and `pytest` run warning-clean
