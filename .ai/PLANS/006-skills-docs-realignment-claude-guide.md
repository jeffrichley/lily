# Feature: SI-007 Skills Docs Realignment to Claude Guide

## Feature Description

Realign Lily skills documentation contracts to match `docs/ideas/The-Complete-Guide-to-Building-Skill-for-Claude.pdf` so Lily can consume externally-authored skills with minimal friction.

## Traceability Mapping

- Roadmap system improvements: `SI-007`
- Debt items: `None`
- No SI/DEBT mapping for this feature: `Not applicable`

## Branch Setup

```bash
PLAN_FILE=".ai/PLANS/006-skills-docs-realignment-claude-guide.md"
PLAN_SLUG="$(basename "$PLAN_FILE" .md)"
BRANCH_NAME="feat/${PLAN_SLUG}"
git show-ref --verify --quiet "refs/heads/${BRANCH_NAME}" \
  && git switch "${BRANCH_NAME}" \
  || git switch -c "${BRANCH_NAME}"
```

## Implementation Plan

- [x] Phase 1: Update SI-007 PRD contract language
  - [x] Intent Lock
    - [x] Source of truth: Claude skills PDF + `.ai/SPECS/002-skills-system/PRD.md`
    - [x] Must: require only `name` and `description` in frontmatter
    - [x] Must: clarify naming policy (`kebab-case` recommendation and normalization)
    - [x] Must: capture PDF security restrictions in explicit bullets
    - [x] Must Not: require extra metadata fields for baseline compatibility
    - [x] Acceptance gates: spec text is explicit and non-contradictory

- [x] Phase 2: Update skills architecture implementation contract
  - [x] Intent Lock
    - [x] Source of truth: Claude skills PDF + `.ai/SPECS/002-skills-system/SKILLS_ARCHITECTURE.md`
    - [x] Must: define parser/normalization behavior and compatibility mode
    - [x] Must: include full optional frontmatter field list from PDF
    - [x] Must: define strict validation/security rules matching PDF
    - [x] Must Not: introduce runtime behavior not represented in current SI-007 scope
    - [x] Acceptance gates: architecture sections map directly to PRD and PDF

- [x] Phase 3: Add tight delta checklist for execution
  - [x] Intent Lock
    - [x] Source of truth: updated SI-007 PRD + SKILLS_ARCHITECTURE
    - [x] Must: produce concise checklist with "aligned/partial/missing" closure tasks
    - [x] Must: include future distribution/packaging work as explicit deferred scope
    - [x] Must Not: leave ambiguous ownerless follow-ups
    - [x] Acceptance gates: checklist is actionable and implementation-ready

## Required Tests and Gates

- Docs consistency/readability check (manual review of contradictions)
- `just docs-check`

## Definition of Visible Done

- A reader can open SI-007 PRD and architecture docs and see:
  - only `name` and `description` are required in frontmatter;
  - naming convention and normalization policy are explicit;
  - PDF security guardrails are explicitly listed;
  - future distribution/API packaging work is explicitly documented as follow-up;
  - a tight delta checklist defines what to implement next.

## Execution Report

### Completion Status

- Completed (docs-only realignment scope).

### Artifacts Updated

- `.ai/SPECS/002-skills-system/PRD.md`
- `.ai/SPECS/002-skills-system/SKILLS_ARCHITECTURE.md`
- `.ai/PLANS/005-skills-system-implementation.md`
- `.ai/PLANS/006-skills-docs-realignment-claude-guide.md`

### What Was Realigned

- Frontmatter contract aligned to guide baseline:
  - required keys: `name`, `description`
  - optional keys documented: `license`, `compatibility`, `allowed-tools`, `metadata`
- Naming policy clarified:
  - kebab-case recommended for authoring
  - non-canonical imports accepted and normalized to internal canonical key
- Security guardrails explicitly documented:
  - reject `<` and `>` in frontmatter values
  - reject reserved `name` prefixes (`claude*`, `anthropic*`)
  - safe YAML parsing only
- Tight delta checklist added and closed to `[aligned]` by linking explicit work into implementation plan phases.
- Distribution/packaging follow-up explicitly tracked in `005` Phase 9.
- Skills tool-policy modes added to specs and plan:
  - `inherit_runtime`
  - `deny_unless_allowed`
  - `use_default_packs`
  - plus precedence/invariants and YAML/TOML config examples.

### Validation Notes

- `ReadLints` run for updated docs files: no diagnostics.

### Key Decisions / Deviations

- **Naming enforcement strategy**:
  - Decision: recommend kebab-case for skill `name` and folder naming, but do not hard-reject imported third-party non-canonical names.
  - Rationale: maximize compatibility with externally-authored skills while still converging local authoring toward a canonical convention.
  - Implementation intent: normalize non-canonical names to an internal canonical key for indexing/matching; preserve original author-facing `name` in metadata and CLI output.

- **Tool policy default behavior**:
  - Decision: make omitted `allowed-tools` behavior configurable via global policy (`inherit_runtime`, `deny_unless_allowed`, `use_default_packs`) instead of one fixed default.
  - Rationale: different deployments need different security postures (convenience-first vs least-privilege by default).
  - Implementation intent: explicit `allowed-tools` on a skill overrides default policy, and runtime/tool-registry boundaries remain the hard upper bound.
