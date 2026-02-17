---
owner: "@team"
last_updated: "2026-02-17"
status: "archived"
source_of_truth: false
---

# Memory Gate M0 Baseline Snapshot

Date: 2026-02-16  
Scope: baseline capture required by `docs/dev/memory_execution_plan.md` Gate M0.

## Command Contract Freeze

Frozen command contracts for migration window:
- `/remember`
- `/memory show`
- `/forget`

## Eval Baseline

Executed:
- `just eval-gates`
- `just ci-gates`

Results:
- Gate B suite (`tests/unit/evals/test_baseline.py`): `12/12` passed (`1.000` pass rate)
- Phase 7 quality suite (`tests/unit/evals/test_phase7_quality.py`):
  - personality consistency: `4/4` passed (`1.000`)
  - task effectiveness: `4/4` passed (`1.000`)
  - fun/delight: `4/4` passed (`1.000`)
  - safety redline: `9/9` passed (`1.000`)

## Observability Baseline Snapshot

Current baseline metrics (proxy capture until runtime telemetry is fully instrumented):
- average prompt/context size per turn (chars): `385.7`
- memory retrieval hit rate: `1.000`
- policy-denied memory write count: `4`

Notes:
- Prompt/context baseline uses deterministic prompt rendering across current persona fixtures.
- Retrieval and policy-denial values are derived from baseline/phase7 harness behavior used by current CI gates.
