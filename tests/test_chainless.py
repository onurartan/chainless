from chainless import Tool, Agent, AgentProtocol, TaskFlow
from chainless.schemas.context import AgentProtocolRunContext

from chainless.models import ModelNames
from pydantic import BaseModel, Field


# ------------------------------------------------------------
# Models
# ------------------------------------------------------------
class SumModel(BaseModel):
    numbers: list[int] = Field(..., description="numbers to add")


class SumResult(BaseModel):
    total: int = Field(..., description="sum result")


# ------------------------------------------------------------
# Example protocol agent (manual implementation)
# ------------------------------------------------------------
class EchoAgent(AgentProtocol):
    name = "Echo"

    def run(self, ctx: AgentProtocolRunContext):
        return {"output": f"Echoed: {ctx.input}"}


# ------------------------------------------------------------
# Helper tool function
# ------------------------------------------------------------
def add_numbers(numbers: list[int]):
    return sum(numbers)


# ------------------------------------------------------------
# Test — Tool usage
# ------------------------------------------------------------
def test_tool():
    tool = Tool(
        name="sumTool",
        description="adding numbers",
        func=add_numbers,
        input_schema=SumModel,
    )

    result = tool.execute({"numbers": [3, 6]})
    info = tool.describe()

    assert result == 9
    assert info["name"] == "sumTool"
    assert info["description"] == "adding numbers"
    assert info["parameters"]["numbers"]["type"] == "array"


# ------------------------------------------------------------
# Test — Agent with a tool
# ------------------------------------------------------------
def test_agent():
    sum_tool = Tool(
        name="sumTool",
        description="adding numbers",
        func=add_numbers,
        input_schema=SumModel,
    )

    sum_agent = Agent(
        name="SumAgent",
        model=ModelNames.DEEPSEEK_CHAT,
        tools=[sum_tool],
        system_prompt="adding numbers agent",
        response_format=SumResult,
    )

    @sum_agent.set_system_prompt
    def override_system_prompt():
        return "agent adding numbers."

    result = sum_agent.run("Sum 5 + 6 using the sum tool")

    meta = sum_agent.get_metadata()
    exported = sum_agent.export_tools_schema()
    as_tool = sum_agent.as_tool()
    

    assert result.output["total"] == 11
    assert sum_agent.name == "SumAgent"
    assert meta["name"] == "SumAgent"
    assert as_tool.name == "SumAgent"
    assert exported["agent_name"] == "SumAgent"
    assert len(exported["tools"]) == 1
    assert sum_agent.system_prompt == "agent adding numbers."


# ------------------------------------------------------------
# Test — AgentProtocol used inside TaskFlow
# ------------------------------------------------------------
def test_agent_protocol():
    flow = TaskFlow("AgentProtocolTest")
    flow.add_agent("echo", EchoAgent())
    flow.step("echo", input_map={"input": "{{input}}"})

    result = flow.run("hello")

    assert result.output == "Echoed: hello"
