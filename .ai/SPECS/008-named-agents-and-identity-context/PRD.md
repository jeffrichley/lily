# PRD



# Feature: Named Agents with Identity Context Injection



**Author:** Jeff + Lily Runtime
**Audience:** Internal engineering and operator UX
**Status:** Draft v1

---

## 1. Executive Summary

Lily should support named agents as first-class runtime units under `.lily/agents/<agent-name>/`, where each agent has its own isolated working context, session/memory state, and identity definition files.

This feature introduces default + named agent selection from the CLI (`run`/`tui`) and formalizes an agent workspace contract that includes both runtime config files and identity/behavior markdown files. The runtime must inject these special markdown files into model context via middleware in a deterministic, documented way.

---

## 2. Mission

Enable multi-agent architecture foundations with deterministic local-first behavior.

Core principles:

- Agent identity is the folder name (supports names like `pepper-potts`).
- Default agent is explicit: `.lily/agents/default/`.
- Agent state is isolated per agent (sessions and memory).
- Relative paths resolve from the selected agent directory.
- Identity markdown context injection is middleware-driven, explicit, deterministic, and documented.

---

## 3. Target Users

- Primary: Lily operator/developer managing one or more agent personas.
- Secondary: Lily runtime maintainer extending toward sub-agent orchestration.

User needs:

- Select an agent by name at CLI runtime.
- Keep each agent's memory/session isolated.
- Define agent persona/constraints in markdown files.
- Ensure those files are loaded into runtime context without hidden behavior.

---

## 4. MVP Scope

### In Scope

- ✅ Named agent directory model under `.lily/agents/<agent-name>/`.
- ✅ Default agent at `.lily/agents/default/`.
- ✅ CLI flag to select named agent.
- ✅ Per-agent session DB/memory scoping.
- ✅ Relative path resolution from selected agent directory.
- ✅ Required special markdown files per agent:
  - `AGENTS.md`
  - `IDENTITY.md`
  - `SOUL.md`
  - `USER.md`
  - `TOOLS.md`
- ✅ Middleware-based context injection contract for special markdown files.
- ✅ Documentation updates for contract + CLI behavior.

### Out of Scope

- ❌ Full inter-agent messaging/orchestration graph.
- ❌ Autonomous agent spawning and scheduling.
- ❌ Cross-agent memory sync policy.

---

## 5. User Stories

- As an operator, I want `lily run --agent pepper-potts` so I can run a specific persona.
- As an operator, I want no flag to default to `default` so baseline workflows stay simple.
- As an operator, I want each agent to have isolated sessions so attach/resume does not bleed across personas.
- As a maintainer, I want required identity markdown files so every agent has explicit persona boundaries.
- As a maintainer, I want deterministic markdown context injection so prompt composition is auditable and testable.

---

## 6. Core Architecture & Patterns

Directory contract:

- `.lily/agents/<agent-name>/agent.toml` (or `agent.yaml`)
- `.lily/agents/<agent-name>/tools.toml` (or `tools.yaml`)
- `.lily/agents/<agent-name>/skills/` (required)
- `.lily/agents/<agent-name>/memory/` (required)
- `.lily/agents/<agent-name>/AGENTS.md` (required)
- `.lily/agents/<agent-name>/IDENTITY.md` (required)
- `.lily/agents/<agent-name>/SOUL.md` (required)
- `.lily/agents/<agent-name>/USER.md` (required)
- `.lily/agents/<agent-name>/TOOLS.md` (required)

Selection and resolution:

- CLI resolves selected agent directory first.
- Runtime config/tool paths are derived from agent directory.
- Relative references (skills roots, logs, tool cwd when relative) resolve from selected agent directory.

Context injection (middleware only):

- Agent identity files are loaded and injected as structured context sections by dedicated middleware right before model invocation.
- Injection order is fixed and documented.
- Missing required file should fail fast with deterministic error.

---

## 7. Tools/Features

- Feature A: Agent locator/resolver (`default` and named).
- Feature B: CLI agent selection (`--agent` with deterministic precedence).
- Feature C: Per-agent session DB path resolution.
- Feature D: Identity markdown context loader + middleware injector.
- Feature E: Operator-facing docs for contract and behavior.

