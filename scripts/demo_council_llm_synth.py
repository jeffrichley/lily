"""Temporary demo: execute council blueprint with real LLM synthesis.

Usage (PowerShell):
    $env:OPENAI_BASE_URL="http://localhost:8000/v1"
    $env:OPENAI_API_KEY="dummy"
    uv run python scripts/demo_council_llm_synth.py `
      --model "Qwen/Qwen2.5-Coder-7B-Instruct-AWQ" `
      --topic "network posture"

Notes:
- Uses OpenAI-compatible chat completions endpoint.
- Demonstrates both strict LLM mode and optional fallback mode.
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from typing import Any

from openai import OpenAI

from lily.blueprints import (
    CouncilBindingModel,
    CouncilBlueprint,
    CouncilFinding,
    CouncilInputModel,
    CouncilSpecialistReport,
    CouncilSpecialistStatus,
    CouncilSynthStrategy,
)


@dataclass(frozen=True)
class _DemoSpecialist:
    """Simple deterministic specialist fixture for demo runs."""

    specialist_id: str
    confidence: float

    def run(self, request: CouncilInputModel) -> CouncilSpecialistReport:
        """Return one finding per specialist.

        Args:
            request: Typed council input payload.

        Returns:
            Specialist report payload.
        """
        return CouncilSpecialistReport(
            specialist_id=self.specialist_id,
            status=CouncilSpecialistStatus.OK,
            findings=(
                CouncilFinding(
                    title=f"{self.specialist_id} finding",
                    recommendation=f"Investigate controls for {request.topic}",
                    confidence=self.confidence,
                    source_specialist=self.specialist_id,
                ),
            ),
            notes="demo specialist report",
        )


class _OpenAiCouncilSynthesizer:
    """LLM synthesizer that calls OpenAI-compatible chat completions."""

    def __init__(self, *, model: str) -> None:
        """Create synthesizer client.

        Args:
            model: Model identifier served by OpenAI-compatible endpoint.
        """
        self._model = model
        self._client = OpenAI(
            base_url=os.environ.get("OPENAI_BASE_URL", "http://localhost:8000/v1"),
            api_key=os.environ.get("OPENAI_API_KEY", "dummy"),
        )

    def run(
        self,
        *,
        request: CouncilInputModel,
        reports: tuple[CouncilSpecialistReport, ...],
        max_findings: int,
    ) -> dict[str, object]:
        """Run LLM synthesis and return CouncilOutputModel-compatible dict.

        Args:
            request: Council run input.
            reports: Specialist report payloads.
            max_findings: Maximum finding count requested.

        Returns:
            Dictionary shaped like CouncilOutputModel.
        """
        system = (
            "You are a synthesis engine. Output JSON only, no markdown fences. "
            "Schema: "
            '{"summary": str, "ranked_findings": ['
            '{"title": str, "recommendation": str, "confidence": number, '
            '"source_specialist": str}'
            '], "failed_specialists": [str]}.'
        )
        payload = {
            "topic": request.topic,
            "max_findings": max_findings,
            "reports": [report.model_dump(mode="json") for report in reports],
        }
        completion = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": (
                        "Synthesize these specialist reports into ranked findings. "
                        f"Input JSON:\n{json.dumps(payload, sort_keys=True)}"
                    ),
                },
            ],
            temperature=0,
        )
        message = completion.choices[0].message.content or ""
        parsed = _extract_json_object(message)
        if not isinstance(parsed, dict):
            raise RuntimeError("LLM did not return a JSON object.")
        return {
            "topic": request.topic,
            "summary": str(parsed.get("summary", "")).strip()
            or f"LLM synthesis for {request.topic}",
            "ranked_findings": parsed.get("ranked_findings", []),
            "participating_specialists": [r.specialist_id for r in reports],
            "failed_specialists": parsed.get("failed_specialists", []),
        }


def _extract_json_object(text: str) -> dict[str, Any]:
    """Extract first JSON object from text content.

    Args:
        text: Raw model response.

    Returns:
        Parsed object.
    """
    stripped = text.strip()
    if stripped.startswith("{"):
        return json.loads(stripped)
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start < 0 or end < 0 or end <= start:
        raise RuntimeError("No JSON object found in model response.")
    return json.loads(stripped[start : end + 1])


def main() -> None:
    """Run demo council blueprint with llm or llm-with-fallback strategy."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model",
        default="Qwen/Qwen2.5-Coder-7B-Instruct-AWQ",
        help="OpenAI-compatible model name.",
    )
    parser.add_argument("--topic", default="network posture", help="Council topic.")
    parser.add_argument(
        "--strategy",
        choices=("llm", "llm_with_fallback"),
        default="llm",
        help=(
            "Synthesis strategy. 'llm' is strict; 'llm_with_fallback' enables fallback."
        ),
    )
    args = parser.parse_args()

    specialists = {
        "offense.v1": _DemoSpecialist("offense.v1", 0.92),
        "defense.v1": _DemoSpecialist("defense.v1", 0.83),
    }
    llm_synth_id = "llm.openai.v1"
    blueprint = CouncilBlueprint(
        specialists=specialists,
        llm_synthesizers={llm_synth_id: _OpenAiCouncilSynthesizer(model=args.model)},
    )
    strategy = (
        CouncilSynthStrategy.LLM
        if args.strategy == "llm"
        else CouncilSynthStrategy.LLM_WITH_FALLBACK
    )
    bindings = CouncilBindingModel(
        specialists=("offense.v1", "defense.v1"),
        synthesizer=llm_synth_id,
        synth_strategy=strategy,
        max_findings=5,
    )
    compiled = blueprint.compile(bindings)
    result = compiled.invoke({"topic": args.topic, "context": ("demo",)})
    print(json.dumps(result.model_dump(mode="json"), indent=2))


if __name__ == "__main__":
    main()
