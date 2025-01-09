"""Logging configuration for scramble."""
import logging
import sys
from typing import Optional
from rich.logging import RichHandler
from rich.console import Console

console = Console()

def setup_logging(level: Optional[str] = None) -> None:
    """Configure logging with minimal format."""
    if level is None:
        level = "INFO"

    # Configure Rich handler with minimal formatting
    rich_handler = RichHandler(
        console=console,
        show_path=True,         # Show filename
        enable_link_path=True,  # Enable clickable links
        markup=True,
        rich_tracebacks=False,  # Disable rich tracebacks
        show_time=False,        # No timestamp
        show_level=True         # Keep level for error distinction
    )

    # Just filename, line number, and message
    rich_handler.setFormatter(logging.Formatter('%(filename)s:%(lineno)d - %(message)s'))

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers = []
    root_logger.addHandler(rich_handler)

def get_logger(name: str) -> logging.Logger:
    """Get a logger with the proper format."""
    return logging.getLogger(name)
