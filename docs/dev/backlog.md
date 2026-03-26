---
owner: "@jeffrichley"
last_updated: "2026-03-26"
status: "active"
source_of_truth: true
---

# Dev Backlog

Track upcoming work items that are not yet in an active implementation plan.

**Deep specs (backlog-owned):** `docs/dev/backlog/skills-distribution-packaging.md` (**BL-007** / **SI-008**).

## User-visible Features

| ID | Item | Priority | Status | Notes |
|---|---|---:|---|---|
| None | None. | - | - | - |

## Internal Engineering Tasks

| ID | Item | Priority | Status | Notes |
|---|---|---:|---|---|
| BL-001 | Add conversation compression/summarization policy to reduce token use while preserving long-session context continuity. | 4 | Open | Trigger by token/message threshold, summarize older turns, keep recent turns verbatim, persist summary with session metadata. |
| BL-002 | Experiment with LangChain middleware strategies for system-prompt skill injection. | 3 | Open | Compare prompt injection approaches (middleware vs pre-chain prompt shaping) for determinism and maintainability. |
| BL-004 | Defer playbook/procedural/agent “execution adapters” for skills until after retrieval-only SKILL.md injection. | 4 | Open | Skills in MVP are context/retrieval artifacts only; no autonomous execution modes. |
| BL-007 | Implement **SI-008** skills distribution (bundle verify/import/export, optional API) per `docs/dev/backlog/skills-distribution-packaging.md`. | 3 | Open | Spec lives under backlog, not `.ai/PLANS/`; code TBD. |
| BL-008 | Add sub-agent to sub-agent communication channels. | 3 | Open | Sourced from `.ai/SPECS/008-named-agents-and-identity-context/PRD.md` future considerations. |
| BL-009 | Create agent capability registry and delegation rules. | 3 | Open | Sourced from `.ai/SPECS/008-named-agents-and-identity-context/PRD.md` future considerations. |
| BL-010 | Add agent lifecycle commands (`init`, `clone`, `archive`). | 3 | Open | Sourced from `.ai/SPECS/008-named-agents-and-identity-context/PRD.md` future considerations. |
