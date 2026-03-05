"""Persona command Rich renderer helpers."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from lily.commands.types import CommandResult


def render_persona_list(console: Console, result: CommandResult) -> bool:
    """Render `/persona list` in table form.

    Args:
        console: Rich console.
        result: Command result payload.

    Returns:
        ``True`` when rendered.
    """
    rows = _persona_rows(result)
    if rows is None:
        return False
    table = Table(title="Personas", show_header=True, header_style="bold cyan")
    table.add_column("Active", style="green", no_wrap=True)
    table.add_column("Persona", style="bold")
    table.add_column("Default Style", style="magenta")
    table.add_column("Summary")
    for row in rows:
        table.add_row(*row)
    console.print(table)
    return True


def _persona_rows(
    result: CommandResult,
) -> tuple[tuple[str, str, str, str], ...] | None:
    """Extract persona table rows from command result payload.

    Args:
        result: Command result payload.

    Returns:
        Parsed row tuples, or ``None`` when payload shape is incompatible.
    """
    data = result.data
    if not isinstance(data, dict):
        return None
    raw_rows = data.get("personas")
    if not isinstance(raw_rows, list):
        return None
    return tuple(
        (
            _active_label(row),
            str(row.get("persona", "")),
            str(row.get("default_style", "")),
            str(row.get("summary", "")),
        )
        for row in raw_rows
        if isinstance(row, dict)
    )


def _active_label(row: dict[str, object]) -> str:
    """Render active marker label for persona rows.

    Args:
        row: Persona row payload.

    Returns:
        Active marker string.
    """
    return "yes" if bool(row.get("active")) else ""


def render_persona_set(console: Console, result: CommandResult) -> bool:
    """Render `/persona use` confirmation panel.

    Args:
        console: Rich console.
        result: Command result payload.

    Returns:
        ``True`` when rendered.
    """
    data = result.data if isinstance(result.data, dict) else None
    if data is None:
        return False
    persona = str(data.get("persona", "")).strip()
    style = str(data.get("style", "")).strip()
    if not persona or not style:
        return False
    console.print(
        Panel(
            f"Active Persona: [bold]{persona}[/bold]\nStyle: [bold]{style}[/bold]",
            title="Persona Updated",
            border_style="green",
            expand=True,
        )
    )
    return True


def render_persona_show(console: Console, result: CommandResult) -> bool:
    """Render `/persona show` details + instructions.

    Args:
        console: Rich console.
        result: Command result payload.

    Returns:
        ``True`` when rendered.
    """
    data = result.data if isinstance(result.data, dict) else None
    if data is None:
        return False
    persona = str(data.get("persona", "")).strip()
    summary = str(data.get("summary", "")).strip()
    default_style = str(data.get("default_style", "")).strip()
    effective_style = str(data.get("effective_style", "")).strip()
    instructions = str(data.get("instructions", "")).strip()
    if not persona:
        return False
    details = Table(show_header=False, box=None, expand=True)
    details.add_column("Field", style="bold cyan", no_wrap=True)
    details.add_column("Value")
    details.add_row("Persona", persona)
    details.add_row("Summary", summary)
    details.add_row("Default Style", default_style)
    details.add_row("Effective Style", effective_style)
    console.print(Panel(details, title="Persona", border_style="green", expand=True))
    if instructions:
        console.print(
            Panel(
                instructions,
                title="Instructions",
                border_style="cyan",
                expand=True,
            )
        )
    return True
