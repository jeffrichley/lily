"""Unit tests for session model configuration validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from lily.session.models import ModelConfig


@pytest.mark.unit
def test_conversation_limits_allow_disabled_zero_values() -> None:
    """Disabled limits should allow zero-valued fields."""
    # Arrange - payload with disabled limits and zero values
    # Act - validate
    config = ModelConfig.model_validate(
        {
            "model_name": "stub",
            "conversation_limits": {
                "tool_loop": {"enabled": False, "max_rounds": 0},
                "timeout": {"enabled": False, "timeout_ms": 0},
                "retries": {"enabled": False, "max_retries": -1},
            },
        }
    )

    # Assert - disabled and zero values accepted
    assert config.conversation_limits.tool_loop.enabled is False
    assert config.conversation_limits.tool_loop.max_rounds == 0
    assert config.conversation_limits.timeout.enabled is False
    assert config.conversation_limits.timeout.timeout_ms == 0
    assert config.conversation_limits.retries.enabled is False
    assert config.conversation_limits.retries.max_retries == -1


@pytest.mark.unit
def test_conversation_limits_reject_invalid_enabled_tool_loop() -> None:
    """Enabled tool-loop limit requires at least one round."""
    # Arrange - payload with enabled tool_loop and max_rounds 0
    # Act - validate
    try:
        ModelConfig.model_validate(
            {
                "model_name": "stub",
                "conversation_limits": {
                    "tool_loop": {"enabled": True, "max_rounds": 0}
                },
            }
        )
    except ValidationError as exc:
        # Assert - max_rounds validation message
        assert "max_rounds must be >= 1" in str(exc)
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("Expected ValidationError")


@pytest.mark.unit
def test_conversation_limits_reject_invalid_enabled_timeout() -> None:
    """Enabled timeout limit requires a positive timeout value."""
    # Arrange - payload with enabled timeout and timeout_ms 0
    # Act - validate
    try:
        ModelConfig.model_validate(
            {
                "model_name": "stub",
                "conversation_limits": {"timeout": {"enabled": True, "timeout_ms": 0}},
            }
        )
    except ValidationError as exc:
        # Assert - timeout_ms validation message
        assert "timeout_ms must be >= 1" in str(exc)
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("Expected ValidationError")


@pytest.mark.unit
def test_conversation_limits_reject_invalid_enabled_retries() -> None:
    """Enabled retries require non-negative retry count."""
    # Arrange - payload with enabled retries and max_retries -1
    # Act - validate
    try:
        ModelConfig.model_validate(
            {
                "model_name": "stub",
                "conversation_limits": {
                    "retries": {"enabled": True, "max_retries": -1}
                },
            }
        )
    except ValidationError as exc:
        # Assert - max_retries validation message
        assert "max_retries must be >= 0" in str(exc)
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("Expected ValidationError")


@pytest.mark.unit
def test_conversation_limits_accept_valid_enabled_values() -> None:
    """Enabled limits should accept valid positive/non-negative values."""
    # Arrange - payload with enabled limits and valid values
    # Act - validate
    config = ModelConfig.model_validate(
        {
            "model_name": "stub",
            "conversation_limits": {
                "tool_loop": {"enabled": True, "max_rounds": 5},
                "timeout": {"enabled": True, "timeout_ms": 20_000},
                "retries": {"enabled": True, "max_retries": 2},
            },
        }
    )

    # Assert - all enabled and values preserved
    assert config.conversation_limits.tool_loop.enabled is True
    assert config.conversation_limits.tool_loop.max_rounds == 5
    assert config.conversation_limits.timeout.enabled is True
    assert config.conversation_limits.timeout.timeout_ms == 20_000
    assert config.conversation_limits.retries.enabled is True
    assert config.conversation_limits.retries.max_retries == 2
