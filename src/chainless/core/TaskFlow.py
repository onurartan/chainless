import asyncio
from typing import List, Callable, Optional, Union

from .taskflow import TaskContext, TaskExecutor
from ..interfaces.AgentProtocol import AgentProtocol
from .._utils._validate_callback import _validate_callback
from .._utils._serialization import clean_output_structure
from .._utils._validate_name import validate_name
from .._schemas import TaskStep


class TaskFlow:
    """
    A structured and extensible task orchestration engine for managing sequences
    of agent-based steps. Supports sequential and parallel execution, conditional steps,
    retries, and lifecycle callbacks.

    Example:
        >>> flow = TaskFlow(name="ExampleFlow", verbose=True)
        >>> flow.add_agent("agent1", SomeAgent())
        >>> flow.step("agent1", input_map={"text": "{{input}}"})
        >>> result = flow.run("Hello world")
        >>> print(result["output"])

    Args:
        name (str): Unique name identifying the task flow.
        verbose (bool): If True, logs detailed execution info.
        on_step_complete (Callable, optional): Called when a step successfully completes.
        retry_on_fail (int): Global retry count for failed steps.
        on_step_start (Callable, optional): Called before a step starts.
        on_step_error (Callable, optional): Called if a step raises an exception.

    Attributes:
        ctx (TaskContext): Internal context containing agents, steps, and outputs.
        executor (TaskExecutor): Executes individual steps based on the context.
        _parallel_groups (List[str]): Groups of steps to be executed in parallel.
    """

    def __init__(
        self,
        name: str,
        verbose: bool = False,
        retry_on_fail: int = 0,
        
        # NEW
        on_step_complete: Optional[Callable] = None,
        on_step_start: Optional[Callable] = None,
        on_step_error: Optional[Callable] = None,
    ):
        validate_name(name, "taskflow name")

        self.ctx = TaskContext(name=name, verbose=verbose)
        self.executor = TaskExecutor(self.ctx)

        if on_step_start:
            _validate_callback(
                on_step_start, ["step_name", "user_input"], "on_step_start"
            )
        if on_step_complete:
            _validate_callback(
                on_step_complete, ["step_name", "output"], "on_step_complete"
            )
        if on_step_error:
            _validate_callback(on_step_error, ["step_name", "error"], "on_step_error")

        self._parallel_groups: List[List[str]] = []

        self.ctx.retry_on_fail = retry_on_fail
        self.ctx.on_step_start = on_step_start
        self.ctx.on_step_complete = on_step_complete
        self.ctx.on_step_error = on_step_error

    def add_agent(self, name: str, agent: AgentProtocol):
        """
        Register an agent to be used in the task flow.

        Args:
            name (str): Unique identifier for the agent.
            agent (AgentProtocol): An object that implements the `start()` method.

        Example:
            >>> flow.add_agent("summarizer", SummarizerAgent())

        Raises:
            ValueError: If an agent with the same name already exists.
            TypeError: If the provided object does not implement AgentProtocol.
        """
        validate_name(name, "agent name")
        if name in self.ctx.agents:
            raise ValueError(f"Agent with name '{name}' already exists.")
        if not isinstance(agent, AgentProtocol):
            raise TypeError(f"{name} is not a valid Agent. It must implement start().")
        self.ctx.agents[name] = agent

    def alias(self, alias_name: str, from_step: str, key: str):
        """
        Create a reusable alias for a value in a step's output. Useful for referencing
        specific keys from a step in later inputs.

        Args:
            alias_name (str): The name to use in future input mappings.
            from_step (str): The step name where the original value was produced.
            key (str): The key in the step's output to alias.

        Example:
            >>> flow.alias("summary", from_step="summarizer", key="text")
            >>> flow.step("translator", input_map={"text": "{{summary}}"})

        Raises:
            ValueError: If alias already exists or inputs are invalid.
        """
        validate_name(alias_name, "alias name")
        if alias_name in self.ctx._aliases:
            raise ValueError(f"Alias '{alias_name}' already exists.")
        self.ctx._aliases[alias_name] = (from_step, key)

    def step(
        self,
        agent_name: str,
        input_map: dict,
        step_name: Optional[str] = None,
        retry_on_fail: int = None,
        timeout: int = None,
        on_start: Optional[Callable] = None,
        on_complete: Optional[Callable] = None,
        on_error: Optional[Callable] = None,
        condition: Union[Callable, None] = None,
        depends_on: Optional[List[str]] = None,
    ):
        """
        Add a new step to the task flow using a specified agent.

        Each step is executed in sequence unless defined in a parallel group.
        The step will resolve dynamic input references before execution.

        Args:
            agent_name (str): Name of a registered agent.
            input_map (dict): Input dictionary with static values or placeholders.
            step_name (str): agent_name is used by default, but if you want to use your agents on other steps, it is recommended to use step_name
            retry_on_fail (int, optional): Overrides global retry setting for this step.
            timeout (int, optional): Timeout for this step in seconds.
            on_start (Callable, optional): Hook before step execution.
            on_complete (Callable, optional): Hook after step completion.
            on_error (Callable, optional): Hook for error handling.
            condition (Callable, optional): Boolean function to conditionally run step.
            depends_on (List[str], optional): Other step names this step depends on.

        Example:
            >>> flow.step("summarizer", input_map={"text": "{{input}}"})
            >>> flow.step("translator", input_map={"text": "{{summarizer.text}}"})
        """

        if step_name is None:
            step_name = agent_name
        if any(s.step_name == step_name for s in self.ctx.steps):
            raise ValueError(f"Step with agent_name '{step_name}' already exists.")
        step_obj = TaskStep(
            step_name=step_name,
            agent_name=agent_name,
            input_map=input_map,
            retry_on_fail=retry_on_fail,
            timeout=timeout,
            on_start=on_start,
            on_complete=on_complete,
            on_error=on_error,
            condition=condition,
            depends_on=depends_on,
        )
        self.ctx.steps.append(step_obj)

        # **this was the old usage, now changed to validation with pydantic**
        # {
        #         "agent_name": agent_name,
        #         "input_map": input_map,
        #         "retry_on_fail": retry_on_fail,
        #         "timeout": timeout,
        #     }

    def parallel(self, step_names: list):
        """
        Define a set of agents to be executed in parallel.

        All agents in this group will start concurrently when reached during execution.
        Their results will be stored individually in the step_outputs.

        Args:
            step_names (list): List of step names that should be run in parallel.

        Example:
        >>> flow.parallel(["summarizer", "sentiment"])
        """
        self._parallel_groups.append(step_names)

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

        Example:
         >>> flow.run("Please summarize and translate this sentence.")
         {'flow': {...}, 'output': 'translated text'}
        """
        self.ctx.initial_input = user_input
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        result = loop.run_until_complete(self._run_async())
        # last_agent = self.steps[-1]["agent_name"] if self.steps else None # OLD
        last_agent = self.ctx.steps[-1].agent_name if self.ctx.steps else None
        last_step = result.get(last_agent, {})
        output_val = (
            last_step.get("output", None) if isinstance(last_step, dict) else last_step
        )
        _output = clean_output_structure(output_val)
        _flow = clean_output_structure(result)

        return {"flow": _flow, "output": _output}

    async def _run_async(self):
        """
        Internal coroutine for orchestrating all defined steps in order
        or in parallel.

        Returns:
            dict: Step outputs keyed by agent name.
        """
        # execution_order = self.executor._get_execution_order() OLD
        execution_order = self.executor._get_execution_order
        executed_steps = set()

        for step_name in execution_order:
            if step_name in executed_steps:
                continue

            step = self.ctx._get_step_by_name(step_name=step_name)
            input_map = step.input_map
            retry_override = step.retry_on_fail
            step_timeout = step.timeout

            if step.condition and not step.condition(self.ctx.step_outputs):
                self.ctx._log(f"[STEP:SKIPPED] {step_name} condition not met, skipped.")
                continue

            parallel_group = next(
                (group for group in self._parallel_groups if step_name in group), None
            )

            if parallel_group:
                self.ctx._log(f"Running parallel group: {parallel_group}")
                coros = []
                names = []
                for name in parallel_group:

                    if name in executed_steps:
                        continue
                    pstep = self.ctx._get_step_by_name(step_name=name)
                    m = pstep.input_map  # input_map
                    r = pstep.retry_on_fail or None  # retry_override
                    t = pstep.timeout or None  # timeout

                    coros.append(
                        self.executor.run_step_async(
                            step_name=name, input_map=m, retry_override=r, timeout=t
                        )
                    )
                    names.append(name)
                    executed_steps.add(name)
                results = await asyncio.gather(*coros, return_exceptions=True)
                errors = []

                for name, result in zip(names, results):
                    if isinstance(result, Exception):
                        errors.append(name, result)
                        self.ctx._log(
                            f"[Parallel ERROR] Step '{name}' failed: {result}"
                        )
                        await self.executor._safe_call_callback(
                            self.ctx.on_step_error, "on_step_error", name, str(result)
                        )
                    else:
                        executed_steps.add(name)

                if errors:
                    err_summary = "; ".join(f"{name}: {str(e)}" for name, e in errors)
                    raise RuntimeError(
                        f"Parallel group failed with errors: {err_summary}"
                    )
                if parallel_group in self._parallel_groups:
                    self._parallel_groups.remove(parallel_group)
            else:
                await self.executor.run_step_async(
                    step_name=step_name,
                    input_map=input_map,
                    retry_override=retry_override,
                    timeout=step_timeout,
                )
                executed_steps.add(step_name)

        return self.ctx.step_outputs
