"""Layer 3: Local command gate runner. Executes gate commands and captures logs."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from lily.kernel.gate_models import GateSpec
from lily.kernel.paths import LOGS_DIR


class GateExecutionResult(BaseModel):
    """Result of a single gate execution (no envelope yet)."""

    success: bool
    returncode: int
    error_message: str | None = None
    log_paths: dict[str, str] = Field(default_factory=dict)


def run_local_gate(
    gate_spec: GateSpec,
    run_root: Path,
    attempt: int = 1,
) -> GateExecutionResult:
    """
    Execute a gate as a local command; capture stdout/stderr to run logs.
    Logs at: .iris/runs/<run_id>/logs/gates/<gate_id>/<attempt>/
    """
    runner = gate_spec.runner
    if runner.kind != "local_command":
        return GateExecutionResult(
            success=False,
            returncode=-1,
            error_message=f"Unsupported gate runner kind: {runner.kind!r}",
            log_paths={},
        )

    log_dir = run_root / LOGS_DIR / "gates" / gate_spec.gate_id / str(attempt)
    log_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = log_dir / "stdout.txt"
    stderr_path = log_dir / "stderr.txt"
    runner_json_path = log_dir / "runner.json"

    summary: dict[str, Any] = {
        "gate_id": gate_spec.gate_id,
        "argv": runner.argv,
        "cwd": runner.cwd,
        "timeout_s": runner.timeout_s,
    }
    if runner.env:
        summary["env"] = runner.env
    runner_json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    env = None
    if runner.env is not None:
        import os

        env = os.environ.copy()
        env.update(runner.env)

    cwd_path: Path | None = None
    if runner.cwd is not None:
        cwd_path = Path(runner.cwd)
        if not cwd_path.is_absolute():
            cwd_path = run_root / cwd_path

    try:
        result = subprocess.run(
            runner.argv,
            cwd=cwd_path,
            env=env,
            capture_output=True,
            text=True,
            timeout=runner.timeout_s,
        )
    except subprocess.TimeoutExpired as e:
        out = (
            e.stdout
            if isinstance(e.stdout, str)
            else (e.stdout.decode("utf-8") if e.stdout else "")
        )
        err = (
            e.stderr
            if isinstance(e.stderr, str)
            else (e.stderr.decode("utf-8") if e.stderr else "")
        )
        stdout_path.write_text(out, encoding="utf-8")
        stderr_path.write_text(err, encoding="utf-8")
        return GateExecutionResult(
            success=False,
            returncode=-1,
            error_message="timeout",
            log_paths={
                "stdout": str(stdout_path),
                "stderr": str(stderr_path),
                "runner.json": str(runner_json_path),
            },
        )
    except FileNotFoundError as e:
        stderr_path.write_text(str(e), encoding="utf-8")
        return GateExecutionResult(
            success=False,
            returncode=-1,
            error_message=f"command not found: {e}",
            log_paths={
                "stdout": str(stdout_path),
                "stderr": str(stderr_path),
                "runner.json": str(runner_json_path),
            },
        )

    stdout_path.write_text(result.stdout or "", encoding="utf-8")
    stderr_path.write_text(result.stderr or "", encoding="utf-8")

    return GateExecutionResult(
        success=result.returncode == 0,
        returncode=result.returncode,
        error_message=None
        if result.returncode == 0
        else (result.stderr or f"exit code {result.returncode}"),
        log_paths={
            "stdout": str(stdout_path),
            "stderr": str(stderr_path),
            "runner.json": str(runner_json_path),
        },
    )
