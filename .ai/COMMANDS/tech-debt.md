---
description: "Analyze codebase and update the canonical technical debt ledger"
argument-hint: [optional-scope-path-or-plan]
---

# Technical Debt: Analyze and Update Ledger

## Objective

Identify, prioritize, and document technical debt in one canonical file:
- `.ai/TECHNICAL_DEBT.md`

This command should update that file directly with concrete, actionable debt items.

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

Write updates only in `.ai/TECHNICAL_DEBT.md` using its template.

Rules:
- Keep IDs stable (`TD-001`, `TD-002`, ...).
- Do not duplicate equivalent debt; merge evidence into existing entries.
- Update `## All Debt Index (ID Order)` on every change.
- Keep `## All Debt Index (ID Order)` sorted by ID ascending.
- Ensure index rows include priority/severity (`P0`..`P3`) and match entry metadata.
- Place entries into status-specific sections:
  - `## Open`
  - `## In Progress`
  - `## Blocked`
  - `## Resolved`
- Move resolved items to `## Resolved` with resolution note/date.
- Within each status section, sort by:
  1. Priority (`P0` -> `P1` -> `P2` -> `P3`)
  2. ID ascending

## Required Output

Provide concise summary:
- new items added
- existing items updated
- items resolved
- highest-priority open debt

## Quality Bar

- Every open debt item has concrete evidence and remediation steps.
- No vague entries without impact or owner.
- Ledger remains readable with clear status sections and priority sorting within each section.
- `## All Debt Index (ID Order)` matches section entries and date fields.
- `## All Debt Index (ID Order)` includes accurate priority/severity for each item.
