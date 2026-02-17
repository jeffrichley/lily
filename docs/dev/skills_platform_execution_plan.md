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

## Gate S2: Phase 3 Alignment (Must Pass Before Sandbox/HITL Work)

`User-visible features`
- None (alignment gate only).

`Internal engineering tasks`
- [x] Confirm Phase 3 locked scope from spec:
  - [x] plugin entrypoint contract for code-backed tools
  - [x] container-only runtime path (no subprocess fallback)
  - [x] preflight hard-deny checks
  - [x] security hash generation + approval cache/store
  - [x] terminal HITL prompt with `run_once|always_allow|deny`
  - [x] SQLite persistence for approvals/provenance at `.lily/db/security.sqlite`
- [x] Confirm container-runtime implementation contract:
  - [x] container orchestration uses Docker Python SDK (`docker` library) in runtime path
  - [x] no direct shell/subprocess `docker run` execution path in runtime
  - [x] default execution image is pinned by digest and configured globally
  - [x] V1 uses one default image for `safe_eval` (no per-skill arbitrary image selection)
- [x] Confirm runtime environment contract:
  - [x] non-root container user
  - [x] network disabled by default
  - [x] read-only root filesystem
  - [x] explicit mount contract only: `/input` (ro) + `/output` (rw)
  - [x] explicit env allowlist only (no implicit host env passthrough)
  - [x] resource controls (memory/cpu/timeout/log-size limits)
- [x] Confirm explicit Phase 3 exclusions:
  - [x] no TUI approval controls
  - [x] no auto-rewrite/remediation pass for denied code
  - [x] no YOLO bypass mode
  - [x] no non-container plugin execution path
- [x] Freeze deterministic security/result code contract for Phase 3:
  - [x] `plugin_contract_invalid`
  - [x] `plugin_container_unavailable`
  - [x] `plugin_timeout`
  - [x] `plugin_runtime_failed`
  - [x] `security_preflight_denied`
  - [x] `security_hash_mismatch` (approval invalidated)
  - [x] `approval_required`
  - [x] `approval_denied`
  - [x] `approval_persist_failed`

`Acceptance criteria`
- [x] S2 checklist completed and referenced in implementation PR.
- [x] Phase 3 error-code contract documented in code/tests before rollout.

`Non-goals`
- no supervisor/subagent orchestration logic.
- no full typed-contract completion across all skill modes (Phase 4).

`Required tests and gates`
- [x] `just docs-check` green before and after Phase 3 edits.

---

## Phase 3: Containerized Plugin Runtime + HITL (`P5`)

`User-visible features`
- [x] Eligible plugin-backed skills execute through container sandbox.
- [x] Terminal approval prompt supports deterministic choices:
  - [x] `run_once`
  - [x] `always_allow`
  - [x] `deny`
- [x] Security denials and approval failures are presented as high-visibility security alerts.

`Internal engineering tasks`
- [x] Plugin contract + loading:
  - [x] define versioned plugin entrypoint interface (typed request/response envelope)
  - [x] enforce plugin metadata/entrypoint validation at load or first invoke
  - [x] deterministic plugin contract errors (`plugin_contract_invalid`)
- [x] Container runner:
  - [x] implement container-only executor adapter via Docker Python SDK (no subprocess path)
  - [x] select pinned default runner image from global config (digest required)
  - [x] enforce resource limits (timeout/cpu/memory/output caps)
  - [x] enforce no-network default
  - [x] enforce read-only root + explicit `/input` and `/output` boundaries
  - [x] enforce non-root user and explicit env allowlist
- [x] Security preflight:
  - [x] add hard-deny static checks for banned patterns/categories
  - [x] emit deterministic `security_preflight_denied` with stable diagnostics
  - [x] block execution before container start on deny
- [x] Security hash:
  - [x] canonical manifest hashing for skill bundle + config/runtime identity
  - [x] include provider/policy/profile/version fingerprints
  - [x] invalidate prior approvals when hash changes
- [x] HITL flow:
  - [x] prompt approval per `(agent, skill, security_hash)`
  - [x] implement grant semantics (`run_once`, `always_allow`)
  - [x] enforce explicit HITL checkpoint for write requests
  - [x] deterministic deny path on user refusal
