from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown
from datetime import datetime
from ..ui.console import console, logger

def show_help():
    """Show help message."""
    table = Table(title="Available Commands")
    table.add_column("Command", style="cyan")
    table.add_column("Description")

    table.add_row(":h, :help", "Show this help message")
    table.add_row(":inspect [id]", "Inspect context files (optional: specific context ID)")
    table.add_row(":s, :stats", "Show system statistics")
    table.add_row(":c, :contexts", "Show stored contexts")
    table.add_row(":dates", "Debug context dates")
    table.add_row(":a, :analysis", "Show detailed compression analysis")
    table.add_row(":d", "Toggle debug mode")
    table.add_row(":sim <query>", "Test similarity scoring against all contexts")
    table.add_row(":q, :quit", "Exit the program")

    console.print(table)

def show_contexts(store):
    """Show stored contexts with semantic chunks."""
    try:
        contexts = store.get_recent_contexts(hours=48)

        if not contexts:
            console.print(Panel("No recent contexts found", border_style="yellow"))
            return

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
            preview = ""
            if ctx.compressed_tokens:
                chunk = ctx.compressed_tokens[0]
                if isinstance(chunk, dict):
                    preview = chunk.get('content', '')[:50]
                else:
                    preview = str(chunk)[:50]
                if len(preview) == 50:
                    preview += "..."

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

        summary = store.get_conversation_summary()
        metadata = Table.grid(padding=1)
        metadata.add_row(
            f"[blue]Total Contexts:[/blue] {summary['total_conversations']}",
            f"[cyan]Active Chains:[/cyan] {summary['conversation_chains']}",
            f"[green]Recent Activity:[/green] {summary['recent_contexts']} contexts in 24h"
        )

        console.print(Panel(metadata, border_style="blue"))
        console.print(table)
        console.print()

    except Exception as e:
        logger.error(f"Error showing contexts: {e}")
        console.print(Panel(str(e), title="Error", border_style="red"))

def show_stats(cli):
    """Show enhanced system statistics."""
    try:
        summary = cli.store.get_conversation_summary()
        stats_table = cli.global_stats.generate_stats_table(hours=24)

        console.print("\n[bold]System Statistics[/bold]")
        console.print(stats_table)

        console.print("\n[bold]Conversation Summary[/bold]")
        summary_table = Table()
        summary_table.add_row("Total Conversations", str(summary['total_conversations']))
        summary_table.add_row("Recent Contexts", str(summary['recent_contexts']))
        summary_table.add_row("Active Chains", str(summary['conversation_chains']))
        console.print(summary_table)

    except Exception as e:
        logger.error(f"Error showing stats: {e}")
        console.print("[red]Failed to load statistics[/red]")

def show_compression_analysis(cli):
    """Show detailed compression analysis."""
    try:
        last_hour = cli.global_stats.get_compression_summary(hours=1)
        last_day = cli.global_stats.get_compression_summary(hours=24)
        all_time = cli.global_stats.get_compression_summary()

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

        token_stats = cli.global_stats.get_token_usage_summary(hours=24)
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

def show_similarity_debug(cli, query: str):
    """Show similarity scores for all contexts."""
    try:
        contexts = cli.store.list()
        results = cli.compressor.find_similar(query, contexts)

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