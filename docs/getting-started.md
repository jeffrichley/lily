# Getting Started with Lily

Lily is a spec-driven orchestration framework that helps you manage your project lifecycle from initial ideas through implementation.

## Installation

Lily is a Python project. Install dependencies using `uv`:

```bash
# Install all dependencies
uv sync

# Or install just runtime dependencies
uv sync --no-dev
```

## Quick Start

### 1. Initialize a Project

Start by initializing a new Lily project:

```bash
# Initialize with a project name
lily init my-project

# Or use current directory name
lily init --here
```

This creates:
- `.lily/` directory with system artifacts
- `docs/` directory with documentation templates
- Initial project state set to "DISCOVERY" phase

### 2. Check Project Status

View your project status:

```bash
lily status
```

This shows:
- Current project phase
- Project metadata
- List of artifacts (documentation and system files)

### 3. Fill in Documentation

Edit the files in `docs/` to define your project:

- **VISION.md**: What is this project? Why does it exist?
- **GOALS.md**: What are the primary objectives?
- **NON_GOALS.md**: What is explicitly out of scope?
- **CONSTRAINTS.md**: Technical, business, or time constraints
- **ASSUMPTIONS.md**: Assumptions about technology, users, context
- **OPEN_QUESTIONS.md**: Questions that need answers

### 4. Generate Specifications

Use Lily's specification workflow to create feature specs:

1. Define features in natural language
2. Lily generates structured specifications
3. Create implementation plans
4. Break down into actionable tasks
5. Hand off to AI coding agents

## Workflow Phases

Lily projects progress through phases:

1. **DISCOVERY**: Initial project setup, defining vision and goals
2. **SPEC**: Creating feature specifications
3. **ARCH**: Architecture design and planning
4. **IMPLEMENT**: Implementation tasks
5. **POLISH**: Testing, documentation, refinement

## Next Steps

- Read the [Architecture documentation](architecture.md) to understand Lily's design
- Explore [Commands](commands/index.md) to see what Lily can do
- Check out [Specifications](specs/) for examples of feature specs
- Review [Ideas](ideas/) for design concepts and UX patterns

## Getting Help

- Browse the documentation sections
- Check command help: `lily <command> --help`
- Review specifications in `specs/` directory

