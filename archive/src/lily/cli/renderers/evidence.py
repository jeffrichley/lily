"""Semantic evidence Rich renderer helper."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from lily.commands.types import CommandResult


def render_evidence_list(console: Console, result: CommandResult) -> bool:
    """Render `/memory evidence show` records with citation + score.

    Args:
        console: Rich console.
        result: Command result payload.

    Returns:
        ``True`` when rendered.
    """
    data = result.data if isinstance(result.data, dict) else None
    raw_records = data.get("records") if data is not None else None
    if not isinstance(raw_records, list):
        return False
    table = Table(
        title=f"Semantic Evidence ({len(raw_records)} hits)",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Score", style="green", no_wrap=True)
    table.add_column("Citation", style="magenta")
    table.add_column("Snippet")
    for row in _evidence_rows(raw_records):
        table.add_row(*row)
    console.print(table)
    console.print(
        Panel(
            "Evidence results are non-canonical context. "
            "Structured long-term memory remains the source of truth.",
            title="Evidence Policy",
            border_style="yellow",
            expand=True,
        )
    )
    return True


def _evidence_rows(raw_records: list[object]) -> tuple[tuple[str, str, str], ...]:
    """Convert raw evidence payload into table rows.

    Args:
        raw_records: Raw records payload.

    Returns:
        Parsed evidence table rows.
    """
    rows: list[tuple[str, str, str]] = []
    for record in raw_records:
        if not isinstance(record, dict):
            continue
        score = float(record.get("score", 0.0))
        rows.append(
            (
                f"{score:.3f}",
                str(record.get("citation", "")),
                str(record.get("content", "")),
            )
        )
    return tuple(rows)
