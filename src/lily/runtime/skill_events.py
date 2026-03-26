"""Typed skill telemetry events (PRD F7) with JSON-safe serialization and redaction.

PRD F7 names map to **retrieval-only MVP** semantics:

- ``skill_discovered``: A skill package was seen during discovery/registry merge
  (``discovered``, ``shadowed``, or ``skipped_invalid`` from ``SkillDiscoveryEvent``).
- ``skill_selected``: The model requested content via ``skill_retrieve`` (retrieval
  request) — corresponds to "selection" before load.
- ``skill_loaded``: A file read completed under policy (``SKILL.md`` or bounded
  reference path); payload includes **length only**, never file contents.
- ``skill_executed``: Retrieval returned successfully to the tool caller (content
  applied to the agent context for this turn) — success path after load.
- ``skill_failed``: Discovery parse skip, policy denial, missing file, or I/O error;
  includes sanitized rationale, never raw skill bodies.

Extension (not in the original F7 short list; used for system-prompt observability):

- ``skill_catalog_injected``: Summaries-only catalog block was appended to the
  system prompt; includes skill count and **character length** of the catalog
  markdown, not the text itself.

Event records are emitted as single-line JSON on logger ``lily.skill.telemetry``
at INFO for downstream sinks; they are **not** a substitute for ``SkillInvokeTrace``.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from lily.runtime.skill_discovery import SkillDiscoveryEvent

SKILL_EVENT_SCHEMA_VERSION = "1"

_LOGGER = logging.getLogger("lily.skill.telemetry")

SkillLoadKind = Literal["skill_md", "reference"]
SkillFailurePhase = Literal["discovery", "retrieval", "load", "unknown"]


def sanitize_telemetry_detail(text: str | None, *, max_len: int = 512) -> str | None:
    """Truncate free-form error or skip text so logs stay bounded.

    Args:
        text: Raw detail string, or ``None``.
        max_len: Maximum UTF-8 character length to retain.

    Returns:
        Truncated string, ``None`` when input is ``None``, or ``"[empty]"`` for
        empty string after strip.
    """
    if text is None:
        return None
    stripped = text.strip()
    if not stripped:
        return "[empty]"
    if len(stripped) <= max_len:
        return stripped
    return f"{stripped[:max_len]}…"


def _path_for_telemetry(path: Path) -> str:
    """Serialize a path for telemetry (no home-dir collapse; stable for tests).

    Args:
        path: Filesystem path to stringify.

    Returns:
        Resolved path string when possible, otherwise ``str(path)``.
    """
    try:
        return str(path.resolve())
    except OSError:
        return str(path)


class SkillDiscoveredPayload(BaseModel):
    """Payload for ``skill_discovered``."""

    model_config = ConfigDict(frozen=True)

    discovery_kind: Literal["discovered", "shadowed", "skipped_invalid"] = Field(
        ...,
        description="Mirrors ``SkillDiscoveryEvent.kind``.",
    )
    canonical_key: str = Field(
        default="",
        description="Normalized key when known; empty for some invalid packages.",
    )
    scope: str = Field(default="", description="Config scope name for the path.")
    path: str = Field(..., description="Filesystem path associated with the event.")
    detail: str | None = Field(
        default=None,
        description="Sanitized skip/parse detail for skipped_invalid only.",
    )
    superseded_by: str | None = Field(
        default=None,
        description="Winner path when discovery_kind is shadowed.",
    )


class SkillSelectedPayload(BaseModel):
    """Payload for ``skill_selected`` (retrieval request)."""

    model_config = ConfigDict(frozen=True)

    requested_name: str = Field(..., description="Name argument to skill_retrieve.")
    reference_subpath: str | None = Field(
        default=None,
        description="Optional relative path under the skill package.",
    )


class SkillLoadedPayload(BaseModel):
    """Payload for ``skill_loaded`` (file read succeeded)."""

    model_config = ConfigDict(frozen=True)

    canonical_key: str = Field(..., description="Registry key for the skill.")
    load_kind: SkillLoadKind = Field(
        ...,
        description="Whether SKILL.md or a reference file was read.",
    )
    relative_path: str | None = Field(
        default=None,
        description="Relative path for reference loads; SKILL.md for primary load.",
    )
    content_length: int = Field(
        ...,
        ge=0,
        description="UTF-8 byte length of returned text (not the text itself).",
    )


class SkillExecutedPayload(BaseModel):
    """Payload for ``skill_executed`` (retrieval returned to caller)."""

    model_config = ConfigDict(frozen=True)

    requested_name: str = Field(..., description="Name passed to skill_retrieve.")
    canonical_key: str | None = Field(
        default=None,
        description="Resolved key when lookup succeeded before load.",
    )
    reference_subpath: str | None = Field(
        default=None,
        description="Optional reference path when provided.",
    )
    result_length: int = Field(
        ...,
        ge=0,
        description="Length of string returned to the model (not the string itself).",
    )


class SkillFailedPayload(BaseModel):
    """Payload for ``skill_failed``."""

    model_config = ConfigDict(frozen=True)

    phase: SkillFailurePhase = Field(
        ...,
        description="Which subsystem reported the failure.",
    )
    error_kind: str = Field(
        ...,
        description="Short classifier, e.g. ``not_found``, ``denied``, ``reference``.",
    )
    detail: str | None = Field(
        default=None,
        description="Sanitized human-readable reason (bounded length).",
    )


class SkillCatalogInjectedPayload(BaseModel):
    """Payload for ``skill_catalog_injected`` (summaries block in system prompt)."""

    model_config = ConfigDict(frozen=True)

    skills_count: int = Field(..., ge=0, description="Number of indexed skills.")
    catalog_char_count: int = Field(
        ...,
        ge=0,
        description="Character length of appended catalog markdown (not the text).",
    )


def emit_skill_event(event: str, payload: BaseModel) -> None:
    """Serialize one telemetry envelope and log at INFO as a single JSON line.

    Args:
        event: Event name (for example ``skill_selected``).
        payload: Validated Pydantic payload model.
    """
    envelope: dict[str, object] = {
        "schema_version": SKILL_EVENT_SCHEMA_VERSION,
        "event": event,
        "payload": payload.model_dump(mode="json"),
    }
    _LOGGER.info("%s", json.dumps(envelope, sort_keys=True))


def emit_skill_discovery_events(events: tuple[SkillDiscoveryEvent, ...]) -> None:
    """Emit ``skill_discovered`` for each discovery/registry diagnostic event.

    Args:
        events: Discovery and merge events from filesystem walk and registry build.
    """
    for ev in events:
        detail = sanitize_telemetry_detail(ev.detail) if ev.detail else None
        superseded = (
            _path_for_telemetry(ev.superseded_by)
            if ev.superseded_by is not None
            else None
        )
        emit_skill_event(
            "skill_discovered",
            SkillDiscoveredPayload(
                discovery_kind=ev.kind,
                canonical_key=ev.canonical_key,
                scope=ev.scope,
                path=_path_for_telemetry(ev.path),
                detail=detail,
                superseded_by=superseded,
            ),
        )


def emit_skill_catalog_injected(*, skills_count: int, catalog_char_count: int) -> None:
    """Emit ``skill_catalog_injected`` when catalog markdown is appended to prompt.

    Args:
        skills_count: Number of skills in the merged registry.
        catalog_char_count: Length of the catalog markdown string (not its content).
    """
    emit_skill_event(
        "skill_catalog_injected",
        SkillCatalogInjectedPayload(
            skills_count=skills_count,
            catalog_char_count=catalog_char_count,
        ),
    )


def emit_skill_selected(*, requested_name: str, reference_subpath: str | None) -> None:
    """Emit ``skill_selected`` when ``skill_retrieve`` runs.

    Args:
        requested_name: Trimmed ``name`` argument from the tool call.
        reference_subpath: Optional relative path under the skill package.
    """
    emit_skill_event(
        "skill_selected",
        SkillSelectedPayload(
            requested_name=requested_name,
            reference_subpath=reference_subpath,
        ),
    )


def emit_skill_loaded(
    *,
    canonical_key: str,
    load_kind: SkillLoadKind,
    relative_path: str | None,
    content_length: int,
) -> None:
    """Emit ``skill_loaded`` after a successful file read.

    Args:
        canonical_key: Registry key for the skill.
        load_kind: Whether ``SKILL.md`` or a reference file was read.
        relative_path: Relative path for reference loads; ``SKILL.md`` for primary.
        content_length: UTF-8 length of the returned text (not the text itself).
    """
    emit_skill_event(
        "skill_loaded",
        SkillLoadedPayload(
            canonical_key=canonical_key,
            load_kind=load_kind,
            relative_path=relative_path,
            content_length=content_length,
        ),
    )


def emit_skill_executed(
    *,
    requested_name: str,
    canonical_key: str | None,
    reference_subpath: str | None,
    result_length: int,
) -> None:
    """Emit ``skill_executed`` when ``skill_retrieve`` returns content.

    Args:
        requested_name: Name passed to ``skill_retrieve``.
        canonical_key: Resolved key after lookup, when available.
        reference_subpath: Optional reference path from the tool call.
        result_length: Length of the string returned to the model.
    """
    emit_skill_event(
        "skill_executed",
        SkillExecutedPayload(
            requested_name=requested_name,
            canonical_key=canonical_key,
            reference_subpath=reference_subpath,
            result_length=result_length,
        ),
    )


def emit_skill_failed(
    *,
    phase: SkillFailurePhase,
    error_kind: str,
    detail: str | None,
) -> None:
    """Emit ``skill_failed`` for retrieval or discovery failures.

    Args:
        phase: Subsystem that produced the failure.
        error_kind: Short classifier for metrics and dashboards.
        detail: Optional sanitized human-readable reason.
    """
    emit_skill_event(
        "skill_failed",
        SkillFailedPayload(
            phase=phase,
            error_kind=error_kind,
            detail=sanitize_telemetry_detail(detail),
        ),
    )
