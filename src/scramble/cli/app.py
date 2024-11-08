"""
Scramble CLI Application

This module provides the command-line interface for the Scramble dialogue system,
handling user interaction, context management, and AI model communication.
"""

# Standard library imports
import sys
import os
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any, TypedDict

# Third-party imports
import click
import dateparser
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table
from rich.logging import RichHandler
from rich.text import Text
import pickle

# Local imports
try:
    from ..core.compressor import SemanticCompressor
    from ..core.store import ContextStore, ContextManager
    from ..core.api import AnthropicClient
    from ..core.context import Context
    from ..core.stats import global_stats
except ImportError:
    # Alternative import if running directly
    from scramble.core.compressor import SemanticCompressor
    from scramble.core.store import ContextStore, ContextManager
    from scramble.core.api import AnthropicClient
    from scramble.core.context import Context
    from scramble.core.stats import global_stats

# Custom exceptions
class ScrambleError(Exception):
    """Base exception class for Scramble-specific errors."""
    pass

class ConfigurationError(ScrambleError):
    """Raised when there's an issue with configuration."""
    pass

class ContextError(ScrambleError):
    """Raised when there's an issue with context management."""
    pass

# Type definitions
class ContextConfig(TypedDict):
    """Configuration settings for context management."""
    max_contexts: int  # Maximum number of contexts to maintain
    time_window_hours: int  # Time window for considering relevant contexts

class ScoringConfig(TypedDict):
    """Configuration settings for context scoring."""
    recency_weight: float  # Weight given to recency in scoring
    chain_bonus: float  # Bonus for contexts in the same conversation chain
    decay_days: int  # Number of days after which context relevance decays

class AppConfig(TypedDict):
    """Main application configuration."""
    context: ContextConfig
    scoring: ScoringConfig

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
    }
}

# Setup logging and console
console = Console(stderr=True, soft_wrap=True)

