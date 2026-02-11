"""Minimal Typer CLI. Layer 0: create run only."""

from pathlib import Path

import typer
from rich.console import Console

from lily.kernel.run import create_run_with_optional_work_order

app = typer.Typer()
run_app = typer.Typer()
app.add_typer(run_app, name="run")
console = Console()


@run_app.command("new")
def run_new(
    work_order: Path | None = typer.Option(
        None,
        "--work-order",
        exists=True,
        file_okay=True,
        dir_okay=False,
        resolve_path=True,
        help="Attach a work order file as a file artifact.",
    ),
) -> None:
    """Create a new run. Optionally attach a work order file."""
    workspace_root = Path.cwd()
    info = create_run_with_optional_work_order(
        workspace_root, work_order_path=work_order
    )
    console.print(f"Created run [bold]{info.run_id}[/bold]")
    console.print(f"Path: {info.run_root}")
    if info.work_order_ref is not None:
        console.print(f"Attached work order: {info.work_order_ref.artifact_id}")


if __name__ == "__main__":
    app()
