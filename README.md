# Chainless – A Lightweight Agentic Framework for Modern AI Workflows

Chainless is a minimalistic, modular framework for building powerful agent workflows and tool-augmented  systems.
It focuses on simplicity, composability, and clarity while enabling advanced multi-agent orchestration without unnecessary complexity.

Chainless gives you the building blocks to create intelligent systems that can reason, execute functions, work in steps, and run as production-ready services.

---

## Why Chainless?

* Simple design with **zero overhead**
* Fully typed and developer friendly
* Clean abstraction for tools, agents, and workflows
* Built-in **TaskFlow** for orchestrated multi-step logic
* Native support for **async tools**, **structured outputs**, and **custom prompts**
* Built-in **FlowServer** for serving flows as HTTP endpoints
* Works with any major  provider (OpenAI, Gemini, Anthropic)

---

## Installation

```bash
pip install chainless
```

You only need to configure your preferred  provider (OpenAI, Gemini, Anthropic, etc.)

---

# Core Concepts

Chainless provides three core primitives that everything else builds on.

**Tool**: A function callable by an agent. Tools can be sync or async.

**Agent**: A reasoning unit that interacts with an , uses tools, applies prompts, and produces structured outputs.

**TaskFlow**: Whether you're building AI assistants, workflow chains, or multi-agent environments, Chainless gives you the control and simplicity to iterate fast.

---

# Quick Start Examples

Below are updated examples that reflect the current design of Chainless.

---

## Example 1: A Simple Agent with a Tool

```python
from chainless import Agent, Tool

@Tool.tool(name="add", description="Adds two numbers.")
def add(a: int, b: int) -> int:
    return a + b

agent = Agent(
    name="MathAgent",
    system_prompt="Use tools when needed to solve math problems.",
    tools=[add]
)

result = agent.run("Please add 5 and 7.")
print(result.output)
```

---

## Example 2: Agents With Structured Outputs

```python
from pydantic import BaseModel
from chainless import Agent

class Info(BaseModel):
    title: str
    summary: str

agent = Agent(
    name="Summarizer",
    system_prompt="Extract a title and a short summary.",
    response_format=Info
)

res = agent.run("Python is a programming language created by Guido van Rossum.")
print(res.output["title"], res.output["summary"])
```

---

## Example 3: Multi Step Workflow Using TaskFlow

```python
from chainless import Agent, TaskFlow

classifier = Agent(
    name="Classifier",
    system_prompt="Classify the topic of the text into categories."
)

summarizer = Agent(
    name="Summarizer",
    system_prompt="Summarize the input in two sentences."
)

flow = TaskFlow("TextProcessingFlow")

flow.add_agent("Classifier", classifier)
flow.add_agent("Summarizer", summarizer)

flow.step("Classifier", input_map={"input": "{{input}}"})
flow.step("Summarizer", input_map={"input": "{{Classifier.output}}"})

result = flow.run("Quantum computing uses qubits to represent information.")
print(result.flow.steps["Summarizer"].output)
# OR
print(result.output)
```

---

## Example 4: Using Tools Inside a TaskFlow Step

```python
from chainless import Agent, TaskFlow, Tool

@Tool.tool(name="temperature", description="Returns the current system temperature.")
def get_temp():
    return 42

agent = Agent(
    name="DiagnosticAgent",
    tools=[get_temp],
    system_prompt="Check system temperature and provide a health report."
)

flow = TaskFlow("DiagnosticsFlow")
flow.add_agent("Diag", agent)
flow.step("Diag", input_map={"input": "{{input}}"})

print(flow.run("status"))
```

---

## Example 5: Serve A Flow With FlowServer

```python
from chainless import Agent, TaskFlow
from chainless.exp.server import FlowServer

agent = Agent(
    name="EchoAgent",
    system_prompt="Repeat the user input."
)

flow = TaskFlow("EchoFlow")
flow.add_agent("Echo", agent)
flow.step("Echo", input_map={"input": "{{input}}"})

endpoint = flow.serve("/echo", name="Echo Service")
server = FlowServer(endpoints=[endpoint], port=8000, api_key="demo")

if __name__ == "__main__":
    server.run()
```

You now have a production-ready API that runs your agents as HTTP services.

---

# Architecture Overview

Chainless follows a clear, minimal architecture.

### Tool

* Smallest executable unit
* Sync or async
* Perfect for integrating external APIs, local logic, or computation

### Agent

* Contains an 
* Uses tools strategically
* Supports structured outputs
* Can apply custom hooks and decorators
* Produces deterministic structured reasoning

### TaskFlow

* Multi agent orchestration
* Step by step execution
* Parallel execution supported
* Input and output mapping with templates
* Ideal for building complex flows from simple components

### FlowServer

* Serve flows as HTTP APIs
* Automatic input validation
* API key support
* Easy deployment

---

# Roadmap

* Improved memory system (in progress)
* Tracing and monitoring tools
* Flow visualization
* CLI for easier testing
* Built in agent simulator

---

# Contributing

Contributions are welcome.
Before submitting large changes or proposals, please open a discussion.

---

# License

MIT License.

---

# Authors

Created and maintained by **Onur Artan / Trymagic**.
