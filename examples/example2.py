from chainless import Agent, TaskFlow, Tool
from chainless.memory import Memory
from pydantic import BaseModel
import random
import asyncio
from enum import Enum

import anyio


# ----------------------------
# Tools
# ----------------------------
class SystemName(str, Enum):
    MAIL_SERVER = "mail_server"
    PAYMENT_GATEWAY = "payment_gateway"
    DATABASE = "database"


def check_system_status(system_name: SystemName):
    statuses = {
        SystemName.MAIL_SERVER: "The mail server is running smoothly, last check was performed 3 days ago.",
        SystemName.PAYMENT_GATEWAY: "The payment gateway is operating with 99.9% uptime and is stable.",
        SystemName.DATABASE: "The database is responding, performance is at 85%, no critical alerts.",
    }
    return statuses.get(
        system_name, f"No information found about the '{system_name}' system."
    )


async def get_user_account_info(user_id: str):
    """Returns the user's current status and plan information."""
    plans = ["Free Plan", "Premium Plan", "Enterprise Plan"]
    status = random.choice(["active", "suspended", "frozen"])
    plan = random.choice(plans)
    await asyncio.sleep(0.1)
    return f"User {user_id}: Status: {status}, Plan: {plan}"


# Tool definitions
status_tool = Tool(
    "SystemStatusTool",
    "Checks whether the specified system is operational and reports its current status.",
    check_system_status,
)
account_tool = Tool(
    "UserAccountTool",
    "Retrieves the status and plan information of the specified user account.",
    get_user_account_info,
)

# ----------------------------
# Structured Output Models
# ----------------------------


class ClassifierOutput(BaseModel):
    category: str
    reason: str


class SolutionOutput(BaseModel):
    solution: str


# ----------------------------
# Agents
# ----------------------------

classifier_agent = Agent(
    name="IssueClassifier",
    system_prompt=(
        "Task: Classify the user's complaint into the correct category.\n"
        "Categories: 'billing', 'technical', 'account', 'other'.\n"
        "Provide a clear explanation of the reasoning."
    ),
    response_format=ClassifierOutput,
)

solution_agent = Agent(
    name="SolutionGenerator",
    tools=[status_tool, account_tool],
    system_prompt=(
        "Task: Generate a solution appropriate to the user's request.\n"
        "Use SystemStatusTool or UserAccountTool if necessary.\n"
        "Present the solution clearly and understandably."
    ),
    response_format=SolutionOutput,
)

report_agent = Agent(
    name="SupportReportAgent",
    system_prompt=(
        "Task: Using the category and solution from the previous steps, create a comprehensive support report.\n"
        "Provide a clear and understandable report to the user without unnecessary technical details."
    ),
)

# ----------------------------
# TaskFlow
# ----------------------------

support_flow = TaskFlow("SupportFlow", verbose=True)
support_flow.add_agent("Classifier", classifier_agent)
support_flow.add_agent("Solution", solution_agent)
support_flow.add_agent("Report", report_agent)


support_flow.step("Classifier", input_map={"input": "{{input}}"})
support_flow.step(
    "Solution",
    step_name="SolutionStep1",
    input_map={"category": "{{Classifier.output.category}}", "details": "{{input}}"},
    prompt_template="""
We received a support request categorized as {{category}}.
Details: {{details}}

Please provide an appropriate solution suggestion. If necessary, use the following tools:
1. SystemStatusTool: Provides system status and performance information.
2. UserAccountTool: Retrieves user account information.
""",
)
support_flow.step(
    "Report",
    input_map={
        "category": "{{Classifier.output.category}}",
        "solution": "{{SolutionStep1.output.solution}}",
    },
    prompt_template="""
Support Request Report:
Category: {{category}}
Solution: {{solution}}
Please use this information to present a comprehensive report to the user.
    """,
)


async def main():

    memory = Memory()

    # ----------------------------
    # RUN
    # ----------------------------
    while True:

        user_input = input("Describe your issue (type 'exit' to quit): ")
        if user_input.lower() == "exit":
            break

        memory.add_user(content=user_input)

        support_flow.ctx._get_step_by_name("Report").message_history = memory.get()

        result = await support_flow.run_async(user_input)
        print("\n--- Final Report ---")
        output = result.output

        memory.add_assistant(content=output)
        print(output)
        # print(memory.get())


if __name__ == "__main__":
    anyio.run(main)
