"""Skill snapshot loader pipeline."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from lily.skills.discover import SKILL_FILENAME, discover_candidates
from lily.skills.eligibility import (
    evaluate_metadata_eligibility,
    evaluate_tool_requirements,
)
from lily.skills.frontmatter import parse_skill_markdown
from lily.skills.precedence import resolve_precedence
from lily.skills.types import (
    EligibilityContext,
    SkillCandidate,
    SkillDiagnostic,
    SkillEntry,
    SkillMetadata,
    SkillSnapshot,
    SkillSource,
)

_COMMAND_RE = re.compile(r"^[a-z0-9_-]+$")


class SkillSnapshotRequest(BaseModel):
    """Inputs required to build a deterministic skill snapshot."""

    model_config = ConfigDict(extra="forbid")

    bundled_dir: Path
    workspace_dir: Path
    user_dir: Path | None = None
    reserved_commands: set[str] = Field(default_factory=set)
    available_tools: set[str] | None = None
    platform: str | None = None
    env: dict[str, str] | None = None


def _assert_required_root(root: Path, label: str) -> None:
    """Ensure a required source root exists and is readable.

    Args:
        root: Filesystem path for a required skill root.
        label: Human-friendly source label for error messages.

    Raises:
        RuntimeError: If the root is missing or not a directory.
    """
    if not root.exists():
        raise RuntimeError(f"Required skills root missing: {label} ({root})")
    if not root.is_dir():
        raise RuntimeError(f"Required skills root is not a directory: {label} ({root})")


def _make_context(
    platform: str | None,
    env: dict[str, str] | None,
    available_tools: set[str] | None,
) -> EligibilityContext:
    """Build eligibility context with deterministic defaults.

    Args:
        platform: Optional platform override.
        env: Optional environment mapping override.
        available_tools: Optional set of allowed tools.

    Returns:
        Normalized eligibility context.
    """
    runtime_platform = platform if platform is not None else sys.platform
    runtime_env = env if env is not None else dict(os.environ)
    return EligibilityContext(
        platform=runtime_platform,
        env=runtime_env,
        available_tools=available_tools,
    )


def _read_skill_metadata(
    skill_dir: Path,
) -> tuple[SkillMetadata | None, str, str | None]:
    """Read and parse skill markdown metadata/body.

    Args:
        skill_dir: Directory containing ``SKILL.md``.

    Returns:
        A tuple of metadata (if parsed), body text, and optional error string.
    """
    skill_path = skill_dir / SKILL_FILENAME
    try:
        raw = skill_path.read_text(encoding="utf-8")
    except OSError as exc:
        return None, "", f"Failed reading SKILL.md: {exc}"

    try:
        metadata, body = parse_skill_markdown(raw, skill_path=skill_path)
        return metadata, body, None
    except ValueError as exc:
        return None, "", str(exc)


def _is_command_valid(command: str) -> bool:
    """Return True when command alias matches the v0 command regex.

    Args:
        command: Candidate command alias.

    Returns:
        Whether the command alias matches the allowed pattern.
    """
    return _COMMAND_RE.fullmatch(command) is not None


def _hash_snapshot(
    entries: tuple[SkillEntry, ...], diagnostics: tuple[SkillDiagnostic, ...]
) -> str:
    """Create deterministic snapshot version hash.

    Args:
        entries: Resolved entries included in the snapshot.
        diagnostics: Diagnostics emitted by the loader pipeline.

    Returns:
        Stable short hash for the snapshot payload.
    """
    payload = {
        "skills": [
            {
                "name": entry.name,
                "source": entry.source.value,
                "path": entry.path.as_posix(),
                "summary": entry.summary,
                "instructions": entry.instructions,
                "invocation_mode": entry.invocation_mode.value,
                "command": entry.command,
                "command_tool": entry.command_tool,
                "requires_tools": list(entry.requires_tools),
                "capabilities": {
                    "declared_tools": list(entry.capabilities.declared_tools),
                },
                "capabilities_declared": entry.capabilities_declared,
                "eligibility": {
                    "os": list(entry.eligibility.os),
                    "env": list(entry.eligibility.env),
                    "binaries": list(entry.eligibility.binaries),
                },
            }
            for entry in entries
        ],
        "diagnostics": [
            {
                "skill_name": diag.skill_name,
                "code": diag.code,
                "message": diag.message,
                "source": diag.source.value if diag.source else None,
                "path": diag.path.as_posix() if diag.path else None,
            }
            for diag in diagnostics
        ],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]


def _discover_all_candidates(
    request: SkillSnapshotRequest,
) -> tuple[list[SkillCandidate], list[SkillDiagnostic]]:
    """Discover candidates from bundled/workspace/user roots.

    Args:
        request: Snapshot build request with root locations.

    Returns:
        A tuple of discovered candidates and discovery diagnostics.
    """
    all_candidates: list[SkillCandidate] = []
    diagnostics: list[SkillDiagnostic] = []

    bundled_candidates, bundled_diags = discover_candidates(
        request.bundled_dir, SkillSource.BUNDLED
    )
    all_candidates.extend(bundled_candidates)
    diagnostics.extend(bundled_diags)

    if (
        request.user_dir is not None
        and request.user_dir.exists()
        and request.user_dir.is_dir()
    ):
        user_candidates, user_diags = discover_candidates(
            request.user_dir, SkillSource.USER
        )
        all_candidates.extend(user_candidates)
        diagnostics.extend(user_diags)

    workspace_candidates, workspace_diags = discover_candidates(
        request.workspace_dir, SkillSource.WORKSPACE
    )
    all_candidates.extend(workspace_candidates)
    diagnostics.extend(workspace_diags)
    return all_candidates, diagnostics


def _validate_command_alias(
    candidate: SkillCandidate, metadata: SkillMetadata, normalized_reserved: set[str]
) -> SkillDiagnostic | None:
    """Validate command alias syntax and collision rules.

    Args:
        candidate: Candidate skill for diagnostics context.
        metadata: Parsed metadata containing command alias fields.
        normalized_reserved: Lowercased reserved command names.

    Returns:
        A diagnostic on failure, or ``None`` when command alias is valid.
    """
    if not metadata.command:
        return None

    command = metadata.command
    command_lower = command.lower()
    if not _is_command_valid(command):
        return SkillDiagnostic(
            skill_name=candidate.name,
            code="invalid_command_alias",
            message=f"Invalid command alias: {command}",
            source=candidate.source,
            path=candidate.path,
        )
    if command_lower in normalized_reserved:
        return SkillDiagnostic(
            skill_name=candidate.name,
            code="command_alias_collision",
            message=f"Command alias collides with reserved command: {command}",
            source=candidate.source,
            path=candidate.path,
        )
    return None


def _resolve_candidate(
    candidate: SkillCandidate,
    context: EligibilityContext,
    normalized_reserved: set[str],
) -> tuple[SkillEntry | None, tuple[SkillDiagnostic, ...]]:
    """Resolve one precedence winner into a usable snapshot entry.

    Args:
        candidate: Candidate selected by precedence resolution.
        context: Runtime context used for eligibility checks.
        normalized_reserved: Lowercased reserved command names.

    Returns:
        A tuple of optional resolved entry and diagnostics for this candidate.
    """
    metadata, body, parse_error = _read_skill_metadata(candidate.path)
    if parse_error:
        return None, (
            SkillDiagnostic(
                skill_name=candidate.name,
                code="malformed_frontmatter",
                message=parse_error,
                source=candidate.source,
                path=candidate.path,
            ),
        )

    assert metadata is not None  # Narrowed by parse_error check.

    command_diag = _validate_command_alias(candidate, metadata, normalized_reserved)
    if command_diag is not None:
        return None, (command_diag,)

    eligible, reasons = evaluate_metadata_eligibility(metadata, context)
    if not eligible:
        return None, (
            SkillDiagnostic(
                skill_name=candidate.name,
                code="ineligible",
                message="; ".join(reasons),
                source=candidate.source,
                path=candidate.path,
            ),
        )

    entry = SkillEntry(
        name=candidate.name,
        source=candidate.source,
        path=(candidate.path / SKILL_FILENAME).resolve(),
        summary=metadata.summary,
        instructions=body.strip(),
        invocation_mode=metadata.invocation_mode,
        command=metadata.command,
        command_tool=metadata.command_tool,
        requires_tools=metadata.requires_tools,
        capabilities=metadata.capabilities.model_copy(
            update={
                # Legacy skills without explicit capabilities are migrated
                # with minimal declaration for their command tool.
                "declared_tools": (
                    metadata.capabilities.declared_tools
                    if metadata.capabilities_declared
                    else tuple(
                        sorted(
                            {
                                *(metadata.capabilities.declared_tools),
                                *metadata.requires_tools,
                                *(
                                    (metadata.command_tool,)
                                    if metadata.command_tool is not None
                                    else ()
                                ),
                            }
                        )
                    )
                )
            }
        ),
        capabilities_declared=metadata.capabilities_declared,
        eligibility=metadata.eligibility,
    )

    tools_ok, tool_reasons = evaluate_tool_requirements(entry, context)
    if not tools_ok:
        return None, (
            SkillDiagnostic(
                skill_name=candidate.name,
                code="missing_required_tools",
                message="; ".join(tool_reasons),
                source=candidate.source,
                path=candidate.path,
            ),
        )
    return entry, ()


def build_skill_snapshot(request: SkillSnapshotRequest) -> SkillSnapshot:
    """Build a deterministic skill snapshot for the current session.

    Args:
        request: Snapshot build request.

    Returns:
        Deterministic skill snapshot used by a session.
    """
    _assert_required_root(request.bundled_dir, "bundled")
    _assert_required_root(request.workspace_dir, "workspace")

    context = _make_context(
        platform=request.platform,
        env=request.env,
        available_tools=request.available_tools,
    )
    normalized_reserved = {name.lower() for name in request.reserved_commands}

    all_candidates, diagnostics = _discover_all_candidates(request)
    winners, precedence_diags = resolve_precedence(tuple(all_candidates))
    diagnostics.extend(precedence_diags)

    resolved_entries: list[SkillEntry] = []
    for candidate in winners:
        entry, candidate_diags = _resolve_candidate(
            candidate, context, normalized_reserved
        )
        diagnostics.extend(candidate_diags)
        if entry is not None:
            resolved_entries.append(entry)

    sorted_entries = tuple(sorted(resolved_entries, key=lambda entry: entry.name))
    sorted_diagnostics = tuple(
        sorted(
            diagnostics,
            key=lambda diag: (
                diag.skill_name,
                diag.code,
                str(diag.path) if diag.path else "",
            ),
        ),
    )

    version = _hash_snapshot(sorted_entries, sorted_diagnostics)
    return SkillSnapshot(
        version=version, skills=sorted_entries, diagnostics=sorted_diagnostics
    )
