"""Rich presenters and row helpers for ``lily skills`` commands."""

from __future__ import annotations

from functools import partial
from typing import Literal

from rich.table import Table

from lily.runtime.skill_cli_diagnostics import SkillCliDiagnostics
from lily.runtime.skill_policies import (
    effective_skill_tools,
    list_policy_denial_reason,
    retrieval_config_denial_reason,
)
from lily.runtime.skill_registry import SkillRegistryEntry
from lily.runtime.skill_types import SkillValidationError, normalize_skill_name

SortKey = Literal["key", "name", "scope"]


def runtime_tool_ids(diag: SkillCliDiagnostics) -> frozenset[str]:
    """Return runtime tool ids from the config allowlist.

    Args:
        diag: Loaded diagnostics snapshot.

    Returns:
        Frozen set of tool names permitted for the agent runtime.
    """
    return frozenset(diag.runtime_config.tools.allowlist)


def _normalize_lookup_key(raw: str) -> str:
    """Map user input to a canonical key guess.

    Args:
        raw: Raw CLI argument text.

    Returns:
        Normalized key string suitable for registry lookup.
    """
    try:
        return normalize_skill_name(raw)
    except SkillValidationError:
        return raw.lower().replace(" ", "-")


def _entry_by_display_name(
    diag: SkillCliDiagnostics,
    display: str,
) -> SkillRegistryEntry | None:
    """Resolve a registry entry when the user typed the display name verbatim.

    Args:
        diag: Loaded diagnostics snapshot.
        display: Exact ``SkillSummary.name`` string.

    Returns:
        Matching entry when found, otherwise ``None``.
    """
    reg = diag.registry
    for k in reg.canonical_keys():
        entry = reg.get(k)
        if entry is not None and entry.summary.name.strip() == display:
            return entry
    return None


def resolve_registry_entry(
    diag: SkillCliDiagnostics,
    name: str,
) -> SkillRegistryEntry | None:
    """Match by canonical key or exact display name.

    Args:
        diag: Loaded diagnostics snapshot.
        name: User-supplied skill label.

    Returns:
        Registry row when found, otherwise ``None``.
    """
    raw = name.strip()
    if not raw:
        return None
    key = _normalize_lookup_key(raw)
    hit = diag.registry.get(key)
    if hit is not None:
        return hit
    return _entry_by_display_name(diag, raw)


def _indexed_rows(
    diag: SkillCliDiagnostics,
) -> list[tuple[str, SkillRegistryEntry | None, str]]:
    """Build one table row per merged registry entry.

    Args:
        diag: Loaded diagnostics snapshot.

    Returns:
        Row tuples for indexed skills.
    """
    rows: list[tuple[str, SkillRegistryEntry | None, str]] = []
    for k in diag.registry.canonical_keys():
        e = diag.registry.get(k)
        assert e is not None
        rows.append((k, e, "indexed"))
    return rows


def _policy_only_rows(
    diag: SkillCliDiagnostics,
) -> list[tuple[str, SkillRegistryEntry | None, str]]:
    """Build rows for keys blocked by lists but absent from the merged registry.

    Args:
        diag: Loaded diagnostics snapshot.

    Returns:
        Row tuples describing policy-only blocks.
    """
    rows: list[tuple[str, SkillRegistryEntry | None, str]] = []
    for k, reason in sorted(diag.policy_blocked.items()):
        if diag.registry.get(k) is not None:
            continue
        rows.append((k, None, f"blocked: {reason}"))
    return rows


def _filter_rows_contains(
    rows: list[tuple[str, SkillRegistryEntry | None, str]],
    contains: str,
) -> list[tuple[str, SkillRegistryEntry | None, str]]:
    """Keep rows whose key or display name matches a substring.

    Args:
        rows: Candidate rows.
        contains: Case-insensitive substring filter.

    Returns:
        Filtered rows.
    """
    needle = contains.lower()
    out: list[tuple[str, SkillRegistryEntry | None, str]] = []
    for k, e, status in rows:
        name_l = (e.summary.name.lower() if e else "") + k.lower()
        if needle in name_l or needle in k.lower():
            out.append((k, e, status))
    return out


def list_row_tuples(
    diag: SkillCliDiagnostics,
    *,
    contains: str | None,
) -> list[tuple[str, SkillRegistryEntry | None, str]]:
    """Build sortable rows: key, optional entry, status text.

    Args:
        diag: Loaded diagnostics snapshot.
        contains: Optional substring filter for names or keys.

    Returns:
        Row tuples for the skills list table.
    """
    rows = _indexed_rows(diag) + _policy_only_rows(diag)
    if contains is None:
        return rows
    return _filter_rows_contains(rows, contains)