- [x] SQLite persistence:
  - [x] create `.lily/db/security.sqlite` initialization/migration-safe setup
  - [x] persist approval grants + provenance records
  - [x] reload and enforce grants across process restarts

`Acceptance criteria`
- [x] Untrusted plugin execution runs through container adapter only.
- [x] Runtime container path uses Docker Python SDK and does not shell out to `docker run`.
- [x] Default plugin runner image is pinned by digest and used deterministically for V1.
- [x] Hard-deny preflight failures block execution before runtime and return deterministic errors.
- [x] Approval reuse works when hash is unchanged; hash change requires new approval.
- [x] `run_once` and `always_allow` behave correctly across multiple invocations.
- [x] Write operations trigger HITL checkpoint even under `always_allow`.
- [x] Approval/provenance records persist and reload from SQLite.

`Non-goals`
- no TUI-native approval controls.
- no auto-fix/auto-rewrite for denied code.
- no generalized plugin marketplace/distribution workflow.
- no network-enabled profile rollout beyond explicitly approved test cases.

`Required tests and gates`
- [x] unit tests for plugin contract validation + deterministic contract failures.
- [x] integration tests for container execution success/timeout/crash paths.
- [x] tests asserting Docker SDK path is used (no subprocess invocation in runtime path).
- [x] tests for image-selection contract (pinned digest required; invalid image config fails deterministically).
- [x] unit/integration tests for preflight hard-deny behavior.
- [x] unit tests for security hash determinism + invalidation behavior.
- [x] integration tests for HITL grant semantics (`run_once`/`always_allow`/`deny`).
- [x] integration tests for write-checkpoint enforcement.
- [x] SQLite persistence/reload tests for approvals/provenance.
- [x] CLI rendering tests for Phase 3 security/approval alerts.
- [x] `just quality-check`.
- [x] `just docs-check`.

---

## Gate S3: Phase 4 Alignment (Must Pass Before Typed-Contract Rollout)

`User-visible features`
- None (alignment gate only).

`Internal engineering tasks`
- [x] Confirm Phase 4 locked scope from spec:
  - [x] complete typed I/O contracts across all supported skill execution paths
  - [x] add contract conformance suite and deterministic envelope regression tests
  - [x] wire conformance checks into CI gate path
- [x] Confirm low-friction authoring contract (required):
  - [x] tiny tool additions remain a small edit path (tool implementation + registry + SKILL declaration)
  - [x] no manual hand-editing of generated contract snapshots in normal flow
  - [x] no extra policy/security ceremony beyond existing Phase 3 controls
- [x] Confirm LangChain interoperability scope:
  - [x] add `LangChain -> Lily` wrapper adapter
  - [x] add `Lily -> LangChain` wrapper adapter
  - [x] preserve deterministic Lily error/result envelope contract
- [x] Confirm explicit Phase 4 exclusions:
  - [x] no supervisor/subagent orchestration rollout (separate feature)
  - [x] no TUI approval UX changes (separate feature)
  - [x] no expansion of security policy model beyond Phase 3

`Acceptance criteria`
- [x] S3 checklist completed and referenced in implementation PR.
- [x] Phase 4 scope explicitly preserves low-friction tool authoring path.

`Non-goals`
- no agent orchestration feature work.
- no plugin marketplace/distribution changes.

`Required tests and gates`
- [x] `just docs-check` green before and after Phase 4 plan edits.

---

## Phase 4: Typed Contract Completion + LangChain Wrappers (`P5`)

`User-visible features`
- [x] Tool/skill failures stay deterministic while contract validation coverage expands.
- [x] Small tool changes and small tool additions keep a lightweight workflow.
- [x] LangChain-compatible tool wrappers are available for interoperability.

`Internal engineering tasks`
- [x] Typed contract completion:
  - [x] ensure all supported execution paths use typed input/output envelopes
  - [x] normalize remaining non-typed result/error paths into stable envelopes
  - [x] document contract versioning and compatibility expectations
- [x] Conformance + regression:
  - [x] add contract conformance suite for provider/tool execution boundaries
  - [x] add deterministic snapshot tests for stable codes/messages/data shape
  - [x] gate CI on conformance + regression suites
