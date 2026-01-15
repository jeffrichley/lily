"""CLI entry point for Lily using Typer."""

import sys
from pathlib import Path
from typing import Optional

import typer

from lily.core.application.commands.init import InitCommand
from lily.core.application.commands.status import StatusCommand
from lily.core.infrastructure.storage import Logger, Storage

app = typer.Typer(
    name="lily",
    help="Lily: A project orchestration framework",
    add_completion=False,
)


@app.command()
def init(
    project_name: Optional[str] = typer.Argument(None, help="Name of the project"),
    here: bool = typer.Option(
        False, "--here", help="Use current directory name as project name"
    ),
) -> None:
    """Initialize a new Lily project.

    Either PROJECT_NAME argument or --here flag must be provided.
    If --here is specified, the current directory name is used as the project name.
    """
    # Determine project name
    root_path = Path.cwd()

    if here:
        # Use current directory name as project name (ignore project_name argument if provided)
        project_name = root_path.name
    elif project_name:
        # Use provided project name
        pass
    else:
        # Neither provided - error
        typer.echo(
            "Error: PROJECT_NAME argument is required unless --here is specified.",
            err=True,
        )
        typer.echo("Usage: lily init [PROJECT_NAME] [--here]", err=True)
        sys.exit(1)

    # Initialize dependencies
    storage = Storage()
    log_jsonl_path = root_path / ".lily" / "log.jsonl"
    log_md_path = root_path / ".lily" / "log.md"
    logger = Logger(storage, log_jsonl_path, log_md_path)

    # Get version from package (hardcoded for now, can be improved)
    version = "0.1.0"

    # Create and execute command
    command = InitCommand(storage, logger, version)

    try:
        result = command.execute(project_name, root_path)
        if result.success:
            typer.echo(result.message)
            sys.exit(0)
        else:
            # Error result - message already formatted with error details and ✗ prefix
            typer.echo(result.message, err=True)
            sys.exit(1)
    except ValueError as e:
        # Validation error - format with clear message
        error_msg = str(e)
        if "permission" in error_msg.lower() or "cannot write" in error_msg.lower():
            typer.echo("✗ Failed to initialize project: Permission denied", err=True)
            typer.echo(f"\n{error_msg}", err=True)
            typer.echo("\nPlease check write permissions and try again.", err=True)
        elif "invalid characters" in error_msg.lower():
            typer.echo("✗ Failed to initialize project: Invalid project name", err=True)
            typer.echo(f"\n{error_msg}", err=True)
        elif "cannot be empty" in error_msg.lower():
            typer.echo(f"✗ Failed to initialize project: {error_msg}", err=True)
        else:
            typer.echo(f"✗ Failed to initialize project: {error_msg}", err=True)
        sys.exit(1)
    except PermissionError as e:
        typer.echo("✗ Failed to initialize project: Permission denied", err=True)
        typer.echo(f"\nError: {e}", err=True)
        typer.echo("\nPlease check write permissions and try again.", err=True)
        sys.exit(1)
    except OSError as e:
        typer.echo("✗ Failed to initialize project: System error", err=True)
        typer.echo(f"\nError: {e}", err=True)
        typer.echo(
            "\nPlease check file system permissions and available disk space.", err=True
        )
        sys.exit(1)
    except Exception as e:
        typer.echo(f"✗ Unexpected error: {e}", err=True)
        typer.echo(
            "\nIf this problem persists, please report it with the error message above.",
            err=True,
        )
        sys.exit(1)


@app.command()
def status() -> None:
    """Display project status and artifact information."""
    root_path = Path.cwd()

    # Initialize dependencies
    storage = Storage()

    # Create and execute command
    command = StatusCommand(storage)

    try:
        # Validate first
        command.validate(root_path)
        result = command.execute(root_path)
        if result.success:
            typer.echo(result.message)
            sys.exit(0)
        else:
            # Error result - message already formatted with error details
            typer.echo(result.message, err=True)
            sys.exit(1)
    except ValueError as e:
        # Validation error - format with clear message
        error_msg = str(e)
        if "not a lily project" in error_msg.lower():
            typer.echo("✗ Not a Lily project", err=True)
            typer.echo(f"\n{error_msg}", err=True)
            typer.echo("\nRun 'lily init' first to initialize a project.", err=True)
        else:
            typer.echo(f"✗ Failed to get status: {error_msg}", err=True)
        sys.exit(1)
    except FileNotFoundError as e:
        typer.echo("✗ Failed to get status: Required files not found", err=True)
        typer.echo(f"\nError: {e}", err=True)
        typer.echo("\nRun 'lily init' first to initialize a project.", err=True)
        sys.exit(1)
    except PermissionError as e:
        typer.echo("✗ Failed to get status: Permission denied", err=True)
        typer.echo(f"\nError: {e}", err=True)
        typer.echo("\nPlease check read permissions and try again.", err=True)
        sys.exit(1)
    except Exception as e:
        typer.echo(f"✗ Unexpected error: {e}", err=True)
        typer.echo(
            "\nIf this problem persists, please report it with the error message above.",
            err=True,
        )
        sys.exit(1)


def main() -> None:
    """Main entry point for CLI."""
    app()


if __name__ == "__main__":
    main()
