from dataclasses import dataclass
from pydantic import BaseModel

from typing import Any, Dict, Optional, List

# DEPRACTED[LANGCHAIN]
# from langchain_core.language_models.chat_models import BaseChatModel

import pydantic_ai.messages as pai_messages
import pydantic_ai.usage as pai_usage
from pydantic_ai.settings import ModelSettings

from chainless.models import ModelNames

@dataclass
class AgentProtocolRunContext:
    input: str
    model: Optional[ModelNames] = None
    model_settings: Optional[ModelSettings] = None
    usage_limits: Optional[pai_usage.UsageLimits] = None
    usage: Optional[pai_usage.Usage] = None
    message_history: Optional[List[pai_messages.ModelMessage]] = None
    extra_inputs: dict[str, Any] = None
    
    

class AgentContext(BaseModel):
    input: str | None = None
    
    # DEPRACTED[LANGCHAIN]
    # llm: Optional[BaseChatModel] = None
    
    model_id: Optional[str] = None
    system_prompt: str | None = None
    tools: list[Any] = []
    extra_inputs: dict[str, Any] = {}

    class Config:
        extra = "allow"


class FlowState(BaseModel):
    steps: Dict[str, Any] = {}
