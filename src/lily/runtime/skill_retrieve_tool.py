"""LangChain tool for on-demand skill retrieval (bound via context var)."""

from __future__ import annotations

from contextvars import ContextVar, Token

from langchain_core.tools import tool

from lily.runtime.skill_invoke_trace import (
    SkillRetrievalTraceEntry,
    record_skill_retrieval_trace,
)
from lily.runtime.skill_loader import (
    SkillLoader,
    SkillLoadError,
    SkillNotFoundError,
    SkillReferenceError,
    SkillRetrievalDeniedError,
)

SKILL_RETRIEVE_TOOL_ID = "skill_retrieve"

_skill_loader_ctx: ContextVar[SkillLoader | None] = ContextVar(
    "skill_loader",
    default=None,
)


def bind_skill_loader(loader: SkillLoader | None) -> Token:
    """Set the loader used by ``skill_retrieve`` for the current async/sync context.

    Args:
        loader: Active loader, or ``None`` when skills are disabled.

    Returns:
        Token for ``reset_skill_loader``.
    """
    return _skill_loader_ctx.set(loader)


def reset_skill_loader(token: Token) -> None:
    """Restore the previous loader binding.

    Args:
        token: Value returned from ``bind_skill_loader``.
    """
    _skill_loader_ctx.reset(token)


@tool
def skill_retrieve(name: str, reference_subpath: str | None = None) -> str:
    """Load a skill's full SKILL.md or a UTF-8 file under its package directory.

    Args:
        name: Skill name as listed in the catalog (matches frontmatter ``name``).
        reference_subpath: Optional file path relative to the skill directory
            (for example ``references/notes.md``, ``assets/data.json``, or
            ``SKILL.md``). Omit to return the full ``SKILL.md`` file text.

    Returns:
        Raw file contents, or an error message when the loader is not bound.
    """
    stripped_name = name.strip()
    loader = _skill_loader_ctx.get()
    ref = reference_subpath
    if ref is not None and ref.strip() == "":
        ref = None

    def _trace_error(detail: str) -> None:
        record_skill_retrieval_trace(
            SkillRetrievalTraceEntry(
                name=stripped_name,
                reference_subpath=ref,
                outcome="error",
                detail=detail,
            )
        )

    if loader is None:
        msg = "Skill retrieval is not available: runtime did not bind a skill loader."
        _trace_error(msg)
        return msg
    try:
        text = loader.retrieve(stripped_name, ref)
    except SkillNotFoundError as exc:
        detail = str(exc)
        _trace_error(detail)
        return detail
    except SkillRetrievalDeniedError as exc:
        detail = str(exc)
        _trace_error(detail)
        return detail
    except SkillReferenceError as exc:
        detail = str(exc)
        _trace_error(detail)
        return detail
    except SkillLoadError as exc:
        detail = str(exc)
        _trace_error(detail)
        return detail
    record_skill_retrieval_trace(
        SkillRetrievalTraceEntry(
            name=stripped_name,
            reference_subpath=ref,
            outcome="success",
            detail=None,
        )
    )
    return text
