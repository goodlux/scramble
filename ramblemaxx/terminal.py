"""Custom terminal implementation for RambleMAXX."""
from textual_terminal import Terminal
from typing import Optional
from rich.style import Style

class ChatTerminal(Terminal):
    """Terminal with chat and command handling."""
    
    def __init__(self, interface=None):
        # Use "textual" for default colors to match our theme
        super().__init__(
            command="bash",
            default_colors="textual"  # This is the correct parameter
        )
        self.interface = interface
    
    def set_interface(self, interface) -> None:
        """Set the interface after initialization."""
        self.interface = interface
    
    async def on_line(self, line: str) -> None:
        """Handle input line."""
        if not line.strip():
            return
            
        try:
            if line.startswith(':'):
                # Handle as Ramble command
                if self.interface:
                    await self.interface.handle_command(line[1:])
            elif line.startswith('!'):
                # Handle as shell command
                await super().on_line(line[1:])
            else:
                # Handle as chat message
                if self.interface:
                    await self.interface.handle_message(line)
        except Exception as e:
            # Show error in terminal
            self.write(f"\r\n[red]Error: {str(e)}[/red]\r\n")