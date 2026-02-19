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
    CouncilSynthStrategy,
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


class _OperationsSpecialist:
    """Specialist fixture with a distinct implementation path."""

    def __init__(self, *, specialist_id: str, confidence: float) -> None:
        """Store fixture id and confidence value."""
        self._specialist_id = specialist_id
        self._confidence = confidence

    def run(self, request: CouncilInputModel) -> CouncilSpecialistReport:
        """Return deterministic specialist report payload with different wording."""
        return CouncilSpecialistReport(
            specialist_id=self._specialist_id,
            status=CouncilSpecialistStatus.OK,
            findings=(
                CouncilFinding(
                    title=f"{self._specialist_id} operations finding",
                    recommendation=f"operationalize controls for {request.topic}",
                    confidence=self._confidence,
                    source_specialist=self._specialist_id,
                ),
            ),
            notes="ops-review",
        )


class _FailingSpecialist:
    """Specialist fixture that raises to test containment."""

    def run(self, request: CouncilInputModel) -> CouncilSpecialistReport:
        """Raise deterministic error."""
        del request
        raise RuntimeError("boom")


class _Llmsynthesizer:
    """LLM synth fixture returning deterministic synthesized output."""

    def run(
        self,
        *,
        request: CouncilInputModel,
        reports: tuple[CouncilSpecialistReport, ...],
        max_findings: int,
    ) -> dict[str, object]:
        """Return typed-serializable payload in synthetic LLM style."""
        findings = [
            finding
            for report in reports
            for finding in report.findings
            if report.status == CouncilSpecialistStatus.OK
        ][:max_findings]
        return {
            "topic": request.topic,
            "summary": f"LLM synthesis for {request.topic}",
            "ranked_findings": [item.model_dump(mode="json") for item in findings],
            "participating_specialists": [report.specialist_id for report in reports],
            "failed_specialists": [
                report.specialist_id
                for report in reports
                if report.status == CouncilSpecialistStatus.ERROR
            ],
        }


class _FailingLlmsynthesizer:
    """LLM synth fixture that fails to trigger deterministic fallback."""

    def run(
        self,
        *,
        request: CouncilInputModel,
        reports: tuple[CouncilSpecialistReport, ...],
        max_findings: int,
    ) -> dict[str, object]:
        """Raise deterministic llm synthesis failure."""
        del request
        del reports
        del max_findings
        raise RuntimeError("llm unavailable")


class _FailingDeterministicSynthesizer:
    """Fallback synth fixture that fails to test deterministic error mapping."""

    def run(
        self,
        *,
        request: CouncilInputModel,
        reports: tuple[CouncilSpecialistReport, ...],
        max_findings: int,
    ) -> dict[str, object]:
        """Raise deterministic fallback failure."""
        del request
        del reports
        del max_findings
        raise RuntimeError("fallback failed")


