# Research: Init Command Implementation

**Date**: 2026-01-14  
**Feature**: Init Command  
**Purpose**: Resolve technical decisions and clarify implementation choices

## Research Questions

### 1. Pydantic Version Selection

**Question**: What version of Pydantic should be used for JSON/JSONL model validation?

**Research**:
- Pydantic v2 is the current stable version (released 2023)
- Pydantic v1 is deprecated but still maintained for legacy projects
- Pydantic v2 offers better performance, improved validation, and better type hints support
- Python 3.13 is fully supported by Pydantic v2

**Decision**: Use Pydantic v2 (latest stable version, >=2.0.0)

**Rationale**: 
- Modern Python 3.13 project should use modern Pydantic
- Better performance and type safety
- Active development and community support
- Required for JSONL parsing with Pydantic models

**Alternatives Considered**:
- Pydantic v1: Rejected - deprecated, no new features
- Manual JSON validation: Rejected - Pydantic provides type safety and validation

---

### 2. CLI Framework Selection: Typer vs Click

**Question**: Which CLI framework should be used: Typer or Click?

**Research**:
- **Typer**: Built on Click, uses type hints, modern Python-first approach, automatic help generation
- **Click**: Mature, battle-tested, more verbose but explicit, widely used
- Both support command registration, argument parsing, help text
- Typer requires Python 3.6+, Click supports older Python versions
- Typer provides better type safety through type hints

**Decision**: Use Typer

**Rationale**:
- Modern Python 3.13 project benefits from type-hint-based CLI
- Cleaner, more Pythonic API
- Automatic help generation reduces boilerplate
- Built on Click (proven foundation) but with modern interface
- Better integration with Pydantic models (both use type hints)

**Alternatives Considered**:
- Click: Rejected - more verbose, less type-safe, older API style
- argparse: Rejected - too low-level, requires more boilerplate
- Custom CLI: Rejected - reinventing the wheel, maintenance burden

---

### 3. Testing Framework and Structure

**Question**: What pytest version and test structure should be used?

**Research**:
- pytest 7.x is current stable (7.4+ recommended for Python 3.13)
- pytest supports modern Python features and type hints
- Standard test structure: `tests/unit/` and `tests/integration/`
- pytest fixtures for test setup/teardown
- pytest-cov for coverage reporting (required for 80% coverage target)

**Decision**: 
- Use pytest >=7.4.0
- Use pytest-cov for coverage reporting
- Structure: `tests/unit/` for unit tests, `tests/integration/` for integration tests
- Use pytest fixtures for temporary directories and test data

**Rationale**:
- pytest 7.4+ fully supports Python 3.13
- Standard Python testing framework, widely adopted
- Good fixture system for filesystem testing (temporary directories)
- Coverage reporting built-in with pytest-cov
- Matches Python community best practices

**Alternatives Considered**:
- unittest: Rejected - more verbose, less modern features
- nose2: Rejected - less active development, pytest is standard
- Custom test runner: Rejected - unnecessary complexity

---

## Additional Technical Decisions

### 4. JSONL Log Format Structure

**Question**: What exact structure should JSONL log entries have?

**Decision**: Each line is a JSON object with:
```json
{
  "timestamp": "ISO 8601 format (YYYY-MM-DDTHH:MM:SS)",
  "command": "init",
  "action": "created|skipped|repaired|failed",
  "files": ["path/to/file1", "path/to/file2"],
  "metadata": {
    "project_name": "myproject",
    "phase": "DISCOVERY"
  }
}
```

**Rationale**: 
- Structured format enables Pydantic model validation
- Includes all necessary audit information
- Extensible metadata field for future additions
- Matches requirements for dual-format logging

---

### 5. Markdown Log Format Structure

**Question**: What exact format should markdown log entries have?

**Decision**: Human-readable format:
```markdown
[YYYY-MM-DD HH:MM:SS] init
- created: docs/VISION.md
- created: .lily/state.json
- skipped: docs/GOALS.md (already exists)
```

**Rationale**:
- Human-readable for quick inspection
- Simple format that's easy to parse visually
- Synchronized with JSONL format (same information, different presentation)

---

### 6. Default Config.json Structure

**Question**: What default keys should config.json contain?

**Decision**: Minimal initial structure:
```json
{
  "version": "0.1.0",
  "project_name": "myproject",
  "created_at": "ISO 8601 timestamp"
}
```

**Rationale**:
- Minimal as per specification (FR-006 says "default configuration keys")
- Extensible structure for future configuration
- Matches state.json structure for consistency
- No assumptions about future needs (YAGNI principle)

---

## Summary

All technical decisions have been made:
- **Pydantic**: v2 (>=2.0.0)
- **CLI Framework**: Typer
- **Testing**: pytest >=7.4.0 with pytest-cov
- **Log Formats**: JSONL (structured) and Markdown (human-readable) with defined schemas
- **Config**: Minimal structure, extensible

All NEEDS CLARIFICATION items from Technical Context have been resolved.

