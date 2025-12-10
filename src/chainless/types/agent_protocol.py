from chainless.schemas.agent_schema import AgentResponse
from chainless.schemas.context import AgentProtocolRunContext

# Types
from typing import Protocol, runtime_checkable


@runtime_checkable
class AgentProtocol(Protocol):
    name: str
    
    # DEPRECATED [LANGCHAIN]
    # def start(self, input: str, verbose: bool = False, **kwargs) -> dict: ...

    def run(
        self,
        ctx: AgentProtocolRunContext
        
        # AgentProtocolRunContext INCLUDES
        # input: str,
        # model: ModelNames = None,
        # model_settings: ModelSettings | None = None,
        # usage_limits: pai_usage.UsageLimits | None = None,
        # usage: pai_usage.Usage | None = None,
        # message_history: list[pai_messages.ModelMessage] = None,
        # extra_inputs: dict[str, Any] = {},
        
    ) -> AgentResponse: ...
