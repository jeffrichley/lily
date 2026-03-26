"""Conversation compression middleware wiring helpers."""

from __future__ import annotations

from typing import Literal, cast

from langchain.agents.middleware.summarization import SummarizationMiddleware
from langchain_core.language_models import BaseChatModel

from lily.runtime.config_schema import ConversationCompressionConfig

type _TriggerContextSize = (
    tuple[Literal["fraction"], float]
    | tuple[Literal["tokens"], int]
    | tuple[Literal["messages"], int]
)

type _KeepContextSize = _TriggerContextSize


def build_conversation_compression_middleware(
    config: ConversationCompressionConfig,
    *,
    model: BaseChatModel,
) -> SummarizationMiddleware:
    """Build a SummarizationMiddleware from Lily compression config.

    Args:
        config: Validated conversation compression configuration.
        model: Chat model used by SummarizationMiddleware to generate summaries.

    Returns:
        A configured `SummarizationMiddleware` instance.
    """
    trigger: _TriggerContextSize
    if config.trigger.kind == "fraction":
        trigger = ("fraction", cast(float, config.trigger.threshold))
    elif config.trigger.kind == "tokens":
        trigger = ("tokens", cast(int, config.trigger.threshold))
    else:
        trigger = ("messages", cast(int, config.trigger.threshold))

    keep: _KeepContextSize
    if config.keep.kind == "fraction":
        keep = ("fraction", cast(float, config.keep.value))
    elif config.keep.kind == "tokens":
        keep = ("tokens", cast(int, config.keep.value))
    else:
        keep = ("messages", cast(int, config.keep.value))

    return SummarizationMiddleware(model=model, trigger=trigger, keep=keep)
