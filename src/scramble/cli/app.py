# src/scramble/cli/app.py
import sys
from typing import Optional

import click

from ..core.compressor import SemanticCompressor
from ..core.store import ContextStore
from ..core.context import Context

@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """scRAMBLE - Semantic Compression for AI Dialogue"""
    if ctx.invoked_subcommand is None:
        # No subcommand - start interactive mode
        app = ScrambleCLI()
        app.start_interactive()

class ScrambleCLI:
    def __init__(self):
        self.compressor = SemanticCompressor()
        self.store = ContextStore()
        
    def start_interactive(self):
        """Start interactive chat session."""
        click.echo("🧠 ramble v0.1.0 - Semantic Compression Active")
        click.echo(f"[Semantic Index: {len(self.store.list())} stored contexts]\n")
        
        while True:
            try:
                user_input = click.prompt('>', prompt_suffix=' ')
                if user_input.lower() in ['exit', 'quit']:
                    break
                    
                # Find relevant contexts
                similar = self.compressor.find_similar(user_input, self.store.list())
                
                if similar:
                    click.echo("\n[Found relevant contexts:]")
                    for context, similarity in similar:
                        self._print_context_info(context, similarity)
                
                # For now, just compress and store the new input
                new_context = self.compressor.compress(user_input)
                self.store.add(new_context)
                
            except KeyboardInterrupt:
                click.echo("\nGoodbye!")
                break
            except Exception as e:
                click.echo(f"Error: {e}", err=True)
                
    def _print_context_info(self, context: Context, similarity: Optional[float] = None):
        """Print information about a context."""
        click.echo(f"Context {context.id[:8]}")
        if similarity is not None:
            click.echo(f"  Similarity: {similarity:.2f}")
        click.echo(f"  Chunks: {context.size}")
        if 'original_length' in context.metadata:
            click.echo(f"  Original length: {context.metadata['original_length']}")
        click.echo()

@cli.command()
def stats():
    """Show statistics about stored contexts"""
    app = ScrambleCLI()
    contexts = app.store.list()
    click.echo(f"Total contexts: {len(contexts)}")
    total_chunks = sum(c.size for c in contexts)
    click.echo(f"Total chunks: {total_chunks}")

if __name__ == '__main__':
    cli()