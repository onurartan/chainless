import asyncio
import traceback
from ..._utils._validate_callback import _call_callback
from . import TaskContext
from functools import cached_property


class TaskExecutor:
    def __init__(self, context: TaskContext):
        self.ctx: TaskContext = context

    async def _safe_call_callback(self, callback, name, *args, **kwargs):
        if callback is None:
            return
        try:
            await _call_callback(callback, *args, **kwargs)
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

        for step in self.ctx.steps:
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
        self, step_name, input_map, retry_override=None, timeout: int = None
    ):
        """
        Asynchronously execute a single step for a given agent.

        This includes resolving input, executing the agent, handling retries,
        and storing the output. Will log and raise errors if retries are exhausted.

        Args:
            agent_name (str): The name of the agent to run.
            input_map (dict): The resolved input map for the agent.
            retry_override (int, optional): If specified, overrides the default retry logic.

        Returns:
            Tuple[str, Any]: The agent name and the resulting output.
        """
        resolved_input = self.ctx.resolve_input(input_map)
        resolved_input["verbose"] = self.ctx.verbose
        resolved_input["input"] = resolved_input.get("input", "") or ""

        self.ctx._log(f"Resolved input for {step_name}: {resolved_input}")

        # step_obj = next(s for s in self.ctx.steps if s.step_name == step_name) OLD
        step_obj = self.ctx._get_step_by_name(step_name=step_name)
        agent_name = step_obj.agent_name

        usr_input = resolved_input.get("input", "") or ""

        await self._safe_call_callback(
            step_obj.on_start, "step_obj.on_start", step_name, usr_input
        )
        await self._safe_call_callback(
            self.ctx.on_step_start, "self.on_step_start", step_name, usr_input
        )

        #  ?OLD _> not v0.1.0
        # if self.on_step_start:
        #     try:
        #         usr_input = resolved_input.get("input", "") or ""
        #         await _call_callback(self.on_step_start, agent_name, usr_input)
        #     except Exception as e:
        #         self._log(f"[Callback ERROR] on_step_start failed: {e}")

        # Run Step AGENT
        agent = self.ctx.agents[agent_name]

        retries = (
            retry_override if retry_override is not None else self.ctx.retry_on_fail
        )
        last_exception = None

        while True:
            try:
                if timeout:
                    output = await asyncio.wait_for(
                        asyncio.to_thread(agent.start, **resolved_input),
                        timeout=timeout,
                    )
                else:
                    output = await asyncio.to_thread(agent.start, **resolved_input)
                self.ctx._log(f"{agent_name} agent completed successfully.")
                break
            except asyncio.TimeoutError:
                last_exception = TimeoutError(
                    f"Step '{agent_name}' timed out after {timeout} seconds."
                )
                self.ctx._log(
                    f"[{self.ctx.task_id}] [TIMEOUT] {agent_name} exceeded timeout limit."
                )
                break
            except Exception as e:
                last_exception = e
                tb = traceback.format_exc()
                self.ctx._log(f"[ERROR] {agent_name} failed: {e}\n{tb}")
                if retries <= 0:
                    self.ctx._log(f"{step_name} step failed with no retries left.")
                    raise RuntimeError(f"{step_name} step failed. Error: {e}") from e
                retries -= 1
                self.ctx._log(
                    f"{step_name} retrying ({self.ctx.retry_on_fail - retries}/{self.ctx.retry_on_fail})..."
                )

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

        self.ctx.step_outputs[step_name] = output
        await self._safe_call_callback(
            self.ctx.on_step_complete, "on_step_complete", step_name, output
        )
        await self._safe_call_callback(
            step_obj.on_complete, "step_obj.on_complete", step_name, output
        )
        return step_name, output
