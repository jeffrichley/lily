Here’s a concrete software design for the **two-layer architecture** (Headless Core + UI shells) that lets you ship a CLI first and later bolt on a full TUI **without rewriting logic**.

## Architecture: Headless Core + UI Shells

### Layer A — Headless Core (the product)

**Responsibilities**

* Workflow state machine (phases)
* Artifact generation (docs)
* Validation gates
* Task/Run/Worker models
* Job scheduling + run logs
* Persistence (filesystem + git)

**Key rule:** Core exposes **commands + events**, not UI.

### Layer B — UI Shells (replaceable skins)

* **CLI shell**: `lily /spec`, `lily /tasks`, etc.
* **REPL shell**: interactive session, slash commands
* **TUI shell**: panes, kanban, logs, diffs

**Key rule:** UI shells call the **same core command API**.

---

## Core design: “Command Bus + Use Cases + Events”

### Primary module boundaries

```
core/
  application/     # use cases (commands)
  domain/          # entities + rules
  infrastructure/  # filesystem, git, external tools
ui/
  cli/
  repl/
  tui/
```

### Data model (domain)

* **Project**: name, root path, active phase
* **Artifact**: path, type, checksum, updated_at
* **Task**: id, title, spec_refs, acceptance_criteria, status, owner(worker)
* **Worker**: id, type(cursor/claude), status, current_task
* **Run**: id, worker_id, task_id, start/end, log stream, outcome

---

## Flow of the app

1. UI parses user intent (command + args)
2. UI calls **CommandBus.execute(Command)**
3. Core:

   * loads project state
   * validates prerequisites
   * runs use case
   * writes artifacts
   * records Run/Event log
4. Core returns a structured **Result**
5. UI renders Result (CLI prints text, TUI updates panes)

---

## GoF patterns to use (and where)

### 1) **Command Pattern** (non-negotiable)

**Purpose:** CLI and TUI both invoke the same operations.

* Each action is a `Command` object:

  * `InitProject`
  * `GenerateSpec`
  * `GenerateArchitecture`
  * `DecomposeTasks`
  * `PackageHandoff`
  * `ValidateArtifacts`

**CLI mapping:** `lily spec` → `GenerateSpecCommand`
**TUI mapping:** button/keybind → `GenerateSpecCommand`

### 2) **Facade** (simple API for UIs)

**Purpose:** UIs talk to one object, not 30 services.

* `LilyApp` facade exposes:

  * `execute(command) -> Result`
  * `subscribe(event_handler)` (optional)
  * `get_status()`

### 3) **Template Method** (consistent artifact generation)

**Purpose:** All docs follow consistent structure.

Base class:

* `ArtifactGenerator.generate()`:

  1. load template
  2. fill sections
  3. append metadata footer
  4. validate required sections
  5. write file

Concrete generators:

* `SpecGenerator`
* `ArchitectureGenerator`
* `TaskListGenerator`

### 4) **Strategy** (swap backends cleanly)

**Purpose:** you’ll swap “how to package” and “how to handoff.”

Strategies:

* `PromptFormatStrategy` (xml-tagged vs markdown blocks)
* `CoderTargetStrategy` (Cursor vs Claude vs OpenAI)
* `DiffStrategy` (git diff vs file diff)
* `ValidationStrictnessStrategy` (tight vs relaxed)

### 5) **State Pattern** (phase enforcement)

**Purpose:** “Spec must exist before Arch” becomes enforceable logic.

States:

* `DiscoveryState`
* `SpecState`
* `ArchitectureState`
* `TasksState`
* `PackagingState`
* `HandoffState`
* `ReviewState`

Each state controls allowed commands:

* In `SpecState`, allow `/spec`, deny `/package` until arch/tasks exist.

### 6) **Observer** (events to UI)

**Purpose:** TUI needs live updates; CLI can ignore or print them.

Core emits events:

* `ArtifactWritten`
* `ValidationFailed`
* `TaskStatusChanged`
* `RunStarted/RunCompleted`

CLI subscribes → prints a line
TUI subscribes → updates panels

### 7) **Abstract Factory** (build the app with the right adapters)

**Purpose:** clean composition without if-else soup.

Factories create:

* storage adapters (filesystem, git)
* coder target adapters
* prompt formatters

Example:

* `ProductionAppFactory`
* `TestAppFactory`

### 8) **Adapter** (external systems)

**Purpose:** Cursor/Claude/OpenAI are “external services” behind a stable interface.

* `CoderAdapter.send_handoff(package) -> HandoffReceipt`
  Even if early versions just produce copy/paste text, the interface stays.

---

## The “shared core” API contract (what UI calls)

### Command execution

* `Result` contains:

  * `summary` (short human-readable)
  * `changed_files` (list)
  * `diagnostics` (warnings/errors)
  * `events` (optional structured)

### Query endpoints (read-only)

* `get_project_status()`
* `list_tasks(filter=...)`
* `tail_run_logs(run_id)`
* `artifact_index()`

This is what powers a TUI without reimplementing logic.

---

## Persistence strategy (keeps it portable)

* Everything under `.lily/`:

  * `.lily/state.json` (phase + pointers)
  * `.lily/runs/<run_id>/log.txt`
  * `.lily/index.json` (artifact index + hashes)
  * `.lily/tasks.json` (or tasks in markdown + index)

Artifacts live in the repo root or `/docs`.

---

## Why this design cleanly supports CLI first, TUI later

* CLI and TUI share:

  * **Commands**
  * **Use cases**
  * **Validators**
  * **Storage**
  * **Events**
* Only difference is rendering + input handling

So you don’t “reuse the TUI”—you reuse the **core**, and the TUI is just another client.

---

## If you want one “anchor” pattern to remember

**Hexagonal Architecture (Ports & Adapters)** is the overarching style:

* Core defines ports (storage, coder, prompt format)
* Adapters implement them
* UI is just another adapter

(GoF patterns above plug into that style nicely.)

---

If you’d like, I can update your existing “Lily – Spec-driven Orchestration Architecture” doc with a new section:

* **Two-Layer Architecture**
* **Command Bus API**
* **GoF pattern mapping**
* **Module tree**
* **Event model**

…and keep it consistent with the rest of your design doc.
