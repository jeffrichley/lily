Yes — kernel first, domain-agnostic, no hard-wired “coding lane.” Let’s define the **layers of things** the kernel must support, so *any* workflow (coding, research, analytics, business) plugs in cleanly.

I’m going to describe the kernel as a small set of **primitives** + **extension points**. Everything else is “outside flow.”

---

## Kernel design goal

A universal execution runtime that can:

* accept a **work order**
* run a **graph of steps**
* produce **artifacts**
* run **gates**
* **route** based on outcomes
* log everything
* do this identically across domains

No domain assumptions. No “coding tasks.” Just machinery.

---

# Layer 0 — Storage and Identity

**Things the kernel must create and manage:**

### 1) Run identity

* `run_id`
* timestamps
* version of kernel
* pointer to work order version

### 2) Artifact store

A predictable filesystem layout (or pluggable backend later) that supports:

* write artifact
* read artifact
* list artifacts
* immutable “inputs” vs mutable “working” outputs
* provenance metadata (who/what produced it)

This is the foundation for auditability.

---

# Layer 1 — Contracts and Validation

The kernel must speak in **schemas**, not prose.

### 3) Typed envelope model (universal)

Instead of hard-wiring “TaskGraph” or “CodingPlan”, the kernel only requires:

* `Envelope<T>`: a wrapper around any typed payload

  * schema_version
  * producer (agent/tool)
  * inputs (artifact refs)
  * hash/signature
  * timestamps
  * payload (domain-defined)

The kernel validates envelopes, not domain semantics.

### 4) Schema registry

Pluggable registry that lets you declare:

* artifact types (by name)
* schema for each type
* validators (Pydantic/JSONSchema)

Kernel uses this to validate artifacts at boundaries.

---

# Layer 2 — Execution Graph Runtime

This is the “scheduler,” but domain-neutral.

### 5) Step abstraction

A step is just:

* inputs (artifact refs)
* outputs (artifact type names)
* executor (tool call / LLM call / script)
* retry policy
* timeout policy

Kernel doesn’t care if the step is “research” or “code.”

### 6) State machine

Kernel tracks:

* current node
* retries
* status per step
* artifact refs produced so far

This enables resume/replay.

---

# Layer 3 — Gates (Verification)

This is your trust engine.

### 7) Gate abstraction

A gate is:

* inputs: artifact refs + workspace snapshot (optional)
* gate runner: deterministic tool OR LLM judge OR hybrid
* outputs: `GateResult` envelope (pass/fail, reasons, pointers to logs)

Kernel enforces:

* required gates for a step (or for the whole run)
* stop/route on failure

Key: gates are **first-class** and domain-agnostic.

---

# Layer 4 — Routing and Policies

This is where failures become deterministic flow.

### 8) Routing rules

Given:

* step result
* gate result(s)
* retry counters
  Route to:
* retry same step
* go to another step
* escalate to human approval
* abort run

Rules are data/config, not hard-coded logic.

### 9) Safety policies / sandboxing

Kernel should support:

* allowlist of writable paths
* do-not-touch paths
* max diff size (optional)
* tool allowlist per executor
* network access policy (later)

This prevents “agent ran wild.”

---

# Layer 5 — Observability and Reproducibility

How you trust and debug.

### 10) Run logs + provenance

Every execution writes:

* step start/end times
* tool stdout/stderr
* input artifact hashes
* output artifact hashes
* environment info (uv lock hash, python version, etc.)

### 11) Replayability hooks

Kernel should support:

* “re-run from step N with same inputs”
* “replace artifact X and continue”
* “dry-run gates only”

This turns chaos into engineering.

---

# Layer 6 — Extension Points (where domain lives)

The kernel must be small; domains plug in here.

### 12) Plugins / Packs

A pack can contribute:

* schemas (artifact types)
* step templates (optional)
* gate templates (optional)
* routing policies (optional)

But the kernel only knows: “load packs; validate; execute graph.”

This is how you avoid hard-wiring tasks.

---

## The “Things” list (kernel deliverables)

If we’re building kernel only, the “things” we need to implement are:

1. **Run + Artifact store**
2. **Envelope + ArtifactRef models**
3. **Schema registry + validation**
4. **Graph runtime (steps, state, resume)**
5. **Gate system (gate runner + gate results + logs)**
6. **Routing/policy engine (data-driven)**
7. **Workspace constraints (allow/deny paths)**
8. **Observability (logs, provenance, replay)**

Everything else (coding/research/business specifics) is a pack.

---

## Big skeptical constraint (important)

If we keep the kernel universal, we must NOT bake in:

* “plan/spec/task graph” semantics
* “PR/merge” semantics
* “research citations” semantics
* “market scoring” semantics

Those are pack-level schemas + gates.

Kernel only enforces:

* artifacts are valid
* gates ran
* routing rules applied
* state persisted

---

## Sharp question to keep us honest

Do you want the kernel to assume **filesystem + local process execution** as the baseline (LLM calls are just another executor), or do you want it abstracted immediately to support remote workers?

Google hat: start local-process + filesystem first (clean abstraction boundaries), then add remote runners as a plugin.

Either way, the layer model above stays the same.
