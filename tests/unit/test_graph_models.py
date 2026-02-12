"""Layer 2: GraphSpec and StepSpec validation."""

import pytest

from lily.kernel.graph_models import (
    ExecutorSpec,
    GraphSpec,
    StepSpec,
    validate_graph_spec,
)


def _make_step(step_id: str, depends_on: list[str] | None = None) -> StepSpec:
    return StepSpec(
        step_id=step_id,
        name=step_id,
        depends_on=depends_on or [],
        executor=ExecutorSpec(kind="local_command", argv=["echo", "ok"]),
    )


def test_unique_step_ids_enforced():
    """Duplicate step_ids must fail validation."""
    with pytest.raises(ValueError, match="unique"):
        GraphSpec(
            graph_id="g1",
            steps=[
                _make_step("a"),
                _make_step("a"),
            ],
        )


def test_missing_dependency_step_id_fails():
    """depends_on must reference existing step_ids."""
    with pytest.raises(ValueError, match="missing step_id|depends_on"):
        GraphSpec(
            graph_id="g1",
            steps=[
                _make_step("a", depends_on=["nonexistent"]),
            ],
        )


def test_cycle_detected():
    """Simple 2-3 node cycle must be detected."""
    with pytest.raises(ValueError, match="Cycle detected"):
        GraphSpec(
            graph_id="g1",
            steps=[
                _make_step("a", depends_on=["c"]),
                _make_step("b", depends_on=["a"]),
                _make_step("c", depends_on=["b"]),
            ],
        )


def test_cycle_detected_two_node():
    """Two-node cycle a -> b -> a."""
    with pytest.raises(ValueError, match="Cycle detected"):
        GraphSpec(
            graph_id="g1",
            steps=[
                _make_step("a", depends_on=["b"]),
                _make_step("b", depends_on=["a"]),
            ],
        )


def test_valid_dag_passes():
    """Valid DAG with no cycles passes validation."""
    g = GraphSpec(
        graph_id="g1",
        steps=[
            _make_step("a"),
            _make_step("b", depends_on=["a"]),
            _make_step("c", depends_on=["a"]),
            _make_step("d", depends_on=["b", "c"]),
        ],
    )
    assert g.graph_id == "g1"
    assert len(g.steps) == 4


def test_empty_steps_fails():
    """Graph must have at least one step."""
    with pytest.raises(ValueError, match="at least one step"):
        GraphSpec(graph_id="g1", steps=[])


def test_graph_spec_from_dict():
    """GraphSpec can be constructed from dict and validated."""
    d = {
        "graph_id": "g1",
        "steps": [
            {
                "step_id": "a",
                "name": "step_a",
                "depends_on": [],
                "executor": {"kind": "local_command", "argv": ["echo", "x"]},
            },
        ],
    }
    g = GraphSpec.model_validate(d)
    assert g.graph_id == "g1"
    assert g.steps[0].step_id == "a"
    assert g.steps[0].executor.argv == ["echo", "x"]


def test_validate_graph_spec_standalone():
    """validate_graph_spec can be called standalone on already-built spec."""
    g = GraphSpec.model_construct(
        graph_id="g1",
        steps=[_make_step("a")],
    )
    validate_graph_spec(g)
