---
owner: "@team"
last_updated: "2026-02-17"
status: "reference"
source_of_truth: false
---

```
docs/specs/agent_mode_v0/SESSION_MODEL_V0.md
```

This is tight, explicit, and intentionally boring in the best way.

---

# Session Model (V0)

This document defines the **session state model** for Lily Agent Mode v0.

The session model specifies:

* What state Lily persists
* What state Lily must not persist
* What guarantees a session provides
* What boundaries exist between sessions

This is a behavioral contract, not an implementation guide.

If state is not defined here, it does not exist in v0.

---

# 1. Purpose of a Session

A session represents:

> A stable conversational execution context with a fixed skill snapshot and persona configuration.

Sessions exist to:

* Preserve conversational continuity
* Prevent skill drift mid-run
* Ensure deterministic command resolution
* Track active agent configuration

A session is local-only in v0.

There is no distributed session layer.

---

# 2. Required Session Fields

A session must track the following fields.

## 2.1 `session_id`

* Unique identifier for the session
* Stable for the lifetime of the session

Format is implementation-defined.

---

## 2.2 `active_agent`

* Name or identifier of the currently active agent/persona
* Defaults to the system default agent

Changing agent via `/agent <name>` updates this field.

---

## 2.3 `skill_snapshot`

The resolved skill index at session creation or reload.

This must include:

* `snapshot_version`
* List of available skills
* Resolved source for each skill
* Optional diagnostic metadata

This snapshot is immutable unless explicitly reloaded.

---

## 2.4 `model_config`

The active model configuration for this session.

This may include:

* model name
* temperature
* reasoning/thinking level (if applicable)
* verbosity mode (if applicable)

Model configuration must remain stable unless explicitly changed.

---

## 2.5 `conversation_state`

The conversation history required for LLM context.

This includes:

* Ordered list of prior messages
* Role attribution (user/system/assistant/tool)
* Any structured tool invocation results

The session must maintain proper role ordering.

No implicit reordering.

---

# 3. Optional Session Fields (V0)

These may exist but are not required:

* `created_at`
* `last_updated_at`
* `reload_count`
* `command_history`
* lightweight debug metadata

These fields must not affect runtime behavior unless explicitly defined elsewhere.

---

# 4. Snapshot Stability Guarantees

Within a session:

* Skill selection uses only the stored `skill_snapshot`
* Command resolution uses only the stored `skill_snapshot`
* Filesystem changes do not affect available skills
* Persona file edits do not affect the session unless reloaded (implementation choice; see below)

---

# 5. Persona Loading Semantics

Persona files (`SOUL.md`, `IDENTITY.md`, `USER.md`, `AGENTS.md`) are loaded:

* At session start
* Or at runtime start before session creation

In v0, persona injection behavior must be consistent for the entire session.

Recommended rule:

* Persona files are read at session creation and treated as fixed for that session.

If you prefer dynamic reload, it must be explicit (e.g., `/reload_persona`), not automatic.

No silent persona drift.

---

# 6. Session Lifecycle

## 6.1 Session Creation

A session is created when:

* A new conversation begins
* Or explicitly via `/new` (if supported)

At creation:

1. Skills are loaded and snapshot is stored
2. Persona files are injected
3. Model configuration is initialized
4. Conversation state is empty (or system bootstrapped)

---

## 6.2 Session Continuation

For each new message:

* Conversation state is appended
* Model context is rebuilt using session state
* Skill snapshot remains unchanged

---

## 6.3 Session Reload

Reload operations may include:

* `/reload_skills`
* `/agent <name>`
* `/reload_persona` (optional future command)

Reload must:

* Explicitly update the relevant field
* Not mutate unrelated session fields

No implicit reload behavior.

---

## 6.4 Session Termination

When a session ends:

* Session state may be discarded
* Or serialized locally (implementation choice)

V0 does not require persistent storage across runtime restarts.

---

# 7. Determinism Requirements

Within a session:

* Given the same conversation state and model configuration,
* and the same skill snapshot,

The system must:

* Resolve deterministic commands identically
* Provide identical skill index results
* Avoid mid-session capability changes

LLM outputs may remain probabilistic.

Loader and command behavior must not.

---

# 8. Isolation Guarantees

Each session must be isolated from other sessions.

A session must not:

* Access another session’s skill snapshot
* Mutate another session’s model configuration
* Share conversation state

No global mutable session state in v0.

---

# 9. Out of Scope (Explicitly Not Included)

V0 session model does not include:

* Multi-channel session routing
* Cross-device synchronization
* Distributed session stores
* Session locking across processes
* Long-term vector memory indexing
* Background job tracking
* Enterprise audit trails
* Full replay bundles
* Deterministic execution logs with artifact hashing

These may exist in future versions.

They do not exist in v0.

---

# 10. Definition of Done (Session Model V0)

The session model is complete when:

* A session correctly captures:

  * active agent
  * skill snapshot
  * model configuration
  * conversation state
* Skill snapshot remains stable unless explicitly reloaded
* Persona injection remains stable within a session
* Deterministic commands operate strictly against session state
* Multiple sessions can run without state bleed

If any state mutates implicitly or leaks across sessions, v0 is not satisfied.

