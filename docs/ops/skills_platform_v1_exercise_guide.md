---
owner: "@team"
last_updated: "2026-02-17"
status: "active"
source_of_truth: true
---

# Skills Platform V1 Exercise Guide

Purpose: exact, copy-paste instructions to exercise Skills Platform V1 in three modes.

Assumptions:
- Shell: PowerShell
- Workspace root: `E:\workspaces\dream\lily`
- Virtual env is active

---

## 1) Trusted Skill via Slash Command (No Docker)

This uses builtin provider (`builtin:add`) and does not hit plugin sandbox.

### Commands

```powershell
cd E:\workspaces\dream\lily
lily run "/skill add 2+2"
```

### Expected

- Terminal response includes `4`
- Result data shows `provider: builtin` and `tool: add`

---

## 2) Docker-Backed Plugin Skill via Slash Command

This uses plugin provider (`plugin:execute`) and runs inside Docker sandbox.

### Step A: Ensure Docker is available

```powershell
docker version
```

Expected: client/server version output (no daemon error).

### Step B: Pull runner image and get pinned digest

```powershell
docker pull python:3.13-slim
docker image inspect python:3.13-slim --format "{{index .RepoDigests 0}}"
```

Copy the output, example:
- `python@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa`

### Step C: Configure pinned sandbox image

Edit `.lily/config.yaml` and add:

```yaml
security:
  sandbox:
    image: "python@sha256:<PASTE_REAL_DIGEST_HERE>"
```

Important:
- Keep the digest real and 64 lowercase hex chars.
- V1 requires pinned digest, not a floating tag.

### Step D: Create plugin skill files

```powershell
New-Item -ItemType Directory -Force .lily/skills/docker_echo | Out-Null
```

Create `.lily/skills/docker_echo/SKILL.md`:

```markdown
---
summary: docker echo
invocation_mode: tool_dispatch
command_tool_provider: plugin
command_tool: execute
capabilities:
  declared_tools: [plugin:execute]
plugin:
  entrypoint: plugin.py
  source_files: [plugin.py]
  profile: safe_eval
  write_access: false
  env_allowlist: []
---
Echo text using plugin container runtime.
```

Create `.lily/skills/docker_echo/plugin.py`:

```python
def run(payload, *, session_id, agent_id, skill_name):
    return {"display": f"docker:{payload}"}
```

### Step E: Reload skills and run plugin

```powershell
lily run "/reload_skills"
lily run "/skill docker_echo hello from sandbox"
```

### Expected

- You should see security approval prompt with:
  - `run_once`
  - `always_allow`
  - `deny`
- Choose `run_once` first.
- Response should include: `docker:hello from sandbox`

---

## 3) LLM Calling a Lily Tool (LangChain Wrapper Path)

Note:
- This is not the slash-command conversation path.
- This is a Python demo path using Phase 4 wrappers.

### Step A: Create demo script

Create `scripts/demo_langchain_tool_call.py`:

```python
from langchain.agents import create_agent

from lily.runtime.executors.tool_dispatch import AddTool
from lily.runtime.executors.langchain_wrappers import LilyToLangChainTool
from lily.session.models import ModelConfig, Session
from lily.skills.types import SkillSnapshot

session = Session(
    session_id="demo-wrapped-agent",
    active_agent="default",
    skill_snapshot=SkillSnapshot(version="v-demo", skills=()),
    model_config=ModelConfig(model_name="openai:Qwen/Qwen2.5-Coder-7B-Instruct-AWQ"),
)

wrapped = LilyToLangChainTool(
    contract=AddTool(),
    session=session,
    skill_name="add",
    description="Adds two numbers. Args: left:int right:int",
).as_structured_tool()

agent = create_agent(
    model=session.model_settings.model_name,
    tools=[wrapped],
    system_prompt="Use tools when needed and answer concisely.",
)

result = agent.invoke(
    {"messages": [{"role": "user", "content": "Use the add tool for 20 and 22."}]}
)
print(result)
```

### Step B: Point model provider env (example vLLM OpenAI-compatible)

```powershell
$env:OPENAI_BASE_URL="http://localhost:8000/v1"
$env:OPENAI_API_KEY="dummy"
```

If your server is elsewhere, replace base URL accordingly (for example `http://host.docker.internal:8000/v1`).

### Step C: Run demo

```powershell
uv run python scripts/demo_langchain_tool_call.py
```

### Expected

- Agent output should reflect tool usage and include `42` in final answer/trace.

---

## Quick Troubleshooting

### `plugin_container_unavailable`

- Check Docker daemon:
  - `docker version`
- Confirm image in config has real digest.

### `approval_required`

- Expected when no cached approval exists.
- Re-run and choose `run_once` or `always_allow`.

### `security_preflight_denied`

- Plugin code includes blocked patterns (for example `import subprocess`).
- Remove blocked pattern and retry.

### `llm_backend_unavailable` in wrapper demo

- Check `OPENAI_BASE_URL`, model id, and model server health:
  - `curl http://localhost:8000/v1/models`

