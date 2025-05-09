from typing import Callable, Optional, Type, Any, Dict
from pydantic import BaseModel, ValidationError
import asyncio
import inspect
from chainless.logger import get_logger

# from langchain_core.tools import Tool as LangChainTool
from langchain_core.tools import StructuredTool


class ToolInputValidationError(Exception):
    """Raised when tool input validation fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.details = details or {}

    def __str__(self):
        return f"[ToolInputValidationError] {super().__str__()}"


class Tool:
    """
    A utility class that wraps a sync or async function into a structured, schema-aware tool.

    This class is primarily designed to be used with AI agents or orchestration systems,
    such as LLM pipelines. It provides input validation (via Pydantic), execution safety,
    runtime metadata, and LangChain compatibility.

    Args:
        name (str): The tool’s name (used in routing or LLM prompt references).
        description (str): A human-readable description of the tool's purpose.
        func (Callable): The function to wrap. Can be synchronous or asynchronous.
        input_schema (Optional[Type[BaseModel]]): Optional Pydantic schema to validate inputs.
        raise_on_error (bool, optional): Whether to raise exceptions on failure. Defaults to True.
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

        self.logger = get_logger(f"Tool[{self.name}]")

        self.raise_on_error = raise_on_error

    # Used for Tool Calls
    def execute(self, input_data: Dict[str, Any]) -> Any:
        """
        Executes the tool function with validated inputs.

        Automatically determines whether the function is sync or async and invokes it safely.
        If input_schema is defined, validation is enforced.

        Args:
            input_data (Dict[str, Any]): Input arguments to the function.

        Returns:
            Any: The result of the function execution.

        Raises:
            ToolInputValidationError: If input validation fails.
            Exception: If function execution fails (unless raise_on_error is False).
        """
        try:
            validated_input = self._validate_input(input_data)
            self.logger.warning("Running.")

            if self._is_async:
                try:

                    return asyncio.run(self._run_async_safe(validated_input))
                except RuntimeError:
                    self.logger.warning(
                        "Detected active event loop, using asyncio.create_task."
                    )
                    return asyncio.get_event_loop().run_until_complete(
                        self._run_async_safe(validated_input)
                    )
            else:
                return self._run_sync(validated_input)
        except Exception as e:
            self.logger.error(f"Tool execution failed: {str(e)}")
            if self.raise_on_error:
                raise {"error": str(e)}

    def _validate_input(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validates input against the Pydantic schema, if one is provided.

        Args:
            input_data (Dict[str, Any]): Raw input data.

        Returns:
            Dict[str, Any]: Validated and parsed input.

        Raises:
            ToolInputValidationError: If input validation fails.
        """
        if not self.input_schema:
            return input_data or {}

        try:
            validated = self.input_schema(**input_data or {})
            return validated.model_dump()
        except ValidationError as e:
            messages = []
            for err in e.errors():
                loc = " -> ".join(str(x) for x in err.get("loc", []))
                msg = err.get("msg", "Unknown error")
                input_val = err.get("input", None)
                messages.append(
                    f"Field `{loc}` error:\n"
                    f" - Reason     : {msg}\n"
                    f" - Provided   : {repr(input_val)}"
                )

            full_message = "Input validation failed:\n" + "\n".join(messages)
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
        Generates structured metadata for the tool, suitable for LLM agents or UIs.

        Returns:
            Dict[str, Any]: Metadata including name, description, and parameter schema.
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
        # for param, detail in param_schema.items():
        #     parameters[param] = {
        #         "type": detail.get("type", "unknown"),
        #         "description": detail.get("description", "No description provided."),
        #     }

        return {
            "name": self.name,
            "description": self.description,
            "parameters": parameters,
        }

    def convert_tool_to_langchain(self) -> StructuredTool:
        """
        Converts the tool into a LangChain-compatible StructuredTool instance.

        Returns:
            StructuredTool: A LangChain-wrapped version of this tool.
        """
        return StructuredTool.from_function(
            name=self.name,
            description=self.description,
            args_schema=self.input_schema,
            func=self.func,
        )

    def __str__(self) -> str:
        return f"Tool(name='{self.name}', description='{self.description}')"
