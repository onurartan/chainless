from chainless import Tool, Agent, TaskFlow
from langchain_deepseek import ChatDeepSeek
from dotenv import load_dotenv

load_dotenv()


def test_taskflow_multi_source_summary_report():
    # --------- Mock Tool Functions --------- #
    def mock_wiki(query: str):
        return "Wikipedia: Python is a high-level programming language."

    def mock_yt(query: str):
        return "YouTube: A transcript of an educational Python video."

    # --------- Mock Tools --------- #
    wiki_tool = Tool("MockWiki", "Retrieves information from Wikipedia", mock_wiki)
    yt_tool = Tool("MockYT", "Fetches YouTube video transcripts", mock_yt)

    llm = ChatDeepSeek(model="deepseek-chat")

    # --------- Agents --------- #
    wiki_agent = Agent(
        name="WikiAgent",
        llm=llm,
        tools=[wiki_tool],
        system_prompt="Only retrieve content from Wikipedia.",
    )

    yt_agent = Agent(
        name="YTAgent",
        llm=llm,
        tools=[yt_tool],
        system_prompt="Only return the transcript from YouTube.",
    )

    summary_agent_wiki = Agent(
        name="SummaryAgentWiki",
        llm=llm,
        system_prompt="Summarize Wikipedia content.",
    )

    summary_agent_yt = Agent(
        name="SummaryAgentYT",
        llm=llm,
        system_prompt="Summarize YouTube transcript.",
    )

    report_agent = Agent(
        name="ReportAgent",
        llm=llm,
        system_prompt="Generate a JSON report from wikipedia_ozet and youtube_ozet.",
    )

    # --------- Custom Starts --------- #

    @wiki_agent.custom_start
    def custom_wiki_start(input: str, tools, system_prompt):
        return {"output": "Wikipedia: Python is a high-level programming language."}

    @yt_agent.custom_start
    def custom_yt_start(input: str, tools, system_prompt):
        return {"output": "YouTube: A transcript of an educational Python video."}

    @summary_agent_wiki.custom_start
    def custom_summary_wiki_start(input: str, tools, system_prompt):
        assert "Wikipedia" in input
        return "Python is a popular programming language among developers."

    @summary_agent_yt.custom_start
    def custom_summary_yt_start(input: str, tools, system_prompt):
        assert "YouTube" in input
        return "The video explains how to define variables in Python."

    @report_agent.custom_start
    def custom_report_start(
        wikipedia_ozet: str, youtube_ozet: str, tools, system_prompt
    ):
        return {
            "topic": "Python",
            "wikipedia": wikipedia_ozet,
            "youtube": youtube_ozet,
        }

    # --------- TaskFlow Definition --------- #
    flow = TaskFlow("MultiSourceSummaryReport")

    flow.add_agent("wiki", wiki_agent)
    flow.add_agent("yt", yt_agent)
    flow.add_agent("summary_wiki", summary_agent_wiki)
    flow.add_agent("summary_yt", summary_agent_yt)
    flow.add_agent("report", report_agent)

    flow.step("wiki", input_map={"input": "{{input}}"})
    flow.step("yt", input_map={"input": "{{input}}"})

    flow.parallel(["wiki", "yt"])

    flow.step("summary_wiki", input_map={"input": "{{wiki.output.output}}"})
    flow.step("summary_yt", input_map={"input": "{{yt.output.output}}"})

    flow.step(
        "report",
        input_map={
            "wikipedia_ozet": "{{summary_wiki.output}}",
            "youtube_ozet": "{{summary_yt.output}}",
        },
    )

    # --------- Run TaskFlow --------- #
    user_input = "Python"
    result = flow.run(user_input)

    # --------- Assertions --------- #
    assert isinstance(result["output"], dict)
    assert result["output"]["topic"] == "Python"
    assert "popular programming language" in result["output"]["wikipedia"]
    assert "define variables" in result["output"]["youtube"]
