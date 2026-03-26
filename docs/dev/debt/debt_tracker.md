---
owner: "@jeffrichley"
last_updated: "2026-03-26"
status: "active"
source_of_truth: true
---

# Lily Debt Tracker

## Active Debt

### P1

- None.

### P2

- None.

### P3

- [ ] [DEBT-017] Remove `pip-audit --ignore-vuln CVE-2026-4539` from `justfile` `audit` when `pygments` publishes a version fixing CVE-2026-4539 on PyPI (currently no release >2.19.2).

- [ ] [DEBT-019] Do not mask stderr output `Unknown SSE event: endpoint` when using MCP `streamable_http` tools (e.g. `langgraph_docs` in default `.lily/config`). We need to figure out why this event is being produced/parsed. **Remediation:** Reproduce with minimal MCP config; capture raw SSE frames/events and current adapter-side parsing expectations; identify whether the server emits an unexpected event type or the adapter mis-maps it; then fix at the correct layer (Lily boundary vs upstream dependency). Open/track upstream issue if it’s a spec/implementation mismatch.

- [ ] [DEBT-020] Ensure secret scanning actually runs as a required gate when committing, so API keys can’t be committed. This should work like a “presubmit” gate (Google-style): `git commit` must fail fast if gitleaks/pre-commit detects secrets. **Remediation:** Verify `gitleaks` is enforced via the actual git hook path used locally (either via `pre-commit` installed as a hook, and/or by making `.ai/COMMANDS/commit.md` run `just secrets-check` before creating the commit). Also ensure CI keeps blocking merges on secret findings (current `just quality-check` includes `secrets-check`). Document the exact enforcement mechanism and required developer setup steps.

## Recently Closed Debt

- [x] [DEBT-018] **Closed 2026-03-26:** `[logging].level` now drives `configure_lily_package_logging()` on the stdlib logger `lily` from `LilySupervisor.from_config_paths` (`src/lily/runtime/logging_setup.py`, `src/lily/agents/lily_supervisor.py`). `lily.skill.telemetry` remains explicitly INFO when skill handlers attach so F7 JSONL still writes under ERROR package level. Reference doc updated: `docs/dev/references/runtime-config-and-interfaces.md` §`logging`; `LoggingConfig.level` field description in `config_schema.py`. Tests: `tests/unit/runtime/test_logging_setup.py`.
