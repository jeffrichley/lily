# Layer 1 — Contracts & Validation (Kernel)

Layer 1 defines the **typed envelope and schema validation** layer of the kernel:

> Envelope + SchemaId + Canonical Hashing + Schema Registry + EnvelopeValidator + optional ArtifactStore envelope helpers

It is designed to be:

* Kernel-pure (universal, no domain logic)
* Pydantic-first
* Deterministic
* Testable in small phases
* Composable with Layer 0 without breaking it

Layer 1 contains **no domain schemas** (only example toy schemas for tests).

---

# 0. Design Principles

1. Envelope is pure data (no IO, no registry access, no DB calls).
2. Payload hash is deterministic and computed from canonical payload bytes only.
3. Schema version is encoded in `schema_id` (single source of truth).
4. SchemaRegistry is in-process (no plugin system yet).
5. Validation occurs only at boundaries via EnvelopeValidator.
6. ArtifactStore envelope helpers are additive and do not modify Layer 0 behavior.

---

# 1. SchemaId Convention (Single Source of Truth)

## 1.1 Schema ID Format

`schema_id` is a string formatted as:

```
<name>.v<integer>
```

Examples:

* `work_order.v1`
* `task_graph.v2`
* `echo_payload.v1`

Rules:

* Version lives **only inside `schema_id`**
* No separate `schema_version` field exists
* Version is not stored redundantly anywhere else

---

# 2. Core Types

## 2.1 EnvelopeMeta

Fields:

* `schema_id: str`
* `producer_id: str`
* `producer_kind: Literal["tool", "llm", "human", "system"]`
* `created_at: datetime`
* `inputs: list[str]`  ← artifact IDs only
* `payload_sha256: str`

Clarifications:

* `inputs` stores **artifact IDs only**, not full ArtifactRef objects.
* `payload_sha256` hashes only the canonical serialized payload.
* `EnvelopeMeta` contains no IO or registry logic.

Tracking:

* [x] EnvelopeMeta implemented as Pydantic model
* [x] producer_kind constrained via Literal
* [x] inputs is list[str] (no ArtifactRef allowed)

---

## 2.2 Envelope[T]

Generic Pydantic model:

```
Envelope[T]:
  meta: EnvelopeMeta
  payload: T
```

Rules:

* Envelope is pure data
* No registry calls
* No hashing inside model constructor
* No IO

Tracking:

* [x] Generic Envelope[T] implemented
* [x] Round-trip serialize/deserialize for Envelope[dict]
* [x] No side effects in models

---

# 3. Canonical Serialization & Hashing

Hash correctness must be deterministic across runs.

## 3.1 canonical_json_bytes(obj)

Rules:

* `sort_keys=True`
* `separators=(",", ":")`
* `ensure_ascii=False`
* `allow_nan=False`
* UTF-8 encoding

Only supported input types:

* Pydantic BaseModel (converted via `model_dump(mode="json")`)
* dict
* list
* str
* int
* float
* bool
* None

Any unsupported type must raise.

Tracking:

* [x] canonical_json_bytes implemented
* [x] Stable regardless of key order
* [x] Fails on unsupported types
* [x] Fails on NaN/Infinity

---

## 3.2 Hash Utilities

* `sha256_bytes(data: bytes) -> str`
* `hash_payload(payload) -> str`

Rules:

* JSON-like payload → canonical JSON bytes → sha256
* bytes → sha256 directly
* File hashing handled in Layer 0
* Hash always computed on **stored canonical bytes**

Tracking:

* [x] sha256_bytes implemented
* [x] hash_payload implemented
* [x] Hash deterministic across runs
* [x] Hash changes when payload changes

---

# 4. Schema Registry (Pydantic-First)

## 4.1 SchemaRegistry

Responsibilities:

* Map `schema_id` → Pydantic model class
* Validate payload against model

Interface:

* `register(schema_id: str, model: type[BaseModel], *, override=False)`
* `get(schema_id: str) -> type[BaseModel]`
* `validate(schema_id: str, payload_obj: Any) -> BaseModel`

Rules:

* Duplicate registration raises unless `override=True`
* Registry validates payload only (not envelope)
* Registry does not perform hashing
* Registry contains no domain logic

Tracking:

* [x] register / get / validate implemented
* [x] Duplicate registration blocked
* [x] validate returns typed model instance
* [x] Clear validation errors
* [x] Tests cover success + failure cases

---

# 5. Envelope Validation (Boundary Enforcement)

## 5.1 EnvelopeValidator

Responsibilities:

1. Validate envelope meta structure
2. Recompute payload hash and compare to `payload_sha256`
3. Validate payload via SchemaRegistry

Returns:

```
(meta: EnvelopeMeta, payload_model: BaseModel)
```

Rules:

* Hash mismatch → fail
* Missing schema_id in registry → fail
* Invalid payload shape → fail
* No silent coercion of schema mismatches

Tracking:

* [x] Hash mismatch test
* [x] Missing schema test
* [x] Invalid payload test
* [x] Successful validation test

---

# 6. Optional ArtifactStore Integration

These helpers must not break existing Layer 0 API.

## 6.1 put_envelope

```
put_envelope(schema_id, payload_model, meta_fields, artifact_name=None)
```

Steps:

1. Build Envelope
2. Compute payload hash
3. Set meta.payload_sha256
4. Store full envelope JSON via Layer 0 `put_json`
5. Return ArtifactRef

Clarification:

* `payload_sha256` hashes only `payload`
* Full envelope is stored, but hash covers payload only

---

## 6.2 get_envelope

* Load JSON
* Return Envelope[Any]
* No validation performed

---

## 6.3 get_validated

* Load envelope
* Validate via EnvelopeValidator
* Return `(meta, payload_model)`

Tracking:

* [x] put_envelope implemented
* [x] get_envelope implemented
* [x] get_validated implemented
* [x] Tests for round-trip + validation failure

---

# 7. Guardrails

Layer 1 must not include:

* Domain schemas
* Plugin systems
* JSONSchema generation (unless trivial)
* Business logic
* Planning semantics
* Graph semantics

Registry is in-process only.

---

# 8. Invariants

Layer 1 guarantees:

* Envelope models are pure
* Payload hash deterministic
* Schema versioning controlled solely by schema_id
* Registry is the single source of schema truth
* Validation happens only at boundaries
* ArtifactStore helpers are additive and backward compatible

Tracking:

* [x] Envelope pure (no IO)
* [x] Hash deterministic
* [x] Registry is single source
* [x] ArtifactStore unchanged for non-envelope calls

---

# 9. Done Criteria

Layer 1 is complete when:

* [x] Envelope + EnvelopeMeta exist and round-trip
* [x] Canonical hashing implemented and tested
* [x] SchemaRegistry implemented and tested
* [x] EnvelopeValidator enforces meta + hash + schema
* [x] Optional ArtifactStore envelope helpers implemented and tested
* [x] No domain schemas exist in kernel
* [x] All tests pass

---

# 10. One-Line Summary for AI Coder

Implement Layer 1 in phases: Envelope models → canonical hashing → SchemaRegistry → EnvelopeValidator → optional ArtifactStore envelope helpers. Keep kernel-only. Add tests for every phase.
