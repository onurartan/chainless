from chainless import Agent, TaskFlow, Tool
from chainless.models import ModelNames
from chainless.exp.server import FlowServer
from pydantic import BaseModel
import random
import asyncio
from enum import Enum

# Using deepseek is not recommended as it may make multiple unnecessary calls and has the lowest accuracy rate. 
# default_model: ModelNames = ModelNames.GEMINI_GEMINI_2_0_FLASH
default_model: ModelNames = ModelNames.DEEPSEEK_CHAT

# ----------------------------
# Tools
# ----------------------------
class SystemName(str, Enum):
    MAIL_SERVER = "mail_server"
    PAYMENT_GATEWAY = "payment_gateway"
    DATABASE = "database"


def check_system_status(system_name: SystemName):
    statuses = {
        SystemName.MAIL_SERVER: "Mail server is running smoothly. Last inspection was 3 days ago.",
        SystemName.PAYMENT_GATEWAY: "Payment gateway is operating with 99.9 percent uptime and is stable.",
        SystemName.DATABASE: "Database is responsive with 85 percent performance. No critical alerts.",
    }
    return statuses.get(system_name, f"No status information found for '{system_name}'.")


async def get_user_account_info(user_id: str):
    """Returns the user's current account status and plan."""
    plans = ["Free Plan", "Premium Plan", "Enterprise Plan"]
    status = random.choice(["active", "suspended", "frozen"])
    plan = random.choice(plans)
    await asyncio.sleep(0.1)
    return f"User {user_id}: Status: {status}, Plan: {plan}"


# Tool definitions
status_tool = Tool(
    "SystemStatusTool",
    "Checks whether a given system is operational and returns status details.",
    check_system_status,
)

account_tool = Tool(
    "UserAccountTool",
    "Fetches the specified user's account status and plan.",
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
    model=default_model,
    system_prompt=(
        "Task: Classify the user's request into the correct category.\n"
        "Categories: 'billing', 'technical', 'account', 'other'.\n"
        "Provide a clear explanation for your classification."
    ),
    response_format=ClassifierOutput,
)

solution_agent = Agent(
    name="SolutionGenerator",
    model=default_model,
    tools=[status_tool, account_tool],
    system_prompt=(
        "Task: Generate an appropriate solution based on the user's request.\n"
        "Use SystemStatusTool or UserAccountTool if needed.\n"
        "Provide a clear, easy to understand solution."
    ),
    response_format=SolutionOutput,
)

report_agent = Agent(
    name="SupportReportAgent",
    model=default_model,
    system_prompt=(
        "Task: Use the category and solution from previous steps to create a complete support report.\n"
        "Provide a clear and simple report for the user without unnecessary technical details."
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
We received a support request under the category: {{category}}.
Details: {{details}}

Please provide an appropriate solution. If necessary, use the following tools:
1. SystemStatusTool: Retrieves system performance and operational status.
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
Support Ticket Report:
Category: {{category}}
Solution: {{solution}}
Please use this information to provide a clear and complete report to the user.
""",
)


# ----------------------------
# Serve via FlowServer
# ----------------------------

support_endpoint = support_flow.serve(path="/support", name="Support Flow")
server = FlowServer(endpoints=[support_endpoint], port=8080, api_key="example_key")

if __name__ == "__main__":
    server.run()
