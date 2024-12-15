from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Literal
from ..core.scroll import ScrollEntry

class ScrollTool(ABC):
    """Base class for all tools."""
    name: str
    description: str
    
    @abstractmethod
    async def run(
        self,
        entry: Optional[ScrollEntry] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Run the tool."""
        pass

class LocalTool(ScrollTool):
    """Tool that runs locally in the same process."""
    pass

class MCPTool(ScrollTool):
    """Tool that runs on a remote MCP server."""
    server_url: str
    
    async def run(
        self, 
        entry: Optional[ScrollEntry] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Run tool on remote server via MCP."""
        # Basic implementation to satisfy return type
        return {
            "action": "mcp_call",
            "server": self.server_url,
            "kwargs": kwargs
        }

class DynamicTool(LocalTool):
    """Tool created by models at runtime."""
    source_code: str
    tool_type: str  # ui, code, view