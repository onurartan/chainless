"use client";

import React from "react";
import Container from "./container";
import { Zap, Puzzle, Feather, Cpu } from "lucide-react";
import { CodeBlock } from "fumadocs-ui/components/codeblock";
import { DynamicCodeBlock } from "fumadocs-ui/components/dynamic-codeblock";

const features = [
  {
    title: "Fast Setup",
    desc: "Spin up an agent pipeline in seconds. Minimal dependencies, clear APIs, and no configuration pain.",
    icon: <Zap className="w-6 h-6" />,
  },
  {
    title: "Modular & Composable",
    desc: "Every piece — Tools, Agents, and TaskFlows — can be reused, combined, and extended with ease.",
    icon: <Puzzle className="w-6 h-6" />,
  },
  {
    title: "Lightweight by Design",
    desc: "No heavy runtimes or bloated abstractions — just Python functions and clean control over logic.",
    icon: <Feather className="w-6 h-6" />,
  },
  {
    title: "Model-Agnostic",
    desc: "Bring your own model — OpenAI, Ollama, Groq, DeepSeek, or custom. Chainless connects with all.",
    icon: <Cpu className="w-6 h-6" />,
  },
];

const WhyDevelopersLove = () => {
  return (
    <Container as="section" className="mt-12 px-6 py-16">
      <div className="max-w-5xl mx-auto text-center">
        <h2 className="text-2xl sm:text-3xl font-extrabold mb-3">
          Why Developers Love Chainless
        </h2>
        <p className="text-gray-400 max-w-3xl mx-auto mb-8">
          Chainless focuses on what truly matters fast iteration, composable
          design, and effortless orchestration. It’s built for developers who
          value clarity, control, and speed.
        </p>

        {/* Feature grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 mb-10">
          {features.map((f, i) => (
            <div
              key={i}
              className="flex gap-4 items-start bg-[#f6f6f6] dark:bg-[#0f0f0f] border border-[#d8d8d8] dark:border-[#1f1f1f] rounded-xl p-5"
            >
              <div className="flex-none rounded-lg bg-linear-to-r from-[#F9E1FF] to-[#00C2FF] text-black p-3">
                {f.icon}
              </div>
              <div className="text-left">
                <h3 className="text-sm font-semibold text-black dark:text-white mb-1">
                  {f.title}
                </h3>
                <p className="text-sm text-[#818181] dark:text-gray-300">{f.desc}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Mini code-snippet */}
        <div className="max-w-3xl mx-auto text-left bg-[#f5f5f5] dark:bg-[#050505] border border-[#d6d6d6] dark:border-[#1b1b1b] rounded-lg p-5">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs text-gray-400">Quickstart</span>
            <span className="text-xs text-gray-500">pip • python</span>
          </div>

          <DynamicCodeBlock  lang="py" code={`# Install
> pip install chainless

# Minimal flow
from chainless import Tool, Agent, TaskFlow

@Tool.tool(name="greet", description="Say hello")
def greet(name: str): 
    return f"Hello, {name}"

agent = Agent(name="welcome", tools=[greet])
flow = TaskFlow("demo")

flow.add_agent("welcome", agent)

flow.step("welcome", step_name="welcome_step", input_map={"input": "{{input}}"})


result = flow.run("Alice")

print(result.output)`} />

         
        </div>
      </div>
    </Container>
  );
};

export default WhyDevelopersLove;
