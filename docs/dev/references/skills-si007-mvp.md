---
owner: "@jeffrichley"
last_updated: "2026-03-25"
status: "active"
source_of_truth: true
---

# SI-007 retrieval MVP: verification and guide alignment

This note ties **shipped behavior** to the skills PRD/architecture and plan `005` (Phases 1–8). Post-MVP distribution and packaging are tracked in `.ai/PLANS/005-skills-system-implementation.md` Phase 9.

## Verification commands

Run from the repository root:

```bash
just quality && just test
just docs-check && just status
uv run pytest tests/unit/runtime -k skill -q
uv run pytest tests/integration -k skill -q
uv run pytest tests/e2e -k "skill or skills" -q
```

Operator-facing checks (config paths may vary):

```bash
uv run lily skills list --config tests/fixtures/config/skills_retrieval/agent.toml
uv run lily skills inspect fixture-skill --config tests/fixtures/config/skills_retrieval/agent.toml
uv run lily skills doctor --config tests/fixtures/config/skills_retrieval/agent.toml
```

## Guide alignment (architecture §20 / PRD security)

| Requirement | Evidence in repo |
|-------------|------------------|
| Required `SKILL.md`; frontmatter keys `name` + `description` | `skill_catalog.py`, `tests/unit/runtime/test_skill_catalog.py` |
| Kebab-case normalization / canonical key | `skill_types.normalize_skill_name`, `test_skill_catalog`, `lily skills` doctor/list |
| Reject `<` / `>` in frontmatter values | `test_angle_bracket_in_name_rejected`, `test_angle_bracket_in_nested_metadata_rejected` |
| Block reserved name prefixes (`claude*`, `anthropic*`) | `test_reserved_name_prefix_claude_rejected`, `test_reserved_name_prefix_anthropic_rejected` |
| Safe YAML (no executable tags) | `skill_catalog` uses `yaml.safe_load` on frontmatter; malformed cases in `test_skill_catalog` |
| Progressive disclosure (catalog summaries → retrieval tool → full file) | `skill_prompt_injector`, `skill_loader`, `skill_retrieve_tool`, integration `test_skills_runtime_flow.py` |
| Retrieval policy before content (`deny`/`allow`, scopes) | `skill_policies.py`, `test_skill_policies`, integration denial trace test |
| CLI policy diagnostics (no raw JSON default) | `cli_skills.py`, `cli_skills_presenters.py`, `tests/e2e/test_cli_skills_commands.py` |
| Structured telemetry (F7) | `skill_events.py`, `tests/unit/runtime/test_skill_events.py`, `test_skill_telemetry_emits_retrieval_flow_events` |

## Explicitly deferred (not MVP-blocking)

- Trigger-quality / under-over-trigger heuristics and rich “doctor” templates (architecture §20 authoring) — optional backlog; not required for SI-007 retrieval MVP closure.
- TUI parity for skills commands — CLI only for MVP (`AGENTS.md` / plan Phase 6).
- Zip/import-export and org distribution (Phase 9).

## Related paths

- Plan: `.ai/PLANS/005-skills-system-implementation.md`
- Post-MVP **distribution** (bundle format, import/export — not retrieval MVP): `docs/dev/backlog/skills-distribution-packaging.md` (roadmap **SI-008**, backlog **BL-007**)
- PRD: `.ai/SPECS/002-skills-system/PRD.md`
- Architecture: `.ai/SPECS/002-skills-system/SKILLS_ARCHITECTURE.md`
