---
owner: "@team"
last_updated: "2026-02-17"
status: "archived"
source_of_truth: false
---

# Memory Phase 7 Baseline vs Post-Migration Metrics

Date: 2026-02-17  
Baseline source: `docs/dev/memory_m0_baseline_2026-02-16.md`  
Post-migration source: `docs/dev/memory_phase7_metrics_post_2026-02-17.json`

## Comparison

| Metric | M0 Baseline | Phase 7 Post | Notes |
|---|---:|---:|---|
| Memory retrieval hit rate | 1.000 | 1.000 | Maintained. |
| Policy-denied memory write count | 4 (harness aggregate) | 1 (sample run) | Post value is per-snapshot sample workload. |
| Write counts | N/A | 1 | Newly instrumented runtime counter. |
| Retrieval hits | N/A | 3 | Newly instrumented runtime counter. |
| Consolidation drift indicator | N/A | 0.000 | Newly instrumented (`skipped/proposed`). |
| Consolidation runs | N/A | 1 | Newly instrumented runtime counter. |
| Per-subdomain read/write rates | N/A | available | Newly instrumented for `persona_core`, `user_profile`, `working_rules`, `task_memory`. |
| `last_verified` freshness distribution | N/A | available | Newly instrumented bucket distribution. |

## How to Reproduce

1. Generate post snapshot:
   - `just memory-metrics-snapshot`
2. Re-run migration eval gates:
   - `just memory-migration-gates`

## Interpretation

- Phase 7 introduces explicit memory observability counters and keeps prior baseline quality signals stable.
- Post snapshot is deterministic for the scripted sample workload and is intended for migration go/no-go comparisons.
