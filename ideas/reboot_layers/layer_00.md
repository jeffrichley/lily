You’re right to call that out. At “kernel” level, Layer 0 isn’t three separate subsystems—it’s **one concrete thing**:

> a *Run Directory + Artifact Store API* with a **Run Manifest** that records identity + provenance.

So yes: “run_id, timestamps, provenance” are **fields**, but we still need to *build* the machinery that creates, persists, and enforces them.

Here’s what Layer 0 actually is, in engineer terms.

---

## Layer 0 = Run Store (filesystem-first)

### What we are building

1. **A deterministic run folder layout**
2. **A RunManifest file** written at run creation
3. **An ArtifactStore API** that writes/reads artifacts and records provenance automatically

That’s it.

Everything else in higher layers relies on this.

---

## 0.1 Run folder layout (the “filesystem contract”)

We define a single canonical structure. Example:

```
.iris/
  runs/
    <run_id>/
      run_manifest.json
      artifacts/
      logs/
      tmp/
```

Rules:

* the kernel owns everything under `.iris/runs/<run_id>/`
* artifacts are written only through the ArtifactStore API (not ad-hoc file writes)
* `tmp/` can be wiped anytime

This is “a thing to make” because the kernel must create this reliably and consistently.

---

## 0.2 Run identity (implemented as RunManifest)

We create a `run_manifest.json` at run start. It contains:

* `run_id` (uuid or sortable id)
* `created_at`, `updated_at`
* `kernel_version`
* `status` (created/running/failed/succeeded)
* `work_order_ref` (even if work_order is not finalized yet)
* `workspace_snapshot` (optional later; path, git commit, etc.)

This is not just “properties” — it’s the **authoritative record** that lets you:

* resume runs
* audit what happened
* reproduce behavior

So the “thing to build” is:

* a RunManifest schema
* creation/update logic
* atomic writes (no half-written manifests)

---

## 0.3 Artifact store (implemented as an API + on-disk indexing)

The ArtifactStore provides a small set of operations:

* `put(kind, payload, metadata) -> ArtifactRef`
* `get(artifact_ref) -> payload`
* `list(run_id, filters...) -> [ArtifactRef]`
* `open_path(artifact_ref) -> filepath` (for big blobs like zip/video)

On disk, it writes:

* the artifact payload (JSON, text, binary)
* a sidecar metadata file OR a central index

**Important:** the store, not the agent, records:

* who produced it (`producer_id`)
* what inputs were used (`input_artifact_refs`)
* when it was created
* content hash

This makes provenance automatic and non-optional.

---

## 0.4 Provenance metadata (implemented as Artifact metadata + lineage)

Provenance isn’t its own module at Layer 0. It’s:

* fields in `ArtifactRef` / artifact metadata
* written automatically by ArtifactStore
* later rendered into a “provenance graph” (Layer 5-ish)

At Layer 0 we only need:

* record `producer`, `inputs`, `timestamp`, `hash`
* ensure artifacts are immutable once written (or versioned)

So the “thing to build” is the metadata model + write behavior.

---

# The Layer 0 deliverables (concrete)

If I turn Layer 0 into a checklist of “things to make,” it becomes:

* [ ] **RunId generator** (uuid or time-sortable)
* [ ] **Run directory creator** (`.iris/runs/<run_id>/...`)
* [ ] **RunManifest schema + writer** (create/update)
* [ ] **ArtifactRef schema** (id, kind, path, hash, created_at, producer, inputs)
* [ ] **ArtifactStore** (put/get/list)
* [ ] **Atomic write utilities** (write temp then rename)
* [ ] **Indexing strategy** (simple `artifacts/index.jsonl` to start)

That’s the actual engineering work.

---

## Why Layer 0 matters (skeptic framing)

If we don’t do Layer 0 cleanly, every later layer becomes “it depends”:

* resume won’t work
* routing won’t be reproducible
* gates won’t be auditable
* plugins won’t be debuggable
* you’ll lose trust

Layer 0 is boring on purpose.

---

If you want, next we can do the same “convert bullet properties into buildable things” for **Layer 1**, but staying disciplined: still kernel-only, still universal.
