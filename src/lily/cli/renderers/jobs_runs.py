"""Jobs run/tail/history Rich renderer helpers."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from lily.commands.types import CommandResult


def render_job_run(console: Console, result: CommandResult) -> bool:
    """Render `/jobs run` success payload in concise panel.

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
    run_id = str(data.get("run_id", "")).strip()
    status = str(data.get("status", "")).strip()
    run_path = str(data.get("run_path", "")).strip()
    if not job_id or not run_id:
        return False
    console.print(
        Panel(
            (
                f"Job: [bold]{job_id}[/bold]\n"
                f"Run: [bold]{run_id}[/bold]\n"
                f"Status: [bold]{status}[/bold]\n"
                f"Artifacts: {run_path}"
            ),
            title="Job Run",
            border_style="green",
            expand=True,
        )
    )
    return True


def render_jobs_tail(console: Console, result: CommandResult) -> bool:
    """Render `/jobs tail` output in structured panel form.

    Args:
        console: Rich console.
        result: Command result payload.

    Returns:
        ``True`` when rendered.
    """
    payload = _jobs_tail_payload(result)
    if payload is None:
        return False
    job_id, run_id, lines = payload
    if run_id is None:
        console.print(
            Panel(
                f"Job: [bold]{job_id}[/bold]\nNo runs found yet.",
                title="Job Tail",
                border_style="yellow",
                expand=True,
            )
        )
        return True
    text = (
        "\n".join(str(line) for line in lines) if lines else "(events.jsonl is empty)"
    )
    console.print(
        Panel(
            f"Job: [bold]{job_id}[/bold]\nRun: [bold]{run_id}[/bold]\n\n{text}",
            title="Job Tail",
            border_style="cyan",
            expand=True,
        )
    )
    return True


def render_jobs_history(console: Console, result: CommandResult) -> bool:
    """Render `/jobs history` output in table form.

    Args:
        console: Rich console.
        result: Command result payload.

    Returns:
        ``True`` when rendered.
    """
    payload = _jobs_history_payload(result)
    if payload is None:
        return False
    job_id, rows = payload
    if not rows:
        console.print(
            Panel(
                f"Job: [bold]{job_id}[/bold]\nNo runs found yet.",
                title="Job History",
                border_style="yellow",
                expand=True,
            )
        )
        return True
    table = Table(
        title=f"Job History: {job_id}",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Run ID", style="bold")
    table.add_column("Status", style="green")
    table.add_column("Attempts", style="magenta", no_wrap=True)
    table.add_column("Started (UTC)")
    table.add_column("Ended (UTC)")
    for row in rows:
        table.add_row(*row)
    console.print(table)
    return True


def _jobs_tail_payload(
    result: CommandResult,
) -> tuple[str, object | None, tuple[object, ...]] | None:
    """Extract jobs tail payload from command result.

    Args:
        result: Command result payload.

    Returns:
        Jobs tail payload tuple, or ``None`` when payload is incompatible.
    """
    data = result.data
    if not isinstance(data, dict):
        return None
    job_id = str(data.get("job_id", "")).strip()
    if not job_id:
        return None
    run_id = data.get("run_id")
    if run_id is None:
        return job_id, None, ()
    lines = _coerce_tail_lines(data.get("lines"))
    if lines is None:
        return None
    return job_id, run_id, lines


def _jobs_history_payload(
    result: CommandResult,
) -> tuple[str, tuple[tuple[str, str, str, str, str], ...]] | None:
    """Extract jobs history rows from command result.

    Args:
        result: Command result payload.

    Returns:
        Job id and history rows tuple, or ``None`` when payload is incompatible.
    """
    data = result.data
    if not isinstance(data, dict):
        return None
    job_id = str(data.get("job_id", "")).strip()
    raw_entries = data.get("entries")
    if not job_id:
        return None
    if not isinstance(raw_entries, list):
        return None
    entries = _dict_entries(raw_entries)
    rows = tuple(
        (
            str(entry.get("run_id", "")),
            str(entry.get("status", "")),
            str(entry.get("attempt_count", "")),
            str(entry.get("started_at", "")),
            str(entry.get("ended_at", "")),
        )
        for entry in entries
    )
    return job_id, rows


def _coerce_tail_lines(raw_lines: object) -> tuple[object, ...] | None:
    """Normalize raw tail line payload.

    Args:
        raw_lines: Raw lines payload.

    Returns:
        Normalized line tuple, or ``None`` when payload is incompatible.
    """
    if not isinstance(raw_lines, list):
        return None
    return tuple(raw_lines)


def _dict_entries(raw_entries: list[object]) -> tuple[dict[str, object], ...]:
    """Filter raw entry payload to dictionaries only.

    Args:
        raw_entries: Raw entry payload.

    Returns:
        Dictionary-only entry tuple.
    """
    return tuple(entry for entry in raw_entries if isinstance(entry, dict))
