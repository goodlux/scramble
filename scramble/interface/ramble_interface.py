"""Ramble-specific interface implementation."""
from typing import Literal
from datetime import datetime
from rich.console import Console
from ..coordinator.coordinator import Coordinator   

from .interface_base import InterfaceBase


PromptStyle = Literal["minimal", "cyberpunk", "terminal", "scroll"]

class RambleInterface(InterfaceBase):
    def __init__(self):
        super().__init__()
        

    async def setup(self) -> None:
        """Setup the interface."""
        if self._setup_complete:
            return
            
        
        # Create coordinator before trying to use it
        self.coordinator = Coordinator()
        await self.coordinator.initialize()
        await self.coordinator.add_model('claude-3-opus')
        self._setup_complete = True

    def format_prompt(self) -> str:
        """Format prompt based on current style."""
        return ">>>>>>"  # Default prompt style
    
    async def display_output(self, content: str) -> None:
        """Display output to the user."""
        print(content)
    
    async def display_error(self, message: str) -> None:
        """Display error message."""
        print(f"[red]Error: {message}[/red]")
    
    async def display_status(self, message: str) -> None:
        """Display status message."""
        print(f"[dim]{message}[/dim]")
    
    async def get_input(self) -> str:
        """Get input from user."""
        return input(self.format_prompt())
    
    async def clear(self) -> None:
        """Clear the display."""
        import os
        os.system('clear' if os.name == 'posix' else 'cls')