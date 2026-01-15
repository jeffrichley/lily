# Feature Specification: Init Command

**Feature Branch**: `001-init-command`  
**Created**: 2026-01-14  
**Status**: Draft  
**Input**: User description: "we will work on @ideas/commands/command_init.md"

## Clarifications

### Session 2026-01-14

- Q: When `lily init` is run, how should the project name be determined? → A: Project name is required unless `--here` flag is specified. If `--here` is provided, use current directory name (basename of current working directory) as project name. If `--here` is not specified, PROJECT_NAME argument is required.
- Q: When `lily init` encounters existing files, what should the system do? → A: Skip existing files, only create missing ones
- Q: When `lily init` encounters a corrupted `.lily/state.json` file, what should happen? → A: Attempt repair by recreating with defaults and logging the corruption issue in the audit log
- Q: What are the minimum required fields/structure for each JSON file created by init? → A: Minimal schemas: state.json needs phase, project_name, created_at, last_updated, version; index.json needs array structure for artifacts; config.json needs default configuration keys
- Q: When `lily init` fails due to insufficient write permissions, what should the system do? → A: Fail immediately with clear error message indicating permission issue and which paths failed
- Q: What format should log entries follow? → A: Both `.lily/log.md` (human-readable markdown) and `.lily/log.jsonl` (JSONL format for programmatic use with Pydantic models)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Initialize New Project (Priority: P1)

A user wants to bootstrap a new project using Lily's orchestration framework. They run the `init` command to establish the project structure, workspace directories, and initial state files that all subsequent Lily commands will depend on.

**Why this priority**: This is the foundational command that establishes the entire project structure and state management system. Without it, no other Lily commands can function. It's the entry point for all Lily workflows.

**Independent Test**: Can be fully tested by running `lily init <project_name>` in an empty or new directory and verifying all required files and directories are created with correct structure and content. This delivers immediate value by establishing a working project foundation.

**Acceptance Scenarios**:

1. **Given** a user is in a directory where they want to initialize a Lily project, **When** they run `lily init myproject`, **Then** all required user-facing artifacts (VISION.md, GOALS.md, NON_GOALS.md, CONSTRAINTS.md, ASSUMPTIONS.md, OPEN_QUESTIONS.md) are created in a `docs/` directory with proper structure and guidance templates
2. **Given** a user runs `lily init myproject`, **When** the command completes successfully, **Then** all system artifacts (`.lily/state.json`, `.lily/index.json`, `.lily/log.md`, `.lily/log.jsonl`, `.lily/config.json`) are created with correct initial values
3. **Given** a user runs `lily init myproject`, **When** the command completes, **Then** the required directory structure (`.lily/runs/`, `.lily/tasks/`) exists with placeholder files
4. **Given** a user runs `lily init myproject` twice in the same directory, **When** the second execution completes, **Then** no files are corrupted, state remains consistent, and the operation completes without errors (idempotent behavior)
5. **Given** a user runs `lily init myproject`, **When** the command completes, **Then** the console displays a clear summary listing all files created and the project is ready for the next phase

---

### User Story 2 - Re-initialize Existing Project (Priority: P2)

A user wants to re-run the `init` command on an already-initialized project, either to repair corrupted files or to ensure all required artifacts exist.

**Why this priority**: While not the primary use case, idempotent behavior is critical for reliability and user confidence. Users should be able to safely re-run init without breaking their project.

**Independent Test**: Can be fully tested by running `lily init myproject` (or `lily init --here`) on a directory that already contains some or all of the expected artifacts, and verifying that existing files are preserved or updated appropriately without corruption.

**Acceptance Scenarios**:

