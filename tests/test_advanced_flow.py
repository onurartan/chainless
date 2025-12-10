from chainless import Tool, Agent, TaskFlow
from chainless.models import ModelNames

# ------------------------------------------------------------
# Test 2 — Advanced Flow: retries, conditions, slow step, final report
# ------------------------------------------------------------
def test_advanced_flow():
    # --------- Tool --------- #
    def mock_data(q):
        return f"Data for {q}"

    data_tool = Tool("DataTool", "Mock data", mock_data)

    # -------- Agents -------- #
    fetch = Agent("Fetch", model=ModelNames.DEEPSEEK_CHAT, tools=[data_tool])
    transform = Agent("Transform", model=ModelNames.DEEPSEEK_CHAT)
    condition = Agent("Condition", model=ModelNames.DEEPSEEK_CHAT)
    flaky = Agent("Flaky", model=ModelNames.DEEPSEEK_CHAT)
    slow = Agent("Slow", model=ModelNames.DEEPSEEK_CHAT)
    final = Agent("Final", model=ModelNames.DEEPSEEK_CHAT)

    # -------- Mocks -------- #
    @fetch.on_start
    def mock_fetch(ctx):
        return {"output": f"Fetched {ctx.input} RunMe"}

    @transform.on_start
    def mock_trans(ctx):
        return ctx.input.replace("Fetched", "Transformed")

    @condition.on_start
    def mock_cond(ctx):
        return "Condition OK"

    retry = {"count": 0}

    @flaky.on_start
    def mock_flaky(ctx):
        if retry["count"] == 0:
            retry["count"] += 1
        return "Success after retry"

    @slow.on_start
    def mock_slow(ctx):
        return "Slow OK"

    @final.on_start
    def mock_final(ctx):
        return {
            "fetch": ctx.extra_inputs["fetch"],
            "transform": ctx.extra_inputs["transform"],
            "condition": ctx.extra_inputs["condition"],
            "flaky": ctx.extra_inputs["flaky"],
            "slow": ctx.extra_inputs["slow"],
        }

    # -------- Flow -------- #
    flow = TaskFlow("Advanced")

    flow.add_agent("fetch", fetch)
    flow.add_agent("transform", transform)
    flow.add_agent("condition", condition)
    flow.add_agent("flaky", flaky)
    flow.add_agent("slow", slow)
    flow.add_agent("final", final)

    flow.step("fetch", input_map={"input": "{{input}}"})
    flow.alias("fetch", "fetch", "output.output")

    flow.step("transform", input_map={"input": "{{fetch}}"}, depends_on=["fetch"])
    
    

    flow.step(
        "condition",
        input_map={"input": "{{fetch}}"},
        depends_on=["fetch"],
        condition=lambda steps: "RunMe" in steps["fetch"].output["output"],
    )

    flow.step(
        "flaky",
        input_map={"input": "{{fetch}}"},
        depends_on=["fetch"],
        retry_on_fail=2,
    )

    flow.step(
        "slow",
        input_map={"input": "{{fetch}}"},
        depends_on=["fetch"],
    )

    flow.step(
        "final",
        input_map={
            "fetch": "{{fetch}}",
            "transform": "{{transform.output}}",
            "condition": "{{condition.output}}",
            "flaky": "{{flaky.output}}",
            "slow": "{{slow.output}}",
        },
        depends_on=["transform", "condition", "flaky", "slow"],
    )

    result = flow.run("AI")
    
    assert result.flow.steps["flaky"].output == "Success after retry"
    assert "Transformed" in result.flow.steps["transform"].output
    assert result.flow.steps["condition"].output == "Condition OK"
