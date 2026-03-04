"""Deterministic resolver for executable target binding."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from lily.runtime.executables.models import (
    ExecutableKind,
    ExecutableRef,
    ExecutableRequest,
)


@dataclass(frozen=True)
class ResolverBindingError(RuntimeError):
    """Deterministic resolver failure with machine-readable code."""

    code: str
    message: str
    data: dict[str, object]

    def __str__(self) -> str:
        """Return human-readable resolver error message."""
        return self.message


class ExecutableCatalogResolver:
    """Resolve executable targets from an in-memory deterministic catalog."""

    def __init__(self, catalog: Iterable[ExecutableRef]) -> None:
        """Store deterministic catalog snapshot for resolution decisions.

        Args:
            catalog: Candidate executable references from runtime registration.
        """
        self._catalog = tuple(catalog)

    def resolve(self, request: ExecutableRequest) -> ExecutableRef:
        """Resolve one request target to exactly one executable reference.

        Args:
            request: Canonical executable request to resolve.

        Returns:
            One resolved executable reference.

        Raises:
            ResolverBindingError: If target is unresolved or ambiguous.
        """
        target_id = request.target.executable_id
        kind_hint = request.target.executable_kind
        id_matches = [
            entry for entry in self._catalog if entry.executable_id == target_id
        ]

        if not id_matches:
            raise ResolverBindingError(
                code="resolver_unresolved",
                message=f"Error: executable '{target_id}' could not be resolved.",
                data={
                    "target_id": target_id,
                    "kind_hint": kind_hint.value if kind_hint else None,
                    "objective": request.objective,
                },
            )

        candidates = self._apply_kind_hint(id_matches, kind_hint)
        if not candidates:
            raise ResolverBindingError(
                code="resolver_unresolved",
                message=(
                    f"Error: executable '{target_id}' was found but no candidate "
                    "matched requested executable_kind."
                ),
                data={
                    "target_id": target_id,
                    "kind_hint": kind_hint.value if kind_hint else None,
                    "candidate_kinds": sorted(
                        {
                            entry.executable_kind.value
                            for entry in id_matches
                            if entry.executable_kind is not None
                        }
                    ),
                },
            )

        if len(candidates) > 1:
            raise ResolverBindingError(
                code="resolver_ambiguous",
                message=(
                    f"Error: executable '{target_id}' is ambiguous in resolver scope."
                ),
                data={
                    "target_id": target_id,
                    "kind_hint": kind_hint.value if kind_hint else None,
                    "candidate_count": len(candidates),
                    "candidate_kinds": sorted(
                        {
                            entry.executable_kind.value
                            for entry in candidates
                            if entry.executable_kind is not None
                        }
                    ),
                },
            )
        return candidates[0]

    @staticmethod
    def _apply_kind_hint(
        candidates: list[ExecutableRef],
        kind_hint: ExecutableKind | None,
    ) -> list[ExecutableRef]:
        """Filter candidates by kind hint while preserving deterministic order.

        Args:
            candidates: Id-matched executable references.
            kind_hint: Optional executable kind hint from request.

        Returns:
            Ordered candidate list after kind filtering.
        """
        if kind_hint is None:
            return candidates
        return [entry for entry in candidates if entry.executable_kind == kind_hint]
