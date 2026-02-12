# Layer 3 — Gates (Verification)
## Phased Implementation Plan (for AI Coder)

You are implementing **Layer 3 (Gates / Verification)** for Project **Lily**.

This layer is the **trust engine** of the kernel.

It must be:
- Domain-neutral
- Deterministic (local-first)
- Fully integrated with Layer 2 Runner
- Strict about pass/fail enforcement

---

# Scope (Kernel-only)

Implement:

- GateSpec
- GateResult schema (`gate_result.v1`)
- Local-command GateRunner
- GateEngine
- Integration with Runner (post-step verification)
- Logging + artifact storage of gate outputs

---

# Out of Scope (Do NOT implement)

- LLM gates
- Hybrid gates
- Routing policies beyond pass/fail
- Automatic retries triggered by gates
- Domain-specific gates (ruff, mypy, etc.)
- Plugin system
- UI/CLI for gate config
- Workspace diff logic
- Complex artifact selection

---

# Global Constraints

- One phase per PR
- Keep models pure (no IO inside models)
- Use existing Layer 0 (ArtifactStore) and Layer 1 (Envelope + Registry)
- No new dependencies
- All logs must be persisted under run logs
- All GateResults must be stored as envelopes

---

# Phase 3.1 — GateResult Schema + Models (No Execution Yet)

## Goal
Define the data models and register the `gate_result.v1` schema.

---

## Tasks

- [x] Add `src/lily/kernel/gate_models.py`
  - [x] Define `GateStatus` enum: `passed`, `failed`
  - [x] Define `GateResultPayload` Pydantic model:
    - `gate_id: str`
    - `status: GateStatus`
    - `reason: str | None`
    - `log_artifact_ids: list[str]`
    - `metrics: dict[str, float] | None`
    - `timestamp: datetime`
- [x] Register schema in SchemaRegistry:
  - schema_id: `gate_result.v1`
  - model: `GateResultPayload`

---

## Tests

- [x] `tests/unit/test_gate_models.py`
  - [x] Payload validates correctly
  - [x] Missing required fields fail
  - [x] Invalid status fails
  - [x] SchemaRegistry can validate gate_result.v1

---

## Acceptance Criteria

- [x] `gate_result.v1` schema registered
- [x] Validation works
- [x] Tests pass

---

# Phase 3.2 — GateSpec + Runner Spec (No Integration Yet)

## Goal
Define GateSpec and GateRunnerSpec (local-command only).

---

## Tasks

- [x] Add `GateRunnerSpec`
  - `kind: Literal["local_command"]`
  - `argv: list[str]`
  - `cwd: str | None`
  - `env: dict[str, str] | None`
  - `timeout_s: float | None`
- [x] Add `GateSpec`
  - `gate_id: str`
  - `name: str`
  - `description: str | None`
  - `inputs: list[str]` (artifact IDs)
  - `workspace_required: bool`
  - `runner: GateRunnerSpec`
  - `required: bool = True`

- [x] Validate:
  - unique gate_id in a list
  - runner.kind == "local_command"

---

## Tests

- [x] `tests/unit/test_gate_spec.py`
  - [x] Valid GateSpec constructs
  - [x] Missing fields fail
  - [x] Invalid runner kind fails

---

## Acceptance Criteria

- [x] GateSpec exists and validates
- [x] Tests pass

---

# Phase 3.3 — Local Command GateRunner (Standalone)

## Goal
Execute a gate as a local command and return structured result (no Runner integration yet).

---

## Tasks

- [x] Add `src/lily/kernel/gate_runner.py`
  - [x] `run_local_gate(gate_spec, run_root, attempt) -> GateExecutionResult`
  - [x] Capture stdout/stderr under:
    - `.iris/runs/<run_id>/logs/gates/<gate_id>/<attempt>/`
  - [x] Write `runner.json` summary
  - [x] Respect timeout
  - [x] Return:
    - success bool
    - returncode
    - log file paths

- [x] No envelope creation yet (just execution result struct)

---

## Tests

- [x] `tests/unit/test_gate_runner.py`
  - [x] Successful command passes
  - [x] Failing command fails
  - [x] Timeout fails
  - [x] Logs created

---

## Acceptance Criteria

- [x] GateRunner works standalone
- [x] Logs are written correctly
- [x] Tests pass

---

# Phase 3.4 — GateEngine + Envelope Creation

## Goal
Convert GateRunner results into GateResult envelopes and store them via ArtifactStore.

---

## Tasks

- [x] Add `GateEngine`
  - [x] `execute_gate(gate_spec, run_root, artifact_store, registry, attempt=1)`
  - [x] Run gate
  - [x] Store logs as artifacts
  - [x] Build `GateResultPayload`
  - [x] Use `put_envelope()` to store result
  - [x] Return artifact_id of GateResult

- [x] Ensure:
  - payload_sha256 computed correctly
  - envelope validated before returning

---

## Tests

- [x] `tests/unit/test_gate_engine.py`
  - [x] Success gate produces passed GateResult
  - [x] Failed gate produces failed GateResult
  - [x] Envelope stored and validated

---

## Acceptance Criteria

- [x] Every gate produces a GateResult envelope
- [x] Logs stored as artifacts
- [x] Tests pass

---

# Phase 3.5 — Integrate Gates into Runner

## Goal
Modify Layer 2 Runner to execute gates after successful step execution.

---

## Tasks

- [x] Extend `StepSpec` to optionally include:
  - `gates: list[GateSpec]`
- [x] Update Runner logic:
  - After step success:
    - For each gate:
      - Call GateEngine
      - Record GateResult artifact ID in StepRunRecord
    - If any required gate fails:
      - Mark step as failed
      - Update RunState
      - Stop run (status failed)
- [x] Ensure:
  - Gate failures do NOT bypass retry policy of step itself
  - Required gate failure blocks progression

---

## Tests

- [x] `tests/unit/test_runner_with_gates.py`
  - [x] Step succeeds and gates pass → run continues
  - [x] Required gate fails → run fails
  - [x] Non-required gate fails → run continues
  - [x] Gate results recorded in RunState

---

## Acceptance Criteria

- [x] Runner executes gates after step success
- [x] Required gate failure blocks step completion
- [x] GateResult artifact IDs recorded
- [x] Tests pass

---

# Phase 3.6 — Optional: Run-Level Gates

## Goal
Allow GraphSpec to define run-level gates executed after all steps succeed.

---

## Tasks

- [x] Extend `GraphSpec` with:
  - `run_gates: list[GateSpec] | None`
- [x] After all steps succeed:
  - Execute run_gates
  - Apply required logic (failure → run failed)

---

## Tests

- [x] `tests/unit/test_run_level_gates.py`
  - [x] Run-level gate passes → run succeeded
  - [x] Required run-level gate fails → run failed

---

## Acceptance Criteria

- [x] Run-level gates execute correctly
- [x] Failures propagate properly
- [x] Tests pass

---

# Global Done Criteria (Layer 3)

- [x] GateSpec implemented and validated
- [x] `gate_result.v1` schema registered
- [x] Local-command GateRunner implemented
- [x] GateEngine produces and stores GateResult envelopes
- [x] Runner integrates gates post-step
- [x] Required gates block progression
- [x] Logs persisted under run logs
- [x] All tests pass
- [x] No domain-specific logic introduced

---

# Final Reminder to AI Coder

Do not:
- Implement LLM gates
- Add routing logic
- Add smart retries
- Add plugin hooks
- Modify Layer 0 or Layer 1 behavior
- Add new dependencies

Implement strictly the phases above.
One PR per phase.
Keep it kernel-pure.