def _bindings() -> BaseModel:
    """Return typed bindings fixture."""
    return CouncilBindingModel(
        specialists=("offense.v1", "defense.v1"),
        synthesizer="default.v1",
        synth_strategy=CouncilSynthStrategy.DETERMINISTIC,
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
            "defense.v1": _OperationsSpecialist(
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
    assert findings[1]["title"] == "defense.v1 operations finding"


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
        synth_strategy=CouncilSynthStrategy.DETERMINISTIC,
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
        synth_strategy=CouncilSynthStrategy.DETERMINISTIC,
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


def test_council_llm_strategy_uses_llm_synthesizer_when_configured() -> None:
    """LLM synth strategy should run selected llm synthesizer implementation."""
    blueprint = CouncilBlueprint(
        specialists={
            "offense.v1": _SecuritySpecialist(
                specialist_id="offense.v1",
                confidence=0.9,
            ),
            "defense.v1": _OperationsSpecialist(
                specialist_id="defense.v1",
                confidence=0.7,
            ),
        },
        llm_synthesizers={"llm.default.v1": _Llmsynthesizer()},
    )
    bindings = CouncilBindingModel(
        specialists=("offense.v1", "defense.v1"),
        synthesizer="llm.default.v1",
        synth_strategy=CouncilSynthStrategy.LLM,
        max_findings=5,
    )

    compiled = blueprint.compile(bindings)
    result = compiled.invoke({"topic": "network posture"})

    assert result.status == BlueprintRunStatus.OK
    assert result.payload["summary"] == "LLM synthesis for network posture"


def test_council_llm_strategy_falls_back_deterministically_on_failure() -> None:
    """LLM synthesis failure should fall back to deterministic synthesis output."""
    blueprint = CouncilBlueprint(
        specialists={
            "offense.v1": _SecuritySpecialist(
                specialist_id="offense.v1",
                confidence=0.9,
            ),
            "defense.v1": _OperationsSpecialist(
                specialist_id="defense.v1",
                confidence=0.7,
            ),
        },
        llm_synthesizers={"llm.default.v1": _FailingLlmsynthesizer()},
    )
    bindings = CouncilBindingModel(
        specialists=("offense.v1", "defense.v1"),
        synthesizer="llm.default.v1",
        synth_strategy=CouncilSynthStrategy.LLM_WITH_FALLBACK,
        max_findings=5,
    )

    compiled = blueprint.compile(bindings)
    result = compiled.invoke({"topic": "network posture"})

    assert result.status == BlueprintRunStatus.OK
    assert "[fallback: llm_synth_failed" in result.payload["summary"]
    assert result.payload["ranked_findings"]


def test_council_llm_strategy_maps_failure_when_fallback_also_fails() -> None:
    """LLM + fallback synthesis failure should map to deterministic synth code."""
    blueprint = CouncilBlueprint(
        specialists={
            "offense.v1": _SecuritySpecialist(
                specialist_id="offense.v1",
                confidence=0.9,
            ),
            "defense.v1": _OperationsSpecialist(
                specialist_id="defense.v1",
                confidence=0.7,
            ),
        },
        synthesizers={"default.v1": _FailingDeterministicSynthesizer()},
        llm_synthesizers={"llm.default.v1": _FailingLlmsynthesizer()},
    )
    bindings = CouncilBindingModel(
        specialists=("offense.v1", "defense.v1"),
        synthesizer="llm.default.v1",
        synth_strategy=CouncilSynthStrategy.LLM_WITH_FALLBACK,
        max_findings=5,
    )
    compiled = blueprint.compile(bindings)
    try:
        compiled.invoke({"topic": "network posture"})
    except BlueprintError as exc:
        assert exc.code == BlueprintErrorCode.EXECUTION_FAILED
        assert str(exc) == "Error: council synthesis failed."
        assert exc.data["synth_error_code"] == "llm_synth_fallback_failed"
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("Expected BlueprintError for failed llm synth fallback.")


def test_council_binding_default_strategy_is_llm() -> None:
    """Default council strategy should be strict LLM synthesis mode."""
    bindings = CouncilBindingModel(
        specialists=("offense.v1", "defense.v1"),
        synthesizer="llm.default.v1",
        max_findings=5,
    )

    assert bindings.synth_strategy == CouncilSynthStrategy.LLM


def test_council_llm_maps_primary_failure_without_fallback() -> None:
    """Default llm strategy should fail deterministically without fallback."""
    blueprint = CouncilBlueprint(
        specialists={
            "offense.v1": _SecuritySpecialist(
                specialist_id="offense.v1",
                confidence=0.9,
            ),
            "defense.v1": _OperationsSpecialist(
                specialist_id="defense.v1",
                confidence=0.7,
            ),
        },
        llm_synthesizers={"llm.default.v1": _FailingLlmsynthesizer()},
    )
    bindings = CouncilBindingModel(
        specialists=("offense.v1", "defense.v1"),
        synthesizer="llm.default.v1",
        synth_strategy=CouncilSynthStrategy.LLM,
        max_findings=5,
    )
    compiled = blueprint.compile(bindings)
    try:
        compiled.invoke({"topic": "network posture"})
    except BlueprintError as exc:
        assert exc.code == BlueprintErrorCode.EXECUTION_FAILED
        assert str(exc) == "Error: council synthesis failed."
        assert exc.data["synth_error_code"] == "llm_synth_failed"
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("Expected BlueprintError for strict llm synth failure.")
