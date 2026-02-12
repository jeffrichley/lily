"""Layer 2: Local command executor."""

from pathlib import Path


from lily.kernel.graph_models import ExecutorSpec
from lily.kernel.executors.local_command import run_local_command


def test_successful_command_produces_stdout_log(tmp_path: Path):
    """Successful command produces stdout log in correct path."""
    spec = ExecutorSpec(
        kind="local_command", argv=["python", "-c", "print('hello world')"]
    )
    result = run_local_command(spec, run_root=tmp_path, step_id="s1", attempt=0)
    assert result.success
    assert result.returncode == 0
    assert "stdout" in result.log_paths
    stdout_path = Path(result.log_paths["stdout"])
    assert stdout_path.exists()
    assert "hello world" in stdout_path.read_text()


def test_failing_command_produces_stderr_returncode(tmp_path: Path):
    """Failing command produces stderr and returncode."""
    spec = ExecutorSpec(
        kind="local_command",
        argv=["python", "-c", "import sys; sys.stderr.write('oops'); sys.exit(1)"],
    )
    result = run_local_command(spec, run_root=tmp_path, step_id="s1", attempt=0)
    assert not result.success
    assert result.returncode == 1
    assert result.error_message
    assert "stderr" in result.log_paths
    stderr_path = Path(result.log_paths["stderr"])
    assert stderr_path.exists()
    assert "oops" in stderr_path.read_text()


def test_timeout_produces_failure(tmp_path: Path):
    """Timeout produces failure with timeout reason."""
    spec = ExecutorSpec(
        kind="local_command", argv=["python", "-c", "import time; time.sleep(10)"]
    )
    result = run_local_command(
        spec, run_root=tmp_path, step_id="s1", attempt=0, timeout_s=0.1
    )
    assert not result.success
    assert result.error_message == "timeout"
    assert "stdout" in result.log_paths


def test_logs_in_correct_paths(tmp_path: Path):
    """Logs are created at .iris/runs/<run_id>/logs/steps/<step_id>/<attempt>/."""
    spec = ExecutorSpec(kind="local_command", argv=["python", "-c", "print('x')"])
    result = run_local_command(spec, run_root=tmp_path, step_id="my_step", attempt=2)
    assert result.success
    stdout_path = Path(result.log_paths["stdout"])
    assert "logs" in str(stdout_path)
    assert "steps" in str(stdout_path)
    assert "my_step" in str(stdout_path)
    assert "2" in str(stdout_path)
    assert (tmp_path / "logs" / "steps" / "my_step" / "2" / "stdout.txt").exists()
    assert (tmp_path / "logs" / "steps" / "my_step" / "2" / "executor.json").exists()


def test_unsupported_executor_kind(tmp_path: Path):
    """Unsupported executor kind returns error without running."""
    spec = ExecutorSpec(kind="python_callable")
    result = run_local_command(spec, run_root=tmp_path, step_id="s1", attempt=0)
    assert not result.success
    assert "Unsupported" in (result.error_message or "")
