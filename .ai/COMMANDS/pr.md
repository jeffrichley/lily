---
description: "Prepare PR title/body from commits, plan, and validation evidence"
argument-hint: [optional-plan-path]
---

# PR: Prepare High-Signal Pull Request

## Objective

Create or update a pull request with a clear title/body that explains what changed, why, and how it was validated.

Reference guidance:
- `.ai/COMMANDS/_shared/story-writing.md`
- `.ai/COMMANDS/_shared/review-checklist.md`

## Process

### 1. Collect PR inputs

- Commit history on branch:
  - `git log --oneline origin/main..HEAD`
- Active plan and execution evidence:
  - `.ai/PLANS/...` including `## Execution Report`
- Validation evidence from `.ai/COMMANDS/validate.md`

### 2. Build PR title

- Keep title specific and outcome-oriented.
- Prefer alignment with dominant commit intent.

### 3. Build PR body

Include:
- Summary (what changed)
- Why (problem/value)
- Validation (commands + outcomes)
- Risks / rollback notes
- References (plans/issues)

### 4. Enforce PR template usage

If available, use repository template:
- `.github/pull_request_template.md`
- `.github/PULL_REQUEST_TEMPLATE.md`
- `.github/PULL_REQUEST_TEMPLATE/*`

When template exists:
- populate all required sections with concrete content
- do not leave placeholder text

If no template exists:
- use structured fallback format below

## Fallback PR Body Format

```markdown
## Summary
- ...

## Why
- ...

## Validation
- `command` -> result
- `command` -> result

## Risks / Rollback
- ...

## References
- .ai/PLANS/00x-*.md
```

## Quality Bar

- PR body can be understood without opening the full diff first.
- Validation evidence is explicit and reproducible.
- Known risks and follow-ups are transparent.
