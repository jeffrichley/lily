# Quick Start: Implementing Init Command

**Date**: 2026-01-14  
**Feature**: Init Command

## Overview

This guide provides a step-by-step approach to implementing the `init` command, the foundational command that bootstraps a Lily project.

## Prerequisites

1. Python 3.13 installed
2. `uv` package manager installed ([install uv](https://github.com/astral-sh/uv))
3. Install runtime dependencies:
   ```bash
   uv add pydantic typer
   ```
   (uv will automatically determine the best compatible versions)

4. Install development dependencies:
   ```bash
   uv add --dev pytest pytest-cov mypy
   ```
   (uv will automatically determine the best compatible versions)

5. Or install all dependencies at once:
   ```bash
   uv sync
   ```
   (reads from `pyproject.toml` and installs both runtime and dev dependencies)

## Implementation Order

### Step 1: Set Up Project Structure

Create the directory structure following the architecture:

```bash
mkdir -p src/lily/core/{application/commands,domain,infrastructure/models}
mkdir -p src/lily/ui/cli
mkdir -p tests/{unit,integration}
```

### Step 2: Implement Pydantic Models

Start with data models (foundation for everything else):

1. **State Model** (`core/infrastructure/models/state.py`):
   - Define `StateModel` with fields: phase, project_name, created_at, last_updated, version
   - Add validation for phase enum
   - Add JSON serialization/deserialization

2. **Artifact Model** (`core/infrastructure/models/index.py`):
   - Define `ArtifactModel` with fields: file_path, artifact_type, last_modified, hash
   - Add validation for artifact_type enum
   - Define `IndexModel` as list of ArtifactModel

3. **Config Model** (`core/infrastructure/models/config.py`):
   - Define `ConfigModel` with fields: version, project_name, created_at
   - Minimal structure, extensible

4. **Log Entry Model** (`core/infrastructure/models/log.py`):
   - Define `LogEntryModel` with fields: timestamp, command, action, files, metadata
   - Add validation for action enum
   - Add JSONL serialization method

### Step 3: Implement Storage Layer

Create filesystem operations (`core/infrastructure/storage.py`):

1. **Basic Operations**:
   - `create_directory()` - Create directory if not exists
   - `create_file()` - Create file with content (skip if exists)
   - `file_exists()` - Check file existence
   - `check_permissions()` - Validate write permissions

2. **JSON Operations**:
   - `read_json()` - Read JSON with corruption repair
   - `write_json()` - Atomic JSON write
   - `calculate_hash()` - SHA-256 hash calculation

3. **Log Operations**:
   - `append_jsonl()` - Append to JSONL file
   - `append_markdown_log()` - Append to markdown log
   - `sync_logs()` - Keep both formats synchronized

### Step 4: Implement Domain Entities

Create domain models (`core/domain/`):

1. **Project Entity** (`domain/project.py`):
   - Represents a Lily project
   - Loads/saves from state.json
   - Handles phase transitions (future)

2. **Artifact Entity** (`domain/artifact.py`):
   - Represents a file artifact
   - Calculates and stores hash
   - Tracks modification time

3. **State Entity** (`domain/state.py`):
   - Manages workflow state
   - Validates state transitions
   - Handles corruption repair

### Step 5: Implement Command Pattern

Create command infrastructure:

1. **Base Command** (`core/application/commands/base.py`):
   - Abstract `Command` class
   - `execute()` and `validate()` methods
   - `CommandResult` protocol

2. **Init Command** (`core/application/commands/init.py`):
   - Implement `InitCommand` class
   - Implement `validate()` - check permissions, validate paths
   - Implement `execute()` - orchestrate file creation
   - Handle idempotency (skip existing files)
   - Handle corruption repair
   - Return `InitResult`

### Step 6: Implement Artifact Templates

Create template generators for markdown files:

1. **Template Method Pattern**:
   - Base `ArtifactGenerator` class
   - Concrete generators: `VisionGenerator`, `GoalsGenerator`, etc.
   - Each generator creates file with proper structure

2. **Template Content**:
   - Section headers
   - Guidance comments
   - Empty bullet lists
   - Consistent formatting

### Step 7: Implement CLI Interface

Create CLI entry point (`ui/cli/main.py`):

1. **Typer Setup**:
   - Register `init` command
   - Parse project name argument
   - Handle command execution

2. **Result Rendering**:
   - Format success output (list created files)
   - Format error output (clear error messages)
   - Exit codes (0 for success, 1 for error)

### Step 8: Implement Logging

Create dual-format logger:

1. **Logger Implementation**:
   - Write to both `.lily/log.md` and `.lily/log.jsonl`
   - Keep formats synchronized
   - Handle log entry creation

2. **Log Entry Creation**:
   - Create entries for: file creation, skipping, repair, errors
   - Include metadata (project_name, phase, etc.)

## Testing Strategy

### Unit Tests

1. **Model Tests** (`tests/unit/test_models.py`):
   - Test Pydantic model validation
   - Test serialization/deserialization
   - Test enum validation

2. **Storage Tests** (`tests/unit/test_storage.py`):
   - Test file operations (create, read, write)
   - Test permission checking
   - Test hash calculation
   - Test corruption repair

3. **Command Tests** (`tests/unit/test_init_command.py`):
   - Test command validation
   - Test idempotency
   - Test error handling
   - Mock storage layer

### Integration Tests

1. **End-to-End Tests** (`tests/integration/test_init_integration.py`):
   - Test full init flow in temporary directory
   - Test file creation
   - Test state persistence
   - Test log synchronization
   - Test re-running init

### Running Tests

Run tests using `uv`:

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src/lily --cov-report=html

# Run specific test file
uv run pytest tests/unit/test_models.py

# Run integration tests only
uv run pytest tests/integration/
```

### Type Checking

Run type checking with mypy:

```bash
# Type check the entire codebase
uv run mypy src/lily

# Type check with strict mode
uv run mypy --strict src/lily

# Type check specific module
uv run mypy src/lily/core/infrastructure/models
```

## Key Implementation Notes

### Idempotency

- Always check `file_exists()` before creating
- Skip existing files (don't overwrite)
- Only create missing files
- Update logs even when skipping files

### Error Handling

- Validate permissions BEFORE attempting file operations
- Fail fast with clear error messages
- Repair corrupted state.json automatically
- Log all errors to both log formats

### Determinism

- Use fixed timestamps for testing (or mock datetime)
- Use deterministic file content (templates)
- No random values in file creation
- Same inputs → same outputs

### Performance

- Batch file operations where possible
- Validate permissions once before bulk operations
- Use atomic writes to prevent partial state
- Target: <5 seconds for full initialization

## Validation Checklist

Before considering implementation complete:

- [ ] All Pydantic models validate correctly
- [ ] Storage layer handles all file operations
- [ ] Init command creates all required files
- [ ] Idempotency works (re-run doesn't break)
- [ ] Corruption repair works
- [ ] Permission errors handled correctly
- [ ] Logs are synchronized (markdown + JSONL)
- [ ] Console output is clear and informative
- [ ] All tests pass (unit + integration)
- [ ] Test coverage >= 80% for critical paths
- [ ] Performance meets <5 second target

## Next Steps

After init command is complete:

1. Implement `status` command (reads state.json and index.json)
2. Implement command bus infrastructure
3. Add TUI support (reuse same command)

## Resources

- **Specification**: [spec.md](./spec.md)
- **Data Model**: [data-model.md](./data-model.md)
- **Contracts**: [contracts/command-interface.md](./contracts/command-interface.md)
- **Research**: [research.md](./research.md)
- **Architecture**: `ideas/core/two_layer.md` and `ideas/core/architecture.md`

