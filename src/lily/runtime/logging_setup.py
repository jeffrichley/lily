"""Skill telemetry logging: JSON lines default to a file; optional stderr mirror."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

_SKILL_LOG = logging.getLogger("lily.skill.telemetry")
_HANDLER_MARKER = "lily_skill_telemetry_handler"


def clear_skill_telemetry_handlers() -> None:
    """Remove Lily-managed handlers from ``lily.skill.telemetry`` and close them."""
    for handler in list(_SKILL_LOG.handlers):
        if getattr(handler, _HANDLER_MARKER, False):
            _SKILL_LOG.removeHandler(handler)
            handler.close()


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
    """Attach a file handler and optionally mirror telemetry to stderr.

    Idempotent for repeated calls in-process: replaces prior Lily-managed handlers.

    Args:
        log_path: Append-only JSONL destination (parent dirs are created).
        echo_to_stderr: When true, also log the same records to ``sys.stderr``.
    """
    clear_skill_telemetry_handlers()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter("%(message)s"))
    setattr(file_handler, _HANDLER_MARKER, True)
    _SKILL_LOG.addHandler(file_handler)
    _SKILL_LOG.setLevel(logging.INFO)
    if echo_to_stderr:
        stream_handler = logging.StreamHandler(sys.stderr)
        stream_handler.setLevel(logging.INFO)
        stream_handler.setFormatter(
            logging.Formatter("%(levelname)s %(name)s: %(message)s"),
        )
        setattr(stream_handler, _HANDLER_MARKER, True)
        _SKILL_LOG.addHandler(stream_handler)
