---
description: "Run a delivery retrospective and codify workflow improvements"
argument-hint: [optional-plan-path-or-feature]
---

# Retro: Improve The System After Delivery

## Objective

Analyze what went well and what did not during recent implementation work, then codify improvements directly into repo guidance (`.ai/RULES.md`, `.ai/COMMANDS/*`, `.ai/REF/*`).

This command is for process hardening, not feature coding.

## Inputs

- Optional: plan file path (for example `.ai/PLANS/007-some-feature.md`)
- If no argument is provided, infer the most recent relevant plan and changed guidance files.

## Process

### 1. Gather Evidence (facts only)

- Read the executed plan(s), especially:
  - `## Implementation Plan`
  - `## Plan Patch` (if present)
  - `## Execution Report`
- Review validation outcomes and notable failures/retries.
- Review changed files from the delivery.
- Identify where agent behavior relied on assumptions vs explicit guidance.

### 2. Run Structured SWOT

Produce:
- **Strengths**: what enabled smooth delivery and should be preserved.
- **Weaknesses**: avoidable friction, ambiguity, missing guardrails.
- **Opportunities**: specific workflow/doc/template improvements.
- **Threats**: repeat failure risks if no rule/process changes are made.

Requirement: each Weakness/Opportunity/Threat must map to at least one concrete repo change.

### 3. Convert Findings Into Changes

Apply updates in this priority order:

1. `.ai/RULES.md`
- Add or refine invariants that prevent repeated failures.
- Keep rules enforceable and concise.

2. `.ai/COMMANDS/*`
- Tighten command templates (prime/plan/execute/validate/review/commit/retro).
- Remove generic or non-applicable instructions.
- Add required sections/checklists where recurring gaps were found.

3. `.ai/REF/*`
- Add deeper guidance when rules would become too verbose.
- If patterns vary by project type, create/update `.ai/REF/project-types/*`.

### 4. Compatibility and Naming Hygiene

- Detect command filename drift (for example `plan.md` vs `plan-feature.md`).
- Standardize to one canonical filename.
- Keep compatibility aliases only when needed, and document them.

### 5. Validate The Governance Changes

Minimum checks:
- Ensure referenced files actually exist.
- Ensure new required sections in command templates are present.
- Ensure AGENTS workflow references remain accurate.

## Required Deliverables

1. Updated files implementing retrospective outcomes.
2. Concise retro report (in chat) with:
- SWOT summary
- Exact files changed
- Why each change reduces future friction

## Update Rules

- Prefer small, targeted doc/rule diffs over broad rewrites.
- Do not create aspirational guidance without enforceable wording.
- If adding a new rule, also update at least one command template that operationalizes it.
- If adding a new command requirement, ensure it aligns with `.ai/RULES.md`.

## Suggested Retro Report Format

```markdown
## Retro Summary

### Strengths
- ...

### Weaknesses
- ...

### Opportunities Implemented
- ...

### Threats Mitigated
- ...

## Governance Updates Applied
- `path/to/file.md`: what changed and why
- `path/to/file.md`: what changed and why

## Residual Risks
- ...
```

