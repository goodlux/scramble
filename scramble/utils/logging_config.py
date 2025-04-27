"""Logging configuration for Scramble."""
import logging
from typing import Optional
from rich.logging import RichHandler
from rich.console import Console

def configure_logging(console: Optional[Console] = None, level: str = "INFO", debug_session: bool = False):
    """Configure application-wide logging with reduced external library noise."""
    if console is None:
        console = Console()
    
    # Set up rich handler
    rich_handler = RichHandler(
        console=console,
        show_time=True,
        show_path=True,
        markup=True,
        rich_tracebacks=True,
        tracebacks_show_locals=debug_session,
    )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add rich handler to root logger
    root_logger.addHandler(rich_handler)
    
    # Reduce verbosity of noisy libraries
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('neo4j').setLevel(logging.INFO)
    logging.getLogger('pymilvus').setLevel(logging.INFO)
    logging.getLogger('_client').setLevel(logging.WARNING)
    logging.getLogger('_trace').setLevel(logging.WARNING)
    logging.getLogger('connectionpool').setLevel(logging.WARNING)
    logging.getLogger('SentenceTransformer').setLevel(logging.INFO)
    
    # Configure custom formatters for some loggers
    for logger_name in ['ms_milvus_store', 'ms_search']:
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)
        
    # Return the configured root logger
    return root_logger

class CompactFormatter(logging.Formatter):
    """Formatter that collapses repeated patterns and highlights key information."""
    
    def format(self, record):
        """Format log records, collapsing verbose patterns."""
        msg = super().format(record)
        
        # Collapse vector hit messages
        if "Hit " in msg and "distance=" in msg:
            return "[VECTOR HIT]"
            
        # Collapse milvus search messages
        if "Performing vector search with" in msg:
            return "[VECTOR SEARCH START]"
            
        # Highlight important context messages
        if "ENRICHED CONTEXT BEING SENT TO MODEL" in msg:
            return f"🔍 {msg}"
            
        return msg
