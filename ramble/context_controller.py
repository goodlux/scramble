# interface/context_controller.py
"""Controller for context-related commands and operations."""
from typing import Optional, Dict, Any
from rich.table import Table
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ContextController:
    """Handles context-related commands and operations."""
    
    def __init__(self, interface):
        """Initialize with reference to parent interface."""
        self.interface = interface
        
    async def handle_command(self, cmd: str) -> None:
        """Handle interface commands."""
        try:
            parts = cmd.strip().split(maxsplit=1)
            command = parts[0]
            args = parts[1] if len(parts) > 1 else ""

            # Core commands that every interface must support
            core_commands = {
                'h': self.show_help,
                'help': self.show_help,
                'q': self.quit,
                'quit': self.quit,
                'c': self.clear,
                'clear': self.clear,
                'd': self.toggle_debug,
                'debug': self.toggle_debug,
            }

            # Context management commands
            context_commands = {
                'contexts': self.show_contexts,
                'inspect': lambda: self.inspect_contexts(args),
                'reindex': self.reindex_contexts,
                'stats': self.show_stats,
                'analysis': self.show_compression_analysis,
                'sim': lambda: self.show_similarity(args),
            }

            # Combine command sets
            commands = {**core_commands, **context_commands}

            if command in commands:
                await commands[command]()
            else:
                await self.interface.display_error(f"Unknown command: {command}")

        except Exception as e:
            logger.error(f"Error handling command '{cmd}': {e}")
            await self.interface.display_error("Failed to execute command")

    # Core commands
    async def show_help(self) -> None:
        """Show help message."""
        help_text = """
Available Commands:
Basic:
  :h, :help    - Show this help message
  :q, :quit    - Exit the program
  :c, :clear   - Clear the screen
  :d, :debug   - Toggle debug mode

Context Management:
  :contexts    - Show recent contexts
  :inspect ID  - Inspect specific context
  :reindex     - Rebuild context index
  :stats       - Show system statistics
  :analysis    - Show compression analysis
  :sim QUERY   - Test similarity matching
"""
        await self.interface.display_output(help_text)

    async def quit(self) -> None:
        """Exit the program."""
        await self.interface.display_status("Goodbye! Contexts saved.")
        self.interface._shutdown_requested = True

    async def clear(self) -> None:
        """Clear the display."""
        await self.interface.clear()

    async def toggle_debug(self) -> None:
        """Toggle debug mode."""
        if self.interface.capabilities['has_debug']:
            current = logger.getEffectiveLevel()
            new_level = logging.DEBUG if current != logging.DEBUG else logging.INFO
            logger.setLevel(new_level)
            status = "enabled ✓" if new_level == logging.DEBUG else "disabled ✗"
            await self.interface.display_status(f"Debug mode {status}")

    # Context management commands
    async def show_contexts(self) -> None:
        """Show recent contexts."""
        contexts = self.interface.store.get_recent_contexts(hours=48)
        
        if not contexts:
            await self.interface.display_status("No recent contexts found")
            return

        # Build context summary
        summary = []
        for ctx in contexts:
            preview = ctx.text_content[:50] + "..." if len(ctx.text_content) > 50 else ctx.text_content
            chain = f"← {ctx.metadata.get('parent_context', '')[:8]}" if 'parent_context' in ctx.metadata else ""
            summary.append(f"{ctx.id[:8]} | {chain} | {preview}")

        await self.interface.display_output("\n".join(summary))

    async def inspect_contexts(self, context_id: Optional[str] = None) -> None:
        """Inspect context details."""
        if not context_id:
            await self.interface.display_error("Usage: :inspect <context_id>")
            return

        try:
            context = next(
                (ctx for ctx in self.interface.store.list() 
                 if ctx.id.startswith(context_id)),
                None
            )

            if not context:
                await self.interface.display_error(f"Context {context_id} not found")
                return

            # Format context details
            details = [
                f"ID: {context.id[:8]}",
                f"Created: {context.created_at.strftime('%Y-%m-%d %H:%M')}",
                f"Parent: {context.metadata.get('parent_context', 'None')[:8]}",
                f"Token Count: {context.token_count}",
                f"Content:\n{context.text_content[:200]}..."
            ]

            await self.interface.display_output("\n".join(details))

        except Exception as e:
            await self.interface.display_error(f"Error inspecting context: {e}")

    async def reindex_contexts(self) -> None:
        """Rebuild context index."""
        try:
            await self.interface.display_status("Reindexing contexts...")
            count = self.interface.store.reindex()
            await self.interface.display_status(f"Reindexed {count} contexts")
        except Exception as e:
            await self.interface.display_error(f"Error reindexing: {e}")

    async def show_stats(self) -> None:
        """Show system statistics."""
        summary = self.interface.store.get_conversation_summary()
        stats = [
            f"Total Conversations: {summary['total_conversations']}",
            f"Recent Contexts: {summary['recent_contexts']}",
            f"Active Chains: {summary['conversation_chains']}",
            f"Last Activity: {summary.get('last_interaction', 'Never')}"
        ]
        await self.interface.display_output("\n".join(stats))

    async def show_compression_analysis(self) -> None:
        """Show compression statistics."""
        try:
            stats = self.interface.context_manager.get_compression_stats()
            analysis = [
                f"Average Compression: {stats['compression_ratio']:.2f}x",
                f"Tokens Saved: {stats['tokens_saved']:,}",
                f"Context Chains: {stats['chain_count']}"
            ]
            await self.interface.display_output("\n".join(analysis))
        except Exception as e:
            await self.interface.display_error(f"Error generating analysis: {e}")

    async def show_similarity(self, query: str) -> None:
        """Show similarity matching results."""
        if not query:
            await self.interface.display_error("Usage: :sim <query text>")
            return

        try:
            contexts = self.interface.store.list()
            results = self.interface.context_manager.compressor.find_similar(
                query, contexts, top_k=5
            )

            summary = []
            for ctx, score, _ in results:
                summary.append(f"{ctx.id[:8]} | Score: {score:.3f} | {ctx.text_content[:50]}...")

            await self.interface.display_output("\n".join(summary))
        except Exception as e:
            await self.interface.display_error(f"Error in similarity search: {e}")