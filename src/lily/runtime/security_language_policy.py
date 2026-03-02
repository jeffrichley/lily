"""Deterministic AST-based language restriction policy for plugin code."""

from __future__ import annotations

import ast
import hashlib
import json
import sys
from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, ConfigDict

from lily.skills.types import SkillEntry


class UntrustedCodeClass(StrEnum):
    """Trust classification for code under policy evaluation."""

    TRUSTED = "trusted"
    UNTRUSTED = "untrusted"


class LockdownLevel(StrEnum):
    """Configurable strictness levels for language restrictions."""

    YOLO = "yolo"
    BASELINE = "baseline"
    STRICT = "strict"
    PARANOID = "paranoid"


class LanguagePolicyConfig(BaseModel):
    """Configuration for deterministic policy evaluation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    code_class: UntrustedCodeClass = UntrustedCodeClass.UNTRUSTED
    lockdown: LockdownLevel = LockdownLevel.STRICT


class LanguagePolicyViolation(BaseModel):
    """One deterministic AST restriction violation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    rule_id: str
    path: str
    line: int
    column: int


class LanguagePolicyCacheResult(BaseModel):
    """Cached deterministic policy result for one file fingerprint."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    allowed: bool
    rule_id: str | None = None
    line: int | None = None
    column: int | None = None


class LanguagePolicyCache(Protocol):
    """Cache contract for language-policy file scan results."""

    def get(
        self,
        *,
        file_sha256: str,
        policy_fingerprint: str,
    ) -> LanguagePolicyCacheResult | None:
        """Lookup one cached file scan result.

        Args:
            file_sha256: SHA256 hash of source file bytes.
            policy_fingerprint: Deterministic policy fingerprint.
        """

    def put(
        self,
        *,
        file_sha256: str,
        policy_fingerprint: str,
        result: LanguagePolicyCacheResult,
    ) -> None:
        """Persist one cached file scan result.

        Args:
            file_sha256: SHA256 hash of source file bytes.
            policy_fingerprint: Deterministic policy fingerprint.
            result: Cached allow/deny result payload.
        """


class InMemoryLanguagePolicyCache:
    """In-memory cache backend for language policy scan results."""

    def __init__(self) -> None:
        """Initialize deterministic in-process cache map."""
        self._rows: dict[tuple[str, str], LanguagePolicyCacheResult] = {}

    def get(
        self,
        *,
        file_sha256: str,
        policy_fingerprint: str,
    ) -> LanguagePolicyCacheResult | None:
        """Lookup one cached file scan result.

        Args:
            file_sha256: SHA256 hash of source file bytes.
            policy_fingerprint: Deterministic policy fingerprint.

        Returns:
            Cached scan result when available, else ``None``.
        """
        return self._rows.get((file_sha256, policy_fingerprint))

    def put(
        self,
        *,
        file_sha256: str,
        policy_fingerprint: str,
        result: LanguagePolicyCacheResult,
    ) -> None:
        """Persist one cached file scan result.

        Args:
            file_sha256: SHA256 hash of source file bytes.
            policy_fingerprint: Deterministic policy fingerprint.
            result: Cached allow/deny result payload.
        """
        self._rows[(file_sha256, policy_fingerprint)] = result


class LanguagePolicyDeniedError(RuntimeError):
    """Deterministic policy denial payload for security-gate integration."""

    def __init__(
        self,
        *,
        skill: str,
        violation: LanguagePolicyViolation,
    ) -> None:
        """Store deterministic denial payload.

        Args:
            skill: Skill name.
            violation: First deterministic violation.
        """
        self.code = "security_language_policy_denied"
        self.message = (
            "Security alert: plugin language policy denied due to blocked rule "
            f"'{violation.rule_id}'."
        )
        self.data = {
            "skill": skill,
            "path": violation.path,
            "signature": violation.rule_id,
            "rule_id": violation.rule_id,
            "line": violation.line,
            "column": violation.column,
        }
        super().__init__(self.message)


class SecurityLanguagePolicy:
    """Deterministic AST policy scanner for plugin source files."""

    _FORBIDDEN_NODES_BASELINE: tuple[type[ast.AST], ...] = (
        ast.Import,
        ast.ImportFrom,
    )
    _FORBIDDEN_BUILTIN_CALLS_STRICT: frozenset[str] = frozenset(
        {
            "__import__",
            "eval",
            "exec",
            "compile",
            "open",
            "input",
        }
    )
    _FORBIDDEN_BUILTIN_CALLS_PARANOID: frozenset[str] = frozenset(
        {
            *tuple(_FORBIDDEN_BUILTIN_CALLS_STRICT),
            "globals",
            "locals",
            "vars",
            "getattr",
            "setattr",
            "delattr",
        }
    )

    def __init__(
        self,
        *,
        config: LanguagePolicyConfig | None = None,
        cache: LanguagePolicyCache | None = None,
    ) -> None:
        """Create policy scanner with deterministic defaults.

        Args:
            config: Optional explicit policy config.
            cache: Optional file scan cache backend.
        """
        self._config = config or LanguagePolicyConfig()
        self._cache = cache or InMemoryLanguagePolicyCache()

    def scan(self, entry: SkillEntry) -> None:
        """Evaluate declared plugin files and deny the first violation.

        Args:
            entry: Skill entry under validation.

        Raises:
            LanguagePolicyDeniedError: If policy rejects the plugin source.
        """
        if self._config.code_class == UntrustedCodeClass.TRUSTED:
            return
        if self._config.lockdown == LockdownLevel.YOLO:
            return

        policy_fingerprint = self._policy_fingerprint()
        for relative in _policy_files(entry):
            absolute = (entry.path.parent / relative).resolve()
            source_bytes = absolute.read_bytes()
            file_sha256 = _sha256_bytes(source_bytes)
            cached = self._cache.get(
                file_sha256=file_sha256,
                policy_fingerprint=policy_fingerprint,
            )
            if cached is not None:
                if cached.allowed:
                    continue
                raise LanguagePolicyDeniedError(
                    skill=entry.name,
                    violation=LanguagePolicyViolation(
                        rule_id=cached.rule_id or "unknown_rule",
                        path=relative,
                        line=cached.line or 1,
                        column=cached.column or 0,
                    ),
                )

            source = source_bytes.decode("utf-8")
            file_violations = self._scan_one(path=relative, source=source)
            if not file_violations:
                self._cache.put(
                    file_sha256=file_sha256,
                    policy_fingerprint=policy_fingerprint,
                    result=LanguagePolicyCacheResult(allowed=True),
                )
                continue

            first = sorted(
                file_violations,
                key=lambda item: (item.line, item.column, item.rule_id),
            )[0]
            self._cache.put(
                file_sha256=file_sha256,
                policy_fingerprint=policy_fingerprint,
                result=LanguagePolicyCacheResult(
                    allowed=False,
                    rule_id=first.rule_id,
                    line=first.line,
                    column=first.column,
                ),
            )
            raise LanguagePolicyDeniedError(skill=entry.name, violation=first)

    def _scan_one(self, *, path: str, source: str) -> list[LanguagePolicyViolation]:
        """Scan one source file and return deterministic violations.

        Args:
            path: Relative plugin file path.
            source: Source text.

        Returns:
            Deterministic policy violations for the file.
        """
        try:
            tree = ast.parse(source, filename=path)
        except SyntaxError as exc:
            return [
                LanguagePolicyViolation(
                    rule_id="syntax_error",
                    path=path,
                    line=exc.lineno or 1,
                    column=exc.offset or 0,
                )
            ]

        visitor = _PolicyVisitor(
            path=path,
            lockdown=self._config.lockdown,
        )
        visitor.visit(tree)
        return visitor.violations

    def _policy_fingerprint(self) -> str:
        """Return deterministic fingerprint for active policy semantics.

        Returns:
            Stable fingerprint for the active policy rule-set and config.
        """
        payload = {
            "policy_version": "v1",
            "code_class": self._config.code_class.value,
            "lockdown": self._config.lockdown.value,
            "python_minor": f"{sys.version_info.major}.{sys.version_info.minor}",
            "rules": {
                "strict_calls": sorted(self._FORBIDDEN_BUILTIN_CALLS_STRICT),
                "paranoid_calls": sorted(self._FORBIDDEN_BUILTIN_CALLS_PARANOID),
                "deny_import_nodes": True,
                "deny_dunder_attribute_in_strict_plus": True,
            },
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
        return _sha256_bytes(encoded)


class _PolicyVisitor(ast.NodeVisitor):
    """AST visitor that emits deterministic rule violations."""

    def __init__(self, *, path: str, lockdown: LockdownLevel) -> None:
        """Store evaluation context.

        Args:
            path: Relative file path.
            lockdown: Active lockdown level.
        """
        self._path = path
        self._lockdown = lockdown
        self.violations: list[LanguagePolicyViolation] = []

    def visit_Import(self, node: ast.Import) -> None:
        """Deny import statements.

        Args:
            node: AST import node.
        """
        self._record("node_import", node)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Deny from-import statements.

        Args:
            node: AST import-from node.
        """
        self._record("node_import_from", node)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Deny blocked builtin calls based on lockdown level.

        Args:
            node: AST call node.
        """
        name = _call_name(node.func)
        if name and name in self._forbidden_calls():
            self._record("forbidden_builtin_call", node)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        """Deny dunder attribute access in strict/paranoid modes.

        Args:
            node: AST attribute node.
        """
        if (
            self._lockdown in {LockdownLevel.STRICT, LockdownLevel.PARANOID}
            and node.attr.startswith("__")
            and node.attr.endswith("__")
        ):
            self._record("dunder_attribute_access", node)
        self.generic_visit(node)

    def _forbidden_calls(self) -> frozenset[str]:
        """Return blocked call names for the active lockdown level.

        Returns:
            Set of blocked direct call names for the configured lockdown level.
        """
        if self._lockdown in {LockdownLevel.YOLO, LockdownLevel.BASELINE}:
            return frozenset()
        if self._lockdown == LockdownLevel.STRICT:
            return SecurityLanguagePolicy._FORBIDDEN_BUILTIN_CALLS_STRICT
        return SecurityLanguagePolicy._FORBIDDEN_BUILTIN_CALLS_PARANOID

    def _record(self, rule_id: str, node: ast.AST) -> None:
        """Append one deterministic violation.

        Args:
            rule_id: Stable rule identifier.
            node: AST node where violation was detected.
        """
        self.violations.append(
            LanguagePolicyViolation(
                rule_id=rule_id,
                path=self._path,
                line=getattr(node, "lineno", 1),
                column=getattr(node, "col_offset", 0),
            )
        )


def _call_name(func: ast.AST) -> str | None:
    """Extract direct call name where available.

    Args:
        func: AST function expression from a ``Call`` node.

    Returns:
        Direct call name when available, else ``None``.
    """
    if isinstance(func, ast.Name):
        return func.id
    return None


def _policy_files(entry: SkillEntry) -> tuple[str, ...]:
    """Return plugin files included in policy scanning.

    Args:
        entry: Skill entry containing plugin file manifest.

    Returns:
        Sorted unique plugin files included in policy scanning.
    """
    values = {
        *entry.plugin.source_files,
        entry.plugin.entrypoint or "",
    }
    return tuple(sorted(value for value in values if value))


def _sha256_bytes(data: bytes) -> str:
    """Compute SHA-256 hex digest from bytes.

    Args:
        data: Input byte payload.

    Returns:
        Hex digest string.
    """
    return hashlib.sha256(data).hexdigest()