def setup_logging(console: Console) -> None:
    """
    Configure application logging with rich handler.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        handlers=[
            RichHandler(
                console=console,
                rich_tracebacks=True,
                show_time=False,
                show_path=False,
                markup=True
            )
        ]
    )

setup_logging(console)
logger = logging.getLogger(__name__)

# CLI commands
@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx: click.Context) -> None:
    """Scramble - Semantic Compression for AI Dialogue"""
    if ctx.invoked_subcommand is None:
        try:
            app = ScrambleCLI()
            app.start_interactive()
        except Exception as e:
            console.print(f"[red]Failed to start Scramble: {e}[/red]")
            sys.exit(1)

@cli.command()
@click.argument('context_id', required=False)
def inspect(context_id: Optional[str] = None):
    """Inspect context files and compare full/compressed versions."""
    app = ScrambleCLI()

    if context_id:
        # Look at specific context
        compressed_path = app.store.storage_path / f"{context_id}.ctx"
        full_path = app.store.storage_path.parent / 'full' / f"{context_id}.ctx"

        table = Table(title=f"Context Inspection: {context_id[:8]}")
        table.add_column("Version")
        table.add_column("Content")
        table.add_column("Metadata")

        if compressed_path.exists():
            with open(compressed_path, 'rb') as f:
                compressed = pickle.load(f)
                table.add_row(
                    "Compressed",
                    compressed.text_content[:200] + "...",
                    str(dict(compressed.metadata))
                )

        if full_path.exists():
            with open(full_path, 'rb') as f:
                full = pickle.load(f)
                table.add_row(
                    "Full",
                    full.text_content[:200] + "...",
                    str(dict(full.metadata))
                )

        console.print(table)

    else:
        # Show summary of all contexts
        table = Table(title="Context Files Overview")
        table.add_column("Context ID")
        table.add_column("Has Compressed")
        table.add_column("Has Full")
        table.add_column("Date")
        table.add_column("Size Diff")

        compressed_path = app.store.storage_path
        full_path = app.store.storage_path.parent / 'full'

        for ctx_file in compressed_path.glob('*.ctx'):
            ctx_id = ctx_file.stem
            full_file = full_path / f"{ctx_id}.ctx"

            with open(ctx_file, 'rb') as f:
                compressed = pickle.load(f)

            has_full = "✓" if full_file.exists() else "✗"
            has_compressed = "✓"
            date = compressed.created_at.strftime("%Y-%m-%d")

            if full_file.exists():
                with open(full_file, 'rb') as f:
                    full = pickle.load(f)
                size_diff = f"{len(compressed.text_content) / len(full.text_content):.2f}x"
            else:
                size_diff = "N/A"

            table.add_row(
                ctx_id[:8],
                has_compressed,
                has_full,
                date,
                size_diff
            )

        console.print(table)

@cli.command()
@click.option('--dry-run', is_flag=True, help='Show what would be done without making changes')
def recompress_full(dry_run: bool):
    """Recompress all full contexts using current compression settings."""
    store = ContextStore()
    compressor = SemanticCompressor()
    full_path = store.storage_path.parent / 'full'

    table = Table(title="Recompression Results")
    table.add_column("Context ID")
    table.add_column("Old Size")
    table.add_column("New Size")
    table.add_column("Improvement")

    for ctx_file in full_path.glob('*.ctx'):
        try:
            with open(ctx_file, 'rb') as f:
                full_ctx = pickle.load(f)

            # Get original compressed version for comparison
            old_compressed = store.contexts.get(full_ctx.id)
            old_size = sum(len(c['content']) for c in old_compressed.compressed_tokens) if old_compressed else 0

            # Create new compressed version
            new_compressed = compressor.compress(full_ctx.text_content, full_ctx.metadata)
            new_size = sum(len(c['content']) for c in new_compressed.compressed_tokens)

            improvement = ((old_size - new_size) / old_size * 100) if old_size > 0 else 0

            table.add_row(
                full_ctx.id[:8],
                str(old_size),
                str(new_size),
                f"{improvement:+.1f}%"
            )

            if not dry_run:
                store.add(new_compressed)

        except Exception as e:
            logger.error(f"Error processing {ctx_file}: {e}")

    console.print(table)


@cli.command()
def config() -> None:
    """Show current configuration settings."""
    app = ScrambleCLI()

    # Create a formatted table instead of raw dict string
    table = Table(title="Current Configuration")
    table.add_column("Section", style="cyan")
    table.add_column("Setting", style="blue")
    table.add_column("Value", style="green")

    # Add context settings
    for key, value in app.config['context'].items():
        table.add_row("context", key, str(value))

    # Add scoring settings
    for key, value in app.config['scoring'].items():
        table.add_row("scoring", key, str(value))

    console.print("\n")
    console.print(Panel.fit(table, title="Configuration"))

@cli.command()
@click.option('--hours', default=48, help='Stats from last N hours')
def detailed_stats(hours: int) -> None:
    """Show detailed statistics for the last N hours."""
    app = ScrambleCLI()
    app._show_stats()

@cli.command()
def recompress() -> None:
    """
    One-time recompression of all contexts.
    Warning: This is a potentially destructive operation.
    """
    store = ContextStore()
    compressor = SemanticCompressor()

    with console.status("[bold blue]Recompressing contexts...", spinner="dots"):
        for ctx in store.list():
            text = "\n".join(
                chunk['content'] if isinstance(chunk, dict) else str(chunk)
                for chunk in ctx.compressed_tokens
            )
            new_ctx = compressor.compress(text)
            store.add(new_ctx)
            console.print(
                f"Recompressed {ctx.id[:8]} "
                f"({new_ctx.metadata.get('compression_ratio', 0):.2f}x)"
            )

@cli.command()
def reindex() -> None:
    """Rebuild context index from stored files."""
    app = ScrambleCLI()

    with console.status("[bold blue]Reindexing contexts...", spinner="dots"):
        count = app.store.reindex()

    console.print(f"[green]Successfully reindexed {count} contexts[/green]")

    # Show reindex statistics
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
            f"{app.context_manager.store.get_date_range().__str__()}"
        )

    console.print(stats)

@cli.command()
def debug_contexts() -> None:
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

# Main CLI Class
class ScrambleCLI:

    def __init__(self, config: AppConfig = DEFAULT_CONFIG):
        """Initialize the CLI with core components."""
        try:
            logger.debug("Initializing CLI components")
            self.config = DEFAULT_CONFIG.copy()
            if config:
                self.config.update(config)

            self.compressor = SemanticCompressor()
            # Replace ContextStore with ContextManager
            self.context_manager = ContextManager()
            self.store = self.context_manager.store  # Keep for backward compatibility

            api_key = os.getenv('ANTHROPIC_API_KEY')
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY environment variable is required")

            self.client = AnthropicClient(
                api_key=api_key,
                compressor=self.compressor,
                context_manager=self.context_manager
            )
            logger.debug("CLI initialization complete")

        except Exception as e:
            logger.error(f"Failed to initialize CLI: {e}")
            raise

    def debug_context_dates(self):
        store = ContextStore()
        for ctx in store.list():
            print(f"Context {ctx.id[:8]}:")
            print(f"  timestamp: {ctx.metadata.get('timestamp')}")
            print(f"  created_at: {getattr(ctx, 'created_at', None)}")

    def _inspect_contexts(self, context_id: Optional[str] = None):
        """Inspect context files and compare full/compressed versions."""
        compressed_path = self.store.storage_path
        full_path = self.store.storage_path / 'full'

        if context_id:
            # Look at specific context
            compressed_file = compressed_path / f"{context_id}.ctx"
            full_file = full_path / f"{context_id}.ctx"

            table = Table(title=f"Context Inspection: {context_id[:8]}")
            table.add_column("Version", style="cyan")
            table.add_column("Content", style="green")
            table.add_column("Metadata", style="yellow")

            if not compressed_file.exists():
                console.print(f"[red]No compressed context found for ID: {context_id}[/red]")
                return

            with open(compressed_file, 'rb') as f:
                compressed = pickle.load(f)
                table.add_row(
                    "Compressed",
                    compressed.text_content[:200] + "...",
                    str(dict(compressed.metadata))
                )

            if full_file.exists():
                with open(full_file, 'rb') as f:
                    full = pickle.load(f)
                    table.add_row(
                        "Full",
                        full.text_content[:200] + "...",
                        str(dict(full.metadata))
                    )
            else:
                table.add_row(
                    "Full",
                    "[red]Not found[/red]",
                    f"Should be at: {full_file}"
                )

            console.print(table)

        else:
            # Show summary of all contexts
            table = Table(title="Context Files Overview")
            table.add_column("Context ID", style="cyan")
            table.add_column("Compressed File", style="green")
            table.add_column("Full File", style="yellow")
            table.add_column("Date/Time", style="blue")

            # Debug directory existence
            console.print(f"\n[cyan]Directory Check:[/cyan]")
            console.print(f"Compressed dir exists: {compressed_path.exists()} at {compressed_path}")
            console.print(f"Full dir exists: {full_path.exists()} at {full_path}\n")

            # Collect all contexts and sort by date
            contexts = []
            for ctx_file in compressed_path.glob('*.ctx'):
                ctx_id = ctx_file.stem
                full_file = full_path / f"{ctx_id}.ctx"

                with open(ctx_file, 'rb') as f:
                    compressed = pickle.load(f)

                compressed_status = "Found ✓" if ctx_file.exists() else "Missing ✗"
                full_status = "Found ✓" if full_file.exists() else "Missing ✗"

                contexts.append({
                    'id': ctx_id,
                    'date': compressed.created_at,
                    'compressed_status': compressed_status,
                    'compressed_file': ctx_file,
                    'full_status': full_status,
                    'full_file': full_file
                })

            # Sort by date
            contexts.sort(key=lambda x: x['date'])

            for ctx in contexts:
                table.add_row(
                    ctx['id'][:8],
                    f"{ctx['compressed_status']}\n{ctx['compressed_file'].name}",
                    f"{ctx['full_status']}\n{ctx['full_file'].name}",
                    ctx['date'].strftime("%Y-%m-%d %H:%M")
                )

            console.print(table)

    def _debug_context_selection(self, message: str):
        """Debug helper to show context selection process with availability status."""
        # Get all contexts first
        all_contexts = self.store.list()
        contexts = self.context_manager.process_message(message)  # This is correct

        table = Table(title=f"Context Selection for: {message}")
        table.add_column("Context ID", style="dim")
        table.add_column("Date", style="cyan")
        table.add_column("Final Score", justify="right")
        table.add_column("Semantic", justify="right")
        table.add_column("Tokens", justify="right")
        table.add_column("Available", style="green")
        table.add_column("Reason", style="blue")

        # Track cumulative tokens for availability calculation
        MAX_CONTEXT_TOKENS = 4000
        cumulative_tokens = 0

        for ctx in sorted(contexts, key=lambda x: x.metadata.get('scoring', {}).get('final_score', 0), reverse=True):
            scoring = ctx.metadata.get('scoring', {})

            # Calculate availability
            ctx_tokens = ctx.token_count
            would_fit = cumulative_tokens + ctx_tokens <= MAX_CONTEXT_TOKENS
            if scoring.get('final_score', 0) > 0.5:
                cumulative_tokens += ctx_tokens if would_fit else 0

            available = "✓" if would_fit else "✗"
            available_style = "green" if would_fit else "red"

            table.add_row(
                ctx.id[:8],
                ctx.created_at.strftime("%Y-%m-%d"),
                f"{scoring.get('final_score', 'N/A'):.3f}",
                f"{scoring.get('semantic_score', 'N/A'):.3f}",
                str(ctx_tokens),
                Text(available, style=available_style),
                ctx.metadata.get('selection_reason', 'unknown')
            )

        # Add summary information
        total_contexts = len(all_contexts)
        available_contexts = sum(1 for ctx in contexts if ctx.token_count + min(cumulative_tokens, MAX_CONTEXT_TOKENS) <= MAX_CONTEXT_TOKENS)

        summary = Table.grid(padding=1)
        summary.add_row(f"[cyan]Total contexts searched:[/cyan] {total_contexts}")
        summary.add_row(f"[cyan]Contexts scored:[/cyan] {len(contexts)}")
        summary.add_row(f"[cyan]Contexts available to Claude:[/cyan] {available_contexts}")
        summary.add_row(f"[cyan]Total tokens used:[/cyan] {min(cumulative_tokens, MAX_CONTEXT_TOKENS)}/{MAX_CONTEXT_TOKENS}")

        console.print(summary)
        console.print(table)
        # Add summary information
        total_contexts = len(all_contexts)
        available_contexts = sum(1 for ctx in contexts if ctx.token_count + min(cumulative_tokens, MAX_CONTEXT_TOKENS) <= MAX_CONTEXT_TOKENS)

        summary = Table.grid(padding=1)
        summary.add_row(f"[cyan]Total contexts searched:[/cyan] {total_contexts}")
        summary.add_row(f"[cyan]Contexts scored:[/cyan] {len(contexts)}")
        summary.add_row(f"[cyan]Contexts available to Claude:[/cyan] {available_contexts}")
        summary.add_row(f"[cyan]Total tokens used:[/cyan] {min(cumulative_tokens, MAX_CONTEXT_TOKENS)}/{MAX_CONTEXT_TOKENS}")

        console.print(summary)
        console.print(table)

    def _debug_context_dates(self):
        """Debug helper to show all context dates."""
        table = Table(title="Context Dates Debug")
        table.add_column("Context ID", style="dim")
        table.add_column("Timestamp")
        table.add_column("Created At")
        table.add_column("Source")

        for ctx in self.store.list():
            timestamp = ctx.metadata.get('timestamp', 'None')
            created_at = getattr(ctx, 'created_at', 'None')
            source = "metadata" if 'timestamp' in ctx.metadata else "created_at" if hasattr(ctx, 'created_at') else "missing"

            table.add_row(
                ctx.id[:8],
                str(timestamp),
                str(created_at),
                source
            )

        console.print(table)

    def process_message(self, message: str, use_all_contexts: bool = False) -> List[Context]:
        """Process message and select relevant contexts."""
        candidates = []

        # Check for temporal references
        if dateparser.parse(message):
            # Use context_manager instead of direct method call
            historical = self.context_manager.find_contexts_by_timeframe(message)
            candidates.extend(historical)

        if use_all_contexts:
            # Use all available contexts
            all_contexts = self.store.list()
            similar = self.compressor.find_similar(message, all_contexts, top_k=10)
            candidates.extend([ctx for ctx, _, _ in similar])
        else:
            # Normal operation with time window
            recent = self.store.get_recent_contexts(hours=168)
            candidates.extend(recent)

            # Check for historical reference keywords
            if any(word in message.lower() for word in ['previous', 'before', 'earlier', 'last time', 'recall']):
                all_contexts = self.store.list()
                similar = self.compressor.find_similar(message, all_contexts, top_k=5)
                candidates.extend([ctx for ctx, _, _ in similar])

        # Use context_manager instead of direct method call
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
                chain = self.context_manager.get_conversation_chain(
                    self.client.current_context.id
                )

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
        table.add_row(":inspect [id]", "Inspect context files (optional: specific context ID)")
        table.add_row(":s, :stats", "Show system statistics")
        table.add_row(":c, :contexts", "Show stored contexts")
        table.add_row(":dates", "Debug context dates")
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
            elif command == 'test':
                if not args:
                    console.print("[yellow]Usage: :test <message>[/yellow]")
                else:
                    self._debug_context_selection(args)
            elif command == 'inspect':  # Add this section
                self._inspect_contexts(args if args else None)
            elif command in ['c', 'contexts']:
                self._show_contexts()
            elif command in ['a', 'analysis']:
                self._show_compression_analysis()
            elif command == 'dates':  # Add this new command
                self._debug_context_dates()
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
                timestamp = datetime.now().strftime("%H:%M")
                user_input = click.prompt(
                    f'[{timestamp}]',
                    prompt_suffix=' > ',
                    show_default=False
                )

                if user_input.lower() in ['exit', 'quit', ':q']:
                    console.print("\n[dim]Goodbye! Contexts saved.[/dim]")
                    break

                if user_input.startswith(':'):
                    self._handle_command(user_input[1:])
                    continue

                # Add logging here
                logger.debug("Processing message...")

                with console.status("[bold blue]Thinking...", spinner="dots"):
                    # Log each step
                    logger.debug("Getting contexts...")
                    contexts = self.process_message(user_input)
                    logger.debug(f"Found {len(contexts)} relevant contexts")

                    logger.debug("Sending to Claude...")
                    result = self.client.send_message(
                        message=user_input,
                        contexts=contexts
                    )
                    logger.debug("Got response from Claude")

                    # Store new context with chain linking
                    if self.client.current_context:
                        logger.debug("Storing new context...")
                        result['context'].metadata['parent_context'] = \
                            self.client.current_context.id
                        self.store.add(result['context'])
                        logger.debug("Context stored")

                    # Show response
                    console.print("\n[bold cyan]Claude:[/bold cyan]")
                    console.print(Markdown(result['response']))

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

# Main guard
if __name__ == '__main__':
    cli()
