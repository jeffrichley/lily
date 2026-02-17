---
owner: "@team"
last_updated: "2026-02-17"
status: "reference"
source_of_truth: false
---

Alright. I’m going to be very precise here.

Given what you’ve already written:

* **LILY_AGENT_MODE_V0.md** (scope) 
* **lily_agent_mode_behaviors.md** (runtime contract) 
* **skills_loader_contract.md** (discovery + precedence + snapshot) 
* **SKILL_SPEC_V0.md** (skill format) 
* **SESSION_MODEL_V0.md** (session state model) 
* **commands_v0.md** (deterministic command surface) 

You are no longer in “design the spec” mode.

You are in **“prove the contracts are coherent”** mode.

---

# The Next Step

## 👉 Implement the Smallest Vertical Slice

Not all of Lily.

Not all commands.

Not all skills.

One complete, end-to-end slice:

> Load → Snapshot → `/skills` → `/skill` → Execute one skill.

If that works, the entire architecture holds.

If it doesn’t, your contracts are wrong — and it’s better to find that now.

---

# What That Vertical Slice Includes

## 1️⃣ Implement the Skills Loader (Minimal, Real)

From `skills_loader_contract.md` :

* Two roots only:

  * Bundled
  * Workspace
* Deterministic precedence
* Deterministic alphabetical ordering
* Eligibility filtering
* Build snapshot object

No reload yet.
No watchers.
No user root if you want to defer it.

Just:

```python
snapshot = build_skill_snapshot()
```

That’s it.

---

## 2️⃣ Implement Session Bootstrap

From `SESSION_MODEL_V0.md` :

Create:

```python
Session(
    session_id=...,
    active_agent="default",
    skill_snapshot=snapshot,
    model_config=...,
    conversation_state=[]
)
```

You now have:

* Snapshot stability
* A container for commands to operate on
* Deterministic command resolution boundary

Still no LLM logic needed.

---

## 3️⃣ Implement Two Commands Only

From `commands_v0.md` :

Implement only:

* `/skills`
* `/skill <name>`

Not `/agent`
Not `/reload_skills`
Not `/help`

Minimal surface.

This proves:

* Snapshot is real
* Deterministic resolution works
* Skill name matching is exact
* No fallback

---

## 4️⃣ Create One First-Party Skill

From `SKILL_SPEC_V0.md` :

Create a single bundled skill:

```
skills/
└── echo/
    └── SKILL.md
```

Make it `llm_orchestration`.

Something dead simple:

> “When invoked, respond by echoing the user request in uppercase.”

No tools.
No filesystem.
No complexity.

If `/skill echo` works deterministically, your entire skill pipeline works.

---

# Why This Is the Correct Next Step

Right now you have:

* Clean contracts
* Clear boundaries
* Deterministic rules
* Strong anti-drift guarantees

But you have not yet tested:

* Whether these contracts compose cleanly in code
* Whether any circular dependency exists
* Whether skill selection + session snapshot + command dispatch create edge-case leaks

This vertical slice will expose:

* Loader mistakes
* Snapshot drift mistakes
* Command parsing bugs
* Spec ambiguity

Before the system gets big.

---

# What You Should Not Do Next

Do not:

* Add more commands
* Add user root
* Add tool policy enforcement
* Add multiple agents
* Add model switching
* Add dynamic persona reload
* Add reload watchers
* Add CI checks
* Add plugin packs

That’s surface expansion.

You haven’t validated the core yet.

---

# Definition of “Slice Complete”

You are done with this step when:

* `build_skill_snapshot()` produces deterministic output
* Session stores it
* `/skills` lists snapshot exactly
* `/skill echo` invokes only `echo`
* No fallback happens
* Snapshot remains stable even if filesystem changes mid-session

If that works, you have proven:

> Lily Agent Mode V0 is structurally sound.

And then — and only then — we add reload.

---

If you want, next message I can give you:

* The exact file structure
* The minimal Python module layout
* The clean execution flow diagram
* Or the 10-step implementation checklist you can hand to Lily-the-coder

Your move.
