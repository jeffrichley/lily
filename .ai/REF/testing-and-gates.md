# Testing and Gates Reference

Purpose: define when to run fast checks vs full gates, and how to handle warnings.

## Baseline Loop (development)

Run for meaningful local changes:
- `just lint`
- `just format-check`
- `just types`
- `just docs-check`
- `just test`

## Final Gate (pre-commit / pre-PR)

Required:
- `just quality && just test`

## Warning Policy

- treat warnings as defects by default
- fix warnings when feasible in the same change
- if unavoidable, document:
  - exact warning signature
  - reason it remains
  - owner + target date for removal

## Failure Handling

- if a command fails:
  1. fix root cause
  2. re-run failed command
  3. continue only on pass

- do not claim completion with known failing validation unless user explicitly accepts risk
