# Tasks: Init Command

**Input**: Design documents from `/specs/001-init-command/`
**Prerequisites**: plan.md, spec.md, data-model.md, contracts/, research.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., [US1], [US2])
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Create project directory structure per implementation plan (src/lily/core/application/commands/, src/lily/core/domain/, src/lily/core/infrastructure/models/, src/lily/ui/cli/, tests/unit/, tests/integration/)
- [X] T002 [P] Create __init__.py files in all package directories (src/lily/__init__.py, src/lily/core/__init__.py, src/lily/core/application/__init__.py, src/lily/core/application/commands/__init__.py, src/lily/core/domain/__init__.py, src/lily/core/infrastructure/__init__.py, src/lily/core/infrastructure/models/__init__.py, src/lily/ui/__init__.py, src/lily/ui/cli/__init__.py)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T003 [P] Create StateModel Pydantic model in src/lily/core/infrastructure/models/state.py with fields: phase (str, enum), project_name (str), created_at (datetime), last_updated (datetime), version (str)
- [X] T004 [P] Create ArtifactModel Pydantic model in src/lily/core/infrastructure/models/index.py with fields: file_path (str), artifact_type (str, enum: "user-facing" or "system"), last_modified (datetime), hash (str)
- [X] T005 [P] Create IndexModel Pydantic model in src/lily/core/infrastructure/models/index.py as list of ArtifactModel
- [X] T006 [P] Create ConfigModel Pydantic model in src/lily/core/infrastructure/models/config.py with fields: version (str), project_name (str), created_at (datetime)
- [X] T007 [P] Create LogEntryModel Pydantic model in src/lily/core/infrastructure/models/log.py with fields: timestamp (datetime), command (str), action (str, enum: "created", "skipped", "repaired", "failed"), files (list[str]), metadata (dict, optional)
- [X] T008 Create Storage class in src/lily/core/infrastructure/storage.py implementing file operations: create_directory(), create_file(), file_exists(), check_permissions(), read_json(), write_json(), append_jsonl(), append_markdown_log(), calculate_hash()
- [X] T009 Create Logger class in src/lily/core/infrastructure/storage.py implementing dual-format logging: log_init() method that writes to both log.md and log.jsonl synchronously
- [X] T010 Create base Command abstract class in src/lily/core/application/commands/base.py with execute() and validate() abstract methods, and CommandResult protocol
- [X] T011 Create CommandResult dataclass in src/lily/core/application/commands/base.py with fields: success (bool), message (str), files_created (list[str]), files_skipped (list[str])

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Initialize New Project (Priority: P1) 🎯 MVP

**Goal**: A user wants to bootstrap a new project using Lily's orchestration framework. They run the `init` command to establish the project structure, workspace directories, and initial state files that all subsequent Lily commands will depend on.

**Independent Test**: Can be fully tested by running `lily init <project_name>` in an empty or new directory and verifying all required files and directories are created with correct structure and content. This delivers immediate value by establishing a working project foundation.

### Implementation for User Story 1

