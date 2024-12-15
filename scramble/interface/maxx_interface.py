"""MAXX-specific interface implementation."""
from typing import Dict, Any, Optional, Literal
from textual.widgets import Log
from textual.app import App

from .interface_base import InterfaceBase


PromptStyle = Literal["minimal", "cyberpunk", "terminal", "scroll"]

class MAXXInterface(InterfaceBase):
    """Interface implementation for RambleMAXX."""
    
    def __init__(self, app: App):
        super().__init__()
        self.app = app
        self.capabilities.update({
            'has_sidebar': True,
            'has_code_view': True,
            'has_themes': True,
            'has_model_select': True,
        })
    
    async def display_output(self, content: str) -> None:
        """Display output in the chat view."""
        chat_view = self.app.query_one("#chat-view", Log)
        chat_view.write(content)
    
    async def display_error(self, message: str) -> None:
        """Display error message."""
        chat_view = self.app.query_one("#chat-view", Log)
        chat_view.write(f"[red]Error: {message}[/red]")
    
    async def display_status(self, message: str) -> None:
        """Display status message."""
        chat_view = self.app.query_one("#chat-view", Log)
        chat_view.write(f"[dim]{message}[/dim]")
    
    async def get_input(self) -> str:
        """Get input through Textual."""
        # This will be handled by the app's input events
        await self.app._input_ready.wait()
        return self.app._current_input
    
    async def clear(self) -> None:
        """Clear the display."""
        chat_view = self.app.query_one("#chat-view", Log)
        chat_view.clear()

    def format_prompt(self) -> str:
        """Format prompt based on current style."""
        timestamp = datetime.now().strftime("%H:%M")
        
        if self.prompt_style == "cyberpunk":
            # First line
            line1 = f"[bold blue]╭─[/bold blue][bold cyan]ramble[/bold cyan] [dim]{timestamp}[/dim]"
            # Second line with no newline
            line2 = f"[bold blue]╰─[/bold blue][bold green]>[/bold green]"
            
            return f"{line1}\n{line2}"  # Let Rich handle the newline