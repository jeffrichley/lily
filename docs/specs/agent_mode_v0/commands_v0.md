```
docs/specs/agent_mode_v0/commands_v0.md
```

---

# Command Surface Contract (V0)

This document defines the **minimal deterministic command surface** for Lily Agent Mode v0.

Commands exist to:

* Override probabilistic behavior
* Control session state
* Inspect skill availability
* Maintain deterministic execution boundaries

If a behavior is not defined here, it does not exist in v0.

---

# 1. Design Principles

The command surface must be:

* Deterministic
* Explicit
* Snapshot-aware
* Session-scoped
* Non-probabilistic

Commands must:

* Never rely on LLM interpretation
* Never silently fallback
* Fail clearly when invalid
* Operate strictly against session state

---

# 2. Command Parsing Rules

## 2.1 Prefix

Commands must begin with:

```
/
```

Example:

```
/skills
/skill plan_compiler
/plan
```

If a message begins with `/`, it is parsed as a command.

No fuzzy parsing.
No LLM classification.
No "maybe it's a command."

---

## 2.2 Exact Match Requirement

Command names must match exactly.

No semantic matching.
No partial matching.
No prefix inference.

---

# 3. Required Commands (V0)

The following commands must exist.

---

## 3.1 `/skills`

### Purpose

List available skills from the current session snapshot.

### Behavior

* Reads `skill_snapshot`
* Outputs skill names
* Includes optional summary (if available)
* Must not trigger skill reload
* Must not re-scan filesystem

### Determinism

Given the same snapshot, output must be identical.

---

## 3.2 `/skill <name>`

### Purpose

Force invocation of a specific skill.

### Behavior

1. Look up `<name>` in session snapshot.
2. If not found:

   * Fail clearly.
   * Do not fallback.
3. If found:

   * Invoke skill deterministically.

Invocation rules:

* If `invocation_mode: llm_orchestration`

  * Inject skill instructions.
* If `invocation_mode: tool_dispatch`

  * Call `command_tool` directly.

Must not select another skill.

Must not reinterpret request.

---

## 3.3 `/reload_skills`

### Purpose

Rebuild skill snapshot.

### Behavior

1. Re-run skill discovery
2. Apply precedence resolution
3. Apply eligibility filtering
4. Build new snapshot
5. Replace session `skill_snapshot`
6. Increment `snapshot_version`

Must not alter:

* conversation_state
* active_agent
* model_config

---

## 3.4 `/agent <name>`

### Purpose

Switch active agent/persona.

### Behavior

1. Validate `<name>` exists.
2. Update `active_agent`.
3. Rebuild system context with persona files.

Must not mutate:

* skill_snapshot
* conversation history
* model configuration (unless agent defines override; optional future feature)

---

## 3.5 `/help <skill>`

### Purpose

Display skill summary and metadata.

### Behavior

1. Look up skill in snapshot.
2. Output:

   * summary
   * invocation_mode
   * required tools
   * eligibility requirements

Must not execute the skill.

Must not read filesystem.

---

# 4. Optional Alias Commands (Skill-Defined)

If a skill declares:

```yaml
command: plan
```

Then:

```
/plan
```

is treated as:

```
/skill plan_compiler
```

Rules:

* Alias must not collide with built-in commands.
* Built-ins always win.
* If collision occurs, skill is excluded at load time.

Alias resolution must occur before LLM involvement.

---

# 5. Command Resolution Order

When parsing input:

1. If input starts with `/`

   * Parse as command.
   * Do not pass to LLM.
2. If no leading `/`

   * Normal conversational flow.
   * LLM may select skill.

Commands always override conversational routing.

---

# 6. Error Handling Contract

## 6.1 Unknown Command

If command does not exist:

* Return clear error.
* Do not fallback to conversation.

---

## 6.2 Missing Arguments

If required argument missing:

Example:

```
/skill
```

Must return:

```
Error: /skill requires a skill name.
```

No interpretation.

---

## 6.3 Invalid Skill Name

If `/skill <name>` not in snapshot:

* Return explicit failure.
* Do not fallback.
* Do not suggest alternatives (optional future UX feature).

---

# 7. Determinism Guarantees

Commands must:

* Operate strictly on session state
* Not depend on LLM reasoning
* Not mutate unrelated session fields
* Produce identical behavior given identical session state

LLM outputs may remain probabilistic.

Command behavior must not.

---

# 8. Out of Scope (V0)

Command surface does not include:

* `/think`
* `/verbose`
* `/reset`
* `/status`
* `/memory`
* `/models`
* `/approve`
* `/sessions`
* Multi-lane execution controls
* Elevated privilege mode
* Admin controls
* Queue inspection
* Policy debugging

We are not building OpenClaw OS.

We are building a minimal deterministic operator.

---

# 9. Definition of Done (Commands V0)

Command surface is complete when:

* `/skills` lists snapshot deterministically
* `/skill <name>` forces deterministic invocation
* `/reload_skills` rebuilds snapshot cleanly
* `/agent <name>` switches persona deterministically
* `/help <skill>` inspects metadata without execution
* Alias commands work when defined
* No command path relies on LLM routing

If any command can silently fall back into probabilistic behavior, V0 is not satisfied.
