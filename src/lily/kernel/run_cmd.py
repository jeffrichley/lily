"""Single place for secure subprocess invocation.

Uses shell=False, list args, and controlled env. All bandit suppressions live here.
"""

from __future__ import annotations

import os
import subprocess  # nosec B404 - used with shell=False, list args, controlled env
from collections.abc import Sequence
from pathlib import Path

# Re-export so callers can catch/annotate without importing subprocess elsewhere.
TimeoutExpired = subprocess.TimeoutExpired
CompletedProcess = subprocess.CompletedProcess


def minimal_env() -> dict[str, str]:
    """Minimal env for subprocess (PATH only).

    Overlay with caller-provided vars as needed.

    Returns:
        Dict with PATH only; caller may update before passing to run_subprocess.
    """
    return {"PATH": os.environ.get("PATH", "")}


def run_subprocess(
    argv: Sequence[str],
    *,
    cwd: str | Path | None = None,
    env: dict[str, str] | None = None,
    timeout: float | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a subprocess with shell=False, list args, and controlled env.

    Caller should build env via minimal_env() and overlay any extra vars.
    Returncode is not checked; caller inspects result.returncode.

    Args:
        argv: Command and arguments as a list (no shell parsing).
        cwd: Working directory for the subprocess.
        env: Environment dict; defaults to minimal_env() if None.
        timeout: Optional timeout in seconds.

    Returns:
        CompletedProcess with stdout, stderr, returncode.
    """
    return subprocess.run(  # noqa: PLW1510  # nosec B603 - shell=False, list args, controlled env
        list(argv),
        cwd=str(cwd) if cwd is not None else None,
        env=env or minimal_env(),
        capture_output=True,
        text=True,
        timeout=timeout,
        shell=False,
    )
