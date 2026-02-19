"""Default blueprint registry wiring for runtime facade."""

from __future__ import annotations

from typing import cast

from lily.blueprints.council import (
    CouncilBlueprint,
    CouncilFinding,
    CouncilInputModel,
    CouncilSpecialistReport,
    CouncilSpecialistStatus,
)
from lily.blueprints.models import Blueprint
from lily.blueprints.registry import BlueprintRegistry


class _SecuritySpecialist:
    """Deterministic specialist for security-oriented council runs."""

    def run(self, request: CouncilInputModel) -> CouncilSpecialistReport:
        """Return one deterministic security finding.

        Args:
            request: Council topic input.

        Returns:
            Deterministic specialist report payload.
        """
        return CouncilSpecialistReport(
            specialist_id="security.v1",
            status=CouncilSpecialistStatus.OK,
            findings=(
                CouncilFinding(
                    title="Security control gap review",
                    recommendation=f"Validate authz boundaries for {request.topic}.",
                    confidence=0.82,
                    source_specialist="security.v1",
                ),
            ),
            notes="deterministic-default",
        )


class _OperationsSpecialist:
    """Deterministic specialist for operations-oriented council runs."""

    def run(self, request: CouncilInputModel) -> CouncilSpecialistReport:
        """Return one deterministic operations finding.

        Args:
            request: Council topic input.

        Returns:
            Deterministic specialist report payload.
        """
        return CouncilSpecialistReport(
            specialist_id="operations.v1",
            status=CouncilSpecialistStatus.OK,
            findings=(
                CouncilFinding(
                    title="Operational hardening checkpoint",
                    recommendation=(
                        f"Define runbook and SLO checks for {request.topic}."
                    ),
                    confidence=0.74,
                    source_specialist="operations.v1",
                ),
            ),
            notes="deterministic-default",
        )


def build_default_blueprint_registry() -> BlueprintRegistry:
    """Build default runtime blueprint registry.

    Returns:
        Registry containing built-in blueprint implementations.
    """
    council = CouncilBlueprint(
        specialists={
            "security.v1": _SecuritySpecialist(),
            "operations.v1": _OperationsSpecialist(),
        }
    )
    return BlueprintRegistry(blueprints=cast(tuple[Blueprint, ...], (council,)))
