import asyncio

from .Tool import Tool
from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import BaseModel, Field

from typing import Optional, Callable, List
from langchain_core.tools import Tool as LangChainTool
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import (
    create_tool_calling_agent,
    AgentExecutor,
)
import inspect

from .._utils._utility import function_to_input_schema


class AgentSchema(BaseModel):
    input: str = Field(..., description="")


class Agent:
    """
    Agent encapsulates a callable LLM-based agent with optional tools and customizable startup behavior.

    This class supports LangChain-compatible tool integration, dynamic prompt generation,
    and advanced orchestration via decorators or manual control.

    Args:
        name (str): Agent name identifier.
        llm (BaseChatModel): A LangChain-compatible language model.
        tools (Optional[list[Tool]]): List of Tool instances for use in agent tasks.
        custom_start (Optional[Callable]): A custom startup function (overrides default behavior).
        system_prompt (Optional[str]): The initial system prompt for the agent.
    """

    def __init__(
        self,
        name: str,
        llm: BaseChatModel,
        tools: list[Tool] = [],
        custom_start: Optional[Callable] = None,
        system_prompt: str | None = None,
    ):
        self.name = name
        self.llm = llm
        self.tools: List[Tool] = tools or []

        self.system_prompt = system_prompt

        self.custom_start_func = custom_start

        self._tools_dict = self._build_tools_dict()
        self.tools_langchain = self._convert_tools_to_langchain(self.tools)

    def _build_tools_dict(self):
        """
        Builds a dictionary of tool metadata for inspection or documentation.
        """
        _tools_dict = []

        if self.tools is None:
            self.tools = []
            _tools_dict = []
            return _tools_dict

        for tool in self.tools:
            _tools_dict.append(tool.describe())

        return _tools_dict

    @property
    def tools_dict(self):
        """Returns metadata for all available tools."""
        return self._tools_dict

    def set_system_prompt(self, func: Callable):
        """
        Decorator for dynamically assigning a system prompt (sync or async).

        Args:
            func (Callable): A function returning a string prompt, sync or async.

        Raises:
            ValueError: If the return value is not a string.
            TypeError: If the input is not a callable.
        """

        if not callable(func):
            raise TypeError("Provided system_prompt must be a callable.")

        result = func()
        if not isinstance(result, str):
            raise ValueError("system_prompt must return a string.")
        self.system_prompt = result

        return func

    def custom_start(self, func: Callable):
        """
        Decorator to assign a custom startup function for the agent.

        The custom function can accept any of: `tools`, `input`, `llm`, `system_prompt`.
        """

        if not callable(func):
            raise TypeError("custom_start must be a callable function.")

        self.custom_start_func = func
        return func

    def tool(self, name: str = None, description: str = None):
        """
        Decorator to register a function as a Tool available to the agent.

        Args:
            name (str, optional): Custom tool name. Defaults to function name.
            description (str, optional): Tool description for documentation.

        Returns:
            Callable: The original function, unmodified.

        Example:
            @agent.tool(name="greet", description="Say hello")
            def greet_tool(name: str):
                return f"Hello {name}!"
        """

        def decorator(func: Callable):
            tool_name = name or func.__name__

            if any(t.name == tool_name for t in self.tools):
                raise ValueError(f"Tool '{tool_name}' already exists.")

            tool_desc = description or func.__doc__ or ""
            input_schema = function_to_input_schema(func)
            tool_obj = Tool(
                name=tool_name,
                description=tool_desc,
                func=func,
                input_schema=input_schema,
                raise_on_error=True,
            )

            self.tools.append(tool_obj)

            self._tools_dict = self._build_tools_dict()
            self.tools_langchain = self._convert_tools_to_langchain(self.tools)
            return func

        return decorator

    def _convert_tools_to_langchain(
        self,
        tools: list[Tool] | None = None,
    ) -> list[LangChainTool]:
        _tools_langchain = []

        if tools is None:
            tools = []
            _tools_langchain = []
            return _tools_langchain

        for tool in tools:
            _tools_langchain.append(tool.convert_tool_to_langchain())
        return _tools_langchain

    def as_tool(self, description: Optional[str] = None) -> Tool:
        """Agents can be used as tools and are suitable for many usage scenarios"""

        def wrapped_func(input: str):
            result = self.start(input)
            return result["output"]

        return Tool(
            name=self.name,
            description=description or f"Agent wrapper: {self.name}",
            input_schema=AgentSchema,
            func=wrapped_func,
        )

    def as_tool_async(self, description: Optional[str] = None) -> Tool:
        """Async version of as_tool for async start method."""

        async def wrapped_func(input: str):
            result = await self.start_async(input)
            return result["output"]

        return Tool(
            name=self.name,
            description=description or f"Agent async wrapper: {self.name}",
            input_schema=AgentSchema,
            func=wrapped_func,
        )

    def start(self, input: str, verbose: bool = False, **kwargs):
        """
        Starts the agent execution with the given input.

        If a custom_start_func is defined, it will be used.
        Otherwise, runs the standard LangChain agent pipeline.

        Args:
            input (str): The input query or command.
            verbose (bool): Enables verbose logging if True.
            **kwargs: Additional parameters forwarded to the custom start function.

        Returns:
            dict: Dictionary with 'output' key containing agent's response.

        Example:
            agent = Agent(name="test", llm=my_llm)
            result = agent.start("Hello, how are you?")
            print(result["output"])
        """
        user_input = input
        if self.custom_start_func:
            sig = inspect.signature(self.custom_start_func)
            args_to_pass = {}

            for key in sig.parameters:
                if key == "tools":
                    args_to_pass["tools"] = self.tools_langchain
                elif key == "input":
                    args_to_pass["input"] = user_input
                elif key == "system_prompt":
                    args_to_pass["system_prompt"] = self.system_prompt
                elif key == "llm":
                    args_to_pass["llm"] = self.llm
                elif key in kwargs:
                    args_to_pass[key] = kwargs[key]

            if inspect.iscoroutinefunction(self.custom_start_func):
                return asyncio.run(self.custom_start_func(**args_to_pass))
            else:
                return {"output": self.custom_start_func(**args_to_pass)}

        # Default agent logic
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", self.system_prompt or "You are a helpful agent."),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        )

        agent = create_tool_calling_agent(self.llm, self.tools_langchain, prompt)
        executor = AgentExecutor(
            agent=agent, tools=self.tools_langchain, verbose=verbose
        )

        result = executor.invoke(
            {
                "chat_history": [],
                "input": user_input,
            }
        )

        return {"output": result}

    async def start_async(self, input: str, verbose: bool = False, **kwargs):
        """
        Asynchronously starts the agent execution with the given input.

        If a custom_start_func is defined, it will be used.
        Otherwise, runs the standard LangChain agent pipeline asynchronously.

        Args:
            input (str): The input query or command.
            verbose (bool): Enables verbose logging if True.
            **kwargs: Additional parameters forwarded to the custom start function.

        Returns:
            dict: Dictionary with 'output' key containing agent's response.

        Example:
            result = await agent.start_async("Hello, how are you?")
            print(result["output"])
        """
        user_input = input
        if self.custom_start_func:
            sig = inspect.signature(self.custom_start_func)
            args_to_pass = {}

            for key in sig.parameters:
                if key == "tools":
                    args_to_pass["tools"] = self.tools_langchain
                elif key == "input":
                    args_to_pass["input"] = user_input
                elif key == "system_prompt":
                    args_to_pass["system_prompt"] = self.system_prompt
                elif key == "llm":
                    args_to_pass["llm"] = self.llm
                elif key in kwargs:
                    args_to_pass[key] = kwargs[key]

            if inspect.iscoroutinefunction(self.custom_start_func):
                return await self.custom_start_func(**args_to_pass)
            else:
                return {"output": self.custom_start_func(**args_to_pass)}

        # Default async agent logic
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", self.system_prompt or "You are a helpful agent."),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        )

        agent = create_tool_calling_agent(self.llm, self.tools_langchain, prompt)
        executor = AgentExecutor(
            agent=agent, tools=self.tools_langchain, verbose=verbose
        )

        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            lambda: executor.invoke(
                {
                    "chat_history": [],
                    "input": user_input,
                }
            ),
        )

        return {"output": result}

    def export_tools_schema(self):
        """
        Agent is output in a dict compatible structure
        """
        return {
            "agent_name": self.name,
            "tools": [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": (
                        tool.input_schema.model_json_schema() if tool.input_schema else None
                    ),
                }
                for tool in self.tools or []
            ],
        }

    def __repr__(self):
        return f"<Agent name='{self.name}' tools={self._tools_dict} total_tool={len(self.tools or [])}>"

    def describe(self) -> dict:
        return {
            "name": self.name,
            "system_prompt": self.system_prompt,
            "total_tool": len(self.tools or []),
            "tools": self._tools_dict,
            "llm": self.llm.metadata,
        }
