"""
RambleMaxx - Unleashed version of Ramble
Now with 100% more MAXX and 100% less React
"""

import os, sys
import signal
from typing import Optional, Dict, Any, TypedDict


from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import (
    Header, 
    Footer, 
    Static, 
    Log, 
    TextArea, 
    MarkdownViewer,
    Input
)
from textual.binding import Binding
from scramble.core.interface import ScrambleInterface
import asyncio


class RambleMaxx(App[None], ScrambleInterface):
    """The MAXX version of Scramble."""
    
    CSS_PATH = "styles/maxx.tcss"
    
    BINDINGS = [
        ("ctrl+t", "cycle_theme", "Theme"),
        ("ctrl+b", "toggle_sidebar", "Toggle Code"),
        ("ctrl+c", "quit", "Quit"),
    ]
    
    def __init__(self):
        App.__init__(self)
        ScrambleInterface.__init__(self)
        self._input_ready = asyncio.Event()
        self._current_input = None
    
    def compose(self) -> ComposeResult:
        """Create our MAXX interface."""
        yield Header(show_clock=True)
        yield Static("🚀 RAMBLEMAXX [bold red]TURBO EDITION[/bold red] 🚀", id="maxx-header")
        yield Horizontal(
            Vertical(
                Log(highlight=True, id="chat-view"),
                Input(id="chat-input", placeholder="Enter message..."),
                id="chat-pane"
            ),
            Vertical(
                TextArea(language="python", id="code-editor"),
                MarkdownViewer(id="code-output"),
                id="side-pane",
                classes="hidden"
            ),
            id="main-container"
        )
        yield Footer()
    
    async def on_mount(self) -> None:
        """Start the interface."""
        # Start the main loop
        asyncio.create_task(self.run())
    
    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission."""
        self._current_input = event.input.value
        event.input.value = ""  # Clear input
        self._input_ready.set()  # Signal input is ready
    
    async def display_output(self, content: str) -> None:
        """Display output in the chat view."""
        chat_view = self.query_one("#chat-view", Log)
        chat_view.write(content)
    
    async def get_input(self) -> str:
        """Get input through Textual."""
        self._input_ready.clear()  # Reset event
        await self._input_ready.wait()  # Wait for input
        return self._current_input
    
    async def handle_command(self, command: str) -> None:
        """Handle commands."""
        if command == "theme":
            self.action_cycle_theme()
        elif command == "clear":
            chat_view = self.query_one("#chat-view", Log)
            chat_view.clear()
        elif command == "help":
            await self.display_output("""
Available commands:
:theme - Cycle theme
:clear - Clear chat
:help  - Show this help
""")




    def action_toggle_sidebar(self) -> None:
        """Toggle sidebar visibility."""
        try:
            side_pane = self.query_one("#side-pane")
            if "hidden" in side_pane.classes:
                side_pane.remove_class("hidden")
            else:
                side_pane.add_class("hidden")
        except NoMatches:
            self.notify("Side pane not found", severity="error")

    def _emergency_shutdown(self, *args: Any) -> None:
        """EMERGENCY SHUTDOWN PROTOCOL"""
        print("\n🚨 EMERGENCY SHUTDOWN INITIATED 🚨")
        self.exit()
        sys.exit(0)

    async def action_quit(self) -> None:
        """Quit with extreme prejudice."""
        print("\n👋 Goodbye! (Containment Successful)")
        self.exit()
        sys.exit(0)