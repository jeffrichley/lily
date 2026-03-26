---
description: Create or update a library documentation skill package
argument-hint: [library-name-or-url]
---

# Library Skill: Generate Library Doctrine Skill Docs

## Objective

Run a two-stage workflow:
1. Research and document findings outside `.agents/skills`.
2. Pass findings to `$skill-creator` to generate a new library expert skill under `.agents/skills/<library-skill>/`.

This workflow creates skill artifacts, not runtime product code.

## Inputs

- Library name and/or URL: `$ARGUMENTS`
- Optional version (ask if needed)

## Required Behavior

- If version is not provided, default to latest stable release.
- If available, include both official docs site and upstream git repository references.
- If cloning open-source code for analysis:
  - clone only into isolated temporary workspace,
  - do not execute untrusted code,
  - delete temporary clone workspace after analysis.
- Require a fresh-agent verification pass before marking output approved.

## Output Location

Stage 1 output (required, outside `.agents/skills`):
- `.ai/SPECS/<NNN>-<feature>/research/sources.md`
- `.ai/SPECS/<NNN>-<feature>/research/version_scope.md`
- `.ai/SPECS/<NNN>-<feature>/research/best_practices.md`
- `.ai/SPECS/<NNN>-<feature>/research/anti_patterns.md`
- `.ai/SPECS/<NNN>-<feature>/research/examples_good_bad.md`
- `.ai/SPECS/<NNN>-<feature>/research/verification.md`
- `.ai/SPECS/<NNN>-<feature>/research/skill_creator_handoff.md`

Stage 2 output (required, final generated skill):
- `.agents/skills/<library-skill>/SKILL.md`
- `.agents/skills/<library-skill>/references/sources.md`
- `.agents/skills/<library-skill>/references/version_scope.md`
- `.agents/skills/<library-skill>/references/best_practices.md`
- `.agents/skills/<library-skill>/references/anti_patterns.md`
- `.agents/skills/<library-skill>/references/examples_good_bad.md`
- `.agents/skills/<library-skill>/references/verification.md`
- `.agents/skills/<library-skill>/agents/openai.yaml` (recommended)

## Invocation Pattern

1. Ensure the skill exists at:
- `.agents/skills/library-doc-researcher/SKILL.md`

2. Invoke the skill in the agent session:
- `$library-doc-researcher`

3. Provide target library details and target skill name.
4. Produce research bundle in:
- `.ai/SPECS/<NNN>-<feature>/research/`
5. Pass the full research bundle to:
- `$skill-creator`
6. Write final generated skill files to `.agents/skills/<library-skill>/`.
7. If `$skill-creator` is unavailable, stop and report blocked. Do not finalize.

## Completion Criteria

- Research bundle exists under `.ai/SPECS/<NNN>-<feature>/research/`.
- `skill_creator_handoff.md` exists under `.ai/SPECS/<NNN>-<feature>/research/`.
- New generated skill exists in `.agents/skills/<library-skill>/`.
- Citations include official docs and upstream repo when available.
- Version policy is documented (latest stable fallback when omitted).
- `$skill-creator` packaging pass is completed.
- Fresh-agent verification notes are present.
- Temporary clone cleanup is documented when cloning was used.
