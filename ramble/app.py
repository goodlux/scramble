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
@click.option('--no-magicscroll', is_flag=True, help='Disable MagicScroll functionality')
@click.option('--simulate', is_flag=True, help='Run in simulation mode (no real models)')
@click.option('--ci-mode', is_flag=True, help='Run in CI/testing mode')
def cli(no_magicscroll, simulate, ci_mode):
    """Ramble - Context-aware CLI chat interface"""
    try:
        import os
        
        # Set environment variable to disable MagicScroll
        if no_magicscroll:
            os.environ['DISABLE_MAGICSCROLL'] = '1'
            console.print("[yellow]MagicScroll functionality disabled[/yellow]")
            
        # Set simulation mode
        if simulate:
            os.environ['SIMULATE_MODELS'] = '1'
            console.print("[yellow]Running in simulation mode (no real models)[/yellow]")
            
        # Set CI mode
        if ci_mode:
            os.environ['CI_MODE'] = '1'
            console.print("[yellow]Running in CI/testing mode[/yellow]")
            
        # Set up better logging with timestamps
        setup_logging()
        console.print("[green]Starting Ramble...[/green]")
        
        console.print("[yellow]Initializing RambleCLI...[/yellow]")
        app = RambleCLI()
        console.print("[green]RambleCLI initialized, starting interactive session...[/green]")
        
        # Run with timeout protection
        console.print("[yellow]Starting interactive session...[/yellow]")
        try:
            asyncio.run(app.start_interactive())
        except EOFError:
            console.print("[yellow]Detected EOF (Ctrl+D), shutting down[/yellow]")
            sys.exit(0)
        except KeyboardInterrupt:
            console.print("[yellow]Detected keyboard interrupt (Ctrl+C), shutting down[/yellow]")
            sys.exit(0)
            
    except KeyboardInterrupt:
        console.print("[yellow]Ramble terminated by user[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]Failed to start Ramble: {e}[/red]")
        import traceback
        console.print(traceback.format_exc())
        sys.exit(1)

if __name__ == '__main__':
    cli()
