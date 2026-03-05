Jeff, here is the **engineering companion spec**. The goal is that **you or Lily could start coding immediately without inventing interfaces on the fly**. This is intentionally concrete and opinionated so implementation friction stays low.

---

# LILY_ARCHITECTURE.md

**Project:** Lily — Self-Evolving Agent Operating System
**Authors:** Jeff + Iris
**Audience:** Engineers implementing Lily
**Status:** Engineering Specification v1

---

# 1. Architecture Principles

Lily is designed around four rules:

```text
Agents reason
Skills encode expertise
Tools execute actions
Registries manage capabilities
```

The system must remain:

* **modular**
* **framework-agnostic**
* **agent-centric**
* **extensible**

The runtime kernel must stay **minimal and stable**.

---

# 2. System Layers

Lily consists of five logical layers.

```text
User
 ↓
Agent Layer
 ↓
Skill Layer
 ↓
Tool Layer
 ↓
Execution Environment
```

Expanded:

```text
User
 ↓
Lily Supervisor Agent
 ↓
Hybrid Skill System
 ├ Playbook Skills
 ├ Procedural Skills
 └ Agent Skills
 ↓
Tool System
 ↓
External APIs / Filesystem / Compute
```

---

# 3. Core Runtime

## 3.1 Agent Kernel

The kernel manages the **agent execution loop**.

Responsibilities:

* maintain conversation state
* call LLM
* detect tool calls
* execute tools
* inject tool results
* repeat until completion

### Kernel Interface

```python
class AgentKernel:

    def run(
        self,
        user_input: str,
        tools: dict,
        max_iters: int = 10
    ) -> str:
        ...
```

---

## 3.2 LLM Adapter Interface

Lily must support multiple model providers.

Define a standard adapter interface.

```python
class LLMAdapter:

    def generate(
        self,
        messages: list[dict]
    ) -> "LLMOutput":
        ...
```

### LLMOutput

```python
class LLMOutput:

    final: str | None
    tool_calls: list["ToolCall"]
```

---

## 3.3 Tool Call Schema

```python
class ToolCall:

    name: str
    arguments: dict
```

Example tool call:

```json
{
  "name": "search_arxiv",
  "arguments": {
    "query": "reinforcement learning swarm robotics"
  }
}
```

---

# 4. Tool System

Tools are deterministic functions.

### Tool Interface

```python
class Tool:

    name: str
    description: str
    input_schema: dict

    def execute(self, args: dict) -> dict:
        ...
```

---

### Example Tool

```python
class SearchArxivTool(Tool):

    name = "search_arxiv"

    description = "Search ArXiv for research papers."

    def execute(self, args):

        query = args["query"]

        results = arxiv_search(query)

        return {"papers": results}
```

---

# 5. Tool Registry

The registry stores available tools.

### Interface

```python
class ToolRegistry:

    def register(self, tool: Tool):
        ...

    def get(self, name: str) -> Tool:
        ...

    def list(self) -> list[Tool]:
        ...
```

---

# 6. Skill System

Skills represent reusable capabilities.

Three skill types are supported.

```text
Playbook
Procedural
Agent
```

---

# 7. Skill Metadata Schema

Every skill must include metadata.

```python
class SkillMetadata:

    name: str

    type: str
    # playbook | procedure | agent

    goal: str

    tags: list[str]

    version: str

    dependencies: list[str]
```

---

# 8. Playbook Skills

Playbook skills encode **reasoning strategies**.

### Directory Structure

```
skills/playbooks/<skill_name>/

SKILL.md
metadata.json
examples.md
```

---

### SKILL.md Template

```markdown
# Skill: Literature Review

Goal:
Perform a structured review of academic literature.

Steps:

1 search for papers
2 cluster topics
3 summarize contributions
4 identify research gaps

Evaluation Criteria:

- coverage
- citation relevance
- clarity of synthesis
```

---

### Playbook Loader Tool

