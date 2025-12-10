import contextlib
import anyio
import anyio.to_thread
import inspect
import traceback

from typing import Optional
from functools import cached_property

from chainless._utils.callback_utils import call_callback
from chainless.schemas.context import AgentProtocolRunContext

from ._task_context import TaskContext

import pydantic_ai.messages as pai_messages


class TaskExecutor:
    """
    Executes individual steps in a TaskFlow context.
    Fully async-compatible using AnyIO for cross-event-loop safety.
    """

    def __init__(self, context: TaskContext):
        self.ctx: TaskContext = context

    async def _safe_call_callback(self, callback, name, *args, **kwargs):
        """
        Safely call user-provided callbacks (sync or async),
        logging success or failure.
        """
        if callback is None:
            return
        try:
            await call_callback(callback, *args, **kwargs)
            self.ctx._log(f"[Callback] {name} executed successfully.")
        except Exception as e:
            self.ctx._log(f"[Callback ERROR] {name} failed: {e}")

    @cached_property
    def _get_execution_order(self):
        import networkx as nx

        if not any(step.depends_on for step in self.ctx.steps):
            return [step.step_name for step in self.ctx.steps]

        G = nx.DiGraph()
        all_agents = {step.step_name for step in self.ctx.steps}

        for step in self.ctx.steps:
            G.add_node(step.step_name)
            depends = step.depends_on or []
            for dep in depends:
                if dep not in all_agents:
                    raise RuntimeError(
                        f"Step '{step.step_name}' depends on unknown agent '{dep}'."
                    )
                G.add_edge(dep, step.step_name)

        try:
            return list(nx.topological_sort(G))
        except nx.NetworkXUnfeasible as e:
            cycle = list(nx.find_cycle(G, orientation="original"))
            cycle_str = " -> ".join(node for node, _ in cycle) + " -> " + cycle[0][0]
            raise RuntimeError(
                f"Step dependency cycle detected! Cycle: {cycle_str}"
            ) from e

    async def run_step_async(
        self,
        step_name,
        input_map,
        prompt_template,
        retry_override=None,
        timeout: int = None,
        message_history: Optional[list[pai_messages.ModelMessage]] = None,
    ):
        """
        Execute a single agent step asynchronously using AnyIO.
        Handles retries, timeouts, sync/async compatibility and callbacks.
        """
        resolved_input = self.ctx.resolve_input(input_map)
        resolved_prompt_template = self.ctx.resolve_prompt(
            prompt_template=prompt_template, resolved_inputs=resolved_input
        )

        resolved_input = dict(resolved_input)
        resolved_input["input"] = (
            resolved_prompt_template or resolved_input.get("input", "") or ""
        )
        resolved_input["message_history"] = message_history
        self.ctx._log(f"Resolved input for {step_name}: {resolved_input}")

        step_obj = self.ctx._get_step_by_name(step_name=step_name)
        agent_name = step_obj.agent_name
        usr_input = resolved_input.get("input", "") or ""

        await self._safe_call_callback(
            step_obj.on_start, "step_obj.on_start", step_name, usr_input
        )
        await self._safe_call_callback(
            self.ctx.on_step_start, "self.on_step_start", step_name, usr_input
        )

        # Run Step AGENT
        agent = self.ctx.agents[agent_name]
        retries = (
            retry_override if retry_override is not None else self.ctx.retry_on_fail
        )
        last_exception = None

        def build_aprctx() -> AgentProtocolRunContext:
            """
            Helper function to build the AgentProtocolRunContext object.
            """
            return AgentProtocolRunContext(
                input=resolved_input.get("input", ""),
                model=resolved_input.get("model"),
                model_settings=resolved_input.get("model_settings"),
                usage_limits=resolved_input.get("usage_limits"),
                usage=resolved_input.get("usage"),
                message_history=resolved_input.get("message_history"),
                extra_inputs=resolved_input.get("extra_inputs", {}),
            )

        def _is_agent_protocol(agent, run_method):
            sig = inspect.signature(run_method)
            params = list(sig.parameters.values())

            if len(params) == 1 and params[0].annotation is AgentProtocolRunContext:
                return True

            return False


        while True:
            try:
                # detect run method
                run_method_async = getattr(agent, "run_async", None)
                run_method_sync = getattr(agent, "run", getattr(agent, "start", None))

                if not (callable(run_method_async) or callable(run_method_sync)):
                    raise AttributeError(f"{agent_name} has no valid run/start method")

                is_protocol = False

                if callable(run_method_sync):
                    is_protocol = _is_agent_protocol(agent, run_method_sync)
                elif callable(run_method_async):
                    is_protocol = _is_agent_protocol(agent, run_method_async)
                
                
                async def _execute_agent():
                    if is_protocol:
                        self.ctx._log(
                            f"Invoking AgentProtocol agent '{agent_name}' with AgentProtocolRunContext"
                        )
                        ctx_obj = build_aprctx()
                        
                        # REMOVED = 
                        # if callable(run_method_async) and inspect.iscoroutinefunction(
                        #     run_method_async
                        # ):
                        #     return await run_method_async(ctx_obj)

                        return await anyio.to_thread.run_sync(
                            lambda: run_method_sync(ctx_obj)
                        )

                    # Agent
                    if callable(run_method_async) and inspect.iscoroutinefunction(
                        run_method_async
                    ):
                        return await run_method_async(**resolved_input)

                    return await anyio.to_thread.run_sync(
                        lambda: run_method_sync(**resolved_input)
                    )

                with (
                    anyio.move_on_after(timeout)
                    if timeout
                    else contextlib.nullcontext()
                ):
                    output = await _execute_agent()

                if output is None:
                    raise TimeoutError(
                        f"Step '{agent_name}' timed out after {timeout} seconds."
                    )

                self.ctx._log(f"{agent_name} completed successfully.")
                break
            except TimeoutError as e:
                last_exception = e
                self.ctx._log(f"[TIMEOUT] {agent_name} exceeded {timeout}s limit.")
                break
            except Exception as e:
                last_exception = e
                tb = traceback.format_exc()
                self.ctx._log(f"[ERROR] {agent_name} failed: {e}\n{tb}")
                if retries <= 0:
                    raise RuntimeError(f"{step_name} failed permanently: {e}") from e
                retries -= 1
                self.ctx._log(
                    f"{step_name} retrying ({self.ctx.retry_on_fail - retries}/{self.ctx.retry_on_fail})..."
                )

        # handle error callbacks
        if last_exception:
            error_msg = str(last_exception)
            self.ctx.step_outputs[step_name] = {"error": error_msg}
            await self._safe_call_callback(
                step_obj.on_error, "step_obj.on_error", step_name, error_msg
            )
            await self._safe_call_callback(
                self.ctx.on_step_error, "on_step_error", step_name, error_msg
            )
            raise last_exception

        # success
        self.ctx.step_outputs[step_name] = output
        await self._safe_call_callback(
            self.ctx.on_step_complete, "on_step_complete", step_name, output
        )
        await self._safe_call_callback(
            step_obj.on_complete, "step_obj.on_complete", step_name, output
        )
        return step_name, output
