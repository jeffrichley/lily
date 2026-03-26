# Feature: Skills PRD + Architecture Documentation

This plan defines the work to produce a deep, standards-aligned PRD and architecture spec for Lily skills using official OpenAI, LangChain, and Anthropic guidance.

## Feature Description

Create two durable specification artifacts for the skills system:
- a product requirements document (PRD)
- a skills architecture document with concrete build design, interfaces, lifecycle, and GoF pattern mapping

Both artifacts must be grounded in current official ecosystem guidance and aligned to Lily's current runtime boundaries.

## User Story

As the Lily maintainer
I want a full PRD and architecture document for skills
So that I can review a concrete, implementation-ready design before coding SI-007.

## Problem Statement

Skills direction currently exists across ideas/reference docs, but there is no single, implementation-grade pair of artifacts that consolidates external standards and defines a clear Lily build contract.

## Solution Statement

Research canonical external sources, synthesize them with current Lily docs/runtime constraints, and publish two deep spec files under `.ai/SPECS/002-skills-system/`.

## Feature Metadata

**Feature Type**: Documentation/specification (internal system improvement planning)  
**Estimated Complexity**: Medium  
**Primary Systems Affected**:
- `.ai/SPECS/` (new spec package)
- `.ai/PLANS/` (this plan and execution report)
- optional status surfaces if current focus wording needs sync
**Dependencies**:
- Official OpenAI Codex skills docs
- Official LangChain multi-agent/deep agents skills docs
- Anthropic official skills guidance

## Traceability Mapping (Required When Applicable)

- Roadmap system improvements: `SI-007`
- Debt items: `None`
- Debt to roadmap linkage (if debt exists): `N/A`

## Branch Setup (Required)

Branch naming must follow the plan filename:
- Plan: `.ai/PLANS/004-skills-prd-architecture.md`
- Branch: `feat/004-skills-prd-architecture`

Commands (must be executable as written):
```bash
PLAN_FILE=".ai/PLANS/004-skills-prd-architecture.md"
PLAN_SLUG="$(basename "$PLAN_FILE" .md)"
BRANCH_NAME="feat/${PLAN_SLUG}"
git show-ref --verify --quiet "refs/heads/${BRANCH_NAME}" \
  && git switch "${BRANCH_NAME}" \
  || git switch -c "${BRANCH_NAME}"
```

---

## Definition of Visible Done

Human-verifiable outputs:
- Open `.ai/SPECS/002-skills-system/PRD.md` and review full skills PRD.
- Open `.ai/SPECS/002-skills-system/SKILLS_ARCHITECTURE.md` and review architecture design + GoF section.
- Verify docs metadata checks pass:
  - `just docs-check`
  - `just status`

## Input Provenance

- Pre-existing local sources:
  - `docs/dev/*.md`
  - `docs/ideas/*.md`
- External official sources gathered during this task:
  - OpenAI Codex skills docs
  - LangChain skills and multi-agent docs
  - Anthropic skills guidance

## Implementation Plan

- [x] Phase 1: Source collection and synthesis baseline
- [x] Phase 2: Draft comprehensive Skills PRD
- [x] Phase 3: Draft Skills Architecture document (including GoF patterns)
- [x] Phase 4: Validate docs surfaces and finalize

### Phase 1: Source collection and synthesis baseline

**Intent Lock**
- Source of truth:
  - `docs/dev/roadmap.md` (`SI-007`)
  - `docs/dev/references/runtime-config-and-interfaces.md` (current runtime boundaries)
  - official external docs listed in this plan
- Must:
  - use official vendor/framework sources as primary references
  - capture constraints already true in Lily runtime
- Must Not:
  - rely on non-official secondary summaries as primary design authority
  - propose features that contradict current documented runtime contracts without explicit note
- Provenance map:
  - each major requirement in PRD/architecture must map to at least one cited source
- Acceptance gates:
  - source list and extracted notes are complete enough to draft both docs without placeholders

### Phase 2: Draft comprehensive Skills PRD

**Intent Lock**
- Source of truth:
  - `.ai/COMMANDS/create-prd.md` required sections
  - Phase 1 research notes
- Must:
  - include full PRD sections with clear scope, metrics, phases, risks
  - distinguish in-scope MVP vs deferred evolution
- Must Not:
  - imply skills runtime is already implemented
  - mix temporary compatibility ideas as complete state
- Provenance map:
  - PRD goals and requirements trace to SI-007 + external standards
- Acceptance gates:
  - PRD exists at `.ai/SPECS/002-skills-system/PRD.md`
  - all required PRD sections present

### Phase 3: Draft Skills Architecture document (including GoF patterns)

**Intent Lock**
- Source of truth:
  - Phase 1 research notes
  - current Lily runtime boundaries and config contracts
- Must:
  - define component boundaries, contracts, lifecycle, and decision logic
  - include explicit GoF patterns section with pattern-to-component mapping
- Must Not:
  - leave core contracts ambiguous (registry interfaces, skill package format, selection rules)
  - collapse skills/subagents/tools into one undefined abstraction
- Provenance map:
  - architecture decisions trace to official docs plus Lily constraints
- Acceptance gates:
  - architecture doc exists at `.ai/SPECS/002-skills-system/SKILLS_ARCHITECTURE.md`
  - GoF section is complete and specific

### Phase 4: Validate docs surfaces and finalize

**Intent Lock**
- Source of truth:
  - `.ai/COMMANDS/status-sync.md`
  - `.ai/RULES.md` docs hygiene requirements
- Must:
  - run docs validation commands
  - update plan checkboxes and append execution report
- Must Not:
  - leave stale status metadata after substantial docs changes
- Provenance map:
  - reported validation outcomes come directly from command results
- Acceptance gates:
  - `just docs-check` passes
  - `just status` executes successfully

## Step-by-Step Tasks

1. Execute branch setup commands from this plan.
2. Collect and normalize source notes from official external docs and local docs/ideas.
3. Create `.ai/SPECS/002-skills-system/PRD.md` with full PRD sections.
4. Create `.ai/SPECS/002-skills-system/SKILLS_ARCHITECTURE.md` with deep technical design and GoF mapping.
5. Run `just docs-check`.
6. Run `just status`.
7. Mark all plan phases complete and append execution evidence.

## Execution Report

### Completion Status

- Completed: all planned phases and tasks.

### Artifacts Created

- `.ai/SPECS/002-skills-system/PRD.md`
- `.ai/SPECS/002-skills-system/SKILLS_ARCHITECTURE.md`

### Commands Run and Outcomes

- `just docs-check` -> pass
- `just status` -> pass

### Acceptance Gate Evidence

- Phase 1:
  - Completed source synthesis from official OpenAI, LangChain, Anthropic, and Agent Skills specification pages.
  - Incorporated Lily runtime boundaries from `docs/dev/references/runtime-config-and-interfaces.md`.
- Phase 2:
  - PRD created with all required sections and explicit SI-007 scope/defer boundaries.
- Phase 3:
  - Architecture doc created with detailed lifecycle, contracts, and GoF pattern mapping.
- Phase 4:
  - Docs validation and status checks both passed.

### Partial/Blocked Items

- None.
