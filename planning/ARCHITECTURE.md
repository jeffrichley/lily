# 🌸 Lily System Architecture & Project Layout

This document defines the updated architecture and directory structure for the Lily project, serving as the blueprint for a modular, AI-native CLI/TUI system. Lily is designed as an AI-first operating system for thought and action, extending beyond coding to include skills, voice, and research augmentation.

---

## 📁 Directory Structure

```bash
project-root/
├── .lily/                         # Project-specific context and metadata
│   ├── TASK_LIST.md               # Task tracker
│   ├── project.yaml               # Defines persona, modules, and skill overrides
│   ├── tools.yaml                 # Tool registry with local overrides
│   ├── config/                    # Project-level configuration files
│   │   └── memory/                # Memory profile definitions
│   ├── tasks/                     # Task-specific workspaces
│   │   └── <task-name>/
│   │       ├── initial.md         # User input or goal
│   │       ├── result.md          # Final AI-generated output
│   │       ├── notes.md           # Iterative or contextual drafts
│   │       └── logs/              # Log files, errors, tool runs
│   ├── skills/                    # Local project skills
│   ├── flows/                     # Local project flows
│   └── modules/                   # Optional project-local modules
│       └── <module-name>/
│           ├── skills/
│           ├── flows/
│           ├── config/
│           └── memory/
├── planning/                      # Planning and system design
│   ├── PLANNING.md
│   ├── TODOS.md
│   ├── FEATURES.md
│   ├── LILY_RULES.md
│   ├── PERSONAS.yaml
│   └── stories/                   # Task planning docs
├── src/lily/                      # Core application code
│   ├── cli.py                     # CLI entrypoint
│   ├── tui/                       # Terminal UI system
│   ├── core/                      # Execution & engine logic
│   │   ├── executor.py            # Skill and flow execution
│   │   ├── resolver.py            # Resolves skills, flows, tools
│   │   ├── tracker.py             # Task state tracking and history
│   │   └── merger.py              # Config/project resolution
│   └── utils/                     # File walkers, YAML helpers, etc.
└── README.md
```

---

## 🧠 System Components

| Component            | Description                                                        |
| -------------------- | ------------------------------------------------------------------ |
| **Skill Engine**     | Runs a single markdown-defined skill, optionally invoking tools    |
| **Flow Engine**      | Executes `flow.yaml` chains of skills, passing structured output   |
| **Persona Layer**    | Alters prompt tone, voice, memory, and toolset                     |
| **Module Loader**    | Imports modular skills/flows from `~/.lily/modules` or local path  |
| **Context Resolver** | Merges `.lily/project.yaml` hierarchically for current context     |
| **Task Tracker**     | Tracks state (`todo` → `in_progress` → `complete`) and links files |
| **Search Index**     | Indexed CLI/TUI access to skills, flows, features                  |
| **TUI Layer**        | Kanban-style terminal UI with task context pane                    |

---

## 🔧 Internal API Contracts

```python
class SkillExecutor:
    def execute(skill_path: Path, input_text: str, persona: Persona, context: ProjectContext) -> SkillResult

class FlowExecutor:
    def run(flow_yaml: Path, input_text: str, persona: Persona, context: ProjectContext) -> FlowResult

class Resolver:
    def resolve_skill(name: str, context: ProjectContext) -> Path
    def resolve_flow(name: str, context: ProjectContext) -> Path
    def resolve_tool(name: str, context: ProjectContext) -> ToolSpec

class PersonaManager:
    def load(name: str) -> Persona
    def apply(persona: Persona, prompt: str) -> str

class TaskTracker:
    def mark_state(task_name: str, state: str) -> None
    def log_result(task_name: str, result_md: str) -> None
```

---

## ✅ Naming Changes

* ✅ Replaced legacy `prp/` directory with: `.lily/tasks/`
* ✅ Moved `tools/registry.yaml` → `.lily/tools.yaml`
* ✅ Moved `config/memory/` → `.lily/config/memory/`

These changes ensure the `.lily/` directory is the canonical project-local brain, supporting overrideable and modular context.

---

## 📌 Next Steps

* [ ] Scaffold these directories and stub files
* [ ] Implement `SkillExecutor` and `Resolver`
* [ ] Wire CLI commands to execute and track `.lily/tasks/<task>`
