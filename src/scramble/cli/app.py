# 1. Imports and setup
import sys
import os
import logging
import dateparser
from datetime import datetime
from typing import List, Optional, Dict, Any, TypedDict

import click
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table
from rich.logging import RichHandler

from scramble.core.store import ContextManager

from ..core.stats import global_stats

# Fix imports by using relative imports from parent package
try:
    from ..core.compressor import SemanticCompressor
    from ..core.store import ContextStore, ContextManager
    from ..core.api import AnthropicClient
    from ..core.context import Context

except ImportError:
    # Alternative import if running directly
    from scramble.core.compressor import SemanticCompressor
    from scramble.core.store import ContextStore
    from scramble.core.api import AnthropicClient
    from scramble.core.context import Context

class ContextConfig(TypedDict):
    max_contexts: int
    time_window_hours: int

class ScoringConfig(TypedDict):
    recency_weight: float
    chain_bonus: float
    decay_days: int

class AppConfig(TypedDict):
    context: ContextConfig
    scoring: ScoringConfig

DEFAULT_CONFIG: AppConfig = {
    'context': {
        'max_contexts': 40,
        'time_window_hours': 108,
    },
    'scoring': {
        'recency_weight': 0.05,
        'chain_bonus': 0.4,
        'decay_days': 7,
    }
}


# Set up rich console with proper error handling
console = Console(stderr=True)

# Configure logging with rich handler
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[
        RichHandler(
            console=console,
            rich_tracebacks=True,
            show_time=False,
            show_path=False
        )
    ]
)
logger = logging.getLogger(__name__)

# 2. CLI group definition
@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """ramble - Semantic Compression for AI Dialogue"""
    if ctx.invoked_subcommand is None:
        try:
            app = ScrambleCLI()
            app.start_interactive()
        except Exception as e:
            console.print(f"[red]Failed to start ramble: {e}[/red]")
            sys.exit(1)

# 3. CLI Commands
@cli.command()
@click.option('--hours', default=48, help='Stats from last N hours')

def config():
    """Show current configuration"""
    app = ScrambleCLI()
    console.print(Panel(str(app.config), title="Current Config"))

def detailed_stats(hours):
    """Show detailed compression and token usage statistics."""
    app = ScrambleCLI()
    app._show_stats()  # Will show the enhanced stats

@cli.command()
def recompress():
    ## here be dragons, this didn't work last time I tried, might be irrelevant now
    """One-time recompression of all contexts"""
    store = ContextStore()
    compressor = SemanticCompressor()

    for ctx in store.list():
        text = "\n".join(chunk['content'] if isinstance(chunk, dict) else str(chunk) for chunk in ctx.compressed_tokens)
        new_ctx = compressor.compress(text)
        store.add(new_ctx)
        print(f"Recompressed {ctx.id[:8]} ({new_ctx.metadata.get('compression_ratio', 0):.2f}x)")

@cli.command()
def reindex():
    """Rebuild context index from stored files."""
    app = ScrambleCLI()

    with console.status("[bold blue]Reindexing contexts...", spinner="dots"):
        count = app.store.reindex()

    console.print(f"[green]Successfully reindexed {count} contexts[/green]")

    # Show stats after reindex
    stats = Table(title="Reindex Results")
    stats.add_column("Metric", style="cyan")
    stats.add_column("Value", justify="right")

    stats.add_row("Total Contexts", str(count))
    stats.add_row(
        "Context Chains",
        str(len(app.store.metadata.get('chains', [])))
    )
    stats.add_row(
        "Date Range",
        f"{app.store.get_date_range_str()}"  # You'll need to add this method
    )

    console.print(stats)

@cli.command()
def debug_contexts():
    """Show detailed information about stored contexts."""
    app = ScrambleCLI()
    contexts = app.store.list()

    table = Table(title="Context Debug Info")
    table.add_column("ID", style="dim")
    table.add_column("Timestamp")
    table.add_column("Size")
    table.add_column("Compression")

    for ctx in contexts:
        table.add_row(
            ctx.id[:8],
            ctx.metadata.get('timestamp', 'unknown'),
            str(ctx.size),
            f"{ctx.metadata.get('compression_ratio', 0):.2f}x"
        )

    console.print(table)

