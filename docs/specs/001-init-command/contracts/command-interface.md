# Command Interface Contract: Init Command

**Date**: 2026-01-14  
**Feature**: Init Command

## CLI Interface

### Command Signature

```bash
lily init [PROJECT_NAME] [--here]
```

**Arguments**:
- `PROJECT_NAME` (required unless `--here` is specified): Name of the project

**Options**:
- `--here`: Use current directory name (basename of current working directory) as project name. If `--here` is specified, PROJECT_NAME argument is not required and will be ignored if provided.

**Behavior**:
- If `--here` is specified: Use current directory name as project name
- If `--here` is NOT specified: PROJECT_NAME argument is REQUIRED (command fails if missing)

**Exit Codes**:
- `0`: Success - project initialized
- `1`: Error - permission denied, invalid path, or other failure

---

## Command Execution Flow

### Input
- Project name (required string unless `--here` flag is specified)
- `--here` flag (optional boolean): If specified, use current directory name as project name
- Current working directory (Path)

### Processing
1. Validate project name: If `--here` is not specified, PROJECT_NAME is required (fail if missing). If `--here` is specified, derive project name from current directory basename
2. Validate current directory is writable (FR-012, FR-018)
3. Check for existing `.lily/` directory
4. Create directory structure (FR-001, FR-007)
5. Create system artifacts (FR-003, FR-004, FR-005, FR-006)
6. Create user-facing artifacts (FR-002, FR-008, FR-009)
7. Update index.json with all created artifacts
8. Write log entries to both log.md and log.jsonl (FR-005)

### Output
- **Success**: Console output listing all created files (FR-013)
- **Failure**: Clear error message with specific failure reason (FR-018)

---

## Command Result Structure

### Success Result

```python
class InitResult:
    success: bool = True
    project_name: str
    files_created: List[str]
    files_skipped: List[str]  # If re-running on existing project
    state_file: Path  # Path to .lily/state.json
    message: str  # Human-readable summary
```

**Example Console Output**:
```
✓ Project 'myproject' initialized successfully

Created files:
  docs/VISION.md
  docs/GOALS.md
  docs/NON_GOALS.md
  docs/CONSTRAINTS.md
  docs/ASSUMPTIONS.md
  docs/OPEN_QUESTIONS.md
  docs/README.md
  .lily/state.json
  .lily/index.json
  .lily/log.md
  .lily/log.jsonl
  .lily/config.json

Project is ready for the next phase (DISCOVERY).
```

### Error Result

```python
class InitError:
    success: bool = False
    error_type: str  # "permission_denied", "invalid_path", "corrupted_state", etc.
    message: str  # Human-readable error message
    failed_paths: List[str]  # Specific paths that failed (for permission errors)
```

**Example Console Output**:
```
✗ Failed to initialize project: Permission denied

Cannot write to the following paths:
  .lily/state.json
  docs/VISION.md

Please check write permissions and try again.
```

---

## Command Pattern Implementation

### Base Command Interface

```python
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Protocol

class CommandResult(Protocol):
    success: bool
    message: str

class Command(ABC):
    @abstractmethod
    def execute(self, *args, **kwargs) -> CommandResult:
        """Execute the command and return result."""
        pass
    
    @abstractmethod
    def validate(self, *args, **kwargs) -> bool:
        """Validate prerequisites before execution."""
        pass
```

### InitCommand Implementation

```python
class InitCommand(Command):
    def __init__(self, storage: Storage, logger: Logger):
        self.storage = storage
        self.logger = logger
    
    def validate(self, project_name: str, root_path: Path) -> bool:
        """Validate that init can proceed."""
        # Check write permissions
        # Check for existing .lily/ (handle corruption if needed)
        # Validate project name
        pass
    
    def execute(self, project_name: str, root_path: Path) -> InitResult:
        """Execute init command."""
        # 1. Validate prerequisites
        # 2. Create directory structure
        # 3. Create all artifacts
        # 4. Update index
        # 5. Write logs
        # 6. Return result
        pass
```

