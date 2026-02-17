"""Conversation execution contracts and LangChain v1 runtime adapter."""

from __future__ import annotations

import concurrent.futures
import logging
from collections.abc import Callable
from typing import Any, Protocol, cast

from langchain.agents import create_agent
from langchain.agents.middleware import (
    AgentMiddleware,
    AgentState,
    ModelRequest,
    ToolCallRequest,
    after_model,
    before_model,
    dynamic_prompt,
)
from langchain_core.messages import ToolMessage
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.errors import GraphRecursionError
from langgraph.runtime import Runtime
from langgraph.types import Command
from pydantic import BaseModel, ConfigDict, Field

from lily.policy import (
    PRECEDENCE_CONTRACT,
    evaluate_post_generation,
    evaluate_pre_generation,
    force_safe_style,
    resolve_effective_style,
)
from lily.prompting import PersonaContext, PromptBuildContext, PromptBuilder, PromptMode
from lily.session.models import ConversationLimitsConfig, Message, MessageRole

_LOGGER = logging.getLogger(__name__)
_DEFAULT_SYSTEM_PROMPT = (
    "You are Lily, an AI assistant.\n"
    "Provide clear, direct, helpful responses.\n"
    "If information is missing, say what is missing instead of guessing.\n"
)
_MAX_COMPACT_HISTORY_EVENTS = 20
_MAX_TOOL_CONTENT_CHARS = 240
_HISTORY_BUDGET_CHARS = 4000
_COMPACTION_SUMMARY_MAX_CHARS = 320
_COMPACTION_SUMMARY_HEAD_CHARS = 220
_COMPACTION_SUMMARY_TAIL_CHARS = 80
_MIN_HISTORY_EVENTS = 2


def _default_persona_context() -> PersonaContext:
    """Return default persona context for generic conversation turns.

    Returns:
        Default persona context with balanced style.
    """
    return PersonaContext(active_persona_id="default")


class ConversationRequest(BaseModel):
    """Normalized conversation turn request."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    session_id: str = Field(min_length=1)
    user_text: str = Field(min_length=1)
    model_name: str = Field(min_length=1)
    history: tuple[Message, ...] = ()
    limits: ConversationLimitsConfig = Field(default_factory=ConversationLimitsConfig)
    memory_summary: str = ""
    persona_context: PersonaContext = Field(default_factory=_default_persona_context)
    prompt_mode: PromptMode = PromptMode.FULL


class ConversationRuntimeContext(BaseModel):
    """LangChain runtime context schema for conversation execution."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    session_id: str = Field(min_length=1)
    model_name: str = Field(min_length=1)
    memory_summary: str = ""
    persona_context: PersonaContext
    prompt_mode: PromptMode


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

    def __init__(
        self,
        checkpointer: BaseCheckpointSaver | None = None,
        *,
        prompt_builder: PromptBuilder | None = None,
    ) -> None:
        """Create default runner.

        Args:
            checkpointer: Optional checkpoint saver for testability.
            prompt_builder: Optional prompt builder override.
        """
        self._checkpointer = checkpointer or InMemorySaver()
        self._prompt_builder = prompt_builder or PromptBuilder()

    def run(self, *, request: ConversationRequest) -> object:
        """Invoke LangChain agent for one conversation turn.

        Args:
            request: Normalized request.

        Returns:
            Raw LangChain invocation payload.
        """
        middleware = self._build_middleware()
        agent = create_agent(
            model=request.model_name,
            tools=[],
            system_prompt=_DEFAULT_SYSTEM_PROMPT,
            checkpointer=self._checkpointer,
            context_schema=ConversationRuntimeContext,
            middleware=middleware,
        )
        messages = _build_messages(request)
        payload: dict[str, Any] = {"messages": messages}
        config = _build_agent_invoke_config(request)
        runtime_context = ConversationRuntimeContext(
            session_id=request.session_id,
            model_name=request.model_name,
            memory_summary=request.memory_summary,
            persona_context=request.persona_context,
            prompt_mode=request.prompt_mode,
        )
        return agent.invoke(
            cast(Any, payload),
            config=cast(Any, config),
            context=runtime_context,
        )

    def _build_middleware(self) -> tuple[Any, ...]:
        """Build deterministic middleware stack for prompt and trace hooks.

        Returns:
            Ordered middleware tuple.
        """
        return (
            _build_dynamic_prompt_middleware(self._prompt_builder),
            _build_before_model_middleware(),
            _build_after_model_middleware(),
            ToolGuardrailMiddleware(),
        )


