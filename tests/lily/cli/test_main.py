"""Tests for main CLI functionality."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from lily.cli.main import discover_and_register_skills, get_project_context
from lily.types.exceptions import SkillCommandError
from lily.types.models import ProjectContext


class TestMainCLI:
    """Test main CLI functionality."""

    def test_get_project_context_returns_current_project_context(self):
        """Should return context for current project directory."""
        # Given: current working directory
        current_dir = Path.cwd()

        # When: get_project_context() called
        context = get_project_context()

        # Then: returns context with current directory as project root
        assert isinstance(context, ProjectContext)
        assert context.project_root == current_dir

    def test_discover_and_register_skills_registers_all_discovered_skills(
        self, mock_command_class, mock_registry_class
    ):
        """Should register all discovered skills as CLI commands."""
        # Given: multiple skills are discovered
        skill_info1 = MagicMock()
        skill_info1.name = "summarize-text"
        skill_info1.path = Path(".lily/skills/summarize-text.md")

        skill_info2 = MagicMock()
        skill_info2.name = "brainstorm-ideas"
        skill_info2.path = Path(".lily/skills/brainstorm-ideas.md")

        mock_registry = mock_registry_class.return_value
        mock_registry.discover_skills.return_value = [skill_info1, skill_info2]

        mock_command = MagicMock()
        mock_command_class.create_command.return_value = mock_command

        # When: discover_and_register_skills() called
        discover_and_register_skills()

        # Then: all discovered skills are registered
        assert mock_registry.discover_skills.call_count == 1
        assert mock_command_class.create_command.call_count == 2

    def test_discover_and_register_skills_handles_empty_skill_list(
        self, mock_registry_class
    ):
        """Should handle case when no skills are discovered."""
        # Given: no skills are discovered
        mock_registry = mock_registry_class.return_value
        mock_registry.discover_skills.return_value = []

        # When: discover_and_register_skills() called
        discover_and_register_skills()

        # Then: discovery completes without errors
        assert mock_registry.discover_skills.call_count == 1

    def test_discover_and_register_skills_continues_on_individual_failures(
        self, mock_command_class, mock_registry_class
    ):
        """Should continue processing when individual skill registration fails."""
        # Given: one skill fails to register
        skill_info1 = MagicMock()
        skill_info1.name = "valid-skill"

        skill_info2 = MagicMock()
        skill_info2.name = "failing-skill"

        mock_registry = mock_registry_class.return_value
        mock_registry.discover_skills.return_value = [skill_info1, skill_info2]

        # First skill succeeds, second fails
        mock_command_class.create_command.side_effect = [
            MagicMock(),
            SkillCommandError("Registration failed"),
        ]

        # When: discover_and_register_skills() called
        discover_and_register_skills()

        # Then: continues processing despite individual failures
        assert mock_registry.discover_skills.call_count == 1
        assert mock_command_class.create_command.call_count == 2

    def test_discover_and_register_skills_handles_discovery_failure(
        self, mock_registry_class
    ):
        """Should handle complete discovery failure gracefully."""
        # Given: skill discovery fails completely
        mock_registry = mock_registry_class.return_value
        mock_registry.discover_skills.side_effect = Exception("Discovery failed")

        # When: discover_and_register_skills() called
        # Then: should not crash the application
        try:
            discover_and_register_skills()
        except Exception as e:
            pytest.fail(f"discover_and_register_skills should handle exceptions: {e}")


# Fixtures for mocking dependencies
@pytest.fixture
def mock_context():
    """Mock project context."""
    with patch("lily.cli.main.get_project_context") as mock:
        mock.return_value = ProjectContext(
            project_root=Path.cwd(),  # Use current directory which exists
            persona="default",
        )
        yield mock


@pytest.fixture
def mock_command_class():
    """Mock DynamicSkillCommand class."""
    with patch("lily.cli.main.DynamicSkillCommand") as mock:
        yield mock


@pytest.fixture
def mock_registry_class():
    """Mock SkillRegistry class."""
    with patch("lily.cli.main.SkillRegistry") as mock:
        yield mock
