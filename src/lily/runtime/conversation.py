"""Conversation execution contracts and LangChain v1 runtime adapter."""

from __future__ import annotations

import concurrent.futures
from collections.abc import Callable
from typing import Any, Protocol, cast

from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.errors import GraphRecursionError
from pydantic import BaseModel, ConfigDict, Field

from lily.session.models import ConversationLimitsConfig, Message

_DEFAULT_SYSTEM_PROMPT = (
    "You are Lily, an AI assistant.\n"
    "Provide clear, direct, helpful responses.\n"
    "If information is missing, say what is missing instead of guessing.\n"
)


class ConversationRequest(BaseModel):
    """Normalized conversation turn request."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    session_id: str = Field(min_length=1)
    user_text: str = Field(min_length=1)
    model_name: str = Field(min_length=1)
    history: tuple[Message, ...] = ()
    limits: ConversationLimitsConfig = Field(default_factory=ConversationLimitsConfig)


class ConversationResponse(BaseModel):
    """Normalized conversation turn response."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    text: str = Field(min_length=1)


class ConversationExecutionError(RuntimeError):
    """Conversation runtime failure with stable error code."""

    def __init__(self, message: str, *, code: str) -> None:
        """Create structured conversation execution error.

        Args:
            message: Human-readable error message.
            code: Stable machine-readable error code.
        """
        super().__init__(message)
        self.code = code


class ConversationExecutor(Protocol):
    """Conversation executor protocol used by runtime facade."""

    def run(self, request: ConversationRequest) -> ConversationResponse:
        """Execute one conversation turn.

        Args:
            request: Normalized conversation request.
        """


class AgentRunner(Protocol):
    """Internal runner abstraction for invoking LangChain agent graph."""

    def run(
        self,
        *,
        request: ConversationRequest,
    ) -> object:
        """Run one invocation and return raw LangChain payload.

        Args:
            request: Normalized conversation request.
        """


class _LangChainAgentRunner:
    """Default LangChain v1/graph runner with in-memory checkpointer."""

    def __init__(self, checkpointer: InMemorySaver | None = None) -> None:
        """Create default runner.

        Args:
            checkpointer: Optional checkpoint saver for testability.
        """
        self._checkpointer = checkpointer or InMemorySaver()

    def run(self, *, request: ConversationRequest) -> object:
        """Invoke LangChain agent for one conversation turn.

        Args:
            request: Normalized request.

        Returns:
            Raw LangChain invocation payload.
        """
        agent = create_agent(
            model=request.model_name,
            tools=[],
            system_prompt=_DEFAULT_SYSTEM_PROMPT,
            checkpointer=self._checkpointer,
        )
        messages = _build_messages(request)
        payload: dict[str, Any] = {"messages": messages}
        config = _build_agent_invoke_config(request)
        return agent.invoke(
            cast(Any, payload),
            config=cast(Any, config),
        )


def _build_messages(request: ConversationRequest) -> list[dict[str, str]]:
    """Build invoke payload messages from persisted session history + turn text.

    Args:
        request: Conversation request.

    Returns:
        Ordered message list for LangChain invocation.
    """
    messages: list[dict[str, str]] = []
    for item in request.history:
        if item.role.value == "system":
            continue
        messages.append({"role": item.role.value, "content": item.content})
    messages.append({"role": "user", "content": request.user_text})
    return messages


def _build_agent_invoke_config(request: ConversationRequest) -> dict[str, Any]:
    """Build LangGraph invoke config with deterministic boundary settings.

    Args:
        request: Normalized conversation request.

    Returns:
        Config dictionary passed to LangGraph invoke.
    """
    config: dict[str, Any] = {"configurable": {"thread_id": request.session_id}}
    recursion_limit = _resolve_recursion_limit(request)
    if recursion_limit is not None:
        config["recursion_limit"] = recursion_limit
    return config


def _resolve_recursion_limit(request: ConversationRequest) -> int | None:
    """Map tool-loop rounds into LangGraph recursion limit.

    Args:
        request: Normalized conversation request.

    Returns:
        Recursion limit when tool-loop boundary is enabled, else None.
    """
    tool_loop = request.limits.tool_loop
    if not tool_loop.enabled:
        return None
    # Approximate graph-step budget: model/tool alternation + framing steps.
    return (tool_loop.max_rounds * 2) + 4


