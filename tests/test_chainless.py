from chainless import Tool, Agent, AgentProtocol, TaskFlow
from pydantic import BaseModel, Field


from langchain_deepseek import ChatDeepSeek
from dotenv import load_dotenv

from langchain.prompts import ChatPromptTemplate

load_dotenv()


class SumModel(BaseModel):
    numbers: list[int] = Field(..., description="numbers")


class SumAgent(BaseModel):
    total: int = Field(..., description="result of the summed number")


class EchoAgent(AgentProtocol):
    name = "Echo"

    def start(self, input: str, verbose: bool = False, **kwargs):
        return {"output": f"Echoed: {input}"}


def sum(numbers: list[int]):
    result = 0
    for number in numbers:
        result += number
    return result


llm = ChatDeepSeek(model="deepseek-chat")


def test_firs_tool():
    sum_tool = Tool(
        name="sumTool", description="adding numbers", func=sum, input_schema=SumModel
    )

    result = sum_tool.execute({"numbers": [3 + 6]})
    tool_describe = sum_tool.describe()
    assert result == 9
    assert tool_describe["name"] == "sumTool"
    assert tool_describe["description"] == "adding numbers"
    assert tool_describe["parameters"]["numbers"]["type"] == "array"


def test_agent():
    sum_tool = Tool(
        name="sumTool", description="adding numbers", func=sum, input_schema=SumModel
    )
    sum_agent = Agent(
        name="SumAgent",
        llm=llm,
        tools=[sum_tool],
        system_prompt="adding numbers agent.",
    )

    @sum_agent.custom_start
    def start(input: str, tools, system_prompt):
        user_input: str = f""" 
    {input}
    """

        model = llm
        tools = tools

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt or ""),
                ("human", "{input}"),
            ]
        )

        model = model.with_structured_output(schema=SumAgent)

        chain = prompt | model
        result = chain.invoke(user_input)

        return result

    @sum_agent.set_system_prompt
    def system_prompt():
        return "agent adding numbers."

    result = sum_agent.start("What is 5+6 sum tool should be used")

    assert result["output"]
    assert result["output"].total == 11
    assert sum_agent.name == "SumAgent"
    assert sum_agent.system_prompt == "agent adding numbers."


def test_agent_protocol():
    flow = TaskFlow(name="AgentProtocolTest")
    flow.add_agent("echo", EchoAgent())
    flow.step("echo", input_map={"input": "{{input}}"})
    result = flow.run("hello")

    assert result["output"]
    assert result["output"] == "Echoed: hello"
