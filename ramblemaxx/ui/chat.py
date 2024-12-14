from textual.widgets import Static
from textual.reactive import reactive
from rich.markdown import Markdown
from typing import Optional

class ChatMessage(Static):
    """Individual chat message with role-based styling."""
    
    message_type = reactive("user")  # user or assistant
    
    def __init__(
        self,
        message: str,
        message_type: str = "user",
        **kwargs
    ):
        super().__init__("", **kwargs)
        self.message_type = message_type
        self.message = message
    
    def render(self) -> str:
        if self.message_type == "user":
            return f"💭 **You**: {self.message}"
        return f"🤖 **Assistant**: {self.message}"

class ChatLog(Static):
    """Scrollable chat history with markdown support."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.messages = []
    
    async def add_message(self, message: str, message_type: str = "user") -> None:
        """Add a new message to the chat."""
        msg = ChatMessage(message, message_type)
        self.messages.append(msg)
        await self._update_display()
    
    async def _update_display(self) -> None:
        """Update the chat display."""
        content = "\n\n".join(msg.render() for msg in self.messages)
        self.update(Markdown(content))