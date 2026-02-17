---
owner: "@team"
last_updated: "2026-02-17"
status: "active"
source_of_truth: true
---

# Skills Platform V1

Status: Proposed  
Date: 2026-02-17  
Scope: skill capability contracts, provider registry, isolated code-backed skills, security policy, and typed I/O governance.

## 1. Why This Feature Exists

Current skills support basic `llm_orchestration` and `tool_dispatch`, but lack:
- explicit capability declarations and enforcement.
- unified provider abstraction for builtin/MCP/plugin tools.
- isolated code-backed skill runtime with security controls.
- full typed contracts across skill execution boundaries.

This feature establishes a secure, deterministic, extensible skills substrate.

## 2. Locked Decisions (V1)

1. Untrusted skill code runs in containers only.
2. V1 ships one basic profile only: `safe_eval`.
3. Preflight policy is hard-deny only.
4. Security approvals are keyed by `(agent_id, skill_id, security_hash)`.
5. Approval modes are `run_once` and `always_allow`; HITL is default-on.
6. Write operations are denied by default and require HITL checkpoint.
7. Durable backend for approval/provenance is SQLite.
8. TUI approval UX is deferred; terminal prompt is in scope.

## 3. Architecture Contract

## 3.1 Skill Capability Contract

Each skill declares:
- invocation mode.
- tool/provider dependencies.
- typed I/O contract references.
- isolation and execution policy fields.

Loader validates contracts at snapshot build time; runtime enforces grants at invoke time.

## 3.2 Provider Registry

Use strategy/registry dispatch, not long conditionals:
- `builtin` provider.
- `mcp` provider.
- `plugin` provider.

Resolution path:
1. validate capability declaration.
2. resolve provider + tool id.
3. enforce policy/grant checks.
4. execute typed request.
5. validate typed response.
6. normalize deterministic envelope.

## 3.3 Security and Isolation

- Container boundary for untrusted code.
- No network by default.
- Read-only root FS with explicit `/input` read and `/output` write boundaries.
- Resource limits (CPU/memory/timeout/stdout-stderr caps).
- Deterministic deny codes for policy/preflight failures.

## 3.4 Security Hash (Locked)

`security_hash` includes:
- `SKILL.md` full content.
- declared plugin executable source files.
- skill metadata/capability contract.
- execution profile + policy version.
- container image digest.
- dependency lock fingerprint.
- declared behavior-affecting config/assets.

Canonical process:
- build sorted file manifest with digests.
- serialize canonical JSON payload.
- compute SHA-256.

Any hash change invalidates prior approval grants.

## 3.5 Durable Governance Data

Persist in SQLite:
- approval grants (`run_once`, `always_allow`) keyed by `(agent, skill, hash)`.
- provenance receipts (hashes, limits, outcome, capped logs metadata).

## 4. Migration Plan (Fixed Scope)

## Phase 1: Capability Contracts + Enforcement

User-visible features:
- `/skills` diagnostics show capability validation failures.

Internal engineering tasks:
- extend frontmatter/types for capability contract.
- add load-time validation + deterministic diagnostics.
- add invoke-time capability grant enforcement.

Acceptance criteria:
- malformed/underdeclared skills are excluded with deterministic diagnostics.
- undeclared tool access fails deterministically.
- existing bundled skills migrate without behavior regression.

Non-goals:
- no provider plugins yet.
- no container runner yet.

Required tests and gates:
- skill frontmatter/type validation tests.
- capability enforcement unit tests.
- `just quality-check` and `just docs-check`.

## Phase 2: Provider Registry (Builtin + MCP)

User-visible features:
- skills invoke tools via declared provider path.

Internal engineering tasks:
- implement provider interface and registry map.
- route existing builtin tools via provider interface.
- add MCP adapter contract with deterministic error mapping.

Acceptance criteria:
- registry-based dispatch is used end-to-end.
- builtin tools remain behavior-compatible.
- unresolved provider/tool returns deterministic codes.

Non-goals:
- no code-backed plugin execution yet.

Required tests and gates:
- registry dispatch unit tests.
- builtin + mocked MCP integration tests.
- `just quality-check`.

## Phase 3: Containerized Plugin Runtime + HITL

User-visible features:
- terminal HITL prompt supports `run_once`, `always_allow`, `deny`.
- eligible skills can run plugin-backed tools in container sandbox.

Internal engineering tasks:
- implement plugin entrypoint contract.
- implement container runner + IPC envelope.
- add preflight hard-deny checks.
- add `security_hash` generation + approval cache/store.
- enforce write requests as explicit HITL checkpoint.
- persist approvals/provenance in SQLite.

Acceptance criteria:
- untrusted plugin execution is container-only.
- unchanged hash can run under cached grant; changed hash requires new approval.
- preflight denies fail before execution with deterministic codes.
- write requests always trigger HITL checkpoint.

Non-goals:
- no subprocess fallback.
- no auto-rewrite remediation flow.
- no TUI approval controls.

Required tests and gates:
- container runner integration tests (ok/timeout/crash).
- security preflight deny tests.
- hash approval caching tests.
- SQLite persistence/reload tests.
- profile/resource/path enforcement tests.
- `just quality-check`.

## Phase 4: End-to-End Typed Contract Completion

User-visible features:
- consistent typed contract behavior across all skill execution paths.

Internal engineering tasks:
- complete typed I/O for remaining non-typed skill paths.
- add conformance suite for skill/provider I/O.
- add regression snapshots for stable error envelopes.

Acceptance criteria:
- conformance suite covers all supported skill execution paths.
- typed-contract debt is closed or explicitly narrowed.
- CI includes contract conformance gate.

Non-goals:
- no supervisor/subagent orchestration in this feature.

Required tests and gates:
- contract conformance suite.
- deterministic envelope snapshot tests.
- `just quality-check` and `just ci-gates`.

## 5. Deferred Items

- Future `yolo` mode (owner/date TBD).
- TUI approval controls (tracked under TUI feature).

