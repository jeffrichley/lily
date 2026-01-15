"""Init command implementation for initializing a new Lily project."""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from lily.core.application.commands.base import (
    Command,
    CommandResult,
    CommandResultImpl,
)
from lily.core.infrastructure.models.config import ConfigModel
from lily.core.infrastructure.models.index import (
    ArtifactModel,
    ArtifactType,
    IndexModel,
)
from lily.core.infrastructure.models.state import Phase, StateModel
from lily.core.infrastructure.storage import Logger, Storage


class InitCommand(Command):
    """Command to initialize a new Lily project."""

    def __init__(self, storage: Storage, logger: Logger, version: str = "0.1.0"):
        """Initialize InitCommand with dependencies.

        Args:
            storage: Storage instance for file operations
            logger: Logger instance for dual-format logging
            version: Lily version string (default: "0.1.0")
        """
        self.storage = storage
        self.logger = logger
        self.version = version

    def validate(self, project_name: str, root_path: Path) -> bool:
        """Validate prerequisites before execution.

        Args:
            project_name: Name of the project
            root_path: Root path where project will be initialized

        Returns:
            True if validation passes

        Raises:
            ValueError: If validation fails with specific error details
        """
        # Validate project name
        if not project_name or not project_name.strip():
            raise ValueError("Project name cannot be empty")

        # Validate project name for filesystem compatibility
        # Disallow characters that are problematic in file paths
        invalid_chars = r'[<>:"/\\|?*\x00-\x1f]'
        if re.search(invalid_chars, project_name):
            raise ValueError(
                "Project name contains invalid characters. "
                'Project name cannot contain: < > : " / \\ | ? * or control characters'
            )

        # Check write permissions
        if not self.storage.check_permissions(root_path):
            raise ValueError(
                f"Cannot write to directory: {root_path}. "
                f"Please check write permissions."
            )

        # Check for corrupted state.json if it exists
        lily_dir = root_path / ".lily"
        state_path = lily_dir / "state.json"
        if self.storage.file_exists(state_path):
            try:
                state_data = self.storage.read_json(state_path)
                # Validate using StateModel
                StateModel(**state_data)
            except (json.JSONDecodeError, ValueError, TypeError):
                # State.json is corrupted - this is okay, we'll repair it
                # Don't raise error, just note it for repair
                pass

        return True

    def execute(self, project_name: str, root_path: Path) -> CommandResult:
        """Execute init command to initialize a new Lily project.

        Args:
            project_name: Name of the project
            root_path: Root path where project will be initialized

        Returns:
            CommandResult with success status and list of created files
        """
        files_created: List[str] = []
        files_skipped: List[str] = []
        files_repaired: List[str] = []
        failed_paths: List[str] = []

        # Validate prerequisites
        try:
            self.validate(project_name, root_path)
        except ValueError as e:
            # Validation failed - return error result
            error_message = f"✗ Failed to initialize project: {e}"
            self.logger.log_init(
                action="failed",
                files=[],
                metadata={
                    "project_name": project_name,
                    "error_type": "validation_error",
                    "error_message": str(e),
                },
            )
            return CommandResultImpl(
                success=False,
                message=error_message,
                files_created=[],
                files_skipped=[],
            )

        # Create directory structure with error handling
        lily_dir = root_path / ".lily"
        runs_dir = lily_dir / "runs"
        tasks_dir = lily_dir / "tasks"
        docs_dir = lily_dir / "docs"

        try:
            self.storage.create_directory(lily_dir)
            self.storage.create_directory(runs_dir)
            self.storage.create_directory(tasks_dir)
            self.storage.create_directory(docs_dir)
        except (OSError, PermissionError) as e:
            failed_paths.append(str(lily_dir))
            error_message = (
                f"✗ Failed to initialize project: Permission denied\n\n"
                f"Cannot write to the following paths:\n"
                f"  {lily_dir}\n\n"
                f"Please check write permissions and try again."
            )
            self.logger.log_init(
                action="failed",
                files=failed_paths,
                metadata={
                    "project_name": project_name,
                    "error_type": "permission_denied",
                    "error_message": str(e),
                },
            )
            return CommandResultImpl(
                success=False,
                message=error_message,
                files_created=[],
                files_skipped=[],
            )

        # Create .gitkeep files with error handling
        gitkeep_runs = runs_dir / ".gitkeep"
        gitkeep_tasks = tasks_dir / ".gitkeep"

        try:
            if not self.storage.file_exists(gitkeep_runs):
                self.storage.create_file(gitkeep_runs, "")
                files_created.append(str(gitkeep_runs.relative_to(root_path)))
            else:
                files_skipped.append(str(gitkeep_runs.relative_to(root_path)))

            if not self.storage.file_exists(gitkeep_tasks):
                self.storage.create_file(gitkeep_tasks, "")
                files_created.append(str(gitkeep_tasks.relative_to(root_path)))
            else:
                files_skipped.append(str(gitkeep_tasks.relative_to(root_path)))
        except (OSError, PermissionError) as e:
            failed_paths.extend(
                [
                    str(gitkeep_runs.relative_to(root_path)),
                    str(gitkeep_tasks.relative_to(root_path)),
                ]
            )
            error_message = (
                "✗ Failed to initialize project: Permission denied\n\n"
                "Cannot write to the following paths:\n"
            )
            for path in failed_paths:
                error_message += f"  {path}\n"
            error_message += "\nPlease check write permissions and try again."
            self.logger.log_init(
                action="failed",
                files=failed_paths,
                metadata={
                    "project_name": project_name,
                    "error_type": "permission_denied",
                    "error_message": str(e),
                },
            )
            return CommandResultImpl(
                success=False,
                message=error_message,
                files_created=files_created,
                files_skipped=[],
            )

        # Create system artifacts
        now = datetime.now(timezone.utc)

        # state.json - with corruption detection and repair
        state_path = lily_dir / "state.json"
        state_corrupted = False
        try:
            if not self.storage.file_exists(state_path):
                state = StateModel(
                    phase=Phase.DISCOVERY,
                    project_name=project_name,
                    created_at=now,
                    last_updated=now,
                    version=self.version,
                )
                self.storage.write_json(state_path, state.model_dump(mode="json"))
                files_created.append(str(state_path.relative_to(root_path)))
            else:
                # Check if state.json is corrupted
                try:
                    state_data = self.storage.read_json(state_path)
                    state = StateModel(**state_data)
                    files_skipped.append(str(state_path.relative_to(root_path)))
                except (json.JSONDecodeError, ValueError, TypeError):
                    # State.json is corrupted - repair it
                    state = StateModel(
                        phase=Phase.DISCOVERY,
                        project_name=project_name,
                        created_at=now,
                        last_updated=now,
                        version=self.version,
                    )
                    self.storage.write_json(state_path, state.model_dump(mode="json"))
                    files_repaired.append(str(state_path.relative_to(root_path)))
                    state_corrupted = True
        except (OSError, PermissionError) as e:
            failed_paths.append(str(state_path.relative_to(root_path)))
            error_message = (
                "✗ Failed to initialize project: Permission denied\n\n"
                "Cannot write to the following paths:\n"
            )
            for path in failed_paths:
                error_message += f"  {path}\n"
            error_message += "\nPlease check write permissions and try again."
            self.logger.log_init(
                action="failed",
                files=failed_paths,
                metadata={
                    "project_name": project_name,
                    "error_type": "permission_denied",
                    "error_message": str(e),
                },
            )
            return CommandResultImpl(
                success=False,
                message=error_message,
                files_created=files_created,
                files_skipped=files_skipped,
            )

        # config.json - with corruption detection and repair
        config_path = lily_dir / "config.json"
        config_corrupted = False
        try:
            if not self.storage.file_exists(config_path):
                config = ConfigModel(
                    version=self.version,
                    project_name=project_name,
                    created_at=now,
                )
                self.storage.write_json(config_path, config.model_dump(mode="json"))
                files_created.append(str(config_path.relative_to(root_path)))
            else:
                # Check if config.json is corrupted
                try:
                    config_data = self.storage.read_json(config_path)
                    config = ConfigModel(**config_data)
                    files_skipped.append(str(config_path.relative_to(root_path)))
                except (json.JSONDecodeError, ValueError, TypeError):
                    # Config.json is corrupted - repair it
                    config = ConfigModel(
                        version=self.version,
                        project_name=project_name,
                        created_at=now,
                    )
                    self.storage.write_json(config_path, config.model_dump(mode="json"))
                    files_repaired.append(str(config_path.relative_to(root_path)))
                    config_corrupted = True
        except (OSError, PermissionError) as e:
            failed_paths.append(str(config_path.relative_to(root_path)))
            error_message = (
                "✗ Failed to initialize project: Permission denied\n\n"
                "Cannot write to the following paths:\n"
            )
            for path in failed_paths:
                error_message += f"  {path}\n"
            error_message += "\nPlease check write permissions and try again."
            self.logger.log_init(
                action="failed",
                files=failed_paths,
                metadata={
                    "project_name": project_name,
                    "error_type": "permission_denied",
                    "error_message": str(e),
                },
            )
            return CommandResultImpl(
                success=False,
                message=error_message,
                files_created=files_created,
                files_skipped=files_skipped,
            )

        # index.json - with corruption detection and repair
        index_path = lily_dir / "index.json"
        index_corrupted = False
        try:
            if not self.storage.file_exists(index_path):
                index = IndexModel(root=[])
                self.storage.write_json(index_path, index.model_dump(mode="json"))
                files_created.append(str(index_path.relative_to(root_path)))
            else:
                # Read existing index to update it
                try:
                    index_data = self.storage.read_json(index_path)
                    # Validate it's a list
                    if not isinstance(index_data, list):
                        raise ValueError("Index must be a list")
                    index = IndexModel(
                        root=[ArtifactModel(**item) for item in index_data]
                    )
                    files_skipped.append(str(index_path.relative_to(root_path)))
                except (json.JSONDecodeError, ValueError, TypeError):
                    # Index.json is corrupted - repair it
                    index = IndexModel(root=[])
                    self.storage.write_json(index_path, index.model_dump(mode="json"))
                    files_repaired.append(str(index_path.relative_to(root_path)))
                    index_corrupted = True
        except (OSError, PermissionError) as e:
            failed_paths.append(str(index_path.relative_to(root_path)))
            error_message = (
                "✗ Failed to initialize project: Permission denied\n\n"
                "Cannot write to the following paths:\n"
            )
            for path in failed_paths:
                error_message += f"  {path}\n"
            error_message += "\nPlease check write permissions and try again."
            self.logger.log_init(
                action="failed",
                files=failed_paths,
                metadata={
                    "project_name": project_name,
                    "error_type": "permission_denied",
                    "error_message": str(e),
                },
            )
            return CommandResultImpl(
                success=False,
                message=error_message,
                files_created=files_created,
                files_skipped=files_skipped,
            )

        # Create user-facing markdown files from templates
        template_mappings = [
            ("VISION.md", ".lily/docs/VISION.md"),
            ("GOALS.md", ".lily/docs/GOALS.md"),
            ("NON_GOALS.md", ".lily/docs/NON_GOALS.md"),
            ("CONSTRAINTS.md", ".lily/docs/CONSTRAINTS.md"),
            ("ASSUMPTIONS.md", ".lily/docs/ASSUMPTIONS.md"),
            ("OPEN_QUESTIONS.md", ".lily/docs/OPEN_QUESTIONS.md"),
            ("README.md", ".lily/docs/README.md"),
        ]

        for template_name, file_path in template_mappings:
            full_path = root_path / file_path

            try:
                if not self.storage.file_exists(full_path):
                    self.storage.copy_template(template_name, full_path)
                    files_created.append(file_path)
                else:
                    files_skipped.append(file_path)
            except (OSError, PermissionError) as e:
                failed_paths.append(file_path)
                error_message = (
                    "✗ Failed to initialize project: Permission denied\n\n"
                    "Cannot write to the following paths:\n"
                )
                for path in failed_paths:
                    error_message += f"  {path}\n"
                error_message += "\nPlease check write permissions and try again."
                self.logger.log_init(
                    action="failed",
                    files=failed_paths,
                    metadata={
                        "project_name": project_name,
                        "error_type": "permission_denied",
                        "error_message": str(e),
                    },
                )
                return CommandResultImpl(
                    success=False,
                    message=error_message,
                    files_created=files_created,
                    files_skipped=files_skipped,
                )

        # Add system artifacts to index (before logging, so logs aren't in index yet)
        system_artifacts = [
            (state_path, ArtifactType.SYSTEM),
            (config_path, ArtifactType.SYSTEM),
            (index_path, ArtifactType.SYSTEM),
        ]

        # Add user-facing artifacts to index
        user_artifacts = [
            (root_path / file_path, ArtifactType.USER_FACING)
            for _, file_path in template_mappings
        ]

        # Combine all artifacts (excluding log files - they'll be added after logging)
        all_artifacts = system_artifacts + user_artifacts

        # Update index with created files
        for artifact_path, artifact_type in all_artifacts:
            if artifact_path.exists():
                # Check if already in index
                relative_path = str(artifact_path.relative_to(root_path))
                existing = next(
                    (a for a in index.root if a.file_path == relative_path),
                    None,
                )

                if existing is None:
                    hash_value = self.storage.calculate_hash(artifact_path)
                    artifact = ArtifactModel(
                        file_path=relative_path,
                        artifact_type=artifact_type,
                        last_modified=datetime.fromtimestamp(
                            artifact_path.stat().st_mtime, tz=timezone.utc
                        ),
                        hash=hash_value,
                    )
                    index.append(artifact)

        # Write updated index (before logging)
        self.storage.write_json(index_path, index.model_dump(mode="json"))

        # Write log entries (this creates log.jsonl and log.md)
        log_jsonl_path = lily_dir / "log.jsonl"
        log_md_path = lily_dir / "log.md"

        # Check if log files existed before logging (for idempotency)
        log_jsonl_existed = self.storage.file_exists(log_jsonl_path)
        log_md_existed = self.storage.file_exists(log_md_path)

        # Log created files
        if files_created:
            self.logger.log_init(
                action="created",
                files=files_created,
                metadata={"project_name": project_name, "phase": "DISCOVERY"},
            )

        # Log skipped files
        if files_skipped:
            self.logger.log_init(
                action="skipped",
                files=files_skipped,
                metadata={"project_name": project_name, "phase": "DISCOVERY"},
            )

        # Log repaired files
        if files_repaired:
            repair_metadata = {
                "project_name": project_name,
                "phase": "DISCOVERY",
                "corruption_detected": "true",
            }
            # Add specific corruption info (convert booleans to strings for metadata)
            if state_corrupted:
                repair_metadata["state_corrupted"] = "true"
            if config_corrupted:
                repair_metadata["config_corrupted"] = "true"
            if index_corrupted:
                repair_metadata["index_corrupted"] = "true"

            self.logger.log_init(
                action="repaired",
                files=files_repaired,
                metadata=repair_metadata,
            )

        # Add log files to created/skipped list and index (they're created by logger)
        log_artifacts = [
            (log_jsonl_path, ArtifactType.SYSTEM, log_jsonl_existed),
            (log_md_path, ArtifactType.SYSTEM, log_md_existed),
        ]

        for log_path, artifact_type, existed_before in log_artifacts:
            if log_path.exists():
                relative_path = str(log_path.relative_to(root_path))
                if existed_before:
                    # Log file existed before, so it should be in skipped
                    if relative_path not in files_skipped:
                        files_skipped.append(relative_path)
                else:
                    # Log file was created in this run
                    if relative_path not in files_created:
                        files_created.append(relative_path)

                # Add to index
                existing = next(
                    (a for a in index.root if a.file_path == relative_path),
                    None,
                )
                if existing is None:
                    hash_value = self.storage.calculate_hash(log_path)
                    artifact = ArtifactModel(
                        file_path=relative_path,
                        artifact_type=artifact_type,
                        last_modified=datetime.fromtimestamp(
                            log_path.stat().st_mtime, tz=timezone.utc
                        ),
                        hash=hash_value,
                    )
                    index.append(artifact)

        # Write updated index again (with log files)
        self.storage.write_json(index_path, index.model_dump(mode="json"))

        # Format success message
        if files_repaired:
            message = f"✓ Project '{project_name}' re-initialized\n\n"
        else:
            message = f"✓ Project '{project_name}' initialized successfully\n\n"

        if files_created:
            message += "Created files:\n"
            for file_path in sorted(files_created):
                message += f"  {file_path}\n"

        if files_repaired:
            message += "\nRepaired files (corrupted files recreated):\n"
            for file_path in sorted(files_repaired):
                message += f"  {file_path}\n"

        if files_skipped:
            message += "\nSkipped files (already exist):\n"
            for file_path in sorted(files_skipped):
                message += f"  {file_path}\n"

        message += "\nProject is ready for the next phase (DISCOVERY)."

        return CommandResultImpl(
            success=True,
            message=message,
            files_created=files_created,
            files_skipped=files_skipped,
        )
