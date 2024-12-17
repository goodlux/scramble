"""Ramble-specific interface implementation."""
from typing import Literal
from datetime import datetime
from rich.console import Console

from ..coordinator.coordinator import Coordinator

PromptStyle = Literal["minimal", "cyberpunk", "terminal", "scroll"]

class RambleInterface():
    """Base class for Ramble interfaces with shared UI functionality."""
    
    def __init__(self):
        super().__init__()
        self.console = Console()
        self.prompt_style: PromptStyle = "cyberpunk"  # Ramble default
        self.coordinator = Coordinator()
    
    def format_prompt(self) -> str:
        """Format prompt based on current style."""
        timestamp = datetime.now().strftime("%H:%M")
        
        if self.prompt_style == "cyberpunk":
            # First line
            line1 = f"[bold blue]╭─[/bold blue][bold cyan]ramble[/bold cyan] [dim]{timestamp}[/dim]"
            # Second line with no newline
            line2 = f"[bold blue]╰─[/bold blue][bold green]>[/bold green]"
            
            return f"{line1}\n{line2}" 