def _list_row_sort_key(
    sort: SortKey,
    item: tuple[str, SkillRegistryEntry | None, str],
) -> tuple[object, ...]:
    """Return a comparable key for one skills list row.

    Args:
        sort: Column ordering key.
        item: One row tuple from ``list_row_tuples``.

    Returns:
        Tuple used as the ``sorted`` key for stable ordering.
    """
    k, e, _st = item
    if sort == "key":
        return (k,)
    if sort == "name":
        name = e.summary.name.lower() if e else k
        return (name, k)
    scope = e.scope if e else ""
    return (scope, k)


def sort_rows(
    rows: list[tuple[str, SkillRegistryEntry | None, str]],
    sort: SortKey,
) -> list[tuple[str, SkillRegistryEntry | None, str]]:
    """Sort list rows for stable CLI output.

    Args:
        rows: Unsorted row tuples.
        sort: Column ordering key.

    Returns:
        Sorted row tuples.
    """
    return sorted(rows, key=partial(_list_row_sort_key, sort))


def _add_index_row(
    table: Table,
    k: str,
    e: SkillRegistryEntry | None,
    status: str,
    *,
    verbose: bool,
) -> None:
    """Append one row to the skills index table.

    Args:
        table: Rich table under construction.
        k: Canonical skill key column.
        e: Registry entry when indexed, otherwise ``None`` for policy-only rows.
        status: Human-readable status label.
        verbose: Whether to include the skill directory column.
    """
    if e is not None:
        ver = e.version or "—"
        path_s = str(e.skill_dir)
        table.add_row(
            k,
            e.summary.name,
            e.scope,
            ver,
            status,
            *([path_s] if verbose else []),
        )
        return
    table.add_row(k, "—", "—", "—", status, *([""] if verbose else []))


def build_skills_index_table(
    diag: SkillCliDiagnostics,
    *,
    sort: SortKey,
    contains: str | None,
    verbose: bool,
) -> tuple[Table, str]:
    """Build the skills list table and a dim footer line.

    Args:
        diag: Loaded diagnostics snapshot.
        sort: Sort order for rows.
        contains: Optional substring filter.
        verbose: Whether to show filesystem paths.

    Returns:
        Rich table plus a footer markup string.
    """
    rows = sort_rows(list_row_tuples(diag, contains=contains), sort)
    table = Table(title="Skills index")
    table.add_column("Key", style="cyan", no_wrap=True)
    table.add_column("Name")
    table.add_column("Scope")
    table.add_column("Version")
    table.add_column("Status")
    if verbose:
        table.add_column("Path")

    for k, e, status in rows:
        _add_index_row(table, k, e, status, verbose=verbose)

    footer = (
        f"[dim]Sorted by {sort}; "
        f"{len(diag.registry.canonical_keys())} indexed, "
        f"{len(diag.policy_blocked)} policy-blocked key(s).[/dim]"
    )
    return table, footer


def doctor_summary_lines(diag: SkillCliDiagnostics) -> list[str]:
    """Build Rich markup lines for the doctor summary panel.

    Args:
        diag: Loaded diagnostics snapshot with skills enabled.

    Returns:
        Rich markup strings for the summary panel body.
    """
    sc = diag.skills_config
    assert sc is not None
    lines = [
        "[bold]Enabled[/bold]: yes",
        f"[bold]Config directory[/bold]: {diag.base_path}",
        f"[bold]Candidates parsed[/bold]: {len(diag.candidates)}",
        f"[bold]Indexed after merge[/bold]: {len(diag.registry.canonical_keys())}",
        f"[bold]skills.retrieval.enabled[/bold]: {sc.retrieval.enabled}",
    ]
    if sc.retrieval.scopes_allowlist:
        lines.append(
            "[bold]Retrieval scope allowlist[/bold]: "
            + ", ".join(sorted(sc.retrieval.scopes_allowlist))
        )
    else:
        lines.append("[bold]Retrieval scope allowlist[/bold]: (any scope)")
    return lines


def _doctor_invalid_rows(diag: SkillCliDiagnostics) -> list[tuple[str, str]]:
    """Rows for packages that failed to parse during discovery.

    Args:
        diag: Loaded diagnostics snapshot.

    Returns:
        Rich kind/detail pairs for invalid packages.
    """
    rows: list[tuple[str, str]] = []
    for ev in diag.discovery_events:
        if ev.kind != "skipped_invalid":
            continue
        detail = f"{ev.path}: {ev.detail or 'invalid package'}"
        rows.append(("[red]invalid[/red]", detail))
    return rows


