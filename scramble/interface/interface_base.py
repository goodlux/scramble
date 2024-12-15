"""Base interface class for Scramble applications."""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime
import asyncio
import os

from ..core.store import ContextManager
from ..core.api import AnthropicClient

class InterfaceBase(ABC):
    """Base interface that supports core Scramble functionality."""
    
    def __init__(self):
        """Initialize interface."""
        # Core components (matching ramble's current working setup)
        self.context_manager = ContextManager()
        self.store = self.context_manager.store
        self.client = None  # Set up in setup()
        
        # Basic state
        self._setup_complete = False
        self._shutdown_requested = False
    
    async def setup(self) -> None:
        """Setup interface and core components."""
        if self._setup_complete:
            return
            
        # Set up client (using existing working code)
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is required")
            
        self.client = AnthropicClient(
            api_key=api_key,
            context_manager=self.context_manager
        )
        
        self._setup_complete = True
    
    # Required interface methods
    @abstractmethod
    async def display_output(self, content: str) -> None:
        """Display output to the user."""
        raise NotImplementedError
        
    @abstractmethod
    async def display_error(self, message: str) -> None:
        """Display error message."""
        raise NotImplementedError
        
    @abstractmethod
    async def display_status(self, message: str) -> None:
        """Display status message."""
        raise NotImplementedError
        
    @abstractmethod
    async def get_input(self) -> str:
        """Get input from user."""
        raise NotImplementedError
    
    @abstractmethod
    async def clear(self) -> None:
        """Clear the display."""
        raise NotImplementedError
    
    # Message handling
    async def process_message(self, message: str) -> None:
        """Process a chat message using existing working code."""
        try:
            contexts = self.context_manager.process_message(message)
            response = await self.client.send_message(
                message=message,
                contexts=contexts
            )
            
            if self.client.current_context:
                response['context'].metadata['parent_context'] = \
                    self.client.current_context.id
                self.store.add(response['context'])
            
            await self.display_output(response['response'])
            
        except Exception as e:
            await self.display_error(f"Error processing message: {e}")
    
    # Command handling
    async def handle_input(self, user_input: str) -> None:
        """Process user input."""
        if user_input.startswith(':'):
            await self.handle_command(user_input[1:])
        else:
            await self.process_message(user_input)
    
    async def handle_command(self, command: str) -> None:
        """Handle basic commands."""
        commands = {
            'h': self.show_help,
            'help': self.show_help,
            'q': self.quit,
            'quit': self.quit,
            'c': self.clear,
            'clear': self.clear,
        }
        
        cmd_func = commands.get(command.lower())
        if cmd_func:
            await cmd_func()
        else:
            await self.display_error(f"Unknown command: {command}")
    
    # Standard commands
    async def show_help(self) -> None:
        """Show help message."""
        help_text = """
Available commands:
:h, :help  - Show this help message
:q, :quit  - Exit the program
:c, :clear - Clear the screen
"""
        await self.display_output(help_text)
    
    async def quit(self) -> None:
        """Exit the program."""
        await self.display_status("Goodbye! Contexts saved.")
        self._shutdown_requested = True
    
    # Main run loop
    async def run(self) -> None:
        """Main interface loop."""
        await self.setup()
        
        try:
            await self.display_output("Welcome to Scramble!")
            
            while not self._shutdown_requested:
                await self.display_output(f"[{datetime.now().strftime('%H:%M')}] > ")
                user_input = await self.get_input()
                await self.handle_input(user_input)
                
        except KeyboardInterrupt:
            await self._emergency_shutdown()
        except Exception as e:
            await self.display_error(f"Fatal error: {e}")
            await self._emergency_shutdown()
    
    async def _emergency_shutdown(self) -> None:
        """Handle emergency shutdown."""
        await self.display_status("\n🚨 Emergency shutdown initiated")
        self._shutdown_requested = True