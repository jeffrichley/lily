---
owner: "@jeffrichley"
last_updated: "2026-03-04"
status: "active"
source_of_truth: false
---

# Interoperability Remediation Matrix V1

Purpose: convert current non-compliance findings into executable remediation work mapped to CAP targets.

Compatibility posture:
- Backward compatibility is explicitly out of scope for this effort.
- Legacy CLI/REPL behavior may be removed or changed when it conflicts with interoperability standards.
- Do not add compatibility shims unless explicitly approved by the user.

## Compliance Gaps By Executable Type

| Executable type | Compliance status | Critical gaps | CAP mapping |
| --- | --- | --- | --- |
| `agent` | Partial | supervisor runtime exists with typed plan/handoff contracts, but gate pipeline/trace-replay/full runtime path integration remains incomplete | `CAP-011`, `CAP-012`, `CAP-013`, `CAP-015` |
| `tool` | Partial | MCP is stubbed by default, no first-class MCP server policy registry | `CAP-004`, `CAP-005`, `CAP-013` |
| `skill` | Partial | metadata schema diverges from Agent Skills import expectations, body loaded at snapshot-time not activation-time | `CAP-002`, `CAP-003` |
| `workflow` | Missing | no first-class workflow executable kind with deterministic step trace model | `CAP-011`, `CAP-015` |
| `blueprint` | Partial | adapter exists, but gate pipeline and full orchestration wiring are not implemented | `CAP-010`, `CAP-011`, `CAP-013` |
| `job` | Partial | job adapter exists, but target model is blueprint-only and no supervisor bridge/trace convergence | `CAP-008`, `CAP-014`, `CAP-015` |

## Remediation Tasks (Normative)

### 1) Cross-Cutting Runtime Contract

- [x] Implement canonical executable envelopes (`ExecutableRef`, `ExecutableRequest`, `ExecutableResult`, `GateDecision`).
- [x] Implement resolver + dispatcher registry runtime.
- [x] Fail unresolved/ambiguous bindings with deterministic codes.
- [ ] Add orchestration trace/replay persistence with run/step/parent IDs.

### 2) Agent Remediation

- [x] Add supervisor runtime as sole delegator in V1.
- [x] Add typed worker handoff request/response contracts.
- [x] Enforce bounded delegation depth and authority propagation.

### 3) Tool Remediation

- [ ] Replace default MCP null resolver behavior with explicit MCP server registry wiring.
- [ ] Add per-server MCP policy config (`allowed_tools`, approvals/auth constraints).
- [ ] Normalize all provider failures to stable machine-readable result codes.
- [ ] Apply unified policy pipeline semantics across provider types where applicable.

### 4) Skill Remediation

- [ ] Add Agent Skills-compatible metadata import/normalization path.
- [ ] Support progressive disclosure: load body on activation, not snapshot build.
- [ ] Preserve deterministic eligibility and capability enforcement in activation path.

### 5) Workflow Remediation

- [ ] Introduce first-class `workflow` executable kind and handler.
- [ ] Require deterministic step graph transitions and per-step trace entries.
- [ ] Provide replay support for workflow execution boundaries.

### 6) Blueprint Remediation

- [x] Route blueprint execution through executable adapters (no direct invocation from callers in orchestration path).
- [x] Ensure blueprint compile/execute boundaries emit common executable envelopes.
- [ ] Enforce gate evaluation at blueprint step boundaries.

### 7) Job Remediation

- [ ] Extend job target kinds to include supervisor/orchestration execution path.
- [ ] Bridge scheduler and direct execution through common executable envelopes.
- [ ] Emit gate-aligned retry/failure semantics and trace references in artifacts.

## Done Criteria For This Matrix

Matrix is complete only when:

1. All rows are `Compliant`.
2. CAP-011 through CAP-015 are implemented and validated.
3. `just quality && just test` passes warning-clean.
4. No compatibility shim was introduced without explicit user approval.

## Debt Drafts Created In Phase 0

- [ ] `DRAFT-EO-001`: Supervisor/worker executable runtime and typed handoff envelopes are missing (`CAP-011`, `CAP-012`).
- [ ] `DRAFT-EO-002`: MCP provider is not first-class operational (registration/policy/allowlist/auth enforcement gap) (`CAP-004`, `CAP-013`).
- [ ] `DRAFT-EO-003`: Skill import is not Agent Skills-compatible and does not implement activation-time progressive disclosure (`CAP-002`, `CAP-003`).
- [ ] `DRAFT-EO-004`: Workflow executable kind and orchestration trace/replay coverage are missing (`CAP-011`, `CAP-015`).
