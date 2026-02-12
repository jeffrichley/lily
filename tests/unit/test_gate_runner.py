"""Layer 3: Local command gate runner."""

from pathlib import Path

from lily.kernel.gate_models import GateRunnerSpec, GateSpec
from lily.kernel.gate_runner import run_local_gate


def _gate_spec(
    gate_id: str = "g1",
    argv: list[str] | None = None,
    timeout_s: float | None = None,
) -> GateSpec:
    return GateSpec(
        gate_id=gate_id,
        name="Test gate",
        runner=GateRunnerSpec(
            kind="local_command",
            argv=argv or ["true"],
            timeout_s=timeout_s,
        ),
    )


def test_successful_command_passes(tmp_path: Path) -> None:
    """Successful command returns success=True and returncode=0."""
    run_root = tmp_path / "run"
    run_root.mkdir()
    (run_root / "logs").mkdir()

    result = run_local_gate(
        _gate_spec(argv=["python", "-c", "print(1)"]), run_root, attempt=1
    )

    assert result.success is True, "successful command should report success"
    assert result.returncode == 0, "successful command should have returncode 0"
    assert result.error_message is None, "success should have no error message"
    assert "stdout" in result.log_paths, "stdout log path should be present"
    assert "stderr" in result.log_paths, "stderr log path should be present"
    assert "runner.json" in result.log_paths, "runner.json log path should be present"


def test_failing_command_fails(tmp_path: Path) -> None:
    """Failing command returns success=False and non-zero returncode."""
    run_root = tmp_path / "run"
    run_root.mkdir()
    (run_root / "logs").mkdir()

    result = run_local_gate(
        _gate_spec(argv=["python", "-c", "import sys; sys.exit(3)"]),
        run_root,
        attempt=1,
    )

    assert result.success is False, "failing command should report failure"
    assert result.returncode == 3, "exit(3) should yield returncode 3"
    assert result.error_message is not None, "failure should have error message"


def test_timeout_fails(tmp_path: Path) -> None:
    """Timeout returns success=False and error_message='timeout'."""
    run_root = tmp_path / "run"
    run_root.mkdir()
    (run_root / "logs").mkdir()

    result = run_local_gate(
        _gate_spec(
            argv=["python", "-c", "import time; time.sleep(10)"],
            timeout_s=0.1,
        ),
        run_root,
        attempt=1,
    )

    assert result.success is False, "timeout should report failure"
    assert result.returncode == -1, "timeout should use returncode -1"
    assert result.error_message is not None, "timeout should set error message"
    assert "timeout" in result.error_message.lower(), (
        "error message should indicate timeout"
    )


def test_logs_created(tmp_path: Path) -> None:
    """Logs are written under .iris/runs/<run_id>/logs/gates/<gate_id>/<attempt>/."""
    run_root = tmp_path / "run"
    run_root.mkdir()
    (run_root / "logs").mkdir()

    result = run_local_gate(
        _gate_spec(gate_id="my-gate", argv=["python", "-c", "print('hi')"]),
        run_root,
        attempt=2,
    )

    assert result.success is True, "command should succeed for log path test"
    log_dir = run_root / "logs" / "gates" / "my-gate" / "2"
    assert log_dir.is_dir(), (
        "log dir should exist under run_root/logs/gates/<gate_id>/<attempt>"
    )
    assert (log_dir / "stdout.txt").read_text().strip() == "hi", (
        "stdout should contain command output"
    )
    assert (log_dir / "stderr.txt").exists(), "stderr file should exist"
    assert (log_dir / "runner.json").exists(), "runner.json should exist"
    assert "gate_id" in (log_dir / "runner.json").read_text(), (
        "runner.json should include gate_id"
    )
