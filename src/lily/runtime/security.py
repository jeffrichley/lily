"""Security services for plugin-backed skill execution."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, ConfigDict

from lily.config import SkillSandboxSettings
from lily.skills.types import SkillEntry


class ApprovalDecision(StrEnum):
    """Operator approval choices for one plugin invocation."""

    RUN_ONCE = "run_once"
    ALWAYS_ALLOW = "always_allow"
    DENY = "deny"


class ApprovalRequest(BaseModel):
    """Prompt payload presented to terminal HITL control."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    agent_id: str
    skill_name: str
    security_hash: str
    write_access: bool
    hash_changed: bool


class SecurityPrompt(Protocol):
    """Terminal prompt contract for security approvals."""

    def request_approval(self, request: ApprovalRequest) -> ApprovalDecision | None:
        """Prompt operator for one approval decision.

        Args:
            request: Approval request payload.
        """


class SecurityAuthorizationError(RuntimeError):
    """Deterministic security failure for plugin execution."""

    def __init__(
        self,
        *,
        code: str,
        message: str,
        data: dict[str, object] | None = None,
    ) -> None:
        """Store deterministic security failure payload.

        Args:
            code: Deterministic machine-readable error code.
            message: Human-readable error message.
            data: Optional structured error payload.
        """
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data or {}