1. **Given** a project directory already contains `.lily/state.json` with phase "DISCOVERY", **When** the user runs `lily init myproject` (or `lily init --here`), **Then** the existing state is preserved and no duplicate or conflicting files are created
2. **Given** a project directory is missing some required artifacts (e.g., `docs/ASSUMPTIONS.md`), **When** the user runs `lily init myproject` (or `lily init --here`), **Then** only the missing artifacts are created, existing files are skipped and left unchanged
3. **Given** a project directory has a corrupted `.lily/state.json`, **When** the user runs `lily init myproject` (or `lily init --here`), **Then** the system recreates the state file with default values and logs the corruption event in both `.lily/log.md` and `.lily/log.jsonl` for audit trail
4. **Given** a user runs `lily init myproject` (or `lily init --here`) in a directory where they lack write permissions, **When** the command attempts to create files, **Then** the system fails immediately with a clear error message indicating the permission issue and which specific paths failed

---

### Edge Cases

- What happens when the user doesn't have write permissions in the current directory? → System fails immediately with clear error message indicating permission issue and which paths failed
- How does the system handle existing files that conflict with Lily's structure (e.g., existing `docs/` directory with different content)? → System skips existing files and only creates missing ones
- What happens when disk space is insufficient during file creation? → System fails with clear error message indicating insufficient disk space. Partial file creation is acceptable (some files may be created before failure, but state.json should not be created if critical files fail)
- How does the system behave if `.lily/` directory already exists but is not a valid Lily workspace? → System attempts repair by recreating corrupted files with defaults and logs the issue
- What happens when the project name contains invalid characters for filesystem paths? → System validates project name before proceeding and fails with clear error message indicating invalid characters. Valid characters: alphanumeric, hyphens, underscores. Invalid: path separators (/ or \), null bytes, control characters
- How does the system handle running `init` in a directory that is already a git repository vs. a new directory? → System behavior is identical regardless of git repository presence. Init does not interact with git (git is out of scope for init command)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST create a `.lily/` directory structure containing all required system artifacts (state.json, index.json, log.md, log.jsonl, config.json, runs/, tasks/)
- **FR-002**: System MUST create a `docs/` directory containing all required user-facing artifacts (VISION.md, GOALS.md, NON_GOALS.md, CONSTRAINTS.md, ASSUMPTIONS.md, OPEN_QUESTIONS.md)
- **FR-003**: System MUST create `.lily/state.json` with initial phase set to "DISCOVERY" and project metadata. Minimum required fields: `phase` (string, value "DISCOVERY"), `project_name` (string), `created_at` (ISO 8601 datetime), `last_updated` (ISO 8601 datetime), `version` (string). Note: `root_path` is not stored in state.json; it is derived from the filesystem location where init is executed.
- **FR-004**: System MUST create `.lily/index.json` to track artifact metadata. Structure must be an array where each entry contains: file path (string), artifact type (string: "user-facing" or "system"), last modified (ISO 8601 datetime), hash (string)
- **FR-005**: System MUST create both `.lily/log.md` (human-readable markdown format) and `.lily/log.jsonl` (JSONL format for programmatic use) as append-only audit logs. Both logs MUST contain an initial entry documenting the init command execution, with entries synchronized between both formats
- **FR-006**: System MUST create `.lily/config.json` with default project-level configuration values. Structure must contain: `version` (string, semantic version), `project_name` (string), `created_at` (ISO 8601 datetime). See data-model.md for complete schema definition. Structure must support extensibility for future keys.
- **FR-007**: System MUST create directory structure for `.lily/runs/` and `.lily/tasks/` with placeholder files to ensure directories exist
- **FR-008**: System MUST create all user-facing markdown files with proper structure including section headers, guidance comments, and empty bullet lists ready for content
- **FR-009**: System MUST create `docs/README.md` explaining the purpose of the docs folder and how Lily uses it
- **FR-010**: System MUST ensure all file creation is deterministic (same inputs produce same outputs - file content is identical across runs with same project name)
- **FR-011**: System MUST support idempotent execution (running init multiple times does not corrupt state or create duplicate files - safe to re-run)
- **FR-016**: System MUST skip existing files when re-running init, only creating files that are missing (preserves user work while ensuring completeness)
- **FR-017**: System MUST attempt to repair corrupted `.lily/state.json` files by recreating them with default values and MUST log the corruption event in both `.lily/log.md` and `.lily/log.jsonl` for audit trail
- **FR-018**: System MUST fail immediately with a clear error message when write permissions are insufficient, indicating the permission issue and which specific paths failed
- **FR-012**: System MUST validate that required paths can be created before proceeding with file creation
- **FR-013**: System MUST provide clear console output listing all files created during initialization
- **FR-014**: System MUST NOT generate any code, invoke any LLM, ask architecture questions, or assume specific programming languages or frameworks during initialization
- **FR-015**: System MUST ensure the created state and structure are compatible with future commands (status, spec, arch, etc.) without requiring changes to the init output format

