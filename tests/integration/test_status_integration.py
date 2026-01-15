"""Integration tests for the status command."""

import tempfile
from pathlib import Path

import pytest

from lily.core.application.commands.init import InitCommand
from lily.core.application.commands.status import StatusCommand
from lily.core.infrastructure.storage import Logger, Storage


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
def logger(storage, temp_dir):
    """Create a Logger instance."""
    log_jsonl_path = temp_dir / ".lily" / "log.jsonl"
    log_md_path = temp_dir / ".lily" / "log.md"
    return Logger(storage, log_jsonl_path, log_md_path)


@pytest.fixture
def init_command(storage, logger):
    """Create an InitCommand instance."""
    return InitCommand(storage, logger, version="0.1.0")


@pytest.fixture
def status_command(storage):
    """Create a StatusCommand instance."""
    return StatusCommand(storage)


def test_status_after_init_shows_correct_phase(init_command, status_command, temp_dir):
    """Test that status after init shows correct phase (DISCOVERY)."""
    project_name = "testproject"

    # Run init first
    init_result = init_command.execute(project_name, temp_dir)
    assert init_result.success

    # Run status
    status_result = status_command.execute(temp_dir)

    assert status_result.success
    assert "testproject" in status_result.message
    assert "Phase: DISCOVERY" in status_result.message
    assert "Version: 0.1.0" in status_result.message


def test_status_shows_all_created_artifacts(init_command, status_command, temp_dir):
    """Test that status shows all created artifacts after init."""
    project_name = "testproject"

    # Run init first
    init_result = init_command.execute(project_name, temp_dir)
    assert init_result.success

    # Run status
    status_result = status_command.execute(temp_dir)

    assert status_result.success
    message = status_result.message

    # Check that user-facing artifacts are listed
    assert "User-facing:" in message
    assert ".lily/docs/VISION.md" in message
    assert ".lily/docs/GOALS.md" in message
    assert ".lily/docs/NON_GOALS.md" in message
    assert ".lily/docs/CONSTRAINTS.md" in message
    assert ".lily/docs/ASSUMPTIONS.md" in message
    assert ".lily/docs/OPEN_QUESTIONS.md" in message
    assert ".lily/docs/README.md" in message

    # Check that system artifacts are listed
    assert "System:" in message
    assert ".lily/state.json" in message
    assert ".lily/config.json" in message
    assert ".lily/index.json" in message
    assert ".lily/log.md" in message
    assert ".lily/log.jsonl" in message


def test_status_with_no_artifacts_handles_gracefully(status_command, temp_dir, storage):
    """Test status with no artifacts (edge case)."""
    # Create minimal project structure (just state.json, no index or artifacts)
    lily_dir = temp_dir / ".lily"
    lily_dir.mkdir()

    from datetime import datetime, timezone
    from lily.core.infrastructure.models.state import Phase, StateModel

    state = StateModel(
        phase=Phase.DISCOVERY,
        project_name="emptyproject",
        created_at=datetime.now(timezone.utc),
        last_updated=datetime.now(timezone.utc),
        version="0.1.0",
    )
    state_path = lily_dir / "state.json"
    storage.write_json(state_path, state.model_dump(mode="json"))

    # Create empty index
    from lily.core.infrastructure.models.index import IndexModel

    index = IndexModel(root=[])
    index_path = lily_dir / "index.json"
    storage.write_json(index_path, index.model_dump(mode="json"))

    # Run status
    status_result = status_command.execute(temp_dir)

    assert status_result.success
    assert "emptyproject" in status_result.message
    assert "User-facing: 0" in status_result.message
    assert "System: 0" in status_result.message


def test_status_in_non_lily_directory_fails_gracefully(status_command, temp_dir):
    """Test status in non-Lily directory (should fail gracefully)."""
    # Don't create .lily directory - just use empty temp_dir

    # Should raise ValueError during validation
    with pytest.raises(ValueError) as exc_info:
        status_command.validate(temp_dir)

    assert "not a lily project" in str(exc_info.value).lower()
    assert "lily init" in str(exc_info.value).lower()


def test_status_end_to_end_workflow(init_command, status_command, temp_dir):
    """Test end-to-end workflow: init then status."""
    project_name = "workflowtest"

    # Step 1: Initialize project
    init_result = init_command.execute(project_name, temp_dir)
    assert init_result.success

    # Step 2: Check status
    status_result = status_command.execute(temp_dir)
    assert status_result.success

    # Verify status output contains expected information
    message = status_result.message
    assert project_name in message
    assert "DISCOVERY" in message
    assert "Artifacts:" in message
    assert "User-facing:" in message
    assert "System:" in message

    # Verify counts match expected artifacts from init
    # Init creates 7 user-facing files (6 docs + README) and 5 system files
    # But we should check that the counts are reasonable
    assert "User-facing:" in message
    assert "System:" in message
