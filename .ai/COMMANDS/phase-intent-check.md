---
description: "Lock one phase intent from plan + source docs before coding"
argument-hint: <plan-path> "<phase-heading>"
---

# Phase Intent Check: Lock Requirements Before Coding

## Objective

Lock non-negotiable intent for one implementation phase so execution remains aligned with source-of-truth docs and does not drift.

## Inputs

- Required: plan path (for example `.ai/PLANS/006-status-sync-system.md`)
- Required: phase heading exactly as written in the plan (for example `"Phase 2: Core Implementation"`)

## Process

### 1. Read the phase and sources

- Read the target phase section in the plan.
- Read `.ai/RULES.md`.
- Read all source-of-truth docs already referenced by that phase.
- If source references are missing, patch the plan before implementation.

### 2. Ensure the phase has an explicit Intent Lock

The phase must have an `Intent Lock` block that includes:

- Source of truth references (file + section)
- Must (non-negotiables)
- Must Not (forbidden shortcuts/fallbacks)
- Acceptance gates (required tests/commands)

Phase contract:
- Before implementation, each phase must have explicit acceptance criteria, explicit non-goals, and required tests/gates.
- If these are missing or ambiguous, stop and patch the plan.

### 3. Resolve ambiguity before coding

- Do not start phase tasks until the lock is specific and testable.
- If a required field/contract is unclear, add an explicit open question in the plan.
- Do not add silent fallback defaults for missing/invalid required fields.

### 4. Execution handoff constraints

- Treat `Must` and `Must Not` as binding during implementation.
- After phase completion:
  - update plan checklist state
  - run `.ai/COMMANDS/status-sync.md <plan-path>`
  - append validation evidence in plan `## Execution Report`

## Required Output

Report:

- phase locked
- source docs used
- final must/must-not summary
- exact acceptance gates to run
