"""Format skill catalog text for system-prompt injection (summaries only)."""

from __future__ import annotations

from lily.runtime.skill_registry import SkillRegistry


def format_skill_catalog_block(registry: SkillRegistry) -> str:
    """Build a stable markdown block listing enabled skills (name + description only).

    Entries are ordered by canonical key. Does not include full ``SKILL.md`` bodies.

    Args:
        registry: Resolved skill registry after discovery and policy filters.

    Returns:
        Markdown text, or an empty string when the registry has no entries.
    """
    keys = registry.canonical_keys()
    if not keys:
        return ""

    lines = [
        "## Skill catalog (index)",
        "",
        "Each bullet is a **short summary** so you can see what skills exist. The full "
        "procedure, constraints, and examples live in that skill's `SKILL.md` and are "
        "**not** included above.",
        "",
        "**How to use this list:**",
        "- When the user's request matches a skill's purpose, call `skill_retrieve` "
        "with **`name`** set to that skill's display **name** (shown in bold) or to "
        "the **canonical id** in backticks—either form works.",
        "- That returns the **entire** `SKILL.md` (frontmatter + body). Read it and "
        "follow it for that turn or task.",
        "- To pull an extra file bundled with the skill (anywhere under that "
        "skill's directory), call `skill_retrieve` again with the same **`name`** "
        "and **`reference_subpath`** set to the path relative to the skill folder "
        "(for example `references/notes.md`, `assets/palette.json`, or `SKILL.md`).",
        "",
    ]
    for key in keys:
        entry = registry.get(key)
        if entry is None:
            continue
        name = entry.summary.name
        desc = entry.summary.description
        lines.append(f"- **{name}** (`{key}`): {desc}")
    return "\n".join(lines) + "\n"
