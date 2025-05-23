from pydantic import BaseModel, field_validator
from typing import Optional, Dict, Any, Callable, List
from enum import Enum


class TaskStep(BaseModel):
    step_name: Optional[str] = None  # NEW
    agent_name: str
    input_map: Dict[str, Any]
    retry_on_fail: Optional[int] = None
    timeout: Optional[int] = None

    # NEW
    condition: Optional[Callable[[dict], bool]] = None
    on_start: Optional[Callable] = None
    on_complete: Optional[Callable] = None
    on_error: Optional[Callable] = None
    depends_on: Optional[List[str]] = []

    @field_validator("step_name")
    def default_step_name(cls, v, values):
        if v is None:
            return values.get("agent_name")
        return v


class LogLevel(Enum):
    INFO = "info"
    ERROR = "error"
