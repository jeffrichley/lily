"""APScheduler runtime service for cron-backed Lily jobs."""

from __future__ import annotations

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
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from lily.blueprints import BlueprintError
from lily.jobs.errors import JobError
from lily.jobs.executor import JobExecutor
from lily.jobs.models import JobSpec, JobTriggerType
from lily.jobs.repository import JobRepository

_APS_JOB_PREFIX = "job:"


class JobSchedulerRuntime:
    """Manage APScheduler lifecycle and cron job registration for Lily."""

    def __init__(
        self,
        *,
        repository: JobRepository,
        executor: JobExecutor,
        runs_root: Path,
        misfire_grace_time: int = 30,
    ) -> None:
        """Create scheduler runtime service.

        Args:
            repository: Job repository for cron job discovery.
            executor: Job executor used by scheduled runs.
            runs_root: Root run artifacts directory.
            misfire_grace_time: Scheduler job misfire grace time in seconds.
        """
        self._repository = repository
        self._executor = executor
        self._runs_root = runs_root
        self._scheduler = BackgroundScheduler(
            timezone=ZoneInfo("UTC"),
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
        self._last_run_by_job_id: dict[str, str] = {}
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
            self._scheduler.shutdown(wait=False)
            self._started = False

    def refresh_jobs(self) -> None:
        """Sync registered APScheduler jobs with cron job specs."""
        scan = self._repository.list_jobs()
        cron_jobs = tuple(
            job for job in scan.jobs if job.trigger.type == JobTriggerType.CRON
        )
        expected_ids = {self._aps_job_id(job.id) for job in cron_jobs}
        for job in list(self._scheduler.get_jobs()):
            if job.id.startswith(_APS_JOB_PREFIX) and job.id not in expected_ids:
                self._scheduler.remove_job(job.id)
        for job in cron_jobs:
            self._register_cron_job(job)

    def _register_cron_job(self, job: JobSpec) -> None:
        """Register one cron job in APScheduler.

        Args:
            job: Cron job specification.
        """
        if job.trigger.cron is None or job.trigger.timezone is None:
            return
        trigger = CronTrigger.from_crontab(
            job.trigger.cron,
            timezone=ZoneInfo(job.trigger.timezone),
        )
        self._scheduler.add_job(
            self._run_job_callback,
            trigger=trigger,
            args=(job.id,),
            id=self._aps_job_id(job.id),
            replace_existing=True,
            coalesce=True,
            max_instances=1,
        )

    def _run_job_callback(self, job_id: str) -> str | None:
        """Execute one scheduled job callback.

        Args:
            job_id: Job identifier.

        Returns:
            Run ID when execution succeeds, otherwise ``None``.
        """
        try:
            run = self._executor.run(job_id)
        except (JobError, BlueprintError):
            return None
        self._last_run_by_job_id[job_id] = run.run_id
        return run.run_id

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
        if isinstance(event.retval, str) and event.retval.strip():
            return event.retval
        return self._last_run_by_job_id.get(job_id)

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
