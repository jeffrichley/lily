"""CLI result rendering policies and Rich views."""

from __future__ import annotations

from collections.abc import Callable

from rich.console import Console
from rich.json import JSON
from rich.markdown import Markdown
from rich.panel import Panel

from lily.cli.renderers.agent import (
    render_agent_list,
    render_agent_set,
    render_agent_show,
)
from lily.cli.renderers.evidence import render_evidence_list
from lily.cli.renderers.jobs_list import (
    render_jobs_list,
)
from lily.cli.renderers.jobs_runs import (
    render_job_run,
    render_jobs_history,
    render_jobs_tail,
)
from lily.cli.renderers.jobs_scheduler import (
    render_jobs_scheduler_action,
    render_jobs_scheduler_status,
)
from lily.cli.renderers.memory import render_memory_list
from lily.cli.renderers.persona import (
    render_persona_list,
    render_persona_set,
    render_persona_show,
)
from lily.cli.result_codes import (
    BLUEPRINT_DIAGNOSTIC_CODES,
    HIDE_DATA_CODES,
    SECURITY_ALERT_CODES,
)
from lily.commands.types import CommandResult, CommandStatus


class CliRenderer:
    """Render command results with Rich structures and code-based policies."""

    def __init__(self, *, console: Console) -> None:
        """Store console used for rendering.

        Args:
            console: Rich console used for output rendering.
        """
        self._console = console

    def render(self, result: CommandResult) -> None:
        """Render one command result.

        Args:
            result: Structured command result.
        """
        if result.status == CommandStatus.OK:
            if self._render_rich_success(result):
                return
            self._console.print(
                Panel(
                    Markdown(result.message),
                    title=f"Lily [{result.code}]",
                    border_style="green",
                    expand=True,
                )
            )
            if result.data and result.code not in HIDE_DATA_CODES:
                self._console.print(
                    Panel(
                        JSON.from_data(result.data),
                        title="Data",
                        border_style="cyan",
                        expand=True,
                    )
                )
            return
        if self._render_blueprint_diagnostic(result):
            return
        self._console.print(
            Panel(
                (
                    "[bold white on red] SECURITY ALERT [/bold white on red]\n"
                    f"Code: {result.code}\n{result.message}"
                )
                if result.code in SECURITY_ALERT_CODES
                else result.message,
                title=(
                    "SECURITY ALERT"
                    if result.code in SECURITY_ALERT_CODES
                    else f"Error [{result.code}]"
                ),
                border_style=(
                    "bold bright_red"
                    if result.code in SECURITY_ALERT_CODES
                    else "bold red"
                ),
                expand=True,
            )
        )
        if result.data:
            self._console.print(
                Panel(
                    JSON.from_data(result.data),
                    title="Data",
                    border_style="cyan",
                    expand=True,
                )
            )

    def _render_blueprint_diagnostic(self, result: CommandResult) -> bool:
        """Render high-visibility diagnostics for blueprint runtime failures.

        Args:
            result: Command result payload.

        Returns:
            ``True`` when diagnostic panel was rendered.
        """
        if result.code not in BLUEPRINT_DIAGNOSTIC_CODES:
            return False
        guidance = (
            "Check blueprint id, bindings schema, and registered dependencies.\n"
            "Review compile/execute logs and re-run after contract fixes."
        )
        self._console.print(
            Panel(
                (
                    "[bold black on yellow] BLUEPRINT DIAGNOSTIC "
                    "[/bold black on yellow]\n"
                    f"Code: {result.code}\n"
                    f"{result.message}\n\n"
                    f"{guidance}"
                ),
                title="Blueprint Diagnostic",
                border_style="bold yellow",
                expand=True,
            )
        )
        if result.data:
            self._console.print(
                Panel(
                    JSON.from_data(result.data),
                    title="Data",
                    border_style="cyan",
                    expand=True,
                )
            )
        return True

    def _render_rich_success(self, result: CommandResult) -> bool:
        """Render specialized success view for selected command result codes.

        Args:
            result: Command result payload.

        Returns:
            ``True`` when a specialized render path handled the result.
        """
        renderers: dict[str, Callable[[Console, CommandResult], bool]] = {
            "persona_listed": render_persona_list,
            "persona_set": render_persona_set,
            "persona_shown": render_persona_show,
            "agent_listed": render_agent_list,
            "agent_set": render_agent_set,
            "agent_shown": render_agent_show,
            "memory_listed": render_memory_list,
            "memory_langmem_listed": render_memory_list,
            "memory_evidence_listed": render_evidence_list,
            "jobs_listed": render_jobs_list,
            "jobs_empty": render_jobs_list,
            "job_run_completed": render_job_run,
            "jobs_tailed": render_jobs_tail,
            "jobs_tail_empty": render_jobs_tail,
            "jobs_history": render_jobs_history,
            "jobs_history_empty": render_jobs_history,
            "jobs_scheduler_status": render_jobs_scheduler_status,
            "jobs_paused": render_jobs_scheduler_action,
            "jobs_resumed": render_jobs_scheduler_action,
            "jobs_disabled": render_jobs_scheduler_action,
        }
        renderer = renderers.get(result.code)
        if renderer is None:
            return False
        return renderer(self._console, result)
