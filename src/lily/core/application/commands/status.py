"""Status command implementation for displaying project state and artifacts."""

import json
from pathlib import Path
from typing import List

from lily.core.application.commands.base import (
    Command,
    CommandResult,
    CommandResultImpl,
)
from lily.core.infrastructure.models.index import (
    ArtifactModel,
    ArtifactType,
    IndexModel,
)
from lily.core.infrastructure.models.state import StateModel
from lily.core.infrastructure.storage import Storage


class StatusCommand(Command):
    """Command to display project status and artifact information."""

    def __init__(self, storage: Storage):
        """Initialize StatusCommand with dependencies.

        Args:
            storage: Storage instance for file operations
        """
        self.storage = storage

    def validate(self, root_path: Path) -> bool:
        """Validate prerequisites before execution.

        Args:
            root_path: Root path of the project

        Returns:
            True if validation passes

        Raises:
            ValueError: If validation fails with specific error details
        """
        lily_dir = root_path / ".lily"
        state_path = lily_dir / "state.json"

        # Check if .lily/state.json exists (validates we're in a Lily project)
        if not self.storage.file_exists(state_path):
            raise ValueError(
                "Not a Lily project. Run 'lily init' first to initialize a project."
            )

        # Check if index.json exists (optional, but should exist after init)
        index_path = lily_dir / "index.json"
        if not self.storage.file_exists(index_path):
            # This is okay - index might be empty or missing, we'll handle it in execute
            pass

        return True

    def execute(self, root_path: Path) -> CommandResult:
        """Execute status command to display project state and artifacts.

        Args:
            root_path: Root path of the project

        Returns:
            CommandResult with success status and formatted status message
        """
        lily_dir = root_path / ".lily"
        state_path = lily_dir / "state.json"
        index_path = lily_dir / "index.json"

        # Read and validate state.json
        try:
            state_data = self.storage.read_json(state_path)
            state = StateModel(**state_data)
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            error_message = (
                "Error: Corrupted state file. Run 'lily init' to repair.\n\n"
                f"Details: {str(e)}"
            )
            return CommandResultImpl(
                success=False,
                message=error_message,
                files_created=[],
                files_skipped=[],
            )

        # Read and validate index.json (optional - may not exist or be empty)
        artifacts: List[ArtifactModel] = []
        try:
            if self.storage.file_exists(index_path):
                index_data = self.storage.read_json(index_path)
                if isinstance(index_data, list) and len(index_data) > 0:
                    index = IndexModel(
                        root=[ArtifactModel(**item) for item in index_data]
                    )
                    artifacts = list(index)
        except (json.JSONDecodeError, ValueError, TypeError):
            # Index is corrupted or invalid - continue with empty artifacts list
            # This is not a fatal error, we can still show state
            pass

        # Group artifacts by type
        user_facing_artifacts = [
            artifact
            for artifact in artifacts
            if artifact.artifact_type == ArtifactType.USER_FACING
        ]
        system_artifacts = [
            artifact
            for artifact in artifacts
            if artifact.artifact_type == ArtifactType.SYSTEM
        ]

        # Sort artifacts alphabetically by file path
        user_facing_artifacts.sort(key=lambda a: a.file_path)
        system_artifacts.sort(key=lambda a: a.file_path)

        # Format timestamps for display
        created_at_str = state.created_at.strftime("%Y-%m-%d %H:%M:%S")
        last_updated_str = state.last_updated.strftime("%Y-%m-%d %H:%M:%S")

        # Build status message
        lines = []
        lines.append(f"Project: {state.project_name}")
        lines.append(f"Phase: {state.phase.value}")
        lines.append(f"Version: {state.version}")
        lines.append(f"Created: {created_at_str}")
        lines.append(f"Last Updated: {last_updated_str}")
        lines.append("")
        lines.append("Artifacts:")

        # User-facing artifacts
        lines.append(f"  User-facing: {len(user_facing_artifacts)}")
        for artifact in user_facing_artifacts:
            lines.append(f"    - {artifact.file_path}")

        # System artifacts
        lines.append(f"  System: {len(system_artifacts)}")
        for artifact in system_artifacts:
            lines.append(f"    - {artifact.file_path}")

        message = "\n".join(lines)

        return CommandResultImpl(
            success=True,
            message=message,
            files_created=[],
            files_skipped=[],
        )
