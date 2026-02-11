Absolutely. Here are **phases** you can feed to your AI coder that keep Layer 1 kernel-pure (universal), small PRs, and testable.

---

# Layer 1 Phases — Contracts & Validation (Kernel)

## Phase 1.1 — Core types: Envelope + SchemaId (no registry yet)

**Goal:** Introduce a universal “typed envelope” container that can wrap any payload, but do not attempt dynamic validation yet.

**Deliverables**

* `SchemaId` / `ArtifactType` convention (string like `work_order.v1`)
* `EnvelopeMeta` model with:

  * `schema_id` (or `artifact_type`)
  * `schema_version` (int, if you want both; otherwise derive version from schema_id)
  * `producer_id`
  * `producer_kind` (`tool|llm|human|system`)
  * `created_at`
  * `inputs` (list of `ArtifactRef` or artifact IDs)
  * `payload_sha256` (hash of canonical payload bytes)
* `Envelope[T]` generic Pydantic model:

  * `meta: EnvelopeMeta`
  * `payload: T`

**Rules**

* Envelope is **pure data** (no IO, no registry, no DB changes).
* Payload hash uses canonical serialization for JSON payloads (deterministic).

**Tests**

* Round-trip serialize/deserialize `Envelope[dict]`
* Payload hash deterministic given same payload

---

## Phase 1.2 — Canonical serialization + hashing utilities

**Goal:** Make hashing/signing reliable and consistent across the system.

**Deliverables**

* Utility: `canonical_json_bytes(obj) -> bytes` (sorted keys, stable separators, UTF-8)
* Utility: `sha256_bytes(data) -> str`
* Utility: `hash_payload(payload) -> str`

  * If payload is JSON-like → canonical JSON hash
  * If payload is bytes/file → hash bytes (but file hashing is Layer 0 already)

**Tests**

* Canonical JSON bytes stable across key order
* Hash changes when payload changes
* Hash stable across runs for same payload

---

## Phase 1.3 — Schema Registry v1 (Pydantic-first)

**Goal:** Provide a registry that maps `schema_id` → Pydantic model type, so kernel can validate envelopes at boundaries.

**Deliverables**

* `SchemaRegistry` class with:

  * `register(schema_id: str, model: type[BaseModel])`
  * `get(schema_id: str) -> type[BaseModel]`
  * `validate(schema_id: str, payload_obj: Any) -> BaseModel`
* Prevent duplicate schema registrations unless explicitly overridden.
* A small built-in registry initialization point (no plugin packs yet).

**Tests**

* Register/get works
* Duplicate register raises
* Validate returns model instance
* Validate fails with clear error for wrong shape

---

## Phase 1.4 — Envelope validation at the boundary (EnvelopeValidator)

**Goal:** Kernel validates “Envelope + payload conforms to schema” without knowing domain semantics.

**Deliverables**

* `EnvelopeValidator` that:

  * checks envelope meta required fields
  * verifies payload hash matches `payload_sha256`
  * validates payload using `SchemaRegistry`
* returns a validated payload model instance (typed)

**Tests**

* Fails on wrong hash
* Fails on missing schema
* Fails on invalid payload
* Passes for valid envelope + payload

---

## Phase 1.5 — Integrate with Layer 0 ArtifactStore (optional but recommended)

**Goal:** Make ArtifactStore capable of storing **enveloped artifacts** and validating them on `get()`.

**Deliverables**

* Add optional methods (do not break existing):

  * `put_envelope(schema_id, payload_model, meta, artifact_name=None) -> ArtifactRef`

    * stores JSON with `{meta, payload}`
    * computes payload hash
    * writes artifact via Layer 0 (put_json)
  * `get_envelope(artifact_ref) -> Envelope[Any]`
  * `get_validated(artifact_ref, registry) -> BaseModel` (validated payload)
* Keep this universal. No domain-specific schemas.

**Tests**

* Put/get envelope roundtrip
* get_validated enforces schema + hash

---

# Guardrails to include in your prompt

* **No domain schemas** in Layer 1 PRs (only example toy schema for tests, like `EchoPayload`).
* **No plugin system** yet (that’s Layer 6). Registry can be “in-process.”
* **No JSONSchema generation** yet unless it’s trivial; start Pydantic-first.

---

# One-liner you can paste to your AI coder (summary)

“Implement Layer 1 in phases: Envelope models → canonical hashing → SchemaRegistry (Pydantic) → EnvelopeValidator → optional ArtifactStore envelope helpers; keep it kernel-only and add tests for each phase.”

If you want, I can turn the above into a single **copy/paste prompt** (like the one you used for `lily run new`) that instructs the coder to implement **Phase 1.1 only** as the next PR.
