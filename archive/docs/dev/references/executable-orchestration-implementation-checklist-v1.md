---
owner: "@team"
last_updated: "2026-03-04"
status: "active"
source_of_truth: false
---

# Executable Orchestration V1 - One-Page Implementation Checklist

Scope source of truth:
- `docs/specs/runtime/executable-orchestration-architecture-v1.md`
- `docs/specs/runtime/lily-interoperability-contract-v1.md`
- `docs/dev/references/capability-ledger.md`
- `docs/dev/references/interoperability-remediation-matrix-v1.md`

Compatibility policy:
- Backward compatibility is out of scope for this implementation.
- Legacy CLI/REPL behavior may be removed when it conflicts with interoperability standards.
- Do not add compatibility shims unless explicitly approved by the user.

## 0) Mandatory Human Review Gate (Do First)

- [x] Review current behavior for executable type: `agent`.
- [x] Review current behavior for executable type: `blueprint`.
- [x] Review current behavior for executable type: `skill`.
- [x] Review current behavior for executable type: `tool`.
- [x] Review current behavior for executable type: `job`.
- [x] Validate every finding against `docs/dev/references/interoperability-remediation-matrix-v1.md`.
- [x] Confirm standards compliance baseline for each type:
  - deterministic request/result envelopes at boundaries,
  - no silent fallback for required contract fields,
  - explicit error codes and typed payloads,
  - policy/approval enforcement where required,
  - traceability artifacts emitted.
- [x] Record findings in `docs/dev/status.md` before writing orchestration code.
- [x] If any executable type is non-compliant, add remediation items to matrix and link each to CAP IDs.

## 1) Ordered Build Checklist (Execution Plan)

## Phase 1 - Common Executable Contracts (CAP-011, CAP-012 foundation)
- [x] Add canonical envelopes and types:
  - `src/lily/runtime/executables/models.py`
  - `src/lily/runtime/executables/types.py`
  - `src/lily/runtime/executables/__init__.py`
- [x] Add unit tests:
  - `tests/unit/runtime/executables/test_executable_models.py`
- [x] Exit criteria:
  - `ExecutableRequest`, `ExecutableResult`, `GateDecision` validated and importable.

## Phase 2 - Resolver + Dispatcher Registry (CAP-004, CAP-011)
- [x] Add resolver and dispatcher:
  - `src/lily/runtime/executables/resolver.py`
  - `src/lily/runtime/executables/dispatcher.py`
- [x] Add registry-based handler interface:
  - `src/lily/runtime/executables/handlers/base.py`
- [x] Add tests:
  - `tests/unit/runtime/executables/test_resolver.py`
  - `tests/unit/runtime/executables/test_dispatcher.py`
- [x] Exit criteria:
  - no `if/elif` dispatch chain for executable kinds; registry map enforced.

## Phase 3 - Adapter Handlers For Existing Runtime (CAP-003, CAP-008, CAP-010)
- [x] Add adapters for current subsystems:
  - `src/lily/runtime/executables/handlers/skill_handler.py`
  - `src/lily/runtime/executables/handlers/tool_handler.py`
  - `src/lily/runtime/executables/handlers/blueprint_handler.py`
  - `src/lily/runtime/executables/handlers/job_handler.py`
  - `src/lily/runtime/executables/handlers/agent_handler.py`
- [x] Rework existing internals as needed; compatibility preservation is not required.
- [x] Add tests:
  - `tests/unit/runtime/executables/handlers/test_agent_handler.py`
  - `tests/unit/runtime/executables/handlers/test_skill_handler.py`
  - `tests/unit/runtime/executables/handlers/test_tool_handler.py`
  - `tests/unit/runtime/executables/handlers/test_blueprint_handler.py`
  - `tests/unit/runtime/executables/handlers/test_job_handler.py`
- [x] Exit criteria:
  - executable kinds are invoked only through dispatcher envelopes.
  - no legacy direct-call bypass remains in new orchestration path.

## Phase 4 - Supervisor Runtime MVP (CAP-011, CAP-012)
- [x] Implement supervisor plan + single-depth delegation:
  - `src/lily/runtime/orchestration/supervisor.py`
  - `src/lily/runtime/orchestration/plan_models.py`
  - `src/lily/runtime/orchestration/aggregator.py`
- [x] Integration wiring:
  - `src/lily/runtime/facade.py`
  - `src/lily/runtime/runtime_dependencies.py`
  - `src/lily/runtime/conversation_orchestrator.py` (only if needed for non-slash path)
- [x] Add tests:
  - `tests/unit/runtime/orchestration/test_supervisor.py`
  - `tests/integration/runtime/test_supervisor_delegation.py`
- [x] Exit criteria:
  - supervisor can execute at least one multi-step plan with typed handoffs.

## Phase 5 - Gate Pipeline (CAP-005, CAP-013)
- [ ] Add gate chain:
  - `src/lily/runtime/orchestration/gates.py`
  - `src/lily/runtime/orchestration/gate_models.py`
- [ ] Support outcomes:
  - `ok`, `retry`, `fallback`, `escalate`, `abort`.
- [ ] Add tests:
  - `tests/unit/runtime/orchestration/test_gates.py`
  - `tests/integration/runtime/test_gate_outcomes.py`
- [ ] Exit criteria:
  - each outcome is deterministic and test-assertable.

## Phase 6 - Jobs-To-Supervisor Bridge (CAP-014)
- [ ] Extend job target support and execution bridge:
  - `src/lily/jobs/models.py`
  - `src/lily/jobs/executor.py`
  - `src/lily/runtime/executables/handlers/job_handler.py`
- [ ] Add tests:
  - `tests/unit/jobs/test_supervisor_job_target.py`
  - `tests/e2e/test_phaseX_jobs_supervisor_bridge.py`
- [ ] Exit criteria:
  - `/jobs run <id>` can execute supervisor-targeted plan and emit trace refs.

## Phase 7 - Unified Trace + Replay (CAP-015)
- [ ] Implement orchestration trace store and replay entrypoint:
  - `src/lily/runtime/orchestration/trace_store.py`
  - `src/lily/runtime/orchestration/replay.py`
- [ ] Ensure run/step IDs and parent links are persisted for all delegated steps.
- [ ] Add tests:
  - `tests/integration/runtime/test_orchestration_trace.py`
  - `tests/integration/runtime/test_orchestration_replay.py`
- [ ] Exit criteria:
  - run-level and step-level replay are available with deterministic envelopes.

## 2) Required Gates Per Phase

- [ ] `just lint`
- [ ] `just format-check`
- [ ] `just types`
- [ ] `just test`

Before merge for each meaningful phase:
- [ ] `just quality && just test`

## 3) CAP Completion Targets

- Phase 1-2: unblock `CAP-011` foundation and harden `CAP-004` architecture.
- Phase 3: normalize `CAP-003`, `CAP-008`, `CAP-010` under common contract.
- Phase 4: deliver initial `CAP-011` + `CAP-012`.
- Phase 5: deliver `CAP-013`.
- Phase 6: deliver `CAP-014`.
- Phase 7: deliver `CAP-015`.

## 4) Stop Rules

- Stop implementation if any phase introduces warning regressions in tests/quality output.
- Stop implementation if resolver/dispatcher devolves into non-registry branching.
- Stop implementation if contracts are bypassed by direct subsystem calls in new code.
- Stop implementation if compatibility shims are introduced without explicit user approval.
