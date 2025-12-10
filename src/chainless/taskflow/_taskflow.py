import asyncio
import anyio
from typing import List, Callable, Optional, Union

from ._task_context import TaskContext
from ._task_executor import TaskExecutor

from chainless.exp.server import FlowEndpoint
from chainless.schemas import TaskStep
from chainless.schemas.taskflow_schema import FlowOutput
from chainless.types.agent_protocol import AgentProtocol

from chainless._utils.callback_utils import validate_callback
from chainless._utils.serialization import clean_output_structure
from chainless._utils.validation import validate_name

from chainless._utils.exception import ChainlessError

import pydantic_ai.messages as pai_messages


def is_valid_agent(agent: object) -> bool:
    # DEPRACTED[LANGCHAIN]
    # callable(getattr(agent, "start", None)) or 
    return callable(
        getattr(agent, "run", None)
    )


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
        on_step_complete: Optional[Callable] = None,
        on_step_start: Optional[Callable] = None,
        on_step_error: Optional[Callable] = None,
    ):
        validate_name(name, "taskflow name")

        self.ctx = TaskContext(name=name, verbose=verbose)
        self.executor = TaskExecutor(self.ctx)

        if on_step_start:
            validate_callback(
                on_step_start, ["step_name", "user_input"], "on_step_start"
            )
        if on_step_complete:
            validate_callback(
                on_step_complete, ["step_name", "output"], "on_step_complete"
            )
        if on_step_error:
            validate_callback(on_step_error, ["step_name", "error"], "on_step_error")

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
            agent (AgentProtocol): An object that implements the `run()` method.

        Example:
            >>> flow.add_agent("summarizer", SummarizerAgent())

        Raises:
            ValueError: If an agent with the same name already exists.
            TypeError: If the provided object does not implement AgentProtocol.
        """
        validate_name(name, "agent name")
        if name in self.ctx.agents:
            # raise ValueError(f"Agent with name '{name}' already exists.")
            raise ChainlessError(f"Agent with name '{name}' already exists.")

        if not is_valid_agent(agent):
            # raise TypeError(
            #     f"{name} is not a valid Agent. It must implement at least 'start()' or 'run()'."
            # )
            raise ChainlessError(
                f"{name} is not a valid Agent. It must implement at least 'run()'."
            )
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
        prompt_template: Optional[str] = None,
        step_name: Optional[str] = None,
        message_history: list[pai_messages.ModelMessage] = None,
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
            # raise ValueError(f"Step with agent_name '{step_name}' already exists.")
            raise ChainlessError(f"Step with agent_name '{step_name}' already exists.")
        
        step_obj = TaskStep(
            step_name=step_name,
            agent_name=agent_name,
            input_map=input_map,
            prompt_template=prompt_template,
            message_history=message_history,
            retry_on_fail=retry_on_fail,
            timeout=timeout,
            on_start=on_start,
            on_complete=on_complete,
            on_error=on_error,
            condition=condition,
            depends_on=depends_on,
        )
        self.ctx.steps.append(step_obj)

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

    def run(
        self,
        user_input: str,
    ) -> FlowOutput:
        """
        Start the task flow synchronously using the provided user input.

        Executes all defined steps (sequential and/or parallel), resolves inputs,
        and returns the output of the last agent executed.

        Args:
            user_input (str): The initial input string for the flow.

        Returns:
            FlowOutput: Contains the full flow outputs and the final output from the last agent.
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

            future = asyncio.run_coroutine_threadsafe(
                self.run_async(user_input=user_input), loop
            )
            result = future.result()
        except RuntimeError:
            result = anyio.run(self._run_async)

        last_agent = self.ctx.steps[-1].agent_name if self.ctx.steps else None
        last_step = result.get(last_agent, {})
        output_val = (
            last_step.get("output", None) if isinstance(last_step, dict) else last_step
        )
        _output = clean_output_structure(output_val)
        _flow = clean_output_structure(result)

        flow_output = {"flow": _flow, "output": _output}
        return FlowOutput.from_flow_output(output=flow_output)

    async def run_async(self, user_input: str):
        self.ctx.initial_input = user_input

        result = await self._run_async()

        last_agent = self.ctx.steps[-1].agent_name if self.ctx.steps else None
        last_step = result.get(last_agent, {})
        output_val = (
            last_step.get("output", None) if isinstance(last_step, dict) else last_step
        )
        _output = clean_output_structure(output_val)
        _flow = clean_output_structure(result)

        flow_output = {"flow": _flow, "output": _output}
        return FlowOutput.from_flow_output(output=flow_output)

    def serve(
        self,
        path: str,
        name: str,
    ):
        return FlowEndpoint(
            flow_name=name,
            path=path,
            flow_runner=self.run_async,
        )

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
            prompt_template = step.prompt_template
            retry_override = step.retry_on_fail
            step_timeout = step.timeout

            # Ensure each step has a valid, registered agent
            if not step.agent_name:
                # raise ValueError(f"Step ''{step_name} must have an assigned agent.")
                raise ChainlessError(f"Step ''{step_name} must have an assigned agent.", error_code="ValueError")

            if step.agent_name not in self.ctx.agents:
                # raise ValueError(
                #     f"Agent '{step.agent_name}' for step '{step_name}' is not registered."
                # )
                raise ChainlessError(
                    f"Agent '{step.agent_name}' for step '{step_name}' is not registered.",
                     error_code="ValueError"
                )

            if step.condition is not None:
                cond_result = step.condition(self.ctx.step_outputs)

                if not isinstance(cond_result, bool):
                    self.ctx._log(
                        f"[STEP:CONDITION-INVALID] {step_name} condition did not return bool "
                        f"(got {type(cond_result).__name__}). Treating as False."
                    )
                    cond_result = False

                if not cond_result:
                    self.ctx._log(f"[STEP:SKIPPED] {step_name} condition not met.")
                    self.ctx.step_outputs[step_name] = {
                        "output": None,
                        "skipped": True,
                    }

                    continue

            parallel_group = next(
                (group for group in self._parallel_groups if step_name in group), None
            )

            if parallel_group:
                self.ctx._log(f"Running parallel group: {parallel_group}")
                results = await self._run_parallel_group(parallel_group, executed_steps)
                executed_steps.update(results)
                self._parallel_groups.remove(parallel_group)

            else:
                await self.executor.run_step_async(
                    step_name=step_name,
                    input_map=input_map,
                    prompt_template=prompt_template,
                    retry_override=retry_override,
                    timeout=step_timeout,
                    message_history=step.message_history,
                )
                executed_steps.add(step_name)

        return self.ctx.step_outputs

    async def _run_parallel_group(self, step_names: list[str], executed_steps: set):
        """
        Executes a group of steps concurrently using anyio.TaskGroup.
        Handles individual errors gracefully and continues logging.
        """
        results = {}
        errors = []

        async with anyio.create_task_group() as tg:
            for name in step_names:
                if name in executed_steps:
                    continue
                step = self.ctx._get_step_by_name(name)

                async def run_step(n=name, s=step):
                    try:
                        await self.executor.run_step_async(
                            step_name=n,
                            input_map=s.input_map,
                            prompt_template=s.prompt_template,
                            retry_override=s.retry_on_fail,
                            timeout=s.timeout,
                            message_history=s.message_history,
                        )
                        results[n] = True
                    except Exception as e:
                        errors.append((n, e))
                        self.ctx._log(f"[Parallel ERROR] Step '{n}' failed: {e}")
                        await self.executor._safe_call_callback(
                            self.ctx.on_step_error, "on_step_error", n, str(e)
                        )

                tg.start_soon(run_step)

        if errors:
            err_summary = "; ".join(f"{n}: {e}" for n, e in errors)
            # raise RuntimeError(f"Parallel group failed: {err_summary}")
            raise ChainlessError(f"Parallel group failed: {err_summary}", error_code="RuntimeError")

        return results.keys()
