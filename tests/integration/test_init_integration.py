"""Integration tests for the init command."""

import json
import tempfile
from pathlib import Path

import pytest

from lily.core.application.commands.init import InitCommand
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


def test_init_creates_all_required_artifacts(init_command, temp_dir):
    """Test that init creates all required artifacts (SC-002).

    Expected artifacts:
    - 6 user-facing markdown files (VISION, GOALS, NON_GOALS, CONSTRAINTS, ASSUMPTIONS, OPEN_QUESTIONS)
    - 1 docs README.md
    - 5 system files (state.json, config.json, index.json, log.md, log.jsonl)
    - 2 .gitkeep files (.lily/runs/.gitkeep, .lily/tasks/.gitkeep)
    Total: 14 artifacts
    """
    project_name = "testproject"
    result = init_command.execute(project_name, temp_dir)

    assert result.success, f"Init failed: {result.message}"

    # User-facing markdown files (6)
    user_facing_files = [
        ".lily/docs/VISION.md",
        ".lily/docs/GOALS.md",
        ".lily/docs/NON_GOALS.md",
        ".lily/docs/CONSTRAINTS.md",
        ".lily/docs/ASSUMPTIONS.md",
        ".lily/docs/OPEN_QUESTIONS.md",
    ]

    # Docs README
    docs_readme = ".lily/docs/README.md"

    # System files (5)
    system_files = [
        ".lily/state.json",
        ".lily/config.json",
        ".lily/index.json",
        ".lily/log.md",
        ".lily/log.jsonl",
    ]

    # .gitkeep files (2)
    gitkeep_files = [
        ".lily/runs/.gitkeep",
        ".lily/tasks/.gitkeep",
    ]

    all_expected_files = (
        user_facing_files + [docs_readme] + system_files + gitkeep_files
    )

    # Verify all files exist
    for file_path in all_expected_files:
        full_path = temp_dir / file_path
        assert full_path.exists(), f"Expected file {file_path} does not exist"

    # Verify count matches SC-002 requirement
    assert len(all_expected_files) == 14, (
        f"Expected 14 artifacts, found {len(all_expected_files)}"
    )

    # Verify files_created includes all files
    assert len(result.files_created) == 14, (
        f"Expected 14 created files, found {len(result.files_created)}"
    )


def test_init_is_idempotent(init_command, temp_dir):
    """Test that running init multiple times produces consistent results."""
    project_name = "testproject"

    # First run
    result1 = init_command.execute(project_name, temp_dir)
    assert result1.success
    first_run_files = set(result1.files_created)

    # Second run
    result2 = init_command.execute(project_name, temp_dir)
    assert result2.success
    second_run_created = set(result2.files_created)
    second_run_skipped = set(result2.files_skipped)

    # Second run should skip all files from first run
    # Note: log files are always appended to, so they may appear in created on subsequent runs
    # But the actual content files should be skipped
    non_log_files_created = {
        f for f in second_run_created if not f.endswith(("log.jsonl", "log.md"))
    }
    assert len(non_log_files_created) == 0, (
        f"Second run should not create any new files (except logs), but created: {non_log_files_created}"
    )
    # Log files are special - they're always appended to, so they may be in created or skipped
    # The important thing is that all other files are skipped
    non_log_files_from_first = {
        f for f in first_run_files if not f.endswith(("log.jsonl", "log.md"))
    }
    non_log_files_skipped = {
        f for f in second_run_skipped if not f.endswith(("log.jsonl", "log.md"))
    }
    assert non_log_files_from_first == non_log_files_skipped, (
        "Second run should skip all non-log files from first run"
    )

    # Third run - should still be idempotent
    result3 = init_command.execute(project_name, temp_dir)
    assert result3.success
    assert len(result3.files_created) == 0, "Third run should not create any new files"


