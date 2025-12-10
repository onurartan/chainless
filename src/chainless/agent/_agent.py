import asyncio
import anyio
import anyio.to_thread
import anyio.from_thread
import inspect

from pydantic import BaseModel

from pydantic_ai import Agent as PydanticAgent
import pydantic_ai.usage as pai_usage
import pydantic_ai.messages as pai_messages
from pydantic_ai.settings import ModelSettings


# -------------------------------------------------------------------
# DEPRECATED [LANGCHAIN SUPPORT]
# LangChain <0.1.x agents and prompt integration
# This block is no longer active. We keep it for historical compatibility
# for developers who reference older versions of Chainless.
# -------------------------------------------------------------------

# from langchain_core.language_models.chat_models import BaseChatModel
# from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
# from langchain.agents import (
#     create_tool_calling_agent,
#     AgentExecutor,
# )

# IMPORTS - INTERNAL
from chainless.tool import Tool, ToolExecutionTracker
from chainless.schemas.context import AgentContext
from ._prepost_hooks import AgentHook

from chainless._utils.schema_utils import function_to_input_schema
from chainless.models._model import get_agent_model
from chainless._utils.validation import validate_model
from chainless.models import ModelNames
from chainless._utils.exception import ChainlessError
from chainless.messages import to_pydantic, SystemMessage

from chainless._utils.serialization import clean_output_structure


from chainless.schemas.agent_schema import AgentResponse, AgentSchema

# TYPING
from typing_extensions import deprecated
from typing import overload

from typing import Union, Type, Any
from typing import Optional, Callable, List


