---
owner: "@jeffrichley"
last_updated: "2026-03-25"
status: "active"
source_of_truth: true
---

# Dev Status Diary

## Current Focus

- Open or refresh the skills retrieval MVP PR using `docs/dev/pr-si007-skills-mvp.md` (branch `feat/005-skills-system-implementation`).
- Execute backlog **BL-007** (Phase 9 skills distribution) per `.ai/PLANS/005-skills-system-implementation.md` (post-MVP; not blocking merge of retrieval MVP).

## Recently Completed

- Closed SI-007 Phase 8 (hardening): full gates, `docs/dev/references/skills-si007-mvp.md` alignment + verification, PR draft `docs/dev/pr-si007-skills-mvp.md`, roadmap SI-007 → Completed (retrieval MVP), backlog **BL-006**/ **BL-007** for deferred heuristics and Phase 9 distribution; extra tests `test_cli_run_smoke_with_skills_fixture_config`, `test_skill_loader_utf8_non_ascii_body_round_trips` (`.ai/PLANS/005-skills-system-implementation.md`).
- Delivered SI-007 Phase 7 skill telemetry: `skill_events` (`SKILL_EVENT_SCHEMA_VERSION`, JSON on `lily.skill.telemetry`), hooks in `build_skill_bundle`, `AgentRuntime._build_agent`, `SkillLoader`, `skill_retrieve`; `sanitize_telemetry_detail`; unit `tests/unit/runtime/test_skill_events.py`; integration `test_skill_telemetry_emits_retrieval_flow_events` (`.ai/PLANS/005-skills-system-implementation.md`).
- Delivered SI-007 Phase 6 CLI skills surfaces: `lily skills list|inspect|doctor` (Rich tables/panels), `SkillCliDiagnostics`, filtering/sorting (`--contains`, `--sort`), `cli_options` shared with root CLI; e2e `tests/e2e/test_cli_skills_commands.py`; user doc snippets for skills CLI deferred to Phase 8 (`.ai/PLANS/005-skills-system-implementation.md`).
- Delivered SI-007 Phase 5 supervisor/runtime integration: `skill_retrieve` omitted from resolved tools when `skills.enabled` is false; `_effective_runtime_config` strips `skill_retrieve` from allowlist when needed; `AgentRunResult.skill_trace` (`SkillInvokeTrace`, `SkillRetrievalTraceEntry`); trace hooks in `skill_retrieve`; integration suite `tests/integration/test_skills_runtime_flow.py`; fixture config `tests/fixtures/config/skills_retrieval/` (`.ai/PLANS/005-skills-system-implementation.md`).
- Delivered SI-007 Phase 4 retrieval policy + linked constraints: `skill_policies` (`effective_skill_tools`, `build_retrieval_blocked_keys`, `retrieval_config_denial_reason`), `SkillsRetrievalConfig` + normalized `skills.allowlist`/`denylist`, `SkillRetrievalDeniedError`, loader deny-before-content + path-bounding under skill package root; tests `test_skill_policies`, extended `test_skill_loader` (`.ai/PLANS/005-skills-system-implementation.md`).
- Delivered SI-007 Phase 3 catalog injection + loader: `skill_prompt_injector`, `skill_loader` / `SkillBundle`, `skill_retrieve` tool + `ContextVar` binding in `AgentRuntime`, `LilySupervisor` + `build_skill_bundle`, `.lily/config/tools.toml` entry; tests `test_skill_prompt_injector`, `test_skill_loader`, `test_skill_retrieve_tool`, integration catalog append (`test_agent_runtime_appends_skill_catalog_to_system_prompt`) (`.ai/PLANS/005-skills-system-implementation.md`).
- Delivered SI-007 Phase 2 discovery and registry: `skill_discovery`, `skill_registry`, `RuntimeConfig.skills` / `SkillsToolsConfig`, unit tests (`test_skill_discovery`, `test_skill_registry`, config skills cases in `test_config_loader`), integration `tests/integration/test_skills_discovery_registry.py` (`.ai/PLANS/005-skills-system-implementation.md`).
- Delivered SI-007 Phase 1 skill contract: `SkillMetadata` / `SkillSummary`, `skill_catalog` parser (`python-frontmatter`), fixtures under `tests/fixtures/skills/`, unit tests `tests/unit/runtime/test_skill_catalog.py` (`.ai/PLANS/005-skills-system-implementation.md`).
- Locked SI-007 execution framing: MVP traceability matrix, phase tracker, dependency graph, risk register (R-001–R-005), rollback-by-phase table, and non-goals in `.ai/PLANS/005-skills-system-implementation.md` (Phase 0).
- Delivered LangChain kernel runtime with YAML config validation and dynamic model routing (SI-001) (`.ai/PLANS/001-langchain-agent-kernel-yaml.md`).
- Delivered CLI + basic Textual TUI surfaces wired to one supervisor/runtime path (SI-001) (`src/lily/cli.py`, `src/lily/ui/`).
- Delivered conversation session attach/resume across CLI and TUI with persisted IDs and thread continuity (SI-006) (`.ai/PLANS/002-conversation-session-attach-resume.md`).
- Completed SI-002 Phase 1-2 foundations: tool catalog schema/loader and Python+MCP resolver layer (`.ai/PLANS/003-simple-tool-registry-python-mcp.md`).
- Completed SI-002 Phase 3 supervisor/runtime catalog wiring with allowlist gate preserved (`.ai/PLANS/003-simple-tool-registry-python-mcp.md`).
- Completed SI-002 end-to-end: tool catalog/resolver wiring, docs updates, and full quality/test gates including security audit remediation (`.ai/PLANS/003-simple-tool-registry-python-mcp.md`).
- Completed SI-002 Phase 5 MCP runtime wiring with deterministic CLI/TUI MCP verification surfaces (`.ai/PLANS/003-simple-tool-registry-python-mcp.md`).
- Completed SI-002 Phase 6 TOML parity: runtime/catalog loaders, `agent.toml`/`tools.toml` support, and YAML/TOML CLI/TUI parity validation (`.ai/PLANS/003-simple-tool-registry-python-mcp.md`).