class LangChainConversationExecutor:
    """Conversation executor backed by LangChain v1 `create_agent`."""

    def __init__(
        self,
        runner: AgentRunner | None = None,
        *,
        normalize_text: Callable[[str], str] | None = None,
    ) -> None:
        """Create LangChain conversation executor.

        Args:
            runner: Optional runner override for tests.
            normalize_text: Optional text normalization override for tests.
        """
        self._runner = runner or _LangChainAgentRunner()
        self._normalize_text = normalize_text or (lambda text: text.strip())

    def run(self, request: ConversationRequest) -> ConversationResponse:
        """Execute one conversation turn through LangChain runtime.

        Args:
            request: Normalized request.

        Returns:
            Normalized assistant response.

        Raises:
            ConversationExecutionError: If invoke fails or payload is invalid.
        """
        normalized = request.model_copy(
            update={
                "session_id": request.session_id.strip(),
                "user_text": request.user_text.strip(),
                "model_name": request.model_name.strip(),
            }
        )
        if not normalized.user_text:
            raise ConversationExecutionError(
                "Conversation input is empty.",
                code="conversation_invalid_input",
            )
        max_attempts = self._resolve_max_attempts(normalized)
        for attempt in range(1, max_attempts + 1):
            try:
                raw = self._invoke_with_limits(normalized)
                text = self._extract_text(raw)
                if not text:
                    raise ConversationExecutionError(
                        "Conversation backend returned empty output.",
                        code="conversation_invalid_response",
                    )
                return ConversationResponse(text=text)
            except ConversationExecutionError as exc:
                if not self._should_retry(
                    exc=exc, attempt=attempt, max_attempts=max_attempts
                ):
                    raise
        raise ConversationExecutionError(
            "Conversation backend is unavailable.",
            code="conversation_backend_unavailable",
        )

    def _invoke_with_limits(self, request: ConversationRequest) -> object:
        """Run one conversation invoke with configured timeout boundary.

        Args:
            request: Normalized conversation request.

        Returns:
            Raw invocation payload.
        """
        timeout = request.limits.timeout
        if not timeout.enabled:
            return self._run_runner(request)
        return self._run_with_timeout(request=request, timeout_ms=timeout.timeout_ms)

    def _run_with_timeout(
        self, *, request: ConversationRequest, timeout_ms: int
    ) -> object:
        """Run one invoke under wall-clock timeout budget.

        Args:
            request: Normalized request payload.
            timeout_ms: Timeout budget in milliseconds.

        Returns:
            Raw invocation payload.

        Raises:
            ConversationExecutionError: If timeout budget is exceeded.
        """
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self._run_runner, request)
            try:
                return future.result(timeout=timeout_ms / 1000)
            except concurrent.futures.TimeoutError as exc:
                future.cancel()
                raise ConversationExecutionError(
                    "Conversation turn exceeded configured timeout.",
                    code="conversation_timeout",
                ) from exc

    def _run_runner(self, request: ConversationRequest) -> object:
        """Run underlying conversation runner and normalize failures.

        Args:
            request: Normalized request payload.

        Returns:
            Raw invocation payload.

        Raises:
            ConversationExecutionError: On normalized backend/loop failures.
        """
        try:
            return self._runner.run(request=request)
        except GraphRecursionError as exc:
            raise ConversationExecutionError(
                "Conversation tool loop exceeded configured max rounds.",
                code="conversation_tool_loop_limit",
            ) from exc
        except ConversationExecutionError:
            raise
        except Exception as exc:
            raise ConversationExecutionError(
                "Conversation backend is unavailable.",
                code="conversation_backend_unavailable",
            ) from exc

    @staticmethod
    def _resolve_max_attempts(request: ConversationRequest) -> int:
        """Resolve max attempts based on retry boundary settings.

        Args:
            request: Normalized request payload.

        Returns:
            Number of attempts to run (initial + retries).
        """
        retries = request.limits.retries
        if not retries.enabled:
            return 1
        return retries.max_retries + 1

    @staticmethod
    def _should_retry(
        *,
        exc: ConversationExecutionError,
        attempt: int,
        max_attempts: int,
    ) -> bool:
        """Determine whether to retry after a failed conversation attempt.

        Args:
            exc: Normalized conversation execution error.
            attempt: Current attempt number.
            max_attempts: Maximum attempts for current run.

        Returns:
            Whether another attempt should be made.
        """
        if attempt >= max_attempts:
            return False
        return exc.code in {"conversation_backend_unavailable", "conversation_timeout"}

    def _extract_text(self, payload: object) -> str:
        """Extract assistant text from LangChain invocation payload.

        Args:
            payload: Raw invocation payload.

        Returns:
            Normalized assistant text or empty string.
        """
        if not isinstance(payload, dict):
            return ""
        messages = payload.get("messages")
        if not isinstance(messages, list) or not messages:
            return ""
        return self._extract_text_from_message(messages[-1])

    def _extract_text_from_message(self, message: object) -> str:
        """Extract normalized text from one message-like payload.

        Args:
            message: Raw final message payload from LangChain response.

        Returns:
            Normalized extracted text, or empty string.
        """
        content = getattr(message, "content", None)
        if isinstance(content, str):
            return self._normalize_text(content)
        if isinstance(content, list):
            return self._normalize_text(self._join_text_chunks(content))
        if isinstance(message, dict):
            maybe = message.get("content")
            if isinstance(maybe, str):
                return self._normalize_text(maybe)
        return ""

    @staticmethod
    def _join_text_chunks(content: list[object]) -> str:
        """Join text chunks from list-style message content.

        Args:
            content: Raw content list payload.

        Returns:
            Joined text chunk string.
        """
        chunks = [
            str(item.get("text", "")).strip()
            for item in content
            if isinstance(item, dict)
        ]
        return "\n".join(chunk for chunk in chunks if chunk)
