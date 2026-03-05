---
owner: "@team"
last_updated: "2026-03-04"
status: "active"
source_of_truth: false
---

# Lily V1 Business Story (Expanded User Story)

## Fictional Business Context

Business: **Northstar Reliability Group (NRG)**  
Type: Mid-size operations and risk intelligence team  
Problem: NRG runs repeated investigation and reporting workflows that are slow, inconsistent, and hard to audit when done manually.

## Business Need

NRG needs one assistant platform that can:

- execute repeatable workflows on schedule,
- run specialist skills and tools safely,
- preserve clear execution identity and audit trail,
- produce deterministic, inspectable outputs for compliance and leadership review.

## Expanded User Story

As an operations lead at NRG,  
I want Lily to route requests, run skills/tools, execute workflows, and preserve run evidence with clear authority boundaries,  
so that my team can automate recurring intelligence work without losing reliability, safety, or auditability.

## What \"Fully Functional Lily V1\" Means For This Business

1. **Operational execution**
- An operator can issue commands from CLI and get deterministic outcomes.
- Jobs can run manually or on schedule and produce run artifacts.

2. **Skill/tool execution**
- Lily can invoke skills and their required tools through a controlled provider path.
- Security approvals and policy checks protect risky plugin execution.

3. **Authority model**
- Runtime execution identity (`active_agent`) is explicit and separate from persona/style context.
- Execution decisions can be traced to the acting agent context.

4. **Workflow and blueprint coverage**
- Jobs can execute blueprint-backed workflows with stable receipts and event trails.

5. **Future complete orchestration**
- Supervisor/subagent delegation exists with typed handoffs and deterministic gate outcomes.
- This is the missing capability that upgrades Lily from strong subsystem platform to full orchestration product.

## How Lily Solves The Need Today

NRG can already use Lily for:

- command-driven skill invocation,
- secured plugin execution,
- scheduled workflow runs via jobs,
- artifact-based operational auditing.

This already reduces manual toil and improves consistency for recurring work.

## What Is Still Blocking Full Business Outcome

NRG cannot yet run a true multi-agent delegated orchestration flow in one runtime path.

Missing pieces:

- supervisor runtime,
- subagent handoff contracts,
- delegation routing/gate outcomes persisted as first-class run semantics.

Without those, Lily is operationally useful but not yet the complete \"agentic operations fabric\" described in long-term ideas/specs.

## V1 Operating Principle

For NRG, Lily V1 should prioritize:

- deterministic execution over novelty,
- auditability over flexibility,
- explicit capability boundaries over broad but partial feature claims.

## Scope Control Rule

Any proposed work item must map to an open capability in:

- `docs/dev/references/capability-ledger.md`

If it does not, it is deferred.