class ToolGuardrailMiddleware(
    AgentMiddleware[AgentState[object], ConversationRuntimeContext, object]
):
    """Middleware enforcing deterministic tool-call guardrails."""

    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command[object]],
    ) -> ToolMessage | Command[object]:
        """Validate tool call input before executing tool handler.

        Args:
            request: Tool call request payload.
            handler: Downstream tool handler.

        Returns:
            Tool execution result.

        Raises:
            ConversationExecutionError: If tool call is denied by policy.
        """
        args_value: object = None
        if isinstance(request.tool_call, dict):
            args_value = request.tool_call.get("args")
        args_text = str(args_value) if args_value is not None else ""
        decision = evaluate_pre_generation(args_text)
        if not decision.allowed:
            raise ConversationExecutionError(
                "Tool call denied by policy.",
                code="conversation_policy_denied",
            )
        return handler(request)


def _build_dynamic_prompt_middleware(prompt_builder: PromptBuilder) -> object:
    """Create dynamic prompt middleware for persona-aware prompt rendering.

    Args:
        prompt_builder: Prompt builder used for deterministic prompt rendering.

    Returns:
        LangChain dynamic prompt middleware.
    """

    @dynamic_prompt
    def lily_dynamic_prompt(request: ModelRequest[ConversationRuntimeContext]) -> str:
        """Build dynamic prompt from runtime persona context.

        Args:
            request: Model request carrying runtime context.

        Returns:
            Deterministic system prompt text.
        """
        runtime_context = request.runtime.context
        build_context = PromptBuildContext(
            persona=runtime_context.persona_context,
            mode=runtime_context.prompt_mode,
            session_id=runtime_context.session_id,
            model_name=runtime_context.model_name,
            memory_summary=runtime_context.memory_summary,
        )
        return prompt_builder.build(build_context)

    return lily_dynamic_prompt


def _build_before_model_middleware() -> object:
    """Create pre-model policy-check middleware.

    Returns:
        LangChain before-model middleware.
    """

    @before_model
    def lily_before_model(
        state: AgentState[object],
        runtime: Runtime[ConversationRuntimeContext],
    ) -> None:
        """Emit trace hook and enforce pre-generation policy checks.

        Args:
            state: Current agent state payload.
            runtime: LangGraph runtime context.

        Raises:
            ConversationExecutionError: If pre-generation policy denies input.
        """
        context = runtime.context
        _LOGGER.debug(
            "conversation.before_model session=%s persona=%s mode=%s",
            context.session_id,
            context.persona_context.active_persona_id,
            context.prompt_mode.value,
        )
        latest_user = _latest_user_text(state)
        if latest_user:
            decision = evaluate_pre_generation(latest_user)
            if not decision.allowed:
                raise ConversationExecutionError(
                    decision.reason,
                    code=decision.code or "conversation_policy_denied",
                )

    return lily_before_model


def _build_after_model_middleware() -> object:
    """Create post-model policy-check middleware.

    Returns:
        LangChain after-model middleware.
    """

    @after_model
    def lily_after_model(
        state: AgentState[object],
        runtime: Runtime[ConversationRuntimeContext],
    ) -> None:
        """Emit trace hook and enforce post-generation policy checks.

        Args:
            state: Current agent state payload.
            runtime: LangGraph runtime context.

        Raises:
            ConversationExecutionError: If post-generation policy denies output.
        """
        context = runtime.context
        _LOGGER.debug(
            "conversation.after_model session=%s persona=%s mode=%s",
            context.session_id,
            context.persona_context.active_persona_id,
            context.prompt_mode.value,
        )
        latest_assistant = _latest_assistant_text(state)
        if latest_assistant:
            decision = evaluate_post_generation(latest_assistant)
            if not decision.allowed:
                raise ConversationExecutionError(
                    decision.reason,
                    code=decision.code or "conversation_policy_denied",
                )

    return lily_after_model


