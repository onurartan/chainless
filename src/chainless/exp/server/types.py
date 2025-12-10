from typing import Any, Callable, Optional, Union
from typing import List, Dict, Sequence

from datetime import datetime, timezone

from pydantic import BaseModel, Field
from enum import Enum

from fastapi import Response
from chainless.schemas.taskflow_schema import (
    FlowSummary,
    FlowOutput,
)


class ErrorCode(str, Enum):
    OK = "OK"
    INVALID_INPUT = "INVALID_INPUT"
    AUTH_FAILED = "AUTH_FAILED"
    FLOW_RUNTIME_ERROR = "FLOW_RUNTIME_ERROR"
    TIMEOUT = "TIMEOUT"
    CONFIG_ERROR = "CONFIG_ERROR"
    DUPLICATE_PATH = "DUPLICATE_PATH"
    INTERNAL = "INTERNAL"


class SuccessResponse(BaseModel):
    success: bool = True
    code: str = ErrorCode.OK
    message: str = "OK"

    flow: Optional[str] = None
    trace_id: str

    flow_summary: Optional[FlowSummary] = None
    final_output: Optional[Any] = None

    duration_seconds: Optional[Union[int, float]] = None

    timestamp: int = Field(
        default_factory=lambda: int(datetime.now(timezone.utc).timestamp() * 1000)
    )

    @classmethod
    def generate_resp(
        cls, flow_name: str, output: FlowOutput, trace_id: str, duration: float
    ):
        """
        Simplifies the complex dictionary structure returned by Chainless TaskFlow
        and converts it to a SuccessResponse.
        """

        return cls(
            flow=flow_name,
            trace_id=trace_id,
            flow_summary=output.flow,
            final_output=output.output,
            duration_seconds=duration,
        )


class FlowServerConfig(BaseModel):
    title: str = "Chainless FlowServer"
    description: str = "FlowServer API"
    version: str = "0.2.0"
    debug: bool = False
    docs_url: Optional[str] = "/docs"
    redoc_url: Optional[str] = "/redoc"
    openapi_url: Optional[str] = "/openapi.json"
    openapi_prefix: str = ""
    openapi_tags: Optional[List[Dict[str, Any]]] = None
    default_response_class: type = Response
    root_path: str = ""
    root_path_in_servers: bool = True
    terms_of_service: Optional[str] = None
    contact: Optional[Dict[str, str]] = None
    license_info: Optional[Dict[str, str]] = None
    dependencies: Optional[Sequence[Callable]] = None
    middleware: Optional[Sequence[Callable]] = None
    exception_handlers: Optional[Dict[Any, Callable]] = None
    lifespan: Optional[Callable] = None
    callbacks: Optional[List[Callable]] = None
    deprecated: Optional[bool] = None
    include_in_schema: bool = True
    swagger_ui_parameters: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    success: bool = False
    code: str
    message: str
    details: Optional[Any] = None
    flow: Optional[str] = None
    trace_id: str
    timestamp: int = Field(
        default_factory=lambda: int(datetime.now(timezone.utc).timestamp() * 1000)
    )


class FlowEndpoint(BaseModel):
    flow_name: str
    path: str
    flow_runner: Callable[[Any], Union[dict, Any]]
    timeout_seconds: Optional[float] = None


class FlowExecutionError(Exception):
    def __init__(
        self,
        code: ErrorCode,
        message: str,
        details: Any = None,
        status_code: int = 400,
        flow: Optional[str] = None,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details
        self.status_code = status_code
        self.flow = flow


class FlowRequest(BaseModel):
    input: Any
