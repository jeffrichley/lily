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
- [x] blueprint registry resolves known ids deterministically.
- [x] unknown ids fail with `blueprint_not_found`.
- [x] invalid bindings fail with `blueprint_bindings_invalid`.

Non-goals:
- no job integration yet.
- no blueprint DSL/template loading.

Required tests and gates:
- [x] registry resolution unit tests.
- [x] bindings schema validation unit tests.
- [x] deterministic error envelope tests.
- [x] `just quality-check`.

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
- [x] `council.v1` executes with 2+ specialists and synthesizer.
- [x] specialist failure containment is deterministic and surfaced.
- [x] output envelope remains contract-conformant.

Non-goals:
- no additional blueprint families.
- no autonomous recursive councils.

Required tests and gates:
- [x] council compile/execute integration tests.
- [x] failure containment tests.
- [x] envelope snapshot tests.
- [x] `just quality-check`.
- [x] `just contract-conformance`.

## Phase B2: Blueprint Governance and Docs

Phase checklist:
- [x] document blueprint authoring constraints
- [x] add `/skills`-style operator diagnostics patterns for blueprint failures
- [x] publish blueprint runbook references and troubleshooting paths
- [x] add CLI diagnostics rendering tests
- [x] pass docs validation via `just quality-check`

User-visible features:
- clear operator diagnostics for blueprint validation and execution failures.

Internal engineering tasks:
- document blueprint authoring constraints.
- add `/skills`-style operator diagnostics patterns for blueprint failures.
- publish blueprint runbook references and troubleshooting paths.

Acceptance criteria:
- [x] blueprint failures render deterministic operator-facing diagnostics.
- [x] docs and examples are discoverable via canonical docs map.

Non-goals:
- no new blueprint types beyond council.

Required tests and gates:
- [x] CLI diagnostics rendering tests.
- [x] docs validation (`just docs-check` through `just quality-check`).

## Phase B3: Synth Strategy Expansion (Deterministic + LLM)

Phase checklist:
- [x] add optional `LLMSynthesizer` implementation behind `CouncilSynthesizer` protocol
- [x] enforce deterministic fallback to baseline synthesizer on LLM unavailability/invalid output
- [x] define stable config switch for synth strategy selection
- [x] add deterministic error mapping for LLM synth failures
- [x] add strategy selection unit tests
- [x] add fallback-path integration tests
- [x] add output-envelope conformance tests for both synth strategies
- [x] pass `just quality-check`
- [x] pass `just contract-conformance`

User-visible features:
- optional higher-quality synthesis mode while preserving deterministic reliability fallback.

Internal engineering tasks:
- implement strategy wiring for deterministic and LLM synth runners.
- preserve existing deterministic synthesis as the default baseline.
- enforce typed output validation for LLM synth path before envelope emission.

Acceptance criteria:
- [x] deterministic synthesizer remains default behavior.
- [x] LLM synthesizer can be enabled explicitly via stable config.
- [x] LLM synth failure or invalid output automatically falls back deterministically.
- [x] output envelope remains contract-conformant for both strategy paths.

Non-goals:
- no autonomous self-modifying synthesis prompts.
- no silent strategy switching without explicit config.

Required tests and gates:
- [x] synth strategy selection tests.
- [x] LLM failure fallback tests.
- [x] envelope conformance tests across both synth paths.
- [x] `just quality-check`.
- [x] `just contract-conformance`.

## Milestone Checklist

- [x] B0 complete
- [x] B1 complete
- [x] B2 complete
- [x] B3 complete

## Decision Log

- 2026-02-18: locked code-defined blueprints for V0 (no blueprint DSL/templates in execution truth).
- 2026-02-18: locked initial blueprint family to `council.v1` for first shipped slice.
- 2026-02-18: B0 completed with `Blueprint` contract, deterministic registry, binding validation, unit coverage, and green quality gate.
- 2026-02-19: B1 completed with `council.v1` compile/execute map-reduce path, typed specialist/synthesis contracts, deterministic run envelope output, failure containment tests, and green `quality-check` + `contract-conformance` gates.
- 2026-02-19: B2 completed with blueprint authoring constraints doc, high-visibility CLI blueprint diagnostics, runbook and canonical-doc links, and green docs/quality gates.
- 2026-02-19: B3 completed with `synth_strategy` selection (`deterministic`/`llm`), optional `LLMSynthesizer`, deterministic fallback path, stable synthesis error mapping, expanded council tests, and green `quality-check` + `contract-conformance` gates.
- 2026-02-19: Strategy default updated by owner request: `synth_strategy` now defaults to strict `llm`; fallback-enabled behavior remains explicit under `llm_with_fallback`.
