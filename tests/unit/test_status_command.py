"""Unit tests for the status command."""

import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from lily.core.application.commands.status import StatusCommand
from lily.core.infrastructure.models.index import (
    ArtifactModel,
    ArtifactType,
    IndexModel,
)
from lily.core.infrastructure.models.state import Phase, StateModel
from lily.core.infrastructure.storage import Storage


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def storage():
    """Create a Storage instance."""
    return Storage()


@pytest.fixture
def status_command(storage):
    """Create a StatusCommand instance."""
    return StatusCommand(storage)


@pytest.fixture
def lily_project(temp_dir, storage):
    """Create a minimal Lily project structure for testing."""
    lily_dir = temp_dir / ".lily"
    lily_dir.mkdir()

    # Create state.json
    state = StateModel(
        phase=Phase.DISCOVERY,
        project_name="testproject",
        created_at=datetime.now(timezone.utc),
        last_updated=datetime.now(timezone.utc),
        version="0.1.0",
    )
    state_path = lily_dir / "state.json"
    storage.write_json(state_path, state.model_dump(mode="json"))

    # Create empty index.json
    index = IndexModel(root=[])
    index_path = lily_dir / "index.json"
    storage.write_json(index_path, index.model_dump(mode="json"))

    return temp_dir


def test_validate_success_when_state_exists(status_command, lily_project):
    """Test that validate succeeds when .lily/state.json exists."""
    result = status_command.validate(lily_project)
    assert result is True


def test_validate_fails_when_not_lily_project(status_command, temp_dir):
    """Test that validate raises ValueError when not a Lily project."""
    with pytest.raises(ValueError) as exc_info:
        status_command.validate(temp_dir)
    assert "not a lily project" in str(exc_info.value).lower()
    assert "lily init" in str(exc_info.value).lower()


def test_validate_handles_missing_index_gracefully(status_command, temp_dir, storage):
    """Test that validate handles missing index.json gracefully."""
    lily_dir = temp_dir / ".lily"
    lily_dir.mkdir()

    # Create only state.json, no index.json
    state = StateModel(
        phase=Phase.DISCOVERY,
        project_name="testproject",
        created_at=datetime.now(timezone.utc),
        last_updated=datetime.now(timezone.utc),
        version="0.1.0",
    )
    state_path = lily_dir / "state.json"
    storage.write_json(state_path, state.model_dump(mode="json"))

    # Should not raise an error
    result = status_command.validate(temp_dir)
    assert result is True


def test_execute_successfully_reads_state_and_artifacts(
    status_command, lily_project, storage
):
    """Test that execute successfully reads and formats state and artifacts."""
    # Add some artifacts to the index
    lily_dir = lily_project / ".lily"
    index_path = lily_dir / "index.json"

    artifacts = [
        ArtifactModel(
            file_path=".lily/docs/VISION.md",
            artifact_type=ArtifactType.USER_FACING,
            last_modified=datetime.now(timezone.utc),
            hash="a" * 64,
        ),
        ArtifactModel(
            file_path=".lily/state.json",
            artifact_type=ArtifactType.SYSTEM,
            last_modified=datetime.now(timezone.utc),
            hash="b" * 64,
        ),
    ]
    index = IndexModel(root=artifacts)
    storage.write_json(index_path, index.model_dump(mode="json"))

    result = status_command.execute(lily_project)

    assert result.success is True
    assert "testproject" in result.message
    assert "DISCOVERY" in result.message
    assert "User-facing: 1" in result.message
    assert "System: 1" in result.message
    assert ".lily/docs/VISION.md" in result.message
    assert ".lily/state.json" in result.message


def test_execute_groups_artifacts_correctly(status_command, lily_project, storage):
    """Test that execute groups artifacts correctly by type."""
    lily_dir = lily_project / ".lily"
    index_path = lily_dir / "index.json"

    artifacts = [
        ArtifactModel(
            file_path=".lily/docs/VISION.md",
            artifact_type=ArtifactType.USER_FACING,
            last_modified=datetime.now(timezone.utc),
            hash="a" * 64,
        ),
        ArtifactModel(
            file_path=".lily/docs/GOALS.md",
            artifact_type=ArtifactType.USER_FACING,
            last_modified=datetime.now(timezone.utc),
            hash="b" * 64,
        ),
        ArtifactModel(
            file_path=".lily/state.json",
            artifact_type=ArtifactType.SYSTEM,
            last_modified=datetime.now(timezone.utc),
            hash="c" * 64,
        ),
        ArtifactModel(
            file_path=".lily/config.json",
            artifact_type=ArtifactType.SYSTEM,
            last_modified=datetime.now(timezone.utc),
            hash="d" * 64,
        ),
    ]
    index = IndexModel(root=artifacts)
    storage.write_json(index_path, index.model_dump(mode="json"))

    result = status_command.execute(lily_project)

    assert result.success is True
    assert "User-facing: 2" in result.message
    assert "System: 2" in result.message

    # Check that artifacts are sorted alphabetically
    message_lines = result.message.split("\n")
    user_facing_section = False
    system_section = False
    user_facing_paths = []
    system_paths = []

    for line in message_lines:
        if "User-facing:" in line:
            user_facing_section = True
            system_section = False
        elif "System:" in line:
            system_section = True
            user_facing_section = False
        elif user_facing_section and line.strip().startswith("-"):
            user_facing_paths.append(line.strip())
        elif system_section and line.strip().startswith("-"):
            system_paths.append(line.strip())

    assert len(user_facing_paths) == 2
    assert len(system_paths) == 2
    # Check alphabetical order
    assert user_facing_paths[0] < user_facing_paths[1]
    assert system_paths[0] < system_paths[1]


def test_execute_handles_empty_index_gracefully(status_command, lily_project):
    """Test that execute handles empty index gracefully."""
    result = status_command.execute(lily_project)

    assert result.success is True
    assert "User-facing: 0" in result.message
    assert "System: 0" in result.message
    assert "testproject" in result.message
    assert "DISCOVERY" in result.message


def test_execute_handles_corrupted_state_json(status_command, temp_dir, storage):
    """Test that execute handles corrupted state.json with clear error."""
    lily_dir = temp_dir / ".lily"
    lily_dir.mkdir()

    # Create corrupted state.json
    state_path = lily_dir / "state.json"
    state_path.write_text("invalid json content {")

    result = status_command.execute(temp_dir)

    assert result.success is False
    assert "corrupted state file" in result.message.lower()
    assert "lily init" in result.message.lower()


def test_execute_handles_corrupted_index_json_gracefully(
    status_command, lily_project, storage
):
    """Test that execute handles corrupted index.json gracefully."""
    lily_dir = lily_project / ".lily"
    index_path = lily_dir / "index.json"

    # Corrupt the index.json
    index_path.write_text("invalid json content {")

    # Should still succeed, just with empty artifacts
    result = status_command.execute(lily_project)

    assert result.success is True
    assert "User-facing: 0" in result.message
    assert "System: 0" in result.message
    assert "testproject" in result.message


def test_execute_formats_output_correctly(status_command, lily_project, storage):
    """Test that execute formats output correctly with all expected sections."""
    result = status_command.execute(lily_project)

    assert result.success is True
    message = result.message

    # Check all required sections are present
    assert "Project:" in message
    assert "Phase:" in message
    assert "Version:" in message
    assert "Created:" in message
    assert "Last Updated:" in message
    assert "Artifacts:" in message
    assert "User-facing:" in message
    assert "System:" in message

    # Check that project name and phase are in the output
    assert "testproject" in message
    assert "DISCOVERY" in message
    assert "0.1.0" in message
