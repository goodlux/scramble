import click
from rich.table import Table
from rich.panel import Panel
from ..ui.console import console


@click.command()
def config():
    """Show current configuration settings."""
    from ..app import RambleCLI
    app = RambleCLI()

    table = Table(title="Current Configuration")
    table.add_column("Section", style="cyan")
    table.add_column("Setting", style="blue")
    table.add_column("Value", style="green")

    for key, value in app.config['context'].items():
        table.add_row("context", key, str(value))

    for key, value in app.config['scoring'].items():
        table.add_row("scoring", key, str(value))

    console.print("\n")
    console.print(Panel.fit(table, title="Configuration"))