# Layer 5 — Observability and Reproducibility

Layer 5 defines the **traceability and replay foundation** of the kernel.

If Layer 3 is trust enforcement and Layer 4 is deterministic flow,
Layer 5 is how you **debug, audit, and reproduce** everything.

This layer turns runtime into engineering instead of guesswork.

---

## 0. Design Principles

1. Every execution must be inspectable.
2. Every artifact must be traceable.
3. Every step must be replayable.
4. Environment must be captured deterministically.
5. Reproducibility must not depend on memory or logs alone.
6. Observability must be structured, not just console output.

Layer 5 does not introduce domain logic.
It strengthens kernel introspection.

---

## 1. Run Logs + Provenance

Layer 5 formalizes structured execution logging.

Logs are not just files — they are part of the execution model.

### 1.1 Execution Trace Requirements

For every step execution, the kernel must record:

- Step ID
- Attempt number
- Start timestamp
- End timestamp
- Duration
- Executor summary (argv, cwd, env subset)
- Input artifact IDs
- Input artifact hashes
- Output artifact IDs
- Output artifact hashes
- Gate results (artifact IDs)
- Policy violations (artifact IDs)
- Return code
- Retry count

This data must be stored in structured form.

### 1.2 StepExecutionRecord (Structured)

Add or extend `StepRunRecord` to include:

- `input_artifact_hashes: dict[str, str]`
- `output_artifact_hashes: dict[str, str]`
- `environment_snapshot_ref: str | None`
- `duration_ms: int`
- `executor_summary: dict`
- `gate_result_ids: list[str]`
- `policy_violation_ids: list[str]`

These must persist in `run_state.json`.

### 1.3 Environment Snapshot

For reproducibility, capture environment info at run start.

Minimum required:

- Python version
- Platform info
- uv lock hash (if present)
- Kernel version
- Timestamp

This must be stored as:

- `environment_snapshot.v1` envelope
- Saved once per run
- Referenced from RunState

**Schema ID:** `environment_snapshot.v1`

**Payload fields:**

- python_version
- platform
- kernel_version
- uv_lock_hash (optional)
- timestamp

### 1.4 Artifact Hash Tracking

At step boundary:

- Before execution: resolve input artifact hashes
- After execution: resolve output artifact hashes

Hashes must come from Layer 1 canonical hashing.

This enables:

- Bit-level reproducibility verification
- Detection of artifact drift
- Integrity auditing

---

## 2. Replayability Hooks

Replay is a first-class feature.

Layer 5 defines the mechanics to safely rerun parts of a graph.

### 2.1 Re-run From Step

Kernel must support:

- Resetting downstream StepRunRecords
- Reusing existing input artifacts
- Clearing output references for affected steps
- Preserving historical logs

Replay must not delete artifacts.
It must only alter RunState.

### 2.2 Replace Artifact and Continue

Kernel must support:

- Injecting a new artifact ID in place of an existing one
- Recording replacement as provenance
- Revalidating downstream dependencies

This enables:

- Human correction
- Manual patching
- External tool injection

Replacement must:

- Produce a `artifact_replacement.v1` envelope
- Record original artifact ID
- Record replacement artifact ID
- Record reason
- Record timestamp

### 2.3 Dry-Run Gates Only

Kernel must support:

- Executing gates without executing steps
- Evaluating required gates against existing artifacts
- Producing GateResult envelopes
- Not mutating step statuses

This enables:

- Validation-only runs
- Debugging gate logic
- Auditing existing outputs

Dry-run must:

- Not execute any StepSpec
- Not change artifact store
- Only append GateResult artifacts

---

## 3. Provenance Graph

Layer 5 must make it possible to reconstruct:

- Which step produced which artifact
- Which artifacts were inputs
- Which environment produced it
- Which gate validated it
- Which policy violations occurred

Kernel does not need a graph database.

But the combination of:

- Envelope metadata
- StepRunRecord
- RunState
- ArtifactStore

Must allow deterministic reconstruction.

---

## 4. Invariants

Layer 5 guarantees:

- Every step execution has structured record
- Every artifact hash is recorded at production
- Every environment snapshot is stored once per run
- Replay does not delete history
- Replacement is traceable
- Dry-run does not mutate execution state

Layer 5 does not guarantee:

- Binary reproducibility across machines
- Identical timing
- Deterministic external tools

---

## 5. Minimal Initial Implementation Scope

Start with:

- Environment snapshot envelope
- StepExecutionRecord expansion
- Input/output artifact hash recording
- Re-run from step support (basic)
- Dry-run gates support (basic)

Defer:

- Artifact replacement (can follow)
- Advanced provenance graph queries
- Full diff-based environment fingerprinting

---

## 6. Done Criteria (Layer 5)

Layer 5 is complete when:

- [x] environment_snapshot.v1 schema implemented
- [x] Environment snapshot stored at run start
- [x] StepRunRecord includes input/output hashes
- [x] Executor summaries recorded
- [x] Gate + policy results attached to step record
- [x] Re-run from step works without deleting artifacts
- [x] Dry-run gates supported
- [x] Provenance reconstruction possible via structured data
- [x] All tests pass
- [x] No domain-specific logic introduced

---

## 7. One-Line Summary for AI Coder

Implement Layer 5 kernel observability and reproducibility: structured step provenance, environment snapshot envelope, artifact hash tracking, replay hooks, and dry-run gate support. Keep domain-neutral and deterministic.
