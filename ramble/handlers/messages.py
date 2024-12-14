from typing import List
from scramble.core.context import Context
from ..ui.console import console, logger
import dateparser
from datetime import datetime
from rich.markdown import Markdown

class MessageHandler:
    def __init__(self, cli):
        self.cli = cli

    def process_message(self, message: str, use_all_contexts: bool = False) -> List[Context]:
        """Process message and select relevant contexts."""
        candidates = []

        # Check for temporal references
        if dateparser.parse(message):
            historical = self.cli.context_manager.find_contexts_by_timeframe(message)
            candidates.extend(historical)

        if use_all_contexts:
            all_contexts = self.cli.store.list()
            similar = self.cli.compressor.find_similar(message, all_contexts, top_k=10)
            candidates.extend([ctx for ctx, _, _ in similar])
        else:
            recent = self.cli.store.get_recent_contexts(hours=168)
            candidates.extend(recent)

            if any(word in message.lower() for word in ['previous', 'before', 'earlier', 'last time', 'recall']):
                all_contexts = self.cli.store.list()
                similar = self.cli.compressor.find_similar(message, all_contexts, top_k=5)
                candidates.extend([ctx for ctx, _, _ in similar])

        return self.cli.context_manager.select_contexts(message, candidates)

    async def handle_message(self, message: str):
        """Handle user message and get response."""
        try:
            contexts = self.process_message(message)
            
            result = self.cli.client.send_message(
                message=message,
                contexts=contexts
            )

            if self.cli.client.current_context:
                result['context'].metadata['parent_context'] = self.cli.client.current_context.id
                self.cli.store.add(result['context'])

            console.print("\n[bold cyan]Claude:[/bold cyan]")
            console.print(Markdown(result['response']))
            
            return result

        except Exception as e:
            logger.exception("Error processing message")
            console.print(Panel(str(e), title="Error", border_style="red"))
            return None