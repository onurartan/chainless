from chainless import Tool, Agent, TaskFlow
from chainless.models import ModelNames
from dotenv import load_dotenv

import requests
from playwright.sync_api import sync_playwright

from .types import WebSiteAnalysisResponse

load_dotenv()

# --- Tools ---

def fetch_html(url: str) -> str:
    res = requests.get(url)
    res.raise_for_status()
    return res.text

html_tool = Tool(
    name="HTMLFetcher",
    description="Fetch HTML content from a URL",
    func=fetch_html
)

def take_screenshot(url: str) -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="networkidle")
        path = f"screenshot.png"
        page.screenshot(path=path)
        browser.close()
        return path

screenshot_tool = Tool(
    name="ScreenshotTaker",
    description="Take screenshot of the URL",
    func=take_screenshot
)

# --- Agent ---
agent = Agent(
    name="WebAnalyzerAgent",
    model=ModelNames.DEEPSEEK_CHAT,
    tools=[html_tool, screenshot_tool],
    response_format=WebSiteAnalysisResponse,
    system_prompt=(
        "You are a web analysis assistant. "
        "You can call the tools: HTMLFetcher (to get page HTML) and ScreenshotTaker (to take screenshots). "
        "Based on user input, decide which tools to call and in what order. "
        "Return final result as JSON with 'html' and 'screenshot_path' fields."
    )
)

# --- TaskFlow ---
flow = TaskFlow(name="SmartWebAnalysis", verbose=True)

flow.add_agent("web_agent", agent)
flow.step("web_agent", {"input": "{{input}}"})

if __name__ == "__main__":
    url = "https://www.movixar.com"
    result = flow.run(url)
    print("Final Agent Output:")
    print(result.output)
