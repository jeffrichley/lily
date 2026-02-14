# Later Backlog (Do Not Forget)

Purpose: track important deferred items while we keep Slice 001 narrow.

## Core Runtime

- [ ] Persist session state to disk (including `skill_snapshot`) so sessions can survive process restarts.
- [ ] Define session reload semantics on startup (`session_id` lookup, missing/corrupt recovery behavior).
- [ ] Add explicit `/reload_skills` command and snapshot version bump behavior.
- [ ] Add `/help <skill>` command using snapshot-only metadata reads.
- [ ] Add `/agent <name>` command and deterministic active-agent switching.

## Skills

- [ ] Add optional user skills root and include it in precedence (`workspace > user > bundled`).
- [ ] Add skill alias commands from frontmatter `command` with collision checks.
- [ ] Add `tool_dispatch` execution path with strict `command_tool` validation.
- [ ] Add richer loader diagnostics output surface for malformed/ineligible skills.
- [ ] Remove temporary `if skill_name == "echo"` branch in backend and make behavior sourcing skill-driven.
- [ ] Load and pass `SKILL.md` body/instructions to execution layer so orchestration is not hardcoded per skill.

## Reliability

- [ ] Add file-locking strategy for session persistence (multi-process safety).
- [ ] Add deterministic queue/serialization boundary for command execution.
- [ ] Add snapshot drift tests for mid-session filesystem mutation.

## Observability

- [ ] Add structured trace events for loader phases and command dispatch decisions.
- [ ] Add optional prompt/session trace artifacts for replay debugging.
- [ ] Reduce third-party provider transport noise in REPL output (toggle or logger filtering for HTTP request logs).

## Product Surface

- [ ] Define explicit persistence policy (what survives restart vs what is ephemeral).
- [ ] Define migration/versioning policy for persisted session schema.

## Commands And UX

- [ ] Add deterministic unknown-command error contract (no conversational fallback for `/...`).
- [ ] Add explicit argument validation errors (for example `/skill` with missing name).
- [ ] Add optional "did you mean" suggestions behind a strict non-executing mode.
- [ ] Define consistent command output envelope (`ok/error`, `code`, `message`, `data`).

## Data Models And Validation

- [ ] Standardize Pydantic config (`extra='forbid'`, strict validation where appropriate).
- [ ] Add schema version field to persisted session payloads.
- [ ] Add migration stubs for future session schema changes.
- [ ] Define canonical normalization rules for skill names and command aliases.

## Persona And Context

- [ ] Decide if persona is fixed at session creation or supports explicit reload command.
- [ ] Add explicit persona reload command if dynamic behavior is desired (`/reload_persona`).
- [ ] Define deterministic merge order for persona files in prompt assembly.

## Testing

- [ ] Add golden tests for `/skills` deterministic ordering output.
- [ ] Add conflict tests for precedence with same skill name across roots.
- [ ] Add malformed frontmatter tests (exclude + diagnostics, no crash).
- [ ] Add eligibility matrix tests (`os`, `env`, `binaries`).
- [ ] Add restart simulation tests once persistence is implemented.

## Security And Safety

- [ ] Define trust model for skill content (trusted local vs untrusted imported skills).
- [ ] Add optional lightweight skill linting/validation command (`skills validate`).
- [ ] Add explicit denylist/allowlist for skill command aliases.
- [ ] Define policy for `tool_dispatch` skills requiring privileged tools.

## Developer Experience

- [ ] Add a single `slice_001_smoke.py` script for manual end-to-end validation.
- [ ] Add a minimal `make/just` target for running the slice demo deterministically.
- [ ] Add architecture decision record (ADR) summarizing command-vs-LLM boundary.
- [ ] Add docs index page linking specs, slice plan, and later backlog.
