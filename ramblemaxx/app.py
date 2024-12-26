"""RambleMAXX - Terminal-based AI interaction interface."""
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Header, Footer, MarkdownViewer

from scramble.interface.maxx_interface import MAXXInterface
from scramble.interface.widgets.chat_terminal_widget import ChatTerminalWidget

class RambleMaxx(App):
    """Terminal-based interface for Scramble."""
    
    CSS_PATH = "styles/maxx.tcss"
    
    BINDINGS = [
        ("ctrl+b", "toggle_sidebar", "Toggle Side"),
        ("ctrl+c", "quit", "Quit"),
        ("f1", "show_help", "Help"),
    ]
    
    def __init__(self):
        # TODO: Interface - Prepare for graph visualization
        # TODO: Interface - Add observer panel hooks
        # TODO: Interface - Set up animation framework
        # TODO: LocalAI - Add observer initialization
        super().__init__()
        self.interface = None
    
    def on_mount(self) -> None:
        """Set up interface after app is mounted."""
        # Create interface
        self.interface = MAXXInterface(self)
        
        # Get terminal widget and connect to interface
        terminal = self.query_one("#chat-term", ChatTerminalWidget)
        terminal.set_interface(self.interface)
        
        # Write welcome message using terminal tool
        self.interface.tool_controller.invoke_tool(
            "ChatTerminalWidget.write", 
            "Welcome to RambleMAXX! Type :help for commands.\n"
        )
    
    def compose(self) -> ComposeResult:
        """Create the interface layout."""
        # TODO: Interface - Add graph visualization area
        # TODO: Interface - Prepare observer panel
        # TODO: Interface - Add relationship display
        yield Header(show_clock=True)
        yield Horizontal(
            # Main chat terminal
            ChatTerminalWidget(id="chat-term"),
            # Right side panel
            Vertical(
                MarkdownViewer(id="doc-view", classes="hidden"),
                id="side-pane",
                classes="hidden"
            ),
            id="main-container"
        )
        yield Footer()
    
    async def on_chat_terminal_widget_input(self, message: ChatTerminalWidget.Input) -> None:
        """Handle terminal input."""
        if message.text.startswith(':'):
            # Handle as Ramble command
            if self.interface:
                await self.interface.handle_command(message.text[1:])
        else:
            # Handle as chat message
            if self.interface:
                await self.interface.handle_message(message.text)
    
    def action_toggle_sidebar(self) -> None:
        """Toggle the side panel."""
        side_pane = self.query_one("#side-pane")
        if "hidden" in side_pane.classes:
            side_pane.remove_class("hidden")
        else:
            side_pane.add_class("hidden")
    
    async def action_show_help(self) -> None:
        """Show help information."""
        if self.interface:
            help_text = """
Available Commands:
F1          - Show this help
Ctrl+B      - Toggle side panel 
Ctrl+C      - Quit

Chat Commands:
:h, :help   - Show command help
:c, :clear  - Clear screen
:q, :quit   - Exit program
"""
            await self.interface.tool_controller.invoke_tool(
                "ChatTerminalWidget.write",
                help_text
            ) 