"""Ramble-specific interface implementation."""
from typing import Literal
from datetime import datetime
from rich.console import Console
from ..coordinator.coordinator import Coordinator   

from .interface_base import InterfaceBase

console = Console()
PromptStyle = Literal["minimal", "cyberpunk", "terminal", "scroll"]

class RambleInterface(InterfaceBase):
    def __init__(self):
        super().__init__()
        self.console = Console()
        self.model_name = None
        self._setup_complete = False

    async def setup(self) -> None:
        """Setup the interface."""
        if self._setup_complete:
            return
            
        # Create coordinator before trying to use it
        self.coordinator = Coordinator()
        await self.coordinator.initialize()
        
        if not self.model_name:
            raise ValueError("Model name not set")
            
        await self.coordinator.add_model(self.model_name)
        await self.coordinator.start_conversation()
        self._setup_complete = True

    async def run(self) -> None:
        """Run the interactive chat loop."""
        await self.display_status("Welcome to Ramble! Type 'exit' to quit.")
        
        while True:
            try:
                # Get user input
                user_input = await self.get_input()
                
                if user_input.lower() in ['exit', 'quit']:
                    await self.display_status("Goodbye!")
                    break
                    
                if not user_input.strip():
                    continue
                
                # Process through coordinator
                result = await self.coordinator.process_message(user_input)
                
                # Display the response
                await self.display_output(result['response'])
                
            except Exception as e:
                await self.display_error(f"Error: {str(e)}")

                
    def format_prompt(self) -> str:
        """Format prompt based on current style."""
        return "ramble> "  
    
    async def display_output(self, content: str) -> None:
        """Display output to the user."""
        self.console.print(content)
    
    async def display_error(self, message: str) -> None:
        """Display error message."""
        self.console.print(f"[red]Error: {message}[/red]")
    
    async def display_status(self, message: str) -> None:
        """Display status message."""
        self.console.print(f"[dim]{message}[/dim]")
    
    async def get_input(self) -> str:
        """Get input from user."""
        return input(self.format_prompt())
    
    async def clear(self) -> None:
        """Clear the display."""
        import os
        os.system('clear' if os.name == 'posix' else 'cls')