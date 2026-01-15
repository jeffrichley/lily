# Data Model: Init Command

**Date**: 2026-01-14  
**Feature**: Init Command

## Entities

### 1. Project

**Purpose**: Represents a Lily-managed project with metadata and workflow state.

**Attributes**:
- `project_name` (string, required): Name of the project
- `phase` (string, enum, required): Current workflow phase (DISCOVERY, SPEC, ARCH, etc.)
- `created_at` (datetime, required): Project creation timestamp
- `last_updated` (datetime, required): Last modification timestamp
- `version` (string, required): Lily version that created/updated the project

**Storage**: Stored in `.lily/state.json` as JSON. Note: `root_path` is not stored in state.json; it is derived from the filesystem location where the init command is executed.

**Validation Rules**:
- `project_name` must be non-empty string
- `phase` must be valid enum value (init sets to "DISCOVERY")
- `created_at` and `last_updated` must be valid ISO 8601 timestamps
- `version` must match semantic versioning format

**State Transitions**: 
- Initial state: `phase = "DISCOVERY"` (set by init command)
- Future commands will transition phase (out of scope for init)

**Pydantic Model**: `StateModel` in `core/infrastructure/models/state.py`

---

### 2. Artifact

**Purpose**: Represents a file created or managed by Lily.

**Attributes**:
- `file_path` (string, required): Relative path from project root
- `artifact_type` (string, enum, required): Either "user-facing" or "system"
- `last_modified` (datetime, required): Last modification timestamp
- `hash` (string, required): Content hash (SHA-256) for change detection

**Storage**: Stored in `.lily/index.json` as array of artifact objects

**Validation Rules**:
- `file_path` must be relative path (not absolute)
- `artifact_type` must be "user-facing" or "system"
- `hash` must be valid SHA-256 hex string (64 characters)

**Relationships**:
- Many artifacts belong to one Project (tracked in index.json)

**Pydantic Model**: `ArtifactModel` in `core/infrastructure/models/index.py`

---

### 3. Log Entry

**Purpose**: Represents an entry in the audit log.

**Attributes**:
- `timestamp` (datetime, required): ISO 8601 format timestamp
- `command` (string, required): Command name (e.g., "init")
- `action` (string, enum, required): Action type: "created", "skipped", "repaired", "failed"
- `files` (list[string], required): List of file paths affected
- `metadata` (dict, optional): Additional context (project_name, phase, error messages, etc.)

**Storage**: 
- `.lily/log.jsonl` - One JSON object per line (JSONL format)
- `.lily/log.md` - Human-readable markdown format

**Validation Rules**:
- `timestamp` must be valid ISO 8601 datetime
- `command` must be non-empty string
- `action` must be valid enum value
- `files` must be list of strings (can be empty)
- Both formats must be kept synchronized

**Pydantic Model**: `LogEntryModel` in `core/infrastructure/models/log.py`

---

### 4. Config

**Purpose**: Project-level Lily configuration.

**Attributes**:
- `version` (string, required): Config schema version
- `project_name` (string, required): Project name
- `created_at` (datetime, required): Config creation timestamp

**Storage**: Stored in `.lily/config.json` as JSON

**Validation Rules**:
- `version` must match semantic versioning
- `project_name` must be non-empty string
- `created_at` must be valid ISO 8601 timestamp

**Future Extensibility**: Structure supports additional keys without breaking existing code

**Pydantic Model**: `ConfigModel` in `core/infrastructure/models/config.py`

---

## Data Relationships

```
Project (1) ──< (many) Artifact
Project (1) ──< (many) LogEntry
Project (1) ──< (1) Config
```

- One Project has many Artifacts (tracked in index.json)
- One Project has many Log Entries (tracked in log.jsonl/log.md)
- One Project has one Config (stored in config.json)

---

## File Structure

### `.lily/state.json`
```json
{
  "phase": "DISCOVERY",
  "project_name": "myproject",
  "created_at": "2026-01-14T10:30:00Z",
  "last_updated": "2026-01-14T10:30:00Z",
  "version": "0.1.0"
}
```

### `.lily/index.json`
```json
[
  {
    "file_path": "docs/VISION.md",
    "artifact_type": "user-facing",
    "last_modified": "2026-01-14T10:30:00Z",
    "hash": "abc123..."
  },
  {
    "file_path": ".lily/state.json",
    "artifact_type": "system",
    "last_modified": "2026-01-14T10:30:00Z",
    "hash": "def456..."
  }
]
```

### `.lily/log.jsonl`
```jsonl
{"timestamp": "2026-01-14T10:30:00Z", "command": "init", "action": "created", "files": ["docs/VISION.md", ".lily/state.json"], "metadata": {"project_name": "myproject", "phase": "DISCOVERY"}}
```

### `.lily/log.md`
```markdown
[2026-01-14 10:30:00] init
- created: docs/VISION.md
- created: .lily/state.json
```

### `.lily/config.json`
```json
{
  "version": "0.1.0",
  "project_name": "myproject",
  "created_at": "2026-01-14T10:30:00Z"
}
```

---

## Validation Rules Summary

1. **State Validation**: 
   - Phase must be valid enum
   - Timestamps must be ISO 8601
   - All required fields present

2. **Artifact Validation**:
   - File paths must be relative
   - Artifact type must be enum value
   - Hash must be valid SHA-256

3. **Log Entry Validation**:
   - Timestamp must be ISO 8601
   - Action must be valid enum
   - Files list must be array of strings

4. **Config Validation**:
   - Version must be semantic version
   - All required fields present

---

## Error Handling

- **Corrupted JSON**: Attempt repair by recreating with defaults (FR-017)
- **Invalid Schema**: Fail with clear error message indicating which file and what's wrong
- **Missing Required Fields**: Use defaults where possible, fail if critical field missing
- **Hash Calculation Failure**: Log error, continue with empty hash (should not happen in normal operation)

