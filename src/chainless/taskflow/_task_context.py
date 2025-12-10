import re
import uuid

from typing import Dict, List, Optional, Callable, Union, Any
from pydantic import BaseModel

from chainless.schemas import LogLevel, TaskStep
from chainless._utils.exception import ChainlessError
from chainless.logger import get_logger


RESERVED_KEYS = {
    "input",
    "model",
    "model_settings",
    "usage_limits",
    "usage",
    "message_history",
    "pre_hooks",
    "post_hooks",
    "extra_inputs",
}


class TaskContext:
    """
    Represents the execution context of a task, storing step outputs, agents, and providing
    methods for resolving inputs and prompts, including template placeholders like {{input}} or {{agent.key}}.

    Attributes:
        task_id (str): Unique identifier for the task.
        name (str): Name of the task.
        verbose (bool): If True, logs extra information.
        logger: Logger instance scoped to this task.
        initial_input: Initial input provided to the task.
        steps (List[TaskStep]): Steps executed within this task.
        agents (dict): Dictionary of agent instances.
        step_outputs (dict): Stores outputs of each step.
        _aliases (dict): Mapping of alias keys to step outputs.
        retry_on_fail (int): Number of retries allowed on failure.
        on_step_start/on_step_complete/on_step_error (Callable | None): Optional hooks.
    """


    def __init__(self, name: str, verbose: bool = False):
        self.task_id = str(uuid.uuid4())
        self.name = name
        self.verbose = verbose
        self.logger = get_logger(f"[TaskFlow:{self.name}]")
        self.initial_input = ""

        self.steps: List[TaskStep] = []
        self.agents = {}
        self.step_outputs: Dict[str, dict] = {}
        self._aliases = {}

        self.retry_on_fail = 0

        self.on_step_start: Optional[Callable] = None
        self.on_step_complete: Optional[Callable] = None
        self.on_step_error: Optional[Callable] = None

    def _log(self, message: str, level: LogLevel = LogLevel.INFO):
        if self.verbose:
            if level == LogLevel.INFO:
                self.logger.info(message)
            elif level == LogLevel.ERROR:
                self.logger.error(message)
            else:
                self.logger.info(message)

    def split_inputs(self, resolved_inputs: dict) -> tuple[dict, dict]:
        """
        Splits input dictionary into reserved keys and extra inputs.

        Returns:
            Tuple[dict, dict]: (reserved, extra) dictionaries.
        """
        reserved = {}
        extra = {}

        for key, val in resolved_inputs.items():
            if key in RESERVED_KEYS:
                reserved[key] = val
            else:
                extra[key] = val

        return reserved, extra

    
    def resolve_input(self, input_map: dict) -> dict:
        """
        Resolves template placeholders like '{{input}}' or '{{agent.key}}' into actual values.

        Raises:
            ChainlessError: If a reference cannot be resolved.

        Returns:
            dict: Resolved input dictionary with 'extra_inputs' key for additional data.
        """
        resolved = {}
        for key, val in input_map.items():
            try:
                resolved[key] = self._resolve_value(val)
            except ChainlessError as e:
                self._log(f"[resolve_input] Failed to resolve key '{key}': {e}", LogLevel.ERROR)
                raise
            except Exception as e:
                self._log(f"[resolve_input] Unexpected error for key '{key}': {e}", LogLevel.ERROR)
                raise ChainlessError(f"Failed to resolve '{key}': {e}")
            
        reserved, extra = self.split_inputs(resolved)
        reserved["extra_inputs"] = extra
        return reserved
    
    def _resolve_value(self, val: Any) -> Any:
        """Internal helper to resolve a single value."""
        if isinstance(val, str) and "{{" in val:
            if "{{input}}" in val:
                return self.initial_input
            
            template = val.strip("{} ").strip()
            if template in self._aliases:
                from_step, from_key = self._aliases[template]
                step_output = self.step_outputs.get(from_step)
                if step_output is None:
                     raise ChainlessError(f"Step '{from_step}' has no output to resolve '{from_key}'.")
                return self._resolve_nested_references(step_output, self._split_reference(from_key), step_name=from_step)
            return self._resolve_references(template)
        return val

    def extract_relevant_content(self, value):
        """
        Extracts meaningful content from dict, BaseModel, or objects with 'content' attribute.

        Returns:
            str: Extracted string content.
        """

        if isinstance(value, dict):
            if "output" in value:
                return self.extract_relevant_content(value["output"])
            if "content" in value:
                return self.extract_relevant_content(value["content"])
            return str(value)

        if isinstance(value, BaseModel):
                dict_val = value.model_dump()
                return self.extract_relevant_content(dict_val)


        if hasattr(value, "content"):
            return self.extract_relevant_content(value.content)

        return str(value)

    def resolve_prompt(
        self, prompt_template: Optional[str], resolved_inputs: dict
    ) -> Union[str, None]:
        """
        Fills {{key}} placeholders in prompt_template using resolved_inputs['extra_inputs'].

        Raises:
            ChainlessError: If a placeholder key is missing.

        Returns:
            Optional[str]: Resolved prompt string or None if template is None.
        """

        if prompt_template is None:
            return None

        simple_inputs = {
            k: self.extract_relevant_content(v)
            for k, v in resolved_inputs["extra_inputs"].items()
        }

        from string import Template
        template_str = re.sub(r"\{\{(\w+)\}\}", r"$\1", prompt_template)
        template = Template(template_str)
        
        try:
            resolved_prompt = template.substitute(simple_inputs)
        except KeyError as e:
            self._log(f"[resolve_prompt] Missing key in template: {e}", LogLevel.ERROR)
            raise ChainlessError(f"Prompt template missing key: {e}")

        return resolved_prompt

    def _resolve_references(self, agent_ref: str):
        """Resolve a reference string to its actual value in step_outputs."""
        parts = self._split_reference(agent_ref)
        step_name = parts[0]
        step_output = self.step_outputs.get(step_name)
        if step_output is None:
            raise ChainlessError(
                message=f"Cannot resolve reference '{agent_ref}': step '{step_name}' has no output."
            )
        return self._resolve_nested_references(
            step_output, parts[1:], step_name=step_name
        )

    def _split_reference(self, agent_ref: str):
        return [part for part in re.split(r"[\.\[\]]+", agent_ref) if part]

    def _resolve_nested_references(self, current_data, parts, step_name: str = None):
        """
        Recursively resolve nested references in dict, list, or BaseModel.

        Raises:
            ChainlessError: If any key, index, or attribute is invalid.
        """
        if not parts:
            return current_data

        part = parts[0]
        
        try:
            if isinstance(current_data, dict):
                if part not in current_data:
                    raise ChainlessError(f"Dict key '{part}' not found in step ' {step_name or '?'}'.")
                return self._resolve_nested_references(current_data[part], parts[1:], step_name)
            elif isinstance(current_data, list):
                index = int(part)
                if index >= len(current_data):
                    raise ChainlessError(f"List index '{index}' out of range for step '{step_name or '?'}'.")
                return self._resolve_nested_references(current_data[index], parts[1:], step_name)
            elif isinstance(current_data, BaseModel):
                current_dict = current_data.model_dump()
                if part not in current_dict:
                    raise ChainlessError(f"Attribute '{part}' not found in BaseModel '{type(current_data).__name__}' for step '{step_name or '?'}'.")
                return self._resolve_nested_references(current_dict[part], parts[1:], step_name)
            else:
                raise ChainlessError(f"Cannot resolve part '{part}': unsupported type '{type(current_data).__name__}' for step '{step_name or '?'}'.")
        except ValueError as e:
            raise ChainlessError(f"Invalid index '{part}' in step '{step_name or '?'}': {e}")

        
    def _get_step_by_name(self, step_name: str) -> TaskStep:
        """Retrieve a TaskStep by name, raise ChainlessError if not found."""
        for step in self.steps:
            if step.step_name == step_name:
                return step
        raise ChainlessError(f"Step '{step_name}' does not exist in the task flow.")
