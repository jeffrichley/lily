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

## 3.1 Scheduler Runtime Standard (J1)

Operators should verify that cron scheduling is implemented with APScheduler runtime
features, not trigger-only helper usage.

Required implementation signals:
- one dedicated APScheduler runtime process is active.
- cron jobs are registered with stable ids and `replace_existing=True`.
- scheduler/job defaults include:
  - `coalesce=True`
  - `max_instances=1`
  - explicit `misfire_grace_time`
- APScheduler event listeners are active for:
  - `EVENT_JOB_EXECUTED`
  - `EVENT_JOB_ERROR`
  - `EVENT_JOB_MISSED`
- listener events are reflected in Lily `events.jsonl`/receipts.
- only one scheduler process owns a given APScheduler job store.

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

## 6.1 Retry/Timeout Operations (J2)

- Retry behavior:
  - job runtime uses bounded attempts (`retry_max + 1` total tries).
  - each attempt emits structured events (`job_attempt_started`, `job_attempt_failed`, `job_attempt_succeeded`).
- Timeout behavior:
  - each attempt is bounded by `runtime.timeout_seconds`.
  - timeout failures map to deterministic `job_execution_failed`.
- Replay workflow:
  - use `lily jobs run <job_id>` to replay the same durable job spec.
  - compare latest and prior `run_receipt.json` payload attempt lineage for diffs.

## 7. Pre-Merge Operational Checks

- run representative jobs manually.
- verify APScheduler runtime registration for cron jobs (stable ids).
- verify `coalesce/max_instances/misfire_grace_time` config is explicitly set.
- verify listener-driven lifecycle events (`executed/error/missed`) appear in artifacts.
- validate required artifact set exists.
- confirm deterministic failure behavior for at least one invalid job.
- run `just quality-check`.

## 8. Deferred Operations (Out of V0)

- distributed scheduler operations.
- webhook/event-trigger runbook.
- external notifier operations (telegram/slack).
- scheduled cleanup policy (retention pruning) automation.
- scheduled self-learning/feedback jobs.

## 9. Related Docs

- Authoring constraints: `docs/dev/blueprint_authoring_constraints.md`
- Blueprint execution plan: `docs/dev/blueprints_execution_plan.md`
- Jobs execution plan: `docs/dev/jobs_execution_plan.md`
- APScheduler user guide (3.x): `https://apscheduler.readthedocs.io/en/3.x/userguide.html`
