from pydantic import BaseModel, Field
from typing import Optional, Any
from pydantic_ai.usage import Usage


from .tool_schema import ToolUsedSchema

class AgentSchema(BaseModel):
    input: str = Field(..., description="")


class AgentResponse(BaseModel):
    output: Any | str
    usage: Optional[Usage] = None
    tools_used: list[ToolUsedSchema] = []