def _build_messages(request: ConversationRequest) -> list[dict[str, str]]:
    """Build invoke payload messages from persisted session history + turn text.

    Args:
        request: Conversation request.

    Returns:
        Ordered message list for LangChain invocation.
    """
    messages = [
        {"role": item.role.value, "content": item.content}
        for item in _compact_history(request.history)
    ]
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
        checkpointer: BaseCheckpointSaver | None = None,
        normalize_text: Callable[[str], str] | None = None,
    ) -> None:
        """Create LangChain conversation executor.

        Args:
            runner: Optional runner override for tests.
            checkpointer: Optional checkpointer override for default runner wiring.
            normalize_text: Optional text normalization override for tests.
        """
        self._runner = runner or _LangChainAgentRunner(checkpointer=checkpointer)
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
                "persona_context": _apply_precedence(request),
            }
        )
        if not normalized.user_text:
            raise ConversationExecutionError(
                "Conversation input is empty.",
                code="conversation_invalid_input",
            )
        pre_decision = evaluate_pre_generation(normalized.user_text)
        if not pre_decision.allowed:
            raise ConversationExecutionError(
                pre_decision.reason,
                code=pre_decision.code or "conversation_policy_denied",
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
                post_decision = evaluate_post_generation(text)
                if not post_decision.allowed:
                    raise ConversationExecutionError(
                        post_decision.reason,
                        code=post_decision.code or "conversation_policy_denied",
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
        return exc.code in {
            "conversation_backend_unavailable",
            "conversation_timeout",
        }

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


def _apply_precedence(request: ConversationRequest) -> PersonaContext:
    """Apply precedence contract to derive effective persona style.

    Args:
        request: Normalized conversation request.

    Returns:
        Persona context with effective style for this turn.
    """
    user_style = request.persona_context.style_level
    effective_style = resolve_effective_style(user_style=user_style)
    if not evaluate_pre_generation(request.user_text).allowed:
        effective_style = force_safe_style()
    _LOGGER.debug(
        "conversation.precedence contract=%s resolved_style=%s",
        PRECEDENCE_CONTRACT,
        effective_style.value,
    )
    return request.persona_context.model_copy(update={"style_level": effective_style})


def _latest_user_text(state: AgentState[object]) -> str:
    """Extract latest user message text from agent state.

    Args:
        state: Current agent state payload.

    Returns:
        Latest user message text, or empty string when unavailable.
    """
    messages = state.get("messages", [])
    for message in reversed(messages):
        role = getattr(message, "type", "")
        content = getattr(message, "content", "")
        if role == "human" and isinstance(content, str):
            return content
    return ""


def _latest_assistant_text(state: AgentState[object]) -> str:
    """Extract latest assistant message text from agent state.

    Args:
        state: Current agent state payload.

    Returns:
        Latest assistant message text, or empty string when unavailable.
    """
    messages = state.get("messages", [])
    for message in reversed(messages):
        role = getattr(message, "type", "")
        content = getattr(message, "content", "")
        if role == "ai" and isinstance(content, str):
            return content
    return ""


def _compact_history(history: tuple[Message, ...]) -> tuple[Message, ...]:
    """Compact history to deterministic bounded context.

    Args:
        history: Full persisted conversation history.

    Returns:
        Compacted history tuple for prompt invocation.
    """
    filtered: list[Message] = []
    evicted_tool_events: list[Message] = []
    for item in history:
        if item.role == MessageRole.TOOL and _is_low_value_tool_output(item.content):
            evicted_tool_events.append(item)
            continue
        filtered.append(item)
    if len(filtered) > _MAX_COMPACT_HISTORY_EVENTS:
        older = filtered[:-_MAX_COMPACT_HISTORY_EVENTS]
        recent = filtered[-_MAX_COMPACT_HISTORY_EVENTS:]
        summary = _summarize_history(older)
        compacted = [Message(role=MessageRole.SYSTEM, content=summary), *recent]
    else:
        compacted = filtered
    if evicted_tool_events:
        tool_summary = _summarize_history(evicted_tool_events, label="tool")
        compacted.insert(0, Message(role=MessageRole.SYSTEM, content=tool_summary))
    return tuple(_enforce_char_budget(compacted, max_chars=_HISTORY_BUDGET_CHARS))


def _is_low_value_tool_output(content: str) -> bool:
    """Determine whether tool output is low-value for prompt context.

    Args:
        content: Tool output text.

    Returns:
        Whether content should be evicted from active context.
    """
    text = content.strip()
    if len(text) <= _MAX_TOOL_CONTENT_CHARS:
        return False
    lowered = text.lower()
    return not ("error" in lowered or "failed" in lowered)


def _summarize_history(
    events: list[Message],
    *,
    label: str = "history",
) -> str:
    """Create deterministic summary for compacted historical events.

    Args:
        events: Events being compacted.
        label: Summary label.

    Returns:
        Deterministic summary string.
    """
    snippets = []
    for event in events:
        preview = " ".join(event.content.split())
        snippets.append(f"{event.role.value}:{preview[:80]}")
    joined = " | ".join(snippets)
    if len(joined) > _COMPACTION_SUMMARY_MAX_CHARS:
        joined = (
            f"{joined[:_COMPACTION_SUMMARY_HEAD_CHARS]} [...] "
            f"{joined[-_COMPACTION_SUMMARY_TAIL_CHARS:]}"
        )
    return f"Compacted {label} summary ({len(events)} events): {joined}"


def _enforce_char_budget(events: list[Message], *, max_chars: int) -> list[Message]:
    """Trim oldest events until total char budget is satisfied.

    Args:
        events: Candidate events.
        max_chars: Maximum total content characters.

    Returns:
        Budget-compliant event list.
    """
    remaining = list(events)
    while (
        sum(len(event.content) for event in remaining) > max_chars
        and len(remaining) > _MIN_HISTORY_EVENTS
    ):
        remaining.pop(0)
    return remaining
