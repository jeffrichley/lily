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

## Gate S1: Phase 2 Alignment (Must Pass Before Provider Refactor)

`User-visible features`
- None (alignment gate only).

`Internal engineering tasks`
- [x] Confirm Phase 2 locked scope from spec:
  - [x] registry-based provider dispatch (`builtin`, `mcp`, `plugin` interface shape)
  - [x] route existing builtin tools through provider path
  - [x] MCP adapter contract + deterministic error mapping
  - [x] preserve Phase 1 capability enforcement guarantees
- [x] Confirm explicit Phase 2 exclusions:
  - [x] no containerized plugin runtime execution yet (Phase 3)
  - [x] no HITL approval workflow yet (Phase 3)
  - [x] no security hash/provenance persistence runtime yet (Phase 3)
  - [x] no new autonomous supervisor/subagent behavior (separate feature)
- [x] Freeze provider error code contract for Phase 2:
  - [x] `provider_unbound`
  - [x] `provider_tool_unregistered`
  - [x] `provider_execution_failed`
  - [x] `provider_policy_denied`

`Acceptance criteria`
- [x] S1 checklist completed and referenced in implementation PR.
- [x] Provider error-code contract documented in code/tests before rollout.

`Non-goals`
- no plugin container sandbox wiring.
- no security-hash approval cache implementation.
- no TUI workflow changes.

`Required tests and gates`
- [x] `just docs-check` green before and after Phase 2 edits.

---

## Phase 2: Provider Registry (Builtin + MCP) (`P5`)

`User-visible features`
- [x] Skills continue to run through stable `/skill` UX while provider-backed routing becomes active.
- [x] Deterministic provider/tool resolution failures show clear, stable user-facing errors.

`Internal engineering tasks`
- [x] Introduce provider abstraction:
  - [x] add `ToolProvider` protocol/contract
  - [x] add provider registry keyed by stable provider id
  - [x] remove mode/provider branching that conflicts with registry pattern
- [x] Implement builtin provider:
  - [x] wrap existing arithmetic tools (`add`, `subtract`, `multiply`) as provider-backed tools
  - [x] keep typed input/output validation path intact
  - [x] preserve existing deterministic success/error envelopes where contract requires stability
- [x] Implement MCP provider contract (adapter scaffold):
  - [x] resolve declared MCP tool identifiers
  - [x] map adapter failures to deterministic provider error codes
  - [x] keep transport/runtime concerns isolated behind provider adapter boundary
- [x] Update skill metadata integration for provider resolution:
  - [x] ensure capability declarations are checked against provider+tool resolution
  - [x] deny undeclared/unregistered provider tools deterministically
- [x] Add observability/diagnostics:
  - [x] include provider id + tool id in structured result data where applicable
  - [x] ensure security-alert rendering triggers for policy-denied provider paths

`Acceptance criteria`
- [x] Registry-based provider dispatch is active end-to-end for skill tool execution.
- [x] Existing builtin tools behave compatibly under provider path (no contract regressions).
- [x] Unresolved provider/tool calls fail with deterministic error codes/messages.
- [x] MCP adapter path is test-covered (mocked integration level) with deterministic failure mapping.

`Non-goals`
- no remote plugin code execution.
- no container runtime hooks.
- no HITL prompt/grant persistence.
- no supervisor orchestration logic.

`Required tests and gates`
- [x] unit tests for provider registry dispatch and provider lookup failures.
- [x] unit tests for builtin provider tool routing + typed validation parity.
- [x] unit tests for capability-denied provider scenarios.
- [x] integration tests for mocked MCP provider success/failure mapping.
- [x] regression tests for existing `/skill add|subtract|multiply` behavior.
- [x] `just quality-check`.
- [x] `just docs-check`.

---

## Status Log

- 2026-02-17: Plan created. User selected Phase 1-only implementation start with rule-based security governance, SQLite security backend, and terminal-first HITL deferred to later phase.
- 2026-02-17: Gate S0 completed. Locked decisions and Phase 1 boundaries validated against `docs/specs/agents/skills_platform_v1.md`; scope remains Phase 1-only.
- 2026-02-17: Phase 1 completed. Added capability contract fields + loader validation, runtime capability denial for undeclared tool use, `/skills` diagnostic rendering, and terminal security-alert Rich panels; targeted unit tests plus `just quality-check` and `just docs-check` passed.
- 2026-02-17: Phase 2 detailed plan added (Gate S1 + provider-registry execution scope, acceptance criteria, non-goals, and tests/gates).
- 2026-02-17: Gate S1 and Phase 2 completed. Added provider registry (`builtin` + MCP adapter contract), provider-scoped deterministic errors, provider-aware tool dispatch/runtime metadata, capability checks supporting provider-qualified declarations, and mocked MCP routing/failure tests; `just quality-check` and `just docs-check` passed.