- [X] T012 [US1] Create InitCommand class in src/lily/core/application/commands/init.py implementing Command interface with validate() and execute() methods
- [X] T013 [US1] Implement validate() method in InitCommand (src/lily/core/application/commands/init.py) to check write permissions and validate project name
- [X] T014 [US1] Implement directory creation logic in InitCommand.execute() (src/lily/core/application/commands/init.py) to create .lily/, .lily/runs/, .lily/tasks/, and docs/ directories
- [X] T015 [US1] Implement system artifact creation in InitCommand.execute() (src/lily/core/application/commands/init.py): create .lily/state.json with StateModel (phase="DISCOVERY", project_name, created_at, last_updated, version)
- [X] T016 [US1] Implement system artifact creation in InitCommand.execute() (src/lily/core/application/commands/init.py): create .lily/config.json with ConfigModel (version, project_name, created_at)
- [X] T017 [US1] Implement system artifact creation in InitCommand.execute() (src/lily/core/application/commands/init.py): create .lily/index.json as empty array (IndexModel)
- [X] T018 [US1] Implement placeholder file creation in InitCommand.execute() (src/lily/core/application/commands/init.py): create .gitkeep files in .lily/runs/ and .lily/tasks/ directories
- [X] T019 [US1] Create ArtifactGenerator base class in src/lily/core/infrastructure/storage.py using Template Method pattern for consistent markdown file generation
- [X] T020 [US1] Implement VisionGenerator in src/lily/core/infrastructure/storage.py to create docs/VISION.md with section headers, guidance comments, and empty bullet lists
- [X] T021 [US1] Implement GoalsGenerator in src/lily/core/infrastructure/storage.py to create docs/GOALS.md with section headers, guidance comments, and empty bullet lists
- [X] T022 [US1] Implement NonGoalsGenerator in src/lily/core/infrastructure/storage.py to create docs/NON_GOALS.md with section headers, guidance comments, and empty bullet lists
- [X] T023 [US1] Implement ConstraintsGenerator in src/lily/core/infrastructure/storage.py to create docs/CONSTRAINTS.md with section headers, guidance comments, and empty bullet lists
- [X] T024 [US1] Implement AssumptionsGenerator in src/lily/core/infrastructure/storage.py to create docs/ASSUMPTIONS.md with section headers, guidance comments, and empty bullet lists
- [X] T025 [US1] Implement OpenQuestionsGenerator in src/lily/core/infrastructure/storage.py to create docs/OPEN_QUESTIONS.md with section headers, guidance comments, and empty bullet lists
- [X] T026 [US1] Implement DocsReadmeGenerator in src/lily/core/infrastructure/storage.py to create docs/README.md explaining the purpose of the docs folder
- [X] T027 [US1] Implement user-facing artifact creation in InitCommand.execute() (src/lily/core/application/commands/init.py): create all 6 markdown files and docs/README.md using generators
- [X] T028 [US1] Implement index.json update logic in InitCommand.execute() (src/lily/core/application/commands/init.py): add all created artifacts to index.json with file_path, artifact_type, last_modified, and hash
- [X] T029 [US1] Implement dual-format log entry creation in InitCommand.execute() (src/lily/core/application/commands/init.py): write initial log entry to both .lily/log.md and .lily/log.jsonl using Logger
- [X] T030 [US1] Implement console output formatting in InitCommand.execute() (src/lily/core/application/commands/init.py): return InitResult with clear summary listing all files created
- [X] T031 [US1] Create CLI entry point in src/lily/ui/cli/main.py using Typer to register `init` command that calls InitCommand
- [X] T032 [US1] Implement CLI argument parsing in src/lily/ui/cli/main.py: accept required PROJECT_NAME argument OR --here flag. If --here is specified, use current directory name as project name. If --here is not specified, PROJECT_NAME is required.
- [X] T033 [US1] Implement CLI result rendering in src/lily/ui/cli/main.py: format InitResult for console output with success message and file list

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently. Running `lily init myproject` should create all required files and directories.

---

## Phase 4: User Story 2 - Re-initialize Existing Project (Priority: P2)

**Goal**: A user wants to re-run the `init` command on an already-initialized project, either to repair corrupted files or to ensure all required artifacts exist.

**Independent Test**: Can be fully tested by running `lily init` on a directory that already contains some or all of the expected artifacts, and verifying that existing files are preserved or updated appropriately without corruption.

### Implementation for User Story 2

- [X] T034 [US2] Implement file existence check in InitCommand.execute() (src/lily/core/application/commands/init.py): check if files exist before creating, skip existing files (idempotent behavior)
- [X] T035 [US2] Implement missing file detection in InitCommand.execute() (src/lily/core/application/commands/init.py): identify which required artifacts are missing and create only those
- [X] T036 [US2] Implement state.json corruption detection in InitCommand.validate() (src/lily/core/application/commands/init.py): validate JSON schema using StateModel, detect corruption
- [X] T037 [US2] Implement state.json repair logic in InitCommand.execute() (src/lily/core/application/commands/init.py): recreate corrupted state.json with default values, log repair event
- [X] T038 [US2] Implement log entry for skipped files in InitCommand.execute() (src/lily/core/application/commands/init.py): log "skipped" action for existing files in both log formats
- [X] T039 [US2] Implement log entry for repaired files in InitCommand.execute() (src/lily/core/application/commands/init.py): log "repaired" action with metadata about corruption in both log formats
- [X] T040 [US2] Update InitResult in InitCommand.execute() (src/lily/core/application/commands/init.py): include files_skipped list in result for re-initialization scenarios
- [X] T041 [US2] Update console output in src/lily/ui/cli/main.py: display both created and skipped files when re-running init

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently. Running `lily init` multiple times should be idempotent and handle corruption repair.

---

## Phase 5: Error Handling & Edge Cases

