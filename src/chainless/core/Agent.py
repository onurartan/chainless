from .Tool import Tool
from langchain_core.language_models.chat_models import BaseChatModel

from typing import Optional, Callable
from langchain_core.tools import Tool as LangChainTool
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import (
    create_tool_calling_agent,
    AgentExecutor,
)
import inspect


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
        tools: list[Tool] | None = None,
        custom_start: Optional[Callable] = None,
        system_prompt: str | None = None,
    ):
        self.name = name
        self.llm = llm
        self.tools = tools

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

    def set_system_prompt(self, func):
        """
        Decorator for dynamically assigning a system prompt.

        Args:
            func (Callable): A function returning a string prompt.

        Raises:
            ValueError: If the return value is not a string.
        """
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
        self.custom_start_func = func
        return func

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

    def start(self, input: str, verbose: bool = False, **kwargs):
        """
        Starts the agent execution with the given input.

        If a custom_start_func is defined, it will be used.
        Otherwise, a standard LangChain agent pipeline will run.

        Args:
            user_input (str): The input query or command.
            verbose (bool): Whether to enable verbose logging.
            **kwargs: Additional parameters forwarded to the custom start function.

        Returns:
            dict: A dictionary with an 'output' key containing the agent's response.
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

            result = self.custom_start_func(**args_to_pass)
            return {"output": result}

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
