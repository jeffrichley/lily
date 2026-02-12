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
    assert result.success, "successful command should report success"
    assert result.returncode == 0, "successful command should have returncode 0"
    assert "stdout" in result.log_paths, "stdout log path should be present"
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
    assert not result.success, "failing command should report failure"
    assert result.returncode == 1, "exit(1) should yield returncode 1"
    assert result.error_message, "failure should have error message"
    assert "stderr" in result.log_paths, "stderr log path should be present"
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
    assert not result.success, "timeout should report failure"
    assert result.error_message is not None, "timeout should set error message"
    assert "timeout" in result.error_message.lower(), (
        "error message should indicate timeout"
    )
    assert "stdout" in result.log_paths, "stdout log path present even on timeout"


def test_logs_in_correct_paths(tmp_path: Path):
    """Logs are created at run_root/logs/steps/<step_id>/<attempt>/."""
    spec = ExecutorSpec(kind="local_command", argv=["python", "-c", "print('x')"])
    result = run_local_command(spec, run_root=tmp_path, step_id="my_step", attempt=2)
    assert result.success, "command should succeed for path test"
    stdout_path = Path(result.log_paths["stdout"])
    expected_log_dir = tmp_path / "logs" / "steps" / "my_step" / "2"
    assert stdout_path.resolve() == (expected_log_dir / "stdout.txt").resolve(), (
        "stdout path under logs/steps/<step_id>/<attempt>"
    )
    assert (expected_log_dir / "stdout.txt").exists(), "stdout.txt file should exist"
    assert (expected_log_dir / "executor.json").exists(), "executor.json should exist"


def test_unsupported_executor_kind(tmp_path: Path):
    """Unsupported executor kind returns error without running."""
    spec = ExecutorSpec(kind="python_callable")
    result = run_local_command(spec, run_root=tmp_path, step_id="s1", attempt=0)
    assert not result.success, "unsupported executor kind should report failure"
    assert "Unsupported" in (result.error_message or ""), (
        "error message should mention unsupported"
    )
