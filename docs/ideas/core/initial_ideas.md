# Lily: Spec-Driven Orchestration Framework

## Purpose

Lily is a spec-driven orchestration system designed to **maximize AI coding quality without doing the coding herself**. Her role is to generate high-quality, structured context artifacts—specs, plans, prompts, and constraints—and hand them off to external AI coding agents such as Claude, Cursor, Gemini, or OpenAI models.

The core philosophy: **great code comes from great context**.

---

## Design Principles

1. **Separation of Concerns**

   * Lily never writes production code
   * External AI coders never decide requirements or architecture

2. **Spec as the Source of Truth**

   * All downstream work derives from written artifacts
   * Specs are human-readable and AI-optimal

3. **Portability First**

   * No shell scripts, no OS assumptions
   * Markdown + structured text only

4. **Tool-Agnostic Handoff**

   * Works equally well with Claude, Cursor, Gemini, OpenAI, or future agents

5. **Phase-Specific Tooling**

   * Each phase produces explicit artifacts
   * No hidden state

---

## High-Level Architecture

```
Human → Lily (Orchestrator)
      → Spec Artifacts
      → Planning Artifacts
      → Prompt Packages
      → AI Coder (Claude / Cursor / etc.)
      → Code
```

Lily operates as a **workflow driver**, not an autonomous coder.

---

## Development Phases

### Phase 1: Discovery & Intent Capture

**Goal:** Establish shared understanding

**Artifacts:**

* `VISION.md`
* `GOALS.md`
* `NON_GOALS.md`
* `ASSUMPTIONS.md`
* `CONSTRAINTS.md`

**Inputs:**

* Natural language discussion
* Existing systems or references

---

### Phase 2: Specification

**Goal:** Define *what* must be built

**Artifacts:**

* `SPEC.md`

  * Functional requirements
  * Behavioral expectations
  * Interfaces (conceptual)
  * Error handling expectations

Specs are:

* Declarative
* Testable
* Free of implementation details

---

### Phase 3: Architecture & Planning

**Goal:** Define *how* it should be built

**Artifacts:**

* `ARCHITECTURE.md`
* `DATA_MODELS.md`
* `INTERFACES.md`
* `TECH_DECISIONS.md`

Includes:

* Directory structure
* Module responsibilities
* External dependencies
* Integration points

---

### Phase 4: Task Decomposition

**Goal:** Create executable work units

**Artifacts:**

* `TASKS.md`
* `ACCEPTANCE_CRITERIA.md`

Each task:

* Has a single responsibility
* References spec sections
* Includes validation conditions

---

### Phase 5: AI Coder Context Packaging

**Goal:** Give AI coders everything they need, nothing they don’t

**Artifacts:**

* `CODER_CONTEXT.md`
* `CODING_RULES.md`
* `STYLE_GUIDE.md`
* `PROMPTS/`

This is the **handoff boundary**.

---

### Phase 6: Verification & Iteration

**Goal:** Ensure alignment with spec

**Artifacts:**

* `TEST_PLAN.md`
* `KNOWN_RISKS.md`
* `OPEN_QUESTIONS.md`

Feedback loops update upstream docs—not ad-hoc prompts.

---

## Prompting Strategy

Lily uses **structured prompting** to reduce ambiguity.

Example:

```xml
<role>You are an expert Python backend engineer</role>

<context>
<architecture>ARCHITECTURE.md</architecture>
<spec>SPEC.md</spec>
<rules>CODING_RULES.md</rules>
</context>

<task>
Implement Task T-003 exactly as specified
</task>

<constraints>
- No new dependencies
- Follow style guide strictly
</constraints>
```

This approach is sometimes referred to as:

* Structured prompting
* XML-style prompting
* Tagged instruction prompting

---

## Technology Choices

**Core Framework:**

* LangChain (or LangGraph) for orchestration

**Artifacts:**

* Markdown
* Structured text (XML-style tags)

**Storage:**

* Git repository as system of record

**Execution:**

* Human-in-the-loop
* External AI coding tools

---

## What Lily Is NOT

* Not a code generator
* Not an IDE replacement
* Not a workflow runner
* Not OS-dependent

Lily is an **architect, planner, and context engineer**.

---

## Biggest Risks & Mitigations

| Risk                  | Mitigation                 |
| --------------------- | -------------------------- |
| Poor specs → bad code | Strict artifact validation |
| Context overload      | Phase-scoped handoffs      |
| Tool lock-in          | Tool-agnostic formats      |
| Drift from intent     | Spec-first iteration       |

---

## Success Criteria

* AI coders require minimal clarification
* Code matches spec on first pass
* Humans can audit decisions via docs
* System works identically across tools

---

## North Star

> **Make AI coding boring—because everything important was decided upstream.**

Lily exists so creativity, architecture, and intent live in documents—not buried in chat logs.
