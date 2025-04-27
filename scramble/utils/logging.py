"""Logging configuration for scramble.

This logger has two distinct sections:
1. MEATBAG ZONE - Core logging setup that Rob likes and relies on
2. CLAUDE ZONE - Debug session logging that Claude uses for analysis
"""
import logging
import sys
from typing import Optional, List
from rich.logging import RichHandler
from rich.console import Console
from pathlib import Path
from datetime import datetime
from scramble.config import Config

console = Console()

def setup_logging(level: Optional[str] = None, debug_session: Optional[bool] = None) -> None:
    """Configure logging with minimal format."""
    if level is None:
        level = "INFO"
        
    # Use Config class for debug setting
    if debug_session is None:
        debug_session = Config.DEBUG_SESSION
        
    # Check if detailed logging is enabled
    import os
    detailed_logging = os.environ.get('SCRAMBLE_DETAILED_LOGGING', '0') == '1'

    # Explicitly type the handlers list
    handlers: List[logging.Handler] = []

    # Configure Rich handler for terminal (always INFO)
    rich_handler = RichHandler(
        console=console,
        show_path=True,
        enable_link_path=True,
        markup=True,
        rich_tracebacks=False,
        show_time=False,
        show_level=True
    )
    rich_handler.setLevel(logging.INFO)  # Keep terminal at INFO level
    rich_handler.setFormatter(logging.Formatter('%(filename)s:%(lineno)d - %(message)s'))
    handlers.append(rich_handler)

    # ==========================================
    # 🤖 CLAUDE ZONE 
    # Session-based debug logging
    # Dumps to project logs directory for access
    # ==========================================

    if debug_session:
        # Create logs directory in project root
        log_dir = Path('/Users/rob/repos/scramble/logs')
        log_dir.mkdir(exist_ok=True)
        session_file = log_dir / f'scramble_debug_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
        file_handler = logging.FileHandler(session_file)
        file_handler.setLevel(logging.DEBUG)  # Debug level just for file
        
        # Use custom formatter to reduce verbose logging if not in detailed mode
        if detailed_logging:
            file_formatter = logging.Formatter(
                '%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s - %(message)s'
            )
        else:
            # Try to use the compact formatter if available
            try:
                from .logging_config import CompactFormatter
                file_formatter = CompactFormatter(
                    '%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s - %(message)s'
                )
            except ImportError:
                file_formatter = logging.Formatter(
                    '%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s - %(message)s'
                )
                
        file_handler.setFormatter(file_formatter)
        handlers.append(file_handler)
        print(f"\n🤖 Claude's debug logs for this session: {session_file}\n")

    # Configure root logger to capture everything
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if debug_session else level)
    root_logger.handlers = []
    for handler in handlers:
        root_logger.addHandler(handler)
        
    # Reduce verbosity of noisy libraries if not in detailed mode
    if not detailed_logging:
        logging.getLogger('httpcore').setLevel(logging.WARNING)
        logging.getLogger('httpx').setLevel(logging.WARNING)
        logging.getLogger('neo4j').setLevel(logging.INFO)
        logging.getLogger('pymilvus').setLevel(logging.INFO)
        logging.getLogger('_client').setLevel(logging.WARNING)
        logging.getLogger('_trace').setLevel(logging.WARNING)
        logging.getLogger('connectionpool').setLevel(logging.WARNING)
        logging.getLogger('SentenceTransformer').setLevel(logging.INFO)

def get_logger(name: str) -> logging.Logger:
    """Get a logger with the proper format."""
    return logging.getLogger(name)