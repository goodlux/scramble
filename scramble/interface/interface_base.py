"""Base interface class for all Scramble applications."""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime
import asyncio
from scramble.utils.logging import get_logger

from scramble.coordinator.coordinator import Coordinator

logger = get_logger(__name__)

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
            
        self.coordinator = await Coordinator.create()
        await self.coordinator.initialize()
        self._setup_complete = True
    
    async def run(self) -> None:
        """Main interface loop."""
        await self.setup()
        
        try:
            await self.display_output("Welcome to Scramble!")
            
            while not self._shutdown_requested:
                user_input = await self.get_input()
                
                if user_input.lower() in ['exit', 'quit', ':q']:
                    if self.coordinator:
                        logger.info("Saving conversation...")
                        await self.coordinator.save_conversation_to_magicscroll()
                    break
                    
                await self.handle_user_input(user_input)
                
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
    async def display_model_output(self, content: str, model_name: str) -> None:
        """Display model output with speaker indicator."""
        raise NotImplementedError
    
    @abstractmethod
    async def clear(self) -> None:
        """Clear the display."""
        raise NotImplementedError
    
    async def handle_user_input(self, user_input: str) -> None:
        """Process user input."""
        if not self.coordinator:
            raise RuntimeError("Coordinator not initialized")
            
        try:
            # Handle system commands
            if user_input.startswith('/'):
                command = user_input[1:].split()
                match command[0]:
                    case 'add':
                        if len(command) > 1:
                            await self.coordinator.add_model_to_conversation(command[1])
                            await self.display_model_output(f"{command[1]} was added to the conversation", "system")
                    case 'remove':
                        if len(command) > 1:
                            await self.coordinator.remove_model_from_conversation(command[1])
                            await self.display_model_output(f"{command[1]} was removed from the conversation", "system")
                    case _:
                        pass  # Handle unknown commands
                return

            # Regular message - pass to coordinator
            response = await self.coordinator.process_message(user_input)
            if response and response.get("response"):
                model_name = response.get("model", "system")
                await self.display_model_output(response["response"], model_name)
                
        except Exception as e:
            await self.display_error(f"Error processing input: {e}")
    
    async def _emergency_shutdown(self) -> None:
        """Handle emergency shutdown."""
        await self.display_status("\n🚨 Emergency shutdown initiated")
        if self.coordinator:
            logger.info("Saving conversation...")
            await self.coordinator.save_conversation_to_magicscroll()
        self._shutdown_requested = True