# Lily Architecture

## Overview

Lily is a spec-driven orchestration framework designed to generate structured specifications, plans, and context artifacts for handoff to external AI coding agents. The architecture emphasizes portability, clarity, and high-quality AI handoffs.

## Core Principles

1. **Spec-Driven**: All features start with specifications that define what, not how
2. **AI Agent Handoffs**: Lily generates artifacts for external AI agents, not code itself
3. **Portability**: Specifications and plans are technology-agnostic
4. **Clarity**: Clear separation between specification, planning, and implementation

## Architecture Layers

### Application Layer

The application layer contains command implementations that orchestrate domain logic.

**Location**: `src/lily/core/application/commands/`

**Commands**:
- `InitCommand`: Initializes new Lily projects
- `StatusCommand`: Displays project status and artifacts

**Pattern**: Command pattern with structured results

### Domain Layer

The domain layer contains business logic and domain models (currently minimal, focused on orchestration).

**Location**: `src/lily/core/domain/`

### Infrastructure Layer

The infrastructure layer provides concrete implementations for storage, logging, and state management.

**Location**: `src/lily/core/infrastructure/`

**Components**:
- `Storage`: File system operations
- `Logger`: Dual-format logging (Markdown + JSONL)
- Models: `Config`, `Index`, `Log`, `State`

### UI Layer

The UI layer provides the CLI interface using Typer.

**Location**: `src/lily/ui/cli/`

**Entry Point**: `main.py` - Defines CLI commands and routes to command implementations

## Project Structure

```
lily/
├── .lily/              # System artifacts (state, index, logs, config)
├── docs/               # User-facing documentation
├── specs/              # Feature specifications
├── ideas/              # Design ideas and architecture notes
├── src/lily/           # Source code
│   ├── core/
│   │   ├── application/commands/  # Command implementations
│   │   ├── domain/                # Domain logic
│   │   └── infrastructure/        # Storage, logging, models
│   └── ui/cli/                    # CLI interface
└── tests/              # Test suites
```

## State Management

Lily maintains project state in `.lily/state.json`:

- **Phase**: Current workflow phase (DISCOVERY, SPEC, ARCH, etc.)
- **Project Metadata**: Name, version, timestamps
- **Artifact Tracking**: Index of all project artifacts

## Artifact Types

### User-Facing Artifacts

Located in `docs/` directory:
- VISION.md
- GOALS.md
- NON_GOALS.md
- CONSTRAINTS.md
- ASSUMPTIONS.md
- OPEN_QUESTIONS.md

### System Artifacts

Located in `.lily/` directory:
- `state.json`: Project state and phase
- `index.json`: Artifact metadata
- `config.json`: Project configuration
- `log.md`: Human-readable audit log
- `log.jsonl`: Machine-readable audit log

## Command Flow

1. **CLI Entry**: User invokes command via `lily <command>`
2. **Validation**: Command validates prerequisites
3. **Execution**: Command executes business logic
4. **Storage**: Results written to file system
5. **Logging**: Operations logged to audit logs
6. **Result**: Structured result returned to CLI

## Extension Points

### Adding New Commands

1. Create command class in `core/application/commands/`
2. Implement `Command` interface (execute, validate)
3. Add CLI entry point in `ui/cli/main.py`
4. Create specification in `specs/`

### Adding New Artifacts

1. Define artifact structure
2. Add to `InitCommand` if user-facing
3. Update `Index` model to track
4. Document in specification

## Design Decisions

### Why Two-Layer Architecture?

Lily uses a simplified two-layer architecture (Application + Infrastructure) rather than traditional DDD layers:

- **Simplicity**: Orchestration framework doesn't need complex domain models
- **Clarity**: Clear separation between commands and storage
- **Portability**: Specifications are independent of implementation

### Why Dual-Format Logging?

- **Markdown**: Human-readable for developers
- **JSONL**: Machine-readable for automation and analysis

### Why Command Pattern?

- **Consistency**: All commands follow same interface
- **Testability**: Easy to test command logic
- **Extensibility**: Easy to add new commands

## Future Architecture Considerations

As Lily grows, consider:

- **Plugin System**: For extending command capabilities
- **TUI Layer**: Interactive terminal interface
- **Specification Templates**: Customizable spec templates
- **Integration Points**: Hooks for external tools

## Related Documentation

- [Architecture Ideas](../ideas/core/architecture.md)
- [Two-Layer Architecture](../ideas/core/two_layer.md)
- [UX Design](../ideas/core/ux.md)

