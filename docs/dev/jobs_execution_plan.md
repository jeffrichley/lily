---
owner: "@team"
last_updated: "2026-02-19"
status: "active"
source_of_truth: true
---

# Jobs Execution Plan

Purpose: phased delivery tracker for `docs/specs/jobs/job_spec_v0.md`.

## Scope Lock

This plan covers job execution, scheduling, artifacts, and operational controls.

## Phase J0: Job Contract + Manual Execution

Phase checklist:
- [x] define job spec model and validation
- [x] implement job repository loading and deterministic error mapping
- [x] implement manual run executor using Run Contract R0 target resolution
- [x] persist required artifacts (`run_receipt.json`, `summary.md`, `events.jsonl`)
- [x] add job schema validation tests
- [x] add manual execution integration tests
- [x] add artifact write tests
- [x] pass `just quality-check`

User-visible features:
- `jobs list`
- `jobs run <job_id>`

Internal engineering tasks:
- define job spec model and validation.
- implement job repository loading and deterministic error mapping.
- implement manual run executor using Run Contract R0 target resolution.
- persist required artifacts (`run_receipt.json`, `summary.md`, `events.jsonl`).

Acceptance criteria:
- [x] valid job specs run deterministically through target execution path.
- [x] invalid specs fail with `job_invalid_spec`.
- [x] missing jobs fail with `job_not_found`.

Non-goals:
- no scheduler loop yet.
- no tail streaming yet.

Required tests and gates:
- [x] job schema validation tests.
- [x] manual execution integration tests.
- [x] artifact write tests.
- [x] `just quality-check`.

## Phase J1: Cron Scheduling + Tailing

Phase checklist:
- [x] implement APScheduler runtime service (`BackgroundScheduler`/`BlockingScheduler`)
- [x] register cron jobs with `add_job(..., id=<job_id>, replace_existing=True)`
- [x] configure `coalesce=True`, `max_instances=1`, and explicit `misfire_grace_time`
- [x] attach APScheduler listeners (`executed`, `error`, `missed`) and map to events/artifacts
- [x] enforce explicit per-job IANA timezone validation
- [x] enforce single scheduler process ownership for one APScheduler job store
- [x] implement event tailer for structured run stream output
- [x] add scheduler runtime registration tests
- [x] add cron parsing/timezone behavior tests
- [x] add tail streaming tests
- [x] add APScheduler integration tests (registration/listeners/misfire-coalesce)
- [x] pass `just quality-check`

User-visible features:
- cron-triggered job runs.
- `jobs tail <job_id>` for active/recent run output.

Internal engineering tasks:
- implement APScheduler runtime service with explicit scheduler defaults.
- map APScheduler lifecycle events to deterministic Lily run events/artifacts.
- enforce single-process scheduler ownership semantics.
- implement event tailer for structured run stream output.

Acceptance criteria:
- [x] cron jobs execute according to configured schedule.
- [x] APScheduler controls (`coalesce`, `max_instances`, `misfire_grace_time`) are configured and test-covered.
- [x] scheduler listeners emit deterministic run lifecycle records (`executed`/`error`/`missed`).
- [x] tail command displays ordered structured events.

Non-goals:
- no distributed scheduler.
- no webhook/event triggers yet.

Required tests and gates:
- [x] scheduler runtime registration tests.
- [x] cron parsing and timezone behavior tests.
- [x] APScheduler registration and listener integration tests.
- [x] APScheduler misfire/coalesce behavior tests.
- [x] tail streaming tests.
- [x] `just quality-check`.

APScheduler implementation guardrails (must hold for J1 completion):
- [x] scheduler uses APScheduler runtime APIs, not trigger-only custom scheduling loop.
- [x] cron triggers are created through `CronTrigger.from_crontab(..., timezone=...)`.
- [x] scheduler adds jobs with stable ids and `replace_existing=True`.
- [x] exactly one scheduler process owns a given job store.

## Phase J2: Retry/Failure Policy + Ops Hardening

Phase checklist:
- [x] implement bounded retry semantics
- [x] enforce timeout/resource boundary handling in run executor
- [x] keep retain-all artifact policy in V0 with deterministic run indexing
- [x] document deferred cleanup/self-learning scheduled jobs as debt/TODO
- [x] document runbook procedures for failures and replay
- [x] add retry boundary tests
- [x] add timeout/failure mapping tests
- [x] add retention lifecycle tests
- [x] pass `just quality-check`
- [x] pass `just contract-conformance`

User-visible features:
- consistent retry behavior and clearer run failure diagnostics.

Internal engineering tasks:
- implement bounded retry semantics.
- enforce timeout/resource boundary handling in run executor.
- add retention/cleanup policy controls for run artifacts.
- document runbook procedures for failures and replay.

Acceptance criteria:
- [x] retry policy behavior is deterministic and test-covered.
- [x] timeout and policy denials produce stable error envelopes.
- [x] retention policy can be applied without corrupting active runs.

Non-goals:
- no cross-host failover.
- no advanced SLA monitoring stack.

Required tests and gates:
- [x] retry boundary tests.
- [x] timeout/failure mapping tests.
- [x] retention lifecycle tests.
- [x] `just quality-check`.
- [x] `just contract-conformance`.

## Phase J3: Durable Scheduler State + Recovery Controls

Phase checklist:
- [x] add SQLite-backed APScheduler job store under `db/`
- [x] persist scheduler runtime metadata for deterministic restart reconciliation
- [x] implement startup reconciliation for misfires/drift after process downtime
- [x] add operator lifecycle commands (`jobs pause`, `jobs resume`, `jobs disable`)
- [x] add run-history command (`jobs history <job_id>`) with stable ordering/limits
- [x] implement scheduler health diagnostics surfaced to CLI
- [x] document operational recovery runbook for restart/drift incidents
- [x] add restart/reconciliation integration tests
- [x] add pause/resume/disable command integration tests
- [x] add history query tests
- [x] pass `just quality-check`
- [x] pass `just contract-conformance`

User-visible features:
- durable schedules across restarts.
- pause/resume/disable lifecycle controls.
- run history inspection per job.

Internal engineering tasks:
- migrate scheduler/job store state to SQLite in `db/`.
- add deterministic startup reconciliation logic for missed windows.
- expose scheduler health/diagnostics for operations.

Acceptance criteria:
- [x] scheduled jobs survive restart with no duplicate execution from one scheduler owner.
- [x] downtime recovery behavior is deterministic and audit-visible in artifacts/events.
- [x] operators can pause/resume/disable jobs without editing spec files.
- [x] operators can inspect recent run history with deterministic sort and limit semantics.

Non-goals:
- no distributed multi-node scheduler leadership.
- no external message-bus trigger system.
- no retention pruning automation yet (remains deferred).

Required tests and gates:
- [x] restart/reconciliation integration tests.
- [x] pause/resume/disable command integration tests.
- [x] history query tests.
- [x] `just quality-check`.
- [x] `just contract-conformance`.

## Milestone Checklist

- [x] J0 complete
- [x] J1 complete
- [x] J2 complete
- [x] J3 complete

## Decision Log

- 2026-02-18: jobs are concrete runnable instances; blueprints remain reusable orchestration definitions.
- 2026-02-18: V0 trigger scope locked to `manual` and `cron`.
