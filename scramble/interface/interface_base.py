"""Base interface class for all Scramble applications."""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime
import asyncio

from scramble.coordinator.coordinator import Coordinator

class InterfaceBase(ABC):
    """Base interface that supports core Scramble functionality."""
    
    def __init__(self):
        """Initialize interface."""
        self.coordinator: Optional[Coordinator] = None
        
        # Initialize capabilities
        self.capabilities: Dict[str, bool] = {
            'has_sidebar': False,
            'has_code_view': False,
            'has_debug': True,
            'has_themes': False,
        }
        
        # Basic state
        self._setup_complete = False
        self._shutdown_requested = False

    async def setup(self) -> None:
        """Setup the interface."""
        if self._setup_complete:
            return
            
        self.coordinator = Coordinator()
        # Initialize the coordinator asynchronously
        await self.coordinator.initialize()
        self._setup_complete = True
    
    async def run(self) -> None:
        """Main interface loop."""
        await self.setup()
        
        try:
            await self.display_output("Welcome to Scramble!")
            
            while not self._shutdown_requested:
                await self.display_output(f"[{datetime.now().strftime('%H:%M')}] > ")
                user_input = await self.get_input()
                
                if user_input.lower() in ['exit', 'quit', ':q']:
                    break
                    
                await self.handle_input(user_input)
                
        except KeyboardInterrupt:
            await self._emergency_shutdown()
        except Exception as e:
            await self.display_error(f"Fatal error: {e}")
            await self._emergency_shutdown()
    
    # Required abstract methods
    @abstractmethod
    def format_prompt(self) -> str:
        """Format prompt for display."""
        raise NotImplementedError
    
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
        if not self.coordinator:
            raise RuntimeError("Coordinator not initialized")
            
        try:
            response = await self.coordinator.process_message(user_input)
            # Display the response if there is one
            if response and response.get("response"):
                await self.display_output(response["response"])
        except Exception as e:
            await self.display_error(f"Error processing input: {e}")
    
    async def _emergency_shutdown(self) -> None:
        """Handle emergency shutdown."""
        await self.display_status("\n🚨 Emergency shutdown initiated")
        self._shutdown_requested = True