**Purpose**: Handle error scenarios and edge cases from specification

- [X] T042 Implement permission validation in InitCommand.validate() (src/lily/core/application/commands/init.py): check write permissions before file operations, fail fast with clear error message
- [X] T043 Implement permission error handling in InitCommand.execute() (src/lily/core/application/commands/init.py): catch permission errors, return InitError with failed_paths list
- [X] T044 Implement invalid project name validation in InitCommand.validate() (src/lily/core/application/commands/init.py): validate project name for filesystem path compatibility
- [X] T045 Implement error logging in InitCommand.execute() (src/lily/core/application/commands/init.py): log "failed" action to both log formats when errors occur
- [X] T046 Update CLI error handling in src/lily/ui/cli/main.py: format and display error messages with specific failure reasons and paths

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [X] T047 [P] Add docstrings to all classes and methods in src/lily/core/application/commands/init.py
- [X] T048 [P] Add docstrings to all classes and methods in src/lily/core/infrastructure/storage.py
- [X] T049 [P] Add docstrings to all Pydantic models in src/lily/core/infrastructure/models/
- [X] T050 Verify deterministic file creation: ensure all file content is deterministic (no random values, fixed timestamps for testing)
- [X] T051 Verify idempotency: test that running init multiple times produces consistent results
- [X] T051a [P] Add integration test in tests/integration/test_init_integration.py: verify SC-002 artifact count (6 user-facing markdown files + 5 system files + 1 docs README + 2 directory structures = 14 total artifacts)
- [X] T052 Performance validation: ensure init completes in under 5 seconds (SC-001)
- [X] T053 Verify log synchronization: ensure log.md and log.jsonl contain identical information

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational completion - MVP deliverable
- **User Story 2 (Phase 4)**: Depends on User Story 1 completion (builds on idempotency)
- **Error Handling (Phase 5)**: Can be done in parallel with User Story 2 or after
- **Polish (Phase 6)**: Depends on all implementation phases being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Depends on User Story 1 completion - Extends US1 with idempotency and repair features

### Within Each User Story

- Models before services (Pydantic models in Phase 2 before InitCommand in Phase 3)
- Storage layer before command implementation
- Command implementation before CLI integration
- Core implementation before error handling

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel (T002)
- All Foundational Pydantic model tasks marked [P] can run in parallel (T003-T007)
- All generator tasks in User Story 1 marked [P] can run in parallel (T020-T026)
- All documentation tasks in Polish phase marked [P] can run in parallel (T047-T049)

---

## Parallel Example: User Story 1

```bash
# Launch all markdown generators in parallel:
Task: "Implement VisionGenerator in src/lily/core/infrastructure/storage.py"
Task: "Implement GoalsGenerator in src/lily/core/infrastructure/storage.py"
Task: "Implement NonGoalsGenerator in src/lily/core/infrastructure/storage.py"
Task: "Implement ConstraintsGenerator in src/lily/core/infrastructure/storage.py"
Task: "Implement AssumptionsGenerator in src/lily/core/infrastructure/storage.py"
Task: "Implement OpenQuestionsGenerator in src/lily/core/infrastructure/storage.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently by running `lily init myproject` and verifying all files are created
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo (Idempotency + Repair)
4. Add Error Handling → Test edge cases → Deploy/Demo
5. Add Polish → Final validation → Deploy/Demo

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (InitCommand, CLI)
   - Developer B: User Story 2 (Idempotency, Repair) - can start after US1 core is done
   - Developer C: Error Handling (can work in parallel)
3. Stories complete and integrate independently

---

## Task Summary

**Total Tasks**: 54

**By Phase**:
- Phase 1 (Setup): 2 tasks
- Phase 2 (Foundational): 9 tasks
- Phase 3 (User Story 1): 22 tasks
- Phase 4 (User Story 2): 8 tasks
- Phase 5 (Error Handling): 5 tasks
- Phase 6 (Polish): 8 tasks

**By User Story**:
- User Story 1: 22 tasks
- User Story 2: 8 tasks

**Parallel Opportunities**: 16 tasks marked [P]

**MVP Scope**: Phases 1-3 (User Story 1 only) = 33 tasks

**Independent Test Criteria**:
- **User Story 1**: Run `lily init myproject` in empty directory, verify all files created
- **User Story 2**: Run `lily init` on existing project, verify idempotency and repair

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify deterministic behavior: same inputs produce same outputs
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence

