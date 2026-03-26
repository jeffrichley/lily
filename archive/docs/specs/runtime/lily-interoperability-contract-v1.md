---
owner: "@jeffrichley"
last_updated: "2026-03-04"
status: "active"
source_of_truth: true
---

# Lily Interoperability Contract V1

Last updated: 2026-03-04  
Status: Draft (implementation authority for orchestration interoperability)

## 1. Purpose

Define the standards-compliant interoperability contract for Lily executable systems so Lily can:

1. Reuse ecosystem assets with minimal translation.
2. Execute heterogeneous targets (`agent`, `tool`, `skill`, `workflow`, `blueprint`, `job`) through one runtime contract.
3. Preserve deterministic policy, audit, and replay guarantees.

## 2. Scope

In scope:

- Runtime invocation contracts.
- Adapter model for non-standard executable types.
- Mapping to external standards (Agent Skills, OpenAI tools/MCP/Codex patterns).
- Compliance rules for import/export and execution.

Out of scope:

- Product UX copy and UI details.
- Provider-specific prompt tuning.
- Legacy compatibility shims outside V1 boundaries.

## 3. Normative Language

The keywords `MUST`, `MUST NOT`, `SHOULD`, `SHOULD NOT`, and `MAY` are normative.

## 4. External Standards Baseline

### 4.1 Skills

Lily `skill` interoperability `MUST` support Agent Skills format:

- canonical `SKILL.md` with valid frontmatter.
- progressive disclosure loading (metadata first, body on activation).
- optional assets (`scripts/`, `references/`, `assets/`) through explicit access policy.

### 4.2 Tools

Lily tool interoperability `MUST` align to OpenAI tool execution semantics:

- structured tool declaration and argument schema.
- explicit tool result envelope (success/error, machine-readable code).
- policy gates before execution (approval/allowlist/sandbox).

### 4.3 MCP

Lily `MUST` treat MCP as first-class external capability transport:

- support registered MCP servers with explicit policy config.
- allow tool allowlisting/filtering per server.
- require deterministic failures for auth/transport/policy errors.

### 4.4 Agents

Lily `agent` interoperability `SHOULD` align with role-based multi-agent orchestration:

- supervisor role for planning and aggregation.
- worker role for delegated bounded execution.
- typed handoff envelopes.

### 4.5 Workflow/Blueprint/Job

No cross-vendor canonical spec currently exists for `blueprint` and `job`.  
Lily therefore `MUST` expose these via Lily-native adapters that present the same invocation envelope as standardized executable kinds.

## 5. Canonical Executable Contract

All executable kinds `MUST` implement one runtime interface through equivalent envelopes:

1. `ExecutableRef`: stable target identity (`kind`, `id`, `version` optional).
2. `ExecutableRequest`: caller, objective, inputs, policy context, trace context.
3. `ExecutableResult`: status, outputs, structured errors, provenance fields.
4. `GateDecision`: deterministic policy outcome (`ok`, `retry`, `fallback`, `escalate`, `abort`).

Caller code `MUST NOT` branch on concrete implementation details after handoff to resolver/dispatcher.

## 6. Resolver and Dispatcher Rules

1. Caller submits intent + optional target hints.
2. Resolver determines final executable binding.
3. Dispatcher invokes kind-specific handler through registry strategy.

Requirements:

- Supervisor/planner `SHOULD` translate user intent into explicit target ids before resolver dispatch when confidence is sufficient.
- Supervisor/planner `MUST` emit schema-validated typed execution plans/handoffs at orchestration boundaries.
- Supervisor runtime `MUST` own executable invocation; planner/tool loops `MUST NOT` directly execute orchestration steps as the primary control path.
- Planner feedback for replanning/summarization `SHOULD` use typed execution digests by default (status, key outputs/errors, gate decisions, references/artifacts), not full raw step history unless explicitly required.
- Resolver `MUST` remain deterministic binding/validation logic, not an LLM-style intent interpreter.
- Executable ids `MUST` be unique within resolver scope.
- Duplicate-id collisions `MUST` fail with deterministic ambiguity errors (`resolver_ambiguous`), never silent tie-breaking.
- Hints (`kind`, partial target refs) `MUST` remain supported for non-supervisor callers and partial-target execution paths.
- Resolver decisions `MUST` be traceable and reproducible from stored context.
- Dispatcher `MUST` be map/registry based (no long `if/elif` chains).
- All unresolved/ambiguous bindings `MUST` return deterministic error envelopes.

