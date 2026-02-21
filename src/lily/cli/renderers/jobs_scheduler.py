"""Jobs scheduler status/action Rich renderer helpers."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from lily.commands.types import CommandResult


def render_jobs_scheduler_status(console: Console, result: CommandResult) -> bool:
    """Render `/jobs status` diagnostics in table/panel form.

    Args:
        console: Rich console.
        result: Command result payload.

    Returns:
        ``True`` when rendered.
    """
    payload = _scheduler_status_payload(result)
    if payload is None:
        return False
    started, registered_jobs, sqlite_path, states = payload
    console.print(
        Panel(
            (
                f"Started: [bold]{started}[/bold]\n"
                f"Registered Jobs: [bold]{registered_jobs}[/bold]\n"
                f"State DB: [bold]{sqlite_path}[/bold]"
            ),
            title="Scheduler Status",
            border_style="cyan",
            expand=True,
        )
    )
    if not states:
        return True
    table = Table(
        title="Scheduler Job States",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Job ID", style="bold")
    table.add_column("State", style="green")
    table.add_column("Updated (UTC)")
    for row in states:
        table.add_row(*row)
    console.print(table)
    return True


def render_jobs_scheduler_action(console: Console, result: CommandResult) -> bool:
    """Render scheduler lifecycle action confirmation panel.

    Args:
        console: Rich console.
        result: Command result payload.

    Returns:
        ``True`` when rendered.
    """
    data = result.data if isinstance(result.data, dict) else None
    if data is None:
        return False
    job_id = str(data.get("job_id", "")).strip()
    action = str(data.get("action", "")).strip()
    if not job_id or not action:
        return False
    console.print(
        Panel(
            f"Job: [bold]{job_id}[/bold]\nAction: [bold]{action}[/bold]",
            title="Scheduler Updated",
            border_style="green",
            expand=True,
        )
    )
    return True


def _scheduler_status_payload(
    result: CommandResult,
) -> tuple[str, str, str, tuple[tuple[str, str, str], ...]] | None:
    """Extract scheduler status panel/table payload from result data.

    Args:
        result: Command result payload.

    Returns:
        Scheduler status tuple, or ``None`` when payload is incompatible.
    """
    data = result.data if isinstance(result.data, dict) else None
    if data is None:
        return None
    started = "yes" if bool(data.get("started")) else "no"
    registered_jobs = str(data.get("registered_jobs", "0"))
    sqlite_path = str(data.get("sqlite_path", ""))
    states = _scheduler_state_rows(data.get("states"))
    return started, registered_jobs, sqlite_path, states


def _scheduler_state_rows(raw_states: object) -> tuple[tuple[str, str, str], ...]:
    """Convert scheduler state payload to table rows.

    Args:
        raw_states: Raw scheduler states payload.

    Returns:
        Parsed scheduler state rows.
    """
    if not isinstance(raw_states, list):
        return ()
    return tuple(
        (
            str(row.get("job_id", "")),
            str(row.get("state", "")),
            str(row.get("updated_at", "")),
        )
        for row in raw_states
        if isinstance(row, dict)
    )
