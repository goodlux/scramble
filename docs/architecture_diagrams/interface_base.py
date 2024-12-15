"""
InterfaceBase: Core interface functionality for scramble applications
"""
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
import asyncio
from datetime import datetime


class InterfaceBase(ABC):
    """Base class for scramble interfaces."""
    
    def __init__(self):
        """Initialize interface."""
        self.capabilities: Dict[str, bool] = {
            'has_sidebar': False,  # Overridden by implementing class
            'has_code_view': False,
            'has_debug': True,     # Default capabilities
            'has_themes': False,
        }
        self._setup_complete = False
        self._shutdown_requested = False
    
    # Display Methods
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
        
    def format_prompt(self) -> str:
        """Format standard prompt with timestamp."""
        return f"[{datetime.now().strftime('%H:%M')}] > "
    
    # Input Methods
    @abstractmethod
    async def get_input(self) -> str:
        """Get input from user."""
        raise NotImplementedError
    
    async def handle_input(self, user_input: str) -> None:
        """Process user input."""
        if user_input.startswith(':'):
            await self.handle_command(user_input[1:])
        else:
            await self.process_message(user_input)
    
    async def handle_command(self, command: str) -> None:
        """Handle interface commands."""
        commands = {
            'h': self.show_help,
            'help': self.show_help,
            'q': self.quit,
            'quit': self.quit,
            'c': self.clear,
            'clear': self.clear,
            'd': self.toggle_debug,
            'debug': self.toggle_debug
        }
        
        cmd_func = commands.get(command.lower())
        if cmd_func:
            await cmd_func()
        else:
            await self.display_error(f"Unknown command: {command}")
    
    # Capability Methods
    def get_capabilities(self) -> Dict[str, bool]:
        """Return interface capabilities."""
        return self.capabilities
    
    def has_capability(self, capability: str) -> bool:
        """Check if interface has specific capability."""
        return self.capabilities.get(capability, False)
    
    # Standard Commands
    async def show_help(self) -> None:
        """Show help message."""
        help_text = """
Available commands:
:h, :help  - Show this help message
:q, :quit  - Exit the program
:c, :clear - Clear the screen
:d, :debug - Toggle debug mode
"""
        await self.display_output(help_text)
    
    async def quit(self) -> None:
        """Exit the program."""
        self._shutdown_requested = True
    
    @abstractmethod
    async def clear(self) -> None:
        """Clear the display."""
        raise NotImplementedError
    
    async def toggle_debug(self) -> None:
        """Toggle debug mode."""
        if self.has_capability('has_debug'):
            # Implementation specific
            pass
    
    # Lifecycle Methods
    async def setup(self) -> None:
        """Setup the interface."""
        if self._setup_complete:
            return
            
        # Implementing classes should call super().setup()
        self._setup_complete = True
    
    async def run(self) -> None:
        """Main interface loop."""
        await self.setup()
        
        try:
            while not self._shutdown_requested:
                await self.display_output(self.format_prompt())
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
