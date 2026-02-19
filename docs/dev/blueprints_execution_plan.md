---
owner: "@team"
last_updated: "2026-02-18"
status: "active"
source_of_truth: true
---

# Blueprints Execution Plan

Purpose: phased delivery tracker for `docs/specs/blueprints/blueprint_spec_v0.md`.

## Scope Lock

This plan covers blueprint substrate only.
Job scheduling/triggering is tracked separately in `docs/dev/jobs_execution_plan.md`.

## Phase B0: Blueprint Runtime Contract

Phase checklist:
- [x] define `Blueprint` interface and registry contract
- [x] implement deterministic blueprint resolution by id
- [x] implement typed bindings/input/output schema contract hooks
- [x] add stable blueprint error mapping
- [x] add registry resolution unit tests
- [x] add bindings schema validation unit tests
- [x] add deterministic error envelope tests
- [x] pass `just quality-check`

User-visible features:
- none (internal foundation).

Internal engineering tasks:
- define `Blueprint` interface and registry contract.
- implement deterministic blueprint resolution by id.
- implement typed bindings/input/output schema contract hooks.
- add stable blueprint error mapping.

Acceptance criteria:
- blueprint registry resolves known ids deterministically.
- unknown ids fail with `blueprint_not_found`.
- invalid bindings fail with `blueprint_bindings_invalid`.

Non-goals:
- no job integration yet.
- no blueprint DSL/template loading.

Required tests and gates:
- registry resolution unit tests.
- bindings schema validation unit tests.
- deterministic error envelope tests.
- `just quality-check`.

## Phase B1: Council Blueprint V1

Phase checklist:
- [x] implement `council.v1` compile path (map/reduce)
- [x] enforce typed specialist outputs for synthesizer input
- [x] add deterministic summary payload contract for council output
- [x] add council compile/execute integration tests
- [x] add failure containment tests
- [x] add envelope snapshot tests
- [x] pass `just quality-check`
- [x] pass `just contract-conformance`

User-visible features:
- one reusable council blueprint execution path is available.

Internal engineering tasks:
- implement `council.v1` compile path (map/reduce).
- enforce typed specialist outputs for synthesizer input.
- add deterministic summary payload contract for council output.

Acceptance criteria:
- `council.v1` executes with 2+ specialists and synthesizer.
- specialist failure containment is deterministic and surfaced.
- output envelope remains contract-conformant.

Non-goals:
- no additional blueprint families.
- no autonomous recursive councils.

Required tests and gates:
- council compile/execute integration tests.
- failure containment tests.
- envelope snapshot tests.
- `just quality-check`.
- `just contract-conformance`.

## Phase B2: Blueprint Governance and Docs

Phase checklist:
- [ ] document blueprint authoring constraints
- [ ] add `/skills`-style operator diagnostics patterns for blueprint failures
- [ ] publish blueprint runbook references and troubleshooting paths
- [ ] add CLI diagnostics rendering tests
- [ ] pass docs validation via `just quality-check`

User-visible features:
- clear operator diagnostics for blueprint validation and execution failures.

Internal engineering tasks:
- document blueprint authoring constraints.
- add `/skills`-style operator diagnostics patterns for blueprint failures.
- publish blueprint runbook references and troubleshooting paths.

Acceptance criteria:
- blueprint failures render deterministic operator-facing diagnostics.
- docs and examples are discoverable via canonical docs map.

Non-goals:
- no new blueprint types beyond council.

Required tests and gates:
- CLI diagnostics rendering tests.
- docs validation (`just docs-check` through `just quality-check`).

## Milestone Checklist

- [x] B0 complete
- [x] B1 complete
- [ ] B2 complete

## Decision Log

- 2026-02-18: locked code-defined blueprints for V0 (no blueprint DSL/templates in execution truth).
- 2026-02-18: locked initial blueprint family to `council.v1` for first shipped slice.
- 2026-02-18: B0 completed with `Blueprint` contract, deterministic registry, binding validation, unit coverage, and green quality gate.
- 2026-02-19: B1 completed with `council.v1` compile/execute map-reduce path, typed specialist/synthesis contracts, deterministic run envelope output, failure containment tests, and green `quality-check` + `contract-conformance` gates.
