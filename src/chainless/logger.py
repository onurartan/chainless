import logging
from rich.console import Console
from rich.logging import RichHandler
from rich.theme import Theme

custom_theme = Theme(
    {
        "logging.level.debug": "dim cyan",
        "logging.level.info": "bold white",
        "logging.level.warning": "bold yellow",
        "logging.level.error": "bold red",
        "logging.level.critical": "bold reverse red",
        "tool.name": "bold magenta",
        "log.time": "green",
        "logging.level.custom": "green",
    }
)
console = Console(theme=custom_theme)


# Chainless Logger
def get_logger(name: str = "chainless", level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        handler = RichHandler(
            console=console,
            markup=True,
            rich_tracebacks=True,
            show_path=False,
            show_time=False,
            show_level=False,
        )

        handler.setFormatter(
            logging.Formatter("[#0c6eed]%(name)s [white]- %(message)s", datefmt="[%X]")
        )
        logger.addHandler(handler)
        logger.propagate = False

    return logger
