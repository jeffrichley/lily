"""Composition root for jobs execution and scheduler runtime wiring."""

from __future__ import annotations

from pathlib import Path

from lily.blueprints import build_default_blueprint_registry
from lily.jobs import JobExecutor, JobRepository, JobSchedulerRuntime
from lily.runtime.runtime_dependencies import JobsBundle, JobsSpec


class JobsFactory:
    """Compose jobs subsystem dependencies for runtime command registry."""

    def build(self, spec: JobsSpec) -> JobsBundle:
        """Build jobs bundle from composition spec.

        Args:
            spec: Jobs composition spec.

        Returns:
            Composed jobs bundle.
        """
        jobs_dir = Path(spec.workspace_root) / "jobs"
        runs_root = Path(spec.workspace_root) / "runs"
        scheduler_runtime: JobSchedulerRuntime | None = None
        if spec.scheduler_enabled:
            scheduler_runtime = self._build_scheduler_runtime(spec.workspace_root)
            scheduler_runtime.start()
        return JobsBundle(
            jobs_executor=JobExecutor(
                repository=JobRepository(jobs_dir=jobs_dir),
                blueprint_registry=build_default_blueprint_registry(),
                runs_root=runs_root,
            ),
            runs_root=runs_root,
            scheduler_control=scheduler_runtime,
            scheduler_runtime=scheduler_runtime,
        )

    @staticmethod
    def _build_scheduler_runtime(workspace_root: Path) -> JobSchedulerRuntime:
        """Build APScheduler runtime service for cron job execution.

        Args:
            workspace_root: Workspace root containing jobs/runs/db roots.

        Returns:
            Scheduler runtime service.
        """
        jobs_dir = workspace_root / "jobs"
        runs_root = workspace_root / "runs"
        scheduler_db_path = workspace_root / "db" / "jobs_scheduler.sqlite3"
        return JobSchedulerRuntime(
            repository=JobRepository(jobs_dir=jobs_dir),
            jobs_dir=jobs_dir,
            runs_root=runs_root,
            sqlite_path=scheduler_db_path,
        )
