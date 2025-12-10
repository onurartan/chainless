from chainless import Agent, TaskFlow, Tool
from chainless.exp.server import FlowServer
from chainless.models import ModelNames
from pydantic import BaseModel
import random
import asyncio
from enum import Enum

# Using deepseek is not recommended as it may make multiple unnecessary calls and has the lowest accuracy rate.
default_model: ModelNames = ModelNames.GEMINI_GEMINI_2_0_FLASH
# default_model: ModelNames = ModelNames.DEEPSEEK_CHAT

# ----------------------------
# Tools
# ----------------------------


class PaymentSystem(str, Enum):
    PAYMENT_GATEWAY = "payment_gateway"
    FRAUD_ENGINE = "fraud_engine"
    LEDGER = "ledger"


def get_system_health(system: PaymentSystem):
    """Returns a mock system status for demonstration."""
    statuses = {
        PaymentSystem.PAYMENT_GATEWAY: "Payment gateway is operational with 99 percent uptime.",
        PaymentSystem.FRAUD_ENGINE: "Fraud engine is running with normal risk thresholds.",
        PaymentSystem.LEDGER: "Ledger system is synchronized and stable.",
    }
    return statuses.get(system, f"No status information available for {system}.")


async def get_transaction_info(tx_id: str):
    """Simulates fetching transaction details."""
    states = ["pending", "failed", "completed", "reversed"]
    amount = random.randint(10, 500)
    status = random.choice(states)
    await asyncio.sleep(0.1)
    return f"Transaction {tx_id}: Status: {status}, Amount: {amount} USD"


system_tool = Tool(
    "PaymentSystemTool",
    "Returns the current status of a payment related subsystem.",
    get_system_health,
)

transaction_tool = Tool(
    "TransactionLookupTool",
    "Fetches mock transaction information based on transaction ID.",
    get_transaction_info,
)


# ----------------------------
# Structured Output Models
# ----------------------------


class PaymentClassifierOutput(BaseModel):
    category: str
    reason: str


class PaymentSolutionOutput(BaseModel):
    solution: str


# ----------------------------
# Agents
# ----------------------------

classifier_agent = Agent(
    name="PaymentClassifier",
    model=default_model,
    system_prompt=(
        "Task: Classify the user's payment issue.\n"
        "Categories: 'failed_payment', 'delayed_payment', 'refund_request', 'other'.\n"
        "Explain the reasoning clearly."
        "IMPORTANT RULE:"
        "After receiving a tool result, you MUST produce a final answer."
        "Do NOT call a tool again after getting tool output."
    ),
    response_format=PaymentClassifierOutput,
)

solution_agent = Agent(
    name="PaymentSolutionGenerator",
    model=default_model,
    tools=[system_tool, transaction_tool],
    system_prompt=(
        "Task: Generate a helpful solution for the user's payment issue.\n"
        "You may use PaymentSystemTool or TransactionLookupTool if needed.\n"
        "Provide a clear and actionable recommendation."
        "IMPORTANT RULE:"
        "After receiving a tool result, you MUST produce a final answer."
        "Do NOT call a tool again after getting tool output."
    ),
    response_format=PaymentSolutionOutput,
)

report_agent = Agent(
    name="PaymentReportAgent",
    model=default_model,
    system_prompt=(
        "Task: Create a final customer facing payment support report.\n"
        "Combine the issue category and the generated solution.\n"
        "Deliver a clear and easy to understand summary."
        "IMPORTANT RULE:"
        "After receiving a tool result, you MUST produce a final answer."
        "Do NOT call a tool again after getting tool output."
    ),
    response_format=str
)


# ----------------------------
# TaskFlow
# ----------------------------

payment_flow = TaskFlow("PaymentSupportFlow", verbose=True)
payment_flow.add_agent("Classifier", classifier_agent)
payment_flow.add_agent("Solution", solution_agent)
payment_flow.add_agent("Report", report_agent)

payment_flow.step("Classifier", input_map={"input": "{{input}}"})

payment_flow.step(
    "Solution",
    step_name="SolutionStep",
    input_map={"category": "{{Classifier.output.category}}", "details": "{{input}}"},
    prompt_template="""
A payment related issue has been categorized as {{category}}.
Details: {{details}}

Please generate an appropriate solution.
Use the following tools when necessary:
1. PaymentSystemTool for system health checks.
2. TransactionLookupTool for transaction information.
""",
)

payment_flow.step(
    "Report",
    input_map={
        "category": "{{Classifier.output.category}}",
        "solution": "{{SolutionStep.output.solution}}",
    },
    prompt_template="""
Payment Issue Report:
Category: {{category}}
Solution: {{solution}}
Please generate a complete and concise customer facing report.
""",
)


# ----------------------------
# FlowServer Setup
# ----------------------------

endpoint = payment_flow.serve(path="/payment-support", name="Payment Support Flow")
server = FlowServer(endpoints=[endpoint], port=8080, api_key="example_key")

if __name__ == "__main__":
    server.run()
