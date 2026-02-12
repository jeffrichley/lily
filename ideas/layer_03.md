# Layer 3 — Gates (Verification)

Layer 3 defines the **verification layer** of the kernel:

> GateSpec + GateRunner + GateResult + GateEngine

This is the **trust engine** of the system.

## Scope

**Gates are:**

- First-class runtime objects
- Domain-neutral
- Deterministic (by default)
- Composable
- Bound to steps or entire runs
- Enforced by the kernel

**Layer 3 does not include:**

- Routing policy logic beyond pass/fail (Layer 4)
- Domain-specific gates (coding, research, etc.)
- Plugin pack integration (Layer 6)
- Smart remediation

---

## 0. Design Principles

1. A gate verifies artifacts or workspace state.
2. Gates do not produce domain outputs; they produce `GateResult`.
3. GateResult is an Envelope (Layer 1).
4. Gate execution must be logged and reproducible.
5. Kernel enforces required gates before a step (or run) is marked successful.
6. Gate failure halts progression unless explicitly configured otherwise.

---

## 1. Core Concepts

### 1.1 Gate

A Gate is a verification unit that:

**Consumes:**

- Artifact IDs
- Optional workspace snapshot metadata

**Executes:**

- Deterministic local tool, or
- Hybrid logic (LLM judge later)

**Produces:**

- A `GateResult` envelope

The kernel does not interpret gate semantics — only pass/fail.

### 1.2 GateResult

`GateResult` is a typed Envelope payload.

**Schema ID:** `gate_result.v1`

**Payload fields:**

| Field               | Type                    |
| ------------------- | ----------------------- |
| `gate_id`           | `str`                   |
| `status`            | `"passed"` or `"failed"` |
| `reason`            | `str` or `None`         |
| `log_artifact_ids`  | `list[str]`             |
| `metrics`           | `dict[str, float]` or `None` |
| `timestamp`         | `datetime`              |

**Rules:**

- GateResult must always be produced.
- Even failure produces GateResult.
- Logs must be stored as artifacts (Layer 0).

---

## 2. Gate Specification

### 2.1 GateSpec

| Field           | Type              | Description                           |
| --------------- | ----------------- | ------------------------------------- |
| `gate_id`       | `str`             | Unique identifier                     |
| `name`          | `str`             | Human-friendly name                   |
| `description`   | `str` or `None`   | Optional description                  |
| `inputs`        | `list[str]`       | Artifact IDs                          |
| `workspace_required` | `bool`        | Whether workspace snapshot is needed  |
| `runner`        | `GateRunnerSpec`  | How the gate executes                 |
| `required`      | `bool`            | Default `True`; failure blocks step/run |

**`required` semantics:**

- `True` → failure blocks step/run.
- `False` → failure recorded but does not block.

### 2.2 GateRunnerSpec (Local-first)

Start with deterministic local runners only.

**A) Local Command Runner**

| Field       | Type                    |
| ----------- | ----------------------- |
| `kind`      | `"local_command"`       |
| `argv`      | `list[str]`             |
| `cwd`       | `str` or `None`          |
| `env`       | `dict[str, str]` or `None` |
| `timeout_s` | `float` or `None`        |

This mirrors the Step local executor but is semantically distinct.

**Future extension:** `kind: "llm_judge"` (not in Layer 3 implementation).

---

## 3. GateEngine

GateEngine integrates with the Layer 2 Runner.

**Responsibilities:**

- Execute gates for:
  - A step (post-step success)
  - Entire run (optional)
- Capture logs
- Produce GateResult envelope
- Persist GateResult via ArtifactStore
- Enforce required behavior

---

## 4. Gate Execution Flow

For each step that has gates:

1. Step finishes successfully.
2. GateEngine retrieves configured gates.
3. For each gate:
   - Execute runner
   - Capture stdout/stderr
   - Store logs as artifacts
   - Build `GateResult` envelope
   - Store envelope via `put_envelope()`
4. If any required gate fails:
   - Mark step as failed in RunState
   - Stop execution (Layer 4 may later override behavior)

**Run-level gates:**

- Execute after all steps succeed
- Same pass/fail semantics

---

## 5. Logging

For each gate execution:

```
.iris/runs/<run_id>/logs/gates/<gate_id>/<attempt>/
  stdout.txt
  stderr.txt
  runner.json
```

All log paths must be stored in:

- GateResult payload (`log_artifact_ids`)
- StepRunRecord (optional reference)

Logs must also be stored as artifacts in Layer 0.

---

## 6. Integration with Layer 2

The Layer 2 Runner must:

- Support optional `gates: list[GateSpec]` on StepSpec
- Call GateEngine after step success
- Update StepRunRecord with `gate_results: list[str]` (artifact IDs of GateResult)
- Enforce required gate failures

Layer 2 must not interpret gate meaning beyond pass/fail.

---

## 7. State Interaction

**RunState must reflect gate outcomes.**

If a required gate fails:

- Step status → `failed`
- `last_error` updated with gate failure reason

**RunStatus transitions:**

- `running` → `failed`

No automatic retry based on gates in Layer 3 (Layer 4 handles routing policies).

---

## 8. Determinism Rules

Layer 3 must ensure:

- Local command gates behave deterministically given same inputs
- GateResult payload contains no non-deterministic fields except `timestamp`
- Logs are preserved

LLM gates are out of scope in Layer 3 baseline.

---

## 9. Invariants

**Layer 3 guarantees:**

- Every gate execution produces a GateResult envelope
- Required gates block progression
- Gate logs are stored as artifacts
- Gate results are persisted via Layer 0
- Kernel does not embed domain logic in gates

**Layer 3 does not guarantee:**

- Correctness of domain semantics
- Smart retry policies
- Intelligent remediation

---

## 10. Done Criteria (Layer 3)

Layer 3 is complete when:

- [x] GateSpec model exists and validated
- [x] GateResult schema (`gate_result.v1`) registered
- [x] Local command gate runner implemented
- [x] GateEngine executes gates post-step
- [x] Gate logs captured and stored
- [x] Required gate failure blocks step
- [x] Unit tests cover pass and fail
- [x] Integration test verifies step + gate behavior

---

## 11. One-Line Summary for AI Coder

Implement Layer 3 kernel gates: GateSpec + GateResult envelope + local-command GateRunner + GateEngine integrated into Runner. Required gates must block step completion. Keep domain-neutral.
