Start with the **headless core skeleton**—but the *very first* work item should be the thing that forces every architectural decision to line up:

## First thing to build: the “Command Pipeline Spine”

Not a cross-cutting concern, not a TUI feature, not even spec generation.

### Build **one vertical slice** that proves:

* commands are real objects
* state exists on disk
* artifacts are written deterministically
* validators can block progression
* UI (CLI) calls the same core API you’ll later reuse in a TUI

That spine becomes the rails everything else rides on.

---

## The first command to implement

### ✅ `init` (Project bootstrap) — this is the correct first command

Because it establishes:

* `.lily/` workspace
* the state machine starting state
* the artifact folder layout
* the logging/event channel
* “where everything lives” for all later commands

**Outputs (minimum):**

* `.lily/state.json` (phase = `DISCOVERY`, project metadata)
* `.lily/log.md` (append-only)
* `docs/` (or `spec/`) folder
* stub artifacts:

  * `VISION.md`
  * `GOALS.md`
  * `NON_GOALS.md`
  * `CONSTRAINTS.md`
  * `OPEN_QUESTIONS.md`

**Validation:** ensure empty repo? (optional), ensure paths created, ensure idempotency.

---

## The cross-cutting concern you *should* do first

Only one: **Artifact Store + State Store**
Because every stage needs read/write and diffs.

So the order is:

1. **Storage layer (filesystem + tiny index)**
2. **Command bus + result object**
3. **`init` command implemented end-to-end**
4. **CLI wiring to call the command bus**

That is the smallest “vertical slice” that proves the architecture.

---

## Why not start with spec generation?

Because spec generation will tempt you into:

* prompt formatting debates
* “how smart should Lily be”
* template complexity
* validation complexity

…and you’ll still lack the rails to ship it.

---

## Milestone definition (what “done” looks like)

Run:

```bash
lily init myproj
```

And you get:

* deterministic files created
* a clean console result that lists files written
* state saved to disk
* re-running it doesn’t break anything (idempotent or safe-fail)
* a `lily status` command can read state and print phase + artifacts present

That’s it. That’s the spine.

---

## Immediately after `init`

Second command should be:

### `status`

It’s tiny, but it forces you to implement:

* state reading
* artifact indexing
* a stable query surface for the future TUI

---

If you want, I’ll write the exact **first sprint plan** (3–6 tasks with acceptance criteria) so you can implement this spine quickly and not drift.







give me a list of alll items/artifacts init will make






Here is the **complete, opinionated list** of artifacts that `init` should create. This is designed so **every later command depends on it**, and nothing here will need to be redesigned when you add the TUI.

I’m separating **user-facing artifacts** from **system/internal artifacts** on purpose.

---

## User-Facing Artifacts (the “project truth”)

These live in the repo and are meant to be read and edited by humans *and* AI coders later.

```
docs/
├── VISION.md
├── GOALS.md
├── NON_GOALS.md
├── CONSTRAINTS.md
├── ASSUMPTIONS.md
├── OPEN_QUESTIONS.md
```

### What each is for (brief but strict)

* **VISION.md**

  * One–two page narrative
  * What this system *is*
  * Who it’s for
  * Why it exists

* **GOALS.md**

  * Explicit success criteria
  * Measurable where possible
  * Ordered by importance

* **NON_GOALS.md**

  * Explicit exclusions
  * Prevents scope creep
  * Critical for AI coder alignment

* **CONSTRAINTS.md**

  * Hard rules (tech, legal, performance, org)
  * “Must / must not” language

* **ASSUMPTIONS.md**

  * Things believed to be true but not yet verified
  * Forces later validation

* **OPEN_QUESTIONS.md**

  * Unknowns blocking later phases
  * Should trend toward empty over time

All of these should be created with:

* section headers
* guidance comments
* empty bullet lists ready to fill

---

## System / Internal Artifacts (the “control plane”)

These live under `.lily/` and are **never manually edited**.

```
.lily/
├── state.json
├── index.json
├── log.md
├── config.json
├── runs/
│   └── .gitkeep
└── tasks/
    └── .gitkeep
```

### Purpose of each

#### `.lily/state.json`

Single source of truth for workflow state.

Contains:

```json
{
  "phase": "DISCOVERY",
  "project_name": "...",
  "created_at": "...",
  "last_updated": "...",
  "version": "0.1.0"
}
```

Used by:

* `status`
* phase gating
* TUI indicators

---

#### `.lily/index.json`

Artifact index + checksums.

Tracks:

* file path
* artifact type
* last modified
* hash

Used for:

* change detection
* validation
* review diffs
* TUI file trees

---

#### `.lily/log.md`

Append-only audit log.

Entries like:

```
[2026-01-14 19:22] init
- created docs/VISION.md
- created .lily/state.json
```

Used for:

* traceability
* debugging
* explaining “why did this change?”

---

#### `.lily/config.json`

Project-level Lily configuration.

Examples:

* default prompt format
* preferred coder target
* validation strictness

Safe to grow later without breaking init.

---

#### `.lily/runs/`

Directory for execution records.

Each future AI dev run gets:

```
.lily/runs/<run_id>/
├── task.json
├── logs.txt
├── summary.md
```

Empty at init, but structure must exist.

---

#### `.lily/tasks/`

Future task storage.

* May later hold per-task folders
* Or act as backing store for a kanban view
* Exists now so later commands don’t mutate structure

---

## Optional but recommended (decide once)

If you want to be very clean from day one:

```
docs/README.md
```

Explains:

* what the docs folder is
* how Lily uses it
* “don’t delete these files”

---

## What `init` explicitly must NOT do

* ❌ Generate specs
* ❌ Ask architecture questions
* ❌ Write any code
* ❌ Invoke an LLM
* ❌ Assume language or framework

Init is **pure structure + state**.

---

## Acceptance criteria for `init`

`lily init` is correct if:

* Running it twice does not corrupt state
* All files are created deterministically
* `lily status` can read phase + artifacts
* Nothing here needs to change when:

  * spec generation is added
  * multiple AI devs are added
  * TUI is added

---

If you want, next I can:

* turn this into a **checklist + test plan**
* write the **exact contents/templates** for each markdown file
* define the **JSON schemas** for state/index/config
