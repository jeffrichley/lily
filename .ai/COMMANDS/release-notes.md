---
description: "Generate lightweight release notes from commits and plans"
argument-hint: [optional-range-or-tag]
---

# Release Notes: Lightweight Changelog Summary

## Objective

Create concise release notes for tagged or batched work using commit history, plan files, and validation evidence.

## Inputs

- Optional commit range/tag (examples):
  - `v0.3.0..HEAD`
  - `HEAD~10..HEAD`
  - `main..feature-branch`
- If omitted, summarize unreleased commits on current branch.

## Process

### 1. Gather source material

- Commit history:
  - `git log --oneline --decorate <range>`
  - `git log --format='%h %s' <range>`
- Relevant plans and execution reports:
  - `.ai/PLANS/*.md` touched by commits or referenced in messages
- Validation highlights from executed commands (from plan `## Execution Report` when available)

### 2. Group changes by type

Use commit/plan intent to group under:
- Added
- Changed
- Fixed
- Docs/Workflow

Avoid repeating low-signal internal churn.

### 3. Capture operator/developer impact

Include:
- new commands/workflows
- behavior changes users will notice
- migration or compatibility notes (if any)
- known limitations or deferred follow-ups

### 4. Publish concise notes

Write human-readable notes suitable for PR summary, release description, or changelog append.

## Required Output Format

```markdown
## Release Notes (<version-or-range>)

### Added
- ...

### Changed
- ...

### Fixed
- ...

### Docs / Workflow
- ...

### Validation Highlights
- `command` -> `result`

### References
- .ai/PLANS/00x-*.md
- <issue/pr links if available>
```

## Quality Bar

- Notes reflect actual merged/staged work only.
- Entries are outcome-focused, not file-dump summaries.
- Language is understandable to both engineers and operators.
- Includes at least one validation highlight when available.
