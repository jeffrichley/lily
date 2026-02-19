---
owner: "@team"
last_updated: "2026-02-19"
status: "active"
source_of_truth: true
---

# Blueprints + Jobs Runbook V0

Purpose: operator runbook for creating, running, and troubleshooting blueprint-backed jobs.

## 1. Prerequisites

- Lily environment initialized.
- Skills platform security policy configured.
- Job specs stored at configured jobs path.
- Blueprint implementations follow `docs/dev/blueprint_authoring_constraints.md`.

## 2. Define a Job (Blueprint-Backed)

Minimum job fields:
- `id`
- `title`
- `target.kind=blueprint`
- `target.id`
- `bindings`
- `trigger`
- `runtime`
- `output`

Validation checklist:
- target blueprint id exists in registry.
- bindings match blueprint bindings schema.
- runtime caps are within policy limits.

## 3. Core Operator Commands

- `lily jobs list`
  - lists known jobs and high-level trigger metadata.
- `lily jobs run <job_id>`
  - executes job once immediately.
- `lily jobs tail <job_id>`
  - tails structured events for active/recent runs.

## 4. Artifact Inspection

Inspect:
- `.lily/runs/<job_id>/<timestamp>/run_receipt.json`
- `.lily/runs/<job_id>/<timestamp>/summary.md`
- `.lily/runs/<job_id>/<timestamp>/events.jsonl`

Use receipt as source of truth for:
- run status
- target and version references
- artifact index
- policy/approval outcomes

## 5. Common Failure Modes

- `job_not_found`
  - confirm id and job discovery path.
- `job_invalid_spec`
  - validate required fields and schema shape.
- `job_target_unresolved`
  - confirm blueprint is registered and version-compatible.
- `job_bindings_invalid`
  - verify field names/types against target bindings schema.
- `job_policy_denied`
  - inspect capability and approval requirements.
- `job_execution_failed`
  - inspect `events.jsonl` and target-specific artifacts.
- `blueprint_not_found`
  - confirm blueprint id is registered in blueprint registry.
- `blueprint_bindings_invalid`
  - validate bindings against blueprint `bindings_schema`.
- `blueprint_compile_failed`
  - inspect unresolved dependency ids and authoring constraints.
- `blueprint_execution_failed`
  - inspect runtime input shape and step-level failure diagnostics.

## 6. Incident Response Steps

1. Capture run id and receipt.
2. Identify first deterministic error code in events.
3. Confirm whether failure is spec, policy, or runtime.
4. Re-run with same spec after remediation.
5. If repeated, open defect with run receipt and event excerpt.

## 7. Pre-Merge Operational Checks

- run representative jobs manually.
- validate required artifact set exists.
- confirm deterministic failure behavior for at least one invalid job.
- run `just quality-check`.

## 8. Deferred Operations (Out of V0)

- distributed scheduler operations.
- webhook/event-trigger runbook.
- external notifier operations (telegram/slack).

## 9. Related Docs

- Authoring constraints: `docs/dev/blueprint_authoring_constraints.md`
- Blueprint execution plan: `docs/dev/blueprints_execution_plan.md`
- Jobs execution plan: `docs/dev/jobs_execution_plan.md`
