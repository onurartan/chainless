from typing import Callable, Any

import asyncio
import anyio
import anyio.to_thread

import inspect


class AgentHook:
    """
    Wraps a callable (sync or async) as a hook for the agent, providing
    timeout handling and safe execution.

    Example:
        >>> async def pre_hook(value, agent):
        ...     return value.upper()
        >>> hook = AgentHook(pre_hook)
        >>> result = await hook.run("hello", agent)
        >>> print(result)
        "HELLO"
    """

    def __init__(self, func: Callable, timeout: float = 5.0, name: str = None) -> None:
        self.func = func
        self.timeout = timeout
        self.name = name or func.__name__

    async def run(self, value, agent) -> Any:
        try:
            if inspect.iscoroutinefunction(self.func):
                return await asyncio.wait_for(
                    self.func(value, agent), timeout=self.timeout
                )
            else:
                return await anyio.to_thread.run_sync(self.func, value, agent)
        except asyncio.TimeoutError:
            print(f"[Hook Timeout] {self.name} exceeded {self.timeout}s")
            return value
        except Exception as e:
            print(f"[Hook Error] {self.name}: {e}")
            return value
