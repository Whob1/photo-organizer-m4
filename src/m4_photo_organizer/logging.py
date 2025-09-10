import logging
import os
from rich.console import Console
from rich.logging import RichHandler

_console = Console()

_LEVEL = os.getenv("PHOTOORG_LOG_LEVEL", "INFO").upper()

_logging_configured = False

def get_logger(name: str) -> logging.Logger:
    global _logging_configured
    if not _logging_configured:
        logging.basicConfig(
            level=_LEVEL,
            format="%(message)s",
            datefmt="[%X]",
            handlers=[RichHandler(console=_console, rich_tracebacks=True, markup=True)],
        )
        _logging_configured = True
    return logging.getLogger(name)

