"""Logging configuration for scramble."""
import logging
import sys
from typing import Optional
from rich.logging import RichHandler
from rich.console import Console

console = Console()

def setup_logging(level: Optional[str] = None) -> None:
    """Configure logging with proper format including filename and line numbers."""
    if level is None:
        level = "INFO"

    # Configure Rich handler
    rich_handler = RichHandler(
        console=console,
        show_path=True,
        enable_link_path=True,
        markup=True,
        rich_tracebacks=True
    )

    # Configure formatter to work with Rich
    rich_handler.setFormatter(logging.Formatter(
        '%(message)s',  # Rich handles the rest
        datefmt='%Y-%m-%d %H:%M:%S'
    ))

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove any existing handlers and add our Rich handler
    root_logger.handlers = []
    root_logger.addHandler(rich_handler)

def get_logger(name: str) -> logging.Logger:
    """Get a logger with the proper format."""
    return logging.getLogger(name)
