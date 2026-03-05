Below is a **Layer 2 spec doc** in the same style as Layers 0–1: kernel-pure, local-first, domain-neutral, and focused on “things to build,” not hard-wired task types.

You can save this as:

`docs/kernel/layer_02_execution_graph.md`

---

# Layer 2 — Execution Graph Runtime (Kernel)

Layer 2 defines the domain-neutral **execution runtime** for the kernel:

> Step model + Graph model + RunState + Runner + Resume/Replay

It is designed to be:

* Kernel-pure (universal; no domain semantics)
* Local-first (executes steps on the local machine)
* Deterministic (given same inputs + executors)
* Resume-safe (persist state after each transition)
* Compatible with Layer 0 (artifacts/logs) and Layer 1 (envelopes/validation)

Layer 2 does **not** include:

* gates (Layer 3)
* routing policies (Layer 4)
* plugins/packs (Layer 6)
* domain-specific task templates

---

# 0. Design Principles

1. The graph runtime executes a directed graph of steps.
2. Steps are data: inputs/outputs/executor/policies.
3. The runner is the only component that mutates RunState.
4. RunState is stored under the run directory as `run_state.json` using atomic-write (Layer 0 pattern).
5. The kernel tracks “what happened” (artifacts, statuses), not “what it means.”
6. Resume must be possible after process crash at any point between steps.

---

# 1. Core Concepts

## 1.1 Step

A Step is the smallest schedulable unit in the kernel. It defines:

* Inputs: references to required artifacts
* Outputs: artifact type names expected to be produced
* Executor: how the step runs (local process / python callable / LLM executor later)
* Policies: retry and timeout limits

Kernel does not interpret the domain meaning of the step.

---

## 1.2 Graph

A Graph is a set of steps plus dependency edges:

* A step is eligible to run when all its dependencies are satisfied.
* Dependencies are explicit: no implicit ordering.

---

## 1.3 RunState

RunState captures the runtime’s current status:

* Which steps have run
* Which are pending / running / succeeded / failed
* Retry counts
* Artifact refs produced per step
* Current step (if any)

RunState enables:

* resume after crash
* replay from step N
* postmortem traceability

---

# 2. Data Models (Kernel)

## 2.1 StepId

* `step_id: str`
* Must be unique within a graph
* Stable across resumes (do not regenerate)

---

## 2.2 Artifact Requirement and Production

Layer 2 only needs references and type names; Layer 0 handles storage and Layer 1 handles envelope validation.

### Inputs

Represent inputs as **artifact IDs** (strings) for stability.

* `input_artifact_ids: list[str]`

If a step needs a specific artifact type, express it as an additional constraint:

* `input_constraints: list[ArtifactConstraint]` (optional)

`ArtifactConstraint` (optional):

* `schema_id: str`
* `selector: str | None` (reserved; can be “latest”, “by_name”, etc. later)

Keep constraints minimal in Layer 2; do not overbuild selection logic yet.

### Outputs

Outputs are declared as schema IDs (preferred) or artifact type names:

* `output_schema_ids: list[str]`

This is a declaration of expectation; it is not enforcement. Enforcement is Layer 3+.

---

## 2.3 Retry Policy

`RetryPolicy`:

* `max_retries: int` (default 0 or 1)
* `backoff_s: float` (optional; can be constant for now)
* `retry_on: list[str]` (optional string codes; for now just “any” vs “none”)

Kernel uses this only for counting and timing; error classification can remain simple.

---

## 2.4 Timeout Policy

`TimeoutPolicy`:

* `timeout_s: float | None`

If timeout triggers, the step is marked failed with reason `timeout`.

---

## 2.5 StepSpec

`StepSpec` fields:

* `step_id: str`
* `name: str` (human-friendly)
* `description: str | None`
* `depends_on: list[str]` (step IDs)
* `input_artifact_ids: list[str]`
* `output_schema_ids: list[str]`
* `executor: ExecutorSpec`
* `retry_policy: RetryPolicy`
* `timeout_policy: TimeoutPolicy`

---

## 2.6 ExecutorSpec (Local-first)

Layer 2 supports a minimal local executor set. Do not implement remote workers yet.

`ExecutorSpec` variants (choose 1–2 to start):

### A) Local command (recommended first)

* `kind: "local_command"`
* `argv: list[str]`
* `cwd: str | None`
* `env: dict[str, str] | None`

### B) Python callable (optional, later)

