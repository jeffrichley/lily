```md
# Layer 2 — Execution Graph Runtime (Kernel)
## Phased Implementation Plan (for AI Coder)

You are implementing **Layer 2 (Execution Graph Runtime)** for Project **Lily**.

### Scope (Kernel-only)
Implement a domain-neutral scheduler that:
- executes a DAG of steps
- persists `run_state.json` (atomic write)
- supports local-first executors (start with local commands)
- captures per-step logs
- supports resume and bounded retries

### Out of Scope (do NOT implement)
- Gates (Layer 3)
- Routing policies (Layer 4)
- Plugin packs (Layer 6)
- Domain semantics (“coding”, “research”, etc.)
- LLM executors
- Artifact selection logic (“latest of type X”)
- Deleting artifacts during replay (immutability stays)

### Constraints (non-negotiable)
- Keep PRs small: **one phase per PR**
- Use existing Typer/Rich conventions where needed, but **CLI is optional** in Layer 2
- Use stdlib only (no new deps)
- No premature abstractions, no refactors outside Layer 2

---

## Phase 2.1 — Data Models: StepSpec + GraphSpec (no runner)
Goal: define the typed spec for a runnable DAG.

### Tasks
- [x] Add `src/lily/kernel/graph_models.py` (or your project’s preferred module) containing:
  - [x] `RetryPolicy` (max_retries, backoff_s optional)
  - [x] `TimeoutPolicy` (timeout_s optional)
  - [x] `ExecutorSpec` (start with `kind="local_command"` + argv/cwd/env)
  - [x] `StepSpec` (step_id, name, description?, depends_on, input_artifact_ids, output_schema_ids, executor, retry_policy, timeout_policy)
  - [x] `GraphSpec` (graph_id, steps)
- [x] Add validation helpers:
  - [x] unique step_id enforcement
  - [x] depends_on references must exist
  - [x] cycle detection (fail fast)

### Tests
- [x] `tests/unit/test_graph_models.py`
  - [x] unique step ids enforced
  - [x] missing dependency step id fails
  - [x] cycle is detected (simple 2–3 node cycle)
  - [x] valid DAG passes

### Acceptance Criteria
- [x] `GraphSpec` can be constructed from dict/json and validated
- [x] Validation errors are clear
- [x] Unit tests pass

---

## Phase 2.2 — RunState Models + Atomic Persistence (no runner)
Goal: define runtime state and persist it safely under the run directory.

### Tasks
- [x] Add `src/lily/kernel/run_state.py` containing:
  - [x] `StepStatus` enum: pending, running, succeeded, failed, skipped (skipped optional but ok)
  - [x] `StepRunRecord` (status, attempts, started_at, finished_at, last_error?, produced_artifact_ids, log_paths)
  - [x] `RunStatus` enum: created, running, blocked, failed, succeeded
  - [x] `RunState` (run_id, status, graph_id, current_step_id?, step_records dict, updated_at)
- [x] Implement RunState persistence:
  - [x] `load_run_state(run_root) -> RunState | None`
  - [x] `save_run_state_atomic(run_root, state) -> None` (write temp → fsync → rename)
- [x] Ensure run_state lives at:
  - [x] `.iris/runs/<run_id>/run_state.json`

### Tests
- [x] `tests/unit/test_run_state.py`
  - [x] save then load round-trip
  - [x] atomic write behavior (at least: file exists and parses; no partial writes)
  - [x] default initialization helper (optional): create empty state for graph

### Acceptance Criteria
- [x] RunState persists deterministically
- [x] JSON is parseable after write
- [x] Unit tests pass

---

## Phase 2.3 — Local Command Executor (no scheduling yet)
Goal: execute a single local-command step and capture logs to run folder.

### Tasks
- [x] Add `src/lily/kernel/executors/local_command.py`
  - [x] `run_local_command(executor_spec, *, run_root, step_id, attempt, timeout_s=None) -> ExecResult`
  - [x] Capture stdout/stderr to:
    - [x] `.iris/runs/<run_id>/logs/steps/<step_id>/<attempt>/stdout.txt`
    - [x] `.iris/runs/<run_id>/logs/steps/<step_id>/<attempt>/stderr.txt`
  - [x] Write `executor.json` summary (argv/cwd/env/timeout)
  - [x] Support timeout (use `subprocess.run(..., timeout=...)`)
- [x] Define `ExecResult` (success bool, returncode, error_message?, log_paths)

### Tests
- [x] `tests/unit/test_local_command_executor.py`
  - [x] successful command produces stdout log
  - [x] failing command produces stderr/returncode
  - [x] timeout produces failure and marks reason

### Acceptance Criteria
- [x] Logs are created in correct paths
- [x] Timeout works
- [x] Unit tests pass

---

## Phase 2.4 — Runner v1: Deterministic Scheduling + Bounded Retries
Goal: execute a validated DAG using RunState + local executor.

### Tasks
- [x] Add `src/lily/kernel/runner.py`
  - [x] `Runner` (or function) that takes `run_root`, `graph_spec`, and executes steps
  - [x] Eligibility rule: step pending AND all deps succeeded
  - [x] Deterministic pick order: topological + `step_id` sort (or simply pick eligible lowest step_id)
  - [x] On start: mark step running, set current_step_id, persist state
  - [x] On success: mark succeeded, persist state
  - [x] On failure:
    - [x] increment attempts
    - [x] if attempts <= max_retries: set pending and retry
    - [x] else set failed and stop run (status failed)
  - [x] Record per-attempt log paths into StepRunRecord
- [x] Runner must update RunState at each transition using atomic writes

### Tests
- [x] `tests/unit/test_runner_v1.py`
  - [x] executes a 2–3 step DAG in dependency order
  - [x] deterministic ordering for independent steps
  - [x] retry policy: a step that fails once and succeeds on retry is marked succeeded
  - [x] exceeds retries → run fails

### Acceptance Criteria
- [x] DAG executes correctly
- [x] Retries bounded and recorded
- [x] State persisted and reflects transitions
- [x] Unit tests pass

---

## Phase 2.5 — Resume Semantics (crash-safe behavior)
Goal: ensure restarting the process can continue safely.

### Tasks
- [x] Implement resume behavior in Runner:
  - [x] load existing RunState if present
  - [x] any step in `running` status → mark `failed` with reason `interrupted`
  - [x] continue execution for eligible pending steps
- [x] Ensure run status transitions are consistent:
  - [x] created → running
  - [x] running → succeeded/failed
  - [ ] (optional) blocked if no eligible steps but not complete

### Tests
- [x] `tests/unit/test_runner_resume.py`
  - [x] create state with a running step; runner marks it interrupted and proceeds
  - [x] run completes afterwards

### Acceptance Criteria
- [x] Resume works and is conservative
- [x] No “running forever” state after restart
- [x] Unit tests pass

---

## Phase 2.6 — Replay API (minimal)
Goal: support “rerun from step X” by resetting downstream statuses.

### Tasks
- [x] Add `rerun_from(state, graph, step_id) -> RunState` utility:
  - [x] mark target step and all downstream steps as pending
  - [x] clear produced_artifact_ids for those steps
  - [x] do not delete artifacts on disk
- [ ] Integrate into Runner as callable hook (no CLI required)

### Tests
- [x] `tests/unit/test_rerun_from.py`
  - [x] downstream detection correct
  - [x] statuses reset as expected

### Acceptance Criteria
- [x] Replay utility works deterministically
- [x] No artifact deletion side effects
- [x] Unit tests pass

---

## Phase 2.7 — Optional: CLI Hook (only if trivial)
Goal: provide a simple command to run a graph spec for a run.

### Tasks (optional)
- [x] `lily run graph --run-id <id> --graph <path>`
  - [x] loads GraphSpec
  - [x] calls Runner
  - [x] prints summary (Rich)

### Tests
- [ ] Optional minimal CLI smoke test (can be skipped if repo avoids CLI tests)

### Acceptance Criteria
- [x] CLI executes graph end-to-end on a toy example

---

## Global Acceptance Criteria (Layer 2)
- [x] Models exist: StepSpec, GraphSpec, RunState and are tested
- [x] Cycle detection is implemented and tested
- [x] Runner executes local-command DAG deterministically
- [x] Per-step logs are captured under run logs
- [x] RunState persists with atomic writes and supports resume
- [x] Retries bounded by policy
- [x] Replay API exists
- [x] `uv run pytest -q` passes (or repo standard)

## Notes
- Keep it universal: do not add domain-specific step semantics.
- Prefer artifact IDs (strings) for inputs.
- Output schema IDs are declarative only (enforced by gates later).
```
