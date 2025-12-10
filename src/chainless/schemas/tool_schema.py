from pydantic import BaseModel
from typing import Any, Optional
from enum import Enum


class ToolUsedStatusEnum(Enum):
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"

class ToolUsedSchema(BaseModel):
    tool_name: str
    input: Any
    output: Any
    status: ToolUsedStatusEnum
    start_time: float = 0.0
    end_time: Optional[float] = None
    duration: float = 0.0
    error: Optional[str] = None