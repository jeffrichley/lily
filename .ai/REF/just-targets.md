# Just Targets Reference

Purpose: canonical mapping between workflow commands and real `justfile` targets.

## Core Validation Flow

- Fast loop:
  - `just lint`
  - `just format-check`
  - `just types`
  - `just docs-check`
  - `just test`

- Final gate (before commit/PR handoff):
  - `just quality && just test`

## Status and Docs Surfaces

- `just status` -> render current branch/docs/plan snapshot
- `just status-ready` -> run docs validation and status snapshot together
- `just docs-check` -> validate docs frontmatter and active-doc staleness

## CI/Quality Adjacent Targets

- `just quality-check` -> check-only equivalent of full quality lane
- `just test-cov` -> tests with coverage (coverage threshold from `pyproject.toml`)
- `just e2e` -> run end-to-end suite only

## Drift Rule

When updating any `.ai/COMMANDS/*` file that references a `just` target:
1. verify target exists in `just --list`
2. if target changed, update this file in the same change
