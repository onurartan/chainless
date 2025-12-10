import time
import typing
import anyio
import inspect
from functools import wraps

from typing import Callable, Optional, Type, Any, Dict
from pydantic import BaseModel, ValidationError, create_model

from chainless.logger import get_logger
from chainless.schemas.tool_schema import ToolUsedSchema, ToolUsedStatusEnum

from pydantic_ai.tools import Tool as PydanticTool
from pydantic_ai import tools as pai_tools
from pydantic.json_schema import GenerateJsonSchema

# DEPRACTED[LANGCHAIN]
# from langchain_core.tools import StructuredTool


class ToolInputValidationError(Exception):
    """Raised when tool input validation fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.details = details or {}

    def __str__(self):
        return f"[ToolInputValidationError] {super().__str__()}"


class ToolExecutionTracker:
    """
    Tracker to record detailed tool execution info per run.
    """

    _executions: list[ToolUsedSchema] = []

    @classmethod
    def reset(cls):
        cls._executions = []

    @classmethod
    def start(cls, tool_name: str, input_data: Dict[str, Any] = None):

        entry = ToolUsedSchema(
            tool_name=tool_name,
            start_time=time.time(),
            end_time=None,
            status=ToolUsedStatusEnum.RUNNING,
            input=input_data or {},
            output=None,
            duration=0.0,
            error=None,
        )
        cls._executions.append(entry)
        return entry

    @classmethod
    def finish(cls, tool_name: str, output: Any = None, error: Exception = None):
        for entry in reversed(cls._executions):
            if (
                entry.tool_name == tool_name
                and entry.status == ToolUsedStatusEnum.RUNNING
            ):
                entry.end_time = time.time()
                entry.duration = entry.end_time - entry.start_time
                entry.status = (
                    ToolUsedStatusEnum.FAILED if error else ToolUsedStatusEnum.SUCCESS
                )
                entry.output = output
                if error:
                    entry.error = str(error)
                break

    @classmethod
    def get(cls) -> list[Dict[str, Any]]:
        return cls._executions.copy()


class Tool:
    """
    Wraps a sync or async function into a structured, schema-aware tool.

     Features:
         - Input validation via Pydantic schema
         - Sync/Async execution
         - Execution tracking and logging
         - PydanticAI compatibility

     Args:
         name: Tool name
         description: Human-readable description
         func: Function to wrap (sync or async)
         input_schema: Optional Pydantic schema to validate inputs
         raise_on_error: Whether to raise exceptions on failure
    """

    def __init__(
        self,
        name: str,
        description: str,
        func: Callable[..., Any],
        input_schema: Optional[Type[BaseModel]] = None,
        raise_on_error: Optional[bool] = True,
    ):
        self.name = name
        self.description = description
        self.func = func
        self.input_schema = input_schema
        self._is_async = inspect.iscoroutinefunction(func)
        self.raise_on_error = raise_on_error

        self.logger = get_logger(f"Tool[{self.name}]")

    @staticmethod
    def tool(
        name: Optional[str] = None,
        description: Optional[str] = None,
        input_schema: Optional[type] = None,
        raise_on_error: bool = True,
    ):
        """
        Decorator to wrap a function as a Tool instance.

        Usage:
            @Tool.tool()
            def my_func(...): ...

            @Tool.tool(name="Custom", description="Custom desc")
            def other_func(...): ...
        """

        def decorator(func: Callable):
            tool_name = name or func.__name__
            tool_description = description or (
                func.__doc__ or "No description provided."
            )
            return Tool(
                name=tool_name,
                description=tool_description,
                func=func,
                input_schema=input_schema,
                raise_on_error=raise_on_error,
            )

        return decorator

    def execute(self, input_data: Dict[str, Any]) -> Any:
        """
        Executes the tool with validated inputs and runtime tracking.

        This is the main entry point to run a tool instance. It validates inputs,
        executes the underlying function (sync or async), tracks execution details,
        and logs results.

        ---
        Parameters
        ----------
        input_data : dict
            The input parameters to be passed to the tool. If a Pydantic schema
            is defined, the data will be validated before execution.

        ---
        Returns
        -------
        Any
            The output of the wrapped function. Returns `None` if an error occurs
            and `raise_on_error=False`.

        ---
        Raises
        ------
        ToolInputValidationError
            If the input data does not match the defined schema.
        Exception
            Any runtime error raised during execution if `raise_on_error=True`.

        ---
        Example
        -------
        ```python
        from chainless import Tool
        from pydantic import BaseModel


        class AddInput(BaseModel):
            a: int
            b: int

        @Tool.tool(name="Adder", description="Adds two numbers", input_schema=AddInput)
        def add(a: int, b: int) -> int:
            return a + b

        result = add.execute({"a": 3, "b": 4})
        print(result)  # 7
        ```
        """
        entry = ToolExecutionTracker.start(self.name, input_data)
        
        self.logger.info(f"'{self.name}' starting with input={input_data}")
        try:
            validated_input = self._validate_input(input_data)

            if self._is_async:
                result = anyio.run(self._run_async_safe, validated_input)
            else:
                result = self._run_sync(validated_input)

            ToolExecutionTracker.finish(self.name, output=result)
            self.logger.info(
                f"'{self.name}' finished successfully with output={result}"
            )
            return result

        except Exception as e:
            ToolExecutionTracker.finish(self.name, error=e)
            self.logger.error(f"'{self.name}' failed: {e}")
            if self.raise_on_error:
                raise
            return None

    def _validate_input(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        if not self.input_schema:
            return input_data or {}

        try:
            validated = self.input_schema(**(input_data or {}))
            return validated.model_dump()
        except ValidationError as e:
            messages = []
            for err in e.errors():
                loc = " -> ".join(str(x) for x in err.get("loc", []))
                msg = err.get("msg", "Unknown error")
                messages.append(f"Field `{loc}` error: {msg}")
            full_message = f"Input validation failed:\n" + "\n".join(messages)
            self.logger.error(full_message)
            raise ToolInputValidationError(full_message, e.errors())

    def _run_sync(self, validated_input: Dict[str, Any]) -> Any:
        try:
            return self.func(**validated_input)
        except Exception as e:
            self.logger.error(f"Synchronous execution failed: {str(e)}")
            raise

    async def _run_async_safe(self, validated_input: Dict[str, Any]) -> Any:
        try:
            return await self.func(**validated_input)
        except Exception as e:
            self.logger.error(f"Asynchronous execution failed: {str(e)}")
            raise

    def describe(self) -> Dict[str, Any]:
        """
        Generates structured metadata for the tool (name, description, parameters)
        """
        param_schema = (
            self.input_schema.model_json_schema()["properties"]
            if self.input_schema
            else {}
        )

        parameters = {
            param: {
                "type": detail.get("type", "unknown"),
                "description": detail.get("description", "No description provided."),
            }
            for param, detail in param_schema.items()
        }

        return {
            "name": self.name,
            "description": self.description,
            "parameters": parameters,
        }

    def convert_tool_to_pydanticai(self) -> PydanticTool:
        """
        Converts the tool into a PydanticAI-compatible Tool with automatic
        fallback type hints if the user did NOT define any.
        """

        # -------------------------------
        # AUTO TYPE-HINT FALLBACK SECTION
        # -------------------------------
        sig = inspect.signature(self.func)
        type_hints = {}

        try:
            type_hints = typing.get_type_hints(self.func)
        except Exception:
            # ignore — we'll fallback anyway
            type_hints = {}

        # If user provided ZERO type hints → auto assign str
        if not type_hints:
            fallback_schema = {}
            for name, param in sig.parameters.items():
                # if self is present in methods, skip
                if name in ("self", "cls"):
                    continue
                fallback_schema[name] = (str, ...)
                
            
            AutoSchemaModel = create_model(f"{self.name}AutoInputSchema", **fallback_schema)
            input_model = AutoSchemaModel
        else:
            # user provided types → respect them
            if self.input_schema:
                input_model = self.input_schema
            else:
                # Build Pydantic model from annotations
                fields = {}
                for name, annotation in type_hints.items():
                    if name not in ("self", "cls"):
                        fields[name] = (annotation, ...)
                input_model = create_model(f"{self.name}Input", **fields)

        # create proxy wrapper
        @wraps(self.func)
        def proxy_func(**kwargs):
            return self.execute(kwargs)

        if not hasattr(input_model, "takes_ctx"):
            setattr(input_model, "takes_ctx", False)
            
        fs = pai_tools._function_schema.function_schema(
        function=proxy_func,        
        schema_generator=GenerateJsonSchema, 
        takes_ctx=False
)

        return PydanticTool(
            name=self.name,
            description=self.description,
            function=proxy_func,
            function_schema=fs,
        )
        
    # DEPRACTED[LANGCHAIN]
    # def convert_tool_to_langchain(self) -> StructuredTool:
    #     """
    #     Converts the tool into a LangChain-compatible StructuredTool instance.

    #     Returns:
    #         StructuredTool: A LangChain-wrapped version of this tool.
    #     """
    #     return StructuredTool.from_function(
    #         name=self.name,
    #         description=self.description,
    #         args_schema=self.input_schema,
    #         func=self.execute,
    #     )

    def __call__(self, *args, **kwargs) -> Any:
        input_data = kwargs if kwargs else (args[0] if args else {})
        return self.execute(input_data)

    def __str__(self) -> str:
        return f"Tool(name='{self.name}', description='{self.description}')"
