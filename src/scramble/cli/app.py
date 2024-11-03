import sys
import os
import logging
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime

import click
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.logging import RichHandler
from rich.style import Style
from rich.text import Text
from rich.spinner import Spinner
from rich.live import Live
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

# Import our core components
from scramble.core.compressor import SemanticCompressor
from scramble.core.store import ContextStore
from scramble.core.api import AnthropicClient


# Set up rich console with enhanced settings
console = Console(highlight=True)

# Configure logging with custom rich handler
logging.basicConfig(
    level=logging.INFO,  # Changed from DEBUG to INFO
    format="%(message)s",
    handlers=[
        RichHandler(
            rich_tracebacks=True,
            show_time=False,
            show_path=False,
            markup=True
        )
    ]
)

logger = logging.getLogger(__name__)

class ScrambleCLI:
    def __init__(self):
        self._setup_styles()
        logger.debug("Initializing ScrambleCLI")
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True
        ) as progress:
            progress.add_task("Initializing compressor...", total=None)
            self.compressor = SemanticCompressor()
            
            progress.add_task("Loading context store...", total=None)
            self.store = ContextStore()
            
            progress.add_task("Connecting to Claude...", total=None)
            self.client = AnthropicClient(
                api_key=os.getenv('ANTHROPIC_API_KEY'),
                compressor=self.compressor
            )
        
    def _setup_styles(self):
        """Configure custom styles"""
        self.styles = {
            'prompt': Style(color="blue", bold=True),
            'user': Style(color="green"),
            'assistant': Style(color="cyan", bold=True),
            'debug': Style(color="grey70", italic=True),
            'error': Style(color="red", bold=True),
            'highlight': Style(color="magenta"),
        }
        
    def start_interactive(self):
        """Start interactive chat session."""
        # Show fancy welcome message
        welcome_text = Text()
        welcome_text.append("🧠 ", style="bold blue")
        welcome_text.append("ramble", style="bold blue")
        welcome_text.append(" v0.1.0\n", style="blue")
        welcome_text.append("Semantic Compression Active", style="dim")
        
        console.print(Panel(
            welcome_text,
            border_style="blue",
            title="Welcome",
            subtitle="Type :h for help"
        ))
        
        # Show context stats in a mini table
        contexts = self.store.list()
        table = Table(show_header=False, box=None)
        table.add_row(
            Text("Contexts:", style="dim"),
            Text(str(len(contexts)), style="bold blue")
        )
        console.print(table)
        console.print()
        
        while True:
            try:
                # Enhanced prompt with timestamp and arrow
                timestamp = datetime.now().strftime("%H:%M")
                prompt = Text()
                prompt.append(f"[{timestamp}]", style=self.styles['prompt'])
                prompt.append(" → ", style="bold blue")
                
                user_input = click.prompt(str(prompt), prompt_suffix="", show_default=False)

                if user_input.lower() in ['exit', 'quit', ':q']:
                    console.print("\n✨ Goodbye!\n", style="bold blue")
                    break
                
                if user_input.startswith(':'):
                    self._handle_command(user_input[1:])
                    continue
                
                # Show user message with style
                console.print(Text("\n You:", style=self.styles['user']))
                console.print(Text(user_input, style="green dim"))
                
                # Show spinner while waiting for response
                with console.status("[bold blue]Claude is thinking...", spinner="dots"):
                    result = self.client.send_message(user_input)
                
                # Show Claude's response with enhanced formatting
                console.print("\n[bold cyan]Claude:[/bold cyan]")
                console.print(Markdown(result['response']))
                
                # Show compression stats in a subtle way if debug mode
                if logger.level == logging.DEBUG:
                    usage = result['usage']
                    stats = Table(show_header=False, box=None)
                    stats.add_row(
                        Text("Tokens:", style="dim"),
                        Text(f"in: {usage['input_tokens']}", style="blue dim"),
                        Text(f"out: {usage['output_tokens']}", style="blue dim")
                    )
                    console.print(stats)
                
                console.print()  # Extra line for readability
                
            except KeyboardInterrupt:
                console.print("\n✨ Goodbye!\n", style="bold blue")
                break
            except Exception as e:
                logger.exception("Error in interactive session")
                console.print(Panel(
                    str(e),
                    title="Error",
                    border_style="red",
                    title_align="left"
                ))

    def _handle_command(self, cmd: str):
        """Handle special CLI commands."""
        cmd = cmd.strip()
        
        if cmd in ['h', 'help']:
            self._show_help()
        elif cmd in ['s', 'stats']:
            self._show_stats()
        elif cmd in ['c', 'contexts']:
            self._show_contexts()
        elif cmd.startswith('d'):
            self._toggle_debug(cmd)
        else:
            console.print(Panel(
                "Type :h for available commands",
                title="Unknown Command",
                border_style="yellow"
            ))

    def _show_help(self):
        """Show help message."""
        table = Table(show_header=False, title="Available Commands", border_style="blue")
        table.add_column("Command", style="cyan")
        table.add_column("Description")
        
        table.add_row(":h, :help", "Show this help message")
        table.add_row(":s, :stats", "Show system statistics")
        table.add_row(":c, :contexts", "Show stored contexts")
        table.add_row(":d", "Toggle debug mode")
        table.add_row(":q, :quit", "Exit the program")
        
        console.print(table)

    def _show_stats(self):
        """Show system statistics."""
        contexts = self.store.list()
        total_chunks = sum(c.size for c in contexts)
        
        table = Table(title="System Statistics", border_style="blue")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", justify="right")
        
        table.add_row("Total Contexts", str(len(contexts)))
        table.add_row("Total Chunks", str(total_chunks))
        table.add_row(
            "Debug Mode",
            "On ✓" if logger.level == logging.DEBUG else "Off ✗"
        )
        
        console.print(table)

    def _show_contexts(self):
        """Show stored contexts."""
        contexts = self.store.list()
        if not contexts:
            console.print(Panel("No stored contexts found", border_style="yellow"))
            return
        
        table = Table(title="Recent Contexts", border_style="blue")
        table.add_column("ID", style="dim")
        table.add_column("Chunks", justify="right")
        table.add_column("Created", style="dim")
        
        for ctx in contexts[-5:]:  # Show last 5 contexts
            created = ctx.created_at.strftime("%H:%M:%S")
            table.add_row(
                ctx.id[:8],
                str(ctx.size),
                created
            )
            
        console.print(table)

    def _toggle_debug(self, cmd: str):
        """Toggle debug mode."""
        if cmd == 'd':
            new_level = logging.DEBUG if logger.level != logging.DEBUG else logging.INFO
            logger.setLevel(new_level)
            status = "enabled ✓" if new_level == logging.DEBUG else "disabled ✗"
            console.print(f"Debug mode {status}", style="bold blue")
        else:
            console.print("Invalid debug command", style="yellow")

@click.group(invoke_without_command=True)
@click.option('--debug', is_flag=True, help="Enable debug mode")
@click.pass_context
def cli(ctx, debug):
    """ramble - Semantic Compression for AI Dialogue"""
    if debug:
        logger.setLevel(logging.DEBUG)
    if ctx.invoked_subcommand is None:
        app = ScrambleCLI()
        app.start_interactive()

@cli.command()
def stats():
    """Show statistics about stored contexts"""
    app = ScrambleCLI()
    app._show_stats()

if __name__ == '__main__':
    cli()