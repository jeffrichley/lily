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

- [ ] [DEBT-019] Eliminate or downgrade stderr noise `Unknown SSE event: endpoint` when using MCP `streamable_http` tools (e.g. `langgraph_docs` in default `.lily/config`). Likely upstream SSE event type handling in `langchain-mcp-adapters` / MCP client vs server. **Remediation:** Reproduce with minimal MCP config; upgrade dependency or filter log at Lily boundary; open/track upstream issue if spec mismatch.

- [ ] [DEBT-020] Reduce redundant work in CI: `just quality-check` includes `secrets-check` (gitleaks via pre-commit), and the matrix runs **ubuntu, macos, windows** — gitleaks is downloaded and run three times per push. **Remediation:** Optional split workflow: one `ubuntu-latest` job for `secrets-check` only, and keep `quality-check` without `secrets-check` in the matrix (or run gitleaks once at end of ubuntu job only), while preserving local `just quality-check` unchanged.

## Recently Closed Debt

- [x] [DEBT-018] **Closed 2026-03-26:** `[logging].level` now drives `configure_lily_package_logging()` on the stdlib logger `lily` from `LilySupervisor.from_config_paths` (`src/lily/runtime/logging_setup.py`, `src/lily/agents/lily_supervisor.py`). `lily.skill.telemetry` remains explicitly INFO when skill handlers attach so F7 JSONL still writes under ERROR package level. Reference doc updated: `docs/dev/references/runtime-config-and-interfaces.md` §`logging`; `LoggingConfig.level` field description in `config_schema.py`. Tests: `tests/unit/runtime/test_logging_setup.py`.
