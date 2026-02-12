"""Layer 3: Local command gate runner. Executes gate commands and captures logs."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

from lily.kernel.canonical import JSONReadOnly
from lily.kernel.gate_models import GateRunnerSpec, GateSpec
from lily.kernel.paths import LOGS_DIR
from lily.kernel.run_cmd import (
    CompletedProcess,
    TimeoutExpired,
    minimal_env,
    run_subprocess,
)


class _GateRunPaths:
    """Paths for a single gate run (logs and runner.json)."""

    def __init__(
        self,
        log_dir: Path,
        stdout_path: Path,
        stderr_path: Path,
        runner_json_path: Path,
    ) -> None:
        self.log_dir = log_dir
        self.stdout_path = stdout_path
        self.stderr_path = stderr_path
        self.runner_json_path = runner_json_path


class GateExecutionResult(BaseModel):
    """Result of a single gate execution (no envelope yet)."""

    success: bool
    returncode: int
    error_message: str | None = None
    log_paths: dict[str, str] = Field(default_factory=dict)


def _decode_io(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return value.decode("utf-8")


def _gate_failure_log_paths(paths: _GateRunPaths) -> dict[str, str]:
    return {
        "stdout": str(paths.stdout_path),
        "stderr": str(paths.stderr_path),
        "runner.json": str(paths.runner_json_path),
    }


def _invoke_gate_subprocess(
    runner: GateRunnerSpec,
    run_root: Path,
    paths: _GateRunPaths,
    summary: dict[str, JSONReadOnly],
) -> GateExecutionResult | CompletedProcess[str]:
    """Run subprocess; return failure result or CompletedProcess on success.

    Args:
        runner: Gate runner spec (argv, cwd, env, timeout).
        run_root: Run directory (for relative cwd).
        paths: Log paths for stdout/stderr/runner.json.
        summary: Summary dict to write to runner.json.

    Returns:
        GateExecutionResult on failure (timeout, not found, etc.),
        CompletedProcess on successful run.
    """
    paths.runner_json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    env = minimal_env()
    if runner.env is not None:
        env.update(runner.env)
    cwd_path: Path | None = None
    if runner.cwd is not None:
        cwd_path = Path(runner.cwd)
        if not cwd_path.is_absolute():
            cwd_path = run_root / cwd_path
    try:
        result = run_subprocess(
            runner.argv,
            cwd=cwd_path,
            env=env,
            timeout=runner.timeout_s,
        )
        return result
    except TimeoutExpired as e:
        paths.stdout_path.write_text(_decode_io(e.stdout), encoding="utf-8")
        paths.stderr_path.write_text(_decode_io(e.stderr), encoding="utf-8")
        return GateExecutionResult(
            success=False,
            returncode=-1,
            error_message="timeout",
            log_paths=_gate_failure_log_paths(paths),
        )
    except FileNotFoundError as e:
        paths.stderr_path.write_text(str(e), encoding="utf-8")
        return GateExecutionResult(
            success=False,
            returncode=-1,
            error_message=f"command not found: {e}",
            log_paths=_gate_failure_log_paths(paths),
        )


def run_local_gate(
    gate_spec: GateSpec,
    run_root: Path,
    attempt: int = 1,
) -> GateExecutionResult:
    """Execute a gate as a local command; capture stdout/stderr to run logs.

    Logs at: .iris/runs/<run_id>/logs/gates/<gate_id>/<attempt>/.

    Args:
        gate_spec: Gate spec (gate_id, runner with argv, etc.).
        run_root: Run directory.
        attempt: Attempt number (1-based).

    Returns:
        GateExecutionResult with success, returncode, logs.
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
    paths = _GateRunPaths(
        log_dir=log_dir,
        stdout_path=log_dir / "stdout.txt",
        stderr_path=log_dir / "stderr.txt",
        runner_json_path=log_dir / "runner.json",
    )
    summary: dict[str, JSONReadOnly] = {
        "gate_id": gate_spec.gate_id,
        "argv": runner.argv,
        "cwd": runner.cwd,
        "timeout_s": runner.timeout_s,
    }
    if runner.env:
        summary["env"] = runner.env

    out = _invoke_gate_subprocess(runner, run_root, paths, summary)
    if isinstance(out, GateExecutionResult):
        return out
    result = out
    paths.stdout_path.write_text(result.stdout or "", encoding="utf-8")
    paths.stderr_path.write_text(result.stderr or "", encoding="utf-8")
    return GateExecutionResult(
        success=result.returncode == 0,
        returncode=result.returncode,
        error_message=None
        if result.returncode == 0
        else (result.stderr or f"exit code {result.returncode}"),
        log_paths=_gate_failure_log_paths(paths),
    )