def _doctor_shadow_rows(diag: SkillCliDiagnostics) -> list[tuple[str, str]]:
    """Rows for shadowed duplicate canonical keys.

    Args:
        diag: Loaded diagnostics snapshot.

    Returns:
        Rich kind/detail pairs for shadowed collisions.
    """
    rows: list[tuple[str, str]] = []
    for ev in diag.registry.events:
        if ev.kind != "shadowed":
            continue
        sup = f" superseded by {ev.superseded_by}" if ev.superseded_by else ""
        rows.append(
            (
                "[yellow]shadowed[/yellow]",
                f"{ev.canonical_key} @ {ev.path}{sup}",
            )
        )
    return rows


def _doctor_policy_rows(diag: SkillCliDiagnostics) -> list[tuple[str, str]]:
    """Rows for allow/deny list blocks.

    Args:
        diag: Loaded diagnostics snapshot.

    Returns:
        Rich kind/detail pairs for policy blocks.
    """
    return [
        ("[magenta]policy[/magenta]", f"{k}: {reason}")
        for k, reason in sorted(diag.policy_blocked.items())
    ]


def _doctor_issue_rows(diag: SkillCliDiagnostics) -> list[tuple[str, str]]:
    """Collect (kind column, detail column) pairs for doctor diagnostics.

    Args:
        diag: Loaded diagnostics snapshot.

    Returns:
        Concatenated Rich rows for the diagnostics table.
    """
    return (
        _doctor_invalid_rows(diag)
        + _doctor_shadow_rows(diag)
        + _doctor_policy_rows(diag)
    )


def doctor_issues_table(diag: SkillCliDiagnostics) -> Table:
    """Build diagnostics table for invalid, shadowed, and policy-blocked rows.

    Args:
        diag: Loaded diagnostics snapshot.

    Returns:
        Rich table ready for console printing.
    """
    issues = Table(title="Diagnostics")
    issues.add_column("Kind")
    issues.add_column("Detail")
    pairs = _doctor_issue_rows(diag)
    for kind, detail in pairs:
        issues.add_row(kind, detail)
    if not pairs:
        issues.add_row("ok", "No invalid packages, shadowing, or list blocks recorded.")
    return issues


def _inspect_identity_lines(entry: SkillRegistryEntry) -> list[str]:
    """Name, paths, and version lines for inspect output.

    Args:
        entry: Registry row for the requested skill.

    Returns:
        Rich markup strings for identity and path fields.
    """
    return [
        f"[bold]Name[/bold]: {entry.summary.name}",
        f"[bold]Canonical key[/bold]: {entry.summary.canonical_key}",
        f"[bold]Description[/bold]: {entry.summary.description}",
        f"[bold]Scope[/bold]: {entry.scope}",
        f"[bold]Version[/bold]: {entry.version or '—'}",
        f"[bold]Skill directory[/bold]: {entry.skill_dir}",
        f"[bold]SKILL.md[/bold]: {entry.skill_md_path}",
        "",
    ]


def _inspect_policy_tool_lines(
    entry: SkillRegistryEntry,
    diag: SkillCliDiagnostics,
) -> list[str]:
    """Policy and effective-tool lines for inspect output.

    Args:
        entry: Registry row for the requested skill.
        diag: Loaded diagnostics snapshot.

    Returns:
        Rich markup strings for policy and tool intersection.
    """
    sc = diag.skills_config
    assert sc is not None
    rt_tools = runtime_tool_ids(diag)
    deny_lists = list_policy_denial_reason(entry.summary.canonical_key, sc)
    deny_retrieval = retrieval_config_denial_reason(
        sc,
        skill_scope=entry.scope,
    )
    eff = effective_skill_tools(
        allowed_tools_raw=entry.summary.allowed_tools,
        skills_tools=sc.tools,
        runtime_tool_ids=rt_tools,
    )
    eff_display = ", ".join(sorted(eff)) if eff else "(empty)"
    return [
        "[bold]Policy (lists)[/bold]: "
        + (deny_lists or "allow/deny lists do not block this key"),
        "[bold]Policy (retrieval)[/bold]: "
        + (deny_retrieval or "retrieval config allows this scope"),
        "",
        f"[bold]Runtime tool allowlist[/bold]: {', '.join(sorted(rt_tools))}",
        f"[bold]Effective tools (F6 ∩ runtime)[/bold]: {eff_display}",
    ]


def inspect_skill_markup_lines(
    entry: SkillRegistryEntry,
    diag: SkillCliDiagnostics,
) -> list[str]:
    """Rich markup lines for ``skills inspect`` panel body.

    Args:
        entry: Registry row for the requested skill.
        diag: Loaded diagnostics snapshot.

    Returns:
        Rich markup strings for the inspect panel.
    """
    return _inspect_identity_lines(entry) + _inspect_policy_tool_lines(entry, diag)
