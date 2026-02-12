```md
# Layer 5 — Observability and Reproducibility
## Phased Implementation Plan (for AI Coder)

You are implementing **Layer 5 (Observability and Reproducibility)** for Project **Lily**.

This layer makes the kernel:
- Auditable
- Debuggable
- Replayable
- Deterministic in trace

It must remain:
- Domain-neutral
- Structured (no ad-hoc logging)
- Backwards-compatible with Layers 0–4

---

# Scope (Kernel-only)

Implement:

- Structured step provenance expansion
- Environment snapshot envelope
- Artifact hash recording
- Re-run from step hook (finalized)
- Dry-run gates mode
- Minimal artifact replacement hook (optional final phase)

---

# Out of Scope (Do NOT implement)

- Full provenance graph database
- External observability systems
- Binary reproducibility guarantees
- Deterministic tool wrappers
- Complex environment fingerprinting
- UI dashboards

---

# Global Constraints

- One phase per PR
- No new dependencies
- All new artifacts must use Envelope system
- No deletion of historical artifacts
- Must not break Layer 2 or 3 functionality
- Preserve backward compatibility for existing runs

---

# Phase 5.1 — Environment Snapshot Envelope

## Goal
Capture reproducibility metadata at run start.

---

## Tasks

- [x] Add `environment_snapshot.v1` schema:
  - python_version
  - platform
  - kernel_version
  - uv_lock_hash (optional)
  - timestamp
- [x] Register schema in SchemaRegistry
- [x] Implement `capture_environment_snapshot()`:
  - Collect python version
  - Collect platform info
  - Compute uv.lock hash if file exists
- [x] At run creation (Layer 0 or Runner start):
  - Create envelope
  - Store via ArtifactStore
  - Record reference in RunState

---

## Tests

- [x] `tests/unit/test_environment_snapshot.py`
  - [x] Envelope validates
  - [x] Snapshot fields populated
  - [x] uv_lock_hash optional
  - [x] Stored artifact retrievable

---

## Acceptance Criteria

- [x] Snapshot stored once per run
- [x] RunState references snapshot artifact
- [x] Tests pass

---

# Phase 5.2 — Step Provenance Expansion

## Goal
Expand StepRunRecord to include structured provenance.

---

## Tasks

- [x] Extend `StepRunRecord` with:
  - input_artifact_hashes
  - output_artifact_hashes
  - duration_ms
  - executor_summary
  - gate_result_ids
  - policy_violation_ids
- [x] Update Runner:
  - Before step:
    - resolve input artifact hashes
  - After step:
    - resolve output artifact hashes
    - compute duration
    - record executor summary
- [x] Ensure data persisted via atomic RunState write

---

## Tests

- [x] `tests/unit/test_step_provenance.py`
  - [x] Input hashes recorded
  - [x] Output hashes recorded
  - [x] Duration populated
  - [x] Gate IDs attached
  - [x] Policy IDs attached

---

## Acceptance Criteria

- [x] Provenance fields persisted
- [x] No regression in Runner behavior
- [x] Tests pass

---

# Phase 5.3 — Deterministic Replay (Finalize Rerun Support)

## Goal
Stabilize and formalize replay behavior.

---

## Tasks

- [x] Implement `re_run_from(step_id)` utility:
  - Reset downstream steps to pending
  - Clear produced_artifact_ids in affected StepRunRecords
  - Preserve logs
- [x] Ensure:
  - Replay does not delete artifacts
  - Replay preserves previous attempts for audit
- [x] Update Runner to support:
  - Running after reset without corruption

---

## Tests

- [x] `tests/unit/test_replay_behavior.py`
  - [x] Downstream reset correct
  - [x] Upstream steps unaffected
  - [x] Artifacts remain on disk
  - [x] Run completes successfully after replay

---

## Acceptance Criteria

- [x] Replay deterministic
- [x] No artifact deletion
- [x] Tests pass

---

# Phase 5.4 — Dry-Run Gates Mode

## Goal
Allow running gates without executing steps.

---

## Tasks

- [x] Add Runner mode: `dry_run_gates=True`
- [x] In this mode:
  - Skip step execution
  - Execute only gates for existing artifacts
  - Produce GateResult envelopes
  - Do NOT mutate StepRunRecord status
- [x] Ensure:
  - Dry-run does not create step outputs
  - Dry-run does not modify artifact store (except GateResults)

---

## Tests

- [x] `tests/unit/test_dry_run_gates.py`
  - [x] Gates execute
  - [x] Step status unchanged
  - [x] GateResults stored
  - [x] No step execution logs created

---

## Acceptance Criteria

- [x] Dry-run mode works
- [x] Step state preserved
- [x] Tests pass

---

# Phase 5.5 — Artifact Replacement Hook (Optional Final Phase)

## Goal
Allow replacing an artifact and continuing.

---

## Tasks

- [x] Add `artifact_replacement.v1` schema:
  - original_artifact_id
  - replacement_artifact_id
  - reason
  - timestamp
- [x] Register schema
- [x] Implement `replace_artifact(old_id, new_id, reason)`
  - Store replacement envelope
  - Update RunState references
  - Trigger downstream reset
- [x] Ensure provenance chain preserved

---

## Tests

- [x] `tests/unit/test_artifact_replacement.py`
  - [x] Replacement envelope stored
  - [x] Downstream steps reset
  - [x] Provenance chain intact

---

## Acceptance Criteria

- [x] Replacement tracked via envelope
- [x] Replay works after replacement
- [x] Tests pass

---

# Global Done Criteria (Layer 5)

- [x] Environment snapshot captured at run start
- [x] StepRunRecord expanded with provenance fields
- [x] Artifact hashes recorded deterministically
- [x] Replay from step works safely
- [x] Dry-run gates supported
- [x] Optional artifact replacement supported
- [x] All new schemas registered
- [x] All tests pass
- [x] No domain logic introduced

---

# Final Reminder to AI Coder

- Do not introduce dashboards.
- Do not add external logging systems.
- Do not refactor earlier layers unless necessary.
- Preserve determinism.
- Preserve backward compatibility.
- One phase per PR.
```
