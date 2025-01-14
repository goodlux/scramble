from typing import Literal, Optional
from rich.console import Console
from scramble.coordinator import Coordinator
from .interface_base import InterfaceBase
from scramble.utils.logging import get_logger

logger = get_logger(__name__)

class RambleInterface(InterfaceBase):
    def __init__(self):
        super().__init__()
        self.console = Console()
        self.model_name: Optional[str] = None
        self._setup_complete = False
        self.coordinator: Optional[Coordinator] = None
        self.current_speaker: Optional[str] = None

    def set_model_name(self, name: str) -> None:
        """Set the model name to use.

        Args:
            name: The name of the model to use
        """
        if not isinstance(name, str):
            raise TypeError("Model name must be a string")
        self.model_name = name

    async def setup(self) -> None:
        """Setup the interface."""
        if self._setup_complete:
            return

        self.coordinator = await Coordinator.create()
        if not self.model_name:
            raise ValueError("Model name not set")

        await self.coordinator.add_model_to_conversation(self.model_name)
        await self.coordinator.start_conversation()
        self._setup_complete = True

        # Send initial greeting through the coordinator
        greeting_result = await self.coordinator.process_message("system: introduce yourself")
        await self.display_model_output(greeting_result['response'], greeting_result['model'])

    def format_prompt(self) -> str:
        """Format prompt based on current style."""
        return "[bold cyan]you[/bold cyan]> "

    def format_model_prompt(self, model_name: str) -> str:
        """Format prompt for model responses."""
        if model_name == "system":
            return "[bold red]system[/bold red]> "
        color = "green" if model_name == "granite" else "blue"  # Different colors for different models
        return f"[bold {color}]{model_name}[/bold {color}]> "

    async def display_model_output(self, content: str, model_name: str) -> None:
        """Display model output with speaker indicator."""
        prompt = self.format_model_prompt(model_name)
        self.console.print(f"{prompt}{content}")

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
        self.console.print(self.format_prompt(), end="")
        return input()

    async def clear(self) -> None:
        """Clear the display."""
        import os
        os.system('clear' if os.name == 'posix' else 'cls')