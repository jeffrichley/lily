---
owner: "@team"
last_updated: "2026-02-17"
status: "reference"
source_of_truth: false
---

# LILY MEMORY SYSTEM — FULL SPECIFICATION (V0)

**Status:** Draft Specification
**Scope:** Local-first long-term memory architecture using LangGraph / LangChain concepts
**Audience:** System architects, agent framework developers, advanced AI workflows
**Primary Goal:** Durable, inspectable, reliable memory for agentic systems without hidden magic

---

# 1. Design Goals

## 1.1 Core Principles

1. **Local-first**

   * System must run fully offline.
   * No cloud dependency for persistence.

2. **Deterministic architecture**

   * Memory behavior must be understandable and debuggable.
   * Avoid opaque “AI magic” memory decisions.

3. **Separation of concerns**

   * Execution state ≠ long-term memory.
   * Retrieval ≠ truth.
   * Storage ≠ extraction logic.

4. **Resumability**

   * Agent runs must be pausable and resumable safely.

5. **Auditability**

   * Ability to inspect what memory existed at any point in time.

6. **Scalability**

   * Start simple (SQLite + JSON).
   * Grow without architectural rewrite.

---

# 2. Conceptual Model

LangGraph defines two distinct memory domains:

## 2.1 Short-Term Memory (Thread Scoped)

Stored via:

* Graph state
* Checkpointer

Purpose:

* Resume runs
* Continue conversations
* Preserve execution progress

Properties:

* Bound to a **thread**
* Temporal
* Execution-focused

---

## 2.2 Long-Term Memory (Cross-Thread)

Stored via:

* Long-term memory store (JSON documents)

Purpose:

* Preferences
* Stable facts
* Rules
* Durable knowledge

Properties:

* Cross-session
* Cross-thread
* Semantic continuity

---

## 2.3 Optional Semantic Retrieval Layer

Separate from long-term memory.

Purpose:

* Retrieve large artifacts by meaning.

Examples:

* transcripts
* research notes
* logs

IMPORTANT:

* Vector retrieval ≠ truth.
* Structured store remains canonical.

---

# 3. Architecture Overview

```
USER INPUT
    ↓
LangGraph Execution
    ↓
Graph State (Short-term)
    ↓
Checkpointer (SQLite)
    ↓
Thread Resume + Debug

Long-term Store
    ↑
Memory Extraction Logic
    ↑
Agent Output / Policies

(Optional)
Vector Store ← Large Artifacts
```

---

# 4. Storage Layers (Authoritative Specification)

## Layer A — Checkpointer (Thread Execution Memory)

### Purpose

Persist full execution state at safe points.

### Recommended Backend

* SQLite checkpointer

### Stores

* Message history
* Intermediate state
* Tool outputs required for continuation
* Execution progress
* Interrupt snapshots

### Best Practices

* ALWAYS supply thread_id.
* Keep state minimal.
* Avoid large blobs.
* Store references (paths, IDs).

### Do NOT

* Use for long-term preferences.
* Store entire datasets.
* Store binary artifacts.

---

## Layer B — Long-Term Memory Store

### Purpose

Cross-session durable memory.

### Data Model

JSON documents organized by namespace.

Example namespace strategy:

```
("user", USER_ID, "profile")
("user", USER_ID, "preferences")
("project", PROJECT_ID, "rules")
("project", PROJECT_ID, "glossary")
("agent", AGENT_NAME, "behavior")
```

### Document Structure (Recommended)

```json
{
  "schema_version": 1,
  "type": "preference",
  "data": {},
  "source_thread_id": "abc123",
  "timestamp": "ISO8601",
  "confidence": 0.95,
  "last_verified": "ISO8601"
}
```

---

### What Belongs Here

GOOD:

* User preferences
* Naming conventions
* Project defaults
* Stable rules
* Persistent agent identity constraints

BAD:

* Raw transcripts
* Temporary plans
* Intermediate tool logs

---

## Layer C — Optional Vector Store

Purpose:

* Retrieval by semantic similarity.

Use for:

* Long text blobs
* Historical logs
* Example runs

RULE:

Structured store = truth
Vector retrieval = supporting evidence.

---

# 5. Memory Types (Psychological Model Mapping)

LangGraph conceptual model:

