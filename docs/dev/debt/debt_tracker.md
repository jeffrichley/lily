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

## Recently Closed Debt

- [x] [DEBT-021] **Closed 2026-03-26:** Added test-time guardrails to prevent accidental paid-provider usage. Default pytest runs now block outbound sockets and `init_chat_model` calls from `tests/conftest.py`, require explicit `@pytest.mark.allows_network` opt-in for live paths, register marker policy in `pyproject.toml`, and include sentinel coverage in `tests/unit/runtime/test_test_guardrails.py`.
- [x] [DEBT-019] **Closed 2026-03-26:** Root cause identified as MCP transport mismatch: `gitmcp` emits SSE `event: endpoint` while Lily default config used `streamable_http` handler expecting `message` events. Lily now supports `sse`, `stdio`, and `websocket` transports in runtime schema/provider wiring; default `langgraph_docs` config switched to `sse`; MCP provider construction refactored to strategy/registry dispatch in `src/lily/runtime/tool_resolvers.py`. Coverage added in `tests/unit/runtime/test_config_loader.py` and `tests/unit/runtime/test_tool_resolvers.py`; transport docs updated in `docs/dev/references/runtime-config-and-interfaces.md`.
- [x] [DEBT-020] **Closed 2026-03-26:** Secret scanning enforcement now uses git-hook + server-side gates. Local commit workflow doc (`.ai/COMMANDS/commit.md`) requires hook install (`just pre-commit-install`) and gitleaks verification (`uv run pre-commit run gitleaks --all-files`). Added push/PR secret scan workflow (`.github/workflows/secret-scan.yml`) so merges can be blocked via required status checks even when local hooks are missing.
- [x] [DEBT-018] **Closed 2026-03-26:** `[logging].level` now drives `configure_lily_package_logging()` on the stdlib logger `lily` from `LilySupervisor.from_config_paths` (`src/lily/runtime/logging_setup.py`, `src/lily/agents/lily_supervisor.py`). `lily.skill.telemetry` remains explicitly INFO when skill handlers attach so F7 JSONL still writes under ERROR package level. Reference doc updated: `docs/dev/references/runtime-config-and-interfaces.md` §`logging`; `LoggingConfig.level` field description in `config_schema.py`. Tests: `tests/unit/runtime/test_logging_setup.py`.
