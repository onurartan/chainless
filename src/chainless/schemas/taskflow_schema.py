import uuid
from enum import Enum

from pydantic import BaseModel, field_validator, Field
from typing import Optional, Dict, Any, Callable, List

from .tool_schema import ToolUsedSchema

import pydantic_ai.messages as pai_messages


class TaskStep(BaseModel):
    step_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    step_name: Optional[str] = None
    agent_name: str
    input_map: Dict[str, Any]
    prompt_template: Optional[str] = None
    retry_on_fail: Optional[int] = None
    timeout: Optional[int] = None
    message_history: Optional[list[pai_messages.ModelMessage]] = None

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


class AgentStep(BaseModel):
    name: str
    output: Optional[Any] = None
    tools_used: List[ToolUsedSchema] = []
    total_tokens: Optional[int] = None
    request_count: Optional[int] = None


class UsageSummary(BaseModel):
    total_requests: Optional[int] = None
    total_tokens: Optional[int] = None


class FlowSummary(BaseModel):
    # REMOVED[OLD]
    # steps: List[AgentStep] = []
    steps: Dict[str, AgentStep] = {}
    usage_summary: Optional[UsageSummary] = None


class FlowOutput(BaseModel):
    flow: FlowSummary
    output: Any

    @classmethod
    def from_flow_output(
        cls,
        output: Dict,
    ):
        """
        Simplifies the complex dictionary structure returned by Chainless TaskFlow
        and converts it to a SuccessResponse.
        """
        flow_data = output.get("flow", {})
        # steps = []
        steps = {}

        for agent_name, agent_data in flow_data.items():

            if not agent_data or not isinstance(agent_data, dict):
                agent_data = {}

            usage = agent_data.get("usage") or {}
            tools_used_raw = agent_data.get("tools_used") or []

            tools_used = [
                ToolUsedSchema(
                    tool_name=t["tool_name"],
                    input=t.get("input"),
                    output=t.get("output"),
                    status=str(t.get("status")),
                    start_time=t.get("start_time"),
                    end_time=t.get("end_time"),
                    duration=t.get("duration"),
                    error=t.get("error"),
                )
                for t in tools_used_raw
            ]
            agent_s_output = agent_data.get("output")

            if isinstance(agent_data.get("output"), dict):
                agent_s_output = agent_data.get("output").get(
                    "output", agent_data.get("output")
                )
            
            # REMOVED[OLD]
            # steps.append(
            #     AgentStep(
            #         name=agent_name,
            #         output=agent_s_output,
            #         tools_used=tools_used,
            #         total_tokens=usage.get("total_tokens") or 0,
            #         request_count=usage.get("requests") or 0,
            #     )
            # )
            steps[agent_name] = AgentStep(
                name=agent_name,
                output=agent_s_output,
                tools_used=tools_used,
                total_tokens=usage.get("total_tokens") or 0,
                request_count=usage.get("requests") or 0,
            )

        total_tokens = sum((s.total_tokens or 0) for s in steps.values())
        total_requests = sum((s.request_count or 0) for s in steps.values())

        flow_output = output.get("output")

        if isinstance(output.get("output"), dict):
            flow_output = output.get("output").get("output", output.get("output"))

        return cls(
            flow=FlowSummary(
                steps=steps,
                usage_summary=UsageSummary(
                    total_tokens=total_tokens,
                    total_requests=total_requests,
                ),
            ),
            output=flow_output,
        )


class LogLevel(Enum):
    INFO = "info"
    ERROR = "error"