# 4. Main CLI Class
class ScrambleCLI:
    def __init__(self, config: AppConfig = DEFAULT_CONFIG):

        self.context_manager = ContextManager()


        """Initialize the CLI with core components."""
        try:
            logger.debug("Initializing CLI components")

            self.config = DEFAULT_CONFIG.copy()
            if config:
                self.config.update(config)

            self.compressor = SemanticCompressor()
            self.store = ContextStore()

            api_key = os.getenv('ANTHROPIC_API_KEY')
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY environment variable is required")

            self.client = AnthropicClient(
                api_key=api_key,
                compressor=self.compressor
            )
            logger.debug("CLI initialization complete")

        except Exception as e:
            logger.error(f"Failed to initialize CLI: {e}")
            raise

    def process_message(self, message: str) -> List[Context]:
        """Process message and select relevant contexts."""
        candidates = []

        # Check for temporal references
        if potential_timeframe := dateparser.parse(message):
            historical = self.context_manager.find_contexts_by_timeframe(message)
            candidates.extend(historical)

        # Get recent contexts
        recent = self.store.get_recent_contexts(hours=48)
        candidates.extend(recent)


        # If we have current context, follow its chain
        if self.client.current_context:
            chain = self.context_manager.get_conversation_chain(
                self.client.current_context.id
            )
            candidates.extend(chain)

        # Select within token budget
        return self.context_manager.select_contexts(message, candidates)

    def _show_welcome(self):
        """Show enhanced welcome message with context stats."""
        try:
            summary = self.store.get_conversation_summary()

            grid = Table.grid(padding=1)
            grid.add_row(
                Panel(
                    "[bold blue]🧠 ramble v0.1.0[/bold blue]\n"
                    "[dim]Semantic Compression Active[/dim]",
                    border_style="blue"
                )
            )

            if summary['total_conversations'] > 0:
                stats = Table.grid(padding=1)
                last_seen = summary['last_interaction'].strftime('%Y-%m-%d %H:%M')
                stats.add_row(f"[blue]Last Conversation:[/blue] {last_seen}")
                stats.add_row(
                    f"[cyan]Total Conversations:[/cyan] {summary['total_conversations']}"
                )
                stats.add_row(
                    f"[green]Recent Contexts:[/green] {summary['recent_contexts']}"
                )
                stats.add_row(
                    f"[yellow]Active Chains:[/yellow] {summary['conversation_chains']}"
                )
                grid.add_row(Panel(stats, border_style="blue"))
            else:
                grid.add_row(
                    Panel(
                        "[cyan]Welcome to your first conversation![/cyan]\n"
                        "[dim]Your context history will be saved here.[/dim]",
                        border_style="blue"
                    )
                )

            console.print(grid)

        except Exception as e:
            logger.error(f"Error showing welcome message: {e}")
            console.print(Panel(str(e), title="Error", border_style="red"))

    def _get_relevant_contexts(self) -> List[Context]:
        """Get relevant contexts for current conversation."""
        try:
            contexts = []
            max_contexts = self.config['context']['max_contexts']

            # Start with chain contexts if we have current context
            if self.client.current_context:
                chain = self.store.get_conversation_chain(
                    self.client.current_context.id,
                )
                contexts.extend(chain)

            # Get recent contexts, leaving room for semantic matches
            remaining = max_contexts - len(contexts)
            if remaining > 0:
                recent = self.store.get_recent_contexts(
                    hours=self.config['context']['time_window_hours'],
                    limit=remaining
                )
                contexts.extend(recent)

            # Remove duplicates while preserving order
            seen = set()
            unique_contexts = []
            for ctx in contexts:
                if ctx.id not in seen:
                    seen.add(ctx.id)
                    unique_contexts.append(ctx)

            return unique_contexts

        except Exception as e:
            logger.error(f"Error getting relevant contexts: {e}")
            return []

    def _show_help(self):
        """Show help message."""
        table = Table(title="Available Commands")
        table.add_column("Command", style="cyan")
        table.add_column("Description")

        table.add_row(":h, :help", "Show this help message")
        table.add_row(":s, :stats", "Show system statistics")
        table.add_row(":c, :contexts", "Show stored contexts")
        table.add_row(":a  :analysis", "Show detailed compression analysis")  # Add this line
        table.add_row(":d", "Toggle debug mode")
        table.add_row(":sim <query>", "Test similarity scoring against all contexts")
        table.add_row(":q, :quit", "Exit the program")

        console.print(table)


    def _show_stats(self):
        """Show enhanced system statistics."""
        try:
            # Get conversation summary
            summary = self.store.get_conversation_summary()

            # Get compression and token stats
            stats_table = global_stats.generate_stats_table(hours=24)  # Last 24h

            # Show stats
            console.print("\n[bold]System Statistics[/bold]")
            console.print(stats_table)

            # Show conversation summary
            console.print("\n[bold]Conversation Summary[/bold]")
            summary_table = Table()
            summary_table.add_row("Total Conversations", str(summary['total_conversations']))
            summary_table.add_row("Recent Contexts", str(summary['recent_contexts']))
            summary_table.add_row("Active Chains", str(summary['conversation_chains']))
            console.print(summary_table)

        except Exception as e:
            logger.error(f"Error showing stats: {e}")
            console.print("[red]Failed to load statistics[/red]")

    def _show_contexts(self):
        """Show stored contexts with semantic chunks."""
        try:
            contexts = self.store.get_recent_contexts(hours=48)

            if not contexts:
                console.print(Panel("No recent contexts found", border_style="yellow"))
                return

            # Create main table
            table = Table(
                title="Recent Contexts",
                show_header=True,
                header_style="bold blue",
                border_style="blue"
            )
            table.add_column("ID", style="dim", width=10)
            table.add_column("Chunks", justify="right", width=8)
            table.add_column("Chain", style="cyan", width=10)
            table.add_column("Content Preview", style="green")

            for ctx in contexts:
                # Get a preview of the context content
                preview = ""
                if ctx.compressed_tokens:
                    chunk = ctx.compressed_tokens[0]
                    if isinstance(chunk, dict):
                        preview = chunk.get('content', '')[:50]
                    else:
                        preview = str(chunk)[:50]
                    if len(preview) == 50:
                        preview += "..."

                # Show chain relationship
                chain_indicator = ""
                if ctx.metadata.get('parent_context'):
                    parent_id = ctx.metadata['parent_context'][:8]
                    chain_indicator = f"← {parent_id}"

                table.add_row(
                    ctx.id[:8],
                    str(len(ctx.compressed_tokens)),
                    chain_indicator,
                    preview
                )

            # Add metadata panel
            summary = self.store.get_conversation_summary()
            metadata = Table.grid(padding=1)
            metadata.add_row(
                f"[blue]Total Contexts:[/blue] {summary['total_conversations']}",
                f"[cyan]Active Chains:[/cyan] {summary['conversation_chains']}",
                f"[green]Recent Activity:[/green] {summary['recent_contexts']} contexts in 24h"
            )

            # Show everything in a nice layout
            console.print(Panel(metadata, border_style="blue"))
            console.print(table)
            console.print()

        except Exception as e:
            logger.error(f"Error showing contexts: {e}")
            console.print(Panel(str(e), title="Error", border_style="red"))

    def _toggle_debug(self, cmd: str):
        """Toggle debug mode."""
        try:
            if cmd == 'd':
                current = logger.getEffectiveLevel()
                new_level = logging.DEBUG if current != logging.DEBUG else logging.INFO
                logger.setLevel(new_level)
                status = "enabled ✓" if new_level == logging.DEBUG else "disabled ✗"
                console.print(f"[blue]Debug mode {status}[/blue]")
            else:
                console.print("[yellow]Invalid debug command[/yellow]")
        except Exception as e:
            logger.error(f"Error toggling debug mode: {e}")

    def _handle_command(self, cmd: str) -> None:
        """Handle CLI commands."""
        try:
            # Split command and args
            parts = cmd.strip().split(maxsplit=1)
            command = parts[0]
            args = parts[1] if len(parts) > 1 else ""

            if command in ['h', 'help']:
                self._show_help()
            elif command in ['s', 'stats']:
                self._show_stats()
            elif command in ['c', 'contexts']:
                self._show_contexts()
            elif command in ['a', 'analysis']:
                self._show_compression_analysis()
            elif command.startswith('d'):
                self._toggle_debug(command)
            elif command == 'sim':  # New command
                if not args:
                    console.print("[yellow]Usage: :sim <query text>[/yellow]")
                else:
                    self._show_similarity_debug(args)
            else:
                console.print("[yellow]Unknown command. Type :h for help.[/yellow]")

        except Exception as e:
            logger.error(f"Error handling command '{cmd}': {e}")
            console.print("[red]Failed to execute command[/red]")

    def _show_similarity_debug(self, query: str):
        """Show similarity scores for all contexts."""
        try:
            contexts = self.store.list()
            results = self.compressor.find_similar(query, contexts)

            table = Table(title=f"Similarity Scores for: {query}")
            table.add_column("Context ID")
            table.add_column("Final Score")
            table.add_column("Semantic")
            table.add_column("Recency")
            table.add_column("Chain")

            for context, score, details in results:
                table.add_row(
                    context.id[:8],
                    f"{score:.3f}",
                    f"{details['semantic_score']:.3f}",
                    f"{details['recency_score']:.3f}",
                    f"{details['chain_bonus']:.1f}"
                )

            console.print(table)
        except Exception as e:
            logger.error(f"Debug error: {e}")

    def _show_compression_analysis(self):
        """Show detailed compression analysis."""
        try:
            # Get stats for different time periods
            last_hour = global_stats.get_compression_summary(hours=1)
            last_day = global_stats.get_compression_summary(hours=24)
            all_time = global_stats.get_compression_summary()

            # Create analysis table
            table = Table(title="Compression Analysis")
            table.add_column("Timeframe")
            table.add_column("Compression")
            table.add_column("Similarity")
            table.add_column("Tokens Saved")

            def add_stats_row(timeframe: str, stats: Dict):
                if not stats:
                    return
                comp_stats = stats['compression_stats']
                sim_stats = stats['similarity_stats']
                table.add_row(
                    timeframe,
                    f"{comp_stats['avg_ratio']:.2f}x",
                    f"{sim_stats['avg_similarity']:.2%}",
                    f"{comp_stats['tokens_saved']:,}"
                )

            add_stats_row("Last Hour", last_hour)
            add_stats_row("Last 24h", last_day)
            add_stats_row("All Time", all_time)

            console.print(table)

            # Show token usage summary
            token_stats = global_stats.get_token_usage_summary(hours=24)
            if token_stats:
                usage_table = Table(title="Token Usage (Last 24h)")
                usage_table.add_row(
                    "Total Tokens", f"{token_stats['total_tokens']:,}"
                )
                usage_table.add_row(
                    "Avg per Turn", f"{token_stats['avg_tokens_per_turn']:.0f}"
                )
                console.print("\n")
                console.print(usage_table)

        except Exception as e:
            logger.error(f"Error showing compression analysis: {e}")
            console.print("[red]Failed to generate analysis[/red]")


    def start_interactive(self):
        """Start interactive chat session."""
        self._show_welcome()

        while True:
            try:
                # Get timestamp for prompt
                timestamp = datetime.now().strftime("%H:%M")
                user_input = click.prompt(
                    f'[{timestamp}]',
                    prompt_suffix=' > ',
                    show_default=False
                )

                if user_input.lower() in ['exit', 'quit', ':q']:
                    console.print("\n[dim]Goodbye! Contexts saved.[/dim]")
                    break

                # Handle special commands
                if user_input.startswith(':'):
                    self._handle_command(user_input[1:])
                    continue

                # Process message and get response
                with console.status("[bold blue]Thinking...", spinner="dots"):
                    # Get contexts using process_message
                    contexts = self.process_message(user_input)

                    # Send message to Claude
                    result = self.client.send_message(
                        message=user_input,
                        contexts=contexts
                    )

                    # Record stats
                    global_stats.record_token_usage(
                        input_tokens=result['usage']['input_tokens'],
                        output_tokens=result['usage']['output_tokens'],
                        context_tokens=result['usage'].get('context_tokens', 0)
                    )

                    # Store new context with chain linking
                    if self.client.current_context:
                        result['context'].metadata['parent_context'] = \
                            self.client.current_context.id
                    self.store.add(result['context'])

                    # Show response
                    console.print("\n[bold cyan]Claude:[/bold cyan]")
                    console.print(Markdown(result['response']))

                    # Show debug info if enabled
                    if logger.level == logging.DEBUG:
                        usage = result['usage']
                        stats = Table.grid()
                        stats.add_row(
                            "[dim]Tokens:[/dim]",
                            f"[blue dim]in: {usage['input_tokens']}[/blue dim]",
                            f"[blue dim]out: {usage['output_tokens']}[/blue dim]"
                        )
                        if contexts:  # Changed from all_contexts to contexts
                            stats.add_row(
                                "[dim]Contexts:[/dim]",
                                f"[blue dim]{len(contexts)} used[/blue dim]"  # Changed from all_contexts to contexts
                            )
                        console.print(stats)

                    console.print()

            except KeyboardInterrupt:
                console.print("\n[dim]Goodbye! Contexts saved.[/dim]")
                break

            except Exception as e:
                logger.exception("Error in interactive session")
                console.print(Panel(
                    str(e),
                    title="Error",
                    border_style="red"
                ))

# 5. Main guard
if __name__ == '__main__':
    cli()
