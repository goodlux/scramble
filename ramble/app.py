"""
Ramble - Context-aware CLI chat interface
"""

import asyncio
import sys
import click
from typing import Dict, TypedDict, Optional
from rich.console import Console
from scramble.interface.ramble_interface import RambleInterface
from scramble.utils.logging import setup_logging, get_logger

# Setup console and logger
console = Console()
logger = get_logger(__name__)

class AppConfig(TypedDict):
    """Main application configuration."""
    ui: Dict[str, str]
    model_name: str


# Default configuration
DEFAULT_CONFIG: AppConfig = {
    'ui': {
        'prompt_style': 'cyberpunk'
    },
    'model_name': 'granite'  # Changed to use simplified name
}


class RambleCLI:
    def __init__(self, config: AppConfig = DEFAULT_CONFIG):
        """Initialize the CLI with core components."""
        try:
            logger.debug("Initializing CLI components")
            self.config = DEFAULT_CONFIG.copy()
            if config:
                self.config.update(config)

            # Initialize new interface with config
            self.interface = RambleInterface()
            self.interface.set_model_name(self.config['model_name'])  # Using the setter
            
            logger.debug("CLI initialization complete")

        except Exception as e:
            logger.error(f"Failed to initialize CLI: {e}")
            raise

    async def start_interactive(self):
        """Start interactive chat session."""
        try:
            await self.interface.setup()  # Ensure setup runs first
            await self.interface.run()
        except Exception as e:
            logger.error(f"Error in interactive session: {e}")
            raise

@click.command()
def cli():
    """Ramble - Context-aware CLI chat interface"""
    try:
        setup_logging()  # Setup logging before any operations
        app = RambleCLI()
        asyncio.run(app.start_interactive())
    except Exception as e:
        console.print(f"[red]Failed to start Ramble: {e}[/red]")
        sys.exit(1)

if __name__ == '__main__':
    cli()