```python
def load_playbook(skill_name):

    path = f".lily/skills/playbooks/{skill_name}/SKILL.md"

    text = open(path).read()

    return {
        "skill": skill_name,
        "playbook": text
    }
```

---

# 9. Procedural Skills

Procedural skills execute **deterministic workflows**.

### Structure

```
skills/procedures/<skill>.py
```

Example:

```python
def summarize_pdf(url):

    pdf = download(url)

    text = extract_text(pdf)

    chunks = chunk(text)

    summaries = summarize_chunks(chunks)

    return assemble_summary(summaries)
```

Procedural skills are registered as tools.

---

# 10. Agent Skills

Agent skills are specialized subagents.

### Structure

```
skills/agents/<agent>.py
```

Example:

```python
class ResearchAgent:

    tools = [
        "search_arxiv",
        "summarize_pdf"
    ]

    def run(self, query):

        return agent_kernel(
            user_input=query,
            tools=self.tools
        )
```

---

# 11. Skill Registry

The registry manages skill discovery.

### Interface

```python
class SkillRegistry:

    def register(self, skill):

        ...

    def find_by_goal(self, goal: str):

        ...

    def find_by_tag(self, tag: str):

        ...
```

---

# 12. Skill Discovery (MVP)

For the MVP use:

```text
keyword matching
tags
simple ranking
```

Future version:

```text
embedding search
capability graphs
performance metrics
```

---

# 13. Skill Graph

Skills form a capability hierarchy.

Example:

```text
design_research_project
 ├ literature_review
 │  ├ summarize_paper
 │  │  └ extract_pdf_text
 │  └ search_papers
 └ experiment_design
```

The registry must support dependency tracking.

---

# 14. Logging System

The system must log every run.

### RunLog Schema

```python
class RunLog:

    task_id: str

    goal: str

    skills_used: list[str]

    tools_used: list[str]

    result: str

    success: bool
```

Logs stored in:

```
runtime_logs/
```

---

# 15. Skill Evolution (Future System)

The evolution engine will:

```text
analyze run logs
detect repeated workflows
extract procedures
generate new skills
register them
```

Example workflow detection:

```text
search_arxiv
summarize_pdf
summarize_pdf
summarize_pdf
```

→ candidate skill:

```text
summarize_papers
```

---

# 16. Supervisor Agent

Lily is the top-level agent.

Responsibilities:

```text
interpret goals
discover skills
invoke skills
delegate to agents
evaluate outputs
```

Decision flow:

```text
User Request
 ↓
Goal Identification
 ↓
Skill Search
 ↓
Skill Execution
 ↓
Tool Execution
 ↓
Return Result
```

---

# 17. Runtime Policies

The kernel must enforce:

### iteration limits

```text
max 10 tool loops
```

### tool allowlists

Agents may only call approved tools.

### error handling

Tools must return structured errors.

---

# 18. Minimal Implementation Plan

Start with the smallest working system.

### Step 1

Implement:

```
AgentKernel
LLMAdapter
ToolRegistry
```

---

### Step 2

Add:

```
basic tools
```

Example:

```
filesystem
web_search
python_runner
```

---

### Step 3

Add:

```
playbook skill loader
procedural skill
```

---

### Step 4

Add:

```
skill registry
skill metadata
```

---

### Step 5

Add:

```
agent skills
```

---

# 19. Testing Strategy

Each skill must include tests.

Example:

```
skills/<skill>/tests/
```

Test categories:

```text
unit tests
integration tests
evaluation tests
```

---

# 20. Observability

Future system should include:

```text
agent trace logs
tool execution metrics
skill performance tracking
```

This will support:

```
skill promotion
skill pruning
skill ranking
```

---

# 21. Long-Term Architecture

The ultimate vision:

```text
Agent = reasoning kernel
Skills = evolving capability graph
Tools = execution interface
```

The system becomes a **self-expanding capability ecosystem**.
