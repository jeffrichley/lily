We go process-first, not architecture-first.

For *this* phase (stealing concepts from OpenClaw), the first thing is to lock in **what Lily must do at runtime** as observable behaviors — then we can decide what “skills” and “commands” exist, and only then touch libraries.

## The process we’ll go through

### Phase 0 — Define scope for this phase (1 page)

**Output:** `scope_openclaw_extraction.md`

* What we are doing: *extracting reusable concepts* (skills/commands/memory/persona/loading precedence/tool policy).
* What we are not doing: *full Lily architecture*, engine runner, IR/kernel, etc.
* Success criteria: “We can run Lily in agent mode with a small set of first-party skills + user skills, loaded deterministically, and invoked in a predictable way.”

---

### Phase 1 — Write a Behavior Spec (not a feature list)

**Output:** `lily_agent_mode_behaviors.md`

This is not “list everything it should do.”
It’s the minimum observable behaviors, like:

* Loads skills from N directories with deterministic precedence
* Builds an “available skills” index each session
* Supports two invocation modes:

  1. conversational (LLM selects skill)
  2. explicit command dispatch (deterministic)
* Has a session concept: remembers selected agent, skill snapshot version, etc.
* Has persona bootstrap files (SOUL/IDENTITY/USER equivalents)
* Has tool policy gates (what tools are available in what contexts)

This keeps us from premature bloat.

---

### Phase 2 — Skill Format + Loader Contract (the core of “this part”)

**Outputs:**

* `skill_spec_v0.md` (format)
* `skills_loader_contract.md` (how discovery/precedence works)
* `skills_snapshot_contract.md` (how stability works across turns)

Decisions here:

* Skill is primarily **docs** (`SKILL.md`) + optional **frontmatter** for metadata.
* Identify which metadata matters now vs later:

  * requirements/eligibility
  * command name(s)
  * dispatch mode (prompt-rewrite vs tool-dispatch)
  * safety notes / permission hints

We’ll keep it simple and very OpenClaw-like at first.

---

### Phase 3 — Command Surface (how the human forces determinism)

**Outputs:**

* `commands_v0.md`
* `command_dispatch_rules.md`

Define a tiny set of built-in commands:

* `/skills` list/search
* `/skill <name>` force-use
* `/help <skill>`
* `/agent <name>` switch agent/persona
* `/reload_skills` (or bump watcher version)

This is how you avoid “agent vibes” when it matters.

---

### Phase 4 — Minimal First-Party Skills (curated, small)

**Output:** a `skills/` folder with 3–5 first-party skills

We do **not** brainstorm 50 things Lily can do.

We ship a tiny curated set that exercises the system:

* `filesystem_helper` (read/search/edit safely)
* `repo_maintainer` (PR template / CI checks guidance)
* `planit` or `work_compiler` (turn chat into a structured work artifact)
* `web_research` (bounded web lookup with citations style)

Goal: prove the mechanism.

---

### Phase 5 — Evaluation Harness

**Outputs:**

* `agent_mode_smoke_tests.md` (manual test scripts)
* `golden_transcripts/` (a few “expected behavior” conversations)

We test:

* precedence (workspace overrides personal overrides bundled)
* deterministic command dispatch works every time
* skill snapshot stability across turns
* persona files load predictably

---

## Answering your specific questions

### “Do we need to list out all the things we want it to do?”

No. That becomes a wishlist and slows you down.

Instead, we define:

* the **skill system behaviors**
* the **minimum command surface**
* a few **first-party skills** that prove the pipeline

Then you can add skills forever without changing the core.

### “Do we talk about architecture?”

Only at the boundary level (contracts). No deep architecture yet.

We define:

* file layout
* loading precedence rules
* how commands map to dispatch
* what is persisted per session (if anything)

### “Do we talk about libraries?”

Not yet. Libraries are implementation detail.
Once contracts are written, picking libs becomes obvious.

---

## The very first concrete thing to do (right now)

Create a single doc with:

1. Phase scope
2. Behavior spec bullets
3. The “done means” checklist

If you want, I’ll draft that file in your preferred markdown style in my next message and you can drop it straight into the repo.
