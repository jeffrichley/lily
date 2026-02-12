"""Unit tests for pack default safety policy merging (Layer 6)."""

from __future__ import annotations


from lily.kernel.pack_models import PackDefinition
from lily.kernel.pack_registration import merge_pack_safety_policies
from lily.kernel.policy_models import SafetyPolicy


def _pack(
    name: str,
    *,
    allow_write_paths: list[str] | None = None,
    deny_write_paths: list[str] | None = None,
    allowed_tools: list[str] | None = None,
    network_access: str = "deny",
    max_diff_size_bytes: int | None = None,
) -> PackDefinition:
    return PackDefinition(
        name=name,
        version="1.0.0",
        minimum_kernel_version="0.1.0",
        default_safety_policy=SafetyPolicy(
            allow_write_paths=allow_write_paths or [],
            deny_write_paths=deny_write_paths or [],
            allowed_tools=allowed_tools or ["local_command"],
            network_access=network_access,
            max_diff_size_bytes=max_diff_size_bytes,
        ),
    )


def test_policy_merge_deterministic() -> None:
    """Merging same packs in same order yields same result."""
    packs = [
        _pack("a", allowed_tools=["local_command"], deny_write_paths=["/sys"]),
        _pack("b", allowed_tools=["local_command"], deny_write_paths=["/etc"]),
    ]
    m1 = merge_pack_safety_policies(packs)
    m2 = merge_pack_safety_policies(packs)
    assert m1 is not None and m2 is not None, (
        "merge should return policy for packs with policies"
    )
    assert m1.allowed_tools == m2.allowed_tools, (
        "deterministic merge: allowed_tools should match"
    )
    assert set(m1.deny_write_paths) == set(m2.deny_write_paths), (
        "deterministic merge: deny_write_paths should match"
    )


def test_conservative_merge_enforced() -> None:
    """allowed_tools intersection, deny_write_paths union, network deny wins."""
    packs = [
        _pack(
            "a",
            allowed_tools=["local_command", "curl"],
            deny_write_paths=["/sys"],
            network_access="allow",
        ),
        _pack(
            "b",
            allowed_tools=["local_command"],
            deny_write_paths=["/etc"],
            network_access="deny",
        ),
    ]
    merged = merge_pack_safety_policies(packs)
    assert merged is not None, "packs with policies should yield merged policy"
    assert set(merged.allowed_tools) == {"local_command"}, (
        "allowed_tools should be intersection"
    )
    assert set(merged.deny_write_paths) == {"/sys", "/etc"}
    assert merged.network_access == "deny"


def test_allow_write_paths_intersection() -> None:
    """allow_write_paths is intersection (only paths all allow)."""
    packs = [
        _pack("a", allow_write_paths=["/tmp", "/out"]),
        _pack("b", allow_write_paths=["/tmp"]),
    ]
    merged = merge_pack_safety_policies(packs)
    assert merged is not None
    assert set(merged.allow_write_paths) == {"/tmp"}


def test_conflicts_resolved_safely() -> None:
    """max_diff_size_bytes: minimum of set values; no pack weakens."""
    packs = [
        _pack("a", max_diff_size_bytes=1000),
        _pack("b", max_diff_size_bytes=500),
    ]
    merged = merge_pack_safety_policies(packs)
    assert merged is not None
    assert merged.max_diff_size_bytes == 500


def test_no_policies_returns_none() -> None:
    """If no pack has default_safety_policy, return None."""
    packs = [
        PackDefinition(name="a", version="1.0.0", minimum_kernel_version="0.1.0"),
        PackDefinition(name="b", version="1.0.0", minimum_kernel_version="0.1.0"),
    ]
    assert merge_pack_safety_policies(packs) is None


def test_single_policy_returns_it() -> None:
    """Single pack with policy returns that policy."""
    pack = _pack("only", allowed_tools=["local_command"])
    merged = merge_pack_safety_policies([pack])
    assert merged is not None
    assert merged.allowed_tools == ["local_command"]