class Agent:
    """
    Agent encapsulates a callable LLM-based agent with optional tool integration,
    dynamic system prompts, and fully customizable start/run behavior.

    This class abstracts the complexity of orchestrating PydanticAI agents,
    allowing you to:
        - Register tools that can be used in agent reasoning.
        - Dynamically override the system prompt at runtime.
        - Inject a custom startup function (`on_start`) for special workflows.
        - Run the agent synchronously or asynchronously with retries and structured output.

    Key Features:
        • Tool Management: Seamlessly converts internal tools to PydanticAI formats.
        • Custom Startup Flow: Supports both sync and async via `on_start` decorator.
        • Deprecation-Ready: Old `custom_start` and `start()` methods preserved with warnings.
        • Agent Export: Can self-describe or expose itself as a Tool for nested agents.

    Example Usage:
        >>> agent = Agent(name="my_agent", model=ModelNames.GEMINI_GEMINI_2_0_FLASH)
        >>> @agent.tool(name="greet")
        ... def greet(name: str):
        ...     return f"Hello {name}!"
        >>> result = agent.run("Say hello to Alice")
        >>> print(result.output)
    """

    @overload
    def __init__(
        self,
        name: str,
        model: Union[ModelNames, str] = ModelNames.GEMINI_GEMINI_2_0_FLASH,
        # llm: Optional[BaseChatModel] = None,
        tools: Optional[list[Tool]] = None,
        response_format: Union[Type[BaseModel], type[str], None] = str,
        system_prompt: str | None = None,
        instructions: str | list[str] | None = None,
        prepare_tools: Optional[Callable] = None,
        retries: int = 3,
        output_retries: Optional[int] = None,
        history_processors: Optional[list[Callable]] = None,
        custom_start: Optional[Callable] = None,
        on_start: Optional[Callable] = None,
    ) -> None: ...

    def __init__(
        self,
        name: str,
        model: Union[ModelNames, str] = ModelNames.GEMINI_GEMINI_2_0_FLASH,
        # llm: Optional[BaseChatModel] = None,
        tools: Optional[list[Tool]] = None,
        response_format: Union[Type[BaseModel], type[str], None] = str,
        system_prompt: str | None = None,
        instructions: str | list[str] | None = None,
        prepare_tools: Optional[Callable[[list[Tool]], list[Tool]]] = None,
        retries: int = 3,
        output_retries: Optional[int] = None,
        history_processors: Optional[list[Callable]] = None,
        custom_start: Optional[Callable] = None,
        on_start: Optional[Callable] = None,
    ):
        # DEPRACTED[LANGCHAIN]
        # llm (BaseChatModel, optional):
        #         A LangChain-compatible chat model. Required if you want to use this agent with
        #         LangChain's tool-calling agent pipeline.
        
        """
        Initialize a new **Chainless Agent**.

        The Agent class abstracts interaction with LLMs and provides structured
        tool integration, retry logic, dynamic prompts, and optional custom startup
        workflows. It is designed to unify  **PydanticAI** agent features
        under a single, consistent API.

        Args:
            name (str):
                Unique identifier for this agent. Used in logging, metadata, and when exporting
                the agent as a tool.

            model (ModelNames_List, optional):
                Default model identifier for PydanticAI execution. This is typically a string key
                from the internal `ModelRegistry`. Defaults to `"gemini/gemini-2.0-flash"`.

            

            tools (list[Tool], optional):
                List of tool objects available to the agent. Each tool can encapsulate a callable
                function, schema, and metadata. Defaults to an empty list.

            response_format (Type[BaseModel] | type[str] | None, optional):
                Defines the expected output type from the agent.
                - `str` (default): returns raw string outputs.
                - `BaseModel`: validates outputs against a Pydantic schema.
                - `None`: raw, unvalidated responses.

            system_prompt (str, optional):
                Initial static instruction for the agent (e.g., persona, role, or behavior).
                Unlike `instructions`, this is always applied as the root system message.

            instructions (str | list[str] | None, optional):
                Additional instructions that guide the agent's reasoning process.
                Can be a single string or a list of strings. Useful for dynamic,
                task-specific context that supplements the `system_prompt`.

            prepare_tools (Callable, optional):
                Function that dynamically prepares or filters tools before each run.
                For example, you can restrict tools based on the user query or runtime context.

            retries (int, optional):
                Maximum number of retries for transient errors during model execution.
                Defaults to `3`.

            output_retries (int, optional):
                Maximum number of retries for validating the model's output against
                the declared `response_format`. Defaults to the value of `retries`.

            history_processors (list[Callable], optional):
                Optional list of functions to preprocess the conversation history before
                sending it to the model. Each processor receives and returns a list of messages.
                Common use cases: anonymization, truncation, filtering, or custom logging.

            custom_start (Callable, deprecated):
                Deprecated in favor of `on_start`. Retained for backward compatibility.

            on_start (Callable, optional):
                Custom startup function (sync or async). If defined, overrides the default
                agent execution pipeline. Receives an `AgentContext` object containing
                `input`, `tools`, and `system_prompt`.

        Raises:
            ChainlessError:
                If invalid values or deprecated parameters are provided.

        Example:
            >>> agent = Agent(name="translator", model="gemini/gemini-2.0-flash")
            >>> @agent.tool(name="greet")
            ... def greet(name: str): return f"Hello {name}!"
            >>> result = agent.run("Say hello to Alice")
            >>> print(result.output)
            "Hello Alice!"
        """
        self.name = name
        # self.llm = llm
        # self.model_name = model.value if isinstance(model, ModelNames) else model
        self.model_name = validate_model(model, self.name)
        self.tools: List[Tool] = tools or []
        self.instructions = instructions
        self.prepare_tools = prepare_tools
        self.output_retries = output_retries
        self.history_processors = history_processors

        self.system_prompt = system_prompt or self._generate_default_system_prompt()
        self.retries = retries
        self.response_format = response_format

        self.custom_start_func = on_start or custom_start

        self._refresh_tool_metadata()

    def _refresh_tool_metadata(self) -> None:
        """Refreshes all cached tool representations (PydanticAI, metadata)."""
        self._tools_dict = [tool.describe() for tool in self.tools]
        # DEPRACTED[LANGCHAIN]
        # self.tools_langchain = [tool.convert_tool_to_langchain() for tool in self.tools]
        self.tools_pydanticai = [
            tool.convert_tool_to_pydanticai() for tool in self.tools
        ]

    def _generate_default_system_prompt(self) -> str:
        """
        Generates a default, context-aware system prompt that explains the agent’s
        capabilities and available tools in a professional yet natural tone.
        """
        base_intro = (
            "You are a capable and efficient AI assistant. "
            "Your goal is to understand the user's intent and provide accurate, "
            "clear, and contextually relevant responses.\n\n"
        )

        if not self.tools:
            return base_intro + (
                "You do not currently have any external tools. "
                "Rely solely on your reasoning and general knowledge."
            )

        tool_descriptions = "\n".join(
            [
                f"- **{t.name}**: {t.description or 'No description provided.'}"
                for t in self.tools
            ]
        )

        tool_section = (
            "You have access to the following tools. "
            "Use them when they can improve accuracy, retrieve information, "
            "or perform external actions:\n\n"
            f"{tool_descriptions}\n\n"
            "Always explain your reasoning when invoking tools."
        )

        return base_intro + tool_section

    @property
    def tools_dict(self):
        """Returns metadata for all available tools."""
        return self._tools_dict

    @overload
    def tool(self, name: str = None, description: str = None) -> None: ...

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

            self._refresh_tool_metadata()
            return func

        return decorator

    def set_system_prompt(self, func: Callable):
        """
        Decorator for dynamically assigning a system prompt (sync or async).

        Args:
            func (Callable): A function returning a string prompt, sync or async.

        Raises:
            ValueError: If the return value is not a string (and not None).
            TypeError: If the input is not a callable.
        """

        if not callable(func):
            # raise TypeError("Provided system_prompt must be a callable.")
            raise ChainlessError(
                "Provided system_prompt must be a callable.", error_code="TypeError"
            )

        result = func()

        if result is None:
            return func

        if not isinstance(result, str):
            # raise ValueError("system_prompt must return a string if not None.")
            raise ChainlessError(
                "system_prompt must return a string if not None.",
                error_code="ValueError",
            )

        self.system_prompt = result
        return func

    def on_start(self, func: Callable):
        """
        Decorator to register a custom startup function for the agent.

        This function overrides the default model pipeline and is ideal for
        implementing specialized reasoning flows, manual tool orchestration,
        or dynamic prompt assembly.

        Example:
            @agent.on_start
            async def my_custom_flow(ctx: AgentContext):
                system_prompt = await ctx.system_prompt
                # result = await ctx.llm.run(system_prompt)
                return system_prompt
        """
        if not callable(func):
            raise ChainlessError(message=f"on_start must be a callable function.")
        self.custom_start_func = func
        return func

    @deprecated(
        "Use on_start() instead of custom_start(). This method will be removed in future releases."
    )
    def custom_start(self, func: Callable):
        """
        Deprecated: use on_start instead.

        Decorator to assign a custom startup function for the agent.

        The custom function can accept any of: `tools`, `input`, `llm`, `system_prompt`.
        """
        return self.on_start(func)

    async def _run_hooks(self, hooks: list[Callable], value, agent):
        if not hooks:
            return value

        for h in hooks:
            hook = AgentHook(h)
            value = await hook.run(value, agent)
        return value

    @overload
    def run(
        self,
        input: str,
        model: ModelNames = None,
        model_settings: ModelSettings | None = None,
        usage_limits: pai_usage.UsageLimits | None = None,
        usage: pai_usage.Usage | None = None,
        message_history: list[pai_messages.ModelMessage] = None,
        pre_hooks: Optional[list[Callable]] = None,
        post_hooks: Optional[list[Callable]] = None,
        extra_inputs: dict[str, Any] = {},
    ) -> AgentResponse: ...

    def run(
        self,
        input: str,
        model: ModelNames = None,
        model_settings: ModelSettings | None = None,
        usage_limits: pai_usage.UsageLimits | None = None,
        usage: pai_usage.Usage | None = None,
        message_history: list[pai_messages.ModelMessage] = None,
        pre_hooks: Optional[list[Callable]] = None,
        post_hooks: Optional[list[Callable]] = None,
        extra_inputs: dict[str, Any] = {},
    ) -> AgentResponse:
        """
        Executes the agent **synchronously** (blocking) with the given input.

        This method is a synchronous wrapper around the agent's async pipeline.
        Use this if you are in synchronous code. For async usage, use `run_async()`.

        Example:
        ```python
        from chainless import Agent

        agent = Agent(name="translator", model=ModelNames.GEMINI_GEMINI_2_0_FLASH)

        @agent.tool(name="greet")
        def greet(name: str):
            return f"Hello {name}!"

        async def main():
            result = agent.run("Say hello to Alice")
            print(result.output)

        #> "Hello Alice!"
        ```

        Args:
            input: User query or task instruction for the agent.
            model: Optional model override for this run.
            model_settings: Optional fine-tuning settings for the model.
            usage_limits: Optional limits on token usage or model requests.
            usage: Optional existing usage tracker for accumulating stats.
            message_history: Optional conversation history to include.
            pre_hooks: Optional list of pre-processing functions on the input.
            post_hooks: Optional list of post-processing functions on the output.
            extra_inputs: Extra keyword arguments passed to custom start functions.

        Returns:
            AgentResponse: Structured response containing:
                - output: The final output of the agent.
                - usage: Usage information if available.
                - tools_used: Metadata of tools invoked during execution.
        """

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return anyio.run(
                self.run_async,
                input,
                model,
                model_settings,
                usage_limits,
                usage,
                message_history,
                pre_hooks,
                post_hooks,
                extra_inputs,
            )
        else:
            # raise RuntimeError(
            #     "Agent.run() cannot be called inside an async event loop. "
            #     "Use `await agent.run_async(...)` instead."
            # )
            raise ChainlessError(
                "Agent.run() cannot be called inside an async event loop. "
                "Use `await agent.run_async(...)` instead.",
                error_code="RuntimeError",
            )

    async def run_async(
        self,
        input: str,
        model: ModelNames = None,
        model_settings: ModelSettings | None = None,
        usage_limits: pai_usage.UsageLimits | None = None,
        usage: pai_usage.Usage | None = None,
        message_history: list[pai_messages.ModelMessage] = None,
        pre_hooks: Optional[list[Callable]] = None,
        post_hooks: Optional[list[Callable]] = None,
        extra_inputs: dict[str, Any] = {},
    ) -> AgentResponse:
        """
        Executes the agent **asynchronously** with the given input.

        This method runs the agent using async/await and supports full async
        pipelines. Use this in async code. For synchronous usage, use `run()`.

        Example:
        ```python
        from chainless import Agent

        agent = Agent(name="translator", model=ModelNames.GEMINI_GEMINI_2_0_FLASH)

        @agent.tool(name="greet")
        def greet(name: str):
            return f"Hello {name}!"

        async def main():
            result = await agent.run_async("Say hello to Alice")
            print(result.output)

        #> "Hello Alice!"
        ```

        Args:
            input: User query or task instruction for the agent.
            model: Optional model override for this run.
            model_settings: Optional fine-tuning settings for the model.
            usage_limits: Optional limits on token usage or model requests.
            usage: Optional existing usage tracker for accumulating stats.
            message_history: Optional conversation history to include.
            pre_hooks: Optional list of pre-processing functions on the input.
            post_hooks: Optional list of post-processing functions on the output.
            extra_inputs: Extra keyword arguments passed to custom start functions.

        Returns:
            AgentResponse: Structured response containing:
                - output: The final output of the agent.
                - usage: Usage information if available.
                - tools_used: Metadata of tools invoked during execution.
        """
        ToolExecutionTracker.reset()
        user_input = input

        # HOOKS
        pre_hooks = pre_hooks or []
        post_hooks = post_hooks or []

        user_input = await self._run_hooks(pre_hooks, user_input, self)

        # get model_id
        # model_id = getattr(model, "value", self.model_name)
        model_id = validate_model(model or self.model_name, self.name)

        # custom_start_func
        if self.custom_start_func:
            ctx = AgentContext(
                input=user_input,
                
                # DEPRACTED[LANGCHAIN]
                # llm=self.llm,
                system_prompt=self.system_prompt,
                tools=self.tools,
                model_id=model_id,
                extra_inputs=extra_inputs,
            )

            output = await self._safe_run_custom_start(ctx)

            return AgentResponse(output=output, usage=None)
        
        # DEPRACTED[LANGCHAIN]
        # if self.llm and not model:
        #     raise ChainlessError(
        #         message=(
        #             f"Agent '{self.name}' was initialized with a LangChain `llm`, "
        #             f"but the `run()` or `run_async()` method requires a `model` instead.\n"
        #             f"Use `start()` or `start_async()` for legacy LLM execution, "
        #             f"or specify a Chainless model via `model=...`."
        #         )
        #     )

        # PydanticAI fallback
        agent_model = get_agent_model(model_id)

        the_agent = PydanticAgent(
            agent_model,
            name=self.name,
            output_type=self.response_format,
            system_prompt=self.system_prompt,
            instructions=self.instructions,
            end_strategy="exhaustive",
            tools=self.tools_pydanticai,
            prepare_tools=self.prepare_tools,
            retries=self.retries,
            output_retries=self.output_retries,
            history_processors=self.history_processors,
        )

        message_history = message_history or []
        new_message_history = [
            SystemMessage(content=self.system_prompt),
            *message_history,
        ]
        _message_history = (
            to_pydantic(new_message_history) if new_message_history else None
        )

        result = await the_agent.run(
            user_prompt=user_input,
            model=agent_model,
            model_settings=model_settings,
            usage_limits=usage_limits,
            usage=usage,
            message_history=_message_history,
        )

        used = ToolExecutionTracker.get()

        result.output = await self._run_hooks(post_hooks, result.output, self)

        # REMOVED
        # if isinstance(result.output, BaseModel):
        #     _output = result.output.model_dump()
        # elif isinstance(result.output, dict):
        #     _output = result.output
        # else:
        #     _output = result.output

        _output = clean_output_structure(result.output)

        return AgentResponse(
            output=_output,
            usage=result.usage() if hasattr(result, "usage") else None,
            tools_used=used,
        )

    def _run_custom_start(self, user_input: str, **kwargs) -> AgentResponse:
        ctx = AgentContext(
            input=user_input,
            
            # DEPRACTED[LANGCHAIN]
            # llm=self.llm,
            system_prompt=self.system_prompt,
            tools=self.tools_pydanticai,
            model_id=getattr(self.model_name, "value", self.model_name),
            **kwargs,
        )

        if inspect.iscoroutinefunction(self.custom_start_func):
            output = anyio.from_thread.run(self.custom_start_func, ctx)
        else:
            output = self.custom_start_func(ctx)

        return AgentResponse(
            output=output,
            usage=None,
        )

    async def _safe_run_custom_start(self, ctx):
        try:
            if inspect.iscoroutinefunction(self.custom_start_func):
                return await self.custom_start_func(ctx)
            else:
                return await anyio.to_thread.run_sync(self.custom_start_func, ctx)
        except Exception as e:
            raise ChainlessError(
                message=f"Custom start function failed in agent '{self.name}': {e}"
            )

    # DEPRACTED[LANGCHAIN]
    # @deprecated(
    #     "Use run() instead of start(). This method will be removed in future releases."
    # )
    # def start(self, input: str, verbose: bool = False, **kwargs):
    #     """
    #     [DEPRECATED] Use `run()` or `run_async()` instead.

    #     Legacy entry point for LangChain-based agents.
    #     This method will be removed in future releases.

    #     Args:
    #         input (str): The input query or command.
    #         verbose (bool): Enables verbose logging if True.
    #         **kwargs: Additional parameters forwarded to the custom start function.

    #     Returns:
    #         dict: Dictionary with 'output' key containing agent's response.

    #     Example:
    #         agent = Agent(name="test", llm=my_llm)
    #         result = agent.start("Hello, how are you?")
    #         print(result["output"])
    #     """

    #     user_input = input
    #     if self.custom_start_func:
    #         return self._run_custom_start(input, **kwargs)

    #     if self.llm is None:
    #         raise ChainlessError(
    #             message="You need a langchain llm to use start and start_async"
    #         )

    #     # Default agent logic
    #     prompt = ChatPromptTemplate.from_messages(
    #         [
    #             ("system", self.system_prompt or "You are a helpful agent."),
    #             ("human", "{input}"),
    #             MessagesPlaceholder(variable_name="agent_scratchpad"),
    #         ]
    #     )

    #     agent = create_tool_calling_agent(self.llm, self.tools_langchain, prompt)
    #     executor = AgentExecutor(
    #         agent=agent, tools=self.tools_langchain, verbose=verbose
    #     )

    #     result = executor.invoke(
    #         {
    #             "chat_history": [],
    #             "input": user_input,
    #         }
    #     )

    #     return {"output": result}

    # @deprecated(
    #     "Use run_async() instead of start_async(). This method will be removed in future releases."
    # )
    # async def start_async(self, input: str, verbose: bool = False, **kwargs):
    #     """
    #     [DEPRECATED] Use `run()` or `run_async()` instead.

    #     Legacy entry point for LangChain-based agents.
    #     This method will be removed in future releases.

    #     Asynchronously starts the agent execution with the given input.

    #     Args:
    #         input (str): The input query or command.
    #         verbose (bool): Enables verbose logging if True.
    #         **kwargs: Additional parameters forwarded to the custom start function.

    #     Returns:
    #         dict: Dictionary with 'output' key containing agent's response.

    #     Example:
    #         result = await agent.start_async("Hello, how are you?")
    #         print(result["output"])
    #     """
    #     user_input = input
    #     if self.custom_start_func:
    #         return self._run_custom_start(input, **kwargs)

    #     if self.llm is None:
    #         raise ChainlessError(
    #             message="You need a langchain llm to use start and start_async"
    #         )

    #     # Default async agent logic
    #     prompt = ChatPromptTemplate.from_messages(
    #         [
    #             ("system", self.system_prompt or "You are a helpful agent."),
    #             ("human", "{input}"),
    #             MessagesPlaceholder(variable_name="agent_scratchpad"),
    #         ]
    #     )

    #     agent = create_tool_calling_agent(self.llm, self.tools_langchain, prompt)
    #     executor = AgentExecutor(
    #         agent=agent, tools=self.tools_langchain, verbose=verbose
    #     )

    #     result = await anyio.to_thread.run_sync(
    #         executor.invoke,
    #         {
    #             "chat_history": [],
    #             "input": user_input,
    #         },
    #     )

    #     return {"output": result}


    # ----------------------
    # Export & Describe & Metadata
    # ----------------------
    def as_tool(self, description: Optional[str] = None) -> Tool:
        """Agents can be used as tools and are suitable for many usage scenarios"""

        def wrapped_func(input: str):
            result = self.run(input)
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
            result = await self.run_async(input)
            return result["output"]

        return Tool(
            name=self.name,
            description=description or f"Agent async wrapper: {self.name}",
            input_schema=AgentSchema,
            func=wrapped_func,
        )

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
                        tool.input_schema.model_json_schema()
                        if tool.input_schema
                        else None
                    ),
                }
                for tool in self.tools or []
            ],
        }

    def get_metadata(self) -> dict:
        return {
            "name": self.name,
            "system_prompt": self.system_prompt,
            "total_tool": len(self.tools or []),
            "tools": self._tools_dict,
        }

    @deprecated(
        "Use get_metadata() instead of describe(). This method will be removed in future releases."
    )
    def describe(self) -> dict:
        return {
            "name": self.name,
            "system_prompt": self.system_prompt,
            "total_tool": len(self.tools or []),
            "tools": self._tools_dict,
        }

    def __repr__(self):
        return f"<Agent name='{self.name}' tools={self._tools_dict} total_tool={len(self.tools or [])}>"
