"""Main CLI entry point for Lily."""

import logging
from pathlib import Path

import typer
from rich.console import Console
from rich.logging import RichHandler

from lily.cli.commands import DynamicSkillCommand
from lily.core.registry import SkillRegistry
from lily.types.models import ProjectContext

# Set up rich logging
console = Console()
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(console=console, rich_tracebacks=True)],
)
logger = logging.getLogger("lily.cli.main")

app = typer.Typer(
    name="lily",
    help="AI-first operating system for thought and action",
    add_completion=True,
    rich_markup_mode="rich",
    no_args_is_help=True,
)


def get_project_context() -> ProjectContext:
    """Get the current project context."""
    return ProjectContext(project_root=Path.cwd(), persona="default")


def discover_and_register_skills():
    """Discover skills and register them as CLI commands."""
    try:
        context = get_project_context()
        registry = SkillRegistry()
        skills = registry.discover_skills(context)

        for skill_info in skills:
            try:
                command = DynamicSkillCommand.create_command(
                    skill_info.name, skill_info
                )
                app.add_typer(command)
                logger.debug(f"Registered skill command: {skill_info.name}")
            except Exception as e:
                logger.warning(f"Failed to register skill {skill_info.name}: {e}")

        logger.info(f"Registered {len(skills)} skill commands")

    except Exception as e:
        logger.error(f"Failed to discover skills: {e}")


# Register discovered skills as commands
discover_and_register_skills()


@app.command()
def run(
    skill_name: str = typer.Argument(..., help="Name of the skill to run"),
    input_file: str = typer.Option(None, "--input", "-i", help="Input file to process"),
    task_name: str = typer.Option(None, "--task", "-t", help="Task name for tracking"),
    persona: str = typer.Option("default", "--persona", "-p", help="Persona to use"),
):
    """Run a skill (legacy command - use direct skill commands instead)."""
    typer.echo(f"Running skill: {skill_name}")
    if input_file:
        typer.echo(f"Input file: {input_file}")
    if task_name:
        typer.echo(f"Task name: {task_name}")
    typer.echo(f"Persona: {persona}")
    typer.echo(
        "Note: Consider using direct skill commands like 'lily summarize-text' instead"
    )


@app.command()
def skills():
    """List all available skills."""
    try:
        context = get_project_context()
        registry = SkillRegistry()
        skills = registry.discover_skills(context)

        if not skills:
            typer.echo("No skills found.")
            return

        typer.echo("📚 Found {} skills:".format(len(skills)))
        for skill in skills:
            tags_str = ", ".join(skill.tags) if skill.tags else "no tags"
            typer.echo(f"  • {skill.name} - {skill.description or 'No description'}")
            typer.echo(f"    Tags: {tags_str}")
            typer.echo()

    except Exception as e:
        logger.error(f"Failed to list skills: {e}")
        raise typer.Exit(1) from e


@app.command()
def clear_cache():
    """Clear the skill cache."""
    try:
        registry = SkillRegistry()
        registry.clear_cache()
        typer.echo("✅ Skill cache cleared")
    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")
        raise typer.Exit(1) from e


def main():
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
