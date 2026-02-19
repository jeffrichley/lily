"""Handler for `/jobs` commands."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from lily.blueprints import BlueprintError
from lily.commands.parser import CommandCall
from lily.commands.types import CommandResult
from lily.jobs import (
    JobError,
    JobRepositoryScan,
    JobRunEnvelope,
    JobTailResult,
)
from lily.session.models import Session

_RUN_ARG_COUNT = 2


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


class JobsCommand:
    """Deterministic `/jobs` command handler."""

    def __init__(
        self,
        executor: JobExecutorPort,
        *,
        runs_root: Path,
    ) -> None:
        """Store execution dependencies.

        Args:
            executor: Jobs execution service.
            runs_root: Root directory for run artifacts.
        """
        self._executor = executor
        self._runs_root = runs_root

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
                    "list | run <job_id> | tail <job_id>."
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
