---
owner: "@jeffrichley"
last_updated: "2026-03-25"
status: "reference"
source_of_truth: false
---

# PR body draft (SI-007 skills retrieval MVP)

Use the block below for `gh pr create` / `gh pr edit`. Headings match `.github/pull_request_template.md`.

---

# Summary

Delivers the SI-007 **retrieval-only** skills MVP: `SKILL.md` contract and discovery, merged registry with deterministic precedence, system-prompt catalog injection, `skill_retrieve` with policy gates and progressive disclosure, supervisor/runtime integration with `skill_trace`, operator `lily skills list|inspect|doctor` (Rich), and JSON skill telemetry on `lily.skill.telemetry`. **Complete:** Phases 1–8 of `.ai/PLANS/005-skills-system-implementation.md`. **Deferred:** Phase 9 distribution/zip, trigger-quality heuristics, TUI parity for skills commands.

---

# Verification

## Required Gates

- [x] `just quality && just test` green (warning-clean)
- [x] `just docs-check` and `just status` green

## Tests Added / Updated

- Unit: `tests/unit/runtime/test_skill_*.py`, `test_skill_events.py`
- Integration: `tests/integration/test_skills_runtime_flow.py`, `test_skills_discovery_registry.py`, and related agent tests
- E2E: `tests/e2e/test_cli_skills_commands.py`, `test_cli_agent_run.py` (skills fixture smoke)

## How to Reproduce / Validate

```bash
just quality && just test
just docs-check && just status
uv run pytest tests/e2e -k "skill or skills" -q
uv run lily skills doctor --config tests/fixtures/config/skills_retrieval/agent.toml
```

---

# Risk Assessment

## Risk Level

- [ ] Low (localized change, strong tests, minimal surface area)
- [x] Medium (touches core paths, moderate surface area, good tests)
- [ ] High (wide surface area, complex behavior, or migration involved)

## Failure Modes Considered

- Skills disabled: `skill_retrieve` omitted from resolved tools; allowlist coherency via `LilySupervisor._effective_runtime_config`
- Policy denial: deny-before-content; trace and telemetry record failure without leaking skill bodies
- Malformed packages: deterministic parser errors; CLI doctor lists collisions and invalid packages

## Rollback Plan

- Set `skills.enabled = false`; ensure allowlist does not reference `skill_retrieve` alone when skills are off

---

# Documentation Impact

- [ ] No docs update needed
- [x] Docs updated in this PR (list paths below)
- [ ] Docs follow-up required (owner + target date below)

`docs/dev/status.md`, `docs/dev/roadmap.md`, `docs/dev/backlog.md`, `docs/dev/backlog/skills-distribution-packaging.md`, `docs/dev/references/skills-si007-mvp.md`, `.ai/PLANS/005-skills-system-implementation.md`, `docs/dev/pr-si007-skills-mvp.md` (this draft file)

---

# Checklist (Ruthless)

- [x] PR distinguishes **shipped** retrieval MVP vs **deferred** Phase 9 / heuristics
- [x] Telemetry events do not embed full skill bodies or prompts
- [x] `Documentation Impact` has exactly one option selected
