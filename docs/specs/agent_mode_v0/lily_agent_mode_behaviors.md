---
owner: "TBD"
last_updated: "TBD"
status: "reference"
source_of_truth: false
---

```
docs/specs/agent_mode_v0/lily_agent_mode_behaviors.md
```

Tight. Contract-focused. No architecture leakage.

---

# Lily Agent Mode — Observable Behaviors (V0)

This document defines the **runtime behaviors** of Lily Agent Mode v0.

This is not an architecture document.
This is not an implementation guide.
This is a contract describing what Lily must do at runtime.

If a behavior is not defined here, it does not exist in v0.

---

# 1. Runtime Scope

Lily Agent Mode v0 is:

> A local, skill-driven conversational operator with deterministic override capabilities.

It supports:

* Skill loading
* Skill selection
* Deterministic skill invocation
* Persona bootstrap
* Session tracking
* Minimal tool policy gating

It does not support:

* Multi-channel routing
* Remote nodes
* Plugin marketplace
* Background jobs
* Distributed execution
* Embedded memory indexing
* Typed execution graph
* Workflow compiler layer

---

# 2. Skill Loading Behavior

## 2.1 Skill Sources

At session start, Lily loads skills from the following sources:

1. Bundled skills directory
2. User-level skills directory (optional in v0)
3. Workspace skills directory

## 2.2 Deterministic Precedence

If duplicate skill names exist:

```
Workspace > User > Bundled
```

The highest-precedence version wins.

This precedence must be deterministic and stable across runs.

## 2.3 Eligibility Filtering

A skill may include optional eligibility metadata (OS, environment variables, binaries).

If eligibility conditions fail:

* The skill is excluded from the available skills index.

No partial loading.

## 2.4 Session Skill Snapshot

At session creation:

* Lily builds an “available skills snapshot.”
* This snapshot is stored in the session.
* The snapshot remains stable for the duration of the session.
* Snapshot updates require explicit reload.

This prevents mid-session skill drift.

---

# 3. Skill Selection Behavior

Lily supports two invocation modes.

---

## 3.1 Conversational Mode (LLM-driven)

* The model may select at most one relevant skill.
* If selecting a skill, it must read `SKILL.md` before executing.
* Skill selection is probabilistic.
* Selection must be explicitly declared before use.

If no skill is relevant, Lily may answer directly.

---

## 3.2 Deterministic Mode (User-forced)

The user may invoke:

```
/skill <name>
```

This behavior:

* Bypasses skill selection reasoning.
* Forces the named skill.
* Fails clearly if the skill does not exist.
* Cannot silently fallback to another skill.

If a skill supports deterministic command dispatch:

* It may bypass prompt rewriting.
* It may directly invoke a mapped tool.

Deterministic invocation always overrides conversational routing.

---

# 4. Session Behavior

Each session tracks:

* Active agent
* Skill snapshot version
* Active model configuration
* Conversation state

Sessions are local-only.

There is no:

* Multi-channel session routing
* Remote session store
* Distributed execution context

Session behavior must be stable and replayable within the same runtime.

---

# 5. Persona Bootstrap Behavior

At runtime start, Lily loads persona files if present:

* `SOUL.md`
* `IDENTITY.md`
* `USER.md`
* `AGENTS.md`

These files:

* Are injected into the system context.
* Are human-editable.
* Persist across sessions.
* Override default persona.

If a file does not exist, it is ignored.

There is no dynamic persona mutation engine in v0.

---

# 6. Tool Policy Behavior

Lily supports minimal tool gating.

* Skills may declare required tools.
* Tool access may be filtered.
* Deterministic commands may require owner-only execution.

There is no sandbox engine in v0.

There is no plugin trust tier system in v0.

Tool policy behavior must be explicit and inspectable.

---

# 7. Command Surface (V0)

Lily must support:

* `/skills` — list available skills
* `/skill <name>` — force skill usage
* `/help <skill>` — show skill summary
* `/agent <name>` — switch active agent (if supported)
* `/reload_skills` — rebuild skill snapshot

All command behavior must be deterministic.

Commands must not rely on probabilistic routing.

---

# 8. Stability Rules

Lily Agent Mode v0 must guarantee:

* Deterministic skill precedence
* Stable session snapshot
* Deterministic command dispatch
* Explicit failure when ambiguity exists
* No silent fallback behavior

If the system cannot deterministically resolve an action, it must fail clearly.

---

# 9. Out of Scope (Explicitly Not Included)

The following are not part of v0:

* Plugin registry
* Skill marketplace
* Multi-agent orchestration
* Agent-to-agent messaging
* Background execution lanes
* Typed execution graph
* Workflow compiler
* Memory vector search
* External provider rotation logic
* Cron scheduler
* Webhook engine
* Container sandboxing
* Enterprise governance layer

These may exist in future versions, but they do not exist in v0.

---

# 10. Definition of Done (V0)

Lily Agent Mode v0 is complete when:

* Skills load deterministically from multiple directories.
* Skill precedence behaves exactly as specified.
* Conversational and deterministic invocation modes both work.
* Persona files inject correctly.
* Session snapshot prevents drift.
* Command surface behaves predictably.
* Three first-party skills execute successfully.
* Manual smoke tests pass.

If any of these behaviors are unstable, v0 is not complete.


