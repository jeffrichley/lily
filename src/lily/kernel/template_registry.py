"""Layer 6: Template registry. StepTemplate -> StepSpec, GateTemplate -> GateSpec."""

from __future__ import annotations

from dataclasses import dataclass

from lily.kernel.gate_models import GateSpec
from lily.kernel.graph_models import StepSpec
from lily.kernel.pack_models import GateTemplate, StepTemplate


@dataclass(frozen=True)
class ExpandStepOptions:
    """Optional overrides when expanding a step template."""

    description: str | None = None
    depends_on: list[str] | None = None
    input_artifact_ids: list[str] | None = None


@dataclass(frozen=True)
class ExpandGateOptions:
    """Optional overrides when expanding a gate template."""

    description: str | None = None
    inputs: list[str] | None = None
    workspace_required: bool = False


class TemplateRegistry:
    """Step and gate templates by template_id. Prevents ID collisions."""

    def __init__(self) -> None:
        """Initialize empty template registries."""
        self._step_templates: dict[str, StepTemplate] = {}
        self._gate_templates: dict[str, GateTemplate] = {}

    def register_step_template(self, template: StepTemplate) -> None:
        """Register step template. Raises if template_id already registered.

        Args:
            template: Step template to register.

        Raises:
            ValueError: If template_id is already registered.
        """
        tid = template.template_id
        if tid in self._step_templates:
            raise ValueError(f"Step template_id already registered: {tid!r}")
        self._step_templates[tid] = template

    def register_gate_template(self, template: GateTemplate) -> None:
        """Register gate template. Raises if template_id already registered.

        Args:
            template: Gate template to register.

        Raises:
            ValueError: If template_id is already registered.
        """
        tid = template.template_id
        if tid in self._gate_templates:
            raise ValueError(f"Gate template_id already registered: {tid!r}")
        self._gate_templates[tid] = template

    def get_step_template(self, template_id: str) -> StepTemplate:
        """Return the step template for template_id. Raises KeyError if not found.

        Args:
            template_id: Template identifier.

        Returns:
            The registered StepTemplate.

        Raises:
            KeyError: If template_id is not registered.
        """
        if template_id not in self._step_templates:
            raise KeyError(f"Unknown step template_id: {template_id!r}")
        return self._step_templates[template_id]

    def get_gate_template(self, template_id: str) -> GateTemplate:
        """Return the gate template for template_id. Raises KeyError if not found.

        Args:
            template_id: Template identifier.

        Returns:
            The registered GateTemplate.

        Raises:
            KeyError: If template_id is not registered.
        """
        if template_id not in self._gate_templates:
            raise KeyError(f"Unknown gate template_id: {template_id!r}")
        return self._gate_templates[template_id]

    def expand_step_template(
        self,
        template_id: str,
        step_id: str,
        name: str,
        *,
        options: ExpandStepOptions | None = None,
    ) -> StepSpec:
        """Expand a step template into a StepSpec. Kernel executes only StepSpec.

        Args:
            template_id: Template to expand.
            step_id: Step identifier for the expanded spec.
            name: Step name.
            options: Optional overrides for description, depends_on, input_artifact_ids.

        Returns:
            StepSpec ready for execution.
        """
        opts = options or ExpandStepOptions()
        template = self.get_step_template(template_id)
        return StepSpec(
            step_id=step_id,
            name=name,
            description=opts.description or template.template_id,
            depends_on=opts.depends_on if opts.depends_on is not None else [],
            input_artifact_ids=(
                opts.input_artifact_ids if opts.input_artifact_ids is not None else []
            ),
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
        options: ExpandGateOptions | None = None,
    ) -> GateSpec:
        """Expand a gate template into a GateSpec. Kernel runs only GateSpec.

        Args:
            template_id: Template to expand.
            gate_id: Gate identifier for the expanded spec.
            name: Gate name.
            options: Optional overrides for description, inputs, workspace_required.

        Returns:
            GateSpec ready for execution.
        """
        opts = options or ExpandGateOptions()
        template = self.get_gate_template(template_id)
        return GateSpec(
            gate_id=gate_id,
            name=name,
            description=opts.description,
            inputs=opts.inputs if opts.inputs is not None else [],
            workspace_required=opts.workspace_required,
            runner=template.runner_spec,
            required=template.required,
        )
