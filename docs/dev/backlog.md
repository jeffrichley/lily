---
owner: "@jeffrichley"
last_updated: "2026-03-25"
status: "active"
source_of_truth: true
---

# Dev Backlog

Track upcoming work items that are not yet in an active implementation plan.

## User-visible Features

| ID | Item | Priority | Status | Notes |
|---|---|---:|---|---|
| None | None. | - | - | - |

## Internal Engineering Tasks

| ID | Item | Priority | Status | Notes |
|---|---|---:|---|---|
| BL-001 | Add conversation compression/summarization policy to reduce token use while preserving long-session context continuity. | 4 | Open | Trigger by token/message threshold, summarize older turns, keep recent turns verbatim, persist summary with session metadata. |
| BL-002 | Experiment with LangChain middleware strategies for system-prompt skill injection. | 3 | Open | Compare prompt injection approaches (middleware vs pre-chain prompt shaping) for determinism and maintainability. |
| BL-003 | Defer `$skill:<id>` explicit invocation + deterministic selection/ranking until after MVP retrieval-only. | 4 | Open | MVP uses tool-based retrieval by skill name; explicit invocation and ranking remain backlog. |
| BL-004 | Defer playbook/procedural/agent “execution adapters” for skills until after retrieval-only SKILL.md injection. | 4 | Open | Skills in MVP are context/retrieval artifacts only; no autonomous execution modes. |
| BL-006 | Add trigger-test / under-over-trigger heuristics and richer `lily skills doctor` authoring guidance (architecture §20). | 3 | Open | Explicitly deferred from SI-007 retrieval MVP; not required for MVP closure. |
| BL-007 | Implement SI-007 Phase 9 skills distribution (zip/import-export, org rollout) per `.ai/PLANS/005-skills-system-implementation.md`. | 3 | Open | Post-MVP; tracked in-plan Phase 9. |

