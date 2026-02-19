"""APScheduler runtime service for cron-backed Lily jobs."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from zoneinfo import ZoneInfo

from apscheduler.events import (
    EVENT_JOB_ERROR,
    EVENT_JOB_EXECUTED,
    EVENT_JOB_MISSED,
    JobExecutionEvent,
)
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from lily.blueprints import BlueprintError, build_default_blueprint_registry
from lily.jobs.errors import JobError, JobErrorCode
from lily.jobs.executor import JobExecutor
from lily.jobs.models import JobSpec, JobTriggerType
from lily.jobs.repository import JobRepository
from lily.jobs.scheduler_state import JobScheduleState, SchedulerStateStore

_APS_JOB_PREFIX = "job:"


class JobSchedulerRuntime:
    """Manage APScheduler lifecycle and cron job registration for Lily."""

    def __init__(
        self,
        *,
        repository: JobRepository,
        jobs_dir: Path,
        runs_root: Path,
        sqlite_path: Path,
        misfire_grace_time: int = 30,
    ) -> None:
        """Create scheduler runtime service.

        Args:
            repository: Job repository for cron job discovery.
            jobs_dir: Jobs directory root for callback execution context.
            runs_root: Root run artifacts directory.
            sqlite_path: SQLite path for APScheduler + runtime metadata.
            misfire_grace_time: Scheduler job misfire grace time in seconds.
        """
        self._repository = repository
        self._jobs_dir = jobs_dir
        self._runs_root = runs_root
        self._sqlite_path = sqlite_path
        self._sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        self._state_store = SchedulerStateStore(sqlite_path=sqlite_path)
        self._scheduler = BackgroundScheduler(
            timezone=ZoneInfo("UTC"),
            jobstores={"default": SQLAlchemyJobStore(url=f"sqlite:///{sqlite_path}")},
            job_defaults={
                "coalesce": True,
                "max_instances": 1,
                "misfire_grace_time": misfire_grace_time,
            },
        )
        self._scheduler.add_listener(
            self._handle_event,
            EVENT_JOB_EXECUTED | EVENT_JOB_ERROR | EVENT_JOB_MISSED,
        )
        self._lock = Lock()
        self._started = False

    def start(self) -> None:
        """Start scheduler and register current cron jobs."""
        with self._lock:
            if not self._started:
                self._scheduler.start(paused=False)
                self._started = True
            self.refresh_jobs()

    def shutdown(self) -> None:
        """Shutdown scheduler service if running."""
        with self._lock:
            if not self._started:
                return
            self._scheduler.shutdown(wait=True)
            jobstores = self._scheduler._jobstores.values()
            for store in jobstores:
                if isinstance(store, SQLAlchemyJobStore):
                    store.engine.dispose()
            self._started = False

    def refresh_jobs(self) -> None:
        """Sync registered APScheduler jobs with cron job specs."""
        scan = self._repository.list_jobs()
        cron_jobs = tuple(
            job for job in scan.jobs if job.trigger.type == JobTriggerType.CRON
        )
        states_by_job = self._resolve_states(cron_jobs)
        expected_ids = self._expected_scheduler_ids(cron_jobs, states_by_job)
        self._remove_stale_scheduler_jobs(expected_ids)
        self._apply_registrations(cron_jobs, states_by_job)

    def _resolve_states(
        self, cron_jobs: tuple[JobSpec, ...]
    ) -> dict[str, JobScheduleState]:
        """Resolve effective schedule state for each cron job.

        Args:
            cron_jobs: Cron job tuple.

        Returns:
            Mapping from job id to schedule state.
        """
        return {job.id: self._resolve_schedule_state(job) for job in cron_jobs}

    def _expected_scheduler_ids(
        self,
        cron_jobs: tuple[JobSpec, ...],
        states_by_job: dict[str, JobScheduleState],
    ) -> set[str]:
        """Build expected APScheduler id set for non-disabled jobs.

        Args:
            cron_jobs: Cron job tuple.
            states_by_job: Job state mapping.

        Returns:
            Expected APScheduler job id set.
        """
        return {
            self._aps_job_id(job.id)
            for job in cron_jobs
            if states_by_job[job.id] != JobScheduleState.DISABLED
        }

    def _remove_stale_scheduler_jobs(self, expected_ids: set[str]) -> None:
        """Remove stale APScheduler jobs not present in expected id set.

        Args:
            expected_ids: Expected APScheduler ids.
        """
        for job in list(self._scheduler.get_jobs()):
            if job.id.startswith(_APS_JOB_PREFIX) and job.id not in expected_ids:
                self._scheduler.remove_job(job.id)

    def _apply_registrations(
        self,
        cron_jobs: tuple[JobSpec, ...],
        states_by_job: dict[str, JobScheduleState],
    ) -> None:
        """Apply APScheduler registration state for each cron job.

        Args:
            cron_jobs: Cron job tuple.
            states_by_job: Job state mapping.
        """
        for job in cron_jobs:
            state = states_by_job[job.id]
            if state == JobScheduleState.DISABLED:
                self._append_disabled_reconcile_event(job)
                continue
            self._register_cron_job(job, state=state)

    def _append_disabled_reconcile_event(self, job: JobSpec) -> None:
        """Append deterministic reconcile event for disabled cron job.

        Args:
            job: Disabled cron job spec.
        """
        self._append_scheduler_event(
            job_id=job.id,
            payload={
                "timestamp": _utc_now(),
                "event_code": "SCHEDULER_RECONCILED",
                "job_id": job.id,
                "state": JobScheduleState.DISABLED.value,
                "spec_hash": _hash_job_spec(job),
                "run_id": None,
            },
        )

    def pause_job(self, job_id: str) -> None:
        """Pause one cron job and persist paused lifecycle state.

        Args:
            job_id: Target job id.
        """
        job = self._require_cron_job(job_id)
        self._state_store.upsert(
            job_id=job.id,
            state=JobScheduleState.PAUSED,
            spec_hash=_hash_job_spec(job),
        )
        self._register_cron_job(job, state=JobScheduleState.PAUSED)

    def resume_job(self, job_id: str) -> None:
        """Resume one cron job and persist active lifecycle state.

        Args:
            job_id: Target job id.
        """
        job = self._require_cron_job(job_id)
        self._state_store.upsert(
            job_id=job.id,
            state=JobScheduleState.ACTIVE,
            spec_hash=_hash_job_spec(job),
        )
        self._register_cron_job(job, state=JobScheduleState.ACTIVE)

    def disable_job(self, job_id: str) -> None:
        """Disable one cron job and remove APScheduler registration.

        Args:
            job_id: Target job id.
        """
        job = self._require_cron_job(job_id)
        self._state_store.upsert(
            job_id=job.id,
            state=JobScheduleState.DISABLED,
            spec_hash=_hash_job_spec(job),
        )
        aps_id = self._aps_job_id(job.id)
        if self._scheduler.get_job(aps_id) is not None:
            self._scheduler.remove_job(aps_id)
        self._append_scheduler_event(
            job_id=job.id,
            payload={
                "timestamp": _utc_now(),
                "event_code": "SCHEDULER_DISABLED",
                "job_id": job.id,
                "run_id": None,
            },
        )

    def status(self) -> dict[str, object]:
        """Return scheduler runtime diagnostics payload.

        Returns:
            Deterministic scheduler status payload.
        """
        states = self._state_store.list_all()
        return {
            "started": self._started,
            "sqlite_path": str(self._sqlite_path),
            "registered_jobs": len(self._scheduler.get_jobs()),
            "state_rows": len(states),
            "states": [
                {
                    "job_id": row.job_id,
                    "state": row.state.value,
                    "spec_hash": row.spec_hash,
                    "updated_at": row.updated_at,
                }
                for row in states
            ],
        }

    def _resolve_schedule_state(self, job: JobSpec) -> JobScheduleState:
        """Resolve persisted schedule state and reconcile spec hash.

        Args:
            job: Loaded job spec.

        Returns:
            Effective schedule state for registration behavior.
        """
        spec_hash = _hash_job_spec(job)
        stored = self._state_store.get(job.id)
        if stored is None:
            self._state_store.upsert(
                job_id=job.id,
                state=JobScheduleState.ACTIVE,
                spec_hash=spec_hash,
            )
            self._append_scheduler_event(
                job_id=job.id,
                payload={
                    "timestamp": _utc_now(),
                    "event_code": "SCHEDULER_RECONCILED",
                    "job_id": job.id,
                    "state": JobScheduleState.ACTIVE.value,
                    "spec_hash": spec_hash,
                    "spec_hash_changed": False,
                    "run_id": None,
                },
            )
            return JobScheduleState.ACTIVE
        hash_changed = stored.spec_hash != spec_hash
        self._state_store.upsert(
            job_id=job.id,
            state=stored.state,
            spec_hash=spec_hash,
        )
        self._append_scheduler_event(
            job_id=job.id,
            payload={
                "timestamp": _utc_now(),
                "event_code": "SCHEDULER_RECONCILED",
                "job_id": job.id,
                "state": stored.state.value,
                "spec_hash": spec_hash,
                "spec_hash_changed": hash_changed,
                "run_id": None,
            },
        )
        return stored.state

    def _require_cron_job(self, job_id: str) -> JobSpec:
        """Load one cron job or raise deterministic trigger-invalid error.

        Args:
            job_id: Target job id.

        Returns:
            Loaded cron job spec.

        Raises:
            JobError: If target job is not cron-triggered.
        """
        job = self._repository.load(job_id)
        if job.trigger.type != JobTriggerType.CRON:
            raise JobError(
                code=JobErrorCode.TRIGGER_INVALID,
                message=f"Error: job '{job.id}' is not cron-triggered.",
                data={"job_id": job.id, "trigger_type": job.trigger.type.value},
            )
        return job

    def _register_cron_job(self, job: JobSpec, *, state: JobScheduleState) -> None:
        """Register one cron job in APScheduler.

        Args:
            job: Cron job specification.
            state: Effective lifecycle state for this registration.
        """
        if job.trigger.cron is None or job.trigger.timezone is None:
            return
        trigger = CronTrigger.from_crontab(
            job.trigger.cron,
            timezone=ZoneInfo(job.trigger.timezone),
        )
        aps_id = self._aps_job_id(job.id)
        self._scheduler.add_job(
            run_scheduled_job_callback,
            trigger=trigger,
            args=(job.id, str(self._jobs_dir), str(self._runs_root)),
            id=aps_id,
            replace_existing=True,
            coalesce=True,
            max_instances=1,
        )
        if state == JobScheduleState.PAUSED:
            self._scheduler.pause_job(aps_id)
        else:
            self._scheduler.resume_job(aps_id)

    def _handle_event(self, event: JobExecutionEvent) -> None:
        """Handle APScheduler execution lifecycle events.

        Args:
            event: APScheduler execution event.
        """
        if not event.job_id.startswith(_APS_JOB_PREFIX):
            return
        job_id = event.job_id.removeprefix(_APS_JOB_PREFIX)
        run_id = self._resolve_run_id(job_id=job_id, event=event)
        payload = {
            "timestamp": _utc_now(),
            "event_code": _event_code_name(event.code),
            "job_id": job_id,
            "scheduled_run_time_utc": event.scheduled_run_time.astimezone(UTC)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z"),
            "run_id": run_id,
        }
        if event.exception is not None:
            payload["exception"] = str(event.exception)
        self._append_scheduler_event(job_id=job_id, payload=payload)

    def _resolve_run_id(self, *, job_id: str, event: JobExecutionEvent) -> str | None:
        """Resolve run id for APScheduler event context.

        Args:
            job_id: Logical Lily job id.
            event: APScheduler event payload.

        Returns:
            Run id if known, otherwise ``None``.
        """
        del job_id
        if isinstance(event.retval, str) and event.retval.strip():
            return event.retval
        return None

    def _append_scheduler_event(
        self, *, job_id: str, payload: dict[str, object]
    ) -> None:
        """Append scheduler lifecycle event to per-job event stream.

        Args:
            job_id: Logical Lily job id.
            payload: Event payload.
        """
        path = self._runs_root / job_id / "scheduler_events.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True))
            handle.write("\n")

    @staticmethod
    def _aps_job_id(job_id: str) -> str:
        """Map Lily job id to APScheduler job id namespace.

        Args:
            job_id: Logical Lily job identifier.

        Returns:
            APScheduler job identifier.
        """
        return f"{_APS_JOB_PREFIX}{job_id}"


def run_scheduled_job_callback(
    job_id: str, jobs_dir: str, runs_root: str
) -> str | None:
    """Execute one scheduled job callback in a pickle-safe module function.

    Args:
        job_id: Logical Lily job id.
        jobs_dir: Jobs directory path string.
        runs_root: Runs directory path string.

    Returns:
        Run id when execution succeeds, otherwise ``None``.
    """
    executor = JobExecutor(
        repository=JobRepository(jobs_dir=Path(jobs_dir)),
        blueprint_registry=build_default_blueprint_registry(),
        runs_root=Path(runs_root),
    )
    try:
        run = executor.run(job_id)
    except (JobError, BlueprintError):
        return None
    return run.run_id


def _hash_job_spec(job: JobSpec) -> str:
    """Create deterministic hash for one job spec.

    Args:
        job: Job spec.

    Returns:
        SHA-256 hash over normalized JSON payload.
    """
    payload = json.dumps(job.model_dump(mode="json"), sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _event_code_name(code: int) -> str:
    """Return stable event name for APScheduler execution code.

    Args:
        code: APScheduler event code.

    Returns:
        Stable event code name string.
    """
    mapping = {
        EVENT_JOB_EXECUTED: "EVENT_JOB_EXECUTED",
        EVENT_JOB_ERROR: "EVENT_JOB_ERROR",
        EVENT_JOB_MISSED: "EVENT_JOB_MISSED",
    }
    return mapping.get(code, f"EVENT_UNKNOWN_{code}")


def _utc_now() -> str:
    """Return UTC timestamp string for scheduler events.

    Returns:
        Normalized UTC timestamp string.
    """
    return (
        datetime.now(tz=UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    )