class SecurityHashService:
    """Canonical security-hash builder for plugin skill bundles."""

    def __init__(self, *, sandbox: SkillSandboxSettings, project_root: Path) -> None:
        """Store runtime identity used in canonical hash payload.

        Args:
            sandbox: Global security sandbox settings.
            project_root: Repository root used for dependency lock fingerprint.
        """
        self._sandbox = sandbox
        self._project_root = project_root

    def compute(self, entry: SkillEntry) -> tuple[str, dict[str, object]]:
        """Compute deterministic security hash for one skill entry.

        Args:
            entry: Skill entry to hash.

        Returns:
            Tuple of hash digest and canonical payload details.

        """
        skill_file = entry.path
        skill_root = skill_file.parent
        file_manifest: list[dict[str, str]] = []
        for relative_path in self._manifest_paths(entry):
            absolute = self._resolve_under_skill_root(skill_root, relative_path)
            file_manifest.append(
                {
                    "path": relative_path,
                    "sha256": _sha256_bytes(absolute.read_bytes()),
                }
            )
        lock_file = self._project_root / "uv.lock"
        lock_sha = (
            _sha256_bytes(lock_file.read_bytes()) if lock_file.exists() else "missing"
        )
        payload: dict[str, object] = {
            "skill_name": entry.name,
            "agent_scope": "per_agent",
            "skill_md_sha256": _sha256_bytes(skill_file.read_bytes()),
            "files": file_manifest,
            "metadata": {
                "provider": entry.command_tool_provider,
                "command_tool": entry.command_tool,
                "capabilities": sorted(entry.capabilities.declared_tools),
                "profile": entry.plugin.profile,
                "write_access": entry.plugin.write_access,
                "env_allowlist": sorted(entry.plugin.env_allowlist),
            },
            "runtime_identity": {
                "policy_version": self._sandbox.policy_version,
                "image": self._sandbox.image,
                "timeout_seconds": self._sandbox.timeout_seconds,
                "memory_mb": self._sandbox.memory_mb,
                "cpu_cores": self._sandbox.cpu_cores,
                "logs_max_bytes": self._sandbox.logs_max_bytes,
            },
            "dependency_lock_fingerprint": lock_sha,
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
        return hashlib.sha256(encoded).hexdigest(), payload

    def _manifest_paths(self, entry: SkillEntry) -> tuple[str, ...]:
        """Build deterministic manifest path list.

        Args:
            entry: Skill entry.

        Returns:
            Sorted unique relative file paths.

        Raises:
            SecurityAuthorizationError: If plugin entrypoint is missing.
        """
        entrypoint = entry.plugin.entrypoint
        if not entrypoint:
            raise SecurityAuthorizationError(
                code="plugin_contract_invalid",
                message=f"Error: skill '{entry.name}' is missing plugin.entrypoint.",
                data={"skill": entry.name},
            )
        paths = {
            entrypoint,
            *entry.plugin.source_files,
            *entry.plugin.asset_files,
        }
        return tuple(sorted(path.strip() for path in paths if path.strip()))

    def _resolve_under_skill_root(self, root: Path, relative_path: str) -> Path:
        """Resolve relative path and reject escapes.

        Args:
            root: Skill root path.
            relative_path: Relative file path from manifest.

        Returns:
            Resolved absolute path.

        Raises:
            SecurityAuthorizationError: If path is unsafe or missing.
        """
        candidate = (root / relative_path).resolve()
        try:
            candidate.relative_to(root.resolve())
        except ValueError as exc:
            raise SecurityAuthorizationError(
                code="plugin_contract_invalid",
                message="Error: plugin file path escapes skill root.",
                data={"path": relative_path},
            ) from exc
        if not candidate.exists() or not candidate.is_file():
            raise SecurityAuthorizationError(
                code="plugin_contract_invalid",
                message="Error: plugin file declared in manifest is missing.",
                data={"path": relative_path},
            )
        return candidate


class SecurityPreflightScanner:
    """Hard-deny static preflight checks for plugin code."""

    _PATTERNS: tuple[tuple[str, str], ...] = (
        ("dynamic_exec_eval", "eval("),
        ("dynamic_exec_exec", "exec("),
        ("dynamic_import", "__import__("),
        ("network_socket", "import socket"),
        ("shell_subprocess", "import subprocess"),
        ("shell_os_system", "os.system("),
    )

    def scan(self, entry: SkillEntry) -> None:
        """Run preflight hard-deny checks for one plugin entry.

        Args:
            entry: Skill entry under validation.

        Raises:
            SecurityAuthorizationError: If blocked pattern is found.
        """
        for relative in _preflight_files(entry):
            absolute = (entry.path.parent / relative).resolve()
            text = absolute.read_text(encoding="utf-8")
            for signature, marker in self._PATTERNS:
                if marker in text:
                    raise SecurityAuthorizationError(
                        code="security_preflight_denied",
                        message=(
                            "Security alert: plugin preflight denied due to blocked "
                            f"pattern '{signature}'."
                        ),
                        data={
                            "skill": entry.name,
                            "signature": signature,
                            "path": relative,
                        },
                    )


class SecurityApprovalStore:
    """SQLite persistence for skill approvals and provenance records."""

    def __init__(self, *, sqlite_path: Path) -> None:
        """Create approval/provenance store.

        Args:
            sqlite_path: SQLite file path.
        """
        self._sqlite_path = sqlite_path
        self._init_schema()

    def lookup_mode(
        self,
        *,
        agent_id: str,
        skill_name: str,
        security_hash: str,
    ) -> ApprovalDecision | None:
        """Resolve cached approval mode for current key.

        Args:
            agent_id: Active agent id.
            skill_name: Skill name.
            security_hash: Security hash.

        Returns:
            Cached approval decision, or None.
        """
        query = (
            "SELECT mode FROM approvals WHERE agent_id=? AND skill_name=? AND "
            "security_hash=?"
        )
        with self._open_connection() as conn:
            row = conn.execute(query, (agent_id, skill_name, security_hash)).fetchone()
        if row is None:
            return None
        return ApprovalDecision(row[0])

    def upsert_mode(
        self,
        *,
        agent_id: str,
        skill_name: str,
        security_hash: str,
        mode: ApprovalDecision,
    ) -> None:
        """Persist approval mode for current key.

        Args:
            agent_id: Active agent id.
            skill_name: Skill name.
            security_hash: Security hash.
            mode: Approval mode.
        """
        now = _utc_iso()
        sql = (
            "INSERT INTO approvals(agent_id, skill_name, security_hash, mode, "
            "created_at, updated_at) VALUES(?,?,?,?,?,?) "
            "ON CONFLICT(agent_id, skill_name, security_hash) DO UPDATE SET "
            "mode=excluded.mode, updated_at=excluded.updated_at"
        )
        with self._open_connection() as conn:
            conn.execute(
                sql,
                (agent_id, skill_name, security_hash, mode.value, now, now),
            )

    def has_other_hash_approval(
        self, *, agent_id: str, skill_name: str, security_hash: str
    ) -> bool:
        """Check whether prior approval exists for another hash value.

        Args:
            agent_id: Active agent id.
            skill_name: Skill name.
            security_hash: Current security hash.

        Returns:
            True when prior approval exists for same agent+skill but different hash.
        """
        sql = (
            "SELECT 1 FROM approvals WHERE agent_id=? AND skill_name=? "
            "AND security_hash<>? LIMIT 1"
        )
        with self._open_connection() as conn:
            row = conn.execute(sql, (agent_id, skill_name, security_hash)).fetchone()
        return row is not None

    def record_provenance(
        self,
        *,
        agent_id: str,
        skill_name: str,
        security_hash: str,
        outcome: str,
        details: dict[str, object],
    ) -> None:
        """Persist one provenance receipt row.

        Args:
            agent_id: Active agent id.
            skill_name: Skill name.
            security_hash: Security hash.
            outcome: Deterministic outcome code.
            details: Structured provenance data.
        """
        sql = (
            "INSERT INTO provenance(created_at, agent_id, skill_name, security_hash, "
            "outcome, details_json) VALUES(?,?,?,?,?,?)"
        )
        with self._open_connection() as conn:
            conn.execute(
                sql,
                (
                    _utc_iso(),
                    agent_id,
                    skill_name,
                    security_hash,
                    outcome,
                    json.dumps(details, sort_keys=True),
                ),
            )

    def _init_schema(self) -> None:
        """Initialize SQLite schema idempotently."""
        self._sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        with self._open_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS approvals (
                    agent_id TEXT NOT NULL,
                    skill_name TEXT NOT NULL,
                    security_hash TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (agent_id, skill_name, security_hash)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS provenance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    skill_name TEXT NOT NULL,
                    security_hash TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    details_json TEXT NOT NULL
                )
                """
            )

    @contextmanager
    def _open_connection(self) -> Iterator[sqlite3.Connection]:
        """Open and close one sqlite connection safely.

        Yields:
            Open sqlite connection.
        """
        conn = sqlite3.connect(self._sqlite_path)
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            yield conn
            conn.commit()
        finally:
            conn.close()


class SecurityGate:
    """Approval + preflight gate for plugin skill execution."""

    def __init__(
        self,
        *,
        hash_service: SecurityHashService,
        preflight: SecurityPreflightScanner,
        store: SecurityApprovalStore,
        prompt: SecurityPrompt | None,
        sandbox: SkillSandboxSettings,
    ) -> None:
        """Create deterministic security-gate coordinator.

        Args:
            hash_service: Security-hash service.
            preflight: Hard-deny preflight scanner.
            store: Approval/provenance persistence store.
            prompt: Optional terminal approval prompt adapter.
            sandbox: Global sandbox settings.
        """
        self._hash_service = hash_service
        self._preflight = preflight
        self._store = store
        self._prompt = prompt
        self._sandbox = sandbox

    def authorize(
        self, *, entry: SkillEntry, agent_id: str
    ) -> tuple[str, dict[str, object]]:
        """Authorize plugin execution for one skill invocation.

        Args:
            entry: Skill entry.
            agent_id: Active agent id.

        Returns:
            Security hash and canonical payload details.

        Raises:
            SecurityAuthorizationError: On deny/approval failure.
        """
        security_hash, payload = self._hash_service.compute(entry)
        self._preflight.scan(entry)

        write_access = entry.plugin.write_access
        mode = self._store.lookup_mode(
            agent_id=agent_id,
            skill_name=entry.name,
            security_hash=security_hash,
        )
        if mode == ApprovalDecision.ALWAYS_ALLOW and not write_access:
            return security_hash, payload

        hash_changed = self._store.has_other_hash_approval(
            agent_id=agent_id,
            skill_name=entry.name,
            security_hash=security_hash,
        )
        if self._sandbox.hitl_default_on:
            decision = self._request_decision(
                agent_id=agent_id,
                skill_name=entry.name,
                security_hash=security_hash,
                write_access=write_access,
                hash_changed=hash_changed,
            )
            if decision == ApprovalDecision.DENY:
                raise SecurityAuthorizationError(
                    code="approval_denied",
                    message="Security alert: execution denied by operator approval.",
                    data={"skill": entry.name, "security_hash": security_hash},
                )
            if decision == ApprovalDecision.ALWAYS_ALLOW and not write_access:
                try:
                    self._store.upsert_mode(
                        agent_id=agent_id,
                        skill_name=entry.name,
                        security_hash=security_hash,
                        mode=ApprovalDecision.ALWAYS_ALLOW,
                    )
                except sqlite3.Error as exc:
                    raise SecurityAuthorizationError(
                        code="approval_persist_failed",
                        message="Error: failed to persist security approval.",
                        data={"skill": entry.name},
                    ) from exc
            return security_hash, payload

        raise SecurityAuthorizationError(
            code="approval_required",
            message="Security alert: approval is required before execution.",
            data={
                "skill": entry.name,
                "security_hash": security_hash,
                "hash_changed": hash_changed,
            },
        )

    def record_outcome(
        self,
        *,
        entry: SkillEntry,
        agent_id: str,
        security_hash: str,
        outcome: str,
        details: dict[str, object],
    ) -> None:
        """Persist provenance outcome; errors are surfaced deterministically.

        Args:
            entry: Skill entry.
            agent_id: Active agent id.
            security_hash: Security hash.
            outcome: Deterministic outcome code.
            details: Structured metadata.

        Raises:
            SecurityAuthorizationError: If provenance persistence fails.
        """
        try:
            self._store.record_provenance(
                agent_id=agent_id,
                skill_name=entry.name,
                security_hash=security_hash,
                outcome=outcome,
                details=details,
            )
        except sqlite3.Error as exc:
            raise SecurityAuthorizationError(
                code="approval_persist_failed",
                message="Error: failed to persist security provenance record.",
                data={"skill": entry.name},
            ) from exc

    def _request_decision(
        self,
        *,
        agent_id: str,
        skill_name: str,
        security_hash: str,
        write_access: bool,
        hash_changed: bool,
    ) -> ApprovalDecision:
        """Resolve approval decision from terminal prompt.

        Args:
            agent_id: Active agent id.
            skill_name: Skill name.
            security_hash: Security hash.
            write_access: Whether skill requests write access.
            hash_changed: Whether prior approval exists for different hash.

        Returns:
            Chosen decision.

        Raises:
            SecurityAuthorizationError: If prompt is unavailable or no decision exists.
        """
        if self._prompt is None:
            raise SecurityAuthorizationError(
                code="security_hash_mismatch" if hash_changed else "approval_required",
                message=(
                    "Security alert: prior approval hash is invalid and terminal "
                    "approval is required."
                    if hash_changed
                    else "Security alert: terminal approval prompt is unavailable."
                ),
                data={"skill": skill_name, "security_hash": security_hash},
            )
        decision = self._prompt.request_approval(
            ApprovalRequest(
                agent_id=agent_id,
                skill_name=skill_name,
                security_hash=security_hash,
                write_access=write_access,
                hash_changed=hash_changed,
            )
        )
        if decision is None:
            raise SecurityAuthorizationError(
                code="approval_required",
                message="Security alert: approval decision was not provided.",
                data={"skill": skill_name},
            )
        return decision


def _sha256_bytes(data: bytes) -> str:
    """Compute SHA-256 hex digest from bytes.

    Args:
        data: Input byte payload.

    Returns:
        Hex digest string.
    """
    return hashlib.sha256(data).hexdigest()


def _preflight_files(entry: SkillEntry) -> Sequence[str]:
    """Return plugin files that should be scanned for denied signatures.

    Args:
        entry: Skill entry under preflight validation.

    Returns:
        Ordered plugin file paths to scan.
    """
    values = {
        *(entry.plugin.source_files),
        entry.plugin.entrypoint or "",
    }
    return tuple(sorted(value for value in values if value))


def _utc_iso() -> str:
    """Return UTC ISO8601 timestamp without microseconds.

    Returns:
        Timestamp string in UTC.
    """
    return datetime.now(UTC).replace(microsecond=0).isoformat()
