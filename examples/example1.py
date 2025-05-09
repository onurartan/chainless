from chainless import Agent, TaskFlow, Tool
from langchain_deepseek import ChatDeepSeek
from dotenv import load_dotenv

from langchain.prompts import ChatPromptTemplate

load_dotenv()


# ----------------------------
# Tool Funcs
# ----------------------------
def wiki_search(query: str):
    return f"Wikipedia info: A brief description about {query}."


def yt_transcript(query: str):
    return f"Automated YouTube transcript of {query} video."


# ----------------------------
# Tools
# ----------------------------
wiki_tool = Tool("WikiTool", "Searches for information on Wikipedia", wiki_search)
yt_tool = Tool("YTTool", "Gets YouTube video transcript", yt_transcript)

# ----------------------------
# LLM
# ----------------------------
llm = ChatDeepSeek(model="deepseek-chat")


# ----------------------------
# Agents
# ----------------------------
wiki_agent = Agent(
    name="WikipediaAgent",
    llm=llm,
    tools=[wiki_tool],
    system_prompt="Bring only Wikipedia information. Do not add any other information.",
)

yt_agent = Agent(
    name="YouTubeAgent",
    llm=llm,
    tools=[yt_tool],
    system_prompt="Return the transcript from YouTube.",
)

summary_agent = Agent(
    name="Summarizer",
    llm=llm,
    system_prompt="Summarize the incoming information in a short and meaningful way. Reduce to 3 sentences.",
)


@summary_agent.custom_start
def start(input: str, tools, system_prompt):
    user_input: str = f""" 
    {input}
    """

    model = llm

    tools = tools

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt or "You're an assistant agent."),
            ("human", "{input}"),
        ]
    )

    chain = model | prompt

    result = chain.invoke(user_input)

    return result


rapor_agent = Agent(
    name="Reporter",
    llm=llm,
    system_prompt="""
    Create a report by collecting the following data:
    - wikipedia_Summary
    - youtube_Summary
    Format: JSON object {“subject”: ..., “wikipedia”: ..., “youtube”: ...}
    Don't write any further comments, just return JSON.
    """,
)


@rapor_agent.custom_start
def start(wikipedia_summary: str, youtube_summary: str, tools, system_prompt):
    user_input: str = f""" 
    wikipedia_Summary: {wikipedia_summary}
    youtube_Summary: {youtube_summary}
    user_input: {input}
    """

    model = llm

    tools = tools

    result = model.invoke(user_input)

    return result


class EchoAgent:
    name = "Echo"

    def start(self, input: str, verbose: bool = False, **kwargs):
        return {"output": f"Echoed: {input}"}


# ----------------------------
# TaskFlow
# ----------------------------
flow = TaskFlow("ResearchFlow", verbose=True)

flow.add_agent("echo", EchoAgent())
flow.add_agent("WikipediaAgent", wiki_agent)
flow.add_agent("YouTubeAgent", yt_agent)
flow.add_agent("Summarizer", summary_agent)
flow.add_agent("Reporter", rapor_agent)


flow.step("WikipediaAgent", input_map={"input": "{{input}}"})
flow.step("YouTubeAgent", input_map={"input": "{{input}}"})
flow.parallel(["WikipediaAgent", "YouTubeAgent"])


flow.step("WikipediaSummary", input_map={"input": "{{WikipediaAgent.output.output}}"})
flow.add_agent("WikipediaSummary", summary_agent)

flow.step("YouTubeSummary", input_map={"input": "{{YouTubeAgent.output.output}}"})
flow.add_agent("YouTubeSummary", summary_agent)

flow.step("echo", input_map={"input": "{{YouTubeSummary.output}}"})


flow.step(
    "Reporter",
    input_map={
        "wikipedia_summary": "{{WikipediaSummary.output}}",
        "youtube_summary": "{{YouTubeSummary.output}}",
    },
)

# ----------------------------
# RUN
# ----------------------------
while True:
    user_input = input("Enter topic (exit to exit): ")
    if user_input.lower() == "exit":
        print("Bye!")
        break

    result = flow.run(user_input)
    print("\n--- Final ---")
    print(result["output"]["content"])
