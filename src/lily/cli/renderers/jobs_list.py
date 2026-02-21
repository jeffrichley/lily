"""Jobs list/diagnostics Rich renderer helpers."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from lily.commands.types import CommandResult


def render_jobs_list(console: Console, result: CommandResult) -> bool:
    """Render `/jobs list` output as table + optional diagnostics.

    Args:
        console: Rich console.
        result: Command result payload.

    Returns:
        ``True`` when rendered.
    """
    data = result.data if isinstance(result.data, dict) else None
    raw_jobs = data.get("jobs") if data is not None else None
    if not isinstance(raw_jobs, list):
        return False
    _render_jobs_table(console, raw_jobs)
    _render_job_diagnostics(console, data)
    return True


def _render_jobs_table(console: Console, raw_jobs: list[object]) -> None:
    if not raw_jobs:
        console.print(
            Panel(
                "No jobs found in `.lily/jobs`.",
                title="Jobs",
                border_style="yellow",
                expand=True,
            )
        )
        return
    table = Table(title="Jobs", show_header=True, header_style="bold cyan")
    table.add_column("Job ID", style="bold")
    table.add_column("Title")
    table.add_column("Target", style="magenta")
    table.add_column("Trigger", style="green")
    for row in raw_jobs:
        if not isinstance(row, dict):
            continue
        table.add_row(
            str(row.get("id", "")),
            str(row.get("title", "")),
            str(row.get("target_id", "")),
            str(row.get("trigger", "")),
        )
    console.print(table)


def _render_job_diagnostics(console: Console, data: dict[str, object] | None) -> None:
    raw_diagnostics = data.get("diagnostics") if data is not None else None
    if not isinstance(raw_diagnostics, list) or not raw_diagnostics:
        return
    lines = []
    for diag in raw_diagnostics:
        if not isinstance(diag, dict):
            continue
        lines.append(
            f"- {diag.get('path', '')} [{diag.get('code', '')}] "
            f"{diag.get('message', '')}"
        )
    console.print(
        Panel(
            "\n".join(lines) if lines else "No diagnostics.",
            title="Job Diagnostics",
            border_style="yellow",
            expand=True,
        )
    )