## Diary Log

- 2026-03-04: Completed phases 1-4 for kernel/runtime/CLI/TUI and validated warning-clean gates.
- 2026-03-04: Marked deferred internal items for registry, sub-agent runtime, and evolution logging (SI-002, SI-003, SI-004).
- 2026-03-05: Completed phases 1-4 for conversation session attach/resume feature and validated full quality/test gates (`.ai/PLANS/002-conversation-session-attach-resume.md`).
- 2026-03-05: Started SI-002 implementation and completed phases 1-2 with passing targeted unit gates; status-sync docs-check remains blocked by pre-existing frontmatter gap in `docs/ideas/tool_registries.md`.
- 2026-03-05: Completed SI-002 phase 3 acceptance gates (integration + e2e); docs-check remains blocked by pre-existing frontmatter gap in `docs/ideas/tool_registries.md`.
- 2026-03-05: Cleared docs-check blocker by adding frontmatter to `docs/ideas/tool_registries.md`; completed SI-002 phase 4 test/docs work, but final quality gate remains blocked by `pip-audit` advisory `langgraph 1.0.8 CVE-2026-28277` (owner `@jeffrichley`, target `2026-03-12`).
- 2026-03-05: Resolved SI-002 final gate blocker by upgrading `langgraph` to `1.0.10` (and `langgraph-prebuilt` to `1.0.8` via lock refresh), then re-ran `just quality` and `just test` successfully.
- 2026-03-05: Completed SI-002 Phase 5 by wiring runtime MCP providers (`mcp_servers`) and verifying MCP tool execution via CLI plus automated TUI parity tests; opened SI-002 Phase 6 for TOML config parity follow-up.
- 2026-03-06: Completed SI-002 Phase 6 with TOML runtime/catalog parity, inferred `agent.toml -> tools.toml` default behavior, and passing full quality/test + coverage gates.
- 2026-03-06: Split roadmap tracking: SI-002 remains completed for tool-registry delivery, and SI-007 is now in progress for first-class skills-system delivery (`docs/dev/roadmap.md`).
- 2026-03-25: Completed SI-007 Phase 0 (execution framing and acceptance lock) on branch `feat/005-skills-system-implementation`; Phase 1 implementation is next.
- 2026-03-25: Phase 0 close validation: `just quality && just test` green; bumped `requests` to 2.33.0 in `uv.lock`; `pip-audit` gate documents **DEBT-017** for CVE-2026-4539 (no `pygments` fix on PyPI yet).
- 2026-03-25: Completed SI-007 Phase 1 (`skill_types`, `skill_catalog`, unit tests + fixtures); full `just quality` and `just test` green on `feat/005-skills-system-implementation`.
- 2026-03-25: Completed SI-007 Phase 2 (`skill_discovery`, `skill_registry`, config `skills.*`); `just quality` and `just test` green (84 tests).
- 2026-03-25: Completed SI-007 Phase 3 (catalog injection, `skill_loader`, `skill_retrieve`, runtime wiring); `just quality` and `just test` green (97 tests).
- 2026-03-25: Completed SI-007 Phase 4 (retrieval policy gates, F6 `effective_skill_tools`, linked-file constraints); `just quality` and `just test` green (111 tests).
- 2026-03-25: Completed SI-007 Phase 5 (supervisor `skill_retrieve` gating, `skill_trace` on `AgentRunResult`, integration tests `test_skills_runtime_flow`); `just quality && just test` green (119 tests).
- 2026-03-25: Completed SI-007 Phase 6 (`cli_skills`, `cli_skills_presenters`, `skill_cli_diagnostics`, e2e CLI tests); `just quality && just test` green (124 tests); skills CLI usage docs follow-up in Phase 8.
- 2026-03-25: Completed SI-007 Phase 7 (`skill_events`, telemetry hooks, redaction tests); `just quality && just test` green (132 tests).
- 2026-03-25: Completed SI-007 Phase 8 (docs/status/roadmap/backlog sync, skills SI-007 reference + PR draft, e2e/loader tests); `just quality && just test` green; SI-007 retrieval MVP scope complete per plan 005 Phases 1–8.