## 7. Kind-Specific Adapter Contract

## 7.1 `agent`

- `MUST` accept delegated objective and bounded context.
- `MUST` return typed result with explicit completion status.
- `MUST` preserve supervisor authority boundaries.

## 7.2 `tool`

- `MUST` expose input schema and deterministic output envelope.
- `MUST` execute under policy gates.
- `MUST` map provider exceptions to stable error codes.

## 7.3 `skill`

- `MUST` resolve from skill metadata contract.
- `MUST` support activation-time loading of instruction body.
- `SHOULD` support both local and MCP-backed skill tool usage.

## 7.4 `workflow`

- `MUST` define a deterministic step graph and transition policy.
- `MUST` emit per-step trace entries.
- `SHOULD` support replay from persisted state boundaries.

## 7.5 `blueprint` (Lily-native adapter)

- `MUST` compile blueprint definition into a runtime execution plan.
- `MUST` emit identical envelope semantics as other executable kinds.
- `MUST` support policy gates at step boundaries.
- `MUST NOT` bypass resolver/dispatcher.

## 7.6 `job` (Lily-native adapter)

- `MUST` execute non-interactively and produce terminal status.
- `MUST` emit durable artifacts/events for audit and replay.
- `MUST` support scheduler-triggered and direct-triggered invocation paths.
- `MUST` expose retry/failure semantics through `GateDecision` and result codes.

## 8. Security and Policy Invariants

All executable kinds `MUST` conform to one policy pipeline:

1. Preflight validation.
2. Trust and capability checks.
3. Approval and allowlist checks.
4. Execution with sandbox constraints.
5. Post-execution provenance capture.

Policy outcome behavior:

- Blocked execution `MUST` fail closed with deterministic machine-readable codes.
- Approved execution `MUST` preserve policy evidence in trace.

## 9. Observability and Replay

Every invocation `MUST` write:

1. Correlation IDs (run id, step id, parent id).
2. Resolver decision record.
3. Gate decisions and rationale.
4. Handler result envelope.
5. Artifact references and timestamps.

Replay requirements:

- System `MUST` support deterministic replay for supported executable kinds.
- Replay `MUST` identify non-deterministic segments explicitly.

## 10. Import/Export Interoperability Policy

Import:

- Agent Skills packages: `MUST` validate metadata contract before activation.
- MCP tools: `MUST` enforce server policy before registration.

Export:

- Lily executables `SHOULD` be exportable as portable descriptors when possible.
- Lily-native `blueprint` and `job` `MAY` require adapter metadata to round-trip.

## 11. Compliance Matrix

Minimum V1 compliance targets:

1. `agent`: compliant via supervisor/worker handoff envelopes.
2. `tool`: compliant via typed tool dispatch + policy gate.
3. `skill`: compliant with Agent Skills loading/activation semantics.
4. `workflow`: compliant with step graph + trace/replay.
5. `blueprint`: compliant through Lily blueprint adapter.
6. `job`: compliant through Lily job adapter and durable artifacts.

A kind is not V1-complete until it passes:

- contract tests.
- policy gate tests.
- trace/replay verification tests.

## 12. Implementation Linkage

This contract is implemented through:

- `docs/specs/runtime/executable-orchestration-architecture-v1.md`
- `docs/dev/references/executable-orchestration-implementation-checklist-v1.md`
- `.ai/PLANS/014-executable-orchestration-v1-e2e.md`

Any deviation from this contract `MUST` be documented with rationale and explicit CAP linkage before merge.
