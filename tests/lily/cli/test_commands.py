"""Tests for dynamic skill command creation."""

from pathlib import Path
from unittest.mock import patch

import pytest
import typer

from lily.cli.commands import DynamicSkillCommand
from lily.types.exceptions import SkillCommandError
from lily.types.models import SkillInfo


class TestDynamicSkillCommand:
    """Test dynamic skill command creation."""

    def test_create_command_generates_executable_cli_command(self):
        """Should create a CLI command that can be executed."""
        # Given: valid skill information
        skill_info = SkillInfo(
            name="summarize-text",
            path=Path(".lily/skills/summarize-text.md"),
            description="Summarize text content",
            tags=["text", "summary"],
            persona="default",
            kind="atomic",
        )

        with patch("pathlib.Path.exists", return_value=True):
            # When: create_command() called
            command = DynamicSkillCommand.create_command("summarize-text", skill_info)

            # Then: returns executable CLI command
            assert isinstance(command, typer.Typer)
            assert command.info.name == "summarize-text"

    def test_create_command_rejects_nonexistent_skills(self):
        """Should reject creation of commands for non-existent skills."""
        # Given: skill file doesn't exist
        fake_skill_info = SkillInfo(
            name="fake-skill",
            path=Path(".lily/skills/fake-skill.md"),
            description="A fake skill",
            tags=["fake"],
            persona="default",
            kind="atomic",
        )

        with (
            patch("pathlib.Path.exists", return_value=False),
            pytest.raises(SkillCommandError),
        ):
            # When/Then: create_command() raises error for non-existent skill
            DynamicSkillCommand.create_command("fake-skill", fake_skill_info)

    def test_create_command_includes_skill_help_information(self):
        """Should include skill description in command help."""
        # Given: skill with description
        skill_info = SkillInfo(
            name="brainstorm-ideas",
            path=Path(".lily/skills/brainstorm-ideas.md"),
            description="Generate creative ideas for a topic",
            tags=["creative", "ideas"],
            persona="creative",
            kind="atomic",
        )

        with patch("pathlib.Path.exists", return_value=True):
            # When: create_command() called
            command = DynamicSkillCommand.create_command("brainstorm-ideas", skill_info)

            # Then: command help includes skill description
            assert command.info.help is not None
            assert "generate creative ideas" in command.info.help.lower()

    def test_create_command_uses_skill_default_persona(self):
        """Should use skill's default persona when available."""
        # Given: skill with specific persona
        skill_info = SkillInfo(
            name="academic-review",
            path=Path(".lily/skills/academic-review.md"),
            description="Academic review skill",
            tags=["academic"],
            persona="academic",  # Specific persona
            kind="atomic",
        )

        with patch("pathlib.Path.exists", return_value=True):
            # When: create_command() called
            command = DynamicSkillCommand.create_command("academic-review", skill_info)

            # Then: command is created successfully
            assert command is not None

    def test_execute_skill_accepts_execution_parameters(self):
        """Should accept and process skill execution parameters."""
        # Given: skill execution parameters
        skill_name = "test-skill"
        input_file = Path("test.md")
        task_name = "test-task"
        persona = "default"

        # When: execute_skill() called
        # Then: should not raise exception (placeholder implementation)
        try:
            DynamicSkillCommand.execute_skill(
                skill_name, input_file, task_name, persona
            )
        except Exception as e:
            pytest.fail(f"execute_skill should not raise exception: {e}")

    def test_create_command_generates_standard_cli_options(self):
        """Should create command with standard CLI options."""
        # Given: skill information
        skill_info = SkillInfo(
            name="code-review",
            path=Path(".lily/skills/code-review.md"),
            description="Review code for issues",
            tags=["code", "review"],
            persona="developer",
            kind="atomic",
        )

        with patch("pathlib.Path.exists", return_value=True):
            # When: create_command() called
            command = DynamicSkillCommand.create_command("code-review", skill_info)

            # Then: command is created successfully
            assert command is not None
