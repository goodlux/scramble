"""Base interface class for all Scramble applications."""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime
import os
import asyncio


# Core components
from ..core.store import ContextManager
from ..coordinator.model_coordinator import ModelCoordinator

# Controllers
from .message_controller import MessageController
from .context_controller import ContextController
from .tool_controller import ToolController

class InterfaceBase(ABC):
    """Base interface that supports core Scramble functionality."""
    
    def __init__(self):
        """Initialize interface."""

        # Initialize capabilities first
        self.capabilities: Dict[str, bool] = {
            'has_sidebar': False,
            'has_code_view': False,
            'has_debug': True,
            'has_themes': False,
        }

        # Core components and controllers stay here
        self.context_manager = ContextManager()
        self.store = self.context_manager.store
        self.model_coordinator = ModelCoordinator()
        
        # Controllers
        self.message_controller = MessageController(self)
        self.context_controller = ContextController(self)
        self.tool_controller = ToolController(self)
        
        # Basic state
        self._setup_complete = False
        self._shutdown_requested = False
    
    @abstractmethod
    def format_prompt(self) -> str:
        """Format prompt for display."""
        raise NotImplementedError
    
    async def setup(self) -> None:
        """Setup the interface."""
        if self._setup_complete:
            return
        
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
    
    # Input handling
    async def handle_input(self, user_input: str) -> None:
        """Process user input."""
        if user_input.startswith(':'):
            await self.context_controller.handle_command(user_input[1:])
        else:
            await self.message_controller.handle_message(user_input)
    
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