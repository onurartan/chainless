from chainless import Tool, Agent, TaskFlow
from chainless.models import ModelNames


# ------------------------------------------------------------
# Test 1 — Multi-Source → Summary → Report Flow
# ------------------------------------------------------------
def test_taskflow():
    # --------- Mock Tools --------- #
    def mock_wiki(q: str) -> str:
        return "Wikipedia says Python is a popular programming language."

    def mock_yt(q):
        return "Video teaches how variables work in Python."

    wiki_tool = Tool("Wiki", "Get wiki data", mock_wiki)
    yt_tool = Tool("YouTube", "Get yt transcript", mock_yt)

    # --------- Agents --------- #
    wiki_agent = Agent(
        name="WikiAgent",
        model=ModelNames.DEEPSEEK_CHAT,
        tools=[wiki_tool],
        system_prompt="Return only Wikipedia content."
    )

    yt_agent = Agent(
        name="YTAgent",
        model=ModelNames.DEEPSEEK_CHAT,
        tools=[yt_tool],
        system_prompt="Return only YouTube transcript."
    )

    summary_wiki = Agent(
        name="SummaryWiki",
        model=ModelNames.DEEPSEEK_CHAT,
        system_prompt="Summarize the Wikipedia text."
    )

    summary_yt = Agent(
        name="SummaryYT",
        model=ModelNames.DEEPSEEK_CHAT,
        system_prompt="Summarize the YouTube transcript."
    )

    report_agent = Agent(
        name="ReportAgent",
        model=ModelNames.DEEPSEEK_CHAT,
        system_prompt="Combine wikipedia_summary and youtube_summary into a final JSON report."
    )

    # --------- Mocked starts --------- #
    @wiki_agent.on_start
    def mock_wiki_start(ctx):
        return {"output": mock_wiki(ctx.input)}

    @yt_agent.on_start
    def mock_yt_start(ctx):
        return {"output": mock_yt(ctx.input)}

    @summary_wiki.on_start
    def mock_sum_wiki(ctx):
        return "Python is popular."

    @summary_yt.on_start
    def mock_sum_yt(ctx):
        return "The video explains variables."

    @report_agent.on_start
    def mock_report(ctx):
        return {
            "topic": "Python",
            "wiki": ctx.extra_inputs["wikipedia_summary"],
            "youtube": ctx.extra_inputs["youtube_summary"],
        }

    # --------- Flow --------- #
    flow = TaskFlow("MultiSource")

    flow.add_agent("wiki", wiki_agent)
    flow.add_agent("yt", yt_agent)
    flow.add_agent("sum_wiki", summary_wiki)
    flow.add_agent("sum_yt", summary_yt)
    flow.add_agent("report", report_agent)

    flow.step("wiki", input_map={"input": "{{input}}"})
    flow.step("yt", input_map={"input": "{{input}}"})

    flow.parallel(["wiki", "yt"])

    flow.step("sum_wiki", input_map={"input": "{{wiki.output.output}}"})
    flow.step("sum_yt", input_map={"input": "{{yt.output.output}}"})

    flow.step(
        "report",
        input_map={
            "wikipedia_summary": "{{sum_wiki.output}}",
            "youtube_summary": "{{sum_yt.output}}",
        },
    )

    result = flow.run("Python")

    assert result.output["topic"] == "Python"
    assert "popular" in result.output["wiki"]
    assert "variables" in result.output["youtube"]


