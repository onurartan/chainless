import re
import uuid
from typing import Dict
from pydantic import BaseModel
from typing import List, Optional, Callable
from ..._schemas import LogLevel

from ..._schemas import TaskStep
from ...logger import get_logger


class TaskContext:
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
        """
        verbose=true is used to generate outputs
        LOG MANGER (soon)
        """
        if self.verbose:
            if level == LogLevel.INFO:
                self.logger.info(message)
            elif level == LogLevel.ERROR:
                self.logger.error(message)
            else:
                self.logger.info(message)

    def resolve_input(self, input_map: dict) -> dict:
        """
        Resolve input mappings by replacing template variables with actual values.

        Supports placeholders like '{{input}}' for initial input or nested references
        such as '{{agent_name.output_key}}' to previous step outputs.

        Args:
            input_map (dict): Input dictionary possibly containing template strings.

        Returns:
            dict: Input map with resolved values.
        """
        resolved = {}
        for key, val in input_map.items():
            try:
                if isinstance(val, str) and "{{" in val:
                    if "{{input}}" in val:
                        resolved[key] = getattr(self, "initial_input", None)
                    else:
                        template = val.strip("{} ").strip()
                        if template in self._aliases:
                            from_step, from_key = self._aliases[template]
                            step_output = self.step_outputs.get(from_step, {})
                            value = self._resolve_nested_references(
                                step_output, self._split_reference(from_key)
                            )
                            resolved[key] = value
                        else:
                            parts = self._resolve_references(template)
                            resolved[key] = parts
                else:
                    resolved[key] = val
            except Exception as e:
                self._log(f"[resolve_input] Error resolving key ({key}): {e}")
                resolved[key] = None
        return resolved

    def _resolve_references(self, agent_ref: str):
        parts = self._split_reference(agent_ref)
        agent_name = parts[0]
        step_output = self.step_outputs.get(agent_name, {})
        return self._resolve_nested_references(step_output, parts[1:])

    def _split_reference(self, agent_ref: str):
        return [part for part in re.split(r"[\.\[\]]+", agent_ref) if part]

    def _resolve_nested_references(self, current_data, parts):
        if not parts:
            return current_data
        part = parts[0]
        try:
            if isinstance(current_data, dict):
                return self._resolve_nested_references(
                    current_data.get(part), parts[1:]
                )
            elif isinstance(current_data, list):
                index = int(part)
                return self._resolve_nested_references(current_data[index], parts[1:])
            elif isinstance(current_data, BaseModel):
                return self._resolve_nested_references(
                    getattr(current_data, part), parts[1:]
                )
        except Exception as e:
            self._log(f"[resolve_nested_references] Hata: {e}")
        return None

    def _get_step_by_name(self, step_name: str):
        try:
            return next(s for s in self.steps if s.step_name == step_name)
        except StopIteration:
            raise ValueError(
                f"Step with name '{step_name}' does not exist in the task flow."
            )
