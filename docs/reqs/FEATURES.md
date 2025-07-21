

# 🌸 Project Lily – Feature List

A modular, interactive system that helps you plan, clarify, and validate AI-assisted development using markdown files, task pipelines, and agent-ready prompts. Fully agent-compatible, CLI-native, and designed to scale across domains.

---

## 🧠 1. Context & Planning

### 📝 Initial.md Authoring Assistant

Guides users through the creation of a structured `initial.md` file describing each feature in human-readable language. The assistant asks clarifying questions when inputs are incomplete or ambiguous, ensuring a rich, clear specification. Key sections include: `FEATURE`, `EXAMPLES`, `DOCUMENTATION`, and `OTHER CONSIDERATIONS`.

### 🧾 PRP Generator

Automatically generates a `prp.md` (Product Requirements Prompt) from `initial.md` using a configurable template system. PRPs include goals, inputs/outputs, constraints, and success conditions, designed to be consumed directly by AI coding agents.

### 🔧 Domain-Specific Template Resolution

Lily searches for a specialized template under `examples/<domain>/prp.md`. If found, it uses that to generate the PRP. If not, it falls back to a default `prp_base.md` located in `PRPs/templates/`. This ensures flexibility across varied engineering domains.

### 🧭 CLAUDE.md + LILY\_RULES.md Integration

* `CLAUDE.md`: Defines rules and constraints for coding agents (e.g., naming conventions, frameworks to use).
* `LILY_RULES.md`: Governs Lily's tone, formatting, behaviors, prompt style, and UX interaction philosophy. This ensures consistent guidance and structure for all Lily-generated outputs.

### 📚 Example Pattern Matching

Automatically indexes the `examples/` directory to extract reusable patterns, which can be suggested in `initial.md` or injected into `prp.md`. These code snippets help ground agent responses in established conventions.

### 🔄 Rework & Critique Loop

If generated code fails validation or doesn’t meet expectations, Lily triggers a rework cycle. This includes auto-rewriting prompts, updating PRPs, or flagging the need for human clarification.

---

## 📋 2. Task Lifecycle & State Management

### 📌 Task State Model

Tracks tasks through a complete lifecycle:

```
[📝 todo] → [🔄 in_progress] → [✅ complete]
               ↓
         [♻️ needs_rework]
```

This ensures transparency in what’s being worked on, what’s blocked, and what’s been completed.

### 🧵 Task Metadata & Ownership

Each task contains metadata: title, priority, tags, agent assignment, creation date, and dependency info. Under the hood, Lily uses UUIDs for tracking but hides them from users.

### 🕸️ Dependency Awareness & Future Graph

Lily detects when features depend on one another (e.g., a dashboard needing user auth). A full task dependency graph is planned, allowing auto-scheduling of work based on readiness.

### 📥 Task Freezing and Archiving

Once a PRP is finalized, it is locked to prevent accidental edits. Completed tasks are archived to declutter the dashboard but remain searchable.

---

## 🖥️ 3. CLI / TUI / UX Features

### 💻 Interactive CLI Interface

Provides commands like `lily init`, `lily new-feature`, `lily generate-prp`, `lily validate`, and `lily tui`. All tasks can be driven from a command-line shell with rich feedback.

### 🧮 Kanban-style Terminal UI

Displays tasks grouped by state with emoji indicators. Keyboard shortcuts allow switching columns, editing features, approving outputs, or requesting rework.

```
╔════════════════════════════════════════════════╗
║   📝 Todo     🔄 In Progress   ✅ Complete      ║
║   feat_1       feat_3          feat_2          ║
║   feat_4       feat_5                          ║
╚════════════════════════════════════════════════╝
```

### 📑 Right-Side Context Panel

TUI includes a scrollable, syntax-highlighted preview panel showing the selected task’s `initial.md`, `prp.md`, and any logs or feedback from validation.

### 🧠 Emoji-Enhanced UX

Lily uses expressive symbols and clear feedback for statuses, rework notices, and validation checks:

* 📝 = Todo
* 🔄 = In Progress
* ✅ = Done
* ❌ = Failed
* ♻️ = Rework
* 🧪 = Test

### ✏️ Markdown Editing with Live Preview

Edit `initial.md` or `prp.md` directly in the TUI with live formatting previews. Also supports undo/redo and conversational edits (e.g., “Lily, add an example for X”).

### 🔄 Save and Resume Sessions

All changes are persisted. When you return, Lily picks up exactly where you left off—drafts, open chats, uncommitted PRPs, etc.

---

## 🤖 4. Agent Integration & MCP Tooling

### 🔌 MCP Server Compatibility

Lily serves tasks over MCP-compatible tools using JSON-RPC or HTTP. Tooling includes:

* `get_next_task_id`
* `get_task_context`
* `execute_task`
* `finalize_task`
* `suggest_tasks`

### 🎯 Agent-Agnostic Output Routing

Whether agents are using Cursor, Claude, Petal, or another tool, Lily packages the same PRP and metadata payloads for seamless drop-in consumption.

### 📁 Filesystem-Based Review

Agents are expected to write code directly to disk. Lily then inspects file outputs (e.g., `utils.py`, `test_example.py`) and compares them against spec and test results.

### 🧠 Smart Prompt Assembly

Each prompt includes the task description, I/O expectations, linked examples, constraints from CLAUDE.md, and formatting rules from LILY\_RULES.md—delivered via MCP or CLI.

---

## 🛡️ 5. Validation, Review & Quality Control

### 🧪 Automated Validation Gates

Each task may define test commands, linting rules, and expected success conditions. These are run in a sandbox or secure subprocess and must pass before a task is considered complete.

### 🧙 Gatekeeper & Debugger Agents

A Gatekeeper Agent ensures the result matches the PRP and passes tests. If not, the LLM Debugger Agent diagnoses what failed and creates suggestions or rework steps.

### 🧼 Prompt Linter

Validates prompts to ensure they contain all required sections (e.g., outputs, I/O format, success criteria). Helps avoid vague or ambiguous instructions.

### 🧑‍⚖️ Human-in-the-Loop Review

Tasks can require human approval even after passing automated checks. Lily shows diffs, highlights test outputs, and allows users to approve, reject, or request a rework.

---

## 🛠️ 6. Developer Experience & Extensibility

### 🧩 Pluggable Template & Rules System

Developers can define new PRP templates or critique rules. `LILY_RULES.md` and `CLAUDE.md` ensure consistency, while templates can enforce domain-specific structure.

### 🔁 Self-Improving "Reprap" Mode

Lily can plan her own improvements. She maintains a `TODOS.md` and creates PRPs and tasks to refine her TUI, CLI, agents, or even add new workflows.

### 🌐 Import / Export Tooling

* Import: Markdown bullets, CSV, or JSON feature lists
* Export: `.zip` of all features, `initial.md`s, and `prp.md`s for archiving or sharing

### ⚙️ Safe Write / Overwrite Guarding

Lily checks for file collisions and warns before overwriting existing specs, logs, or prompts.

### 🔬 Plugin-Ready Architecture

Future support for plugins like:

* Coverage checkers
* Security linters
* Git-integrated validators
