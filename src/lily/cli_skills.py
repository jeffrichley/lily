"""Typer handlers for ``lily skills`` (list, inspect, doctor)."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from typer import Exit

from lily.cli_options import ConfigOption, OverrideOption
from lily.cli_skills_presenters import (
    SortKey,
    build_skills_index_table,
    doctor_issues_table,
    doctor_summary_lines,
    inspect_skill_markup_lines,
    resolve_registry_entry,
)
from lily.runtime.config_loader import ConfigLoadError
from lily.runtime.skill_cli_diagnostics import SkillCliDiagnostics

skills_app = typer.Typer(
    no_args_is_help=True,
    help="Inspect local skills, registry merge, and retrieval policy.",
)
_console = Console()


@skills_app.command("list")
def skills_list_command(
    config: ConfigOption = Path(".lily/config/agent.toml"),
    override: OverrideOption = None,
    sort: Annotated[
        SortKey,
        typer.Option("--sort", help="Sort by canonical key, display name, or scope."),
    ] = "key",
    contains: Annotated[
        str | None,
        typer.Option(
            "--contains",
            help="Keep rows whose key or display name contains this substring.",
        ),
    ] = None,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Show extra columns (paths)."),
    ] = False,
) -> None:
    """List discovered skills, merge outcomes, and policy-blocked keys.

    Args:
        config: Base runtime config path.
        override: Optional override runtime config path.
        sort: Sort order for printed rows.
        contains: Optional substring filter on key or display name.
        verbose: Whether to include filesystem paths.

    Raises:
        Exit: When the runtime config cannot be loaded (exit code 1).
    """
    try:
        diag = SkillCliDiagnostics.from_config_paths(config, override)
    except ConfigLoadError as exc:
        _console.print(Panel.fit(str(exc), title="Config Error", border_style="red"))
        raise Exit(code=1) from exc

    if not diag.enabled or diag.skills_config is None:
        _console.print(
            Panel.fit(
                "Skills are disabled or not configured "
                "(set `[skills]` with `enabled = true` in the runtime config).",
                title="Skills",
                border_style="yellow",
            )
        )
        return

    table, footer = build_skills_index_table(
        diag,
        sort=sort,
        contains=contains,
        verbose=verbose,
    )
    _console.print(table)
    _console.print(footer)


@skills_app.command("inspect")
def skills_inspect_command(
    name: Annotated[str, typer.Argument(help="Skill display name or canonical key.")],
    config: ConfigOption = Path(".lily/config/agent.toml"),
    override: OverrideOption = None,
) -> None:
    """Show metadata, policy, and effective tools for one indexed skill.

    Args:
        name: Skill display name or canonical key.
        config: Base runtime config path.
        override: Optional override runtime config path.

    Raises:
        Exit: When config loading fails, skills are disabled, or the name is unknown
            (exit code 1).
    """
    try:
        diag = SkillCliDiagnostics.from_config_paths(config, override)
    except ConfigLoadError as exc:
        _console.print(Panel.fit(str(exc), title="Config Error", border_style="red"))
        raise Exit(code=1) from exc

    if not diag.enabled or diag.skills_config is None:
        _console.print(
            Panel.fit(
                "Skills are disabled; nothing to inspect.",
                title="Skills",
                border_style="yellow",
            )
        )
        raise Exit(code=1)

    entry = resolve_registry_entry(diag, name)
    if entry is None:
        _console.print(
            Panel.fit(
                f"No indexed skill matches {name!r}. "
                "Use `lily skills list` to see canonical keys.",
                title="Not found",
                border_style="red",
            )
        )
        raise Exit(code=1)

    lines = inspect_skill_markup_lines(entry, diag)
    _console.print(
        Panel.fit(
            "\n".join(lines),
            title=f"Skill: {entry.summary.name}",
            border_style="green",
        )
    )


@skills_app.command("doctor")
def skills_doctor_command(
    config: ConfigOption = Path(".lily/config/agent.toml"),
    override: OverrideOption = None,
) -> None:
    """Summarize discovery health, collisions, invalid packages, and policy blocks.

    Args:
        config: Base runtime config path.
        override: Optional override runtime config path.

    Raises:
        Exit: When the runtime config cannot be loaded (exit code 1).
    """
    try:
        diag = SkillCliDiagnostics.from_config_paths(config, override)
    except ConfigLoadError as exc:
        _console.print(Panel.fit(str(exc), title="Config Error", border_style="red"))
        raise Exit(code=1) from exc

    if not diag.enabled or diag.skills_config is None:
        _console.print(
            Panel.fit(
                "Skills subsystem is [yellow]disabled[/yellow] or missing `[skills]` "
                "in the runtime config.",
                title="Skills doctor",
                border_style="yellow",
            )
        )
        return

    _console.print(
        Panel.fit(
            "\n".join(doctor_summary_lines(diag)),
            title="Summary",
            border_style="blue",
        )
    )
    _console.print(doctor_issues_table(diag))
