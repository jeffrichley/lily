# Plan Authoring Reference

Purpose: keep plans implementation-ready and phase-scoped before coding starts.

## Required Plan Skeleton

- feature header and problem/solution framing
- `## Branch Setup` with executable branch commands
- `## Implementation Plan` with markdown checkboxes
- per-phase intent locks (source of truth, must, must-not, acceptance gates)
- `## Required Tests and Gates`
- `## Definition of Visible Done` for user-observable changes
- `## Execution Report` (append as phases complete)

## Phase Intent Lock Checklist

For each phase, define explicitly:
- acceptance criteria
- non-goals
- required tests/gates
- authoritative source docs/files

## Scope Control

- treat phase scope as fixed once intent is locked
- if requirements change, add `## Plan Patch` before implementing new scope

## Evidence Discipline

In execution report entries, include:
- command run
- pass/fail outcome
- key output artifact/surface verified

## Anti-Patterns

- broad implementation without locked acceptance gates
- deferred checklist updates until end of feature
- missing evidence for claimed completion
