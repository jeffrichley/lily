"""Runtime logging: Lily package log levels, Rich console, and skill telemetry."""

from __future__ import annotations

import logging
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler

_LILY_ROOT_LOGGER = "lily"
_SKILL_LOG = logging.getLogger("lily.skill.telemetry")
_HANDLER_MARKER = "lily_skill_telemetry_handler"
_LILY_RICH_HANDLER_MARKER = "lily_rich_stderr_handler"


def configure_lily_package_logging(level: str) -> None:
    """Apply ``[logging].level`` to stdlib loggers under the ``lily`` namespace.

    Sets ``logging.getLogger("lily")`` so all descendant loggers such as
    ``lily.runtime.*`` inherit the threshold unless they set their own level.

    Attaches a single **Rich** ``RichHandler`` to stderr for ``lily.*`` records
    (idempotent per process). Does **not** change third-party loggers (e.g.
    ``langchain``). Skill F7 telemetry on ``lily.skill.telemetry`` sets its own
    level to ``INFO`` when skill handlers are installed, so JSON lines still emit
    even if this level is ``WARNING`` or ``ERROR``.

    Args:
        level: One of ``DEBUG``, ``INFO``, ``WARNING``, ``ERROR`` (from config).
    """
    numeric = getattr(logging, level.upper(), logging.INFO)
    lily = logging.getLogger(_LILY_ROOT_LOGGER)
    lily.setLevel(numeric)
    if any(getattr(h, _LILY_RICH_HANDLER_MARKER, False) for h in lily.handlers):
        return
    rich_handler = RichHandler(
        level=logging.NOTSET,
        console=Console(stderr=True),
        show_time=True,
        show_path=False,
        markup=False,
        rich_tracebacks=False,
        omit_repeated_times=True,
    )
    setattr(rich_handler, _LILY_RICH_HANDLER_MARKER, True)
    lily.addHandler(rich_handler)


def clear_skill_telemetry_handlers() -> None:
    """Remove Lily-managed handlers from ``lily.skill.telemetry`` and close them."""
    for handler in list(_SKILL_LOG.handlers):
        if getattr(handler, _HANDLER_MARKER, False):
            _SKILL_LOG.removeHandler(handler)
            handler.close()
    if not _SKILL_LOG.handlers:
        _SKILL_LOG.propagate = True


def resolve_skill_telemetry_log_path(
    config_path: str | Path,
    *,
    relative_override: str | None,
) -> Path:
    """Pick the log file path for skill JSON telemetry.

    Default: ``<parent-of-config-dir>/logs/skill-telemetry.jsonl`` (e.g. under
    ``.lily/logs`` when the runtime config lives in ``.lily/config/``).

    Args:
        config_path: Path to the runtime config file (``agent.toml`` / ``agent.yaml``).
        relative_override: Optional path; relative paths resolve against the config
            file's directory.

    Returns:
        Absolute filesystem path for the append-only JSONL log.
    """
    config_dir = Path(config_path).resolve().parent
    if relative_override is not None and relative_override.strip():
        candidate = Path(relative_override.strip())
        resolved = (
            candidate if candidate.is_absolute() else config_dir / candidate
        ).resolve()
        return resolved
    return (config_dir.parent / "logs" / "skill-telemetry.jsonl").resolve()


def configure_skill_telemetry_handlers(
    log_path: Path,
    *,
    echo_to_stderr: bool,
) -> None:
    """Attach a plain file handler and optionally mirror telemetry to stderr with Rich.

    Idempotent for repeated calls in-process: replaces prior Lily-managed handlers.

    The JSONL file remains **plain text** (one JSON object per line). The optional
    stderr mirror uses :class:`rich.logging.RichHandler` so operators get styled
    output when using ``--show-skill-telemetry``. Telemetry does not propagate to
    the parent ``lily`` logger, avoiding duplicate lines next to
    :func:`configure_lily_package_logging`.

    Args:
        log_path: Append-only JSONL destination (parent dirs are created).
        echo_to_stderr: When true, also log the same records to ``sys.stderr`` via Rich.
    """
    clear_skill_telemetry_handlers()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter("%(message)s"))
    setattr(file_handler, _HANDLER_MARKER, True)
    _SKILL_LOG.addHandler(file_handler)
    _SKILL_LOG.setLevel(logging.INFO)
    _SKILL_LOG.propagate = False
    if echo_to_stderr:
        rich_echo = RichHandler(
            level=logging.INFO,
            console=Console(stderr=True),
            show_time=True,
            show_path=False,
            markup=False,
            rich_tracebacks=False,
            omit_repeated_times=True,
        )
        setattr(rich_echo, _HANDLER_MARKER, True)
        _SKILL_LOG.addHandler(rich_echo)
