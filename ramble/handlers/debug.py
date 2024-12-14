import logging
from typing import Optional
from rich.table import Table
from rich.text import Text
from ..ui.console import console, logger

def toggle_debug(cmd: str):
    """Toggle debug mode."""
    try:
        current = logger.getEffectiveLevel()
        new_level = logging.DEBUG if current != logging.DEBUG else logging.INFO
        logger.setLevel(new_level)
        status = "enabled ✓" if new_level == logging.DEBUG else "disabled ✗"
        console.print(f"[blue]Debug mode {status}[/blue]")
    except Exception as e:
        logger.error(f"Error toggling debug mode: {e}")

def show_context_dates(cli):
    """Debug helper to show all context dates."""
    table = Table(title="Context Dates Debug")
    table.add_column("Context ID", style="dim")
    table.add_column("Timestamp")
    table.add_column("Created At")
    table.add_column("Source")

    for ctx in cli.store.list():
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

def show_context_selection(cli, message: str):
    """Debug helper to show context selection process."""
    all_contexts = cli.store.list()
    contexts = cli.context_manager.process_message(message)

    table = Table(title=f"Context Selection for: {message}")
    table.add_column("Context ID", style="dim")
    table.add_column("Date", style="cyan")
    table.add_column("Final Score", justify="right")
    table.add_column("Semantic", justify="right")
    table.add_column("Tokens", justify="right")
    table.add_column("Available", style="green")
    table.add_column("Reason", style="blue")

    MAX_CONTEXT_TOKENS = 4000
    cumulative_tokens = 0

    for ctx in sorted(contexts, key=lambda x: x.metadata.get('scoring', {}).get('final_score', 0), reverse=True):
        scoring = ctx.metadata.get('scoring', {})
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

    summary = Table.grid(padding=1)
    available_contexts = sum(1 for ctx in contexts if ctx.token_count + min(cumulative_tokens, MAX_CONTEXT_TOKENS) <= MAX_CONTEXT_TOKENS)
    summary.add_row(f"[cyan]Total contexts searched:[/cyan] {len(all_contexts)}")
    summary.add_row(f"[cyan]Contexts scored:[/cyan] {len(contexts)}")
    summary.add_row(f"[cyan]Contexts available:[/cyan] {available_contexts}")
    summary.add_row(f"[cyan]Total tokens:[/cyan] {min(cumulative_tokens, MAX_CONTEXT_TOKENS)}/{MAX_CONTEXT_TOKENS}")

    console.print(summary)
    console.print(table)

def inspect_contexts(cli, context_id: Optional[str] = None):
    """Inspect context files and compare versions."""
    try:
        if context_id:
            compressed_path = cli.store.storage_path / f"{context_id}.ctx"
            full_path = cli.store.storage_path.parent / 'full' / f"{context_id}.ctx"

            logger.debug(f"Inspecting context {context_id}")
            logger.debug(f"Compressed path: {compressed_path} (exists: {compressed_path.exists()})")
            logger.debug(f"Full path: {full_path} (exists: {full_path.exists()})")

            table = Table(title=f"Context Inspection: {context_id[:8]}", style="cyan")
            table.add_column("Version", style="blue")
            table.add_column("Content", style="green")
            table.add_column("Metadata", style="yellow")

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

    except Exception as e:
        logger.error(f"Error in inspect contexts: {e}")
        console.print(f"[red]Error: {e}[/red]")