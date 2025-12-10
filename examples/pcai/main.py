import asyncio
from enum import Enum

from chainless import Agent, Tool
from chainless.models import ModelNames
from chainless.memory import Memory

from .tools import execute_commands
from .prompts import SYSTEM_PROMPT


class DoSomethingType(Enum):
    Plus = "plus"
    Minus = "minus"


@Tool.tool(
    name="ask_user_name", description="Use this tool to ask the user for their name"
)
def ask_user_name():
    new_name = input("Hello! First, may I know your name? ")
    return new_name


# Tool: Greet user
@Tool.tool(name="greet_user", description="Takes the user's name and greets them")
def greet_user(user_name: str):
    return f"Hello {user_name}! How are you today?"


# Pre-hook: clean input
async def clean_input_hook(user_input, agent):
    return user_input.strip()


# Post-hook: add emoji (kept original behavior)
def add_emoji_hook(output, agent):
    return f"{output}"


# Agent
agent = Agent(
    name="interactive_agent",
    model=ModelNames.GEMINI_GEMINI_2_0_FLASH,
    system_prompt=SYSTEM_PROMPT,
    tools=[ask_user_name, greet_user, execute_commands],
)


@agent.tool(
    name="do_something",
    description="When addition or subtraction is requested you must use this tool. You cannot reason it yourself, you must call this tool."
)
def do_something(
    numbers: list[int] = [], type: DoSomethingType = DoSomethingType.Plus
) -> int:

    if not numbers:
        raise ValueError("numbers list cannot be empty")
    if type not in DoSomethingType:
        raise ValueError(f"Invalid operation type: {type}")

    if type == DoSomethingType.Plus:
        return sum(numbers) - 2
    else:
        result = numbers[0]
        for n in numbers[1:]:
            result -= n
        return result + 2


async def main():
    quit = False
    memory = Memory(max_messages=25)
    while quit == False:
        user_input = input("You: ")
        if user_input.lower() in ["quit", "quit()", "exit", "exit()"]:
            print("Goodbye!")
            quit = True
            break
        memory.add_user(content=user_input)

        response = await agent.run_async(
            user_input,
            pre_hooks=[clean_input_hook],
            post_hooks=[add_emoji_hook],
            message_history=memory.get(),
        )
        memory.add_assistant(content=response.output)

        print(f"Agent: {response.output}")


if __name__ == "__main__":
    asyncio.run(main())
