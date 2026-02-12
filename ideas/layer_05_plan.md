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

- [ ] Add `environment_snapshot.v1` schema:
  - python_version
  - platform
  - kernel_version
  - uv_lock_hash (optional)
  - timestamp
- [ ] Register schema in SchemaRegistry
- [ ] Implement `capture_environment_snapshot()`:
  - Collect python version
  - Collect platform info
  - Compute uv.lock hash if file exists
- [ ] At run creation (Layer 0 or Runner start):
  - Create envelope
  - Store via ArtifactStore
  - Record reference in RunState

---

## Tests

- [ ] `tests/unit/test_environment_snapshot.py`
  - [ ] Envelope validates
  - [ ] Snapshot fields populated
  - [ ] uv_lock_hash optional
  - [ ] Stored artifact retrievable

---

## Acceptance Criteria

- [ ] Snapshot stored once per run
- [ ] RunState references snapshot artifact
- [ ] Tests pass

---

# Phase 5.2 — Step Provenance Expansion

## Goal
Expand StepRunRecord to include structured provenance.

---

## Tasks

- [ ] Extend `StepRunRecord` with:
  - input_artifact_hashes
  - output_artifact_hashes
  - duration_ms
  - executor_summary
  - gate_result_ids
  - policy_violation_ids
- [ ] Update Runner:
  - Before step:
    - resolve input artifact hashes
  - After step:
    - resolve output artifact hashes
    - compute duration
    - record executor summary
- [ ] Ensure data persisted via atomic RunState write

---

## Tests

- [ ] `tests/unit/test_step_provenance.py`
  - [ ] Input hashes recorded
  - [ ] Output hashes recorded
  - [ ] Duration populated
  - [ ] Gate IDs attached
  - [ ] Policy IDs attached

---

## Acceptance Criteria

- [ ] Provenance fields persisted
- [ ] No regression in Runner behavior
- [ ] Tests pass

---

# Phase 5.3 — Deterministic Replay (Finalize Rerun Support)

## Goal
Stabilize and formalize replay behavior.

---

## Tasks

- [ ] Implement `re_run_from(step_id)` utility:
  - Reset downstream steps to pending
  - Clear produced_artifact_ids in affected StepRunRecords
  - Preserve logs
- [ ] Ensure:
  - Replay does not delete artifacts
  - Replay preserves previous attempts for audit
- [ ] Update Runner to support:
  - Running after reset without corruption

---

## Tests

- [ ] `tests/unit/test_replay_behavior.py`
  - [ ] Downstream reset correct
  - [ ] Upstream steps unaffected
  - [ ] Artifacts remain on disk
  - [ ] Run completes successfully after replay

---

## Acceptance Criteria

- [ ] Replay deterministic
- [ ] No artifact deletion
- [ ] Tests pass

---

# Phase 5.4 — Dry-Run Gates Mode

## Goal
Allow running gates without executing steps.

---

## Tasks

- [ ] Add Runner mode: `dry_run_gates=True`
- [ ] In this mode:
  - Skip step execution
  - Execute only gates for existing artifacts
  - Produce GateResult envelopes
  - Do NOT mutate StepRunRecord status
- [ ] Ensure:
  - Dry-run does not create step outputs
  - Dry-run does not modify artifact store (except GateResults)

---

## Tests

- [ ] `tests/unit/test_dry_run_gates.py`
  - [ ] Gates execute
  - [ ] Step status unchanged
  - [ ] GateResults stored
  - [ ] No step execution logs created

---

## Acceptance Criteria

- [ ] Dry-run mode works
- [ ] Step state preserved
- [ ] Tests pass

---

# Phase 5.5 — Artifact Replacement Hook (Optional Final Phase)

## Goal
Allow replacing an artifact and continuing.

---

## Tasks

- [ ] Add `artifact_replacement.v1` schema:
  - original_artifact_id
  - replacement_artifact_id
  - reason
  - timestamp
- [ ] Register schema
- [ ] Implement `replace_artifact(old_id, new_id, reason)`
  - Store replacement envelope
  - Update RunState references
  - Trigger downstream reset
- [ ] Ensure provenance chain preserved

---

## Tests

- [ ] `tests/unit/test_artifact_replacement.py`
  - [ ] Replacement envelope stored
  - [ ] Downstream steps reset
  - [ ] Provenance chain intact

---

## Acceptance Criteria

- [ ] Replacement tracked via envelope
- [ ] Replay works after replacement
- [ ] Tests pass

---

# Global Done Criteria (Layer 5)

- [ ] Environment snapshot captured at run start
- [ ] StepRunRecord expanded with provenance fields
- [ ] Artifact hashes recorded deterministically
- [ ] Replay from step works safely
- [ ] Dry-run gates supported
- [ ] Optional artifact replacement supported
- [ ] All new schemas registered
- [ ] All tests pass
- [ ] No domain logic introduced

---

# Final Reminder to AI Coder

- Do not introduce dashboards.
- Do not add external logging systems.
- Do not refactor earlier layers unless necessary.
- Preserve determinism.
- Preserve backward compatibility.
- One phase per PR.
```
