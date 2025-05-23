from chainless import Tool, Agent, TaskFlow
from langchain_deepseek import ChatDeepSeek
from dotenv import load_dotenv
import time

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
    flow = TaskFlow("MultiSourceSummaryReport", verbose=True)

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


def test_taskflow_with_all_advanced_features():
    # ----------------- Mock Tool Functions ----------------- #
    def mock_data_api(query: str):
        return f"Data for {query}"

    # ----------------- Tools ----------------- #
    data_tool = Tool("DataTool", "Returns mock data", mock_data_api)

    # ----------------- LLM ----------------- #
    llm = ChatDeepSeek(model="deepseek-chat")

    # ----------------- Agents ----------------- #
    fetch_agent = Agent(
        name="FetchAgent",
        llm=llm,
        tools=[data_tool],
        system_prompt="Fetch data for given topic.",
    )

    transform_agent = Agent(
        name="TransformAgent",
        llm=llm,
        system_prompt="Transform the fetched data into a better format.",
    )

    condition_agent = Agent(
        name="ConditionAgent",
        llm=llm,
        system_prompt="This step should only run if the fetched data contains 'RunMe'.",
    )

    flaky_agent = Agent(
        name="FlakyAgent",
        llm=llm,
        system_prompt="Fails once, succeeds on retry.",
    )

    slow_agent = Agent(
        name="SlowAgent",
        llm=llm,
        system_prompt="Intentionally slow agent.",
    )

    final_agent = Agent(
        name="FinalAgent",
        llm=llm,
        system_prompt="Combine everything into a final report.",
    )

    # ----------------- Custom Start Mocks ----------------- #
    @fetch_agent.custom_start
    def fetch_start(input, tools, system_prompt):
        return {"output": f"Fetched: {input} RunMe"}

    @transform_agent.custom_start
    def transform_start(input, tools, system_prompt):
        return input.replace("Fetched:", "Transformed:")

    @condition_agent.custom_start
    def condition_start(input, tools, system_prompt):
        assert "RunMe" in input
        return "Condition met and step executed."

    retry_counter = {"count": 0}

    @flaky_agent.custom_start
    def flaky_start(input, tools, system_prompt):
        if retry_counter["count"] < 1:
            retry_counter["count"] += 1
            raise Exception("Temporary error.")
        return "Recovered after retry."

    @slow_agent.custom_start
    def slow_start(input, tools, system_prompt):
        time.sleep(0.1)  # Mock delay
        return "Completed despite delay."

    @final_agent.custom_start
    def final_start(fetch, transform, condition, flaky, slow, tools, system_prompt):
        return {
            "fetch": fetch,
            "transform": transform,
            "condition": condition,
            "flaky": flaky,
            "slow": slow,
        }

    def increment_retry(step_name, user_input):
        print(
            f" {step_name} ->  Retry counter before increment: {retry_counter['count']}"
        )
        retry_counter["count"] += 1
        print(f"{step_name} -> Retry counter after increment: {retry_counter['count']}")

    # ----------------- TaskFlow Setup ----------------- #
    flow = TaskFlow("AdvancedFlow", verbose=True, on_step_start=increment_retry)

    flow.add_agent("fetcher", fetch_agent)
    flow.add_agent("transform", transform_agent)
    flow.add_agent("condition_check", condition_agent)
    flow.add_agent("flaky", flaky_agent)
    flow.add_agent("slow", slow_agent)
    flow.add_agent("final", final_agent)

    flow.step("fetcher", input_map={"input": "{{input}}"}, step_name="data_fetcher")
    flow.alias("data_fetcher", "data_fetcher", "output.output")

    flow.step(
        "transform",
        input_map={"input": "{{data_fetcher}}"},
        depends_on=["data_fetcher"],
    )

    flow.step(
        "condition_check",
        input_map={"input": "{{data_fetcher}}"},
        depends_on=["data_fetcher"],
        on_start=increment_retry,
        condition=lambda steps: "RunMe" in steps["data_fetcher"]["output"]["output"],
    )

    flow.step(
        "flaky",
        input_map={"input": "{{data_fetcher}}"},
        depends_on=["data_fetcher"],
        retry_on_fail=3,
    )

    flow.step(
        "slow",
        input_map={"input": "{{data_fetcher}}"},
        depends_on=["data_fetcher"],
        timeout=1,  # Mocked as very short
    )

    flow.step(
        "final",
        input_map={
            "fetch": "{{data_fetcher}}",
            "transform": "{{transform.output}}",
            "condition": "{{condition_check.output}}",
            "flaky": "{{flaky.output}}",
            "slow": "{{slow.output}}",
        },
        depends_on=["transform", "condition_check", "flaky", "slow"],
    )

    # ----------------- Run TaskFlow ----------------- #
    result = flow.run("AI")

    # ----------------- Assertions ----------------- #
    assert isinstance(result["output"], dict)
    assert "fetch" in result["output"]
    assert result["output"]["flaky"] == "Recovered after retry."
    assert "Transformed:" in result["output"]["transform"]
    assert "Condition met" in result["output"]["condition"]
    assert "delay" in result["output"]["slow"]
