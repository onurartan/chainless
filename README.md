# Chainless 🧠 – A Minimalistic Framework for Agentic Workflows

**Chainless** is a lightweight, extensible framework for building agent-based systems on top of large language models (LLMs). Designed to be modular, composable, and developer-friendly, Chainless provides an intuitive abstraction layer over LangChain and similar LLM orchestration libraries.

---

## Overview

Chainless introduces three core primitives:

- **Tool** – Wraps callable functions with structured metadata
- **Agent** – Manages reasoning, tool execution, and LLM interactions
- **TaskFlow** – Enables orchestrated multi-step workflows with sequential or parallel logic

Whether you're building AI assistants, workflow chains, or multi-agent environments, Chainless gives you the control and simplicity to iterate fast.

---

## Key Features

- 🧩 Modular design – Agents and tools are decoupled and reusable
- ⚙️ LangChain-compatible – Use any `BaseChatModel` and native LangChain tools
- 🔁 Supports sequential and parallel task execution
- 🧠 Customizable prompts and reasoning flows via decorators
- 🛠 Minimal dependencies and simple integration
- ✅ Typed, testable, and developer-centric

---

## Installation

```bash
pip install chainless
```

> Note: Chainless requires LangChain and an LLM provider (e.g., OpenAI, Anthropic). Make sure to configure credentials as needed.

---

## 📘 Usage Examples

Below are a few examples of how to use **Chainless** in increasing complexity.

---

### 🔹 Example 1: Simple Tool Call via Agent

```python
from chainless import Tool, Agent
from langchain_openai import ChatOpenAI

# Define a simple tool
reverse_tool = Tool("Reverser", "Reverses a string", lambda input: input[::-1])

# Set up LLM
llm = ChatOpenAI()

# Create agent
agent = Agent(
    name="SimpleReverser",
    llm=llm,
    tools=[reverse_tool],
    system_prompt="Use the Reverser tool to reverse the input string."
)

# Run agent
response = agent.start("Hello world")
print(response["output"])
```

---

### 🔸 Example 2: Parallel Tool Usage in a TaskFlow

```python
from chainless import Tool, Agent, TaskFlow

# Define tools
wiki_tool = Tool("WikiTool", "Searches Wikipedia", lambda q: f"Wikipedia info: {q}")
yt_tool = Tool("YTTool", "Fetches YouTube transcript", lambda q: f"Transcript of {q}")

# Create agents
wiki_agent = Agent("WikipediaAgent", llm=llm, tools=[wiki_tool])
yt_agent = Agent("YouTubeAgent", llm=llm, tools=[yt_tool])

# Build TaskFlow
flow = TaskFlow("ParallelSearch")

flow.add_agent("WikipediaAgent", wiki_agent)
flow.add_agent("YouTubeAgent", yt_agent)

flow.step("WikipediaAgent", input_map={"input": "{{input}}"})
flow.step("YouTubeAgent", input_map={"input": "{{input}}"})

flow.parallel(["WikipediaAgent", "YouTubeAgent"])

result = flow.run("Artificial Intelligence")
print(result)
```

---

### 🟠 Example 3: Custom Reasoning with a Summarizer Agent

```python
from chainless import Agent
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

llm = ChatOpenAI(model="gpt-4o")

summary_agent = Agent(
    name="Summarizer",
    llm=llm,
    system_prompt="Summarize input in 2 sentences."
)

@summary_agent.custom_start
def start(input: str, tools, system_prompt):
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}")
    ])
    chain = llm | prompt
    return chain.invoke(input)

result = summary_agent.start("Chainless is a lightweight agentic orchestration library...")
print(result["output"])
```

---

### 🔴 Example 4: Multi-Agent TaskFlow with Conditional Data Routing

```python
from chainless import TaskFlow

# Reuse wiki_agent, yt_agent, summary_agent from previous examples
report_agent = Agent(
    name="Reporter",
    llm=llm,
    system_prompt="""
    Combine the given summaries into a JSON report:
    {
      "topic": ...,
      "wikipedia": ...,
      "youtube": ...
    }
    """
)

@report_agent.custom_start
def start(wikipedia_ozet: str, youtube_ozet: str, tools, system_prompt):
    content = f"Wikipedia: {wikipedia_ozet}nYouTube: {youtube_ozet}"
    return llm.invoke(content)

flow = TaskFlow("MultiModalSummarization")

flow.add_agent("WikipediaAgent", wiki_agent)
flow.add_agent("YouTubeAgent", yt_agent)
flow.add_agent("WikiSummary", summary_agent)
flow.add_agent("YouTubeSummary", summary_agent)
flow.add_agent("Reporter", report_agent)

flow.step("WikipediaAgent", input_map={"input": "{{input}}"})
flow.step("YouTubeAgent", input_map={"input": "{{input}}"})
flow.parallel(["WikipediaAgent", "YouTubeAgent"])

flow.step("WikiSummary", input_map={"input": "{{WikipediaAgent.output.output}}"})
flow.step("YouTubeSummary", input_map={"input": "{{YouTubeAgent.output.output}}"})

flow.step("Reporter", input_map={
    "wikipedia_ozet": "{{WikiSummary.output}}",
    "youtube_ozet": "{{YouTubeSummary.output}}"
})

output = flow.run("Quantum Computing")
print(output["output"]["content"])
```

---

## Architecture

Chainless follows a simple but powerful pattern:

- **Tool**: Smallest executable unit. Synchronous, stateless.
- **Agent**: Wraps an LLM and optionally calls tools. Supports custom reasoning logic.
- **TaskFlow**: Manages execution of agents in steps, supports references, retries, and callbacks.

The framework is ideal for:

- Custom LLM agents with tool use
- Multi-step conversational agents
- Parallel agent execution
- Complex logic workflows without DAG complexity

---


## Roadmap

- ✅ Decorator-based agent customization
- ✅ Async tool support
- ⏳ Built-in memory support
- ⏳ CLI for flow testing

---

## Contributing

We welcome contributions from the community. If you have ideas, bug reports, or suggestions, please open an issue or a pull request.

For larger changes, please open a discussion first.

---

## License

This project is licensed under the MIT License.

---

## Authors

Maintained by Onur Artan / Trymagic. Inspired by LangChain’s ecosystem and the need for leaner abstraction models in agentic applications.