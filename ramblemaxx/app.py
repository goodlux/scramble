"""
RambleMaxx - Unleashed version of Ramble
Now with 100% more MAXX and 100% less React
"""

import os

from scramble.core.compressor import SemanticCompressor
from scramble.core.store import  ContextManager
from scramble.core.api import AnthropicClient
from scramble.core.mcp import MCPHandler
from scramble.core.tools import ToolInterface




from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import (
    Header, 
    Footer, 
    Static, 
    MarkdownViewer,
    TextArea,
    Input,
    MarkdownViewer
)
from textual.binding import Binding
from textual.reactive import reactive
from textual.css.query import NoMatches
from rich.markdown import Markdown




class RambleMaxx(App[None], ToolInterface):
    """The MAXX version of Ramble"""
    
    CSS_PATH = "styles/maxx.tcss"
    
    BINDINGS = [
        ("ctrl+t", "cycle_theme", "Theme"),
        ("ctrl+b", "toggle_sidebar", "Toggle Code"),
        ("ctrl+k", "clear", "Clear"),
        ("ctrl+m", "cycle_mode", "Mode"),
        ("f1", "show_help", "Help"),
    ]
    
    def __init__(self):
        super().__init__()
        self.compressor = SemanticCompressor()
        self.context_manager = ContextManager()
        self.client = AnthropicClient(
            api_key=os.getenv('ANTHROPIC_API_KEY'),
            compressor=self.compressor,
            context_manager=self.context_manager
        )
        self.current_view_mode = "split"
        self.mcp = MCPHandler(self)
        self.tools = {}  # Registered tools

    async def register_tool(self, tool: ScrollTool) -> None:
        """Register a tool with the interface."""
        self.tools[tool.name] = tool
        
    async def handle_tool_call(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Handle a tool being called."""
        if tool_name not in self.tools:
            raise ValueError(f"Unknown tool: {tool_name}")
        return await self.tools[tool_name].run(**kwargs)


class MAXXViewer(MarkdownViewer):
    """Custom markdown viewer that handles our content updates."""
    
    async def append_markdown(self, text: str) -> None:
        """Add new markdown content."""
        current = self.document.text if self.document else ""
        if current:
            current += "\n\n"
        self.markdown = current + text

class RambleMaxx(App[None]):
    """The MAXX version of Ramble"""
    
    CSS_PATH = "styles/maxx.tcss"
    
    BINDINGS = [
        ("ctrl+t", "cycle_theme", "Theme"),
        ("ctrl+b", "toggle_sidebar", "Toggle Code"),
        ("ctrl+k", "clear", "Clear"),
        ("ctrl+m", "cycle_mode", "Mode"),
        ("f1", "show_help", "Help"),
    ]

    def compose(self) -> ComposeResult:
        """Create our MAXX interface."""
        yield Header(show_clock=True)
        yield Static("🚀 RAMBLEMAXX [bold red]TURBO EDITION[/bold red] 🚀", id="maxx-header")
        yield Horizontal(
            Vertical(
                MAXXViewer(id="chat-log"),  # Using our custom viewer
                Input(
                    placeholder="💭 Enter MAXX chat or :help for commands...",
                    id="chat-input"
                ),
                id="chat-pane"
            ),
            Vertical(
                TextArea(
                    language="python",
                    id="code-editor",
                    #placeholder="// Your MAXX code here..."
                ),
                MAXXViewer(id="code-output"),  # Using our custom viewer
                id="code-pane"
            ),
            id="main-container"
        )
        yield Footer()

    async def on_mount(self) -> None:
        """Set up the app when it starts."""
        try:
            self.chat_log = self.query_one("#chat-log", MarkdownViewer)
            self.code_editor = self.query_one("#code-editor", TextArea)
            self.chat_input = self.query_one("#chat-input", Input)
            
            # Show welcome message
            welcome_md = Markdown("""
# Welcome to RambleMaxx 🚀

[bold red]TURBO EDITION[/bold red]

- Split pane layout for maximum power
- Full markdown and code support
- Theme switching with Ctrl+T
- View modes with Ctrl+M
- Help available with F1

Let's get MAXX! 
            """)
            self.chat_log.markdown = welcome_md
        except NoMatches as e:
            self.notify("Error setting up interface", severity="error")

    async def handle_maxx_chat(self, text: str) -> None:
        """Process chat messages."""
        # Show user message
        current_md = self.chat_log.markdown
        new_md = Markdown(str(current_md) + f"\n\n**You**: {text}\n\n")
        self.chat_log.markdown = new_md
        
        # Get Claude's response
        response = await self.client.send_message(text)
        
        # Update with Claude's response
        current_md = self.chat_log.markdown
        new_md = Markdown(str(current_md) + f"\n\n**Claude**: {response['response']}\n\n")
        self.chat_log.markdown = new_md

    async def handle_maxx_command(self, command: str) -> None:
        """Handle MAXX commands."""
        if command == "help":
            help_text = """
# RambleMaxx Commands

- `:help` - Show this help
- `:clear` - Clear chat
- `:theme` - Cycle themes
- `:mode` - Change view mode
            """
            await self.chat_log.load(help_text)
        elif command == "clear":
            await self.action_clear()
        else:
            self.notify(f"Unknown command: {command}", severity="error")

    async def action_clear(self) -> None:
        """Clear the chat."""
        await self.chat_log.load("")
    def action_toggle_sidebar(self) -> None:
        """Toggle code pane visibility."""
        try:
            code_pane = self.query_one("#code-pane")
            code_pane.visible = not code_pane.visible
        except NoMatches:
            self.notify("Code pane not found", severity="error")

    def action_show_help(self) -> None:
        """Show help overlay."""
        self.notify("Help system coming soon!", severity="information")