* `kind: "python_callable"`
* `import_path: str` (e.g., `lily.executors.foo:run`)
* `kwargs: dict[str, Any]`

Start with **local_command** only unless you already need python_callable.

---

## 2.7 GraphSpec

`GraphSpec`:

* `graph_id: str`
* `steps: list[StepSpec]`

Validation invariants:

* step_ids unique
* all depends_on references exist
* graph has at least one step
* detect cycles (must fail fast)

---

# 3. Runtime State Models

## 3.1 StepStatus

`StepStatus` enum:

* `pending`
* `running`
* `succeeded`
* `failed`
* `skipped` (optional; for replay controls)

---

## 3.2 StepRunRecord

Per step execution record:

* `step_id`
* `status`
* `attempts` (int)
* `started_at`
* `finished_at`
* `last_error: str | None`
* `produced_artifact_ids: list[str]`
* `log_paths: dict[str, str]` (stdout/stderr paths under run logs)

---

## 3.3 RunState

Stored at:

`.iris/runs/<run_id>/run_state.json`

Fields:

* `run_id`
* `status: "created" | "running" | "blocked" | "failed" | "succeeded"`
* `graph_id`
* `current_step_id: str | None`
* `step_records: dict[str, StepRunRecord]`
* `updated_at`

RunState is updated:

* when a step starts
* when a step finishes
* when a retry is scheduled
* on run completion/failure

RunState writes must use atomic-write pattern and (optionally) the run lock.

---

# 4. Runner Behavior (Kernel)

## 4.1 Eligibility

A step is eligible when:

* its status is `pending`
* all `depends_on` steps are `succeeded`

---

## 4.2 Execution Loop (Local-first)

Runner algorithm:

1. Load `GraphSpec`
2. Load or initialize `RunState`
3. While there exists eligible steps:

   * pick next eligible step (deterministic ordering: topological + step_id sort)
   * mark step `running`, persist state
   * execute via executor
   * capture stdout/stderr to run logs
   * on success:

     * record produced artifact IDs (if any were produced by the executor)
     * mark `succeeded`, persist state
   * on failure:

     * if attempts ≤ max_retries: mark `pending` and increment attempts
     * else mark `failed`, persist state and stop (or mark run failed)

Layer 2 does not attempt smart routing; it only applies retry policy.

---

## 4.3 Resume

On process restart:

* Load `RunState`
* Any `running` step is treated as `failed` with reason “interrupted” (simple + safe default)
* Continue scheduling from eligible `pending` steps

This is conservative and avoids assuming external side effects completed.

---

## 4.4 Replay Controls (Minimal)

Provide API hooks (not full CLI UX yet):

* `rerun_from(step_id)`:

  * mark that step and downstream steps as `pending`
  * clear produced_artifact_ids for those steps in RunState
  * do not delete artifacts automatically (immutability); future layers can garbage-collect if desired

Keep replay minimal; no complex partial rehydration.

---

# 5. Logging (Layer 2 Requirements)

For each step attempt, write:

`.iris/runs/<run_id>/logs/steps/<step_id>/<attempt>/`

* `stdout.txt`
* `stderr.txt`
* `executor.json` (argv/cwd/env summary)

Runner must store log paths in StepRunRecord.

---

# 6. Invariants

Layer 2 guarantees:

* GraphSpec is validated (unique IDs, no missing deps, no cycles)
* RunState is persistently updated with atomic writes
* Execution order is deterministic given same graph and same outcomes
* Steps run only when dependencies succeeded
* Retries are bounded by policy
* Resume after crash is safe (running → interrupted failure)
* Produced artifact IDs recorded per step

Layer 2 does **not** guarantee:

* correctness of step outputs (Layer 3 gates)
* artifact type correctness beyond recording IDs (Layer 1 validation can be used by executors, but runtime does not enforce semantics)

---

# 7. Done Criteria (Layer 2)

Layer 2 is complete when:

* [x] StepSpec, GraphSpec, RunState models exist and are tested
* [x] Cycle detection implemented and tested
* [x] Runner executes a simple graph of local commands
* [x] Logs captured per step attempt
* [x] RunState persists and supports resume
* [x] Retry policy enforced
* [x] Minimal replay API exists (`rerun_from`)
* [x] All tests pass

---

# 8. One-Line Summary for AI Coder

Implement Layer 2 kernel runtime: StepSpec/GraphSpec + RunState (atomic JSON) + local-command executor runner + deterministic scheduling + bounded retries + resume + per-step logs. Keep it universal; no gates/routing/plugins.
