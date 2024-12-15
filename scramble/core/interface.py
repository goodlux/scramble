"""Core interface for Scramble clients."""
"""
DEPRECATED: This interface is being replaced by scramble/interface/interface_base.py
Keeping for reference until new interface is fully implemented.
"""
from typing import Protocol, runtime_checkable
import os
from datetime import datetime

from .store import ContextManager
from .compressor import SemanticCompressor
from .api import AnthropicClient

class ScrambleMixin:
    """Mixin for Scramble clients."""
    
    def setup_scramble(self) -> None:
        """Initialize core components."""
        self.compressor = SemanticCompressor()
        self.context_manager = ContextManager()
        self.store = self.context_manager.store

        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is required")

        self.client = AnthropicClient(
            api_key=api_key,
            compressor=self.compressor,
            context_manager=self.context_manager
        )
    
    async def display_output(self, _content: str) -> None:
        """Display output to user."""
        raise NotImplementedError
    
    async def get_input(self) -> str:
        """Get input from user."""
        raise NotImplementedError

    async def handle_command(self, _command: str) -> None:
        """Handle a command."""
        raise NotImplementedError
    
    async def process_message(self, message: str) -> None:
        """Process a chat message."""
        try:
            # Get relevant contexts
            contexts = self.context_manager.process_message(message)
            
            # Send to model - make sure this is async
            response = await self.client.send_message(
                message=message,
                contexts=contexts
            )
            
            # Store new context with chains linking
            if self.client.current_context:
                response['context'].metadata['parent_context'] = \
                    self.client.current_context.id
                self.store.add(response['context'])
            
            # Display response
            await self.display_output(response['response'])
            
        except Exception as e:
            await self.display_output(f"Error: {e}")

    async def run_scramble(self) -> None:
        """Main interaction loop."""
        try:
            # Show welcome
            await self.display_output("Welcome to Scramble!")
            
            while True:
                # Show prompt
                await self.display_output(f"[{datetime.now().strftime('%H:%M')}] > ")
                
                # Get input
                user_input = await self.get_input()
                
                if user_input.lower() in ['exit', 'quit', ':q']:
                    await self.display_output("Goodbye! Contexts saved.")
                    break
                
                if user_input.startswith(':'):
                    await self.handle_command(user_input[1:])
                else:
                    await self.process_message(user_input)
                    
        except Exception as e:
            await self.display_output(f"Error in main loop: {e}")