| Type       | Meaning              | Storage         |
| ---------- | -------------------- | --------------- |
| Semantic   | facts/preferences    | Store           |
| Episodic   | past events/examples | Store or Vector |
| Procedural | rules/instructions   | Store           |

---

# 6. Memory Writing Strategies

## 6.1 Hot Path Writing

Memory written during execution.

Use when:

* Critical preference discovered.
* Immediate persistence required.

Risk:

* Slows execution.

---

## 6.2 Background Consolidation (Recommended)

Separate process:

* Analyze completed conversations.
* Extract durable memory.
* Merge into profiles.

Benefits:

* Stable memory.
* Lower latency.
* Cleaner logic.

---

## 6.3 Deterministic Before Intelligent

Phase 1:

* Rule-based extraction.

Phase 2:

* LLM-assisted extraction.

Phase 3:

* LangMem or similar automation.

---

# 7. Thread Model

Thread = execution lineage.

Properties:

* Independent timeline.
* Can resume later.
* Contains checkpoints.

Rules:

* Never reuse thread IDs for unrelated runs.
* Treat thread history as immutable timeline.

---

# 8. Memory Hygiene Policies

## Mandatory Fields

All memory entries SHOULD include:

* source_thread_id
* timestamp
* schema_version
* confidence score

---

## Expiration Rules

Memory categories:

| Category             | TTL    |
| -------------------- | ------ |
| volatile context     | short  |
| temporary preference | medium |
| core identity        | never  |

---

## Profile Consolidation

Preferred pattern:

* Maintain consolidated profile doc.
* Merge new facts.
* Prevent memory fragmentation.

---

# 9. Best Practices

## Architectural

* Separate execution from memory.
* Keep memory schema versioned.
* Design explicit extraction policies.

---

## Operational

* Back up SQLite DB.
* Export memory snapshots for inspection.
* Use human-readable mirrors if desired.

---

## Prompt Integration

Inject memory selectively:

* only relevant memory
* avoid full memory dumps
* reduce context bloat

---

# 10. Critical DO NOT List

## DO NOT

* Treat vector search as canonical truth.
* Store huge artifacts in checkpoint state.
* Mix execution progress with long-term facts.
* Allow uncontrolled auto-memory writes.
* Write memory without provenance.
* Depend on LLM hallucinated memory extraction without validation.
* Use memory as hidden global state.

---

# 11. Comparison — Manual File-Based Memory vs LangGraph Model

## Manual File-Based

### Pros

* Human-readable.
* Git-friendly.
* Easy early prototyping.

### Cons

* No atomic checkpoints.
* Difficult resume semantics.
* Race conditions.
* Schema drift risk.
* Hard replay/time-travel.

---

## LangGraph-Based

### Pros

* Thread durability.
* Interrupt/resume support.
* Built-in execution model.
* Debuggable state evolution.

### Cons

* Requires architectural discipline.
* Slight learning curve.

---

## Hybrid Strategy (Recommended)

* LangGraph = source of truth.
* File exports = inspection layer.

---

# 12. Scaling Guidance

Start:

```
SQLite checkpointer
Structured store
No vectors
Manual extraction
```

Scale later:

```
Add background consolidator
Add vector store
Add intelligent extraction
```

---

# 13. Failure Modes & Mitigations

## Memory Bloat

Mitigation:

* consolidation passes
* TTL policies

---

## Stale Facts

Mitigation:

* last_verified
* confidence decay

---

## Conflicting Memories

Mitigation:

* merge policies
* provenance tracking

---

# 14. Recommended Initial Implementation Plan

1. Implement SQLite checkpointer.
2. Define namespace convention.
3. Create memory schemas.
4. Add explicit write APIs.
5. Add read filters.
6. Create consolidation pass.
7. Add optional vector layer later.

---

# 15. Guiding Philosophy

Memory is not magic.

Memory is:

* structured state
* versioned truth
* controlled persistence

The system must always answer:

> Why does the agent believe this?

If that answer cannot be traced — the memory system is failing.

---

# 16. Future Extensions (Non-Blocking)

* Memory confidence scoring evolution
* Automatic contradiction detection
* Memory summarization passes
* Multi-agent shared memory spaces
* Governance rules for write permissions

---

# END OF SPEC
