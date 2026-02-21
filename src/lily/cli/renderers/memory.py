"""Memory list Rich renderer helper."""

from __future__ import annotations

from rich.console import Console
from rich.table import Table

from lily.commands.types import CommandResult


def render_memory_list(console: Console, result: CommandResult) -> bool:
    """Render `/memory show` records in table form.

    Args:
        console: Rich console.
        result: Command result payload.

    Returns:
        ``True`` when rendered.
    """
    rows = _memory_rows(result)
    if rows is None:
        return False
    table = Table(
        title=f"Memory ({len(rows)} records)",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("ID", style="green")
    table.add_column("Namespace", style="magenta", no_wrap=True)
    table.add_column("Content")
    for row in rows:
        table.add_row(*row)
    console.print(table)
    return True


def _memory_rows(result: CommandResult) -> tuple[tuple[str, str, str], ...] | None:
    """Extract memory table rows from command result payload.

    Args:
        result: Command result payload.

    Returns:
        Parsed row tuples, or ``None`` when payload shape is incompatible.
    """
    data = result.data
    if not isinstance(data, dict):
        return None
    raw_records = data.get("records")
    if not isinstance(raw_records, list):
        return None
    return tuple(
        (
            str(record.get("id", "")),
            str(record.get("namespace", "")),
            str(record.get("content", "")),
        )
        for record in raw_records
        if isinstance(record, dict)
    )
