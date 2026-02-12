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


def test_successful_command_passes(tmp_path: Path):
    """Successful command returns success=True and returncode=0."""
    run_root = tmp_path / "run"
    run_root.mkdir()
    (run_root / "logs").mkdir()

    result = run_local_gate(
        _gate_spec(argv=["python", "-c", "print(1)"]), run_root, attempt=1
    )

    assert result.success is True
    assert result.returncode == 0
    assert result.error_message is None
    assert "stdout" in result.log_paths
    assert "stderr" in result.log_paths
    assert "runner.json" in result.log_paths


def test_failing_command_fails(tmp_path: Path):
    """Failing command returns success=False and non-zero returncode."""
    run_root = tmp_path / "run"
    run_root.mkdir()
    (run_root / "logs").mkdir()

    result = run_local_gate(
        _gate_spec(argv=["python", "-c", "import sys; sys.exit(3)"]),
        run_root,
        attempt=1,
    )

    assert result.success is False
    assert result.returncode == 3
    assert result.error_message is not None


def test_timeout_fails(tmp_path: Path):
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

    assert result.success is False
    assert result.returncode == -1
    assert result.error_message == "timeout"


def test_logs_created(tmp_path: Path):
    """Logs are written under .iris/runs/<run_id>/logs/gates/<gate_id>/<attempt>/."""
    run_root = tmp_path / "run"
    run_root.mkdir()
    (run_root / "logs").mkdir()

    result = run_local_gate(
        _gate_spec(gate_id="my-gate", argv=["python", "-c", "print('hi')"]),
        run_root,
        attempt=2,
    )

    assert result.success is True
    log_dir = run_root / "logs" / "gates" / "my-gate" / "2"
    assert log_dir.is_dir()
    assert (log_dir / "stdout.txt").read_text().strip() == "hi"
    assert (log_dir / "stderr.txt").exists()
    assert (log_dir / "runner.json").exists()
    assert "gate_id" in (log_dir / "runner.json").read_text()
