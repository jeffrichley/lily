"""Minimal Typer CLI. Layer 0: create run. Layer 2: run graph."""

import json
from pathlib import Path
from types import EllipsisType
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from lily.kernel.graph_models import GraphSpec
from lily.kernel.paths import get_run_root
from lily.kernel.run import create_run_with_optional_work_order
from lily.kernel.run_directory import create_run_directory
from lily.kernel.runner import run_graph

app = typer.Typer()
run_app = typer.Typer()
app.add_typer(run_app, name="run")
console = Console()


@run_app.command("new")
def run_new(
    work_order: Annotated[
        Path | None,
        typer.Option(
            "--work-order",
            exists=True,
            file_okay=True,
            dir_okay=False,
            resolve_path=True,
            help="Attach a work order file as a file artifact.",
        ),
    ] = None,
) -> None:
    """Create a new run. Optionally attach a work order file.

    Args:
        work_order: Optional path to a work order file to attach as artifact.
    """
    workspace_root = Path.cwd()
    info = create_run_with_optional_work_order(
        workspace_root, work_order_path=work_order
    )
    console.print(f"Created run [bold]{info.run_id}[/bold]")
    console.print(f"Path: {info.run_root}")
    if info.work_order_ref is not None:
        console.print(f"Attached work order: {info.work_order_ref.artifact_id}")


@run_app.command("graph")
def run_graph_cmd(
    run_id: str = typer.Option(..., "--run-id", help="Run ID (from lily run new)."),
    graph_path: Annotated[
        Path | EllipsisType,
        typer.Option(
            "--graph",
            exists=True,
            file_okay=True,
            dir_okay=False,
            resolve_path=True,
            help="Path to GraphSpec JSON file.",
        ),
    ] = ...,
) -> None:
    """Run a graph spec for a run.

    Args:
        run_id: Run ID (from lily run new).
        graph_path: Path to GraphSpec JSON file.
    """
    assert isinstance(graph_path, Path), "--graph is required"
    workspace_root = Path.cwd()
    run_root = get_run_root(workspace_root, run_id)
    if not run_root.exists():
        create_run_directory(workspace_root, run_id)

    data = json.loads(graph_path.read_text(encoding="utf-8"))
    graph = GraphSpec.model_validate(data)
    state = run_graph(run_root, graph)

    console.print(f"Run [bold]{run_id}[/bold]: {state.status}")
    table = Table(header_style="bold")
    table.add_column("Step", style="cyan")
    table.add_column("Status")
    table.add_column("Attempts")
    for step_id, rec in state.step_records.items():
        table.add_row(step_id, rec.status, str(rec.attempts))
    console.print(table)


if __name__ == "__main__":
    app()
