# Implementation Plan: Init Command

**Branch**: `001-init-command` | **Date**: 2026-01-14 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-init-command/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

The `init` command is the foundational command that bootstraps a new Lily project by creating the required directory structure, system artifacts (state.json, index.json, log files, config.json), and user-facing documentation templates. This command establishes the "command pipeline spine" that all future Lily commands depend on. The implementation will use the Command Pattern for the command itself, filesystem operations for artifact creation, and Pydantic models for structured data validation. The command must be idempotent, deterministic, and handle edge cases like existing files, corrupted state, and permission errors.

## Technical Context

**Language/Version**: Python 3.13 (as specified in pyproject.toml)  
**Primary Dependencies**: 
- Pydantic >=2.0.0 (for JSON/JSONL model validation)
- Typer (for CLI framework)
- pytest >=7.4.0 with pytest-cov (for testing and coverage)
- Standard library (pathlib, json, datetime) for filesystem and JSON operations
**Storage**: Filesystem-based (no database required for init command)  
**Testing**: pytest >=7.4.0 with pytest-cov, test structure: `tests/unit/` and `tests/integration/`
**Target Platform**: Cross-platform (Linux, macOS, Windows) - command-line tool  
**Project Type**: Single Python package (CLI application)  
**Performance Goals**: Init command must complete in under 5 seconds (per SC-001)  
**Constraints**: 
- Must be deterministic (same inputs produce same outputs)
- Must be idempotent (safe to run multiple times)
- Must not invoke LLMs or generate code
- Must not require interactive input beyond project name
- All file operations must be atomic where possible
**Scale/Scope**: Single project initialization per execution (not batch processing)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Phase 0 ✅ PASSED

**Code Quality:**
- [x] All code will meet production-quality standards (readable, maintainable, error handling)
- [x] Code will be properly structured with clear separation of concerns (following architecture: core/application, core/domain, core/infrastructure)
- [x] Appropriate documentation will be included for complex behavior (Pydantic models, command execution flow)

**Minimal Code Generation:**
- [x] Implementation plan includes ONLY code required by specification (init command, file creation, state management)
- [x] No speculative features or "nice-to-have" items included
- [x] No premature abstractions or "future-proofing" code planned (only what's needed for init)
- [x] All planned code traces directly to specification requirements (FR-001 through FR-018)

**Gang of Four Patterns:**
- [x] Design identifies which GoF patterns will be used:
  - **Command Pattern**: InitCommand class for the command execution (required by architecture)
  - **Template Method Pattern**: For consistent artifact generation (markdown templates)
  - **Strategy Pattern**: Not needed for init (no swappable algorithms)
  - **State Pattern**: Not needed for init (state is just data, not behavior)
  - **Observer Pattern**: Not needed for init (no event subscriptions required)
  - **Facade Pattern**: CommandBus/App facade for CLI to call (required by architecture)
  - **Abstract Factory**: Not needed for init (no adapter families)
- [x] Pattern selection is justified: Command Pattern required by architecture for all commands; Template Method for consistent file generation
- [x] Patterns solve concrete problems: Command Pattern enables CLI/TUI reuse; Template Method ensures deterministic artifact structure

**Testability:**
- [x] Code structure enables unit and integration testing (command class, storage layer, models all testable)
- [x] Critical paths have corresponding test plans (file creation, idempotency, error handling, corruption repair)
- [x] Test coverage targets are defined: Minimum 80% for critical paths (per constitution)

### Post-Phase 1 ✅ PASSED

**Re-evaluation after design completion:**

- [x] **Code Quality**: Design maintains production-quality standards with clear separation (application/domain/infrastructure layers)
- [x] **Minimal Code Generation**: Design includes only required components (models, storage, command, CLI) - no speculative code
- [x] **GoF Patterns**: Command Pattern and Template Method Pattern properly applied to solve concrete problems
- [x] **Testability**: Design enables comprehensive testing with unit tests (models, storage, command) and integration tests (end-to-end init flow)

**No violations detected. Design is compliant with constitution.**

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/
└── lily/
    ├── __init__.py
    ├── app.py                    # CLI entry point (future: TUI entry)
    └── core/
        ├── __init__.py
        ├── application/         # Use cases (commands)
        │   ├── __init__.py
        │   └── commands/
        │       ├── __init__.py
        │       ├── base.py        # Base Command class
        │       └── init.py       # InitCommand implementation
        ├── domain/               # Entities + rules
        │   ├── __init__.py
        │   ├── project.py         # Project entity
        │   ├── artifact.py        # Artifact entity
        │   └── state.py           # State entity
        └── infrastructure/        # Filesystem, storage
            ├── __init__.py
            ├── storage.py        # Filesystem operations
            └── models/            # Pydantic models
                ├── __init__.py
                ├── state.py       # State JSON model
                ├── index.py       # Index JSON model
                ├── config.py      # Config JSON model
                └── log.py         # Log entry JSONL model
    └── ui/
        └── cli/
            ├── __init__.py
            └── main.py            # CLI command registration (Typer/Click)

tests/
├── unit/
│   ├── test_init_command.py
│   ├── test_storage.py
│   └── test_models.py
└── integration/
    └── test_init_integration.py
```

**Structure Decision**: Following the two-layer architecture from `ideas/core/two_layer.md`, the code is organized into:
- `core/application/commands/` - Command Pattern implementations (InitCommand)
- `core/domain/` - Domain entities (Project, Artifact, State)
- `core/infrastructure/` - Filesystem operations and Pydantic models
- `ui/cli/` - CLI interface (will be extended to TUI later without changing core)

## Phase Completion Status

### Phase 0: Research ✅ Complete

**Output**: [research.md](./research.md)

**Resolved**:
- Pydantic version: v2 (>=2.0.0)
- CLI framework: Typer
- Testing framework: pytest >=7.4.0 with pytest-cov
- Log formats: JSONL and Markdown structures defined
- Config structure: Minimal extensible structure

### Phase 1: Design & Contracts ✅ Complete

**Outputs**:
- [data-model.md](./data-model.md) - Entity definitions, relationships, validation rules
- [contracts/command-interface.md](./contracts/command-interface.md) - CLI interface, command pattern, storage contracts
- [quickstart.md](./quickstart.md) - Implementation guide and testing strategy

**Design Artifacts**:
- Data models defined with Pydantic schemas
- Command interface contract established
- Storage layer interface defined
- Logging dual-format structure specified
- Error handling contracts defined

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
