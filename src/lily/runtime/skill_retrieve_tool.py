"""LangChain tool for on-demand skill retrieval (bound via context var)."""

from __future__ import annotations

from contextvars import ContextVar, Token

from langchain_core.tools import tool

from lily.runtime.skill_loader import (
    SkillLoader,
    SkillLoadError,
    SkillNotFoundError,
    SkillReferenceError,
)

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
    """Load a skill's full SKILL.md or a UTF-8 file under its references/ directory.

    Args:
        name: Skill name as listed in the catalog (matches frontmatter ``name``).
        reference_subpath: Optional file path relative to ``references/``
            (for example ``notes.md`` or ``subdir/guide.md``). Omit to return
            the full ``SKILL.md`` file text.

    Returns:
        Raw file contents, or an error message when the loader is not bound.
    """
    loader = _skill_loader_ctx.get()
    if loader is None:
        return "Skill retrieval is not available: runtime did not bind a skill loader."
    ref = reference_subpath
    if ref is not None and ref.strip() == "":
        ref = None
    try:
        return loader.retrieve(name.strip(), ref)
    except SkillNotFoundError as exc:
        return str(exc)
    except SkillReferenceError as exc:
        return str(exc)
    except SkillLoadError as exc:
        return str(exc)