- [x] Low-friction authoring path:
  - [x] add optional `BaseToolContract` class with default method behaviors (`parse_payload`, `execute_typed`, `render_output`)
  - [x] keep direct `ToolContract` implementation supported (base class is optional, not mandatory)
  - [x] require tiny tools to override only behavior they actually need
  - [x] add minimal scaffolding command/template for new tiny tools
  - [x] add one-command contract snapshot generation/update flow
  - [x] document tiny-change workflow (`change code -> run fast gate -> done`)
- [x] LangChain interoperability adapters:
  - [x] implement `LangChain -> Lily` adapter (schema + invoke mapping)
  - [x] implement `Lily -> LangChain` adapter (StructuredTool mapping)
  - [x] map wrapper failures to deterministic Lily error envelopes
  - [x] add focused tests for args_schema and result-shape compatibility

`Acceptance criteria`
- [x] Conformance suite covers all currently supported skill execution paths.
- [x] CI includes contract conformance gate and fails deterministically on drift.
- [x] Tiny tool add/change workflow is documented and test-validated as lightweight.
- [x] Optional `BaseToolContract` path is available and verified to reduce boilerplate for simple tools.
- [x] LangChain wrapper adapters can round-trip representative tools without contract ambiguity.

`Non-goals`
- no new security trust tiers beyond Phase 3.
- no broad refactor of runtime architecture unrelated to typed contract boundaries.

`Required tests and gates`
- [x] unit tests for remaining typed contract boundary coverage.
- [x] conformance suite for provider/tool contract parity.
- [x] unit tests for optional `BaseToolContract` defaults and override behavior.
- [x] regression snapshot tests for deterministic envelopes.
- [x] adapter tests for `LangChain -> Lily` and `Lily -> LangChain`.
- [x] `just quality-check`.
- [x] `just docs-check`.

---

## Status Log

- 2026-02-17: Plan created. User selected Phase 1-only implementation start with rule-based security governance, SQLite security backend, and terminal-first HITL deferred to later phase.
- 2026-02-17: Gate S0 completed. Locked decisions and Phase 1 boundaries validated against `docs/specs/agents/skills_platform_v1.md`; scope remains Phase 1-only.
- 2026-02-17: Phase 1 completed. Added capability contract fields + loader validation, runtime capability denial for undeclared tool use, `/skills` diagnostic rendering, and terminal security-alert Rich panels; targeted unit tests plus `just quality-check` and `just docs-check` passed.
- 2026-02-17: Phase 2 detailed plan added (Gate S1 + provider-registry execution scope, acceptance criteria, non-goals, and tests/gates).
- 2026-02-17: Gate S1 and Phase 2 completed. Added provider registry (`builtin` + MCP adapter contract), provider-scoped deterministic errors, provider-aware tool dispatch/runtime metadata, capability checks supporting provider-qualified declarations, and mocked MCP routing/failure tests; `just quality-check` and `just docs-check` passed.
- 2026-02-17: Phase 3 detailed plan added (Gate S2 + containerized plugin runtime/HITL/security-hash/SQLite persistence scope, acceptance criteria, non-goals, and tests/gates).
- 2026-02-17: Gate S2 and Phase 3 completed. Added plugin provider contract validation, Docker SDK container runtime, hard-deny preflight scanner, canonical security hashing, terminal HITL approvals (`run_once`/`always_allow`/`deny`), SQLite-backed approval/provenance persistence at `.lily/db/security.sqlite`, and security alert code/render coverage; `just quality-check` and `just docs-check` passed.
- 2026-02-17: Phase 4 execution plan expanded with Gate S3 + detailed implementation scope for end-to-end typed contract completion, low-friction tool authoring workflow, and LangChain wrapper interoperability.
- 2026-02-17: Gate S3 completed. Phase 4 scope, low-friction authoring requirements (including optional `BaseToolContract`), LangChain wrapper scope, exclusions, and gate criteria were frozen before implementation; `just docs-check` passed.
- 2026-02-17: Phase 4 completed. Added optional `BaseToolContract`, LangChain wrapper adapters (`LangChain -> Lily`, `Lily -> LangChain`) with deterministic wrapper error mapping, contract conformance test lane, deterministic envelope snapshot generation/check flow, and lightweight tool authoring workflow docs; `just contract-conformance`, `just quality-check`, and `just docs-check` passed.
