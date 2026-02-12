"""Layer 6: Template registry and expansion. StepTemplate -> StepSpec, GateTemplate -> GateSpec."""

from __future__ import annotations

from lily.kernel.gate_models import GateSpec
from lily.kernel.graph_models import StepSpec
from lily.kernel.pack_models import GateTemplate, StepTemplate


class TemplateRegistry:
    """Stores step and gate templates by fully-qualified template_id. Prevents ID collisions."""

    def __init__(self) -> None:
        self._step_templates: dict[str, StepTemplate] = {}
        self._gate_templates: dict[str, GateTemplate] = {}

    def register_step_template(self, template: StepTemplate) -> None:
        """Register a step template. Raises ValueError if template_id already registered."""
        tid = template.template_id
        if tid in self._step_templates:
            raise ValueError(f"Step template_id already registered: {tid!r}")
        self._step_templates[tid] = template

    def register_gate_template(self, template: GateTemplate) -> None:
        """Register a gate template. Raises ValueError if template_id already registered."""
        tid = template.template_id
        if tid in self._gate_templates:
            raise ValueError(f"Gate template_id already registered: {tid!r}")
        self._gate_templates[tid] = template

    def get_step_template(self, template_id: str) -> StepTemplate:
        """Return the step template for template_id. Raises KeyError if not found."""
        if template_id not in self._step_templates:
            raise KeyError(f"Unknown step template_id: {template_id!r}")
        return self._step_templates[template_id]

    def get_gate_template(self, template_id: str) -> GateTemplate:
        """Return the gate template for template_id. Raises KeyError if not found."""
        if template_id not in self._gate_templates:
            raise KeyError(f"Unknown gate template_id: {template_id!r}")
        return self._gate_templates[template_id]

    def expand_step_template(
        self,
        template_id: str,
        step_id: str,
        name: str,
        *,
        description: str | None = None,
        depends_on: list[str] | None = None,
        input_artifact_ids: list[str] | None = None,
    ) -> StepSpec:
        """Expand a step template into a StepSpec. Kernel executes only StepSpec."""
        template = self.get_step_template(template_id)
        return StepSpec(
            step_id=step_id,
            name=name,
            description=description or template.template_id,
            depends_on=depends_on if depends_on is not None else [],
            input_artifact_ids=input_artifact_ids if input_artifact_ids is not None else [],
            output_schema_ids=template.output_schema_ids,
            executor=template.default_executor,
            retry_policy=template.default_retry_policy,
            timeout_policy=template.default_timeout_policy,
            gates=template.default_gates,
        )

    def expand_gate_template(
        self,
        template_id: str,
        gate_id: str,
        name: str,
        *,
        description: str | None = None,
        inputs: list[str] | None = None,
        workspace_required: bool = False,
    ) -> GateSpec:
        """Expand a gate template into a GateSpec. Kernel runs only GateSpec."""
        template = self.get_gate_template(template_id)
        return GateSpec(
            gate_id=gate_id,
            name=name,
            description=description,
            inputs=inputs if inputs is not None else [],
            workspace_required=workspace_required,
            runner=template.runner_spec,
            required=template.required,
        )
