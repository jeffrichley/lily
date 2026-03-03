"""Unit tests for deterministic AST language restriction policy."""

from __future__ import annotations

from pathlib import Path

import pytest

from lily.runtime.security_language_policy import (
    InMemoryLanguagePolicyCache,
    LanguagePolicyConfig,
    LanguagePolicyDeniedError,
    LockdownLevel,
    SecurityLanguagePolicy,
    UntrustedCodeClass,
)
from lily.skills.types import (
    InvocationMode,
    SkillCapabilitySpec,
    SkillEntry,
    SkillPluginSpec,
    SkillSource,
)


def _entry(skill_root: Path, *, source_files: tuple[str, ...]) -> SkillEntry:
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
            entrypoint=source_files[0],
            source_files=source_files,
            profile="safe_eval",
        ),
    )


def _write_skill(skill_root: Path, files: dict[str, str]) -> None:
    """Write minimal skill manifest and plugin files."""
    skill_root.mkdir(parents=True, exist_ok=True)
    (skill_root / "SKILL.md").write_text("# test", encoding="utf-8")
    for rel_path, content in files.items():
        (skill_root / rel_path).write_text(content, encoding="utf-8")


@pytest.mark.unit
def test_language_policy_allows_safe_plugin_source(tmp_path: Path) -> None:
    """Policy should allow benign code without blocked AST patterns."""
    # Arrange - write a benign plugin and construct scanner inputs.
    skill_root = tmp_path / "skills" / "echo_plugin"
    _write_skill(
        skill_root,
        {
            "plugin.py": (
                "def run(payload, **kwargs):\n"
                "    note = 'contains text eval( but is only a string'\n"
                "    return {'display': payload, 'note': note}\n"
            )
        },
    )
    entry = _entry(skill_root, source_files=("plugin.py",))
    scanner = SecurityLanguagePolicy()

    # Act - run policy scan for the plugin entry.
    scanner.scan(entry)
    # Assert - no exception means the benign source is accepted.


@pytest.mark.unit
def test_language_policy_denies_import_node_deterministically(tmp_path: Path) -> None:
    """Policy should deny import statements with deterministic payload fields."""
    # Arrange - write plugin source containing an import statement.
    skill_root = tmp_path / "skills" / "echo_plugin"
    _write_skill(skill_root, {"plugin.py": "import os\n"})
    entry = _entry(skill_root, source_files=("plugin.py",))
    scanner = SecurityLanguagePolicy()

    # Act - scan and capture deterministic deny error.
    with pytest.raises(LanguagePolicyDeniedError) as exc_info:
        scanner.scan(entry)
    # Assert - deny payload contains stable code/message/data fields.
    exc = exc_info.value
    assert exc.code == "security_language_policy_denied"
    assert "blocked rule 'node_import'" in exc.message
    assert exc.data["skill"] == "echo_plugin"
    assert exc.data["path"] == "plugin.py"
    assert exc.data["signature"] == "node_import"
    assert exc.data["rule_id"] == "node_import"


@pytest.mark.unit
def test_language_policy_denies_forbidden_builtin_call(tmp_path: Path) -> None:
    """Policy should deny direct eval/exec-style builtin calls."""
    # Arrange - write plugin source that directly calls eval.
    skill_root = tmp_path / "skills" / "echo_plugin"
    _write_skill(skill_root, {"plugin.py": "eval('1+1')\n"})
    entry = _entry(skill_root, source_files=("plugin.py",))
    scanner = SecurityLanguagePolicy()

    # Act - scan and capture deterministic deny error.
    with pytest.raises(LanguagePolicyDeniedError) as exc_info:
        scanner.scan(entry)
    # Assert - denial maps to forbidden builtin call rule.
    assert exc_info.value.data["rule_id"] == "forbidden_builtin_call"


@pytest.mark.unit
def test_language_policy_denies_syntax_errors_deterministically(tmp_path: Path) -> None:
    """Policy should treat syntax errors as deterministic deny events."""
    # Arrange - write syntactically invalid plugin source.
    skill_root = tmp_path / "skills" / "echo_plugin"
    _write_skill(skill_root, {"plugin.py": "def run(:\n    return 1\n"})
    entry = _entry(skill_root, source_files=("plugin.py",))
    scanner = SecurityLanguagePolicy()

    # Act - scan and capture deterministic deny error.
    with pytest.raises(LanguagePolicyDeniedError) as exc_info:
        scanner.scan(entry)
    # Assert - denial rule is syntax_error with source path context.
    assert exc_info.value.data["rule_id"] == "syntax_error"
    assert exc_info.value.data["path"] == "plugin.py"


