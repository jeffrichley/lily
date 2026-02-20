"""Unit tests for plugin security hash/preflight/approval services."""

from __future__ import annotations

from pathlib import Path

import pytest

from lily.config import SkillSandboxSettings
from lily.runtime.security import (
    ApprovalDecision,
    ApprovalRequest,
    SecurityApprovalStore,
    SecurityAuthorizationError,
    SecurityGate,
    SecurityHashService,
    SecurityPreflightScanner,
    SecurityPrompt,
)
from lily.skills.types import (
    InvocationMode,
    SkillCapabilitySpec,
    SkillEntry,
    SkillPluginSpec,
    SkillSource,
)


class _PromptStub(SecurityPrompt):
    """Prompt stub that returns a fixed decision."""

    def __init__(self, decision: ApprovalDecision) -> None:
        self.decision = decision
        self.calls = 0

    def request_approval(self, request: ApprovalRequest) -> ApprovalDecision | None:
        del request
        self.calls += 1
        return self.decision


def _entry(skill_root: Path) -> SkillEntry:
    """Build plugin skill entry fixture."""
    return SkillEntry(
        name="echo_plugin",
        source=SkillSource.WORKSPACE,
        path=skill_root / "SKILL.md",
        invocation_mode=InvocationMode.TOOL_DISPATCH,
        command_tool_provider="plugin",
        command_tool="execute",
        capabilities=SkillCapabilitySpec(declared_tools=("plugin:execute",)),
        plugin=SkillPluginSpec(
            entrypoint="plugin.py",
            source_files=("plugin.py",),
            profile="safe_eval",
        ),
    )


def _write_skill(skill_root: Path, plugin_source: str) -> None:
    """Write minimal skill + plugin files."""
    skill_root.mkdir(parents=True, exist_ok=True)
    (skill_root / "SKILL.md").write_text("# test", encoding="utf-8")
    (skill_root / "plugin.py").write_text(plugin_source, encoding="utf-8")


@pytest.mark.unit
def test_security_hash_is_deterministic(tmp_path: Path) -> None:
    """Security hash should be stable for unchanged bundle content."""
    skill_root = tmp_path / "skills" / "echo_plugin"
    _write_skill(
        skill_root,
        "def run(payload, **kwargs):\n    return {'display': payload}\n",
    )
    entry = _entry(skill_root)
    sandbox = SkillSandboxSettings()
    service = SecurityHashService(sandbox=sandbox, project_root=tmp_path)

    first, _ = service.compute(entry)
    second, _ = service.compute(entry)

    assert first == second


@pytest.mark.unit
def test_security_preflight_denies_blocked_signature(tmp_path: Path) -> None:
    """Preflight should hard-deny blocked code signatures before execution."""
    skill_root = tmp_path / "skills" / "echo_plugin"
    _write_skill(skill_root, "import subprocess\n")
    entry = _entry(skill_root)

    scanner = SecurityPreflightScanner()
    try:
        scanner.scan(entry)
    except SecurityAuthorizationError as exc:
        assert exc.code == "security_preflight_denied"
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("Expected SecurityAuthorizationError")


@pytest.mark.unit
def test_security_gate_requires_prompt_when_no_cached_grant(tmp_path: Path) -> None:
    """Security gate should fail with approval_required when prompt is absent."""
    skill_root = tmp_path / "skills" / "echo_plugin"
    _write_skill(
        skill_root,
        "def run(payload, **kwargs):\n    return {'display': payload}\n",
    )
    entry = _entry(skill_root)
    sandbox = SkillSandboxSettings()
    gate = SecurityGate(
        hash_service=SecurityHashService(sandbox=sandbox, project_root=tmp_path),
        preflight=SecurityPreflightScanner(),
        store=SecurityApprovalStore(sqlite_path=tmp_path / "security.sqlite"),
        prompt=None,
        sandbox=sandbox,
    )

    try:
        gate.authorize(entry=entry, agent_id="default")
    except SecurityAuthorizationError as exc:
        assert exc.code == "approval_required"
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("Expected SecurityAuthorizationError")


@pytest.mark.unit
def test_security_gate_reuses_always_allow_grant(tmp_path: Path) -> None:
    """Always-allow grant should persist and skip repeat prompts for same hash."""
    skill_root = tmp_path / "skills" / "echo_plugin"
    _write_skill(
        skill_root,
        "def run(payload, **kwargs):\n    return {'display': payload}\n",
    )
    entry = _entry(skill_root)
    sandbox = SkillSandboxSettings()
    prompt = _PromptStub(ApprovalDecision.ALWAYS_ALLOW)
    gate = SecurityGate(
        hash_service=SecurityHashService(sandbox=sandbox, project_root=tmp_path),
        preflight=SecurityPreflightScanner(),
        store=SecurityApprovalStore(sqlite_path=tmp_path / "security.sqlite"),
        prompt=prompt,
        sandbox=sandbox,
    )

    first_hash, _ = gate.authorize(entry=entry, agent_id="default")
    second_hash, _ = gate.authorize(entry=entry, agent_id="default")

    assert first_hash == second_hash
    assert prompt.calls == 1
