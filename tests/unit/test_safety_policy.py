"""Layer 4: SafetyPolicy model."""

import pytest
from pydantic import ValidationError

from lily.kernel.policy_models import SafetyPolicy


def test_valid_config_passes() -> None:
    """SafetyPolicy accepts valid config."""
    policy = SafetyPolicy(
        allow_write_paths=["/allowed/out", "./out"],
        deny_write_paths=["/etc"],
        max_diff_size_bytes=1024,
        allowed_tools=["local_command", "custom"],
        network_access="deny",
    )
    assert policy.allow_write_paths == ["/allowed/out", "./out"]
    assert policy.deny_write_paths == ["/etc"]
    assert policy.max_diff_size_bytes == 1024
    assert policy.allowed_tools == ["local_command", "custom"]
    assert policy.network_access == "deny"


def test_invalid_network_access_fails() -> None:
    """Invalid network_access raises ValidationError."""
    with pytest.raises(ValidationError):
        SafetyPolicy(
            allow_write_paths=[],
            deny_write_paths=[],
            allowed_tools=["local_command"],
            network_access="invalid",  # type: ignore[arg-type]
        )


def test_default_policy() -> None:
    """default_policy returns permissive defaults."""
    policy = SafetyPolicy.default_policy()
    assert policy.allow_write_paths == []
    assert policy.deny_write_paths == []
    assert policy.max_diff_size_bytes is None
    assert policy.allowed_tools == ["local_command"]
    assert policy.network_access == "deny"


def test_empty_defaults() -> None:
    """SafetyPolicy with no args uses empty lists and defaults."""
    policy = SafetyPolicy()
    assert policy.allow_write_paths == []
    assert policy.deny_write_paths == []
    assert policy.allowed_tools == []
    assert policy.network_access == "deny"
