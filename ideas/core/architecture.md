Here’s the architecture I’d ship for Lily, plus the patterns that keep it clean, portable, and not over-engineered.

## Architecture patterns to use

### 1) Pipeline + Stages (core)

**Why:** Lily is a deterministic “document factory.” A pipeline keeps it predictable.

* Each stage takes **inputs + prior artifacts**, produces **new artifacts + a short state summary**.
* Stages are idempotent: rerun a stage, same output unless inputs changed.

### 2) State Machine (workflow control)

**Why:** Prevents “wandering chat” and makes progress auditable.
States like:

* `DISCOVERY → SPEC → ARCH → TASKS → PACKAGING → HANDOFF → REVIEW`

### 3) Command Pattern (slash-command UX)

**Why:** Matches what you like about spec-driven ecosystems.
Commands like:

* `/init`, `/spec`, `/arch`, `/tasks`, `/package`, `/handoff`, `/review`, `/amend`

Each command maps to one pipeline stage and produces files.

### 4) Template Method (consistent doc generation)

**Why:** Every artifact should look the same every time.
Each doc type has:

* header block
* required sections
* validation checklist
* “open questions” footer

### 5) Strategy Pattern (swap coders, swap formats)

**Why:** Tool-agnostic handoff is a core requirement.
Pluggable strategies for:

* **Coder targets:** Cursor vs Claude vs “OpenAI Codex-like”
* **Prompt format:** XML-tagged vs Markdown blocks
* **Repo type:** Python project vs Node vs “unknown”

### 6) Gatekeeper / Quality Gate (non-negotiable)

**Why:** Biggest risk is bad context.
A validation step that checks:

* spec completeness (reqs + non-goals + constraints)
* architecture decisions recorded
* tasks have acceptance criteria
* handoff package is “minimal but sufficient”

### 7) Event Sourcing-lite (audit trail)

**Why:** You want to know *why* docs changed.
Append-only `LOG.md` entries per command:

* command run
* inputs
* what changed
* unresolved questions

---

## Recommended app flow

### The “happy path”

1. **/init**

   * Creates skeleton docs and a project “sCOPE.
   * Outputs: `VISION.md`, `GOALS.md`, `NON_GOALS.md`, `CONSTRAINTS.md`

2. **/spec**

   * Lily interviews you briefly (or consumes your notes) and writes `SPEC.md`.
   * Outputs: `SPEC.md`, `ASSUMPTIONS.md`, `OPEN_QUESTIONS.md`

3. **/arch**

   * Turns spec into structure and decisions.
   * Outputs: `ARCHITECTURE.md`, `DATA_MODELS.md`, `INTERFACES.md`, `TECH_DECISIONS.md`

4. **/tasks**

   * Decomposes into implementable units for a coding agent.
   * Outputs: `TASKS.md`, `ACCEPTANCE_CRITERIA.md`, optional `TEST_PLAN.md`

5. **/package**

   * Produces the “coder handoff bundle” (the *only* thing the AI coder needs).
   * Outputs: `CODER_CONTEXT.md`, `CODING_RULES.md`, `PROMPTS/`, maybe `TASK_PACKS/T-###/`

6. **/handoff**

   * Lily emits a single copy/paste prompt (or a Cursor “instruction block”) referencing the bundle.

7. **/review**

   * After coder outputs code, Lily runs alignment checks and generates:
   * Outputs: `REVIEW.md` (what matches spec, what deviates, what to fix)

### The “iteration loop”

* If review finds drift: `/amend spec` or `/amend tasks` → rerun `/package` → re-handoff.

---

## Concrete module layout (simple and scalable)

```
lily/
  app.py                 # CLI/TUI entry
  core/
    state.py             # Workflow state machine
    pipeline.py          # Stage runner
    commands.py          # Command registry
  stages/
    discovery.py
    spec.py
    architecture.py
    tasks.py
    packaging.py
    review.py
  artifacts/
    templates/           # Jinja2 or simple formatters
    validators/          # quality gates
  adapters/
    coders/
      cursor.py
      claude.py
      openai.py
    formats/
      xml_tagged.py
      markdown_blocks.py
  storage/
    repo_fs.py           # writes/reads files from repo
    diff.py              # change detection, summaries
```

Minimal dependencies: `typer` (CLI), `pydantic`, maybe `jinja2` (optional).

---

## The key design decision

**Lily is a “document compiler,” not an agent that improvises.**
So the architecture should optimize for:

* repeatability
* traceability
* quality gates
* clean handoffs

