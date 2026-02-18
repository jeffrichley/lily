---
owner: "@team"
last_updated: "2026-02-18"
status: "active"
source_of_truth: true
---

# Blueprint Spec V0

Status: Proposed  
Date: 2026-02-18  
Scope: blueprint contract for reusable workflow orchestration patterns.

## 1. Why This Exists

Lily needs a reusable orchestration layer so new capabilities are configured, not hand-wired.
Blueprints provide that layer by defining stable workflow shapes with typed slots.

## 2. Definitions

- `Blueprint`: code-defined orchestration recipe that compiles to an executable graph.
- `BlueprintId`: stable identifier (for example `council.v1`).
- `BlueprintBindings`: validated runtime values bound into blueprint slots.
- `BlueprintInstance`: a concrete configured run target produced from `Blueprint + Bindings`.
- `Runnable`: any execution target implementing Run Contract R0.

## 3. Dependency Contract

Blueprints depend on:
- Skills Platform V1 contracts (`docs/specs/agents/skills_platform_v1.md`).
- Existing security policy and approval enforcement.
- Job system for scheduled/triggered execution (`docs/specs/jobs/job_spec_v0.md`).

## 4. Architecture Contract

## 4.1 V0 Shape

- Blueprints are code-defined and registry-addressable.
- No template DSL in V0.
- Optional thin metadata manifest is deferred.

## 4.2 Required Blueprint Interface

Every blueprint implementation must declare:
- `id`: stable string id.
- `version`: semantic or monotonic blueprint version.
- `summary`: concise human-readable purpose.
- `bindings_schema`: typed schema for slot bindings.
- `input_schema`: typed run input schema.
- `output_schema`: typed run output schema.
- `compile(bindings)`: builds executable graph.

## 4.3 Run Contract Alignment

All blueprint execution must return a shared top-level envelope:
- `status`
- `artifacts`
- `approvals_requested`
- `references`
- `payload` (blueprint-specific typed output)

## 4.4 Error Contract

V0 stable error codes:
- `blueprint_not_found`
- `blueprint_bindings_invalid`
- `blueprint_compile_failed`
- `blueprint_execution_failed`
- `blueprint_contract_invalid`

Errors must be deterministic and include only non-sensitive diagnostics.

## 5. V0 Blueprint Set

V0 starts with one blueprint:
- `council.v1` (map/reduce specialist workflow).

Deferred:
- `pipeline.v1`
- `plan_execute_verify.v1`

## 6. Security and Policy Contract

- Blueprint runs inherit skills/platform capability policy.
- Blueprint compile/execution cannot bypass provider/capability checks.
- Risky side effects always use approval gates before effecting writes/publish/send.

## 7. Acceptance Criteria

- `council.v1` is registered and executable through shared run contract.
- Invalid bindings fail before execution with deterministic validation errors.
- Blueprint output conforms to shared envelope and typed payload contract.
- All runs write deterministic artifacts and trace references.

## 8. Non-Goals (V0)

- No blueprint authoring DSL.
- No marketplace/plugin blueprint loading.
- No autonomous recursive blueprint spawning.
- No dynamic code generation of blueprint implementations.

## 9. Required Tests and Gates

- Registry lookup tests (`found`, `missing`, version mismatch behavior).
- Bindings schema validation tests.
- Compile failure containment tests.
- Envelope conformance tests.
- `just quality-check`
- `just contract-conformance`

## 10. Open Questions

- Whether to add thin manifests for LLM-assisted job creation in V1.x.
- Blueprint versioning compatibility policy (`strict pin` vs `compatible range`).
- Caching compiled graphs across runs vs compile-per-run defaults.

