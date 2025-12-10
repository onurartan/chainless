"""
[!INFO]
EXPERIMENTAL is a special feature; many errors and unexpected results may occur.
"""

import uuid
import time
import inspect

import contextlib

from typing import List, Optional, Callable

import anyio
import anyio.to_thread
import uvicorn

from fastapi import FastAPI, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse

import chainless
from chainless.logger import get_logger

from .types import FlowServerConfig
from .types import (
    FlowEndpoint,
    FlowRequest,
    FlowExecutionError,
    ErrorCode,
    ErrorResponse,
    SuccessResponse,
)
from chainless.schemas.taskflow_schema import FlowOutput, FlowSummary

logger = get_logger()


def _short_preview(obj: object, max_len: int = 512) -> str:
    """
    Return a short string preview of an object for logging/response previews.
    Avoid printing extremely large content into logs/responses.
    """
    try:
        s = str(obj)
    except Exception:
        s = "<unserializable>"
    if len(s) > max_len:
        return s[: max_len - 3] + "..."
    return s


class FlowServer:
    """
    FlowServer: lightweight Flow runner HTTP server built on FastAPI.

    Improvements vs. experimental version:
      - structured logging for requests/responses/exceptions
      - per-request trace_id and timestamps
      - centralized safe runner for sync/async flows with timeout handling
      - improved exception handlers that include trace_id
      - clearer validation and error codes

    Usage:
        server = FlowServer(endpoints=[...], api_key="my-secret", host="0.0.0.0", port=8080)
        server.run(reload=False)
    """

    def __init__(
        self,
        endpoints: List[FlowEndpoint],
        api_key: str,
        host: str = "localhost",
        port: int = 8000,
        app: Optional[FastAPI] = None,
        default_timeout: Optional[float] = 30.0,
        app_config: Optional[FlowServerConfig] = None,
    ):
        """
        endpoints: list of FlowEndpoint dataclass instances
        app: optional FastAPI instance to mount onto (if None, a new FastAPI app is created)
        default_timeout: used when endpoint.timeout_seconds is None
        """
        self.app = app or FastAPI(**(app_config.model_dump() if app_config else {}))
        self.host = host
        self.port = port
        self.api_key = api_key
        self.default_timeout = default_timeout
        self._validate_endpoint_configs(endpoints)
        self.endpoints = endpoints

        self.start_time = time.time()
        self.security = HTTPBearer(auto_error=False)

        # register handlers and endpoints
        self._register_exception_handlers()
        self._register_endpoints()
        self._register_healthz()

        self.app.middleware("http")

        async def _request_logger(request: Request, call_next):
            trace_id = str(uuid.uuid4())
            request.state.trace_id = trace_id
            start_ts = time.time()
            try:
                response = await call_next(request)
                duration_ms = int((time.time() - start_ts) * 1000)
                logger.info(
                    {
                        "event": "http_request",
                        "trace_id": trace_id,
                        "method": request.method,
                        "path": request.url.path,
                        "status_code": response.status_code,
                        "duration_ms": duration_ms,
                    }
                )
                return response
            except Exception as exc:
                logger.exception(
                    {
                        "event": "http_request_error",
                        "trace_id": trace_id,
                        "method": request.method,
                        "path": request.url.path,
                    }
                )
                raise

    def _validate_endpoint_configs(self, endpoints: List[FlowEndpoint]):
        paths = set()
        for ep in endpoints:
            if not isinstance(ep.path, str) or not ep.path.startswith("/"):
                raise ValueError(f"Endpoint path must start with '/': {ep.path}")
            if ep.path in paths:
                raise ValueError(f"Duplicate endpoint path registered: {ep.path}")
            paths.add(ep.path)
            if not callable(ep.flow_runner):
                raise ValueError(f"flow_runner for {ep.flow_name} must be callable")

    # EXPECTION handlers
    def _register_exception_handlers(self):
        @self.app.exception_handler(FlowExecutionError)
        async def flow_exc_handler(request: Request, exc: FlowExecutionError):
            trace_id = getattr(request.state, "trace_id", str(uuid.uuid4()))
            # logger.error(
            #     f"FlowExecutionError for flow={exc.flow} code={exc.code} message={exc.message} details={exc.details}"
            # )

            logger.error(
                {
                    "event": "flow_error",
                    "trace_id": trace_id,
                    "flow": exc.flow,
                    "code": exc.code,
                    "message": exc.message,
                    "details": _short_preview(exc.details),
                }
            )
            body = ErrorResponse(
                success=False,
                code=exc.code,
                message=exc.message,
                details=exc.details,
                flow=exc.flow,
                trace_id=trace_id,
            )
            content = body.model_dump(mode="json")
            return JSONResponse(status_code=exc.status_code, content=content)

        @self.app.exception_handler(Exception)
        async def generic_exc_handler(request: Request, exc: Exception):
            trace_id = getattr(request.state, "trace_id", str(uuid.uuid4()))
            logger.exception(
                {
                    "event": "unhandled_exception",
                    "trace_id": trace_id,
                    "path": getattr(request, "url", None),
                    "error": _short_preview(str(exc)),
                }
            )
            body = ErrorResponse(
                success=False,
                code=ErrorCode.INTERNAL,
                message="Internal server error",
                details=str(exc),
                trace_id=trace_id,
            )
            content = body.model_dump(mode="json")
            return JSONResponse(status_code=500, content=content)

    async def _safe_run_flow(
        self,
        runner: Callable[[object], object],
        input_obj: object,
        timeout: Optional[float],
        trace_id: str,
        flow_name: str,
    ):
        """
        Runs runner(input_obj) safely. Accepts sync or async runner.
        Returns: (output, duration_seconds)
        Raises FlowExecutionError on errors/timeouts.
        """
        output = FlowOutput(flow=FlowSummary(steps={}, usage_summary=None),  output=None)
        start_ts = time.time()

        try:
            with anyio.move_on_after(timeout) if timeout else contextlib.nullcontext():

                if inspect.iscoroutinefunction(runner):
                    output = await runner(input_obj)
                else:
                    output = await anyio.to_thread.run_sync(runner, input_obj)

            duration = time.time() - start_ts
            return output, duration

        except TimeoutError:
            logger.warning(
                {
                    "event": "flow_timeout",
                    "trace_id": trace_id,
                    "flow": flow_name,
                    "timeout_seconds": timeout,
                }
            )
            raise FlowExecutionError(
                code=ErrorCode.TIMEOUT,
                message=f"Flow execution timed out after {timeout} seconds.",
                details=None,
                status_code=504,
                flow=flow_name,
            )

        except FlowExecutionError:
            # propagate as-is
            raise

        except Exception as e:
            logger.exception(
                {
                    "event": "flow_runtime_error",
                    "trace_id": trace_id,
                    "flow": flow_name,
                    "error": _short_preview(str(e)),
                }
            )
            raise FlowExecutionError(
                code=ErrorCode.FLOW_RUNTIME_ERROR,
                message="Flow runtime error",
                details=_short_preview(str(e)),
                status_code=500,
                flow=flow_name,
            )

    def _register_endpoints(self):
        for ep in self.endpoints:
            runner = ep.flow_runner
            flow_name = ep.flow_name
            timeout = (
                ep.timeout_seconds
                if ep.timeout_seconds is not None
                else self.default_timeout
            )

            # define endpoint function that captures runner/auth/flow_name/timeout via closure
            def _make_endpoint(
                runner,
                flow_name,
                timeout,
            ):

                async def _run_endpoint(
                    body: FlowRequest,
                    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
                        self.security
                    ),
                ):

                    trace_id = str(uuid.uuid4())

                    # AUTH
                    if credentials is None or credentials.credentials != self.api_key:
                        logger.info(
                            {
                                "event": "auth_failed",
                                "trace_id": trace_id,
                                "flow": flow_name,
                            }
                        )
                        raise FlowExecutionError(
                            code=ErrorCode.AUTH_FAILED,
                            message="Invalid or missing API key.",
                            status_code=403,
                            flow=flow_name,
                        )

                    # VALIDATION
                    if body is None or getattr(body, "input", None) is None:
                        logger.info(
                            {
                                "event": "invalid_input",
                                "trace_id": trace_id,
                                "flow": flow_name,
                            }
                        )
                        raise FlowExecutionError(
                            code=ErrorCode.INVALID_INPUT,
                            message="Missing 'input' in request body.",
                            details=None,
                            status_code=400,
                            flow=flow_name,
                        )

                    input_preview = _short_preview(body.input, max_len=1024)
                    logger.info(
                        {
                            "event": "flow_request",
                            "trace_id": trace_id,
                            "flow": flow_name,
                            "input_preview": input_preview,
                            "timeout_seconds": timeout,
                        }
                    )

                    # RUN the flow
                    output, duration = await self._safe_run_flow(
                        runner, body.input, timeout, trace_id, flow_name
                    )

                    # IF success
                    output_preview = _short_preview(output, max_len=1024)
                    resp = SuccessResponse.generate_resp(
                        flow_name=flow_name,
                        output=output,
                        trace_id=trace_id,
                        duration=duration,
                    )
                    logger.info(
                        {
                            "event": "flow_success",
                            "trace_id": trace_id,
                            "flow": flow_name,
                            "duration_ms": int(duration * 1000),
                            "input_preview": input_preview,
                            "output_preview": output_preview,
                        }
                    )

                    content = resp.model_dump(mode="json")
                    return JSONResponse(status_code=200, content=content)

                return _run_endpoint

            endpoint_func = _make_endpoint(
                runner=runner,
                flow_name=flow_name,
                timeout=timeout,
            )

            # POST route
            self.app.post(ep.path, name=flow_name)(endpoint_func)

    def _register_healthz(self):
        @self.app.get("/healthz", include_in_schema=False)
        async def healthz():
            uptime = time.time() - self.start_time
            return {
                "status": "ok",
                "uptime_seconds": uptime,
                "version": chainless.__version__,
                "endpoints": len(self.endpoints),
            }

    def run(self, reload: bool = False):
        uvicorn.run(self.app, host=self.host, port=self.port, reload=reload)


__all__ = ["FlowServer", "FlowServerConfig"]
