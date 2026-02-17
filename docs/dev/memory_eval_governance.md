# Memory Eval Governance

Purpose: define eval lanes and review cadence for memory migration quality control.

## Eval Lanes

- Regression lane (frozen contracts):
  - `just eval-regression`
  - includes:
    - `tests/unit/evals/test_baseline.py`
    - `tests/unit/evals/test_phase7_quality.py`
- Capability lane (new memory behavior):
  - `just eval-capability`
  - includes:
    - `tests/unit/evals/test_memory_migration_quality.py`

## CI Gate

- Memory migration gate:
  - `just memory-migration-gates`
  - runs static quality + regression lane + capability lane

## Multi-Trial Policy

- For stochastic-sensitive cases, run multiple trials and enforce pass-rate threshold.
- Current policy:
  - minimum trials: 3
  - required pass-rate: 1.0 for deterministic fixtures
- When real model-backed stochastic evals are enabled:
  - raise trials to 5-10
  - require threshold >= 0.9

## Transcript Review Cadence

- Weekly:
  - sample 10 eval transcripts from capability lane
  - review drift and false pass/fail indicators
- Per release:
  - review all failed eval transcripts before merge
- Monthly:
  - calibrate cases and thresholds; add/remove cases based on incident patterns
