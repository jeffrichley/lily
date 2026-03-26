"""Structured skill trace for supervisor invoke results (retrieval-only MVP)."""

from __future__ import annotations

from contextvars import ContextVar, Token
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SkillRetrievalTraceEntry(BaseModel):
    """One skill_retrieve call observed during an agent invoke."""

    model_config = ConfigDict(frozen=True)

    name: str
    reference_subpath: str | None = None
    outcome: Literal["success", "error"] = Field(
        ...,
        description="Whether loader returned content or surfaced a policy/load error.",
    )
    detail: str | None = Field(
        default=None,
        description="Error or denial message when outcome is error.",
    )


class SkillInvokeTrace(BaseModel):
    """Deterministic skill metadata for one `AgentRuntime.run` / supervisor prompt."""

    model_config = ConfigDict(frozen=True)

    skills_enabled: bool = False
    catalog_injected: bool = False
    retrievals: tuple[SkillRetrievalTraceEntry, ...] = ()


_skill_retrieval_trace_buffer: ContextVar[list[SkillRetrievalTraceEntry] | None] = (
    ContextVar("skill_retrieval_trace_buffer", default=None)
)


def bind_skill_trace() -> tuple[Token, list[SkillRetrievalTraceEntry]]:
    """Start a trace buffer for the current invoke; pair with ``reset_skill_trace``.

    Returns:
        Token for reset and the mutable list appended by ``skill_retrieve``.
    """
    buf: list[SkillRetrievalTraceEntry] = []
    token = _skill_retrieval_trace_buffer.set(buf)
    return token, buf


def reset_skill_trace(token: Token) -> None:
    """Restore the previous trace buffer binding.

    Args:
        token: Value returned from ``bind_skill_trace``.
    """
    _skill_retrieval_trace_buffer.reset(token)


def record_skill_retrieval_trace(entry: SkillRetrievalTraceEntry) -> None:
    """Append one entry when ``skill_retrieve`` runs inside an active trace buffer.

    Args:
        entry: One retrieval outcome to append to the active buffer.
    """
    buf = _skill_retrieval_trace_buffer.get()
    if buf is not None:
        buf.append(entry)
