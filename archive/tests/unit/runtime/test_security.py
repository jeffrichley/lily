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
from lily.runtime.security_language_policy import LanguagePolicyCacheResult
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
    # Arrange - skill files, entry, hash service
    skill_root = tmp_path / "skills" / "echo_plugin"
    _write_skill(
        skill_root,
        "def run(payload, **kwargs):\n    return {'display': payload}\n",
    )
    entry = _entry(skill_root)
    sandbox = SkillSandboxSettings()
    service = SecurityHashService(sandbox=sandbox, project_root=tmp_path)

    # Act - compute hash twice
    first, _ = service.compute(entry)
    second, _ = service.compute(entry)

    # Assert - hashes equal
    assert first == second


@pytest.mark.unit
def test_security_preflight_denies_blocked_signature(tmp_path: Path) -> None:
    """Preflight should hard-deny blocked code signatures before execution."""
    # Arrange - skill with blocked import, entry, scanner
    skill_root = tmp_path / "skills" / "echo_plugin"
    _write_skill(skill_root, "import subprocess\n")
    entry = _entry(skill_root)

    scanner = SecurityPreflightScanner()
    # Act - scan
    try:
        scanner.scan(entry)
    except SecurityAuthorizationError as exc:
        # Assert - preflight denied
        assert exc.code == "security_preflight_denied"
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("Expected SecurityAuthorizationError")


@pytest.mark.unit
def test_security_gate_requires_prompt_when_no_cached_grant(tmp_path: Path) -> None:
    """Security gate should fail with approval_required when prompt is absent."""
    # Arrange - skill, entry, gate with prompt=None
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

    # Act - authorize
    try:
        gate.authorize(entry=entry, agent_id="default")
    except SecurityAuthorizationError as exc:
        # Assert - approval_required
        assert exc.code == "approval_required"
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("Expected SecurityAuthorizationError")


@pytest.mark.unit
def test_security_gate_reuses_always_allow_grant(tmp_path: Path) -> None:
    """Always-allow grant should persist and skip repeat prompts for same hash."""
    # Arrange - skill, entry, gate with ALWAYS_ALLOW prompt stub
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

    # Act - authorize twice
    first_hash, _ = gate.authorize(entry=entry, agent_id="default")
    second_hash, _ = gate.authorize(entry=entry, agent_id="default")

    # Assert - same hash, prompt called once (cached)
    assert first_hash == second_hash
    assert prompt.calls == 1


@pytest.mark.unit
def test_security_gate_denies_language_policy_violation(tmp_path: Path) -> None:
    """Security gate should deny plugins that violate AST language policy."""
    # Arrange - plugin source with import node and normal gate dependencies.
    skill_root = tmp_path / "skills" / "echo_plugin"
    _write_skill(skill_root, "import os\n")
    entry = _entry(skill_root)
    sandbox = SkillSandboxSettings()
    gate = SecurityGate(
        hash_service=SecurityHashService(sandbox=sandbox, project_root=tmp_path),
        preflight=SecurityPreflightScanner(),
        store=SecurityApprovalStore(sqlite_path=tmp_path / "security.sqlite"),
        prompt=_PromptStub(ApprovalDecision.RUN_ONCE),
        sandbox=sandbox,
    )

    # Act - authorize and capture policy denial.
    try:
        gate.authorize(entry=entry, agent_id="default")
    except SecurityAuthorizationError as exc:
        # Assert - deterministic language policy denial payload is surfaced.
        assert exc.code == "security_language_policy_denied"
        assert exc.data["skill"] == "echo_plugin"
        assert exc.data["path"] == "plugin.py"
        assert exc.data["signature"] == "node_import"
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("Expected SecurityAuthorizationError")


@pytest.mark.unit
def test_security_gate_denies_non_utf8_plugin_source(tmp_path: Path) -> None:
    """Security gate should map non-UTF8 plugin source to deterministic denial."""
    # Arrange - plugin source bytes that fail UTF-8 decode.
    skill_root = tmp_path / "skills" / "echo_plugin"
    skill_root.mkdir(parents=True, exist_ok=True)
    (skill_root / "SKILL.md").write_text("# test", encoding="utf-8")
    (skill_root / "plugin.py").write_bytes(b"\xff\xfe\x00")
    entry = _entry(skill_root)
    sandbox = SkillSandboxSettings()
    gate = SecurityGate(
        hash_service=SecurityHashService(sandbox=sandbox, project_root=tmp_path),
        preflight=SecurityPreflightScanner(),
        store=SecurityApprovalStore(sqlite_path=tmp_path / "security.sqlite"),
        prompt=_PromptStub(ApprovalDecision.RUN_ONCE),
        sandbox=sandbox,
    )

    # Act - authorize and capture policy denial.
    try:
        gate.authorize(entry=entry, agent_id="default")
    except SecurityAuthorizationError as exc:
        # Assert - deterministic non-UTF8 decode denial is surfaced.
        assert exc.code == "security_language_policy_denied"
        assert exc.data["signature"] == "file_decode_error"
        assert exc.data["path"] == "plugin.py"
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("Expected SecurityAuthorizationError")


@pytest.mark.unit
def test_security_gate_denies_plugin_file_read_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Security gate should map plugin file read failures to deterministic denial."""
    # Arrange - valid plugin source with forced read failure on plugin file path.
    skill_root = tmp_path / "skills" / "echo_plugin"
    _write_skill(
        skill_root,
        "def run(payload, **kwargs):\n    return {'display': payload}\n",
    )
    plugin_file = (skill_root / "plugin.py").resolve()
    original_read_bytes = Path.read_bytes
    read_counts: dict[Path, int] = {}

    def _read_bytes_raise(path: Path) -> bytes:
        resolved = path.resolve()
        read_counts[resolved] = read_counts.get(resolved, 0) + 1
        # First read is from SecurityHashService.
        # Second read is from language policy scan.
        if resolved == plugin_file and read_counts[resolved] >= 2:
            raise OSError("forced read failure")
        return original_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", _read_bytes_raise)
    entry = _entry(skill_root)
    sandbox = SkillSandboxSettings()
    gate = SecurityGate(
        hash_service=SecurityHashService(sandbox=sandbox, project_root=tmp_path),
        preflight=SecurityPreflightScanner(),
        store=SecurityApprovalStore(sqlite_path=tmp_path / "security.sqlite"),
        prompt=_PromptStub(ApprovalDecision.RUN_ONCE),
        sandbox=sandbox,
    )

    # Act - authorize and capture policy denial.
    try:
        gate.authorize(entry=entry, agent_id="default")
    except SecurityAuthorizationError as exc:
        # Assert - deterministic read failure denial is surfaced.
        assert exc.code == "security_language_policy_denied"
        assert exc.data["signature"] == "file_read_error"
        assert exc.data["path"] == "plugin.py"
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("Expected SecurityAuthorizationError")


@pytest.mark.unit
def test_security_store_language_policy_cache_roundtrip(tmp_path: Path) -> None:
    """Security store should persist and reload policy cache rows deterministically."""
    # Arrange - create store and deterministic cache key/result payload.
    store = SecurityApprovalStore(sqlite_path=tmp_path / "security.sqlite")
    key = {
        "file_sha256": "a" * 64,
        "policy_fingerprint": "b" * 64,
    }
    expected = LanguagePolicyCacheResult(
        allowed=False,
        rule_id="node_import",
        line=1,
        column=0,
    )

    # Act - write and read back language-policy cache row.
    store.upsert_language_policy_result(result=expected, **key)
    actual = store.lookup_language_policy_result(**key)

    # Assert - roundtrip preserves deterministic payload fields.
    assert actual == expected
