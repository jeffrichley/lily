---
description: "Create a concise next-agent/human handoff summary for continuity"
argument-hint: [optional-plan-path]
---

# Handoff: Session Continuity Summary

## Objective

Create a concise, high-signal handoff so the next agent/human can continue work without re-discovery.

## Inputs

- Optional: active plan path (for example `.ai/PLANS/007-some-feature.md`)
- Current git state and validation outcomes

## Process

### 1. Gather current state

- `git status --short`
- `git log --oneline --decorate -n 10`
- `just status`
- active plan `## Implementation Plan`, `## Plan Patch` (if any), `## Execution Report` (if any)
- most recent validation results from `.ai/COMMANDS/validate.md`

### 2. Produce concise handoff

Required sections:
- What changed
- What is complete
- What is pending
- Blockers / risks
- Exact next commands

Keep the handoff concrete and short. Include file paths and command lines.

## Required Handoff Template

```markdown
## Handoff Summary

### Completed
- ...

### Pending
- ...

### Blockers / Risks
- ...

### Changed Files
- `path/to/file`
- `path/to/file`

### Validation Status
- `command` -> `pass/fail`

### Next Commands
1. `command`
2. `command`
3. `command`
```

## Quality Bar

- No vague statements ("some stuff", "misc fixes").
- Includes explicit next executable commands.
- Reflects actual repo state (git + validation).
