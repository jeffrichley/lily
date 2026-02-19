"""Unit tests for council blueprint compile and execution paths."""

from __future__ import annotations

from pydantic import BaseModel

from lily.blueprints import (
    BlueprintError,
    BlueprintErrorCode,
    BlueprintRunStatus,
    CouncilBindingModel,
    CouncilBlueprint,
    CouncilFinding,
    CouncilInputModel,
    CouncilSpecialistReport,
    CouncilSpecialistStatus,
)


class _SecuritySpecialist:
    """Specialist fixture that returns one deterministic finding."""

    def __init__(self, *, specialist_id: str, confidence: float) -> None:
        """Store fixture id and confidence value."""
        self._specialist_id = specialist_id
        self._confidence = confidence

    def run(self, request: CouncilInputModel) -> CouncilSpecialistReport:
        """Return deterministic specialist report payload."""
        return CouncilSpecialistReport(
            specialist_id=self._specialist_id,
            status=CouncilSpecialistStatus.OK,
            findings=(
                CouncilFinding(
                    title=f"{self._specialist_id} finding",
                    recommendation=f"review {request.topic}",
                    confidence=self._confidence,
                    source_specialist=self._specialist_id,
                ),
            ),
            notes="ok",
        )


class _FailingSpecialist:
    """Specialist fixture that raises to test containment."""

    def run(self, request: CouncilInputModel) -> CouncilSpecialistReport:
        """Raise deterministic error."""
        del request
        raise RuntimeError("boom")


def _bindings() -> BaseModel:
    """Return typed bindings fixture."""
    return CouncilBindingModel(
        specialists=("offense.v1", "defense.v1"),
        synthesizer="default.v1",
        max_findings=5,
    )


def test_council_compile_and_execute_returns_deterministic_envelope() -> None:
    """Council blueprint should compile and execute map/reduce deterministically."""
    blueprint = CouncilBlueprint(
        specialists={
            "offense.v1": _SecuritySpecialist(
                specialist_id="offense.v1",
                confidence=0.9,
            ),
            "defense.v1": _SecuritySpecialist(
                specialist_id="defense.v1",
                confidence=0.7,
            ),
        }
    )

    compiled = blueprint.compile(_bindings())
    result = compiled.invoke({"topic": "service perimeter", "context": ("api",)})

    assert result.status == BlueprintRunStatus.OK
    assert result.artifacts == ("summary.md", "events.jsonl")
    assert result.approvals_requested == ()
    assert result.references == ("offense.v1", "defense.v1")
    assert result.payload["topic"] == "service perimeter"
    findings = result.payload["ranked_findings"]
    assert isinstance(findings, list)
    assert findings[0]["source_specialist"] == "offense.v1"
    assert findings[1]["source_specialist"] == "defense.v1"


def test_council_compile_fails_with_unresolved_specialist() -> None:
    """Compile should fail deterministically when specialist id is unresolved."""
    blueprint = CouncilBlueprint(
        specialists={
            "offense.v1": _SecuritySpecialist(
                specialist_id="offense.v1",
                confidence=0.9,
            )
        }
    )
    bindings = CouncilBindingModel(
        specialists=("offense.v1", "missing.v1"),
        synthesizer="default.v1",
        max_findings=5,
    )

    try:
        blueprint.compile(bindings)
    except BlueprintError as exc:
        assert exc.code == BlueprintErrorCode.COMPILE_FAILED
        assert str(exc) == (
            "Error: council compile failed due to unresolved specialists."
        )
        assert exc.data["unresolved_specialists"] == ("missing.v1",)
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("Expected BlueprintError for unresolved specialist.")


def test_council_execution_contains_specialist_failure() -> None:
    """Specialist failure should be contained and surfaced in output payload."""
    blueprint = CouncilBlueprint(
        specialists={
            "offense.v1": _SecuritySpecialist(
                specialist_id="offense.v1",
                confidence=0.9,
            ),
            "defense.v1": _FailingSpecialist(),
        }
    )
    bindings = CouncilBindingModel(
        specialists=("offense.v1", "defense.v1"),
        synthesizer="default.v1",
        max_findings=5,
    )
    compiled = blueprint.compile(bindings)

    result = compiled.invoke({"topic": "cloud perimeter"})

    assert result.status == BlueprintRunStatus.OK
    assert result.payload["failed_specialists"] == ["defense.v1"]
    findings = result.payload["ranked_findings"]
    assert isinstance(findings, list)
    assert len(findings) == 1
    assert findings[0]["source_specialist"] == "offense.v1"


def test_council_execution_invalid_input_maps_to_execution_failed() -> None:
    """Invalid execution input should map to deterministic execution-failed code."""
    blueprint = CouncilBlueprint(
        specialists={
            "offense.v1": _SecuritySpecialist(
                specialist_id="offense.v1",
                confidence=0.9,
            ),
            "defense.v1": _SecuritySpecialist(
                specialist_id="defense.v1",
                confidence=0.7,
            ),
        }
    )
    compiled = blueprint.compile(_bindings())
    try:
        compiled.invoke({"context": ("missing topic",)})
    except BlueprintError as exc:
        assert exc.code == BlueprintErrorCode.EXECUTION_FAILED
        assert str(exc) == "Error: council execution input is invalid."
        assert exc.data["blueprint"] == "council.v1"
        assert exc.data["validation_errors"]
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("Expected BlueprintError for invalid execution input.")
