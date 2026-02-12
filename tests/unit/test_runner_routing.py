"""Layer 4: Runner integration with RoutingEngine."""

from pathlib import Path

from lily.kernel import create_run, run_graph
from lily.kernel.gate_models import GateRunnerSpec, GateSpec
from lily.kernel.graph_models import ExecutorSpec, GraphSpec, RetryPolicy, StepSpec
from lily.kernel.routing_models import (
    RoutingAction,
    RoutingActionType,
    RoutingCondition,
    RoutingRule,
)
from lily.kernel.run_state import RunStatus, StepStatus


def _run_root(tmp_path: Path, name: str) -> Path:
    r = tmp_path / name
    r.mkdir(parents=True)
    (r / "logs").mkdir()
    (r / "artifacts").mkdir()
    (r / "tmp").mkdir()
    return r


def test_escalate_sets_run_blocked(tmp_path: Path):
    """Routing rule with escalate sets run status to blocked."""
    run_id, run_root = create_run(tmp_path)
    rules = [
        RoutingRule(
            rule_id="escalate_on_gate_fail",
            when=RoutingCondition(step_status="succeeded", gate_status="failed"),
            action=RoutingAction(type=RoutingActionType.ESCALATE, reason="gate failed"),
        ),
    ]
    gate = GateSpec(
        gate_id="fail",
        name="Fail",
        required=True,
        runner=GateRunnerSpec(
            kind="local_command",
            argv=["python", "-c", "import sys; sys.exit(1)"],
        ),
    )
    graph = GraphSpec(
        graph_id="g1",
        steps=[
            StepSpec(
                step_id="a",
                name="a",
                executor=ExecutorSpec(
                    kind="local_command",
                    argv=["python", "-c", "print(1)"],
                ),
                gates=[gate],
            ),
        ],
        routing_rules=rules,
    )
    state = run_graph(run_root, graph)
    assert state.status == RunStatus.BLOCKED, "escalate rule should set run to BLOCKED"
    assert "gate failed" in (state.escalation_reason or ""), (
        "escalation_reason should mention gate failed"
    )
    assert state.escalation_step_id == "a", (
        "escalation_step_id should be the step with failing gate"
    )


def test_abort_run_sets_run_failed(tmp_path: Path):
    """Routing rule with abort_run sets run status to failed."""
    run_id, run_root = create_run(tmp_path)
    rules = [
        RoutingRule(
            rule_id="abort_on_fail",
            when=RoutingCondition(step_status="failed"),
            action=RoutingAction(
                type=RoutingActionType.ABORT_RUN, reason="step failed"
            ),
        ),
    ]
    graph = GraphSpec(
        graph_id="g1",
        steps=[
            StepSpec(
                step_id="bad",
                name="bad",
                executor=ExecutorSpec(
                    kind="local_command",
                    argv=["python", "-c", "import sys; sys.exit(1)"],
                ),
                retry_policy=RetryPolicy(max_retries=0),
            ),
        ],
        routing_rules=rules,
    )
    state = run_graph(run_root, graph)
    assert state.status == RunStatus.FAILED, "abort_run rule should set run to FAILED"
    assert state.step_records["bad"].status == StepStatus.FAILED, (
        "failing step should be FAILED"
    )


def test_retry_rule_overrides_default(tmp_path: Path):
    """Routing rule with retry_step can override default abort when retries exhausted."""
    counter_file = tmp_path / "counter"
    counter_file.write_text("0")
    script_file = tmp_path / "retry_script.py"
    script_file.write_text(f"""
import sys
p = {str(counter_file)!r}
n = int(open(p).read())
open(p, "w").write(str(n + 1))
sys.exit(1 if n < 2 else 0)
""")
    run_id, run_root = create_run(tmp_path)
    rules = [
        RoutingRule(
            rule_id="retry_more",
            when=RoutingCondition(step_status="failed", retry_exhausted=True),
            action=RoutingAction(type=RoutingActionType.RETRY_STEP, reason="one more"),
        ),
    ]
    graph = GraphSpec(
        graph_id="g1",
        steps=[
            StepSpec(
                step_id="flaky",
                name="flaky",
                executor=ExecutorSpec(
                    kind="local_command",
                    argv=["python", str(script_file)],
                ),
                retry_policy=RetryPolicy(max_retries=1),
            ),
        ],
        routing_rules=rules,
    )
    state = run_graph(run_root, graph)
    assert state.status == RunStatus.SUCCEEDED, (
        "retry rule should allow run to succeed after retries"
    )
    assert state.step_records["flaky"].status == StepStatus.SUCCEEDED, (
        "flaky step should succeed after retry"
    )


def test_goto_step_changes_execution_order(tmp_path: Path):
    """Routing rule with goto_step redirects to target step."""
    run_id, run_root = create_run(tmp_path)
    rules = [
        RoutingRule(
            rule_id="goto_c_on_a_fail",
            when=RoutingCondition(step_status="failed", step_id="a"),
            action=RoutingAction(
                type=RoutingActionType.GOTO_STEP,
                target_step_id="c",
                reason="skip b",
            ),
        ),
    ]
    graph = GraphSpec(
        graph_id="g1",
        steps=[
            StepSpec(
                step_id="a",
                name="a",
                executor=ExecutorSpec(
                    kind="local_command",
                    argv=["python", "-c", "import sys; sys.exit(1)"],
                ),
                retry_policy=RetryPolicy(max_retries=0),
            ),
            StepSpec(
                step_id="b",
                name="b",
                depends_on=["a"],
                executor=ExecutorSpec(
                    kind="local_command",
                    argv=["python", "-c", "print('b')"],
                ),
            ),
            StepSpec(
                step_id="c",
                name="c",
                depends_on=[],  # no deps so it's eligible when we goto
                executor=ExecutorSpec(
                    kind="local_command",
                    argv=["python", "-c", "print('c')"],
                ),
            ),
        ],
        routing_rules=rules,
    )
    state = run_graph(run_root, graph)
    # goto_step from a (failed) to c: c runs and succeeds
    assert state.step_records["a"].status == StepStatus.FAILED, (
        "step a should remain failed"
    )
    assert state.step_records["b"].status == StepStatus.PENDING, (
        "step b should be skipped (PENDING)"
    )
    assert state.step_records["c"].status == StepStatus.SUCCEEDED, (
        "goto_step target c should run and succeed"
    )
