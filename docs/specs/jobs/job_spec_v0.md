---
owner: "@team"
last_updated: "2026-02-19"
status: "active"
source_of_truth: true
---

# Job Spec V0

Status: Proposed  
Date: 2026-02-18  
Scope: scheduled/triggered execution wrapper around blueprint instances and other runnables.

## 1. Why This Exists

Lily should execute repeatable work as durable, inspectable jobs.
Jobs unify manual runs, scheduled runs, and trigger-based runs under one contract.

## 2. Definitions

- `Job`: persistent configuration that executes a runnable target.
- `JobId`: stable identifier.
- `Trigger`: execution rule (`manual` or `cron` in V0).
- `Run`: one execution occurrence of a job.
- `RunId`: unique per run.
- `Artifact`: durable run output file(s).

## 3. Job Contract

Locked decisions (V0):
- [x] Blueprint metadata mode: code-only blueprints (execution truth in code).
- [x] Job spec location: concrete executable jobs live under `.lily/jobs/*.job.yaml`.
- [x] Cron timezone: explicit per-job IANA timezone is required.
- [x] Retention default: retain all run artifacts in V0.

## 3.1 Job Schema (Conceptual)

Required fields:
- [ ] `id`
- [ ] `title`
- [ ] `target.kind` (`blueprint` in V0)
- [ ] `target.id` (for example `council.v1`)
- [ ] `bindings`
- [ ] `trigger`
- [ ] `runtime` (timeout/retry/parallelism caps)
- [ ] `output` (artifact and render settings)
- [ ] `timezone` (IANA timezone name, required when `trigger.type=cron`)

## 3.2 Trigger Model (V0)

Supported:
- [x] `manual`
- [x] `cron`

Deferred:
- [ ] webhook/event triggers
- [ ] queue/topic triggers

Timezone contract:
- [x] cron jobs must declare explicit IANA timezone.
- [x] missing or invalid timezone fails with `job_trigger_invalid`.
- [x] run receipts store timestamps in UTC for stable audit semantics.

## 3.3 Execution Contract

Job run sequence:
1. load and validate job spec.
2. resolve target runnable.
3. validate bindings against target schema.
4. enforce capability and approval policy.
5. execute target via Run Contract R0.
6. persist artifacts and run receipt.
7. emit deterministic summary.

## 3.4 Shared Output Envelope

Every job run returns:
- `status`
- `started_at`
- `ended_at`
- `target`
- `artifacts`
- `approvals_requested`
- `references`
- `payload`

## 3.5 Stable Error Codes

- `job_not_found`
- `job_invalid_spec`
- `job_trigger_invalid`
- `job_target_unresolved`
- `job_bindings_invalid`
- `job_execution_failed`
- `job_policy_denied`

## 4. Artifact Contract

Default path:
- `.lily/runs/<job_id>/<timestamp>/`

Required files:
- `run_receipt.json`
- `summary.md`
- `events.jsonl`

Optional files:
- target-specific artifacts (for example `report.md`, `evidence.json`).

## 5. Observability and Replay

V0 must support:
- listing runs by job id.
- tailing run events for active/recent runs.
- deterministic replay request for a prior run configuration (without side effects unless approved).

## 6. Acceptance Criteria

- [ ] `jobs list`, `jobs run <job_id>`, and `jobs tail <job_id>` work for V0 job types.
- [ ] Cron-triggered jobs execute with deterministic runtime boundaries.
- [ ] Every run writes mandatory artifacts and a stable receipt.
- [ ] Failures remain contained and return stable error codes.

## 7. Non-Goals (V0)

- No distributed job scheduler.
- No cross-host execution.
- No multi-tenant isolation model.
- No trigger types beyond manual and cron.

## 8. Required Tests and Gates

- [ ] Job schema validation tests.
- [ ] Trigger parsing/evaluation tests.
- [ ] Artifact persistence tests.
- [ ] Failure/retry boundary tests.
- [ ] CLI integration tests for list/run/tail.
- [ ] `just quality-check`
- [ ] `just contract-conformance`

## 9. Open Questions

- Whether replay keeps original run id lineage or assigns fresh lineage id.
