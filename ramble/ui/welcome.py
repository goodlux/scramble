from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from scramble.core.store import ContextStore

console = Console(stderr=True, soft_wrap=True)

def show_welcome(store: ContextStore) -> None:
    """Show welcome message and stats."""
    grid = Table.grid(padding=1)
    
    # Add welcome header
    grid.add_row(
        Panel(
            "[bold blue]🧠 Ramble v0.1.0[/bold blue]\n"
            "[dim]Powered by Scramble[/dim]",
            border_style="blue"
        )
    )

    try:
        summary = store.get_conversation_summary()

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
        console.print(f"[red]Error showing welcome message: {e}[/red]")