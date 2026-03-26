"""Retrieval policy gates and effective tool resolution (PRD F6)."""

from __future__ import annotations

from collections.abc import Sequence

from lily.runtime.config_schema import SkillsConfig, SkillsToolsConfig
from lily.runtime.skill_discovery import SkillCandidate


def candidate_allowed_by_lists(canonical_key: str, skills_config: SkillsConfig) -> bool:
    """Return whether allowlist/denylist permits this canonical skill key.

    Args:
        canonical_key: Normalized skill identifier.
        skills_config: Skills policy configuration.

    Returns:
        True when the key may appear in the merged registry.
    """
    if canonical_key in skills_config.denylist:
        return False
    allow = skills_config.allowlist
    return not (bool(allow) and canonical_key not in allow)


def list_policy_denial_reason(
    canonical_key: str,
    skills_config: SkillsConfig,
) -> str | None:
    """Explain why allowlist/denylist blocks retrieval, or None if not blocked.

    Args:
        canonical_key: Normalized skill identifier.
        skills_config: Skills policy configuration.

    Returns:
        Human-readable denial reason when lists block the key.
    """
    if canonical_key in skills_config.denylist:
        return f"skill {canonical_key!r} is listed in skills.denylist"
    allow = skills_config.allowlist
    if bool(allow) and canonical_key not in allow:
        return f"skill {canonical_key!r} is not listed in skills.allowlist"
    return None


def build_retrieval_blocked_keys(
    candidates: Sequence[SkillCandidate],
    skills_config: SkillsConfig,
) -> dict[str, str]:
    """Map canonical keys blocked by allow/deny lists to deterministic reasons.

    Used so retrieval can distinguish policy denial from unknown skills.

    Args:
        candidates: Discovered skill packages (pre-registry merge).
        skills_config: Skills policy configuration.

    Returns:
        Keys that exist on disk but are excluded from the registry, with reasons.
    """
    out: dict[str, str] = {}
    for cand in candidates:
        key = cand.summary.canonical_key
        if candidate_allowed_by_lists(key, skills_config):
            continue
        reason = list_policy_denial_reason(key, skills_config)
        out[key] = reason or "skill retrieval blocked by skills policy lists"
    return out


def retrieval_config_denial_reason(
    skills_config: SkillsConfig,
    *,
    skill_scope: str,
) -> str | None:
    """Return a reason when runtime retrieval config blocks this skill scope.

    Args:
        skills_config: Skills configuration including ``skills.retrieval``.
        skill_scope: Winning scope for the registry entry
            (``repository``, ``user``, or ``system``).

    Returns:
        Denial message when retrieval is disabled or scope is not permitted.
    """
    retrieval = skills_config.retrieval
    if not retrieval.enabled:
        return "skill retrieval is disabled (skills.retrieval.enabled is false)"
    allowed_scopes = retrieval.scopes_allowlist
    if allowed_scopes and skill_scope not in allowed_scopes:
        return (
            f"skill retrieval is not allowed for scope {skill_scope!r}; "
            f"permitted scopes: {sorted(allowed_scopes)}"
        )
    return None


def parse_allowed_tools_field(raw: str | None) -> frozenset[str]:
    """Parse comma- or whitespace-separated tool ids from frontmatter.

    Args:
        raw: Optional ``allowed-tools`` string from ``SKILL.md``.

    Returns:
        Non-empty tool id tokens.
    """
    if raw is None or not str(raw).strip():
        return frozenset()
    parts = [p.strip() for p in str(raw).replace(",", " ").split() if p.strip()]
    return frozenset(parts)


def _union_default_packs(skills_tools: SkillsToolsConfig) -> frozenset[str]:
    """Collect tool ids from configured default packs.

    Args:
        skills_tools: Skills tool-pack configuration (``default_packs`` and ``packs``).

    Returns:
        Frozen union of tool ids listed in each default pack.
    """
    out: set[str] = set()
    for pack_id in skills_tools.default_packs:
        out.update(skills_tools.packs[pack_id])
    return frozenset(out)


def effective_skill_tools(
    *,
    allowed_tools_raw: str | None,
    skills_tools: SkillsToolsConfig,
    runtime_tool_ids: frozenset[str],
) -> frozenset[str]:
    """Compute tools a skill may use: intersect runtime with skill policy (PRD F6).

    When ``allowed-tools`` is omitted, behavior follows ``skills.tools.default_policy``:
    ``inherit_runtime`` uses the full runtime set; ``deny_unless_allowed`` yields an
    empty skill-level set; ``use_default_packs`` unions configured default packs.

    When ``allowed-tools`` is present, explicit ids replace the default-policy branch;
    the result is still intersected with ``runtime_tool_ids``.

    Args:
        allowed_tools_raw: Raw ``allowed-tools`` frontmatter or None if omitted.
        skills_tools: ``skills.tools`` configuration (packs and default policy).
        runtime_tool_ids: Tool names the agent runtime actually exposes.

    Returns:
        Effective tool id set (possibly empty). Empty sets must fail fast on
        tool-calling paths; content retrieval may still be allowed (PRD F6).
    """
    if allowed_tools_raw is not None and str(allowed_tools_raw).strip():
        skill_ids = parse_allowed_tools_field(allowed_tools_raw)
        return skill_ids & runtime_tool_ids
    policy = skills_tools.default_policy
    if policy == "inherit_runtime":
        return frozenset(runtime_tool_ids)
    if policy == "deny_unless_allowed":
        return frozenset()
    return _union_default_packs(skills_tools) & runtime_tool_ids
