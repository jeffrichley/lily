"""Unit tests for skill telemetry schema, serialization, and redaction."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lily.runtime.skill_discovery import SkillDiscoveryEvent
from lily.runtime.skill_events import (
    SKILL_EVENT_SCHEMA_VERSION,
    SkillCatalogInjectedPayload,
    SkillDiscoveredPayload,
    SkillExecutedPayload,
    SkillFailedPayload,
    SkillLoadedPayload,
    SkillSelectedPayload,
    emit_skill_catalog_injected,
    emit_skill_discovery_events,
    emit_skill_event,
    emit_skill_executed,
    emit_skill_failed,
    emit_skill_loaded,
    emit_skill_selected,
    sanitize_telemetry_detail,
)


@pytest.mark.unit
def test_schema_version_constant_is_semver_like_string() -> None:
    """Schema version string stays compatible with downstream sinks."""
    # Arrange - no setup required beyond module import
    # Act - read the constant
    ver = SKILL_EVENT_SCHEMA_VERSION
    # Assert - non-empty digit-led string
    assert isinstance(ver, str)
    assert ver
    assert ver[0].isdigit()


@pytest.mark.unit
def test_sanitize_telemetry_detail_truncates_long_strings() -> None:
    """Long free-form text is truncated to avoid log blowups."""
    # Arrange - a string longer than the max length
    long_text = "x" * 600
    # Act - sanitize with a short max length
    out = sanitize_telemetry_detail(long_text, max_len=100)
    # Assert - bounded length and ellipsis suffix
    assert out is not None
    assert len(out) <= 102
    assert out.endswith("…")


@pytest.mark.unit
def test_sanitize_telemetry_detail_none_and_empty() -> None:
    """None maps to None; empty becomes a placeholder."""
    # Arrange - None and whitespace-only strings
    # Act - sanitize None and blank input
    none_out = sanitize_telemetry_detail(None)
    empty_out = sanitize_telemetry_detail("   ")
    # Assert - None stays None; blank becomes placeholder
    assert none_out is None
    assert empty_out == "[empty]"


@pytest.mark.unit
def test_emit_skill_event_json_roundtrip(caplog: pytest.LogCaptureFixture) -> None:
    """Emitted log line is single JSON object with schema and payload."""
    # Arrange - enable telemetry logger capture
    caplog.set_level("INFO", logger="lily.skill.telemetry")
    # Act - emit one failure-shaped event
    emit_skill_event(
        "skill_failed",
        SkillFailedPayload(
            phase="retrieval",
            error_kind="not_found",
            detail="missing",
        ),
    )
    # Assert - JSON envelope fields
    assert caplog.records
    raw = caplog.records[-1].getMessage()
    data = json.loads(raw)
    assert data["schema_version"] == SKILL_EVENT_SCHEMA_VERSION
    assert data["event"] == "skill_failed"
    assert data["payload"]["error_kind"] == "not_found"
    assert data["payload"]["phase"] == "retrieval"


@pytest.mark.unit
def test_payload_models_dump_json_safe() -> None:
    """All payload types produce JSON-serializable dicts."""
    # Arrange - one instance of each payload model
    models = [
        SkillDiscoveredPayload(
            discovery_kind="discovered",
            canonical_key="a-b",
            scope="repository",
            path="/tmp/x/SKILL.md",
        ),
        SkillSelectedPayload(requested_name="n", reference_subpath=None),
        SkillLoadedPayload(
            canonical_key="a-b",
            load_kind="skill_md",
            relative_path="SKILL.md",
            content_length=10,
        ),
        SkillExecutedPayload(
            requested_name="n",
            canonical_key="a-b",
            reference_subpath=None,
            result_length=10,
        ),
        SkillFailedPayload(phase="load", error_kind="x", detail="y"),
        SkillCatalogInjectedPayload(skills_count=2, catalog_char_count=100),
    ]
    # Act - dump each model to JSON-compatible dict and serialize
    for model in models:
        dumped = model.model_dump(mode="json")
        serialized = json.dumps(dumped)
        # Assert - round-trip string is non-empty JSON
        assert serialized


@pytest.mark.unit
def test_emit_skill_discovery_events_only_paths_and_sanitized_detail(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Discovery telemetry carries paths and bounded detail, not SKILL.md bodies."""
    # Arrange - capture logs and one skipped_invalid discovery event
    caplog.set_level("INFO", logger="lily.skill.telemetry")
    ev = SkillDiscoveryEvent(
        kind="skipped_invalid",
        canonical_key="",
        scope="repository",
        path=Path("/tmp/pkg/SKILL.md"),
        detail="validation failed: name is required",
    )
    # Act - emit telemetry for the discovery event
    emit_skill_discovery_events((ev,))
    # Assert - envelope shape; no YAML frontmatter markers in payload
    assert caplog.records
    data = json.loads(caplog.records[-1].getMessage())
    assert data["event"] == "skill_discovered"
    assert "validation failed" in (data["payload"]["detail"] or "")
    payload_str = json.dumps(data["payload"])
    assert "---" not in payload_str


@pytest.mark.unit
def test_helper_emitters_include_schema_version(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Convenience emitters delegate to the same envelope shape."""
    # Arrange - capture telemetry logger
    caplog.set_level("INFO", logger="lily.skill.telemetry")
    # Act - emit one of each helper path
    emit_skill_selected(requested_name="s", reference_subpath=None)
    emit_skill_loaded(
        canonical_key="k",
        load_kind="skill_md",
        relative_path="SKILL.md",
        content_length=3,
    )
    emit_skill_executed(
        requested_name="s",
        canonical_key="k",
        reference_subpath=None,
        result_length=3,
    )
    emit_skill_failed(phase="retrieval", error_kind="denied", detail="blocked")
    emit_skill_catalog_injected(skills_count=1, catalog_char_count=50)
    # Assert - every record is JSON with schema_version
    for rec in caplog.records:
        data = json.loads(rec.getMessage())
        assert data["schema_version"] == SKILL_EVENT_SCHEMA_VERSION
        assert "event" in data
        assert "payload" in data
