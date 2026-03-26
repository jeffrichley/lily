"""Unit tests for conversation facade routing and message compaction."""

from __future__ import annotations

import pytest

from lily.commands.types import CommandResult
from lily.runtime.conversation import (
    ConversationExecutionError,
    ConversationRequest,
    ConversationResponse,
    _build_messages,
)
from lily.runtime.facade import RuntimeFacade
from lily.session.models import (
    HistoryCompactionBackend,
    Message,
    MessageRole,
    ModelConfig,
    Session,
)
from lily.skills.types import SkillSnapshot


class _ConversationSuccessExecutor:
    """Facade-level conversation executor fixture."""

    def run(self, request: ConversationRequest) -> ConversationResponse:
        """Return deterministic conversation response.

        Args:
            request: Conversation request payload.

        Returns:
            Successful response.
        """
        assert request.user_text == "hello lily"
        assert request.limits.tool_loop.enabled is False
        assert request.limits.tool_loop.max_rounds == 8
        assert request.persona_context.active_persona_id == "default"
        assert request.prompt_mode.value == "full"
        return ConversationResponse(text="hello human")


class _ConversationErrorExecutor:
    """Facade-level conversation executor fixture returning stable error."""

    def run(self, request: ConversationRequest) -> ConversationResponse:
        """Raise deterministic conversation error.

        Args:
            request: Conversation request payload.
        """
        del request
        raise ConversationExecutionError(
            "Conversation backend is unavailable.",
            code="conversation_backend_unavailable",
        )


class _ConversationCaptureExecutor:
    """Facade-level conversation executor fixture that captures requests."""

    def __init__(self) -> None:
        """Initialize last-request capture slot."""
        self.last_request: ConversationRequest | None = None

    def run(self, request: ConversationRequest) -> ConversationResponse:
        """Capture request and return deterministic response."""
        self.last_request = request
        return ConversationResponse(text="ok")


class _ConversationInvalidationCaptureExecutor:
    """Conversation executor fixture that records cache invalidation reasons."""

    def __init__(self) -> None:
        """Initialize invalidation reason capture."""
        self.reasons: list[str] = []

    def run(self, request: ConversationRequest) -> ConversationResponse:
        """Return deterministic response."""
        del request
        return ConversationResponse(text="ok")

    def invalidate_cache(self, *, reason: str) -> None:
        """Capture invalidation reason invoked by runtime facade."""
        self.reasons.append(reason)


class _CommandRegistryFixedResult:
    """Command registry fixture that returns one fixed command result."""

    def __init__(self, result: CommandResult) -> None:
        """Store deterministic command result."""
        self._result = result

    def dispatch(self, command: object, session: object) -> CommandResult:
        """Return fixed command result regardless of command payload."""
        del command
        del session
        return self._result


def _session() -> Session:
    """Create minimal session fixture for runtime routing tests."""
    return Session(
        session_id="session-test",
        active_agent="default",
        skill_snapshot=SkillSnapshot(version="v-test", skills=()),
        model_config=ModelConfig(),
        conversation_state=[
            Message(role=MessageRole.SYSTEM, content="system"),
            Message(role=MessageRole.USER, content="prior user"),
            Message(role=MessageRole.ASSISTANT, content="prior assistant"),
        ],
    )


@pytest.mark.unit
def test_runtime_routes_non_command_input_to_conversation_executor() -> None:
    """Runtime should route non-command turns through conversation executor path."""
    # Arrange - runtime with success conversation executor, session
    runtime = RuntimeFacade(conversation_executor=_ConversationSuccessExecutor())
    session = _session()

    # Act - handle non-command input
    result = runtime.handle_input("hello lily", session)

    # Assert - conversation reply and session state updated
    assert result.status.value == "ok"
    assert result.code == "conversation_reply"
    assert result.message == "hello human"
    assert result.data == {"route": "conversation"}
    assert session.conversation_state[-2].role.value == "user"
    assert session.conversation_state[-2].content == "hello lily"
    assert session.conversation_state[-1].role.value == "assistant"
    assert session.conversation_state[-1].content == "hello human"


@pytest.mark.unit
def test_runtime_maps_conversation_errors_to_deterministic_result() -> None:
    """Runtime should map conversation execution failures into stable envelopes."""
    # Arrange - runtime with error conversation executor, session
    runtime = RuntimeFacade(conversation_executor=_ConversationErrorExecutor())
    session = _session()

    # Act - handle input (executor raises)
    result = runtime.handle_input("hello lily", session)

    # Assert - error envelope with conversation_backend_unavailable
    assert result.status.value == "error"
    assert result.code == "conversation_backend_unavailable"
    assert result.message == "Error: Conversation backend is unavailable."


