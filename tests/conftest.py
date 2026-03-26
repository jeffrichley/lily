"""Shared pytest configuration for reboot test suites."""

from __future__ import annotations

import os
import socket
from collections.abc import Iterator

import pytest
from langchain_core.language_models import BaseChatModel
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage

from lily.runtime.config_schema import ModelProfileConfig, ModelProvider
from lily.runtime.model_factory import ModelBuilder, ModelFactory

_LIVE_PROVIDER_ENV_VARS = (
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GOOGLE_API_KEY",
    "GROQ_API_KEY",
)
_ORIGINAL_CREATE_CONNECTION = socket.create_connection
_ORIGINAL_SOCKET_CONNECT = socket.socket.connect


def _network_guard_error() -> RuntimeError:
    """Return deterministic outbound-network guard error."""
    return RuntimeError(
        "Outbound network calls are blocked in tests by default. "
        "Use @pytest.mark.allows_network for explicit opt-in."
    )


def _is_localhost_host(host: object) -> bool:
    """Return whether the socket host target resolves to localhost."""
    if not isinstance(host, str):
        return False
    normalized = host.strip("[]").lower()
    return normalized in {"localhost", "127.0.0.1", "::1"}


def _extract_host(target: object) -> object:
    """Extract host from socket address argument."""
    if isinstance(target, tuple) and target:
        return target[0]
    return target


def _blocked_create_connection(*_args: object, **_kwargs: object) -> object:
    """Block non-localhost socket create_connection in default test runs."""
    target = _kwargs.get("address")
    if target is None and _args:
        target = _args[0]
    if _is_localhost_host(_extract_host(target)):
        return _ORIGINAL_CREATE_CONNECTION(*_args, **_kwargs)
    raise _network_guard_error()


def _blocked_socket_connect(
    self: socket.socket, *_args: object, **_kwargs: object
) -> None:
    """Block non-localhost raw socket connect in default test runs."""
    target = _kwargs.get("address")
    if target is None and _args:
        target = _args[0]
    if _is_localhost_host(_extract_host(target)):
        return _ORIGINAL_SOCKET_CONNECT(self, *_args, **_kwargs)
    raise _network_guard_error()


_blocked_create_connection.__lily_guarded__ = True
_blocked_socket_connect.__lily_guarded__ = True


def _blocked_init_chat_model(*_args: object, **_kwargs: object) -> object:
    """Block live model initialization in tests by default."""
    raise RuntimeError(
        "Live model initialization is blocked in tests. "
        "Use @pytest.mark.allows_network for explicit opt-in."
    )


@pytest.fixture(autouse=True)
def _guard_live_network_and_models(
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[None]:
    """Apply default-deny guards for network + live model calls.

    Tests can opt in with ``@pytest.mark.allows_network``.
    """
    allows_network = request.node.get_closest_marker("allows_network") is not None
    if allows_network:
        yield
        return

    configured_live_vars = [
        key for key in _LIVE_PROVIDER_ENV_VARS if os.environ.get(key, "").strip()
    ]
    strict_env_fail = os.environ.get("LILY_TEST_STRICT_PROVIDER_ENV") == "1"
    if configured_live_vars and strict_env_fail:
        joined = ", ".join(configured_live_vars)
        pytest.fail(
            "Live provider credentials are set during a strict non-network test run: "
            f"{joined}. Unset these env vars or mark the test with "
            "@pytest.mark.allows_network."
        )
    for key in configured_live_vars:
        monkeypatch.delenv(key, raising=False)

    monkeypatch.setattr(socket, "create_connection", _blocked_create_connection)
    monkeypatch.setattr(socket.socket, "connect", _blocked_socket_connect)
    monkeypatch.setattr(
        "lily.runtime.model_factory.init_chat_model",
        _blocked_init_chat_model,
    )
    yield


@pytest.fixture
def fake_model_factory() -> ModelFactory:
    """Return deterministic fake-model factory for runtime tests."""

    def _builder(_profile: ModelProfileConfig) -> BaseChatModel:
        return FakeMessagesListChatModel(responses=[AIMessage(content="fake")])

    builders: dict[ModelProvider, ModelBuilder] = {
        ModelProvider.OPENAI: _builder,
        ModelProvider.OLLAMA: _builder,
    }
    return ModelFactory(builders=builders)