def test_init_repairs_corrupted_state_json(init_command, temp_dir):
    """Test that init repairs corrupted state.json."""
    project_name = "testproject"

    # Create corrupted state.json
    lily_dir = temp_dir / ".lily"
    lily_dir.mkdir(parents=True, exist_ok=True)
    state_path = lily_dir / "state.json"
    state_path.write_text("{ invalid json }")

    # Run init
    result = init_command.execute(project_name, temp_dir)
    assert result.success

    # Verify state.json was repaired - check message or verify it's valid
    # The repair is logged, so we verify the file is now valid JSON
    state_data = json.loads(state_path.read_text())
    assert "project_name" in state_data
    assert state_data["project_name"] == project_name
    assert "phase" in state_data

    # Check log for repair entry
    log_jsonl_path = temp_dir / ".lily" / "log.jsonl"
    if log_jsonl_path.exists():
        with log_jsonl_path.open() as f:
            log_entries = [json.loads(line) for line in f if line.strip()]
        repair_entries = [e for e in log_entries if e.get("action") == "repaired"]
        assert len(repair_entries) > 0, "Should have repair log entry"


def test_log_synchronization(init_command, temp_dir):
    """Test that log.md and log.jsonl contain identical information."""
    project_name = "testproject"
    result = init_command.execute(project_name, temp_dir)
    assert result.success

    log_jsonl_path = temp_dir / ".lily" / "log.jsonl"
    log_md_path = temp_dir / ".lily" / "log.md"

    # Read JSONL entries
    jsonl_entries = []
    with log_jsonl_path.open() as f:
        for line in f:
            if line.strip():
                jsonl_entries.append(json.loads(line))

    # Read markdown log
    md_content = log_md_path.read_text()

    # Verify we have entries
    assert len(jsonl_entries) > 0, "Should have at least one log entry"

    # Verify each JSONL entry has corresponding markdown content
    for entry in jsonl_entries:
        # Check that command name appears in markdown
        assert entry["command"] in md_content, (
            f"Command {entry['command']} not found in markdown log"
        )
        # Check that action appears in markdown
        assert entry["action"] in md_content, (
            f"Action {entry['action']} not found in markdown log"
        )
        # Check that files appear in markdown
        for file_path in entry.get("files", []):
            assert file_path in md_content, (
                f"File {file_path} not found in markdown log"
            )


def test_init_performance(init_command, temp_dir):
    """Test that init completes in under 5 seconds (SC-001)."""
    import time

    project_name = "testproject"
    start_time = time.time()
    result = init_command.execute(project_name, temp_dir)
    elapsed_time = time.time() - start_time

    assert result.success
    assert elapsed_time < 5.0, (
        f"Init took {elapsed_time:.2f} seconds, expected < 5 seconds"
    )


def test_deterministic_file_creation(init_command, temp_dir):
    """Test that file creation is deterministic (no random values)."""
    project_name = "testproject"
    result1 = init_command.execute(project_name, temp_dir)
    assert result1.success

    # Get hash of created files
    storage = Storage()
    file_hashes = {}
    for file_path in result1.files_created:
        full_path = temp_dir / file_path
        if full_path.exists() and full_path.is_file():
            file_hashes[file_path] = storage.calculate_hash(full_path)

    # Clean up and run again
    import shutil

    shutil.rmtree(temp_dir / ".lily", ignore_errors=True)

    result2 = init_command.execute(project_name, temp_dir)
    assert result2.success

    # Verify hashes match (deterministic)
    # Note: Files with timestamps (state.json, config.json, index.json, log files)
    # will have different hashes due to timestamps, so exclude them from deterministic check
    timestamp_based_files = {
        ".lily/state.json",
        ".lily/config.json",
        ".lily/index.json",
        ".lily/log.jsonl",
        ".lily/log.md",
    }

    for file_path, expected_hash in file_hashes.items():
        # Skip timestamp-based files for deterministic check
        if file_path in timestamp_based_files:
            continue

        full_path = temp_dir / file_path
        if full_path.exists() and full_path.is_file():
            actual_hash = storage.calculate_hash(full_path)
            assert actual_hash == expected_hash, (
                f"File {file_path} hash mismatch - not deterministic"
            )