@pytest.mark.unit
@pytest.mark.parametrize(
    ("command_text", "result_code", "expected_reason"),
    [
        ("/reload_skills", "skills_reloaded", "skills_reloaded"),
        ("/reload_persona", "persona_reloaded", "persona_reloaded"),
    ],
)
def test_runtime_invalidates_conversation_cache_on_reload_commands(
    command_text: str,
    result_code: str,
    expected_reason: str,
) -> None:
    """Runtime should invalidate conversation cache after reload-style commands."""
    # Arrange - runtime with fixed command result and invalidation-capable executor
    executor = _ConversationInvalidationCaptureExecutor()
    runtime = RuntimeFacade(
        command_registry=_CommandRegistryFixedResult(
            CommandResult.ok("done", code=result_code)
        ),
        conversation_executor=executor,
    )
    session = _session()

    # Act - execute command
    result = runtime.handle_input(command_text, session)

    # Assert - result succeeds and cache invalidation reason captured
    assert result.status.value == "ok"
    assert executor.reasons == [expected_reason]


@pytest.mark.unit
def test_build_messages_compacts_low_value_tool_output_and_bounds_history() -> None:
    """Message builder should evict low-value tool payloads and compact history."""
    # Arrange - long history with large tool payload, request with compaction
    history = tuple(
        [
            Message(role=MessageRole.USER, content=f"user turn {index}")
            for index in range(30)
        ]
        + [
            Message(
                role=MessageRole.TOOL,
                content="x" * 500,
            )
        ]
    )
    request = ConversationRequest(
        session_id="session-test",
        user_text="current turn",
        model_name="test-model",
        history=history,
        limits={
            "tool_loop": {"enabled": False, "max_rounds": 8},
            "timeout": {"enabled": False, "timeout_ms": 30_000},
            "retries": {"enabled": True, "max_retries": 1},
            "compaction": {"backend": "rule_based", "max_tokens": 1000},
        },
    )

    # Act - build messages
    messages = _build_messages(request)

    # Assert - current turn last, compacted, low-value tool output evicted
    assert messages[-1] == {"role": "user", "content": "current turn"}
    assert len(messages) <= 23
    assert not any(
        message["role"] == "tool" and message["content"] == ("x" * 500)
        for message in messages
    )


@pytest.mark.unit
def test_build_messages_langgraph_native_backend_bounds_history() -> None:
    """LangGraph-native compaction should bound history under token budget."""
    # Arrange - long history, langgraph_native compaction, low max_tokens
    history = tuple(
        Message(role=MessageRole.USER, content=f"user turn {index}")
        for index in range(80)
    )
    request = ConversationRequest.model_validate(
        {
            "session_id": "session-test",
            "user_text": "current turn",
            "model_name": "test-model",
            "history": [item.model_dump() for item in history],
            "limits": {
                "tool_loop": {"enabled": False, "max_rounds": 8},
                "timeout": {"enabled": False, "timeout_ms": 30_000},
                "retries": {"enabled": True, "max_retries": 1},
                "compaction": {"backend": "langgraph_native", "max_tokens": 80},
            },
        }
    )

    # Act - build messages
    messages = _build_messages(request)

    # Assert - current turn last, compacted length under full history
    assert messages[-1] == {"role": "user", "content": "current turn"}
    assert len(messages) < len(history) + 1


@pytest.mark.unit
def test_compaction_backend_parity_preserves_latest_history_turn() -> None:
    """Both compaction backends should preserve recent turns near prompt tail."""
    # Arrange - long history, rule and native requests with compaction limits
    history = tuple(
        Message(role=MessageRole.USER, content=f"user turn {index}")
        for index in range(60)
    )
    rule_request = ConversationRequest(
        session_id="session-test",
        user_text="now",
        model_name="test-model",
        history=history,
    )
    native_request = ConversationRequest.model_validate(
        {
            "session_id": "session-test",
            "user_text": "now",
            "model_name": "test-model",
            "history": [item.model_dump() for item in history],
            "limits": {
                "tool_loop": {"enabled": False, "max_rounds": 8},
                "timeout": {"enabled": False, "timeout_ms": 30_000},
                "retries": {"enabled": True, "max_retries": 1},
                "compaction": {"backend": "langgraph_native", "max_tokens": 120},
            },
        }
    )

    # Act - build messages for both backends
    rule_messages = _build_messages(rule_request)
    native_messages = _build_messages(native_request)

    # Assert - both preserve latest turn (user turn 59) in compacted output
    assert rule_messages[-2]["role"] in {"user", "assistant", "system", "tool"}
    assert native_messages[-2]["role"] in {"user", "assistant", "system", "tool"}
    assert any(item["content"] == "user turn 59" for item in rule_messages)
    assert any(item["content"] == "user turn 59" for item in native_messages)


@pytest.mark.unit
def test_runtime_facade_can_override_compaction_backend() -> None:
    """Runtime facade should pass configured compaction backend into request limits."""
    # Arrange - capture executor, runtime with langgraph_native compaction override
    capture = _ConversationCaptureExecutor()
    runtime = RuntimeFacade(
        conversation_executor=capture,
        compaction_backend=HistoryCompactionBackend.LANGGRAPH_NATIVE,
        compaction_max_tokens=77,
    )
    session = _session()

    # Act - send conversation input
    result = runtime.handle_input("hello lily", session)

    # Assert - request has compaction backend and max_tokens
    assert result.status.value == "ok"
    assert capture.last_request is not None
    assert (
        capture.last_request.limits.compaction.backend
        == HistoryCompactionBackend.LANGGRAPH_NATIVE
    )
    assert capture.last_request.limits.compaction.max_tokens == 77
