Perfect. Here’s a clean, copy-paste prompt you can give your AI agent to analyze OpenClaw properly.

---

# 🔍 OpenClaw Deep Architectural Analysis Task

You are analyzing the OpenClaw project as a systems architect.

This is **not** a surface-level feature review.

You must evaluate it as if we are deciding whether to:

* borrow architectural concepts,
* adopt design patterns,
* or deliberately avoid certain implementation decisions.

Focus on structural and systemic qualities — not marketing.

---

# 🎯 Goal

Identify:

1. What architectural ideas are strong and reusable
2. What design decisions introduce instability or nondeterminism
3. What parts would not scale into a production-grade agent OS
4. Where execution, planning, and safety boundaries are weak or strong

We are especially interested in skill systems, execution determinism, replayability, and extensibility.

---

# 📦 1. Skill System Analysis

## A. What is a “skill” technically?

* Is a skill just markdown?
* Is it markdown + code?
* Where does executable logic live?
* How are skills discovered and loaded?
* Is there a manifest or schema?

Clarify:

* Is `skill.md` documentation only?
* Or does it act as executable logic?

---

## B. How are skills selected?

* Is skill invocation rule-based or LLM-driven?
* If given the same input twice, is the same skill chosen?
* Can selection be overridden deterministically?
* Is there routing logic separate from LLM reasoning?

We want to know:
Is skill invocation deterministic or probabilistic?

---

## C. Skill Composition

* Can skills call other skills?
* Are workflows composable?
* Is there a registry?
* Is there versioning?

Assess extensibility structure.

---

# ⚙️ 2. Execution Model

## A. Is there an Intermediate Representation (IR)?

Does OpenClaw use:

Intent → Structured Plan → Execution

Or:

Intent → LLM decides → Tool call

Is there a structured plan object?
Is there a typed execution graph?
Or is execution reactive and incremental?

---

## B. Can workflows be previewed?

* Can you inspect a full plan before execution?
* Or are steps generated dynamically mid-run?
* Is there separation between planning and execution phases?

---

## C. Failure Handling

* What happens when a skill fails?
* Is there retry logic?
* Are errors structured?
* Is execution state persisted?
* Can a run be resumed?

---

# 🔐 3. Safety & Permissions

## A. Sandboxing

* Can skills execute arbitrary shell commands?
* Is file system access restricted?
* Is network access restricted?
* Are permissions declarative or implicit?

## B. Prompt Injection Risk

* Can skill markdown contain executable instruction leakage?
* Are skills validated or linted?
* Are external skills trusted by default?

Assess supply-chain and injection risks.

---

# 📊 4. Observability & Reproducibility

Does OpenClaw log:

* Step start/end times
* Tool input/output
* Environment details
* Artifact hashes
* Deterministic run directories

Can a run be replayed exactly?

Is there provenance tracking?

---

# 🧠 5. Planning vs Execution Boundary

Where does planning end and execution begin?

* Is there a compiler phase?
* Or is execution intertwined with planning?
* Is there a structured escalation into workflows?

Is there a clear boundary between:
Narrative reasoning
Structured planning
Execution

---

# 🧬 6. Evolution Model

How do new skills get added?

* Is behavior stable across updates?
* Can changes be diffed?
* Is there drift between versions?
* Is there a registry with constraints?

Does the system evolve safely or chaotically?

---

# 🚨 7. Identify Core Weaknesses

Explicitly identify:

* Where nondeterminism exists
* Where safety boundaries are weak
* Where replayability breaks down
* Where markdown becomes semi-executable
* Where LLM behavior substitutes for structure

Be critical.

---

# 📌 8. Output Format

Provide your findings in this structure:

1. Architectural Strengths
2. Architectural Weaknesses
3. Production Readiness Assessment
4. Concepts Worth Borrowing
5. Concepts to Avoid
6. Missing Layers for Enterprise-Grade System
7. Overall Verdict

---

# ⚠️ Important

Do not summarize documentation.

Reverse-engineer design intent and evaluate systemic qualities.

Focus on:

* Determinism
* Safety
* Extensibility
* Observability
* Structural clarity

We are evaluating OpenClaw as a potential conceptual foundation — not as a toy.

Be rigorous.
