# Lily Punchlist

Purpose: concrete engineering checklist to get Lily to a solid, usable state.

## Priority 5 (Do First)

- [x] Remove prototype hardcoding (`echo`)
  - [x] Remove `if request.skill_name == "echo"` behavior in `src/lily/runtime/llm_backend/langchain_adapter.py`
  - [x] Pass skill artifact instructions/body into LLM request path
  - [x] Ensure no skill-name-specific runtime branches remain

- [x] Implement real `tool_dispatch`
  - [x] Replace placeholder in `src/lily/runtime/executors/tool_dispatch.py`
  - [x] Add strict `command_tool` validation and deterministic error outputs
  - [x] Wire dispatch path through runtime facade/executor setup

- [x] Expand core command surface
  - [x] Add `/reload_skills`
  - [x] Add `/help <skill>`
  - [x] Add skill alias commands from frontmatter `command` with built-in collision protection

- [x] Standardize command envelope
  - [x] Extend `CommandResult` to include `code` and `data` in addition to `status` and `message`
  - [x] Update handlers/executors to return stable machine-readable outputs
  - [x] Update CLI rendering path accordingly

- [x] Add session persistence + reload semantics
  - [x] Persist session state to disk (`session_id`, `active_agent`, `model_config`, `skill_snapshot`, conversation)
  - [x] Add session schema version field and migration stub path
  - [x] Define recovery behavior for missing/corrupt persisted state

- [x] Add per-session execution serialization
  - [x] Introduce a per-session queue/lane boundary for command + execution flow
  - [x] Prevent interleaving/race issues under concurrent inputs

- [x] Add reliability coverage
  - [x] Restart simulation tests (session restore + snapshot continuity)
  - [x] Snapshot drift tests (filesystem mutation does not alter current session snapshot)
  - [x] Concurrency/serialization tests

## Priority 4 (Next Elevation)

- [ ] Add `/agent <name>` (deferred until real agents/persona subsystem exists)
- [ ] Typed skill I/O contracts
  - [ ] Add optional input/output schema fields to skill metadata
  - [ ] Validate input pre-execution and output post-execution
  - [ ] Return deterministic validation errors
  - [ ] Prove with at least two skills end-to-end
