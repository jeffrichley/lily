"""Layer 6: Register pack contributions (schemas, etc.) into kernel registries."""

from __future__ import annotations

from lily.kernel.pack_models import PackDefinition
from lily.kernel.policy_models import SafetyPolicy
from lily.kernel.routing_models import RoutingRule
from lily.kernel.schema_registry import SchemaRegistry
from lily.kernel.template_registry import TemplateRegistry


def register_pack_schemas(
    registry: SchemaRegistry, packs: list[PackDefinition]
) -> None:
    """Register all pack schemas into the registry.

    No override; kernel schemas cannot be overridden. Fails on duplicate schema_id.

    Args:
        registry: Schema registry to register on.
        packs: List of pack definitions.

    Raises:
        ValueError: On duplicate schema_id across packs.
    """
    seen_from_packs: dict[str, str] = {}  # schema_id -> pack name (for error message)
    for pack in packs:
        for reg in pack.schemas:
            if reg.schema_id in seen_from_packs:
                raise ValueError(
                    f"Duplicate schema_id {reg.schema_id!r} from pack {pack.name!r}; "
                    f"already registered by pack {seen_from_packs[reg.schema_id]!r}"
                )
            registry.register(reg.schema_id, reg.model, override=False)
            seen_from_packs[reg.schema_id] = pack.name


def register_pack_templates(
    registry: TemplateRegistry, packs: list[PackDefinition]
) -> None:
    """Register all pack step and gate templates. Fails on template_id collision.

    Args:
        registry: Template registry to register on.
        packs: List of pack definitions.
    """
    for pack in packs:
        for st in pack.step_templates:
            registry.register_step_template(st)
        for gt in pack.gate_templates:
            registry.register_gate_template(gt)


def merge_routing_rules(pack_rules_list: list[list[RoutingRule]]) -> list[RoutingRule]:
    """Merge routing rules from packs (by load order).

    Raises ValueError on duplicate rule_id. Caller composes with kernel defaults.

    Args:
        pack_rules_list: List of rule lists (one per pack, in load order).

    Returns:
        Flattened list of rules (duplicate rule_id raises).

    Raises:
        ValueError: On duplicate rule_id.
    """
    seen: set[str] = set()
    result: list[RoutingRule] = []
    for rules in pack_rules_list:
        for rule in rules:
            if rule.rule_id in seen:
                raise ValueError(f"Duplicate routing rule_id: {rule.rule_id!r}")
            seen.add(rule.rule_id)
            result.append(rule)
    return result


def _intersect_allowed_tools(policies: list[SafetyPolicy]) -> set[str]:
    out = set(policies[0].allowed_tools)
    for p in policies[1:]:
        out &= set(p.allowed_tools)
    return out


def _intersect_allow_write_paths(policies: list[SafetyPolicy]) -> set[str]:
    out = set(policies[0].allow_write_paths)
    for p in policies[1:]:
        out &= set(p.allow_write_paths)
    return out


def _union_deny_write_paths(policies: list[SafetyPolicy]) -> set[str]:
    out = set(policies[0].deny_write_paths)
    for p in policies[1:]:
        out |= set(p.deny_write_paths)
    return out


def _merge_two_or_more_policies(policies: list[SafetyPolicy]) -> SafetyPolicy:
    """Intersect allow*, union deny*, min max_diff, deny if any deny.

    Args:
        policies: Two or more safety policies to merge.

    Returns:
        Single merged SafetyPolicy (no weakening).
    """
    allowed_tools_set = _intersect_allowed_tools(policies)
    allow_write_set = _intersect_allow_write_paths(policies)
    deny_write_set = _union_deny_write_paths(policies)
    max_diff_values = [
        p.max_diff_size_bytes for p in policies if p.max_diff_size_bytes is not None
    ]
    max_diff = min(max_diff_values) if max_diff_values else None
    network_deny = any(p.network_access == "deny" for p in policies)
    return SafetyPolicy(
        allow_write_paths=sorted(allow_write_set),
        deny_write_paths=sorted(deny_write_set),
        max_diff_size_bytes=max_diff,
        allowed_tools=sorted(allowed_tools_set),
        network_access="deny" if network_deny else "allow",
    )


def merge_pack_safety_policies(packs: list[PackDefinition]) -> SafetyPolicy | None:
    """Merge default_safety_policy from packs (no weakening).

    allowed_tools/allow_write_paths: intersection; deny_write_paths: union;
    network_access: deny if any deny; max_diff_size_bytes: min or None.
    Returns None if no pack has default_safety_policy.

    Args:
        packs: List of pack definitions.

    Returns:
        Merged SafetyPolicy or None if no pack has default_safety_policy.
    """
    policies = [
        p.default_safety_policy for p in packs if p.default_safety_policy is not None
    ]
    if not policies:
        return None
    if len(policies) == 1:
        return policies[0]
    return _merge_two_or_more_policies(policies)
