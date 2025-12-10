from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markup import escape

console = Console()


def spacing():
    console.print("")


def escape_rich_markup(text):
    """Escape special characters in text to prevent Rich markup interpretation"""
    if text is None:
        return ""

    # Convert to string if not already
    if not isinstance(text, str):
        text = str(text)

    # Use Rich's built-in escape function
    return escape(text)


def error_message(error_type: str, detail: str, error_code: int = None):
    """
    Prints a formatted error panel for API and service errors.

    Args:
        error_type: The type of error (e.g., "API Key Error", "Call Error")
        detail: Detailed error message
        error_code: Optional HTTP status code
    """
    table = Table(show_header=False, expand=True, box=None)
    table.width = 60

    # Add error code if provided
    if error_code:
        table.add_row("[bold]Error Code:[/bold]", f"[red]{error_code}[/red]")
        table.add_row("")  # Add spacing

    # Add error details
    table.add_row("[bold]Error Details:[/bold]")
    table.add_row(f"[red]{escape_rich_markup(detail)}[/red]")

    panel = Panel(
        table,
        title=f"[bold red]Chainless - {escape_rich_markup(error_type)}[/bold red]",
        border_style="red",
        expand=True,
        width=70,
    )

    console.print(panel)
    spacing()
