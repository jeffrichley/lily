---
owner: "@team"
last_updated: "2026-02-18"
status: "active"
source_of_truth: true
---

# Blueprints + Jobs Architecture V0

Status: Proposed  
Date: 2026-02-18  
Scope: architecture for blueprint-driven orchestration and job-based execution.

## 1. Architecture Goals

- Make new workflows mostly configuration, not custom wiring.
- Keep execution deterministic, auditable, and policy-enforced.
- Preserve extensibility without controller complexity growth.

## 2. Runtime Topology

`Director -> Job Runner -> Blueprint Registry -> Blueprint Compiler -> Execution Graph -> Runnables/Tools -> Artifacts`

Control plane:
- selects runnable target and bindings.
- validates contract and policy gates.

Data plane:
- executes graph steps.
- emits events/artifacts/receipts.

## 3. Core Components

- `BlueprintRegistry`: stable id-to-blueprint resolution.
- `BlueprintCompiler`: turns blueprint + bindings into executable graph.
- `JobRepository`: loads/validates job specs.
- `JobScheduler`: triggers manual/cron job execution.
- `RunExecutor`: executes with timeout/retry/resource boundaries.
- `ArtifactWriter`: writes receipts/events/outputs.
- `PolicyGate`: capability/approval enforcement before side effects.

## 4. Canonical Flows

## 4.1 Manual Run

1. `jobs run <id>`
2. load + validate job spec
3. resolve blueprint target
4. validate bindings
5. compile graph
6. execute
7. persist artifacts + receipt
8. render structured summary

## 4.2 Cron Run

1. scheduler evaluates trigger window
2. enqueue job run request
3. execute via same path as manual run
4. persist artifacts + receipt
5. emit terminal/ops summary

## 5. Contract Boundaries

- Spec validation boundary: before compile.
- Compile boundary: before execution.
- Policy boundary: before side effects.
- Output boundary: before receipt/artifact finalization.

No boundary may be skipped by any execution path.

## 6. Security Boundaries

- Skills/platform capability checks are enforced in graph step execution.
- Side-effecting operations remain hard-denied or HITL-gated per policy.
- All denials and suspicious paths log high-visibility structured events.

## 7. Storage Layout

- Job specs: `.lily/jobs/*.job.yaml` (proposed location).
- Run artifacts: `.lily/runs/<job_id>/<timestamp>/...`
- Security approvals/provenance: `.lily/db/security.sqlite` (existing V1 decision).

## 8. Extensibility Model

Additions should be registration-based:
- register new blueprint id in registry.
- define typed bindings/input/output schemas.
- keep Run Contract R0 unchanged.

This prevents large conditional branching in core execution code.

## 9. Risks and Mitigations

- Risk: compile/runtime drift between job and blueprint versions.
  Mitigation: explicit version pinning and deterministic contract checks.
- Risk: hidden side effects in graph steps.
  Mitigation: mandatory policy boundary and approval checkpoints.
- Risk: artifact sprawl.
  Mitigation: retention and rotation policy (to be defined in jobs plan).

