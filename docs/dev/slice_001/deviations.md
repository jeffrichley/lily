---
owner: "@team"
last_updated: "2026-02-17"
status: "reference"
source_of_truth: false
---

# Slice 001 Deviations

Purpose: record where implementation intentionally diverged from the original slice design docs, with rationale.

## 1. LLM Backend Provider Choice

- Planned: hidden adapter with LangGraph implementation.
- Implemented: hidden adapter with LangChain v1 high-level `create_agent` flow in `runtime.llm_backend.langchain_adapter`.

Rationale:

- Team decision to prefer higher-level LangChain v1 primitives first, while preserving an internal adapter seam.
- Keeps framework details isolated and swappable.

## 2. Echo Behavior Enforcement Location

- Planned intent: behavior should be expressed by skill artifact and orchestration contract.
- Implemented: temporary `echo`-specific prompt enforcement branch in `langchain_adapter` (`if request.skill_name == "echo"`).

Rationale:

- Needed deterministic vertical-slice proof behavior for manual and automated smoke validation.
- Chosen as a temporary scaffold for Slice 001.

Follow-up:

- Move behavior sourcing to skill content/metadata-driven execution and remove skill-name branching in backend.

## 3. CLI Command Set Shape

- Planned at slice level: deterministic command surface exists.
- Implemented: explicit Typer commands `run` and `repl` as delivery shell around that surface.

Rationale:

- Enables scriptable tests (`run`) and manual validation (`repl`) without coupling to future UI choices.

## 4. REPL Exit Handling

- Planned: basic REPL loop.
- Implemented: explicit handling for `exit`, `quit`, `exit()`, `quit()`, and prompt aborts.

Rationale:

- Prevent noisy shutdown traces during manual smoke validation.
