"""Handler for `/jobs` commands."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from lily.blueprints import BlueprintError
from lily.commands.parser import CommandCall
from lily.commands.types import CommandResult
from lily.jobs import (
    JobError,
    JobHistoryResult,
    JobRepositoryScan,
    JobRunEnvelope,
    JobTailResult,
)
from lily.session.models import Session

_RUN_ARG_COUNT = 2
_HISTORY_LIMIT_ARG_COUNT = 4


class JobExecutorPort(Protocol):
    """Executor port used by jobs command handler."""

    def list_jobs(self) -> JobRepositoryScan:
        """List available jobs and diagnostics."""

    def run(self, job_id: str) -> JobRunEnvelope:
        """Execute one job by stable id.

        Args:
            job_id: Stable job identifier.
        """

    def tail(self, job_id: str, *, limit: int = 50) -> JobTailResult:
        """Tail latest run events for one job.

        Args:
            job_id: Stable job identifier.
            limit: Max lines to return.
        """

    def history(self, job_id: str, *, limit: int = 20) -> JobHistoryResult:
        """Return recent run history for one job.

        Args:
            job_id: Stable job identifier.
            limit: Max entries to return.
        """


class JobSchedulerControlPort(Protocol):
    """Scheduler control operations for `/jobs` lifecycle commands."""

    def pause_job(self, job_id: str) -> None:
        """Pause one cron job.

        Args:
            job_id: Target job id.
        """

    def resume_job(self, job_id: str) -> None:
        """Resume one cron job.

        Args:
            job_id: Target job id.
        """

    def disable_job(self, job_id: str) -> None:
        """Disable one cron job.

        Args:
            job_id: Target job id.
        """

    def status(self) -> dict[str, object]:
        """Return scheduler status payload."""


class JobsCommand:
    """Deterministic `/jobs` command handler."""

    def __init__(
        self,
        executor: JobExecutorPort,
        *,
        runs_root: Path,
        scheduler_control: JobSchedulerControlPort | None = None,
    ) -> None:
        """Store execution dependencies.

        Args:
            executor: Jobs execution service.
            runs_root: Root directory for run artifacts.
            scheduler_control: Optional scheduler controls for lifecycle ops.
        """
        self._executor = executor
        self._runs_root = runs_root
        self._scheduler_control = scheduler_control

    def execute(self, call: CommandCall, session: Session) -> CommandResult:
        """Route `/jobs` subcommands deterministically.

        Args:
            call: Parsed command call.
            session: Active session (unused in J0, kept for command protocol).

        Returns:
            Deterministic command result envelope.
        """
        del session
        if not call.args:
            return CommandResult.error(
                (
                    "Error: /jobs requires subcommand: "
                    "list | run <job_id> | tail <job_id> | history <job_id> "
                    "| pause <job_id> | resume <job_id> | disable <job_id> | status."
                ),
                code="invalid_args",
                data={"command": "jobs"},
            )
        return self._dispatch_subcommand(call.args)

    def _dispatch_subcommand(self, args: tuple[str, ...]) -> CommandResult:
        """Dispatch parsed jobs subcommand to handler.

        Args:
            args: Slash command arguments.

        Returns:
            Deterministic command result payload.
        """
        subcommand = args[0]
        handlers = {
            "list": self._handle_list,
            "run": self._handle_run,
            "tail": self._handle_tail,
            "history": self._handle_history,
            "pause": self._handle_pause,
            "resume": self._handle_resume,
            "disable": self._handle_disable,
            "status": self._handle_status,
        }
        handler = handlers.get(subcommand)
        if handler is None:
            return CommandResult.error(
                f"Error: unknown jobs subcommand '{subcommand}'.",
                code="invalid_args",
                data={"command": "jobs", "subcommand": subcommand},
            )
        return handler(args)

    def _handle_list(self, args: tuple[str, ...]) -> CommandResult:
        """Handle `/jobs list` validation and execution.

        Args:
            args: Slash command arguments.

        Returns:
            Deterministic command result payload.
        """
        if len(args) != 1:
            return CommandResult.error(
                "Error: /jobs list does not accept additional arguments.",
                code="invalid_args",
                data={"command": "jobs list"},
            )
        return self._list_jobs()

    def _handle_run(self, args: tuple[str, ...]) -> CommandResult:
        """Handle `/jobs run` validation and execution.

        Args:
            args: Slash command arguments.

        Returns:
            Deterministic command result payload.
        """
        if len(args) != _RUN_ARG_COUNT:
            return CommandResult.error(
                "Error: /jobs run requires exactly one job id.",
                code="invalid_args",
                data={"command": "jobs run"},
            )
        return self._run_job(args[1])

    def _handle_tail(self, args: tuple[str, ...]) -> CommandResult:
        """Handle `/jobs tail` validation and execution.

        Args:
            args: Slash command arguments.

        Returns:
            Deterministic command result payload.
        """
        if len(args) != _RUN_ARG_COUNT:
            return CommandResult.error(
                "Error: /jobs tail requires exactly one job id.",
                code="invalid_args",
                data={"command": "jobs tail"},
            )
        return self._tail_job(args[1])

    def _handle_history(self, args: tuple[str, ...]) -> CommandResult:
        """Handle `/jobs history` validation and execution.

        Args:
            args: Slash command arguments.

        Returns:
            Deterministic command result payload.
        """
        if len(args) == _RUN_ARG_COUNT:
            return self._history_job(args[1], limit=20)
        if len(args) == _HISTORY_LIMIT_ARG_COUNT and args[2] == "--limit":
            try:
                limit = int(args[3])
            except ValueError:
                return CommandResult.error(
                    "Error: /jobs history --limit must be an integer.",
                    code="invalid_args",
                    data={"command": "jobs history", "args": list(args)},
                )
            if limit < 1:
                return CommandResult.error(
                    "Error: /jobs history --limit must be >= 1.",
                    code="invalid_args",
                    data={"command": "jobs history", "args": list(args)},
                )
            return self._history_job(args[1], limit=limit)
        return CommandResult.error(
            "Error: /jobs history requires '<job_id>' and optional '--limit <n>'.",
            code="invalid_args",
            data={"command": "jobs history", "args": list(args)},
        )

    def _handle_pause(self, args: tuple[str, ...]) -> CommandResult:
        """Handle `/jobs pause` validation and execution.

        Args:
            args: Slash command arguments.

        Returns:
            Deterministic command result payload.
        """
        if len(args) != _RUN_ARG_COUNT:
            return CommandResult.error(
                "Error: /jobs pause requires exactly one job id.",
                code="invalid_args",
                data={"command": "jobs pause"},
            )
        return self._scheduler_action("pause", args[1])

    def _handle_resume(self, args: tuple[str, ...]) -> CommandResult:
        """Handle `/jobs resume` validation and execution.

        Args:
            args: Slash command arguments.

        Returns:
            Deterministic command result payload.
        """
        if len(args) != _RUN_ARG_COUNT:
            return CommandResult.error(
                "Error: /jobs resume requires exactly one job id.",
                code="invalid_args",
                data={"command": "jobs resume"},
            )
        return self._scheduler_action("resume", args[1])

    def _handle_disable(self, args: tuple[str, ...]) -> CommandResult:
        """Handle `/jobs disable` validation and execution.

        Args:
            args: Slash command arguments.

        Returns:
            Deterministic command result payload.
        """
        if len(args) != _RUN_ARG_COUNT:
            return CommandResult.error(
                "Error: /jobs disable requires exactly one job id.",
                code="invalid_args",
                data={"command": "jobs disable"},
            )
        return self._scheduler_action("disable", args[1])

    def _handle_status(self, args: tuple[str, ...]) -> CommandResult:
        """Handle `/jobs status` validation and execution.

        Args:
            args: Slash command arguments.

        Returns:
            Deterministic command result payload.
        """
        if len(args) != 1:
            return CommandResult.error(
                "Error: /jobs status does not accept additional arguments.",
                code="invalid_args",
                data={"command": "jobs status"},
            )
        if self._scheduler_control is None:
            return CommandResult.error(
                "Error: jobs scheduler controls are unavailable in this runtime.",
                code="jobs_scheduler_unavailable",
                data={},
            )
        status = self._scheduler_control.status()
        return CommandResult.ok(
            "Scheduler status loaded.",
            code="jobs_scheduler_status",
            data=status,
        )

    def _list_jobs(self) -> CommandResult:
        """List repository jobs with deterministic diagnostics section.

        Returns:
            Deterministic command result payload.
        """
        try:
            scan = self._executor.list_jobs()
        except JobError as exc:
            return CommandResult.error(str(exc), code=exc.code.value, data=exc.data)

        if not scan.jobs:
            lines = ["No jobs found in `.lily/jobs`.", *self._diagnostic_lines(scan)]
            return CommandResult.ok(
                "\n".join(lines),
                code="jobs_empty",
                data={
                    "jobs": [],
                    "diagnostics": [
                        diag.model_dump(mode="json") for diag in scan.diagnostics
                    ],
                },
            )

        lines = [
            f"{job.id} - {job.title}" for job in scan.jobs
        ] + self._diagnostic_lines(scan)
        return CommandResult.ok(
            "\n".join(lines),
            code="jobs_listed",
            data={
                "jobs": [
                    {
                        "id": job.id,
                        "title": job.title,
                        "target_kind": job.target.kind.value,
                        "target_id": job.target.id,
                        "trigger": job.trigger.type.value,
                    }
                    for job in scan.jobs
                ],
                "diagnostics": [
                    diag.model_dump(mode="json") for diag in scan.diagnostics
                ],
            },
        )

    @staticmethod
    def _diagnostic_lines(scan: JobRepositoryScan) -> list[str]:
        """Render diagnostics section lines for jobs list output.

        Args:
            scan: Repository scan output.

        Returns:
            Formatted diagnostics section lines.
        """
        if not scan.diagnostics:
            return []
        lines = ["", "Diagnostics:"]
        lines.extend(
            f"- {diag.path} [{diag.code}] {diag.message}" for diag in scan.diagnostics
        )
        return lines

    def _run_job(self, job_id: str) -> CommandResult:
        """Execute one job and surface deterministic result payload.

        Args:
            job_id: Target job identifier.

        Returns:
            Deterministic command result payload.
        """
        try:
            run = self._executor.run(job_id)
        except JobError as exc:
            return CommandResult.error(str(exc), code=exc.code.value, data=exc.data)
        except BlueprintError as exc:
            return CommandResult.error(str(exc), code=exc.code.value, data=exc.data)

        run_path = self._runs_root / run.job_id / run.run_id
        return CommandResult.ok(
            f"Job '{run.job_id}' completed with status '{run.status}'.",
            code="job_run_completed",
            data={
                "job_id": run.job_id,
                "run_id": run.run_id,
                "status": run.status,
                "started_at": run.started_at,
                "ended_at": run.ended_at,
                "target": run.target,
                "artifacts": list(run.artifacts),
                "approvals_requested": list(run.approvals_requested),
                "references": list(run.references),
                "payload": run.payload,
                "run_path": str(run_path),
            },
        )

    def _tail_job(self, job_id: str) -> CommandResult:
        """Tail latest run events for one job.

        Args:
            job_id: Target job identifier.

        Returns:
            Deterministic command result payload.
        """
        try:
            tail = self._executor.tail(job_id, limit=50)
        except JobError as exc:
            return CommandResult.error(str(exc), code=exc.code.value, data=exc.data)
        if tail.run_id is None:
            return CommandResult.ok(
                f"No run artifacts found yet for job '{tail.job_id}'.",
                code="jobs_tail_empty",
                data={"job_id": tail.job_id, "run_id": None, "lines": []},
            )
        return CommandResult.ok(
            "\n".join(tail.lines) if tail.lines else "(events.jsonl is empty)",
            code="jobs_tailed",
            data={
                "job_id": tail.job_id,
                "run_id": tail.run_id,
                "lines": list(tail.lines),
                "line_count": len(tail.lines),
            },
        )

    def _history_job(self, job_id: str, *, limit: int) -> CommandResult:
        """Load run history entries for one job.

        Args:
            job_id: Target job identifier.
            limit: Maximum entries to return.

        Returns:
            Deterministic command result payload.
        """
        try:
            history = self._executor.history(job_id, limit=limit)
        except JobError as exc:
            return CommandResult.error(str(exc), code=exc.code.value, data=exc.data)
        entries = [
            {
                "run_id": item.run_id,
                "status": item.status,
                "started_at": item.started_at,
                "ended_at": item.ended_at,
                "path": item.path,
                "attempt_count": item.attempt_count,
            }
            for item in history.entries
        ]
        if not entries:
            return CommandResult.ok(
                f"No runs found yet for job '{history.job_id}'.",
                code="jobs_history_empty",
                data={"job_id": history.job_id, "entries": []},
            )
        return CommandResult.ok(
            f"Loaded {len(entries)} run(s) for job '{history.job_id}'.",
            code="jobs_history",
            data={"job_id": history.job_id, "entries": entries},
        )

    def _scheduler_action(self, action: str, job_id: str) -> CommandResult:
        """Execute one scheduler lifecycle action for a cron job.

        Args:
            action: Lifecycle action (`pause`, `resume`, `disable`).
            job_id: Target job id.

        Returns:
            Deterministic command result payload.
        """
        if self._scheduler_control is None:
            return CommandResult.error(
                "Error: jobs scheduler controls are unavailable in this runtime.",
                code="jobs_scheduler_unavailable",
                data={"action": action, "job_id": job_id},
            )
        handlers = {
            "pause": self._scheduler_control.pause_job,
            "resume": self._scheduler_control.resume_job,
            "disable": self._scheduler_control.disable_job,
        }
        handler = handlers[action]
        try:
            handler(job_id)
        except JobError as exc:
            return CommandResult.error(str(exc), code=exc.code.value, data=exc.data)
        return CommandResult.ok(
            f"Scheduler action '{action}' applied to job '{job_id}'.",
            code=f"jobs_{action}d" if action != "pause" else "jobs_paused",
            data={"job_id": job_id, "action": action},
        )
