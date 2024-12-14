from typing import List, Dict, Any
from .base import ScrollTool

class ToolInterface:
    """Interface that UIs must implement for tool support."""
    
    async def register_tool(self, tool: ScrollTool) -> None:
        """Register a tool with this interface."""
        raise NotImplementedError
    
    async def handle_tool_call(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Handle a tool being called."""
        raise NotImplementedError

    async def get_capabilities(self) -> List[str]:
        """Return what this interface can handle."""
        raise NotImplementedError