---

## 8. Technology Stack

- Python runtime (existing Lily stack)
- Typer CLI (existing)
- Pydantic config validation (existing)
- SQLite session store (existing)

No new external dependency required for MVP.

---

## 9. Security & Configuration

- Treat identity markdown as local trusted configuration files.
- Do not read outside selected agent directory unless explicitly configured.
- Fail fast on missing required files/directories.
- Preserve existing strict config validation; avoid silent fallbacks.
- Personality/identity context must be injected by middleware, not by static
  startup-time system prompt mutation.

---

## 10. API Specification

CLI additions:

- `lily run --agent <name>`
- `lily tui --agent <name>`

Optional future:

- `lily agents list`
- `lily agents inspect <name>`

---

## 11. Success Criteria

- Named agent selection works for `run` and `tui`.
- Default path uses `.lily/agents/default/`.
- Session storage is isolated per agent.
- Required markdown files are validated.
- Runtime injects special markdown files into context via middleware in deterministic order.
- Docs explicitly describe injection contract.

---

## 12. Implementation Phases

### Phase 1: Agent directory + resolution contract

- Goal: Add deterministic agent lookup and config path derivation.
- Deliverables:
  - Agent directory resolver.
  - Validation for required files/directories.
  - `default` fallback behavior.
- Validation:
  - Unit tests for valid/missing/malformed agent directories.

### Phase 2: CLI integration and session isolation

- Goal: Route `run`/`tui` through selected agent and isolate sessions.
- Deliverables:
  - `--agent` options.
  - Per-agent session DB path usage.
  - Explicit conflict/error behavior for `--config` interactions.
- Validation:
  - E2E CLI tests for default/named/missing-agent cases.

### Phase 3: Identity markdown context injection via middleware

- Goal: Inject special markdown files into runtime context via middleware.
- Deliverables:
  - Loader for required markdown files.
  - Dedicated middleware implementation for personality/context injection.
  - Stable injection order and formatting.
  - Deterministic error semantics for missing files.
- Validation:
  - Unit/integration tests for injected content ordering and presence.

### Phase 4: Docs and migration guidance

- Goal: Make operator contract explicit and migratable.
- Deliverables:
  - Runtime docs updated with named-agent + injection contract.
  - Migration notes for moving `.lily/config/`* -> `.lily/agents/default/*`.
- Validation:
  - Docs checks and explicit examples verified.

---

## 13. Future Considerations

- Sub-agent to sub-agent communication channels.
- Agent capability registry and delegation rules.
- Agent lifecycle commands (`init`, `clone`, `archive`).

---

## 14. Risks & Mitigations

- Risk: Ambiguous CLI precedence (`--agent` with `--config`).
  - Mitigation: define strict conflict policy and test matrix.
- Risk: Prompt bloat from markdown injection.
  - Mitigation: stable formatting and bounded sections; optional truncation policy later.
- Risk: Breaking existing workflows.
  - Mitigation: default agent migration path and compatibility docs.

---

## 15. Appendix

External inspiration for identity/workspace file structure:

- [OpenClaw templates directory](https://github.com/openclaw/openclaw/tree/main/docs/zh-CN/reference/templates)
- [AGENTS.md template](https://raw.githubusercontent.com/openclaw/openclaw/main/docs/zh-CN/reference/templates/AGENTS.md)
- [IDENTITY.md template](https://raw.githubusercontent.com/openclaw/openclaw/main/docs/zh-CN/reference/templates/IDENTITY.md)
- [SOUL.md template](https://raw.githubusercontent.com/openclaw/openclaw/main/docs/zh-CN/reference/templates/SOUL.md)
- [TOOLS.md template](https://raw.githubusercontent.com/openclaw/openclaw/main/docs/zh-CN/reference/templates/TOOLS.md)
- [USER.md template](https://raw.githubusercontent.com/openclaw/openclaw/main/docs/zh-CN/reference/templates/USER.md)
