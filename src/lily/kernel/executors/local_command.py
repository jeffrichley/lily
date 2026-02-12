"""Layer 2: Local command executor."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

from lily.kernel.canonical import JSONReadOnly
from lily.kernel.graph_models import ExecutorSpec
from lily.kernel.paths import LOGS_DIR
from lily.kernel.run_cmd import (
    CompletedProcess,
    TimeoutExpired,
    minimal_env,
    run_subprocess,
)


def _decode_io(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return value.decode("utf-8")


class _ExecPaths:
    """Paths for a single step execution (logs and executor.json)."""

    def __init__(
        self,
        stdout_path: Path,
        stderr_path: Path,
        executor_json_path: Path,
    ) -> None:
        self.stdout_path = stdout_path
        self.stderr_path = stderr_path
        self.executor_json_path = executor_json_path


def _exec_log_paths(paths: _ExecPaths) -> dict[str, str]:
    return {
        "stdout": str(paths.stdout_path),
        "stderr": str(paths.stderr_path),
        "executor.json": str(paths.executor_json_path),
    }


def _invoke_exec_subprocess(
    executor_spec: ExecutorSpec,
    run_root: Path,
    paths: _ExecPaths,
    summary: dict[str, JSONReadOnly],
    timeout_s: float | None,
) -> ExecResult | CompletedProcess[str]:
    """Run subprocess; return failure ExecResult or CompletedProcess on success.

    Args:
        executor_spec: Command and env/cwd to run.
        run_root: Run directory root for resolving relative cwd.
        paths: Log paths for stdout, stderr, executor.json.
        summary: JSON summary written to executor.json.
        timeout_s: Optional timeout in seconds.

    Returns:
        ExecResult on timeout or command-not-found; CompletedProcess on success.
    """
    paths.executor_json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    env = minimal_env()
    if executor_spec.env is not None:
        env.update(executor_spec.env)
    cwd_path: Path | None = None
    if executor_spec.cwd is not None:
        cwd_path = Path(executor_spec.cwd)
        if not cwd_path.is_absolute():
            cwd_path = run_root / cwd_path
    try:
        result = run_subprocess(
            executor_spec.argv,
            cwd=cwd_path,
            env=env,
            timeout=timeout_s,
        )
        return result
    except TimeoutExpired as e:
        paths.stdout_path.write_text(_decode_io(e.stdout), encoding="utf-8")
        paths.stderr_path.write_text(_decode_io(e.stderr), encoding="utf-8")
        return ExecResult(
            success=False,
            returncode=-1,
            error_message="timeout",
            log_paths=_exec_log_paths(paths),
        )
    except FileNotFoundError as e:
        paths.stderr_path.write_text(str(e), encoding="utf-8")
        return ExecResult(
            success=False,
            returncode=-1,
            error_message=f"command not found: {e}",
            log_paths=_exec_log_paths(paths),
        )


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
    """Execute a local command, capturing stdout/stderr to run logs.

    Logs at: .iris/runs/<run_id>/logs/steps/<step_id>/<attempt>/.

    Args:
        executor_spec: Command and env/cwd to run.
        run_root: Run directory root.
        step_id: Step identifier for log paths.
        attempt: Attempt number for log paths.
        timeout_s: Optional timeout in seconds.

    Returns:
        ExecResult with success, returncode, error_message, log_paths.
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
    paths = _ExecPaths(
        stdout_path=log_dir / "stdout.txt",
        stderr_path=log_dir / "stderr.txt",
        executor_json_path=log_dir / "executor.json",
    )
    summary: dict[str, JSONReadOnly] = {
        "argv": executor_spec.argv,
        "cwd": executor_spec.cwd,
        "timeout_s": timeout_s,
    }
    if executor_spec.env:
        summary["env"] = executor_spec.env

    out = _invoke_exec_subprocess(executor_spec, run_root, paths, summary, timeout_s)
    if isinstance(out, ExecResult):
        return out
    result = out
    paths.stdout_path.write_text(result.stdout or "", encoding="utf-8")
    paths.stderr_path.write_text(result.stderr or "", encoding="utf-8")
    return ExecResult(
        success=result.returncode == 0,
        returncode=result.returncode,
        error_message=None
        if result.returncode == 0
        else (result.stderr or f"exit code {result.returncode}"),
        log_paths=_exec_log_paths(paths),
    )
