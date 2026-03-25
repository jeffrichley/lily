---
owner: "@jeffrichley"
last_updated: "2026-03-02"
status: "active"
source_of_truth: false
---

# [Debt][P1] Add pre-execution language restriction layer (RestrictedPython or equivalent AST policy)

## Source
- Debt tracker: `docs/dev/debt/debt_tracker.md` (Active Debt → P1)

## Internal engineering tasks
- Implement deterministic pre-execution restriction for plugin code.
- Stabilize denial codes/messages and cover them with tests.
- Document layered security model: language restriction + container isolation.

## User-visible features
- None.

## Acceptance criteria
- A deterministic pre-execution restriction layer is active for plugin code.
- Denial codes/messages are stable and test-covered.
- Docs explicitly describe the layered security model.

## Non-goals
- Replacing container isolation boundary.
- Shipping a full sandbox redesign.

## Required tests and gates
- Security-focused unit tests for deny/allow behavior.
- Contract/integration tests for stable denial envelopes.
- `just quality test` warning-clean.

## Metadata
- Priority: `P1`
- Owner: `@jeffrichley`
- Target: `2026-03-08`
