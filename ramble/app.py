"""RambleMAXX - Terminal-based AI interaction interface."""
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import (
    Header, 
    Footer, 
    Static, 
    Log, 
    TextArea, 
    MarkdownViewer
)
import asyncio

from scramble.interface.maxx_interface import MAXXInterface

class RambleMaxx(App):
    """Terminal-based interface for Scramble."""
    
    CSS_PATH = "styles/maxx.tcss"
    
    BINDINGS = [
        ("ctrl+b", "toggle_sidebar", "Toggle Side"),
        ("ctrl+c", "quit", "Quit"),
        ("f1", "show_help", "Help"),
    ]
    
    def __init__(self):
        super().__init__()
        self.interface = None
        self._current_line = ""
        self._input_ready = asyncio.Event()
    
    def on_mount(self) -> None:
        """Set up interface after app is mounted."""
        self.interface = MAXXInterface(self)
    
    def compose(self) -> ComposeResult:
        """Create the interface layout."""
        yield Header(show_clock=True)
        yield Horizontal(
            # Main chat view
            Log(id="chat-view"),
            # Right side panel
            Vertical(
                MarkdownViewer(id="doc-view", classes="hidden"),
                TextArea(id="code-view", classes="hidden"),
                id="side-pane",
                classes="hidden"
            ),
            id="main-container"
        )
        yield Footer()
    
    async def on_key(self, event) -> None:
        """Handle terminal-style input."""
        chat_view = self.query_one("#chat-view", Log)
        
        if event.key == "enter":
            if self.interface and self._current_line:
                # Process input
                await self.interface.handle_input(self._current_line)
                self._current_line = ""
                # Show new prompt
                chat_view.write("")  # New line
        else:
            # Handle input buffering
            if event.key == "backspace":
                self._current_line = self._current_line[:-1]
            elif len(event.key) == 1:  # Regular character
                self._current_line = self._current_line + event.key
            
            # Update display - just use plain text for input line
            chat_view.write(f"> {self._current_line}")
    
    def action_toggle_sidebar(self) -> None:
        """Toggle the side panel."""
        side_pane = self.query_one("#side-pane")
        if "hidden" in side_pane.classes:
            side_pane.remove_class("hidden")
        else:
            side_pane.add_class("hidden")
    
    def action_show_help(self) -> None:
        """Show help information."""
        chat_view = self.query_one("#chat-view", Log)
        chat_view.write("[bold]Available Commands:[/bold]")
        chat_view.write("F1          - Show this help")
        chat_view.write("Ctrl+B      - Toggle side panel")
        chat_view.write("Ctrl+C      - Quit")
        chat_view.write(":h, :help   - Show command help")
        chat_view.write(":c, :clear  - Clear screen")
        chat_view.write(":q, :quit   - Exit program")
    
    def action_quit(self) -> None:
        """Exit the application."""
        self.exit()