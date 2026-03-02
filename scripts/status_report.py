"""Render one command project/docs status summary for operators."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

ROOT = Path(__file__).resolve().parents[1]
STATUS_FILE = ROOT / "docs" / "dev" / "status.md"
ROADMAP_FILE = ROOT / "docs" / "dev" / "roadmap.md"
DEBT_FILE = ROOT / "docs" / "dev" / "debt" / "debt_tracker.md"
PLANS_DIR = ROOT / "docs" / "dev" / "plans"


@dataclass(frozen=True)
class DocMeta:
    """Minimal parsed frontmatter metadata."""

    status: str
    last_updated: str


def _frontmatter(path: Path) -> DocMeta:
    """Parse frontmatter for status and last_updated fields."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return DocMeta(status="unknown", last_updated="unknown")

    status = "unknown"
    last_updated = "unknown"
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if line.startswith("status:"):
            status = line.split(":", 1)[1].strip().strip('"')
        if line.startswith("last_updated:"):
            last_updated = line.split(":", 1)[1].strip().strip('"')
    return DocMeta(status=status, last_updated=last_updated)


def _count_open_checkboxes(path: Path) -> int:
    """Count markdown unchecked checkboxes in one file."""
    text = path.read_text(encoding="utf-8")
    return len(re.findall(r"^- \[ \] ", text, flags=re.MULTILINE))


def _current_focus_items() -> list[str]:
    """Extract `Current Focus` bullets from status diary."""
    text = STATUS_FILE.read_text(encoding="utf-8")
    marker = "## Current Focus"
    if marker not in text:
        return []
    section = text.split(marker, 1)[1]
    section = section.split("\n## ", 1)[0]
    return [
        line.strip()[2:].strip()
        for line in section.splitlines()
        if line.strip().startswith("- ")
    ]


def _git_state() -> tuple[str, bool]:
    """Return branch and dirty-state from git."""
    branch = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    ).stdout.strip()
    dirty = bool(
        subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        ).stdout.strip()
    )
    return (branch or "unknown", dirty)


def main() -> int:
    """Render status report."""
    console = Console()

    status_meta = _frontmatter(STATUS_FILE)
    roadmap_meta = _frontmatter(ROADMAP_FILE)
    debt_meta = _frontmatter(DEBT_FILE)
    open_debt = _count_open_checkboxes(DEBT_FILE)
    branch, dirty = _git_state()

    console.print(
        Panel(
            (
                f"Branch: [bold]{branch}[/bold]\n"
                f"Working tree: [bold]{'dirty' if dirty else 'clean'}[/bold]\n"
                f"Open debt items: [bold]{open_debt}[/bold]"
            ),
            title="Lily Status",
            border_style="cyan",
            expand=True,
        )
    )

    docs_table = Table(
        title="Canonical Docs", show_header=True, header_style="bold cyan"
    )
    docs_table.add_column("Surface")
    docs_table.add_column("Path")
    docs_table.add_column("Status")
    docs_table.add_column("Last Updated")
    docs_table.add_row(
        "Status Diary",
        "docs/dev/status.md",
        status_meta.status,
        status_meta.last_updated,
    )
    docs_table.add_row(
        "Roadmap", "docs/dev/roadmap.md", roadmap_meta.status, roadmap_meta.last_updated
    )
    docs_table.add_row(
        "Debt Tracker",
        "docs/dev/debt/debt_tracker.md",
        debt_meta.status,
        debt_meta.last_updated,
    )
    console.print(docs_table)

    plan_table = Table(
        title="Execution Plans", show_header=True, header_style="bold cyan"
    )
    plan_table.add_column("Plan")
    plan_table.add_column("Lifecycle")
    plan_table.add_column("Open Tasks")
    for plan in sorted(PLANS_DIR.glob("*_execution_plan.md")):
        meta = _frontmatter(plan)
        plan_table.add_row(plan.name, meta.status, str(_count_open_checkboxes(plan)))
    console.print(plan_table)

    focus = _current_focus_items()
    focus_text = (
        "\n".join(f"- {item}" for item in focus)
        if focus
        else "No `Current Focus` entries found."
    )
    console.print(
        Panel(focus_text, title="Current Focus", border_style="green", expand=True)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
