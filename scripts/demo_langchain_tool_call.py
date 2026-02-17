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