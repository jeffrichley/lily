"""Dynamic skill command creation for CLI."""

import logging
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.logging import RichHandler

from lily.types.exceptions import SkillCommandError
from lily.types.models import SkillInfo

# Set up rich logging
console = Console()
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(console=console, rich_tracebacks=True)],
)
logger = logging.getLogger("lily.cli.commands")


class DynamicSkillCommand:
    """Creates dynamic Typer commands for skills."""

    @staticmethod
    def create_command(skill_name: str, skill_info: SkillInfo) -> typer.Typer:
        """Create a Typer command for a skill."""
        # Validate skill file exists
        if not skill_info.path.exists():
            raise SkillCommandError(f"Skill file {skill_info.path} does not exist")

        # Create the command
        app = typer.Typer(
            name=skill_name,
            help=skill_info.description or f"Execute the {skill_name} skill",
            no_args_is_help=True,
            rich_markup_mode="rich",
        )

        # Add the command function
        @app.command()
        def skill_command(
            input_file: Optional[Path] = typer.Option(
                None, "--input", "-i", help="Input file to process"
            ),
            task_name: Optional[str] = typer.Option(
                None, "--task", "-t", help="Task name for tracking"
            ),
            persona: str = typer.Option(
                skill_info.persona or "default",
                "--persona",
                "-p",
                help="Persona to use for execution",
            ),
        ):
            """Execute the skill with given parameters."""
            DynamicSkillCommand.execute_skill(
                skill_name, input_file, task_name, persona
            )

        return app

    @staticmethod
    def execute_skill(
        skill_name: str,
        input_file: Optional[Path],
        task_name: Optional[str],
        persona: str,
    ) -> None:
        """Execute a skill with given parameters."""
        # Placeholder implementation - will be replaced with actual skill execution
        logger.info(f"Executing skill: {skill_name}")
        logger.info(f"Input file: {input_file}")
        logger.info(f"Task name: {task_name}")
        logger.info(f"Persona: {persona}")

        # TODO: Implement actual skill execution
        # 1. Load skill content
        # 2. Apply persona
        # 3. Substitute input
        # 4. Execute with LLM
        # 5. Save results to .lily/tasks/

        console.print(f"✨ [green]Skill '{skill_name}' would be executed here[/green]")
        console.print(f"📥 Input: {input_file or 'None'}")
        console.print(f"📋 Task: {task_name or 'Auto-generated'}")
        console.print(f"🧠 Persona: {persona}")
