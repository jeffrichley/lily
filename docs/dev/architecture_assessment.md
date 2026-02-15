# Architecture Assessment: Personality Roadmap + Current Lily Project

## Scope and Method

This review covers two layers:

1. `docs/dev/personality_roadmap.md` as a **target architecture**.
2. The current codebase under `src/lily/` as the **implemented architecture**.

Primary method: read architecture docs, runtime/command/session/skills modules, then evaluate alignment, gaps, and sequencing risk.

---

## A) Assessment of `personality_roadmap.md`

## Overall judgement

The roadmap is architecturally strong as a direction document. It is explicit about user-visible capabilities, internal system work, dependencies, and phased build order. The pattern mapping (Builder/Strategy/Command/Facade/Repository/etc.) is coherent with the type of runtime Lily is becoming.

The core strength is that it frames personality as an engineered subsystem, not prompt text alone.

## What is architecturally strong

- **Clear separation of concern tracks**: user-visible features are distinguished from internal engineering work, which reduces planning ambiguity.
- **Dependency awareness**: persona compiler, memory schema, typed contracts, and eval harness are linked in a realistic dependency chain.
- **Determinism emphasis**: repeated mention of deterministic prompt assembly and deterministic tool error envelopes is exactly right for reliability and testability.
- **Safety as first-class**: persona safety/policy checks and CI redline tests are included as architecture, not an afterthought.
- **Phased plan quality**: phases are decomposed by capability maturity (foundation -> usability -> reliability -> safety -> expansion), which is appropriate for a CLI-first agent runtime.

## Architectural risks in the roadmap

1. **Potential over-concentration in PromptBuilder/PersonaManager**
   - The diagrams centralize many responsibilities around prompt + persona flows.
   - Risk: these classes become god-objects unless section providers/policies/memory retrieval are strongly modularized.

2. **Memory architecture still undecided where it matters most**
   - The open decision about separate stores vs unified typed namespace affects retrieval strategy, migrations, and operational complexity.
   - This should be decided before broad command surface growth (`/remember`, `/forget`, `/memory show`).

3. **Eval harness rubric ambiguity**
   - “Delight/fun” and consistency goals are directionally good, but need explicit scoring contracts (rubric schema, judge model policy, thresholds).
   - Without this, CI gates become unstable or gameable.

4. **Persona policy interaction model not fully specified**
   - The roadmap references a decorator and redline checks, but not the conflict strategy when style goals collide with policy constraints.
   - Define precedence rules now to avoid drift later.

## Recommended refinements before implementation expands

- Freeze a **memory ADR** now (dual-store vs unified namespace, retrieval query contract, retention/deletion semantics).
- Define a **policy precedence contract** (safety > user style > persona default > stochastic expression).
- Create eval artifact schemas up front:
  - `consistency_eval_case.json`
  - `delight_eval_case.json`
  - `safety_redline_case.json`
- Add explicit anti-god-object guardrails:
  - max module complexity budgets,
  - interface boundaries for section providers,
  - narrow DTOs between runtime and persona subsystems.

---

## B) Assessment of Current Project Architecture

## Current architectural shape (implemented)

The current implementation is a clean, deterministic V0 command runtime:

- CLI constructs and persists session state.
- Runtime facade routes input into command path (conversation path intentionally unimplemented).
- Command registry dispatches built-ins and command-alias-to-skill fallbacks.
- Skill invoker selects executor by invocation mode.
- Executors split into LLM orchestration and tool-dispatch flows.
- Skill loader builds deterministic snapshots with precedence/eligibility/diagnostics.

This is a good modular baseline for the roadmap.

## Strengths in the current architecture

1. **Good boundary layering already exists**
   - `cli` -> `runtime facade` -> `commands`/`skill invoker` -> `executors`.
   - This makes later persona/memory additions easier without rewriting everything.

2. **Deterministic command contract is strong**
   - `CommandResult` envelopes and explicit error codes are consistently used.
   - Unknown commands, alias ambiguity, parse failures, and executor binding errors are handled explicitly.

3. **Invocation mode abstraction is practical**
   - `SkillInvoker` maps `InvocationMode` to executors cleanly.
   - This supports adding persona-aware or policy-gated executors without breaking callers.

4. **Skill snapshot pipeline is architecture-grade for V0**
   - discovery, precedence, metadata parse, eligibility checks, deterministic version hash, and diagnostics are present.
   - This is a robust substrate for future persona/system prompt loading behavior.

5. **Concurrency serialization exists per session**
   - session lane control in runtime is the right foundation for deterministic per-session behavior and memory writes.

## Architectural gaps vs roadmap

1. **No conversational runtime yet**
   - `RuntimeFacade` returns `conversation_unimplemented` for non-command input.
   - This is currently the largest capability gap relative to personality goals.

2. **Prompting subsystem is minimal/not central yet**
   - There is no implemented persona compiler pipeline matching the roadmap’s Builder + section model.

3. **Memory system not yet split for personality/task concerns**
   - Session persistence exists, but not a dedicated personality memory repository + retrieval contract.

4. **Policy enforcement layer absent in execution chain**
   - Tool and LLM paths are structured, but no policy gate/decorator aligned to persona safety redlines yet.

5. **Eventing/eval architecture not implemented**
   - No event bus, no persona consistency harness, no delight/safety gates.

## Priority architecture moves (next)

1. Implement non-command conversational turn path with an internal orchestration contract.
2. Introduce `PersonaContext` and `PromptBuilder` interfaces before adding many persona commands.
3. Add memory repository interfaces (personality/task) with file-backed adapters first.
4. Insert policy checks at two boundaries:
   - pre-LLM prompt policy,
   - post-generation response policy.
5. Add slim event hooks for session/persona/memory changes to support future eval and telemetry.

---

## Final verdict

- **Roadmap quality**: architecturally high-quality direction with clear priorities and realistic dependencies.
- **Current system quality**: well-structured deterministic V0 runtime with good extension seams.
- **Main risk**: if user-facing personality commands are added before prompt/memory/policy contracts are stabilized, complexity and inconsistency will spike.

Overall: Lily is in a healthy architectural position, provided the next iterations prioritize core contracts (conversation orchestration, persona compiler, memory model, policy layer) before broad surface expansion.
