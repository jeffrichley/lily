---
owner: "@team"
last_updated: "2026-02-17"
status: "active"
source_of_truth: true
---

# Skills Platform Execution Plan

Purpose: phased implementation tracker for `docs/specs/agents/skills_platform_v1.md`.

Scope contract:
- phase scope is fixed unless explicitly changed by user.
- before implementing each phase, acceptance criteria/non-goals/tests-gates are explicit.
- work items are split into:
  - `User-visible features`
  - `Internal engineering tasks`

---

## Gate S0: Phase 1 Alignment (Must Pass Before Code Changes)

`User-visible features`
- None (alignment gate only).

`Internal engineering tasks`
- [x] Confirm V1 locked decisions from spec are frozen for Phase 1:
  - [x] container-only policy remains future-phase work
  - [x] single profile (`safe_eval`) remains future-phase work
  - [x] hard-deny security model remains future-phase work
  - [x] SQLite path policy captured (`.lily/db/security.sqlite`) for future phases
  - [x] deterministic/rule-based security path (no LLM adjudication)
- [x] Confirm Phase 1 implementation boundary:
  - [x] capability schema/frontmatter updates only
  - [x] load-time diagnostics for invalid/underdeclared skills
  - [x] invoke-time capability enforcement
  - [x] no provider registry refactor yet
  - [x] no plugin/container runtime yet

`Acceptance criteria`
- [x] S0 checklist completed and referenced in PR.
- [x] No scope expansion beyond Phase 1 in active implementation PR.

`Non-goals`
- no provider registry changes.
- no MCP provider integration changes.
- no plugin runtime changes.
- no HITL prompt implementation yet.

`Required tests and gates`
- [x] `just docs-check` green before and after Phase 1 edits.

---

## Phase 1: Capability Contracts + Enforcement (`P5`)

`User-visible features`
- [x] `/skills` output includes deterministic diagnostics for capability/frontmatter validation failures.
- [x] Capability-denied or suspicious ("hinky") skill paths render a high-visibility Rich security alert panel.

`Internal engineering tasks`
- [x] Extend skill metadata/frontmatter schema:
  - [x] add capability contract fields required by Phase 1
  - [x] keep deterministic parsing errors and explicit diagnostic codes
- [x] Add load-time validation:
  - [x] reject malformed/underdeclared skills from snapshot
  - [x] include deterministic diagnostics in snapshot
- [x] Add invoke-time enforcement:
  - [x] enforce declared capabilities before execution
  - [x] emit deterministic failure envelopes on undeclared access
- [x] Add security-alert render contract for denied/hinky events:
  - [x] define stable result codes treated as security alerts in CLI render path
  - [x] render alerts with high-visibility Rich styling (alarm-style panel)
  - [x] include deterministic minimal diagnostic context without dumping raw internals by default
- [x] Maintain compatibility for existing bundled skills via migration-safe defaults where allowed by spec.

`Acceptance criteria`
- [x] malformed skill frontmatter/capability declarations are rejected with deterministic diagnostics.
- [x] undeclared tool/capability usage fails deterministically at runtime.
- [x] denied/hinky paths display security-alert Rich rendering in terminal UX.
- [x] existing bundled skills load and execute without behavior regression.

`Non-goals`
- no provider registry implementation (`Phase 2`).
- no containerized plugin runtime/HITL (`Phase 3`).
- no end-to-end typed contract completion beyond Phase 1 scope (`Phase 4`).

`Required tests and gates`
- [x] unit tests for frontmatter/capability schema validation.
- [x] unit tests for snapshot diagnostics behavior.
- [x] unit tests for invoke-time capability enforcement.
- [x] CLI render tests for security-alert path presentation.
- [x] `just quality-check`.
- [x] `just docs-check`.

---

## Status Log

- 2026-02-17: Plan created. User selected Phase 1-only implementation start with rule-based security governance, SQLite security backend, and terminal-first HITL deferred to later phase.
- 2026-02-17: Gate S0 completed. Locked decisions and Phase 1 boundaries validated against `docs/specs/agents/skills_platform_v1.md`; scope remains Phase 1-only.
- 2026-02-17: Phase 1 completed. Added capability contract fields + loader validation, runtime capability denial for undeclared tool use, `/skills` diagnostic rendering, and terminal security-alert Rich panels; targeted unit tests plus `just quality-check` and `just docs-check` passed.
