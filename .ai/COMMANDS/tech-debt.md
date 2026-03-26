---
description: "Analyze codebase and update the canonical technical debt ledger"
argument-hint: [optional-scope-path-or-plan]
---

# Technical Debt: Analyze and Update Ledger

## Objective

Identify, prioritize, and document technical debt in one canonical file:
- `docs/dev/debt/debt_tracker.md`

This command should update that file directly with concrete, actionable debt items and stable debt IDs.

## Inputs

- Optional scope path or plan reference (for focused analysis).
- If omitted, analyze repo-wide using recent changes and quality signals.

## Analysis Process

### 1. Collect evidence

Use objective sources:
- Recent diffs/commits: `git status --short`, `git log --oneline -n 20`
- Validation failures/warnings: lint, typecheck, tests, complexity/security tools
- Suppressions / TODO hotspots:
  - `rg -n \"TODO|FIXME|HACK|XXX|nosec|type: ignore|pragma: no cover\"`
- Plan and execution gaps:
  - `.ai/PLANS/*` (open checklist items, deferred patches, repeated blockers)

### 2. Classify debt

For each candidate, classify:
- Priority (`P0`..`P3`)
- Type (`architecture|testing|typing|docs|security|performance|ops|tooling|other`)
- Area/module ownership
- Impact and risk

### 3. Decide action

For each item:
- create new entry,
- update existing entry status/priority/evidence,
- or mark resolved with evidence.

### 4. Update ledger

Write updates only in `docs/dev/debt/debt_tracker.md` using its structure.

Rules:
- Keep IDs stable (`DEBT-001`, `DEBT-002`, ...).
- New open debt entries must include a unique `DEBT-XXX` token in the checkbox line.
- If the debt maps to a roadmap system improvement, include:
  - `Roadmap: SI-XXX`
- Do not duplicate equivalent debt; merge evidence into existing entries.
- Follow tracker sections (`## Active Debt` by `P1/P2/P3`, and `## Recently Closed Debt`).
- When resolving debt, move/update entry under `## Recently Closed Debt` with closure date and evidence.

## Required Output

Provide concise summary:
- new items added
- existing items updated
- items resolved
- highest-priority open debt

## Quality Bar

- Every open debt item has concrete evidence and remediation steps.
- No vague entries without impact or owner.
- Ledger remains readable with clear priority sections and deterministic ID labeling.
- `DEBT-XXX` identifiers remain unique and stable.
