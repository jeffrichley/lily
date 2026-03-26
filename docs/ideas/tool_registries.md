---
owner: "@jeffrichley"
last_updated: "2026-03-05"
status: "reference"
source_of_truth: false
---

Yes — and you’re asking exactly the right question for Lily. The key is designing a **tool discovery + registry system that aligns with emerging standards** instead of inventing something custom that won’t interoperate later.

There are **three standards-ish patterns emerging** right now:

1. **Annotation discovery** (`@tool`, decorators)
2. **Config-based tool catalogs**
3. **Protocol-based discovery (MCP)**

A good Lily architecture should support **all three simultaneously**.

I'll walk you through the architecture that aligns with what the ecosystem is converging toward.

---

# First: understand a key fact about LangGraph tools

LangGraph does **not have a global tool registry**.

Tools are typically passed into a node or bound to the model at runtime. ([LangChain Forum][1])

That means **you must build the registry yourself** if you want dynamic discovery.

This is normal — most advanced agent systems do exactly that.

---

# The architecture Lily should use

The emerging pattern across LangGraph, MCP, and multi-agent systems looks like this:

```
Tool Sources
   │
   ├─ Python tools (@tool)
   ├─ MCP servers
   ├─ Config-defined tools
   │
   ▼
Tool Discovery Layer
   │
   ▼
Tool Registry
   │
   ▼
Agent Runtime
   │
   ▼
bind_tools()
```

The **Tool Registry is the key component.**

---

# Tool source 1 — decorator discovery (`@tool`)

You already know this one.

Example:

```python
from langchain.tools import tool

@tool
def web_search(query: str) -> str:
    ...
```

But the trick is **auto-discovery**.

Instead of manually importing tools, Lily should scan modules.

Example:

```python
import pkgutil
import inspect

def discover_tools(package):
    tools = []

    for _, modname, _ in pkgutil.walk_packages(package.__path__, package.__name__ + "."):
        module = __import__(modname, fromlist=["dummy"])

        for _, obj in inspect.getmembers(module):
            if getattr(obj, "is_tool", False):
                tools.append(obj)

    return tools
```

Then Lily automatically loads tools from:

```
lily/
  tools/
     filesystem/
     web/
     coding/
```

This is the **standard Python plugin pattern**.

---

# Tool source 2 — config-defined tools

Many AI systems let you define tools in config files.

Example YAML:

```yaml
tools:
  - name: weather_api
    type: http
    endpoint: https://api.weather.com
    schema: weather.schema.json
```

These get wrapped into tool objects at runtime.

Example loader:

```python
def load_config_tools(path):
    config = yaml.safe_load(open(path))

    for tool in config["tools"]:
        registry.register(create_tool(tool))
```

This lets users extend Lily **without writing Python**.

---

# Tool source 3 — MCP discovery (very important)

This is the most “standardized” mechanism right now.

The **Model Context Protocol (MCP)** lets agents discover tools from external servers. ([Wikipedia][2])

An MCP server exposes tools like this:

```
list_tools → returns schemas
call_tool → executes tool
```

Agents connect and automatically retrieve tool schemas.

Example lifecycle:

```
connect MCP server
     ↓
list_tools()
     ↓
convert schemas → tool objects
     ↓
register in registry
```

MCP explicitly supports **tool discovery and invocation** so agents can dynamically integrate external systems. ([Descope][3])

This is becoming the **closest thing to a universal tool standard**.

---

# The Lily Tool Registry

Now we combine all sources.

Example:

```python
class ToolRegistry:

    def __init__(self):
        self.tools = {}

    def register(self, tool):
        self.tools[tool.name] = tool

    def get(self, name):
        return self.tools[name]

    def list(self):
        return list(self.tools.values())
```

Loader pipeline:

```python
registry = ToolRegistry()

registry.register_many(discover_tools(lily.tools))
registry.register_many(load_config_tools("tools.yaml"))
registry.register_many(load_mcp_tools())
```

Now Lily has a **unified tool catalog**.

---

# Runtime tool selection

Agents should **not receive all tools**.

Instead they get filtered tools.

LangChain itself recommends dynamic tool selection because too many tools can overwhelm the model. ([LangChain Docs][4])

Example:

```python
tools = registry.search(query)

llm.bind_tools(tools)
```

This can use:

* embeddings
* tags
* skill membership

---

# Skills registering tools

This is where skills come in.

Example:

```yaml
skill: research

tools:
  - web_search
  - scrape_page
  - summarize
```

When a skill loads:

```
skill loads
   ↓
tools activated
   ↓
agent gets those tools
```

LangChain actually recommends **dynamic tool registration when skills load**. ([LangChain Docs][5])

---

# Final architecture for Lily

Here’s the **standards-friendly version**.

```
lily/
  tools/
     filesystem/
     web/
     coding/

  skills/
     research.yaml
     coding.yaml

  tool_registry.py
  tool_loader.py
```

Runtime:

```
start Lily
    ↓
discover Python tools
    ↓
load config tools
    ↓
connect MCP servers
    ↓
build registry
```

Agent execution:

```
task arrives
   ↓
skill selected
   ↓
tools filtered
   ↓
bind_tools()
```

---

# The design rule I recommend for Lily

Tools should be **discoverable, not manually registered**.

Meaning:

```
drop a file in /tools
    ↓
tool appears in registry
```

This is how:

* VSCode extensions
* pytest plugins
* FastAPI routers

all work.

---

# My honest recommendation (important for Lily)

If you want a **future-proof design**, Lily should support:

1. **Python tool auto-discovery**
2. **config tool manifests**
3. **MCP servers**

Those three together give you:

```
local tools
user tools
remote tools
```

in one registry.

That’s exactly where the agent ecosystem is going.

---

If you'd like, I can also show you the **cleanest registry architecture I've seen for agent systems**.

It's used in some advanced agent frameworks and would fit Lily extremely well:

**Capability Registry + Tool Router + Skill Loader**

It solves the scaling problem once Lily has **100+ tools**, which will happen faster than you think.

[1]: https://forum.langchain.com/t/are-dynamic-tool-lists-allowed-when-using-create-agent/1920?utm_source=chatgpt.com "Are dynamic tool lists allowed when using create_agent?"
[2]: https://en.wikipedia.org/wiki/Model_Context_Protocol?utm_source=chatgpt.com "Model Context Protocol"
[3]: https://www.descope.com/learn/post/mcp?utm_source=chatgpt.com "What Is the Model Context Protocol (MCP) and How It Works"
[4]: https://docs.langchain.com/oss/python/langchain/agents?utm_source=chatgpt.com "Agents - Docs by LangChain"
[5]: https://docs.langchain.com/oss/python/langchain/multi-agent/skills?utm_source=chatgpt.com "Skills"
