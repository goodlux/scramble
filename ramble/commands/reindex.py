import click
from rich.table import Table
from ..ui.console import console

@click.command()
def reindex():
    """Rebuild context index from stored files."""
    from ..app import RambleCLI
    app = RambleCLI()

    with console.status("[bold blue]Reindexing contexts...", spinner="dots"):
        count = app.store.reindex()

    console.print(f"[green]Successfully reindexed {count} contexts[/green]")

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