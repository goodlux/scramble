"""
Ramble - Context-aware CLI chat interface
Built on the Scramble semantic compression system.
"""

import sys
import os
import click
from datetime import datetime
from typing import Optional, Dict, Any, TypedDict

from scramble.core.compressor import SemanticCompressor
from scramble.core.store import  ContextManager
from scramble.core.api import AnthropicClient

from .ui.console import console, logger, setup_logging
from .ui.welcome import show_welcome
from .handlers.commands import CommandHandler
from .handlers.messages import MessageHandler
from .commands.inspect import inspect
from .commands.reindex import reindex
from .commands.stats import detailed_stats
from .commands.config import config

from .ui.console import console, logger, setup_logging, prompt_user  # Add prompt_user here
from .ui.welcome import show_welcome
from .handlers.commands import CommandHandler
from .handlers.messages import MessageHandler

from textual.widgets import Static

from rich.console import Console, RenderableType
from rich.markdown import Markdown

# Type definitions
class ContextConfig(TypedDict):
    """Configuration settings for context management."""
    max_contexts: int
    time_window_hours: int

class ScoringConfig(TypedDict):
    """Configuration settings for context scoring."""
    recency_weight: float
    chain_bonus: float
    decay_days: int

class AppConfig(TypedDict):
    """Main application configuration."""
    context: ContextConfig
    scoring: ScoringConfig
    ui: Dict[str, str]

# Default configuration
DEFAULT_CONFIG: AppConfig = {
    'context': {
        'max_contexts': 40,
        'time_window_hours': 200,
    },
    'scoring': {
        'recency_weight': 0.05,
        'chain_bonus': 0.4,
        'decay_days': 7,
    },
    'ui': {
        'prompt_style': 'cyberpunk'  # Set default style here
    }
}

# Setup logging
setup_logging(console)



class RambleCLI:
    def __init__(self, config: AppConfig = DEFAULT_CONFIG):
        """Initialize the CLI with core components."""
        try:
            logger.debug("Initializing CLI components")
            self.config = DEFAULT_CONFIG.copy()
            if config:
                self.config.update(config)

            self.compressor = SemanticCompressor()
            self.context_manager = ContextManager()
            self.store = self.context_manager.store

            api_key = os.getenv('ANTHROPIC_API_KEY')
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY environment variable is required")

            self.client = AnthropicClient(
                api_key=api_key,
                compressor=self.compressor,
                context_manager=self.context_manager
            )

            self.command_handler = CommandHandler(self)
            self.message_handler = MessageHandler(self)
            
            self._output_handler = None
            self._display = None  # Add this for RambleDisplay
            
            logger.debug("CLI initialization complete")

        except Exception as e:
            logger.error(f"Failed to initialize CLI: {e}")
            raise

    def set_display(self, display: 'RambleDisplay'):
        """Set the display component."""
        self._display = display
        # If using RambleDisplay, it handles its own output
        if display:
            self._output_handler = display.handle_output

    def set_output_handler(self, handler):
        """Set raw output handler (for RambleMAXX)."""
        if not self._display:  # Only set if not using RambleDisplay
            self._output_handler = handler

    async def display(self, content):
        """Display content through handler."""
        if self._output_handler:
            await self._output_handler(content)
        else:
            console.print(content)

    async def start_interactive(self):
        """Start interactive chat session."""
        await self.display("Welcome to Ramble!")

        while True:
            try:
                # Display prompt
                await self.display(f"[{datetime.now().strftime('%H:%M')}] > ")
                
                user_input = prompt_user(
                    prompt_style=self.config['ui']['prompt_style']
                )

                if user_input.lower() in ['exit', 'quit', ':q']:
                    await self.display("\n[dim]Goodbye! Contexts saved.[/dim]")
                    break

                if user_input.startswith(':'):
                    self.command_handler.handle_command(user_input[1:])
                    continue

                await self.message_handler.handle_message(user_input)

            except KeyboardInterrupt:
                await self.display("\n[dim]Goodbye! Contexts saved.[/dim]")
                break
            except Exception as e:
                logger.exception("Error in interactive session")
                await self.display(f"[red]Error: {e}[/red]")
        

class RambleDisplay(Static):
    """Display for the Ramble interface."""
    
    def __init__(self, ramble: RambleCLI, **kwargs):
        super().__init__("", **kwargs)
        self.ramble = ramble
        self.console = Console()
        
    def on_mount(self) -> None:
        """Set up Ramble output capture."""
        self.ramble.set_output_handler(self.handle_output)
        
    async def handle_output(self, content: RenderableType) -> None:
        """Handle output from Ramble."""
        # Capture Ramble's output and display it
        with self.console.capture() as capture:
            self.console.print(content)
        self.update(capture.get())



@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx: click.Context) -> None:
    """Ramble - Context-aware CLI chat interface"""
    if ctx.invoked_subcommand is None:
        try:
            import asyncio
            app = RambleCLI()
            asyncio.run(app.start_interactive())  # Run the async function
        except Exception as e:
            console.print(f"[red]Failed to start Ramble: {e}[/red]")
            sys.exit(1)

# Add commands to cli group
cli.add_command(inspect)
cli.add_command(reindex)
cli.add_command(detailed_stats)
cli.add_command(config)

if __name__ == '__main__':
    cli()

