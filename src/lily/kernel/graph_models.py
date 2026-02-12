"""Layer 2: Graph and Step spec models. Kernel-pure, domain-neutral."""

from __future__ import annotations


from pydantic import BaseModel, Field, model_validator


class RetryPolicy(BaseModel):
    """Retry policy for a step. Kernel uses for counting and timing only."""

    max_retries: int = 0
    backoff_s: float | None = None
    retry_on: list[str] | None = None  # optional; "any" vs "none" for now


class TimeoutPolicy(BaseModel):
    """Timeout policy. If timeout triggers, step marked failed with reason timeout."""

    timeout_s: float | None = None


class ExecutorSpec(BaseModel):
    """Local command executor. Layer 2 supports local_command only initially."""

    kind: str = "local_command"
    argv: list[str] = Field(default_factory=list)
    cwd: str | None = None
    env: dict[str, str] | None = None


class StepSpec(BaseModel):
    """Smallest schedulable unit. Kernel does not interpret domain meaning."""

    step_id: str
    name: str
    description: str | None = None
    depends_on: list[str] = Field(default_factory=list)
    input_artifact_ids: list[str] = Field(default_factory=list)
    output_schema_ids: list[str] = Field(default_factory=list)
    executor: ExecutorSpec
    retry_policy: RetryPolicy = Field(default_factory=RetryPolicy)
    timeout_policy: TimeoutPolicy = Field(default_factory=TimeoutPolicy)


class GraphSpec(BaseModel):
    """DAG of steps. Validation: unique ids, deps exist, no cycles, at least one step."""

    graph_id: str
    steps: list[StepSpec] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_graph(self) -> "GraphSpec":
        validate_graph_spec(self)
        return self


def topological_order(graph: GraphSpec) -> list[str]:
    """Return step_ids in topological order (deps first). Ties broken by step_id sort."""
    step_by_id = {s.step_id: s for s in graph.steps}
    result: list[str] = []
    visited: set[str] = set()

    def visit(sid: str) -> None:
        if sid in visited:
            return
        visited.add(sid)
        for dep in sorted(step_by_id[sid].depends_on):
            visit(dep)
        result.append(sid)

    for sid in sorted(step_by_id):
        visit(sid)
    return result


def validate_graph_spec(graph: GraphSpec) -> None:
    """
    Validate GraphSpec. Raises ValueError on failure.
    - step_ids unique
    - all depends_on references exist
    - at least one step
    - no cycles
    """
    if not graph.steps:
        raise ValueError("Graph must have at least one step")

    step_ids = {s.step_id for s in graph.steps}
    if len(step_ids) != len(graph.steps):
        raise ValueError("step_ids must be unique within the graph")

    for s in graph.steps:
        for dep in s.depends_on:
            if dep not in step_ids:
                raise ValueError(f"depends_on references missing step_id: {dep!r}")

    _detect_cycle(graph)


def _detect_cycle(graph: GraphSpec) -> None:
    """Raise ValueError if graph contains a cycle."""
    step_ids = {s.step_id for s in graph.steps}
    step_by_id = {s.step_id: s for s in graph.steps}
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {sid: WHITE for sid in step_ids}

    def visit(sid: str, path: list[str]) -> None:
        if color[sid] == GRAY:
            idx = path.index(sid)
            cycle = path[idx:] + [sid]
            raise ValueError(f"Cycle detected: {' -> '.join(cycle)}")
        if color[sid] == BLACK:
            return
        color[sid] = GRAY
        step = step_by_id[sid]
        for dep in step.depends_on:
            visit(dep, path + [sid])
        color[sid] = BLACK

    for sid in step_ids:
        if color[sid] == WHITE:
            visit(sid, [])
