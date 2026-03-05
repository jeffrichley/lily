# PRD

# Lily — Self-Evolving Agent Operating System

**Author:** Jeff + Iris
**Audience:** Internal engineering
**Status:** Draft v1

---

# 1. Overview

Lily is a **general-purpose agent operating system** designed to support intelligent assistants capable of:

* reasoning about complex tasks
* delegating work to specialized agents
* executing deterministic tools
* evolving capabilities over time

The core philosophy is:

```
Agent = Reasoning
Skills = Expertise
Tools = Execution
```

Unlike traditional automation pipelines, Lily is designed as a **capability ecosystem** where new skills can be created, refined, and reused across tasks.

---

# 2. Goals

The system must support:

### G1 — Agentic reasoning

Lily should operate using a **ReAct-style loop**:

```
observe
reason
act
repeat
```

### G2 — Hybrid skills

Skills must support:

1. reasoning playbooks
2. deterministic procedures
3. specialized sub-agents

### G3 — Capability registry

All skills must be:

* discoverable
* versioned
* searchable
* reusable

### G4 — Evolution

The system must log task solutions so that reusable procedures can be extracted into skills later.

### G5 — Minimal kernel

The system should rely on a **very small core runtime**.

Everything else should be modular.

---

# 3. Non-Goals (Important)

This system will **not initially include**:

* reinforcement learning
* automated skill generation
* autonomous long-term planning
* complex memory architectures

These may be added later.

---

# 4. High-Level Architecture

```
User
 ↓
Lily Supervisor Agent
 ↓
Skill System
 ↓
Tools / Execution
```

Expanded view:

```
User
 ↓
Supervisor Agent (Lily)
 ↓
Hybrid Skill Layer
 ├ Playbook Skills
 ├ Procedural Skills
 └ Agent Skills
 ↓
Tools
 ↓
External Systems
```

---

# 5. Core Runtime (Agent Kernel)

The core of Lily is an **agent kernel loop**.

Responsibilities:

1. call LLM
2. detect tool calls
3. execute tools
4. return tool outputs to LLM
5. repeat until completion

### Kernel behavior

```
messages ← user input

loop:
    response ← LLM(messages)

    if response.final:
        return response.final

    for tool_call in response.tool_calls:
        result ← execute(tool_call)

        messages.append(result)
```

Key constraints:

* max iteration limit
* tool allowlist
* error handling

---

# 6. Hybrid Skill System

Lily supports **three types of skills**.

---

# 6.1 Playbook Skills

Purpose:

Guide reasoning.

These are **instructional knowledge modules**.

Example:

```
literature_review
architecture_design
research_synthesis
```

Structure:

```
skills/playbooks/<skill_name>/

SKILL.md
examples.md
metadata.json
```

Example SKILL.md:

```
Goal:
Perform a literature review.

Steps:
1 search for relevant papers
2 cluster topics
3 summarize contributions
4 identify research gaps
```

Playbooks are injected into the LLM context when invoked.

---

# 6.2 Procedural Skills

Purpose:

Execute reliable workflows.

Example:

```
summarize_pdf
analyze_repo
generate_prp
```

Structure:

```
skills/procedures/<skill>.py
```

Example:

```python
def summarize_pdf(url):
    pdf = download(url)
    text = extract_text(pdf)
    chunks = split(text)
    return summarize(chunks)
```

These appear to the kernel as **tools**.

---

# 6.3 Agent Skills

Purpose:

Provide specialized reasoning.

Example:

```
ResearchAgent
CodingAgent
VideoAgent
```

Structure:

```
skills/agents/<agent>.py
```

Agent skills run their own kernel with specialized tools.

Example:

```
ResearchAgent
  tools:
    arxiv_search
    paper_summarize
    citation_extract
```

The supervisor invokes them as tools.

---

# 7. Skill Registry

The registry manages all capabilities.

Responsibilities:

```
register skills
search skills
track metadata
version skills
record performance
```

Example schema:

```
Skill
 ├ name
 ├ type
 ├ goal
 ├ tags
 ├ version
 ├ dependencies
 └ success metrics
```

Example:

```python
class SkillRegistry:

    def register(skill):
        ...

    def find(goal):
        ...

    def promote(skill):
        ...
```

---

# 8. Tool System

Tools represent **deterministic execution capabilities**.

Examples:

```
filesystem
web_search
python_runner
ffmpeg
docker
```

Structure:

```
tools/<tool>.py
```

Example:

```python
def search_arxiv(query):
    ...
```

Tools must:

* have clear input schemas
* return structured outputs
* avoid LLM dependencies

---

# 9. Capability Genome (Skill Graph)

Skills form a **hierarchical capability graph**.

Example:

```
plan_research
 ├ literature_review
 │  ├ summarize_paper
 │  │  └ extract_pdf_text
 │  └ search_papers
 └ experiment_design
```

Benefits:

* modular capability reuse
* scalable skill ecosystem
* efficient discovery

---

# 10. Skill Evolution (MVP)

The initial system will not automatically create skills.

Instead it will log task execution data.

Each task run records:

```
user goal
tools used
skills used
final output
success/failure
```

Stored in:

```
runtime_logs/
```

Future evolution system will:

```
detect repeated workflows
extract procedures
convert to procedural skills
register skill
```

---

# 11. File Structure

```
.lily/
   skills/
       playbooks/
       procedures/
       agents/

src/lily/

   runtime/
       kernel.py
       policies.py

   registries/
       skill_registry.py
       tool_registry.py

   agents/
       lily_agent.py

   tools/
       filesystem.py
       web_search.py
       python_runner.py
```

---

# 12. Lily Supervisor Agent

Lily is the **top-level orchestrator**.

Responsibilities:

```
interpret user goals
select skills
delegate work
evaluate results
```

Decision flow:

```
User request
 ↓
Identify goal
 ↓
Find relevant skill
 ↓
Invoke skill or tool
 ↓
Evaluate result
```

---

# 13. Implementation Phases

---

# Phase 1 — Core Runtime

Deliverables:

```
agent kernel
tool registry
basic tools
```

Goal:

Simple agent that can call tools.

---

# Phase 2 — Hybrid Skills

Deliverables:

```
playbook skill loader
procedural skills
agent skills
```

Goal:

Hybrid skill execution.

---

# Phase 3 — Skill Registry

Deliverables:

```
skill metadata
skill search
skill versioning
```

Goal:

Capability discovery.

---

# Phase 4 — Task Logging

Deliverables:

```
execution logs
skill usage metrics
```

Goal:

Foundation for skill evolution.

---

# Phase 5 — Skill Extraction (Future)

Deliverables:

```
workflow mining
automatic skill creation
skill promotion
```

Goal:

Self-improving capability ecosystem.

---

# 14. Risks

### Over-engineering

Avoid building:

```
complex planning engines
massive orchestration layers
excessive agent hierarchies
```

The kernel must remain simple.

---

### Skill explosion

Without registry management, the system may accumulate redundant skills.

Solution:

```
skill evaluation
skill pruning
skill promotion
```

---

# 15. Success Criteria

The MVP is successful if Lily can:

1. interpret user requests
2. load relevant playbook skills
3. execute procedural skills
4. delegate to agent skills
5. call tools
6. complete multi-step tasks

---

# 16. Long-Term Vision

The long-term goal is a **capability ecosystem**.

```
Agent = reasoning core
Skills = evolving expertise
Tools = execution layer
```

Over time the system becomes a **self-growing library of intelligence**.
