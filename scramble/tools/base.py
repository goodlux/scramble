from dataclasses import dataclass
from typing import Any, Dict, Optional

@dataclass
class ScrollTool:
    """Base class for all Scroll tools."""
    name: str
    description: str
    
    async def run(self, **kwargs) -> Dict[str, Any]:
        """All tools must implement run."""
        raise NotImplementedError
    

class LocalTool:
    """Base class for UI/interface tools."""
    name: str
    description: str
    tool_type: Literal["ui", "code", "view"] = "ui"
    
    async def run(self, **kwargs) -> Dict[str, Any]:
        """Run the local tool."""
        raise NotImplementedError

class MCPTool:
    """Base class for MCP-compatible tools."""
    name: str
    description: str
    tool_type: Literal["mcp"] = "mcp"
    
    async def run(self, **kwargs) -> Dict[str, Any]:
        """Run the MCP tool."""
        raise NotImplementedError
    
    