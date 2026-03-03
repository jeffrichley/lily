# Project Type: CLI Tool

Use this overlay when working on Lily command UX, output rendering, and operator workflows.

## Output UX Rules

- default interactive output should be Rich-rendered (tables/panels)
- avoid raw JSON as default interactive output
- use explicit JSON mode only when requested by contract/flag

## Command Behavior Rules

- deterministic success/failure envelopes for command flows
- explicit validation errors for malformed inputs
- no silent fallback defaults for required command fields

## Validation Expectations

Before commit/PR handoff for CLI-affecting changes:
- `just lint`
- `just format-check`
- `just types`
- `just docs-check`
- `just test`
- `just quality && just test`

## Documentation Expectations

If user-visible CLI behavior changes:
- update authoritative docs in the same change
- ensure `just status` remains accurate for operator surfaces
