# scramble/interface/widgets/base.py
from textual.widget import Widget
from textual.message import Message
from typing import Dict, Any, Optional

class BaseTextualWidget(Widget):
    """Base class for Scramble widgets."""
    
    def __init__(
        self,
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ):
        super().__init__(name=name, id=id, classes=classes)
        self.interface = None
        self.capabilities: Dict[str, bool] = {}
        self.tool_methods: Dict[str, callable] = {}
        
    def register_tool(self, name: str, method: callable) -> None:
        """Register a widget method as a tool."""
        self.tool_methods[name] = method
        
    def set_interface(self, interface) -> None:
        """Connect widget to interface."""
        self.interface = interface
        # Register tools with interface
        for name, method in self.tool_methods.items():
            self.interface.tool_controller.register_tool(
                f"{self.__class__.__name__}.{name}",
                method
            )
            
    async def handle_command(self, command: str) -> None:
        """Handle widget-specific commands."""
        pass

    class BaseMessage(Message):
        """Base message type for Scramble Base widgets."""
        def __init__(self, widget: "BaseWidget", data: Any):
            self.widget = widget
            self.data = data
            super().__init__()