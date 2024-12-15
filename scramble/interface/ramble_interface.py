"""Ramble-specific interface implementation."""
from typing import Literal
from datetime import datetime
from .interface_base import InterfaceBase
from rich.console import Console

PromptStyle = Literal["minimal", "cyberpunk", "terminal", "scroll"]

class RambleInterface(InterfaceBase):
    """Base class for Ramble interfaces with shared UI functionality."""
    
    def __init__(self):
        super().__init__()
        self.console = Console()
        self.prompt_style: PromptStyle = "cyberpunk"  # Ramble default
        self._custom_prompt_fn = None
    
    def set_prompt_style(self, style: PromptStyle) -> None:
        """Set the prompt style."""
        self.prompt_style = style
    
    def set_custom_prompt(self, prompt_fn) -> None:
        """Set a custom prompt function."""
        self._custom_prompt_fn = prompt_fn
    
    def format_prompt(self) -> str:
        """Format prompt based on current style."""
        timestamp = datetime.now().strftime("%H:%M")
        
        if self.prompt_style == "cyberpunk":
            # First line
            line1 = f"[bold blue]╭─[/bold blue][bold cyan]ramble[/bold cyan] [dim]{timestamp}[/dim]"
            # Second line with no newline
            line2 = f"[bold blue]╰─[/bold blue][bold green]>[/bold green]"
            
            return f"{line1}\n{line2}"  # Let Rich handle the newline