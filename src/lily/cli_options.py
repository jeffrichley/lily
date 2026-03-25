"""Shared Typer option annotations for Lily CLI commands."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

ConfigOption = Annotated[
    Path,
    typer.Option(
        "--config",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=False,
        help="Path to base runtime config (.yaml/.yml/.toml).",
    ),
]
OverrideOption = Annotated[
    Path | None,
    typer.Option(
        "--override",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=False,
        help="Optional path to runtime override config (.yaml/.yml/.toml).",
    ),
]
