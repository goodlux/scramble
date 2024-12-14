import click
import pickle
from rich.table import Table
from ..ui.console import console

@click.command()
@click.argument('context_id', required=False)
def inspect(context_id: str = None):
    """Inspect context files and compare full/compressed versions."""
    from ..app import RambleCLI  # Import here to avoid circular imports
    app = RambleCLI()

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