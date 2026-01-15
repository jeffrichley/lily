# Lily Commands

Lily provides a set of CLI commands to help you manage your project lifecycle from specification to implementation.

## Available Commands

### `lily init`

Initialize a new Lily project in the current directory.

**Usage:**
```bash
lily init <PROJECT_NAME>
# or
lily init --here
```

**Options:**
- `PROJECT_NAME`: Name of the project (required unless `--here` is specified)
- `--here`: Use current directory name as project name

**What it does:**
- Creates `.lily/` directory with system artifacts (state.json, index.json, config.json, logs)
- Creates `docs/` directory with user-facing documentation templates:
  - VISION.md
  - GOALS.md
  - NON_GOALS.md
  - CONSTRAINTS.md
  - ASSUMPTIONS.md
  - OPEN_QUESTIONS.md
- Sets initial project phase to "DISCOVERY"
- Creates audit logs in both Markdown and JSONL formats

**Example:**
```bash
# Initialize with project name
lily init my-awesome-project

# Initialize using current directory name
lily init --here
```

**See also:**
- [Init Command Specification](../specs/001-init-command/spec.md)
- [Init Command Quickstart](../specs/001-init-command/quickstart.md)

---

### `lily status`

Display the current project status, including phase, artifacts, and project metadata.

**Usage:**
```bash
lily status
```

**What it shows:**
- Current project phase (DISCOVERY, SPEC, ARCH, etc.)
- Project name and creation date
- List of user-facing artifacts (documentation files)
- List of system artifacts (state, index, logs, config)
- Project version

**Example output:**
```
Project: my-awesome-project
Phase: DISCOVERY
Created: 2026-01-15

User-facing artifacts:
  ✓ docs/VISION.md
  ✓ docs/GOALS.md
  ...

System artifacts:
  ✓ .lily/state.json
  ✓ .lily/index.json
  ...
```

**See also:**
- [Status Command Specification](../specs/001-init-command/spec.md)

---

## Command Architecture

Lily commands follow a consistent architecture:

1. **Command Interface**: CLI entry point using Typer
2. **Command Class**: Business logic implementation
3. **Storage Layer**: File system operations
4. **Result Object**: Structured command results

All commands:
- Validate prerequisites before execution
- Return structured results with success/failure status
- Provide clear error messages
- Log operations to audit logs

## Future Commands

Planned commands include:
- `lily spec` - Generate feature specifications
- `lily plan` - Create implementation plans
- `lily arch` - Generate architecture documentation
- `lily tasks` - Break down plans into actionable tasks

