from .Agent import Agent
from ..utils.serialization import clean_output_structure
from ..interfaces.AgentProtocol import AgentProtocol
from chainless.logger import get_logger
from pydantic import BaseModel
import re
import asyncio
import traceback


class TaskFlow:
    def __init__(
        self,
        name: str,
        verbose: bool = False,
        on_step_complete=None,
        retry_on_fail: int = 0,
    ):
        self.name = name
        self.agents = {}
        self.steps = []
        self.step_outputs = {}
        self.verbose = verbose
        self.on_step_complete = on_step_complete
        self.retry_on_fail = retry_on_fail
        self._parallel_groups = []

        self.logger = get_logger(f"[TaskFlow:{self.name}]")

    def add_agent(self, name: str, agent: AgentProtocol):
        if not isinstance(agent, AgentProtocol):
          raise TypeError(f"{name} is not a valid Agent. It must implement start().")
        self.agents[name] = agent

    def step(self, agent_name: str, input_map: dict, retry_on_fail: int = None):
        """
        Add a new step to the task flow using a specified agent.

        Each step is executed in sequence unless defined in a parallel group.
        The step will resolve dynamic input references before execution.

        Args:
            agent_name (str): Name of the agent to be executed.
            input_map (dict): Dictionary mapping input parameters for the agent.
                              Supports templated values like '{{input}}' or '{{agent.output_key}}'.
            retry_on_fail (int, optional): Number of times to retry this step on failure.
                                           Overrides the global retry count if provided.
        """
        self.steps.append(
            {
                "agent_name": agent_name,
                "input_map": input_map,
                "retry_on_fail": retry_on_fail,
            }
        )

    def parallel(self, agent_names: list):
        """
        Define a set of agents to be executed in parallel.

        All agents in this group will start concurrently when reached during execution.
        Their results will be stored individually in the step_outputs.

        Args:
            agent_names (list): List of agent names that should be run in parallel.
        """
        self._parallel_groups.append(agent_names)

    def resolve_input(self, input_map: dict) -> dict:
        """
        Resolve input mappings by replacing template variables with actual values.

        Supports placeholders like '{{input}}' for initial input or nested references
        such as '{{agent_name.output_key}}' to previous step outputs.

        Args:
            input_map (dict): Input dictionary possibly containing template strings.

        Returns:
            dict: Input map with resolved values.
        """
        resolved = {}
        for key, val in input_map.items():
            try:
                if isinstance(val, str) and "{{" in val:
                    if "{{input}}" in val:
                        resolved[key] = getattr(self, "initial_input", "")
                    else:
                        agent_ref = val.strip("{} ")
                        parts = self._resolve_references(agent_ref)
                        resolved[key] = parts
                else:
                    resolved[key] = val
            except Exception as e:
                self._log(f"[resolve_input] Error resolving key ({key}): {e}")
                resolved[key] = None
        return resolved

    def _resolve_references(self, agent_ref: str):
        parts = self._split_reference(agent_ref)
        agent_name = parts[0]
        step_output = self.step_outputs.get(agent_name, {})
        return self._resolve_nested_references(step_output, parts[1:])

    def _split_reference(self, agent_ref: str):
        return [part for part in re.split(r"[\.\[\]]+", agent_ref) if part]

    def _resolve_nested_references(self, current_data, parts):
        if not parts:
            return current_data
        part = parts[0]
        try:
            if isinstance(current_data, dict):
                return self._resolve_nested_references(
                    current_data.get(part), parts[1:]
                )
            elif isinstance(current_data, list):
                index = int(part)
                return self._resolve_nested_references(current_data[index], parts[1:])
            elif isinstance(current_data, BaseModel):
                return self._resolve_nested_references(
                    getattr(current_data, part), parts[1:]
                )
        except Exception as e:
            self._log(f"[resolve_nested_references] Hata: {e}")
        return None

    def _log(self, message: str):
        if self.verbose:
            self.logger.info(message)

    async def _run_step_async(self, agent_name, input_map, retry_override=None):
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
        resolved_input = self.resolve_input(input_map)
        resolved_input["verbose"] = self.verbose
        resolved_input["input"] = resolved_input.get("input", "") or ""

        self._log(f"Resolved input for {agent_name}: {resolved_input}")

        # Run Step AGENT
        agent = self.agents[agent_name]

        retries = retry_override if retry_override is not None else self.retry_on_fail
        last_exception = None

        while True:
            try:
                output = await asyncio.to_thread(agent.start, **resolved_input)
                self._log(f"{agent_name} agent başarıyla tamamlandı.")
                break
            except Exception as e:
                last_exception = e
                tb = traceback.format_exc()
                self._log(f"[ERROR] {agent_name} failed: {e}\n{tb}")
                if retries <= 0:
                    self._log(f"{agent_name} step failed with no retries left.")
                    raise RuntimeError(f"{agent_name} step failed. Error: {e}") from e
                retries -= 1
                self._log(
                    f"{agent_name} retrying ({self.retry_on_fail - retries}/{self.retry_on_fail})..."
                )

        self.step_outputs[agent_name] = output
        if self.on_step_complete:
            try:
                self.on_step_complete(agent_name, output)
            except Exception as cb_error:
                self._log(f"[Callback ERROR] on_step_complete failed: {cb_error}")
        return agent_name, output

    def run(self, user_input: str):
        """
        Start the task flow synchronously using the provided user input.

        Executes all defined steps (sequential and/or parallel), resolves inputs,
        and returns the output of the last agent executed.

        Args:
            user_input (str): The initial input string for the flow.

        Returns:
            dict: Contains the full flow outputs and the final output from the last agent.
                  {
                      "flow": <All step outputs>,
                      "output": <Final output>
                  }
        """
        self.initial_input = user_input
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        result = loop.run_until_complete(self._run_async())
        last_agent = self.steps[-1]["agent_name"] if self.steps else None
        last_step = result.get(last_agent, {})
        output_val = (
            last_step.get("output", None) if isinstance(last_step, dict) else last_step
        )
        _output = clean_output_structure(output_val)
        _flow = clean_output_structure(result)

        return {"flow": _flow, "output": _output}

    async def _run_async(self):
        """
        Internal coroutine that processes each step in order or in parallel.

        Returns:
            dict: All outputs from each agent step.
        """
        for step in self.steps:
            agent_name = step["agent_name"]
            input_map = step["input_map"]
            retry_override = step.get("retry_on_fail")

            parallel_group = next(
                (group for group in self._parallel_groups if agent_name in group), None
            )

            if parallel_group:
                self._log(f"Running parallel group: {parallel_group}")
                coros = []
                for name in parallel_group:
                    m = next(
                        s["input_map"] for s in self.steps if s["agent_name"] == name
                    )
                    r = next(
                        (
                            s.get("retry_on_fail")
                            for s in self.steps
                            if s["agent_name"] == name
                        ),
                        None,
                    )
                    coros.append(self._run_step_async(name, m, retry_override=r))
                await asyncio.gather(*coros)
                self._parallel_groups.remove(parallel_group)
            else:
                await self._run_step_async(
                    agent_name, input_map, retry_override=retry_override
                )

        return self.step_outputs