### Key Entities *(include if feature involves data)*

- **Project**: Represents a Lily-managed project with a name and workflow phase. Key attributes include project_name, created_at timestamp, and current phase state. The root path is derived from the filesystem location where init is executed, not stored in state.json.
- **Artifact**: Represents a file created or managed by Lily. Key attributes include file path, artifact type (user-facing vs system), last modified timestamp, and content hash for change detection. Artifacts are tracked in `.lily/index.json` as an array structure, where each entry contains: file path, artifact type, last modified timestamp, and hash
- **State**: Represents the workflow state machine state stored in `.lily/state.json`. Key attributes include phase (DISCOVERY, SPEC, ARCH, etc.), project metadata, and version information. Minimum required fields: `phase` (string), `project_name` (string), `created_at` (timestamp), `last_updated` (timestamp), `version` (string)
- **Log Entry**: Represents an entry in the append-only audit log. Logs are maintained in dual format: `.lily/log.md` (human-readable markdown) and `.lily/log.jsonl` (JSONL format for programmatic parsing with Pydantic models). Key attributes include timestamp, command executed, and list of files created or modified. Both formats must be kept synchronized

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can successfully initialize a new Lily project in under 5 seconds from command execution to completion
- **SC-002**: 100% of required artifacts are created deterministically on every successful init execution: 6 user-facing markdown files (VISION.md, GOALS.md, NON_GOALS.md, CONSTRAINTS.md, ASSUMPTIONS.md, OPEN_QUESTIONS.md), 5 system files (state.json, index.json, config.json, log.md, log.jsonl), 1 docs directory README (docs/README.md), and 2 directory structures (.lily/runs/, .lily/tasks/) with placeholder files
- **SC-003**: Users can re-run `lily init` on the same project directory without errors or state corruption (100% idempotency success rate)
- **SC-004**: The initialized project structure enables the `status` command to successfully read and display phase information and artifact presence without modification to init output format
- **SC-005**: All created artifacts contain proper structure (section headers, guidance comments, empty lists) that are immediately usable for content entry by users or AI coders
- **SC-006**: Console output clearly communicates all created files and directories, enabling users to verify successful initialization without manual file system inspection

## Assumptions

- Users have write permissions in the directory where they run `lily init`
- The filesystem supports standard directory and file creation operations
- Project names provided by users are valid for filesystem paths (no special characters that would cause path issues)
- Users understand that `.lily/` is a system directory that should not be manually edited
- The initialized project will be used within a version control system (git), but init does not require git to be initialized
- Future commands (status, spec, arch, etc.) will read from the structure created by init without requiring format changes

## Dependencies

- Storage layer (filesystem operations) must be implemented before init command
- Command bus and result object infrastructure must exist to support command execution
- Basic validation framework for path creation and file writing

## Constraints

- Init command must NOT generate any code or invoke LLMs
- Init command must NOT make assumptions about programming languages or frameworks
- Init command must NOT ask interactive questions or require user input beyond project name
- All artifacts must be created deterministically (no random or time-dependent content that changes between runs)
- System artifacts under `.lily/` must never be manually edited by users
- The structure created by init must remain stable and not require changes when future features (TUI, multiple AI devs, spec generation) are added
