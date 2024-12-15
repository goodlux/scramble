from textual.message import Message
from textual.events import Key
from rich.segment import Segment
from rich.style import Style
import pyte
from .base_textual_widget import BaseTextualWidget

class ChatTerminalWidget(BaseTextualWidget):
    """A terminal-like widget optimized for chat interactions."""
    
    DEFAULT_CSS = """
    ChatTerminalWidget {
        background: #111111;
        color: #cccccc;
        border: none;
        padding: 0;
        margin: 0;
    }
    """

    def __init__(
        self,
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ):
        super().__init__(name=name, id=id, classes=classes)
        
        # Use private attributes for pyte screen and stream
        self._screen = pyte.Screen(80, 24)
        self._stream = pyte.Stream(self._screen)
        
        # Input handling
        self.input_buffer = ""
        self.cursor_position = 0
        
        # Register tools
        self.register_tool("write", self.write)
        self.register_tool("clear", self.clear)

    def update_terminal_size(self) -> None:
        """Update terminal size based on widget size."""
        width = max(1, self.size.width // 8)
        height = max(1, self.size.height // 16)
        
        if (width, height) != (self._screen.columns, self._screen.lines):
            new_screen = pyte.Screen(width, height)
            new_screen.reset()
            self._screen = new_screen
            self._stream = pyte.Stream(self._screen)

    def write(self, text: str) -> None:
        """Write text to the terminal."""
        if not text.endswith('\r\n') and '\n' in text:
            text = text.replace('\n', '\r\n')
            
        self._stream.feed(text)
        self.refresh()

    def clear(self) -> None:
        """Clear the terminal screen."""
        self._screen.reset()
        self.refresh()
    
    def render(self) -> list[Segment]:
        """Render the terminal content."""
        lines = []
        for lineno in range(self._screen.lines):
            line = []
            for char in self._screen.buffer[lineno]:
                style = Style(
                    color=char.fg or "white",
                    bgcolor=char.bg or "black",
                    bold=char.bold,
                    italic=char.italics,
                )
                line.append(Segment(char.data, style))
            lines.extend(line)
            if lineno < self._screen.lines - 1:
                lines.append(Segment("\n"))
        return lines