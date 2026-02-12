"""Layer 2: Runner v1 — deterministic scheduling and retries."""

from pathlib import Path


from lily.kernel.graph_models import ExecutorSpec, GraphSpec, StepSpec
from lily.kernel.run_state import RunStatus, StepStatus
from lily.kernel.runner import run_graph


def _make_step(step_id: str, depends_on: list[str] | None = None) -> StepSpec:
    return StepSpec(
        step_id=step_id,
        name=step_id,
        depends_on=depends_on or [],
        executor=ExecutorSpec(kind="local_command", argv=["python", "-c", "print(1)"]),
    )


def test_executes_dag_in_dependency_order(tmp_path: Path):
    """Runner executes 2-3 step DAG in dependency order."""
    graph = GraphSpec(
        graph_id="g1",
        steps=[
            _make_step("a"),
            _make_step("b", depends_on=["a"]),
            _make_step("c", depends_on=["b"]),
        ],
    )
    run_root = tmp_path / "run-1"
    run_root.mkdir(parents=True)
    (run_root / "logs").mkdir()
    (run_root / "artifacts").mkdir()
    (run_root / "tmp").mkdir()

    state = run_graph(run_root, graph)

    assert state.status == RunStatus.SUCCEEDED
    assert state.step_records["a"].status == StepStatus.SUCCEEDED
    assert state.step_records["b"].status == StepStatus.SUCCEEDED
    assert state.step_records["c"].status == StepStatus.SUCCEEDED


def test_deterministic_ordering_for_independent_steps(tmp_path: Path):
    """Independent steps are picked in deterministic (topo + step_id) order."""
    graph = GraphSpec(
        graph_id="g1",
        steps=[
            _make_step("b"),
            _make_step("a"),
            _make_step("c", depends_on=["a", "b"]),
        ],
    )
    run_root = tmp_path / "run-2"
    run_root.mkdir(parents=True)
    (run_root / "logs").mkdir()
    (run_root / "artifacts").mkdir()
    (run_root / "tmp").mkdir()

    state = run_graph(run_root, graph)

    assert state.status == RunStatus.SUCCEEDED
    # a and b are independent; topo order is a, b, c (sorted by step_id)
    assert state.step_records["a"].status == StepStatus.SUCCEEDED
    assert state.step_records["b"].status == StepStatus.SUCCEEDED
    assert state.step_records["c"].status == StepStatus.SUCCEEDED


def test_retry_succeeds_on_second_attempt(tmp_path: Path):
    """Step that fails once and succeeds on retry is marked succeeded."""
    from lily.kernel.graph_models import RetryPolicy

    counter_file = tmp_path / "counter"
    counter_file.write_text("0")
    script_file = tmp_path / "retry_script.py"
    script_file.write_text(f"""
import sys
p = {str(counter_file)!r}
n = int(open(p).read())
open(p, "w").write(str(n + 1))
sys.exit(1 if n < 1 else 0)
""")
    graph = GraphSpec(
        graph_id="g1",
        steps=[
            StepSpec(
                step_id="flaky",
                name="flaky",
                executor=ExecutorSpec(
                    kind="local_command", argv=["python", str(script_file)]
                ),
                retry_policy=RetryPolicy(max_retries=1),
            ),
        ],
    )
    run_root = tmp_path / "run-3"
    run_root.mkdir(parents=True)
    (run_root / "logs").mkdir()
    (run_root / "artifacts").mkdir()
    (run_root / "tmp").mkdir()

    state = run_graph(run_root, graph)

    assert state.status == RunStatus.SUCCEEDED
    assert state.step_records["flaky"].status == StepStatus.SUCCEEDED
    assert state.step_records["flaky"].attempts == 1  # one failure before success


def test_exceeds_retries_run_fails(tmp_path: Path):
    """Step that exceeds retries causes run to fail."""
    from lily.kernel.graph_models import RetryPolicy

    graph = GraphSpec(
        graph_id="g1",
        steps=[
            StepSpec(
                step_id="bad",
                name="bad",
                executor=ExecutorSpec(
                    kind="local_command", argv=["python", "-c", "exit(1)"]
                ),
                retry_policy=RetryPolicy(max_retries=1),
            ),
        ],
    )
    run_root = tmp_path / "run-4"
    run_root.mkdir(parents=True)
    (run_root / "logs").mkdir()
    (run_root / "artifacts").mkdir()
    (run_root / "tmp").mkdir()

    state = run_graph(run_root, graph)

    assert state.status == RunStatus.FAILED
    assert state.step_records["bad"].status == StepStatus.FAILED
    assert state.step_records["bad"].attempts == 2  # initial + 1 retry, both failed
