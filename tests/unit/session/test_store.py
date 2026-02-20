"""Unit tests for session persistence store."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lily.session.models import ModelConfig, Session
from lily.session.store import (
    SESSION_SCHEMA_VERSION,
    SessionSchemaVersionError,
    load_session,
    recover_corrupt_session,
    save_session,
)
from lily.skills.types import SkillSnapshot


def _session() -> Session:
    """Create minimal session fixture for store tests."""
    return Session(
        session_id="session-store-test",
        active_agent="default",
        skill_snapshot=SkillSnapshot(version="v-store", skills=()),
        model_config=ModelConfig(model_name="stub-model"),
    )


@pytest.mark.unit
def test_save_and_load_roundtrip(tmp_path: Path) -> None:
    """Store should roundtrip persisted session payload."""
    # Arrange - path and minimal session
    path = tmp_path / "session.json"
    source = _session()

    # Act - save then load
    save_session(source, path)
    loaded = load_session(path)

    # Assert - loaded matches source and file has schema version
    assert loaded.session_id == source.session_id
    assert loaded.model_settings.model_name == "stub-model"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == SESSION_SCHEMA_VERSION


@pytest.mark.unit
def test_load_unsupported_schema_version_raises(tmp_path: Path) -> None:
    """Unsupported schema should raise explicit version error."""
    # Arrange - file with unsupported schema_version
    path = tmp_path / "session.json"
    path.write_text(
        json.dumps({"schema_version": 999, "session": {}}),
        encoding="utf-8",
    )

    # Act - load session (expect exception)
    try:
        load_session(path)
    except SessionSchemaVersionError as exc:
        # Assert - message mentions unsupported version
        assert "Unsupported session schema version" in str(exc)
    else:  # pragma: no cover - safety assertion
        raise AssertionError("Expected SessionSchemaVersionError")


@pytest.mark.unit
def test_recover_corrupt_session_moves_file_aside(tmp_path: Path) -> None:
    """Recovery should move invalid session to .corrupt backup path."""
    # Arrange - corrupt session file
    path = tmp_path / "session.json"
    path.write_text("{bad json", encoding="utf-8")

    # Act - recover corrupt session
    backup = recover_corrupt_session(path)

    # Assert - backup path returned, original removed
    assert backup is not None
    assert backup.name.startswith("session.json.corrupt-")
    assert not path.exists()
    assert backup.exists()
