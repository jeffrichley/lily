"""Unit tests for global test-time network/model guardrails."""

from __future__ import annotations

import socket

import pytest

from lily.runtime.config_schema import ModelProfileConfig, ModelProvider
from lily.runtime.model_factory import ModelFactory, ModelFactoryError

pytestmark = pytest.mark.unit


def test_default_test_mode_blocks_live_model_initialization() -> None:
    """Default test guard should fail fast on real model initialization."""
    # Arrange - build one openai profile with default model factory.
    profile = ModelProfileConfig(
        provider=ModelProvider.OPENAI,
        model="gpt-5-nano",
        temperature=0.1,
        timeout_seconds=5,
    )
    factory = ModelFactory()

    # Act - run model factory create_model with default test guard active.
    with pytest.raises(ModelFactoryError) as err:
        factory.create_model(profile)
    # Assert - guard blocks init_chat_model path with deterministic error.
    assert "blocked in tests" in str(err.value)


def test_default_test_mode_blocks_outbound_network() -> None:
    """Default test guard should block raw outbound socket attempts."""
    # Arrange - use a known public address to force outbound-connect path.
    address = ("example.com", 80)
    # Act - attempt outbound connect under default guard.
    with pytest.raises(RuntimeError) as err:
        socket.create_connection(address, timeout=1.0)
    # Assert - guard emits deterministic block message.
    assert "Outbound network calls are blocked" in str(err.value)


@pytest.mark.allows_network
def test_allows_network_marker_disables_default_socket_patch() -> None:
    """Opt-in marker should skip default socket monkeypatch guard."""
    # Arrange - no setup required; test inspects create_connection symbol.
    # Act - inspect sentinel attribute applied by default guard patching.
    guarded = getattr(socket.create_connection, "__lily_guarded__", False)
    # Assert - network marker bypasses default socket patch.
    assert not guarded
