"""Layer 2: Local command executor."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from lily.kernel.graph_models import ExecutorSpec
from lily.kernel.paths import LOGS_DIR


class ExecResult(BaseModel):
    """Result of a single step execution."""

    success: bool
    returncode: int
    error_message: str | None = None
    log_paths: dict[str, str] = Field(default_factory=dict)


def run_local_command(
    executor_spec: ExecutorSpec,
    *,
    run_root: Path,
    step_id: str,
    attempt: int,
    timeout_s: float | None = None,
) -> ExecResult:
    """
    Execute a local command, capturing stdout/stderr to run logs.
    Logs at: .iris/runs/<run_id>/logs/steps/<step_id>/<attempt>/
    """
    if executor_spec.kind != "local_command":
        return ExecResult(
            success=False,
            returncode=-1,
            error_message=f"Unsupported executor kind: {executor_spec.kind!r}",
            log_paths={},
        )

    log_dir = run_root / LOGS_DIR / "steps" / step_id / str(attempt)
    log_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = log_dir / "stdout.txt"
    stderr_path = log_dir / "stderr.txt"
    executor_json_path = log_dir / "executor.json"

    # executor.json summary
    summary: dict[str, Any] = {
        "argv": executor_spec.argv,
        "cwd": executor_spec.cwd,
        "timeout_s": timeout_s,
    }
    if executor_spec.env:
        summary["env"] = executor_spec.env
    executor_json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    env = None
    if executor_spec.env is not None:
        import os

        env = os.environ.copy()
        env.update(executor_spec.env)

    cwd = executor_spec.cwd
    if cwd is not None:
        cwd = Path(cwd)
        if not cwd.is_absolute():
            cwd = run_root / cwd

    try:
        result = subprocess.run(
            executor_spec.argv,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired as e:
        stdout_path.write_text(e.stdout or "", encoding="utf-8")
        stderr_path.write_text(e.stderr or "", encoding="utf-8")
        return ExecResult(
            success=False,
            returncode=-1,
            error_message="timeout",
            log_paths={
                "stdout": str(stdout_path),
                "stderr": str(stderr_path),
                "executor.json": str(executor_json_path),
            },
        )
    except FileNotFoundError as e:
        stderr_path.write_text(str(e), encoding="utf-8")
        return ExecResult(
            success=False,
            returncode=-1,
            error_message=f"command not found: {e}",
            log_paths={
                "stdout": str(stdout_path),
                "stderr": str(stderr_path),
                "executor.json": str(executor_json_path),
            },
        )

    stdout_path.write_text(result.stdout or "", encoding="utf-8")
    stderr_path.write_text(result.stderr or "", encoding="utf-8")

    return ExecResult(
        success=result.returncode == 0,
        returncode=result.returncode,
        error_message=None
        if result.returncode == 0
        else (result.stderr or f"exit code {result.returncode}"),
        log_paths={
            "stdout": str(stdout_path),
            "stderr": str(stderr_path),
            "executor.json": str(executor_json_path),
        },
    )
