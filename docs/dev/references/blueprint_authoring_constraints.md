---
owner: "@team"
last_updated: "2026-02-19"
status: "active"
source_of_truth: true
---

# Blueprint Authoring Constraints

Purpose: define hard constraints for implementing code-defined blueprints in Lily V0.

Scope:
- blueprint implementation shape
- compile and runtime boundaries
- deterministic diagnostics and error behavior

## 1. Blueprint Contract Requirements

Every blueprint implementation must declare:
- `id`: stable blueprint id (for example `council.v1`)
- `version`: explicit blueprint version string
- `summary`: concise purpose description
- `bindings_schema`: Pydantic model for compile-time bindings
- `input_schema`: Pydantic model for execution input
- `output_schema`: Pydantic model for execution output
- `compile(bindings)`: compile method returning executable runnable/graph

All schema fields must be concrete `BaseModel` subclasses.

## 2. Compile-Time Constraints

Compile must be deterministic and side-effect free:
- validate bindings via `bindings_schema`
- resolve dependencies by explicit ids only
- fail fast for unresolved dependencies
- return deterministic `blueprint_compile_failed` errors when unresolved

Compile must not:
- execute external side effects
- mutate session or persistent stores
- hide unresolved dependency errors

## 3. Runtime Constraints

Execution must:
- validate raw input via `input_schema`
- produce `BlueprintRunEnvelope` output
- include deterministic `status`, `artifacts`, `references`, and `payload`
- serialize payload in stable JSON-compatible shape

Execution failures must:
- return `blueprint_execution_failed` with structured diagnostics
- avoid unhandled exceptions crossing public runtime boundary

## 4. Error Code Contract

Reserved blueprint codes:
- `blueprint_not_found`
- `blueprint_bindings_invalid`
- `blueprint_compile_failed`
- `blueprint_execution_failed`
- `blueprint_contract_invalid`

Rules:
- use stable code names exactly
- do not overload one code for multiple failure classes
- include `data` payload with machine-usable context when available

## 5. Policy and Security Boundaries

Blueprint logic cannot bypass existing security policy boundaries:
- provider/capability checks remain authoritative
- side effects requiring HITL approval must still gate before execution
- prompt text alone is never policy enforcement

## 6. Observability and Operator UX

Blueprint errors must remain operator-visible:
- CLI should render high-visibility `Blueprint Diagnostic` panel for `blueprint_*` codes
- include code, message, and optional structured data payload
- preserve reproducibility through run artifacts once Jobs runtime is wired

## 7. Testing Requirements

Minimum test coverage for a new blueprint:
- compile success path
- compile unresolved dependency path
- execution success path
- execution invalid input path
- failure containment path (if blueprint is multi-step/parallel)
- deterministic envelope assertions

Required quality gates:
- `just quality-check`
- `just contract-conformance` (where envelope contracts apply)

## 8. V0 Non-Goals

- no blueprint template DSL as execution truth
- no dynamic code generation of blueprints
- no hidden fallback that changes strategy without explicit configuration

