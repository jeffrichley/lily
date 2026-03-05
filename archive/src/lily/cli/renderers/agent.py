"""Agent command Rich renderer helpers."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from lily.commands.types import CommandResult


def render_agent_list(console: Console, result: CommandResult) -> bool:
    """Render `/agent list` in table form.

    Args:
        console: Rich console.
        result: Command result payload.

    Returns:
        ``True`` when rendered.
    """
    data = result.data if isinstance(result.data, dict) else None
    raw_rows = data.get("agents") if data is not None else None
    if not isinstance(raw_rows, list):
        return False
    table = Table(title="Agents", show_header=True, header_style="bold cyan")
    table.add_column("Active", style="green", no_wrap=True)
    table.add_column("Agent", style="bold")
    table.add_column("Summary")
    for row in raw_rows:
        if not isinstance(row, dict):
            continue
        table.add_row(
            "yes" if bool(row.get("active")) else "",
            str(row.get("agent", "")),
            str(row.get("summary", "")),
        )
    console.print(table)
    return True


def render_agent_set(console: Console, result: CommandResult) -> bool:
    """Render `/agent use` confirmation panel.

    Args:
        console: Rich console.
        result: Command result payload.

    Returns:
        ``True`` when rendered.
    """
    data = result.data if isinstance(result.data, dict) else None
    if data is None:
        return False
    agent = str(data.get("agent", "")).strip()
    if not agent:
        return False
    console.print(
        Panel(
            f"Active Agent: [bold]{agent}[/bold]",
            title="Agent Updated",
            border_style="green",
            expand=True,
        )
    )
    return True


def render_agent_show(console: Console, result: CommandResult) -> bool:
    """Render `/agent show` details panel.

    Args:
        console: Rich console.
        result: Command result payload.

    Returns:
        ``True`` when rendered.
    """
    data = result.data if isinstance(result.data, dict) else None
    if data is None:
        return False
    agent = str(data.get("agent", "")).strip()
    summary = str(data.get("summary", "")).strip()
    if not agent:
        return False
    console.print(
        Panel(
            f"Agent: [bold]{agent}[/bold]\nSummary: {summary}",
            title="Agent",
            border_style="green",
            expand=True,
        )
    )
    return True