---

## Storage Interface Contract

### Storage Operations

```python
class Storage(Protocol):
    def create_directory(self, path: Path) -> None:
        """Create directory if it doesn't exist."""
        pass
    
    def create_file(self, path: Path, content: str) -> None:
        """Create file with content. Skip if exists (idempotent)."""
        pass
    
    def file_exists(self, path: Path) -> bool:
        """Check if file exists."""
        pass
    
    def read_json(self, path: Path) -> dict:
        """Read JSON file. Attempt repair if corrupted."""
        pass
    
    def write_json(self, path: Path, data: dict) -> None:
        """Write JSON file atomically."""
        pass
    
    def append_jsonl(self, path: Path, entry: dict) -> None:
        """Append JSONL entry to file."""
        pass
    
    def append_markdown_log(self, path: Path, entry: str) -> None:
        """Append markdown log entry."""
        pass
    
    def calculate_hash(self, path: Path) -> str:
        """Calculate SHA-256 hash of file content."""
        pass
    
    def check_permissions(self, path: Path) -> bool:
        """Check if path is writable."""
        pass
```

---

## Logger Interface Contract

### Dual-Format Logging

```python
class Logger(Protocol):
    def log_init(
        self,
        action: str,  # "created", "skipped", "repaired"
        files: List[str],
        metadata: dict
    ) -> None:
        """Log init command execution to both log.md and log.jsonl."""
        pass
```

**Synchronization Requirement**: Both log formats must contain the same information, written atomically.

---

## Error Handling Contract

### Error Types

1. **PermissionError**: Write permission denied
   - **Behavior**: Fail immediately with clear message (FR-018)
   - **Message**: List all failed paths

2. **CorruptedStateError**: `.lily/state.json` is corrupted
   - **Behavior**: Repair by recreating with defaults, log event (FR-017)
   - **Message**: Inform user of repair action

3. **InvalidPathError**: Project name contains invalid characters
   - **Behavior**: Fail with validation error
   - **Message**: Explain valid character requirements

4. **DiskSpaceError**: Insufficient disk space
   - **Behavior**: Fail with clear error
   - **Message**: Indicate space requirement

---

## Idempotency Contract

### Re-running Init

When `lily init` is run on an already-initialized project:

1. **Existing Files**: Skip (do not overwrite) - FR-016
2. **Missing Files**: Create only missing files
3. **Corrupted Files**: Repair corrupted system files (state.json, index.json, config.json)
4. **Log Entries**: Append new log entry documenting the re-run
5. **Result**: Success with list of files created vs. skipped

**Example**:
```
✓ Project 'myproject' re-initialized

Created files:
  docs/ASSUMPTIONS.md  (was missing)

Skipped files (already exist):
  docs/VISION.md
  .lily/state.json
  ... (other existing files)
```

---

## Validation Contract

### Pre-execution Validation

1. **Path Validation**: 
   - Current directory exists and is accessible
   - Project name is valid for filesystem paths

2. **Permission Validation**:
   - Check write permissions before attempting file creation
   - Fail fast if permissions insufficient

3. **State Validation**:
   - If `.lily/state.json` exists, validate schema
   - If corrupted, repair before proceeding

### Post-execution Validation

1. **File Creation Verification**:
   - Verify all required files exist
   - Verify file contents match expected structure

2. **State Consistency**:
   - Verify state.json is valid
   - Verify index.json contains all created artifacts
   - Verify logs are synchronized

---

## Performance Contract

### Timing Requirements

- **SC-001**: Complete initialization in under 5 seconds
- **Measurement**: From command invocation to result return

### Optimization Strategies

- Batch file operations where possible
- Use atomic file writes to prevent partial state
- Validate permissions once before bulk operations
- Calculate hashes only for files that need indexing

