---
owner: "@team"
last_updated: "2026-02-18"
status: "active"
source_of_truth: true
---

# Jobs Execution Plan

Purpose: phased delivery tracker for `docs/specs/jobs/job_spec_v0.md`.

## Scope Lock

This plan covers job execution, scheduling, artifacts, and operational controls.

## Phase J0: Job Contract + Manual Execution

Phase checklist:
- [ ] define job spec model and validation
- [ ] implement job repository loading and deterministic error mapping
- [ ] implement manual run executor using Run Contract R0 target resolution
- [ ] persist required artifacts (`run_receipt.json`, `summary.md`, `events.jsonl`)
- [ ] add job schema validation tests
- [ ] add manual execution integration tests
- [ ] add artifact write tests
- [ ] pass `just quality-check`

User-visible features:
- `jobs list`
- `jobs run <job_id>`

Internal engineering tasks:
- define job spec model and validation.
- implement job repository loading and deterministic error mapping.
- implement manual run executor using Run Contract R0 target resolution.
- persist required artifacts (`run_receipt.json`, `summary.md`, `events.jsonl`).

Acceptance criteria:
- valid job specs run deterministically through target execution path.
- invalid specs fail with `job_invalid_spec`.
- missing jobs fail with `job_not_found`.

Non-goals:
- no scheduler loop yet.
- no tail streaming yet.

Required tests and gates:
- job schema validation tests.
- manual execution integration tests.
- artifact write tests.
- `just quality-check`.

## Phase J1: Cron Scheduling + Tailing

Phase checklist:
- [ ] implement scheduler component with deterministic cron evaluation
- [ ] enforce explicit per-job IANA timezone validation
- [ ] add run queue semantics and duplicate-run guardrails
- [ ] implement event tailer for structured run stream output
- [ ] add scheduler tick tests
- [ ] add cron parsing/timezone behavior tests
- [ ] add tail streaming tests
- [ ] pass `just quality-check`

User-visible features:
- cron-triggered job runs.
- `jobs tail <job_id>` for active/recent run output.

Internal engineering tasks:
- implement scheduler component with deterministic cron evaluation.
- add run queue semantics and duplicate-run guardrails.
- implement event tailer for structured run stream output.

Acceptance criteria:
- cron jobs execute according to configured schedule.
- concurrent scheduler ticks do not duplicate the same intended run.
- tail command displays ordered structured events.

Non-goals:
- no distributed scheduler.
- no webhook/event triggers yet.

Required tests and gates:
- scheduler tick tests.
- cron parsing and timezone behavior tests.
- tail streaming tests.
- `just quality-check`.

## Phase J2: Retry/Failure Policy + Ops Hardening

Phase checklist:
- [ ] implement bounded retry semantics
- [ ] enforce timeout/resource boundary handling in run executor
- [ ] keep retain-all artifact policy in V0 with deterministic run indexing
- [ ] document deferred cleanup/self-learning scheduled jobs as debt/TODO
- [ ] document runbook procedures for failures and replay
- [ ] add retry boundary tests
- [ ] add timeout/failure mapping tests
- [ ] add retention lifecycle tests
- [ ] pass `just quality-check`
- [ ] pass `just contract-conformance`

User-visible features:
- consistent retry behavior and clearer run failure diagnostics.

Internal engineering tasks:
- implement bounded retry semantics.
- enforce timeout/resource boundary handling in run executor.
- add retention/cleanup policy controls for run artifacts.
- document runbook procedures for failures and replay.

Acceptance criteria:
- retry policy behavior is deterministic and test-covered.
- timeout and policy denials produce stable error envelopes.
- retention policy can be applied without corrupting active runs.

Non-goals:
- no cross-host failover.
- no advanced SLA monitoring stack.

Required tests and gates:
- retry boundary tests.
- timeout/failure mapping tests.
- retention lifecycle tests.
- `just quality-check`.
- `just contract-conformance`.

## Milestone Checklist

- [ ] J0 complete
- [ ] J1 complete
- [ ] J2 complete

## Decision Log

- 2026-02-18: jobs are concrete runnable instances; blueprints remain reusable orchestration definitions.
- 2026-02-18: V0 trigger scope locked to `manual` and `cron`.