@pytest.mark.unit
def test_language_policy_denies_non_utf8_source_deterministically(
    tmp_path: Path,
) -> None:
    """Policy should deny non-UTF8 plugin source deterministically."""
    # Arrange - write plugin source bytes that are invalid UTF-8.
    skill_root = tmp_path / "skills" / "echo_plugin"
    skill_root.mkdir(parents=True, exist_ok=True)
    (skill_root / "SKILL.md").write_text("# test", encoding="utf-8")
    (skill_root / "plugin.py").write_bytes(b"\xff\xfe\x00")
    entry = _entry(skill_root, source_files=("plugin.py",))
    scanner = SecurityLanguagePolicy()

    # Act - scan and capture deterministic deny error.
    with pytest.raises(LanguagePolicyDeniedError) as exc_info:
        scanner.scan(entry)
    # Assert - denial maps to non-UTF8 decode failure rule.
    assert exc_info.value.data["rule_id"] == "file_decode_error"
    assert exc_info.value.data["path"] == "plugin.py"


@pytest.mark.unit
def test_language_policy_denies_file_read_errors_deterministically(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Policy should deny file read failures with deterministic payload fields."""
    # Arrange - write valid skill files then force read_bytes failure for plugin file.
    skill_root = tmp_path / "skills" / "echo_plugin"
    _write_skill(skill_root, {"plugin.py": "def run():\n    return 1\n"})
    plugin_file = (skill_root / "plugin.py").resolve()
    entry = _entry(skill_root, source_files=("plugin.py",))
    scanner = SecurityLanguagePolicy()
    original_read_bytes = Path.read_bytes

    def _read_bytes_raise(path: Path) -> bytes:
        if path.resolve() == plugin_file:
            raise OSError("forced read failure")
        return original_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", _read_bytes_raise)

    # Act - scan and capture deterministic deny error.
    with pytest.raises(LanguagePolicyDeniedError) as exc_info:
        scanner.scan(entry)
    # Assert - denial maps to file read error rule.
    assert exc_info.value.data["rule_id"] == "file_read_error"
    assert exc_info.value.data["path"] == "plugin.py"


@pytest.mark.unit
def test_language_policy_denies_first_violation_in_sorted_file_order(
    tmp_path: Path,
) -> None:
    """Policy should select first violation by deterministic path ordering."""
    # Arrange - write two violating files with reverse lexical order input.
    skill_root = tmp_path / "skills" / "echo_plugin"
    _write_skill(
        skill_root,
        {
            "z_plugin.py": "import os\n",
            "a_plugin.py": "from math import sqrt\n",
        },
    )
    entry = _entry(skill_root, source_files=("z_plugin.py", "a_plugin.py"))
    scanner = SecurityLanguagePolicy()

    # Act - scan and capture deterministic deny error.
    with pytest.raises(LanguagePolicyDeniedError) as exc_info:
        scanner.scan(entry)
    # Assert - reported violation path follows deterministic sorted order.
    assert exc_info.value.data["path"] == "a_plugin.py"
    assert exc_info.value.data["rule_id"] == "node_import_from"


@pytest.mark.unit
def test_language_policy_lockdown_levels_are_configurable(tmp_path: Path) -> None:
    """Paranoid mode should deny calls that strict mode allows."""
    # Arrange - write plugin source that calls vars().
    skill_root = tmp_path / "skills" / "echo_plugin"
    _write_skill(skill_root, {"plugin.py": "vars()\n"})
    entry = _entry(skill_root, source_files=("plugin.py",))
    strict_scanner = SecurityLanguagePolicy(
        config=LanguagePolicyConfig(lockdown=LockdownLevel.STRICT)
    )
    paranoid_scanner = SecurityLanguagePolicy(
        config=LanguagePolicyConfig(lockdown=LockdownLevel.PARANOID)
    )

    # Act - scan once with strict then with paranoid lockdown.
    strict_scanner.scan(entry)
    with pytest.raises(LanguagePolicyDeniedError) as exc_info:
        paranoid_scanner.scan(entry)
    # Assert - paranoid mode denies vars() via forbidden builtin call rule.
    assert exc_info.value.data["rule_id"] == "forbidden_builtin_call"


@pytest.mark.unit
def test_language_policy_trusted_code_class_skips_restrictions(tmp_path: Path) -> None:
    """Trusted classification should bypass policy restrictions."""
    # Arrange - write restricted source but configure trusted code class.
    skill_root = tmp_path / "skills" / "echo_plugin"
    _write_skill(skill_root, {"plugin.py": "import os\n"})
    entry = _entry(skill_root, source_files=("plugin.py",))
    scanner = SecurityLanguagePolicy(
        config=LanguagePolicyConfig(code_class=UntrustedCodeClass.TRUSTED)
    )

    # Act - run policy scan for trusted classification.
    scanner.scan(entry)
    # Assert - no exception means trusted code bypass remains deterministic.


@pytest.mark.unit
def test_language_policy_yolo_lockdown_skips_restrictions(tmp_path: Path) -> None:
    """YOLO lockdown should bypass AST restrictions for untrusted code."""
    # Arrange - write restricted source and configure untrusted+yolo.
    skill_root = tmp_path / "skills" / "echo_plugin"
    _write_skill(skill_root, {"plugin.py": "import os\neval('1+1')\n"})
    entry = _entry(skill_root, source_files=("plugin.py",))
    scanner = SecurityLanguagePolicy(
        config=LanguagePolicyConfig(
            code_class=UntrustedCodeClass.UNTRUSTED,
            lockdown=LockdownLevel.YOLO,
        )
    )

    # Act - run policy scan with YOLO lockdown.
    scanner.scan(entry)
    # Assert - no exception means YOLO bypass is deterministic.


@pytest.mark.unit
def test_language_policy_cache_hit_skips_rescan_for_allowed_file(
    tmp_path: Path,
) -> None:
    """Second scan should hit cache and avoid reparsing unchanged safe source."""
    # Arrange - safe source, shared cache, and scanner with call guard hook.
    skill_root = tmp_path / "skills" / "echo_plugin"
    _write_skill(
        skill_root,
        {"plugin.py": "def run(payload, **kwargs):\n    return {}\n"},
    )
    entry = _entry(skill_root, source_files=("plugin.py",))
    cache = InMemoryLanguagePolicyCache()
    scanner = SecurityLanguagePolicy(cache=cache)
    scanner.scan(entry)

    def _fail_scan_one(*, path: str, source: str) -> list[object]:
        del path
        del source
        raise AssertionError("Expected cache hit to bypass _scan_one")

    scanner._scan_one = _fail_scan_one  # type: ignore[method-assign]

    # Act - rescan unchanged source.
    scanner.scan(entry)
    # Assert - no assertion failure means cache hit bypassed rescanning.


@pytest.mark.unit
def test_language_policy_cache_replays_denial_for_unchanged_file(
    tmp_path: Path,
) -> None:
    """Second scan of unchanged violating file should deny from cache."""
    # Arrange - violating source, shared cache, and scanner.
    skill_root = tmp_path / "skills" / "echo_plugin"
    _write_skill(skill_root, {"plugin.py": "import os\n"})
    entry = _entry(skill_root, source_files=("plugin.py",))
    cache = InMemoryLanguagePolicyCache()
    scanner = SecurityLanguagePolicy(cache=cache)
    with pytest.raises(LanguagePolicyDeniedError):
        scanner.scan(entry)

    def _fail_scan_one(*, path: str, source: str) -> list[object]:
        del path
        del source
        raise AssertionError("Expected cache hit to bypass _scan_one")

    scanner._scan_one = _fail_scan_one  # type: ignore[method-assign]

    # Act - rescan unchanged violating source and capture denial.
    with pytest.raises(LanguagePolicyDeniedError) as exc_info:
        scanner.scan(entry)
    # Assert - cached denial preserves deterministic rule and path.
    assert exc_info.value.data["rule_id"] == "node_import"
    assert exc_info.value.data["path"] == "plugin.py"


@pytest.mark.unit
def test_language_policy_cache_invalidates_on_file_hash_change(tmp_path: Path) -> None:
    """Changing file contents should invalidate prior cache entry automatically."""
    # Arrange - cache an allow result from initial safe source.
    skill_root = tmp_path / "skills" / "echo_plugin"
    plugin_path = skill_root / "plugin.py"
    _write_skill(
        skill_root,
        {"plugin.py": "def run(payload, **kwargs):\n    return {}\n"},
    )
    entry = _entry(skill_root, source_files=("plugin.py",))
    scanner = SecurityLanguagePolicy(cache=InMemoryLanguagePolicyCache())
    scanner.scan(entry)
    plugin_path.write_text("import os\n", encoding="utf-8")

    # Act - rescan after content change and capture deny.
    with pytest.raises(LanguagePolicyDeniedError) as exc_info:
        scanner.scan(entry)
    # Assert - changed hash forced rescan and returned import deny.
    assert exc_info.value.data["rule_id"] == "node_import"


@pytest.mark.unit
def test_language_policy_cache_invalidates_on_policy_fingerprint_change(
    tmp_path: Path,
) -> None:
    """Changing lockdown level should miss cache via policy fingerprint change."""
    # Arrange - strict caches allow for vars(), paranoid should not reuse that allow.
    skill_root = tmp_path / "skills" / "echo_plugin"
    _write_skill(skill_root, {"plugin.py": "vars()\n"})
    entry = _entry(skill_root, source_files=("plugin.py",))
    shared_cache = InMemoryLanguagePolicyCache()
    strict_scanner = SecurityLanguagePolicy(
        cache=shared_cache,
        config=LanguagePolicyConfig(lockdown=LockdownLevel.STRICT),
    )
    paranoid_scanner = SecurityLanguagePolicy(
        cache=shared_cache,
        config=LanguagePolicyConfig(lockdown=LockdownLevel.PARANOID),
    )
    strict_scanner.scan(entry)

    # Act - scan same file under paranoid lockdown.
    with pytest.raises(LanguagePolicyDeniedError) as exc_info:
        paranoid_scanner.scan(entry)
    # Assert - denial confirms fingerprint mismatch did not reuse strict allow.
    assert exc_info.value.data["rule_id"] == "forbidden_builtin_call"
