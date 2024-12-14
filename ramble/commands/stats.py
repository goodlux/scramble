import click
from rich.table import Table
from rich.panel import Panel
from ..ui.console import console



@click.command()
@click.option('--hours', default=48, help='Stats from last N hours')
def detailed_stats(hours: int):
    """Show detailed statistics for the last N hours."""
    from ..app import RambleCLI
    app = RambleCLI()
    app._show_stats()