---
owner: "@team"
last_updated: "2026-02-17"
status: "archived"
source_of_truth: false
---


# 🎯 What Phase Of Lily Are We Actually In?

Right now we are not building:

* Gateway
* Multi-channel chat routing
* Node pairing
* Mobile apps
* Plugin marketplace
* Browser automation platform
* Cron engine
* OAuth provider manager

We are building:

> Lily agent mode as a local, skill-driven operator.

That’s it.

Everything else is noise for now.

---

# 🪓 Step 1: Carve OpenClaw Down To What Matters For Lily

From that entire list, the only parts relevant to this phase are:

### Core Skill System

* Skill loading precedence
* Skill frontmatter metadata
* Deterministic command dispatch
* Skill snapshot per session

### Persona Model

* SOUL.md
* IDENTITY.md
* USER.md
* AGENTS.md

### Tool Policy Layer

* Allow/deny tools
* Owner-only commands
* Session write locking (conceptually)

### Runtime Resilience (conceptually, not fully)

* Queueing concept
* Retry logic
* Failover mindset

That’s it.

Everything else is platform expansion.

---

# 🧭 Where We Go From Here (Clear Process)

## Phase 1 — Define Lily Agent Mode Scope (1 doc, small)

We create:

`LILY_AGENT_MODE_V0.md`

It answers:

* What does Lily load?
* How does Lily select skills?
* What is deterministic vs LLM-driven?
* What is persisted per session?
* What is NOT included in V0?

No architecture.
No libraries.
No runtime yet.

Just contracts and boundaries.

---

## Phase 2 — Define Skill Contract (Tiny)

We create:

`SKILL_SPEC_V0.md`

Define:

* Required frontmatter
* Optional metadata
* Invocation mode
* Permissions hints
* Command mapping

Keep it minimal.

If it doesn’t support execution decisions, it doesn’t belong in v0.

---

## Phase 3 — Define Session Concept

We create:

`SESSION_MODEL_V0.md`

Session tracks:

* active agent
* skill snapshot version
* active model config
* conversation state

That’s enough.

No multi-channel routing.
No remote nodes.

---

## Phase 4 — Build 3 First-Party Skills

Only three.

Not 52.

Examples:

* `repo_maintainer`
* `plan_compiler`
* `research_assistant`

If the system works with three,
it works with thirty later.

---

# 🧠 The Rule For This Stage

If a feature does not help Lily:

* Load skills
* Select skills
* Execute skills safely
* Preserve persona
* Allow deterministic override

It does not exist.

---

# 💡 Strategic Insight

OpenClaw is a **platform OS**.

You are building:

* A compiler-grade execution core
* With skill-driven behavior
* And conversational skin

If you try to copy their surface,
you will lose your differentiator.

Your differentiator is:

Typed contracts
Compile boundary
Kernel execution
Replayability

OpenClaw does not have that layer.

---

# 🎯 So The Actual First Thing We Do

We do not talk libraries.

We do not talk gateway.

We do not talk plugins.

We write:

A 1-page document:

**“What is Lily Agent Mode v0?”**

And it must fit on one page.

If it doesn’t fit on one page,
it’s too big.

---

If you want, I’ll draft that one-page scope right now in your tone — clean, sharp, non-bloated.
